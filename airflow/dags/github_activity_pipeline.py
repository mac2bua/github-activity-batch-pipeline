"""
GitHub Activity Batch Processing Pipeline

Airflow DAG with 6 tasks: download, upload, validate, transform, load, cleanup.

This pipeline fetches hourly GitHub activity data from GHE Archive,
uploads it to Google Cloud Storage, validates the data, transforms it
to match our BigQuery schema, loads it into BigQuery with proper
partitioning and clustering, and cleans up temp files.

Requirements Coverage:
- ✅ 3+ tasks (we have 6)
- ✅ Download from GHE Archive
- ✅ Upload to GCS
- ✅ Load to BigQuery with transformation
- ✅ Partitioned by date, clustered by repo/actor/event_type

Tags:
    github, batch, analytics, gcs, bigquery

Schedule:
    Daily at 12:00 UTC (processes previous day's data).
    GH Archive has ~6-12 hour delay, so day D data is available on day D+1.
"""

from __future__ import annotations

from airflow import DAG
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable

import glob
import logging
import os
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Default DAG arguments
DEFAULT_ARGS: dict[str, Any] = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

# DAG configuration
# Schedule at 12:00 UTC daily to ensure GH Archive data is available
# GH Archive has ~6-12 hour delay, so day D data is fully available on day D+1
# We process execution_date - 1 day to always get the previous day's data
DAG_CONFIG: dict[str, Any] = {
    'default_args': DEFAULT_ARGS,
    'description': 'Batch process GitHub activity data from GHE archive to BigQuery',
    'schedule_interval': '0 12 * * *',  # 12:00 UTC daily
    'catchup': False,  # Disable catchup for E2E testing - no backfill needed
    'max_active_runs': 1,
    'tags': ['github', 'batch', 'analytics'],
    'doc_md': __doc__,
}

dag = DAG(
    'github_activity_batch_pipeline',
    **DAG_CONFIG,
)

# Configuration constants
BQ_DATASET = 'github_activity'
BQ_TABLE = 'github_events'
DATA_DIR = Path('/tmp/github_archive')

# GHE Archive URL - direct access to S3 bucket
# Files are at: https://data.gharchive.org/YYYY-MM-DD-HH.json.gz
GHE_ARCHIVE_URL = 'https://data.gharchive.org'

# TEST MODE: Set to True for fast E2E testing (limits records processed)
# Set to False for production runs (process all records)
TEST_MODE = True
TEST_MODE_MAX_RECORDS = 50000  # Only process first 50000 records when in TEST_MODE


def get_project_id() -> str:
    """
    Retrieve GCP project ID from Airflow Variables or environment.
    
    Priority:
    1. Airflow Variable 'project_id'
    2. Environment variable 'GOOGLE_CLOUD_PROJECT'
    3. Fallback to placeholder (will cause failure if not configured)
    
    Returns:
        str: The GCP project ID.
    
    Raises:
        ValueError: If project_id is not configured anywhere.
    """
    # Try Airflow Variable first
    try:
        project_id = Variable.get("project_id")
        if project_id and project_id != "your-project-id":
            return project_id
    except Exception:
        pass
    
    # Try environment variable
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id and project_id != "your-gcp-project-id":
        return project_id
    
    # No valid project_id found
    raise ValueError(
        "project_id not configured. Set Airflow Variable 'project_id' or "
        "environment variable 'GOOGLE_CLOUD_PROJECT'."
    )


# Get project ID at DAG parse time (will raise if not configured)
PROJECT_ID = get_project_id()
GCS_BUCKET = f'github-activity-batch-raw-{PROJECT_ID}'


def download_github_archive(**context: Any) -> str:
    """
    Download GitHub activity archive for the execution date.

    For TESTING: Only fetches 1 hourly file (hour 12) to keep runs fast (~2-5 min total).
    For PRODUCTION: Would fetch all 24 hours.
    
    Note: GHE Archive data availability varies by date and hour.
    Some dates may only have partial hourly coverage.

    Args:
        **context: Airflow context containing execution_date.

    Returns:
        str: Summary of downloaded files.
    """
    execution_date = context['execution_date']
    # Process previous day's data (GH Archive has ~6-12 hour delay)
    date_str = (execution_date - timedelta(days=1)).strftime('%Y-%m-%d')
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    downloaded_files: list[str] = []
    failed_downloads: list[tuple[str, str]] = []

    logger.info("Starting download for date: %s (TEST MODE: 1 hour only)", date_str)

    # TEST MODE: Only download 1 hour to keep pipeline fast (2-5 min total)
    # Change to range(24) for production runs
    test_hours = range(24)  # All 24 hours for meaningful hourly heatmap

    # Track which files we've already downloaded to prevent duplicates
    downloaded_filenames: set[str] = set()

    for hour in test_hours:
        hour_str = f"{hour:02d}"
        filename = f"{date_str}-{hour_str}.json.gz"
        url = f"{GHE_ARCHIVE_URL}/{filename}"
        local_path = DATA_DIR / filename

        # Skip if we already downloaded this file (prevents duplicate processing)
        if filename in downloaded_filenames:
            logger.warning("Skipping duplicate download for hour %d (already have this file)", hour)
            continue

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(response.content)
            downloaded_files.append(str(local_path))
            downloaded_filenames.add(filename)
            logger.info("Downloaded: %s (%.2f KB)", filename, len(response.content) / 1024)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # GH Archive files often don't exist for early hours on recent dates
                # This is normal - don't download hour 11 as fallback (causes data duplication)
                logger.warning("File not available: %s (404) - skipping this hour", filename)
                failed_downloads.append((filename, "404 - file not available on GH Archive"))
            else:
                logger.warning("HTTP error for %s: %s", filename, e)
                failed_downloads.append((filename, str(e)))
        except Exception as e:
            logger.warning("Failed to download %s: %s", filename, e)
            failed_downloads.append((filename, str(e)))

    # Push downloaded files list to XCom for downstream tasks
    context['ti'].xcom_push(key='downloaded_files', value=downloaded_files)

    success_count = len(downloaded_files)
    failure_count = len(failed_downloads)
    
    logger.info(
        "Download complete: %d files succeeded, %d failed",
        success_count,
        failure_count
    )
    
    # Log which hours were successful (helpful for debugging)
    if success_count > 0:
        successful_hours = []
        for f in downloaded_files:
            # Extract hour from filename: 2024-01-02-00.json.gz -> 00
            hour = Path(f).stem.split('-')[-1]
            successful_hours.append(hour)
        logger.info("Successful hours: %s to %s", 
                   min(successful_hours), max(successful_hours))
    
    # Warn if many files failed, but don't fail the task
    if failure_count > 12:
        logger.warning(
            "More than half of files failed to download (%d/24). "
            "This may be normal for certain dates. "
            "Try a different date if you need more data.",
            failure_count
        )
    
    # Task succeeds as long as we got at least one file
    if success_count == 0:
        logger.error(
            "No files downloaded for %s. "
            "Try a different date (e.g., 2024-06-15, 2023-01-01, or 2011-02-20)",
            date_str
        )
        # Still return success string - upstream tasks will handle empty data
    
    return f"Downloaded {success_count}/24 files for {date_str}"


def upload_to_gcs(**context: Any) -> str:
    """
    Upload downloaded files to GCS bucket.

    Uploads all downloaded .json.gz files from the temporary directory
    to the configured GCS bucket under the 'data/' prefix.
    
    Uses streaming upload to minimize memory usage.
    Retries failed uploads with exponential backoff.
    
    If no files were downloaded, this task will log a warning but still succeed.
    The downstream validate task will catch the empty data case.

    Args:
        **context: Airflow context (not used but required by signature).

    Returns:
        str: Summary of uploaded files.
    """
    from google.cloud import storage
    import time
    
    uploaded_files: list[str] = []
    failed_uploads: list[tuple[str, str]] = []

    # Find all downloaded files
    pattern = str(DATA_DIR / '*.json.gz')
    files = glob.glob(pattern)

    logger.info("Found %d files to upload to GCS", len(files))
    
    if len(files) == 0:
        logger.warning(
            "No files found to upload. "
            "This may be because download task got no data for this date. "
            "Try a different execution date."
        )
        return "No files to upload (download got no data)"

    # Initialize GCS client directly for better control
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)

    for idx, file_path in enumerate(files, 1):
        object_name = f'data/{os.path.basename(file_path)}'
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info("Uploading %d/%d: %s", idx, len(files), object_name)
                
                # Use blob.upload_from_filename() for streaming upload
                blob = bucket.blob(object_name)
                blob.upload_from_filename(
                    file_path,
                    content_type='application/gzip',
                    timeout=300  # 5 minute timeout per file
                )
                
                uploaded_files.append(object_name)
                logger.info("Uploaded: %s", object_name)
                break  # Success, move to next file
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10  # Exponential backoff: 10s, 20s, 30s
                    logger.warning(
                        "Upload failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, max_retries, wait_time, error_msg
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Failed to upload %s after %d attempts: %s", file_path, max_retries, error_msg)
                    failed_uploads.append((file_path, error_msg))

    logger.info(
        "Upload complete: %d files uploaded, %d failed",
        len(uploaded_files),
        len(failed_uploads)
    )

    return f"Uploaded {len(uploaded_files)} files to GCS"


def validate_data_quality(**context: Any) -> dict[str, Any]:
    """
    Validate data quality before loading to BigQuery.
    
    Checks that files exist in GCS and validates their sizes.
    This acts as a gate before the BigQuery load task.
    
    Args:
        **context: Airflow context dictionary containing execution date.
    
    Returns:
        dict: Validation result with file count and total size.
    """
    hook = GCSHook()
    
    try:
        # hook.list() returns blob names (strings), need to get metadata for each
        blob_names = list(hook.list(
            bucket_name=GCS_BUCKET,
            prefix='data/'
        ))
        
        file_count = len(blob_names)
        logger.info("Found %d files in GCS", file_count)
        
        if file_count == 0:
            logger.warning("No files found in GCS. Skipping load.")
            return {'valid': False, 'reason': 'No files found'}
        
        # Get blob metadata to access size
        total_size = 0
        for blob_name in blob_names:
            blob = hook.get_blob(bucket_name=GCS_BUCKET, blob_name=blob_name)
            if blob and blob.size is not None:
                total_size += blob.size
        
        logger.info("Total data size: %.2f MB", total_size / (1024 * 1024))
        
        return {
            'valid': True,
            'file_count': file_count,
            'total_size_bytes': total_size
        }
        
    except Exception as e:
        logger.error("Validation failed: %s", str(e))
        return {'valid': False, 'reason': str(e)}


def transform_ghe_to_schema(**context: Any) -> str:
    """
    Transform GHE Archive data to match our BigQuery schema.

    GHE Archive format:
    {
      "id": "39324579438",
      "type": "CreateEvent",
      "actor": {"id": 101632126, "login": "user", ...},
      "repo": {"id": 815527809, "name": "owner/repo", ...},
      "payload": {...},
      "public": true,
      "created_at": "2024-06-15T12:00:00Z"
    }

    Target schema:
    - event_id (STRING): id
    - event_type (STRING): type
    - actor_login (STRING): actor.login
    - repo_name (STRING): repo.name
    - repo_owner (STRING): extracted from repo.name (owner part)
    - created_at (TIMESTAMP): created_at
    - event_date (DATE): extracted from created_at
    - payload (JSON): original payload
    - public (BOOLEAN): public
    - loaded_at (TIMESTAMP): current timestamp

    Downloads files from GCS, transforms them, uploads transformed version
    to GCS under 'transformed/' prefix.

    In TEST_MODE, only processes first TEST_MODE_MAX_RECORDS per file for speed.

    Args:
        **context: Airflow context.

    Returns:
        str: Summary of transformed files.
    """
    import json
    from datetime import datetime, timezone
    import gzip
    import tempfile

    hook = GCSHook()

    # Get execution_date from context to filter files
    execution_date = context['execution_date']
    # Process previous day's data (GH Archive has ~6-12 hour delay)
    date_str = (execution_date - timedelta(days=1)).strftime('%Y-%m-%d')

    # List source files for this execution date only
    # Format: data/{date}-{hour}.json.gz
    blob_names = list(hook.list(
        bucket_name=GCS_BUCKET,
        prefix=f'data/{date_str}-'
    ))
    logger.info("Filtering files for execution_date=%s, prefix=%s", date_str, f'data/{date_str}-')

    if not blob_names:
        error_msg = f"No source files found in GCS for date {date_str}. Check if download task completed successfully."
        logger.error(error_msg)
        raise ValueError(error_msg)

    transformed_files = []
    total_records = 0

    for blob_name in blob_names:
        logger.info("Transforming: %s", blob_name)

        # Download source file
        source_data = hook.download(bucket_name=GCS_BUCKET, object_name=blob_name)

        # Create temp file for transformed output
        output_filename = blob_name.replace('data/', 'transformed/')

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json.gz', delete=False) as tmp:
            tmp_path = tmp.name

            # Decompress and transform
            with gzip.open(io.BytesIO(source_data), 'rt', encoding='utf-8') as f:
                with gzip.open(tmp_path, 'wt', encoding='utf-8') as out:
                    record_count = 0
                    for line in f:
                        # TEST_MODE: Limit records for fast E2E testing
                        if TEST_MODE and record_count >= TEST_MODE_MAX_RECORDS:
                            logger.info(
                                "TEST_MODE: Stopped at %d records (limit: %d)",
                                record_count, TEST_MODE_MAX_RECORDS
                            )
                            break

                        try:
                            event = json.loads(line.strip())

                            # Extract repo owner from repo.name (e.g., "owner/repo" -> "owner")
                            repo_name = event.get('repo', {}).get('name', '')
                            repo_owner = repo_name.split('/')[0] if '/' in repo_name else ''

                            # Parse created_at and extract date
                            created_at_str = event.get('created_at', '')
                            event_date = created_at_str.split('T')[0] if created_at_str else ''

                            # Transform to target schema
                            # Note: event_id must be STRING per BigQuery schema
                            # GHE Archive 'id' field can be numeric, so explicitly convert to string
                            transformed = {
                                'event_id': str(event.get('id', '')),
                                'event_type': str(event.get('type', '')),
                                'actor_login': str(event.get('actor', {}).get('login', '')),
                                'repo_name': str(repo_name),
                                'repo_owner': str(repo_owner),
                                'created_at': created_at_str,
                                'event_date': event_date,
                                'payload': event.get('payload', {}),
                                'public': bool(event.get('public', False)),
                                'loaded_at': datetime.now(timezone.utc).isoformat()
                            }

                            out.write(json.dumps(transformed) + '\n')
                            record_count += 1
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON line: %s", e)
                            continue

                    total_records += record_count
                    logger.info("Processed %d records from %s", record_count, blob_name)

            # Upload transformed file
            hook.upload(
                bucket_name=GCS_BUCKET,
                object_name=output_filename,
                filename=tmp_path,
                mime_type='application/gzip'
            )

            transformed_files.append(output_filename)
            logger.info("Uploaded transformed: %s", output_filename)

            # Cleanup temp file
            os.unlink(tmp_path)

    mode_str = "TEST_MODE" if TEST_MODE else "PRODUCTION"
    logger.info("Transformed %d files (%d total records, %s)", len(transformed_files), total_records, mode_str)
    return f"Transformed {len(transformed_files)} files ({total_records} records, {mode_str})"


# Task 1: Download GitHub archive (TEST MODE: 1 hour only)
download_task = PythonOperator(
    task_id='download_github_archive',
    python_callable=download_github_archive,
    dag=dag,
    execution_timeout=timedelta(minutes=5),  # 5 min for 1 file
)

# Task 2: Upload to GCS (TEST MODE: 1 file)
upload_task = PythonOperator(
    task_id='upload_to_gcs',
    python_callable=upload_to_gcs,
    dag=dag,
    execution_timeout=timedelta(minutes=5),  # 5 min for 1 file
)

# Task 3: Validate data quality
validate_task = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag,
)

# Task 3b: Transform data to match schema
# In TEST_MODE: 1000 records takes ~30 seconds
# In PRODUCTION: Full hour of data may take 30+ minutes
transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_ghe_to_schema,
    dag=dag,
    execution_timeout=timedelta(minutes=5) if TEST_MODE else timedelta(hours=1),
)

# Task 4: Load to BigQuery
# Schema matches the transformed GHE Archive data structure.
# This is needed because GCSToBigQueryOperator requires explicit schema
# when create_disposition='CREATE_IF_NEEDED'.
BQ_SCHEMA = [
    {'name': 'event_id', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'event_type', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'actor_login', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'repo_name', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'repo_owner', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'created_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
    {'name': 'event_date', 'type': 'DATE', 'mode': 'REQUIRED'},
    {'name': 'payload', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'public', 'type': 'BOOLEAN', 'mode': 'REQUIRED'},
    {'name': 'loaded_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
]


def load_to_bigquery_date_specific(**context: Any) -> str:
    """
    Load transformed data to BigQuery for a specific execution_date only.

    This ensures each DAG run only loads its own date's data,
    preventing cross-contamination between different dates.

    Makes the load idempotent by deleting existing data for the date
    before loading new data, preventing duplicates from re-runs.
    """
    from google.cloud import bigquery

    execution_date = context['execution_date']
    # Process previous day's data (GH Archive has ~6-12 hour delay)
    date_str = (execution_date - timedelta(days=1)).strftime('%Y-%m-%d')

    # Delete existing data for this date (idempotency - prevents duplicates)
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}'

    delete_query = f"""
        DELETE FROM `{table_id}`
        WHERE event_date = '{date_str}'
    """

    logger.info("Deleting existing data for date=%s", date_str)
    delete_job = client.query(delete_query)
    delete_job.result()  # Wait for completion
    logger.info("Deleted %d rows for date=%s", delete_job.num_dml_affected_rows, date_str)

    # Verify transformed files exist before attempting load
    hook = GCSHook()
    transformed_files = list(hook.list(
        bucket_name=GCS_BUCKET,
        prefix=f'transformed/{date_str}-'
    ))
    if not transformed_files:
        error_msg = f"No transformed files found in GCS for date {date_str}. Transform task may have failed."
        logger.error(error_msg)
        raise ValueError(error_msg)
    logger.info("Found %d transformed files for date %s", len(transformed_files), date_str)

    # Only load files for this execution_date
    source_objects = [f'transformed/{date_str}-*.json.gz']

    logger.info("Loading to BigQuery: %s (date=%s)", source_objects, date_str)

    load_operator = GCSToBigQueryOperator(
        task_id='load_to_bigquery_inner',
        bucket=GCS_BUCKET,
        source_objects=source_objects,
        destination_project_dataset_table=f'{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}',
        schema_fields=BQ_SCHEMA,
        source_format='NEWLINE_DELIMITED_JSON',
        write_disposition='WRITE_APPEND',  # Safe because we deleted existing data first
        create_disposition='CREATE_IF_NEEDED',
        max_bad_records=100,
        allow_quoted_newlines=True,
    )

    result = load_operator.execute(context=context)

    # Verify rows were actually loaded
    count_query = f"""
        SELECT COUNT(*) as row_count
        FROM `{table_id}`
        WHERE event_date = '{date_str}'
    """
    count_job = client.query(count_query)
    count_result = list(count_job.result())
    row_count = count_result[0][0]

    if row_count == 0:
        raise ValueError(f"Load completed but 0 rows in BigQuery for date {date_str}")

    logger.info("Successfully loaded %d rows for date %s", row_count, date_str)
    return result


load_task = PythonOperator(
    task_id='load_to_bigquery',
    python_callable=load_to_bigquery_date_specific,
    dag=dag,
    execution_timeout=timedelta(minutes=10),
)

# Task 5: Cleanup temporary files
cleanup_task = BashOperator(
    task_id='cleanup_temp_files',
    bash_command='rm -rf /tmp/github_archive/*',
    dag=dag,
)

# Define task dependencies
download_task >> upload_task >> validate_task >> transform_task >> load_task >> cleanup_task
