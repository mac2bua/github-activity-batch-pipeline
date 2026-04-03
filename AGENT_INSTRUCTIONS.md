# Agent Instructions: BATCH Pipeline End-to-End Validation

**You are an autonomous agent with unlimited runtime.** Your goal is to make the Airflow DAG run successfully end-to-end with REAL data.

---

## Mission

Fix and validate the GitHub Activity Batch Pipeline until ALL 6 tasks complete successfully in Airflow **with actual GCS and BigQuery**.

**Repository:** `~/Repositories/github-activity-batch-pipeline/`

**Airflow:** http://localhost:8080 (admin/admin)

**Test Date:** `2024-06-15` (good data availability)

---

## Task Flow (6 Tasks)

```
download_github_archive → upload_to_gcs → validate_data_quality → transform_data → load_to_bigquery → cleanup_temp_files
```

---

## Your Loop (REAL DAG, NO SHORTCUTS)

```
while DAG_NOT_SUCCESSFUL:
    1. Copy updated DAG to Airflow:
       docker cp airflow/dags/github_activity_pipeline.py \
         $(docker ps -q -f name=airflow-scheduler):/opt/airflow/dags/
    
    2. Restart Airflow scheduler:
       docker compose restart airflow-scheduler
    
    3. Trigger DAG run:
       curl -X POST http://localhost:8080/api/v1/dags/github_activity_batch_pipeline/dagRuns \
         -u admin:admin \
         -H "Content-Type: application/json" \
         -d '{"execution_date": "2024-06-15T00:00:00+00:00"}'
    
    4. Monitor task execution (poll every 30s):
       - Watch all 6 tasks
       - Wait for completion (may take 10-20 minutes)
    
    5. If ANY task fails:
       a. Read FULL error log from Airflow API
       b. Identify root cause (not just symptom)
       c. Implement fix in github_activity_pipeline.py
       d. Create/update unit test that would have caught this
       e. Run pytest to verify fix doesn't break existing tests
       f. Go to step 1 (re-run full DAG)
    
    6. If ALL tasks succeed:
       a. Verify data in BigQuery (row counts, schema, types)
       b. Run DAG again with different date (e.g., 2024-01-01)
       c. Verify second run also succeeds
    
    7. Log progress to ~/clawd/memory/agent-debugger-status.md
    
    8. Continue loop until:
       - 2+ consecutive DAG runs succeed
       - BigQuery data verified correct
       - All tests passing
```

**NO SHORTCUTS.** Every iteration runs the REAL DAG with REAL GCS and BigQuery.

---

## Tools Available

- **Ollama models only** (ollama/qwen3.5:cloud)
- Airflow REST API (http://localhost:8080/api/v1/...)
- Docker Compose (copy files, restart services)
- pytest (run unit tests AFTER fixing)
- gcloud (query BigQuery for verification)
- curl (trigger DAGs, fetch logs)
- Standard shell tools

---

## Known Fixes (Already Applied)

1. ✅ `validate_data_quality`: Use `hook.get_blob()` for metadata
2. ✅ `transform_data`: Use `filename` parameter (not `file_data`)
3. ✅ `transform_data`: Cast `event_id` to `str()` explicitly
4. ✅ Added `transform_data` task to convert GHE schema → BigQuery schema

**Your job:** Verify these fixes work with REAL Airflow + GCS + BigQuery. There may be NEW bugs that only appear in production.

---

## Common Production Issues to Watch For

1. **GCS authentication** - Service account permissions in container
2. **BigQuery schema drift** - Table exists but schema changed
3. **File path mismatches** - Local vs container paths
4. **Timeout issues** - Large files, slow network
5. **Data format edge cases** - Null values, unexpected types in GHE data
6. **Partition/clustering conflicts** - WRITE_APPEND with incompatible schema

---

## Exit Condition

**You succeed when:**
- ✅ 2+ consecutive DAG runs complete with status "success"
- ✅ All 6 tasks show green in Airflow UI
- ✅ BigQuery data verified:
  - Row count matches GCS files
  - Schema matches terraform/bigquery.tf
  - event_id is STRING (not INTEGER)
  - All REQUIRED fields populated
- ✅ Unit tests updated and passing
- ✅ Status file updated to "COMPLETE"

**Then:** Notify main session.

---

## Rules

1. **NO MOCKS for main validation** - Always run real DAG
2. **Don't give up** - Run in infinite loop until success
3. **Test thoroughly** - Create tests for every bug found
4. **Use Ollama only** - No Anthropic/OpenAI models
5. **Log progress** - Update status file every iteration
6. **Be thorough** - Fix ALL errors, run multiple dates
7. **Don't notify user** - Only notify when COMPLETE

---

## Status File Format

Write to `~/clawd/memory/agent-debugger-status.md`:

```markdown
# Debugger Agent Status

**Iteration:** 5

**Current Status:** Fixing load_to_bigquery task

**DAG Run ID:** manual__2026-04-04T01-00-00

**Task Results:**
- download_github_archive: ✅ success (15 files)
- upload_to_gcs: ✅ success
- validate_data_quality: ✅ success
- transform_data: ✅ success
- load_to_bigquery: ❌ failed
- cleanup_temp_files: skipped

**Error:**
Field event_id has changed type from STRING to INTEGER

**Root Cause:**
GHE Archive id field is numeric, needs explicit str() casting

**Fix Applied:**
Added str() around event.get('id', '') in transform_ghe_to_schema()

**Tests Updated:**
Added test_transform_event_id_type_casting

**Next Action:** Restarting Airflow, re-triggering DAG

**Progress:** 5/6 tasks passing, 1 failing
```

---

## Start Now

1. Copy DAG to Airflow container
2. Restart scheduler
3. Trigger DAG
4. Begin the loop

Good luck! 🚀
