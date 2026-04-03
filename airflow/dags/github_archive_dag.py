"""
GitHub Archive Batch Processing DAG
DE Zoomcamp 2026 Final Project
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalToGCSOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
import requests
import os
from pathlib import Path

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'github_archive_batch_pipeline',
    default_args=default_args,
    description='Batch processing pipeline for GitHub Archive data',
    schedule_interval='@daily',
    start_date=datetime(2026, 1, 1),
    catchup=True,
    max_active_runs=1,
    tags=['github', 'batch', 'zoomcamp'],
)

GCS_BUCKET = os.getenv('GCS_BUCKET', 'gh-activity-dev')
BQ_DATASET = os.getenv('BQ_DATASET', 'gh_activity_dev')
BQ_TABLE = os.getenv('BQ_TABLE', 'github_events')
DATA_DIR = Path('/tmp/github_archive')


def download_github_archive(**context):
    """Download GitHub Archive data for the execution date."""
    execution_date = context['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    base_url = "https://data.gharchive.org"
    downloaded_files = []
    
    for hour in range(24):
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
            print(f"Downloaded: {filename}")
        except Exception as e:
            print(f"Failed to download {filename}: {str(e)}")
    
    context['ti'].xcom_push(key='downloaded_files', value=downloaded_files)
    return f"Downloaded {len(downloaded_files)} files for {date_str}"


def load_to_bigquery(**context):
    """Load data from GCS to BigQuery."""
    execution_date = context['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    return {
        "query": f"""
        MERGE `{BQ_DATASET}.{BQ_TABLE}` T
        USING (
          SELECT * FROM `gharchive.day.{date_str}`
        ) S
        ON T.id = S.id
        WHEN NOT MATCHED THEN INSERT (id, type, actor_login, repo_name, action, created_at, date_partition, payload, org_login, file_url)
        VALUES (S.id, S.type, S.actor.login, S.repo.name, S.action, S.created_at, DATE(S.created_at), TO_JSON_STRING(S.payload), S.org.login, '')
        """,
        "useLegacySql": False
    }


download_task = PythonOperator(
    task_id='download_github_archive',
    python_callable=download_github_archive,
    provide_context=True,
    dag=dag,
)

upload_task = LocalToGCSOperator(
    task_id='upload_to_gcs',
    src=['/tmp/github_archive/*.json.gz'],
    bucket=GCS_BUCKET,
    object_prefix='data/',
    gzip=True,
    dag=dag,
)

load_task = BigQueryInsertJobOperator(
    task_id='load_to_bigquery',
    configuration={'query': load_to_bigquery},
    dag=dag,
)

download_task >> upload_task >> load_task
