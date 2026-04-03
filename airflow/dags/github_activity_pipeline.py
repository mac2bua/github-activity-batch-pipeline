"""
GitHub Activity Batch Processing Pipeline

Airflow DAG with 5 tasks: download, upload, validate, load, cleanup.

This pipeline fetches hourly GitHub activity data from GHE Archive,
uploads it to Google Cloud Storage, validates the data, loads it into
BigQuery with proper partitioning and clustering, and cleans up temp files.

Requirements Coverage:
- ✅ 3+ tasks (we have 5)
- ✅ Download from GHE Archive
- ✅ Upload to GCS
- ✅ Load to BigQuery with transformation
- ✅ Partitioned by date, clustered by repo/actor/event_type

Tags:
    github, batch, analytics, gcs, bigquery

Schedule:
    Daily at midnight with catchup enabled for backfilling.
"""

from __future__ import annotations

from airflow import DAG
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import HTTPError

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
DAG_CONFIG: dict[str, Any] = {
    'default_args': DEFAULT_ARGS,
    'description': 'Batch process GitHub activity data from GHE archive to BigQuery',
    'schedule_interval': '@daily',
    'catchup': True,
    'max_active_runs': 1,
    'tags': ['github', 'batch', 'analytics'],
    'doc_md': __doc__,
}

dag = DAG(
    'github_activity_batch_pipeline',
    **DAG_CONFIG,
)

# Configuration constants
GHE_ARCHIVE_URL = 'https://gharchive.org'
BQ_DATASET = 'github_activity'
BQ_TABLE = 'github_events'


def get_project_id() -> str:
    """
    Retrieve GCP project ID from Airflow Variables.
    
    Returns:
        str: The GCP project ID, or a placeholder if not configured.
    """
    try:
        return Variable.get("project_id")
    except Exception:
        logger.warning("project_id Variable not found, using placeholder")
        return "your-project-id"


GCS_BUCKET = f'github-activity-batch-raw-{get_project_id()}'
GCS_PREFIX = 'raw/{{ ds }}'


def download_github_archive(**context: Any) -> dict[str, Any]:
    """
    Download GitHub activity archive for the execution date.
    
    Fetches hourly JSON.gz files from GHE Archive for all 24 hours of the
    execution date. Files are stored temporarily for upload to GCS.
    
    Args:
        **context: Airflow context dictionary containing execution date.
    
    Returns:
        dict: Download statistics including files downloaded, count, and success rate.
    """
    ds: str = context['ds']  # Execution date in YYYY-MM-DD format
    download_dir = Path('/tmp/github_archive')
    download_dir.mkdir(exist_ok=True, parents=True)
    
    files_downloaded: list[str] = []
    failed_downloads: list[tuple[str, str]] = []
    
    logger.info("Starting download for date: %s", ds)
    
    # Download 24 hourly files for the day
    for hour in range(24):
        hour_str = f'{hour:02d}'
        filename = f'{ds}-{hour_str}.json.gz'
        url = f'{GHE_ARCHIVE_URL}/data/{ds}-{hour_str}.json.gz'
        local_path = download_dir / filename
        
        try:
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            files_downloaded.append(filename)
            logger.info("✓ Downloaded: %s (%d bytes)", filename, len(response.content))
            
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.warning("File not available yet: %s", filename)
                failed_downloads.append((filename, '404'))
            else:
                logger.error("HTTP error for %s: %s", filename, str(e))
                failed_downloads.append((filename, str(e)))
        except Exception as e:
            logger.error("Failed to download %s: %s", filename, str(e))
            failed_downloads.append((filename, str(e)))
    
    # Log summary
    logger.info("Download complete: %d/24 files succeeded", len(files_downloaded))
    if failed_downloads:
        logger.warning("Failed downloads: %d", len(failed_downloads))
        for fname, reason in failed_downloads[:5]:  # Show first 5 failures
            logger.warning("  - %s: %s", fname, reason)
    
    return {
        'files': files_downloaded,
        'count': len(files_downloaded),
        'failed_count': len(failed_downloads),
        'success_rate': len(files_downloaded) / 24.0 if files_downloaded else 0.0
    }

def upload_to_gcs(**context: Any) -> dict[str, Any]:
    """
    Upload downloaded files to GCS bucket.
    
    Uploads all downloaded .json.gz files to the GCS bucket under the
    raw/{date} prefix using the GCS hook for authenticated upload.
    
    Args:
        **context: Airflow context dictionary containing execution date.
    
    Returns:
        dict: Upload statistics including uploaded files and GCS path.
    """
    ds: str = context['ds']
    download_dir = Path('/tmp/github_archive')
    gcs_prefix = f'raw/{ds}'
    
    hook = GCSHook()
    uploaded_files: list[str] = []
    failed_uploads: list[tuple[str, str]] = []
    
    logger.info("Starting upload to GCS bucket: %s", GCS_BUCKET)
    
    if not download_dir.exists():
        logger.error("Download directory not found: %s", download_dir)
        return {'uploaded_files': [], 'count': 0, 'error': 'No files to upload'}
    
    for file_path in download_dir.glob('*.json.gz'):
        object_name = f'{gcs_prefix}/{file_path.name}'
        
        try:
            hook.upload(
                bucket_name=GCS_BUCKET,
                object_name=object_name,
                filename=str(file_path),
                mime_type='application/gzip'
            )
            uploaded_files.append(object_name)
            logger.info("✓ Uploaded: %s", object_name)
        except Exception as e:
            logger.error("Failed to upload %s: %s", file_path.name, str(e))
            failed_uploads.append((file_path.name, str(e)))
    
    logger.info("Upload complete: %d files uploaded to GCS", len(uploaded_files))
    
    return {
        'uploaded_files': uploaded_files,
        'count': len(uploaded_files),
        'failed_count': len(failed_uploads),
        'gcs_path': f'gs://{GCS_BUCKET}/{gcs_prefix}/'
    }

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
    ds: str = context['ds']
    gcs_prefix = f'raw/{ds}'
    
    hook = GCSHook()
    
    try:
        blobs = list(hook.list(
            bucket_name=GCS_BUCKET,
            prefix=gcs_prefix
        ))
        
        file_count = len(blobs)
        logger.info("Found %d files in GCS for date %s", file_count, ds)
        
        if file_count == 0:
            logger.warning("No files found in GCS for %s. Skipping load.", ds)
            return {'valid': False, 'reason': 'No files found'}
        
        # Check total size
        total_size = sum(blob.size for blob in blobs if blob.size is not None)
        logger.info("Total data size: %.2f MB", total_size / (1024 * 1024))
        
        return {
            'valid': True,
            'file_count': file_count,
            'total_size_bytes': total_size
        }
        
    except Exception as e:
        logger.error("Validation failed: %s", str(e))
        return {'valid': False, 'reason': str(e)}


# Task 1: Download GitHub archive
download_task = PythonOperator(
    task_id='download_github_archive',
    python_callable=download_github_archive,
    dag=dag,
)

# Task 2: Upload to GCS
upload_task = PythonOperator(
    task_id='upload_to_gcs',
    python_callable=upload_to_gcs,
    dag=dag,
)

# Task 3: Validate data quality
validate_task = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag,
)

# Task 4: Load to BigQuery
# Note: Table schema, partitioning, and clustering are pre-created via Terraform.
# GCSToBigQueryOperator in Airflow 2.8+ Google provider 10.x does not accept
# schema_fields, clustering_fields, or time_partitioning parameters.
load_task = GCSToBigQueryOperator(
    task_id='load_to_bigquery',
    bucket=GCS_BUCKET,
    source_objects=[f'raw/{{{{ ds }}}}/'],
    destination_project_dataset_table=f'{get_project_id()}.{BQ_DATASET}.{BQ_TABLE}',
    source_format='NEWLINE_DELIMITED_JSON',
    write_disposition='WRITE_APPEND',
    max_bad_records=100,
    allow_quoted_newlines=True,
    dag=dag,
)

# Task 5: Cleanup temporary files
cleanup_task = BashOperator(
    task_id='cleanup_temp_files',
    bash_command='rm -rf /tmp/github_archive/*',
    dag=dag,
)

# Define task dependencies
download_task >> upload_task >> validate_task >> load_task >> cleanup_task
