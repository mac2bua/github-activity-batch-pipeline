# Bug Fix Summary: Project ID Configuration

## Problem

The DAG was failing at runtime with a confusing error:

```
google.api_core.exceptions.NotFound: 404 POST ... 
Not found: Dataset your-project-id:github_activity
```

### Root Cause

The `get_project_id()` function in `github_activity_pipeline.py` was returning a placeholder value `"your-project-id"` when the Airflow Variable was not configured:

```python
def get_project_id() -> str:
    try:
        return Variable.get("project_id")
    except Exception:
        logger.warning("project_id Variable not found, using placeholder")
        return "your-project-id"  # ← BUG: Silent failure
```

This caused:
1. DAG to parse successfully (no immediate error)
2. Bucket name to be wrong: `github-activity-batch-raw-your-project-id`
3. BigQuery table reference to be wrong: `your-project-id.github_activity.github_events`
4. Runtime failure with confusing "Dataset not found" error

### Why Tests Didn't Catch It

The existing tests only checked:
- DAG structure (tasks exist, dependencies correct)
- Task IDs and configuration values exist
- Import succeeds

They didn't test:
- That `get_project_id()` returns a **valid** project ID
- That placeholder values are rejected
- That the DAG fails **fast** when misconfigured

## Solution

### 1. Fail Fast with Clear Error

Changed `get_project_id()` to raise `ValueError` when project_id is not configured:

```python
def get_project_id() -> str:
    """
    Retrieve GCP project ID from Airflow Variables or environment.
    
    Priority:
    1. Airflow Variable 'project_id'
    2. Environment variable 'GOOGLE_CLOUD_PROJECT'
    
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
    import os
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id and project_id != "your-gcp-project-id":
        return project_id
    
    # No valid project_id found - fail immediately
    raise ValueError(
        "project_id not configured. Set Airflow Variable 'project_id' or "
        "environment variable 'GOOGLE_CLOUD_PROJECT'."
    )
```

### 2. Added Environment Variable Fallback

Now checks `GOOGLE_CLOUD_PROJECT` environment variable as fallback:
- More flexible for Docker deployments
- Works with `.env` file configuration
- Airflow Variable still takes priority

### 3. Rejects Placeholder Values

Explicitly rejects:
- `"your-project-id"` (Airflow Variable placeholder)
- `"your-gcp-project-id"` (env var placeholder from `.env.example`)

### 4. Compute PROJECT_ID Once

Changed from calling `get_project_id()` multiple times to computing once at module load:

```python
PROJECT_ID = get_project_id()  # Computed once, fails fast
GCS_BUCKET = f'github-activity-batch-raw-{PROJECT_ID}'
```

This ensures:
- Consistent project ID throughout DAG execution
- Immediate failure if not configured (at parse time)
- No repeated lookups

## Tests Added

Created `tests/test_project_id_config.py` with:

1. **Test missing config raises ValueError**
   - Verifies fail-fast behavior
   
2. **Test Airflow Variable works**
   - Verifies primary configuration method

3. **Test environment variable works**
   - Verifies fallback mechanism

4. **Test Airflow Variable takes priority**
   - Verifies correct precedence

5. **Test placeholder values rejected**
   - Verifies "your-project-id" and "your-gcp-project-id" are rejected

6. **Test DAG import fails without project_id**
   - Critical test: ensures we fail at parse time, not runtime

## Files Changed

| File | Change |
|------|--------|
| `airflow/dags/github_activity_pipeline.py` | Fixed `get_project_id()`, added fail-fast |
| `tests/test_project_id_config.py` | New test suite (232 lines) |
| `docs/CONFIGURATION.md` | New configuration guide |
| `docs/BUGFIX_SUMMARY.md` | This file |

## How to Verify the Fix

### Before Fix (Broken Behavior)
```
1. Don't set project_id
2. DAG parses successfully ✗ (should fail)
3. Trigger DAG
4. Runtime error: "Dataset your-project-id:github_activity not found"
```

### After Fix (Correct Behavior)
```
1. Don't set project_id
2. DAG fails to parse: "ValueError: project_id not configured" ✓
3. Clear error message tells user what to fix
4. User sets project_id
5. DAG parses and runs successfully
```

## Commits

- `cd7d8d7` - Fix: Fail fast when project_id is not configured
- `13658b0` - docs: Add configuration guide for project_id and GCP setup

## Related Fixes

This fix was made after fixing the Airflow 2.8+ `GCSToBigQueryOperator` compatibility issue (commit `939de57`). Both fixes improve error handling:

1. **GCSToBigQueryOperator**: Removed invalid parameters, added integration tests
2. **Project ID**: Fail fast with clear error, added unit tests
3. **Source Objects**: Fixed GCS path pattern mismatch, added unit tests

All follow the principle: **Fail fast with clear errors, not late with confusing ones.**

---

# Bug Fix Summary: GCS Source Objects Pattern Mismatch

## Problem

The `load_to_bigquery` task was failing with:

```
google.api_core.exceptions.NotFound: 404 Not found: URI 
gs://github-activity-batch-raw-github-activity-batch-pipeline/raw/2024-01-02/
```

### Root Cause

The `source_objects` parameter in `GCSToBigQueryOperator` was set to a directory pattern:

```python
source_objects=[f'raw/{{{{ ds }}}}/']  # ← BUG: Directory doesn't exist
```

But GCS doesn't have real directories. The `upload_to_gcs` task uploads individual files:

```
raw/2024-01-02/2024-01-02-00.json.gz
raw/2024-01-02/2024-01-02-01.json.gz
...
```

There is NO object called `raw/2024-01-02/` in GCS. That "directory" is just a prefix in the file object names.

When `GCSToBigQueryOperator` tried to load from `raw/2024-01-02/`, BigQuery looked for that exact object, didn't find it, and returned 404.

### Why This Was Confusing

1. **GCS has flat namespace**: "Directories" are just prefixes in object names
2. **Upload creates files, not directories**: `raw/{ds}/file.json.gz` creates one object
3. **Directory pattern matches nothing**: `raw/{{ ds }}/` looks for non-existent object
4. **Error message is misleading**: "Not found: URI gs://..." suggests the bucket or path is wrong

## Solution

Changed `source_objects` to use wildcard pattern that matches actual files:

```python
source_objects=[f'raw/{{{{ ds }}}}/*.json.gz']  # ← FIXED: Matches uploaded files
```

This pattern:
- Uses `*` wildcard to match all `.json.gz` files
- Matches the exact pattern uploaded by `upload_to_gcs` task
- Works with GCS's flat object namespace

## Tests Added

Created `tests/test_gcs_source_objects.py` with:

1. **Test upload object_name format** - Verifies upload creates `raw/{ds}/filename.json.gz`
2. **Test source_objects uses wildcard** - Verifies load task uses `*.json.gz` pattern
3. **Test source_objects not directory-only** - Verifies pattern doesn't end with `/`
4. **Test upload and load use same prefix** - Verifies both use `raw/` consistently
5. **Test GCS bucket consistency** - Verifies both tasks use same bucket
6. **Conceptual test: GCS has no directories** - Documents GCS flat namespace behavior

## Files Changed

| File | Change |
|------|--------|
| `airflow/dags/github_activity_pipeline.py` | Fixed `source_objects` pattern |
| `tests/test_gcs_source_objects.py` | New test suite (315 lines) |
| `docs/BUGFIX_SUMMARY.md` | This file |

## How to Verify the Fix

### Before Fix (Broken)
```
source_objects=['raw/{{ ds }}/']
Result: 404 Not found: URI gs://bucket/raw/2024-01-02/
```

### After Fix (Working)
```
source_objects=['raw/{{ ds }}/*.json.gz']
Result: Finds and loads all matching files
```

## Commit

- `4dbc747` - Fix: GCSToBigQueryOperator source_objects pattern mismatch

## Key Lesson

**GCS has no directories.** Everything is a flat namespace with object names that contain `/` characters. When specifying source objects:

- ❌ `raw/2024-01-02/` - Looks for non-existent directory object
- ✅ `raw/2024-01-02/*.json.gz` - Matches actual file objects

Always use wildcards to match file patterns, never directory-only paths.
