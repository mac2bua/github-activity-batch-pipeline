# Fix Summary: BigQuery Schema Type Mismatch

**Date:** 2026-04-04 01:32 GMT+2  
**Error:** `Field event_id has changed type from STRING to INTEGER`

---

## Root Cause

The GHE Archive `id` field can be **numeric** (e.g., `39324579438`), but our BigQuery schema defines `event_id` as `STRING`. When the transform task wrote numeric IDs directly, BigQuery interpreted them as `INTEGER`, causing a schema mismatch on subsequent loads.

**Error from BigQuery:**
```
google.api_core.exceptions.BadRequest: 400 Provided Schema does not match Table 
github-activity-batch-pipeline:github_activity.github_events. 
Field event_id has changed type from STRING to INTEGER
```

---

## Fix Applied

Added explicit type casting in `transform_ghe_to_schema()` to ensure all fields match BigQuery schema types:

```python
transformed = {
    'event_id': str(event.get('id', '')),      # ← Cast to STRING
    'event_type': str(event.get('type', '')),  # ← Cast to STRING
    'actor_login': str(event.get('actor', {}).get('login', '')),
    'repo_name': str(repo_name),
    'repo_owner': str(repo_owner),
    'created_at': created_at_str,
    'event_date': event_date,
    'payload': event.get('payload', {}),
    'public': bool(event.get('public', False)),  # ← Explicit bool
    'loaded_at': datetime.now(timezone.utc).isoformat()
}
```

**Key changes:**
- `str(event.get('id', ''))` - Ensures numeric IDs become strings
- `bool(event.get('public', False))` - Explicit boolean conversion
- `str()` on all string fields - Prevents any type ambiguity

---

## Testing

### 1. Unit Tests (9/9 Passing)
```bash
python3 -m pytest tests/test_pipeline_tasks.py -v
```

Added regression test `test_transform_event_id_type_casting` to verify numeric IDs are cast to strings.

### 2. Schema Verification (PASSED)
```bash
python3 scripts/verify_transform_output.py
```

Output:
```
✓ event_id: str (expected: str)
✓ event_type: str (expected: str)
✓ actor_login: str (expected: str)
✓ repo_name: str (expected: str)
✓ repo_owner: str (expected: str)
✓ created_at: str (expected: str)
✓ event_date: str (expected: str)
✓ payload: dict (expected: dict)
✓ public: bool (expected: bool)
✓ loaded_at: str (expected: str)

ALL TYPES CORRECT ✓
BigQuery schema match: CONFIRMED
```

### 3. DAG Integrity (5/5 Passing)
```bash
python3 scripts/test_dag_integrity.py
```

---

## Deployment Steps

### Option 1: Copy to Airflow Container
```bash
# Copy updated DAG
cp ~/Repositories/github-activity-batch-pipeline/airflow/dags/github_activity_pipeline.py \
   ~/Repositories/github-activity-batch-pipeline/airflow/dags/

# Restart Airflow scheduler to pick up changes
cd ~/Repositories/github-activity-batch-pipeline
docker compose restart airflow-scheduler
```

### Option 2: Direct Container Copy
```bash
# Copy directly into container
docker cp ~/Repositories/github-activity-batch-pipeline/airflow/dags/github_activity_pipeline.py \
  $(docker ps -q -f name=airflow-scheduler):/opt/airflow/dags/github_activity_pipeline.py

# Restart scheduler
docker compose restart airflow-scheduler
```

### Trigger Test Run
1. Open Airflow UI: http://localhost:8080
2. Find `github_activity_batch_pipeline`
3. Click "Play" (or trigger existing run)
4. Use execution date: `2024-06-15` (good data availability)
5. Monitor all 6 tasks complete successfully

---

## Expected Results

All tasks should complete green:
- ✅ `download_github_archive`: 10-24 files downloaded
- ✅ `upload_to_gcs`: Files uploaded to `data/` prefix
- ✅ `validate_data_quality`: Validation passed
- ✅ `transform_data`: Schema conversion complete, uploaded to `transformed/`
- ✅ `load_to_bigquery`: **Data loaded without schema error**
- ✅ `cleanup_temp_files`: Temp files removed

### Verify in BigQuery
```sql
SELECT 
  event_date,
  COUNT(*) as event_count,
  COUNT(DISTINCT actor_login) as unique_users,
  COUNT(DISTINCT repo_name) as unique_repos
FROM `github-activity-batch-pipeline.github_activity.github_events`
WHERE event_date = '2024-06-15'
GROUP BY event_date;
```

---

## Files Modified

| File | Change |
|------|--------|
| `airflow/dags/github_activity_pipeline.py` | Added explicit type casting in transform task |
| `tests/test_pipeline_tasks.py` | Added regression test for type casting |
| `scripts/verify_transform_output.py` | New schema verification script |

**Commits:** 3 new commits
- `8854457` Add: Transform output schema verification script
- `664ecdb` Add: Regression test for event_id type casting
- `318f943` Fix: Explicitly cast event_id to STRING in transform task

---

## Lessons Learned

1. **JSON numeric fields**: GHE Archive `id` looks like a string but can be numeric in JSON
2. **BigQuery schema enforcement**: BigQuery strictly enforces types on `WRITE_APPEND`
3. **Defensive casting**: Always explicitly cast to expected types, don't rely on JSON parsing
4. **Test with realistic data**: Unit tests should use numeric IDs to catch this early

---

**Status:** ✅ Fixed, tested, ready for deployment
