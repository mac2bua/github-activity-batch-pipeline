"""
GitHub Archive Batch Processing DAG

DE Zoomcamp 2026 Final Project

This DAG downloads GitHub Archive data, uploads it to GCS, and loads it
into BigQuery using a MERGE statement for deduplication.

Tags:
    github, batch, zoomcamp, gcs, bigquery

Schedule:
    Daily at midnight with catchup enabled for backfilling.
"""

from __future__ import annotations

import glob
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

logger = logging.getLogger(__name__)

# Default DAG arguments
DEFAULT_ARGS: dict[str, Any] = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG configuration
dag = DAG(
    'github_archive_batch_pipeline',
    default_args=DEFAULT_ARGS,
    description='Batch processing pipeline for GitHub Archive data',
    schedule_interval=None,  # Disabled - manual triggers only for testing
    start_date=datetime(2024, 6, 1),
    catchup=False,  # Disabled to prevent backlog during testing
    max_active_runs=1,
    tags=['github', 'batch', 'zoomcamp'],
)

# Configuration from environment variables
GCS_BUCKET = os.getenv('GCS_BUCKET', 'gh-activity-dev')
BQ_DATASET = os.getenv('BQ_DATASET', 'gh_activity_dev')
BQ_TABLE = os.getenv('BQ_TABLE', 'github_events')
DATA_DIR = Path('/tmp/github_archive')


def download_github_archive(**context: Any) -> str:
    """
    Download GitHub Archive data for the execution date.

    Fetches hourly JSON.gz files from data.gharchive.org for all 24 hours
    of the execution date.

    Args:
        **context: Airflow context containing execution_date.

    Returns:
        str: Summary of downloaded files.
    """
    execution_date = context['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    base_url = "https://data.gharchive.org"
    downloaded_files: list[str] = []
    failed_downloads: list[tuple[str, str]] = []

    logger.info("Starting download for date: %s", date_str)

    # TEST MODE: Download only 1 hour for fast end-to-end testing (< 5 minutes)
    # Set to False for production runs (all 24 hours)
    TEST_MODE = True
    test_hours = [12]  # Just hour 12 (noon) for testing
    hours_to_download = test_hours if TEST_MODE else range(24)

    for hour in hours_to_download:
        hour_str = f"{hour:02d}"
        filename = f"{date_str}-{hour_str}.json.gz"
        url = f"{base_url}/{filename}"
        local_path = DATA_DIR / filename

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(response.content)
            downloaded_files.append(str(local_path))
            logger.info("Downloaded: %s", filename)
        except Exception as e:
            error_msg = str(e)
            logger.warning("Failed to download %s: %s", filename, error_msg)
            failed_downloads.append((filename, error_msg))

    # Push downloaded files list to XCom for downstream tasks
    context['ti'].xcom_push(key='downloaded_files', value=downloaded_files)

    success_count = len(downloaded_files)
    logger.info(
        "Download complete: %d/24 files succeeded, %d failed",
        success_count,
        len(failed_downloads)
    )

    return f"Downloaded {success_count} files for {date_str}"


def upload_to_gcs(**context: Any) -> str:
    """
    Upload downloaded files to GCS bucket.

    Uploads all downloaded .json.gz files from the temporary directory
    to the configured GCS bucket under the 'data/' prefix.

    Args:
        **context: Airflow context (not used but required by signature).

    Returns:
        str: Summary of uploaded files.
    """
    hook = GCSHook()
    uploaded_files: list[str] = []
    failed_uploads: list[tuple[str, str]] = []

    # Find all downloaded files
    pattern = str(DATA_DIR / '*.json.gz')
    files = glob.glob(pattern)

    logger.info("Found %d files to upload to GCS", len(files))

    for file_path in files:
        object_name = f'data/{os.path.basename(file_path)}'
        try:
            hook.upload(
                bucket_name=GCS_BUCKET,
                object_name=object_name,
                filename=file_path,
                mime_type='application/gzip'
            )
            uploaded_files.append(object_name)
            logger.info("Uploaded: %s", object_name)
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to upload %s: %s", file_path, error_msg)
            failed_uploads.append((file_path, error_msg))

    logger.info(
        "Upload complete: %d files uploaded, %d failed",
        len(uploaded_files),
        len(failed_uploads)
    )

    return f"Uploaded {len(uploaded_files)} files to GCS"


# Define tasks
download_task = PythonOperator(
    task_id='download_github_archive',
    python_callable=download_github_archive,
    dag=dag,
)

upload_task = PythonOperator(
    task_id='upload_to_gcs',
    python_callable=upload_to_gcs,
    dag=dag,
)

# Load from GCS to BigQuery using external table approach
# First create an external table from GCS, then merge into the target table
LOAD_QUERY = """
-- Create or replace external table from GCS files
CREATE OR REPLACE EXTERNAL TABLE `{{ params.dataset }}.staging_{{ params.table }}_{{ ds_nodash }}`
OPTIONS (
  format = 'JSON',
  compression = 'GZIP',
  uris = ['gs://{{ params.bucket }}/data/{{ ds }}*.json.gz']
);

-- Merge into target table with deduplication
MERGE `{{ params.dataset }}.{{ params.table }}` T
USING (
  SELECT DISTINCT
    id,
    type,
    actor.login as actor_login,
    repo.name as repo_name,
    action,
    created_at,
    DATE(created_at) as date_partition,
    TO_JSON_STRING(payload) as payload,
    org.login as org_login,
    '' as file_url
  FROM `{{ params.dataset }}.staging_{{ params.table }}_{{ ds_nodash }}`
  WHERE id IS NOT NULL
) S
ON T.id = S.id
WHEN NOT MATCHED THEN INSERT (
    id, type, actor_login, repo_name, action,
    created_at, date_partition, payload, org_login, file_url
)
VALUES (
    S.id, S.type, S.actor_login, S.repo_name, S.action,
    S.created_at, S.date_partition, S.payload, S.org_login, S.file_url
);

-- Drop the staging table
DROP EXTERNAL TABLE IF EXISTS `{{ params.dataset }}.staging_{{ params.table }}_{{ ds_nodash }}`;
"""

load_task = BigQueryInsertJobOperator(
    task_id='load_to_bigquery',
    configuration={
        'query': {
            'query': LOAD_QUERY,
            'useLegacySql': False,
        }
    },
    params={
        'dataset': BQ_DATASET,
        'table': BQ_TABLE,
        'bucket': GCS_BUCKET,
    },
    dag=dag,
)

# Define task dependencies
download_task >> upload_task >> load_task
