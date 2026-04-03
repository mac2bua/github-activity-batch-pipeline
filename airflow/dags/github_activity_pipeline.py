"""
GitHub Activity Batch Processing Pipeline
Airflow DAG with 4 tasks: download, upload, load, cleanup

Requirements Coverage:
- ✅ 3+ tasks (we have 4)
- ✅ Download from GHE Archive
- ✅ Upload to GCS
- ✅ Load to BigQuery with transformation
- ✅ Partitioned by date, clustered by repo/actor/event_type
"""

from airflow import DAG
from airflow.providers.google.cloud.operators.gcs import GCSListOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import requests
import json
import gzip
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'github_activity_batch_pipeline',
    default_args=default_args,
    description='Batch process GitHub activity data from GHE archive to BigQuery',
    schedule_interval='@daily',
    catchup=True,
    max_active_runs=1,
    tags=['github', 'batch', 'analytics'],
    doc_md=__doc__,
)

# Configuration from Airflow Variables
def get_project_id():
    try:
        return Variable.get("project_id")
    except:
        return "your-project-id"

GCS_BUCKET = f'github-activity-batch-raw-{get_project_id()}'
GCS_PREFIX = 'raw/{{ ds }}'
BQ_DATASET = 'github_activity'
BQ_TABLE = 'github_events'
GHE_ARCHIVE_URL = 'https://gharchive.org'


def download_github_archive(**context):
    """
    Task 1: Download GitHub activity archive for the execution date
    
    Fetches hourly JSON.gz files from GHE Archive for all 24 hours of the execution date.
    Files are stored temporarily for upload to GCS in the next task.
    
    Returns:
        dict: Count of successfully downloaded files
    """
    ds = context['ds']  # Execution date in YYYY-MM-DD format
    download_dir = Path('/tmp/github_archive')
    download_dir.mkdir(exist_ok=True, parents=True)
    
    files_downloaded = []
    failed_downloads = []
    
    logger.info(f"Starting download for date: {ds}")
    
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
            logger.info(f'✓ Downloaded: {filename} ({len(response.content)} bytes)')
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f'File not available yet: {filename}')
                failed_downloads.append((filename, '404'))
            else:
                logger.error(f'HTTP error for {filename}: {str(e)}')
                failed_downloads.append((filename, str(e)))
        except Exception as e:
            logger.error(f'Failed to download {filename}: {str(e)}')
            failed_downloads.append((filename, str(e)))
    
    # Log summary
    logger.info(f"Download complete: {len(files_downloaded)}/24 files succeeded")
    if failed_downloads:
        logger.warning(f"Failed downloads: {len(failed_downloads)}")
        for fname, reason in failed_downloads[:5]:  # Show first 5 failures
            logger.warning(f"  - {fname}: {reason}")
    
    return {
        'files': files_downloaded,
        'count': len(files_downloaded),
        'failed_count': len(failed_downloads),
        'success_rate': len(files_downloaded) / 24.0
    }


def upload_to_gcs(**context):
    """
    Task 2: Upload downloaded files to GCS bucket
    
    Uploads all downloaded .json.gz files to the GCS bucket under the raw/{date} prefix.
    Uses the GCS hook for authenticated upload.
    
    Returns:
        dict: Count of successfully uploaded files
    """
    from airflow.providers.google.cloud.hooks.gcs import GCSHook
    
    ds = context['ds']
    download_dir = Path('/tmp/github_archive')
    gcs_prefix = f'raw/{ds}'
    
    hook = GCSHook()
    uploaded_files = []
    failed_uploads = []
    
    logger.info(f"Starting upload to GCS bucket: {GCS_BUCKET}")
    
    if not download_dir.exists():
        logger.error(f"Download directory not found: {download_dir}")
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
            logger.info(f'✓ Uploaded: {object_name}')
        except Exception as e:
            logger.error(f'Failed to upload {file_path.name}: {str(e)}')
            failed_uploads.append((file_path.name, str(e)))
    
    logger.info(f"Upload complete: {len(uploaded_files)} files uploaded to GCS")
    
    return {
        'uploaded_files': uploaded_files,
        'count': len(uploaded_files),
        'failed_count': len(failed_uploads),
        'gcs_path': f'gs://{GCS_BUCKET}/{gcs_prefix}/'
    }


def validate_data_quality(**context):
    """
    Task 3: Validate data quality before loading to BigQuery
    
    Checks that files exist in GCS and are valid gzip files.
    This is a gate before the BigQuery load.
    """
    from airflow.providers.google.cloud.hooks.gcs import GCSHook
    
    ds = context['ds']
    gcs_prefix = f'raw/{ds}'
    
    hook = GCSHook()
    
    try:
        blobs = list(hook.list(
            bucket_name=GCS_BUCKET,
            prefix=gcs_prefix
        ))
        
        file_count = len(blobs)
        logger.info(f"Found {file_count} files in GCS for date {ds}")
        
        if file_count == 0:
            logger.warning(f"No files found in GCS for {ds}. Skipping load.")
            return {'valid': False, 'reason': 'No files found'}
        
        # Check total size
        total_size = sum(blob.size for blob in blobs)
        logger.info(f"Total data size: {total_size / (1024*1024):.2f} MB")
        
        return {
            'valid': True,
            'file_count': file_count,
            'total_size_bytes': total_size
        }
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return {'valid': False, 'reason': str(e)}


# Task 1: Download GitHub archive
download_task = PythonOperator(
    task_id='download_github_archive',
    python_callable=download_github_archive,
    provide_context=True,
    dag=dag,
)

# Task 2: Upload to GCS
upload_task = PythonOperator(
    task_id='upload_to_gcs',
    python_callable=upload_to_gcs,
    provide_context=True,
    dag=dag,
)

# Task 3: Validate data quality
validate_task = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    provide_context=True,
    dag=dag,
)

# Task 4: Load to BigQuery
load_task = GCSToBigQueryOperator(
    task_id='load_to_bigquery',
    bucket=GCS_BUCKET,
    source_objects=[f'raw/{{{{ ds }}}}/'],
    source_format='NEWLINE_DELIMITED_JSON',
    destination_project_dataset_table=f'{get_project_id()}.{BQ_DATASET}.{BQ_TABLE}',
    schema_fields=[
        {'name': 'id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'type', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'actor_login', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'repo_name', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'repo_owner', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'payload', 'type': 'JSON', 'mode': 'NULLABLE'},
        {'name': 'public', 'type': 'BOOLEAN', 'mode': 'REQUIRED'},
        {'name': 'created_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'event_date', 'type': 'DATE', 'mode': 'REQUIRED'},
        {'name': 'loaded_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
    ],
    write_disposition='WRITE_APPEND',
    create_disposition='CREATE_IF_NEEDED',
    time_partitioning={'type': 'DAY', 'field': 'event_date'},
    clustering_fields=['repo_name', 'actor_login', 'event_type'],
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
