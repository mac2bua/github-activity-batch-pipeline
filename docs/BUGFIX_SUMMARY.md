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

Both follow the principle: **Fail fast with clear errors, not late with confusing ones.**
