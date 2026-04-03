# Bugfix Summary: GitHub Activity Batch Pipeline

## Issues Fixed (2026-04-04)

### 1. validate_data_quality Task Error
**Error:** `'str' object has no attribute 'size'`

**Root Cause:** `hook.list()` returns blob names (strings), not blob objects with metadata.

**Fix:** Updated to use `hook.get_blob()` to fetch blob metadata for each blob name:
```python
blob_names = list(hook.list(bucket_name=GCS_BUCKET, prefix='data/'))
total_size = 0
for blob_name in blob_names:
    blob = hook.get_blob(bucket_name=GCS_BUCKET, blob_name=blob_name)
    if blob and blob.size is not None:
        total_size += blob.size
```

### 2. load_to_bigquery Schema Mismatch
**Error:** `Provided Schema does not match Table... Field event_id is missing in new schema`

**Root Cause:** GHE Archive native format doesn't match our BigQuery schema:
- GHE Archive: nested structure (`actor.login`, `repo.name`)
- BigQuery: flat schema with extracted fields (`actor_login`, `repo_name`, `repo_owner`, `event_date`, `loaded_at`)

**Fix:** Added new `transform_data` task that:
- Downloads files from GCS `data/` prefix
- Decompresses and parses JSON
- Extracts nested fields to flat structure
- Parses `repo_owner` from `repo.name`
- Extracts `event_date` from `created_at`
- Adds `loaded_at` timestamp
- Uploads transformed files to `transformed/` prefix

Updated `load_to_bigquery` to read from `transformed/*.json.gz`.

### 3. transform_data Upload Error
**Error:** `upload() got an unexpected keyword argument 'file_data'`

**Root Cause:** `GCSHook.upload()` expects `filename` (file path), not `file_data` (bytes).

**Fix:** Changed to use `filename` parameter matching the working `upload_to_gcs` task.

## New Task Flow

```
download_github_archive → upload_to_gcs → validate_data_quality → transform_data → load_to_bigquery → cleanup_temp_files
```

## Tests Added

### Unit Tests (`tests/test_pipeline_tasks.py`)
8 unit tests covering:
- `download_github_archive`: success + partial 404 handling
- `upload_to_gcs`: success + no files case
- `validate_data_quality`: success + no files case  
- `transform_ghe_to_schema`: success + no source files case

Run: `python3 -m pytest tests/test_pipeline_tasks.py -v`

### DAG Integrity Tests (`scripts/test_dag_integrity.py`)
5 tests validating:
- DAG object exists
- All 6 tasks exist
- Task dependency chain is correct
- Task count = 6
- Schedule configuration (@daily, catchup=true)

Run: `python3 scripts/test_dag_integrity.py`

## Files Modified

| File | Changes |
|------|---------|
| `airflow/dags/github_activity_pipeline.py` | Fixed validate_data_quality, added transform_data task, fixed upload call |
| `tests/test_pipeline_tasks.py` | New file - 8 unit tests |
| `scripts/test_dag_integrity.py` | New file - DAG integrity tests |
| `Makefile.test` | New file - test targets |

## Deployment Steps

1. Copy updated DAG to Airflow:
```bash
cp airflow/dags/github_activity_pipeline.py <AIRFLOW_DAGS_FOLDER>/
```

2. Restart Airflow scheduler (if using Docker):
```bash
docker compose restart airflow-scheduler
```

3. Trigger DAG run for a test date:
```bash
# In Airflow UI: Trigger DAG with execution_date=2024-06-15
```

4. Monitor task execution - all 6 tasks should complete successfully.

## Test Results

All tests passing:
- ✅ 8/8 unit tests
- ✅ 5/5 DAG integrity tests
