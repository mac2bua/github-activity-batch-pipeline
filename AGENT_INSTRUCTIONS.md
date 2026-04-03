# Agent Instructions: BATCH Pipeline End-to-End Validation

**You are an autonomous agent with unlimited runtime.** Your goal is to make the Airflow DAG run successfully end-to-end.

---

## Mission

Fix and validate the GitHub Activity Batch Pipeline until ALL 6 tasks complete successfully in Airflow.

**Repository:** `~/Repositories/github-activity-batch-pipeline/`

**Airflow:** http://localhost:8080 (admin/admin)

**Test Date:** `2024-06-15` (good data availability)

---

## Task Flow (6 Tasks)

```
download_github_archive → upload_to_gcs → validate_data_quality → transform_data → load_to_bigquery → cleanup_temp_files
```

---

## Your Loop (Optimized for Speed)

```
while DAG_NOT_SUCCESSFUL:
    # FAST LOOP (30 seconds per iteration)
    1. Run fast validation: python3 scripts/fast_validate.py 2024-06-15
       - Downloads 1 hour of GHE data (~60MB, 30s)
       - Tests transform logic on 100 events
       - Validates schema types (catches event_id INTEGER bug)
    
    2. If fast validation fails:
       a. Read error (schema type mismatch, etc.)
       b. Fix transform_ghe_to_schema() in github_activity_pipeline.py
       c. Run unit tests: pytest tests/test_pipeline_tasks.py -v (5s)
       d. Repeat fast validation
       e. Continue loop
    
    3. If fast validation passes (10+ iterations):
       # SLOW VALIDATION (5-15 minutes, only when confident)
       a. Copy DAG to Airflow: docker cp ... or cp to dags folder
       b. Restart scheduler: docker compose restart airflow-scheduler
       c. Trigger full DAG run
       d. Monitor all 6 tasks
       e. If ANY task fails: go back to step 1
    
    4. Log progress to memory/agent-debugger-status.md
    5. Continue loop
```

**Key optimization:** Fast validation catches 90% of bugs in 30s. Only run full DAG when confident.

---

## Tools Available

- **Ollama models only** (ollama/qwen3.5:cloud)
- **Fast validation** (30s): `python3 scripts/fast_validate.py 2024-06-15`
- **Unit tests** (5s): `pytest tests/test_pipeline_tasks.py -v`
- Airflow REST API (http://localhost:8080/api/v1/...)
- Docker Compose (restart services)
- gcloud (query BigQuery if needed)
- Standard shell tools

**Speed:** Fast loop = 30s iterations. Full DAG = only when confident.

---

## Known Fixes (Already Applied)

1. ✅ `validate_data_quality`: Use `hook.get_blob()` for metadata
2. ✅ `transform_data`: Use `filename` parameter (not `file_data`)
3. ✅ `transform_data`: Cast `event_id` to `str()` explicitly
4. ✅ Added `transform_data` task to convert GHE schema → BigQuery schema

**Your job:** Verify these fixes work in actual Airflow run. There may be NEW bugs.

---

## Exit Condition

**You succeed when:**
- DAG run completes with status "success"
- All 6 tasks show green in Airflow UI
- You have verified data in BigQuery

**Then:** Write status to `memory/agent-debugger-status.md` with "COMPLETE" and notify main session.

---

## Rules

1. **Don't give up** - Run in infinite loop until success
2. **Test thoroughly** - Create tests for every fix
3. **Use Ollama only** - No Anthropic/OpenAI models
4. **Log progress** - Update status file every iteration
5. **Be thorough** - Fix ALL errors, not just the current one
6. **Don't notify user** - Only notify when COMPLETE

---

## Status File Format

Write to `~/clawd/memory/agent-debugger-status.md`:

```markdown
# Debugger Agent Status

**Started:** 2026-04-04 01:40

**Iteration:** 5

**Current Status:** Fixing load_to_bigquery task

**Errors Found:**
1. validate_data_quality: 'str' object has no attribute 'size' - FIXED
2. transform_data: upload() wrong parameter - FIXED
3. load_to_bigquery: event_id type mismatch - FIXED
4. [current error]

**Next Action:** Restarting Airflow and re-triggering DAG

**Progress:** 4/6 tasks passing
```

---

## Start Now

1. Copy your code to Airflow DAGs folder
2. Restart Airflow scheduler
3. Trigger DAG
4. Begin the loop

Good luck! 🚀
