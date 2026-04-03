# Bug Fix Summary: GCS Path Mismatch and GHE Archive URL

## Problem

The `download_github_archive` task was failing with all 24 hourly files returning 404 errors:

```
[2026-04-03, 22:24:41 UTC] WARNING - File not available yet: 2024-01-01-00.json.gz
...
[2026-04-03, 22:24:50 UTC] INFO - Download complete: 0/24 files succeeded, 24 failed
```

Additionally, even if downloads succeeded, the `load_to_bigquery` task would fail with:
```
404 Not found: URI gs://bucket/raw/2024-01-02/
```

## Root Causes

### Bug 1: GCS Path Mismatch

The upload and load tasks were using different path formats:

| Task | Path Format | Example |
|------|-------------|---------|
| `upload_to_gcs` | `data/{filename}` | `data/2024-01-02-00.json.gz` |
| `GCSToBigQueryOperator` | `raw/{{ ds }}/*.json.gz` | `raw/2024-01-02/*.json.gz` |

**Result**: Files uploaded to `data/` but BigQuery looked in `raw/{date}/` → 404 error.

### Bug 2: Incorrect GHE Archive URL

The download task was using the wrong URL format:

```python
# WRONG (returns 404)
url = "https://gharchive.org/data/2024-01-01-00.json.gz"

# CORRECT (returns 200)
url = "https://data.gharchive.org/2024-01-01-00.json.gz"
```

The old code used `GHE_ARCHIVE_URL = 'https://gharchive.org'` and appended `/data/`, but the actual files are hosted directly on `data.gharchive.org`.

### Bug 3: Data Availability

Even with the correct URL, some dates have incomplete data. For example, 2024-01-01 had some hours available but not all 24. The task should succeed with partial downloads.

## Solution

### 1. Fixed GCS Path Consistency

Changed both tasks to use the same flat `data/` prefix:

```python
# upload_to_gcs
object_name = f'data/{os.path.basename(file_path)}'

# GCSToBigQueryOperator
source_objects=['data/*.json.gz']
```

### 2. Fixed GHE Archive URL

```python
# Direct access to S3 bucket
GHE_ARCHIVE_URL = 'https://data.gharchive.org'

# File URL construction
url = f"{GHE_ARCHIVE_URL}/{filename}"
# Result: https://data.gharchive.org/2024-01-02-00.json.gz
```

### 3. Allow Partial Downloads

The download task now:
- Succeeds as long as at least one file is downloaded
- Logs warnings for failed downloads
- Warns if >50% of files fail (suggests trying a different date)
- Pushes downloaded files list to XCom for downstream tasks

### 4. Simplified Code

- Removed complex nested path structure (`raw/{date}/`)
- Use flat `data/` prefix for all files
- Removed unused return dict from download/upload functions
- Consistent error handling across all tasks

## Files Changed

| File | Change |
|------|--------|
| `airflow/dags/github_activity_pipeline.py` | Fixed URL, paths, and partial download handling |
| `tests/test_gcs_source_objects.py` | Updated tests for new path format |

## How to Test

### 1. Choose a Date with Good Data

Some dates have better coverage than others. For testing:
- ✅ **Good dates**: 2024-06-15, 2023-01-01 (most hours available)
- ⚠️ **Partial dates**: 2024-01-01 (some hours missing)
- ❌ **Bad dates**: Very recent dates (data not yet available)

### 2. Trigger DAG in Airflow UI

1. Go to http://localhost:8080
2. Find `github_activity_batch_pipeline`
3. Click "Play" button
4. Set execution date (e.g., `2024-06-15`)
5. Watch task logs

### 3. Expected Results

**Download task**:
```
INFO - Starting download for date: 2024-06-15
INFO - Downloaded: 2024-06-15-00.json.gz
...
INFO - Download complete: 24/24 files succeeded, 0 failed
```

**Upload task**:
```
INFO - Found 24 files to upload to GCS
INFO - Uploaded: data/2024-06-15-00.json.gz
...
INFO - Upload complete: 24 files uploaded, 0 failed
```

**Load task**:
```
INFO - Using existing BigQuery table for storing data...
INFO - Executing: {'load': {... 'sourceUris': ['gs://bucket/data/*.json.gz'] ...}}
```

## Verification Commands

```bash
# Test URL format
curl -I https://data.gharchive.org/2024-06-15-00.json.gz
# Should return: HTTP/2 200

# Test old URL (should fail)
curl -I https://gharchive.org/data/2024-06-15-00.json.gz
# Should return: HTTP/2 404

# Validate DAG syntax
python3 -m py_compile airflow/dags/github_activity_pipeline.py
```

## Commits

- `921845c` - Fix: GCS path mismatch and GHE Archive URL format

## Key Lessons

1. **Path consistency is critical**: Upload and load tasks must use the same path format
2. **GCS has no directories**: Always use wildcards (`*.json.gz`) to match file objects
3. **Test URLs before deploying**: A simple `curl -I` can catch URL format errors
4. **Handle partial data gracefully**: External data sources may have gaps
5. **Flat is better than nested**: Simple `data/` prefix is easier than `raw/{date}/`

## Related Fixes

This fix builds on previous bug fixes:
- `cd7d8d7` - Fail fast when project_id is not configured
- `4dbc747` - GCSToBigQueryOperator source_objects pattern mismatch

All follow the principle: **Fail fast with clear errors, test thoroughly, and handle edge cases gracefully.**
