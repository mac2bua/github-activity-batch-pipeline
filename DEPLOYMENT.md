# Deployment Guide - GitHub Activity Batch Pipeline

## Quick Deploy

```bash
# 1. Copy DAG file to Airflow
cp airflow/dags/github_activity_pipeline.py <AIRFLOW_HOME>/dags/

# 2. Restart Airflow scheduler
docker compose restart airflow-scheduler airflow-webserver

# 3. Trigger DAG run in Airflow UI
# Go to http://localhost:8080, find github_activity_batch_pipeline, click "Play"
```

## Pre-Deployment Checklist

### ✅ Tests Passing
```bash
# Run unit tests
python3 -m pytest tests/test_pipeline_tasks.py -v

# Run DAG integrity tests
python3 scripts/test_dag_integrity.py

# Or run all tests
make -f Makefile.test test
```

Expected output:
- 8/8 unit tests passing
- 5/5 DAG integrity tests passing

### ✅ Code Quality
```bash
# Check Python syntax
python3 -m py_compile airflow/dags/github_activity_pipeline.py
```

### ✅ Git Status
```bash
git log --oneline -5
git status  # Should be clean
```

## Architecture

### Task Flow (6 tasks)
```
download_github_archive
    ↓
upload_to_gcs
    ↓
validate_data_quality
    ↓
transform_data          ← NEW: Converts GHE Archive format to BigQuery schema
    ↓
load_to_bigquery
    ↓
cleanup_temp_files
```

### Data Flow
1. **Download**: Fetches hourly `.json.gz` files from `data.gharchive.org`
2. **Upload**: Stores raw files in GCS under `data/` prefix
3. **Validate**: Checks files exist and have valid sizes
4. **Transform**: Converts nested GHE format → flat BigQuery schema
   - Extracts `actor_login` from `actor.login`
   - Extracts `repo_name`, `repo_owner` from `repo.name`
   - Parses `event_date` from `created_at`
   - Adds `loaded_at` timestamp
   - Outputs to `transformed/` prefix
5. **Load**: Loads transformed data into BigQuery table
6. **Cleanup**: Removes local temp files

### BigQuery Schema
| Field | Type | Mode | Source |
|-------|------|------|--------|
| event_id | STRING | REQUIRED | `id` |
| event_type | STRING | REQUIRED | `type` |
| actor_login | STRING | REQUIRED | `actor.login` |
| repo_name | STRING | REQUIRED | `repo.name` |
| repo_owner | STRING | REQUIRED | extracted from `repo.name` |
| created_at | TIMESTAMP | REQUIRED | `created_at` |
| event_date | DATE | REQUIRED | extracted from `created_at` |
| payload | JSON | NULLABLE | `payload` |
| public | BOOLEAN | REQUIRED | `public` |
| loaded_at | TIMESTAMP | REQUIRED | current timestamp |

### Partitioning & Clustering
- **Partitioned by**: `event_date` (DAY)
- **Clustered by**: `repo_name`, `actor_login`, `event_type`
- **Expiration**: 90 days

## Testing in Airflow

### Recommended Test Dates
- `2024-06-15`: Good data availability
- `2023-01-01`: Full year data
- `2011-02-20`: Historical data

### How to Trigger
1. Open Airflow UI (http://localhost:8080)
2. Find `github_activity_batch_pipeline` DAG
3. Click the "Play" button
4. Select execution date (e.g., 2024-06-15)
5. Click "Trigger"

### Monitor Progress
- Watch task colors: queued (grey) → running (green) → success (dark green)
- Click individual tasks to view logs
- Expected runtime: 5-15 minutes depending on data volume

## Troubleshooting

### Task Fails with 404 Errors
**Normal behavior** - GHE Archive doesn't have all hours for all dates. Task succeeds if ≥1 file downloads.

### No Data for Date
Try a different execution date. Some recent dates may have no data yet.

### Schema Mismatch Error
Ensure `transform_data` task runs before `load_to_bigquery`. The transform step is critical.

### GCS Permission Errors
Verify service account has Storage Admin role:
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<SERVICE_ACCOUNT>@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

### BigQuery Permission Errors
Verify service account has BigQuery Admin role:
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<SERVICE_ACCOUNT>@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"
```

## Cost Monitoring

### Budget Alert
- Set at €2 (configured in Terraform)
- Monitor in GCP Console → Billing → Budgets

### Expected Costs (Test Data)
- 1 day of data: <€0.01
- 1 week of data: <€0.10
- 1 month of data: <€0.50

### Cost Optimization
- Test with single day first
- Use partition filtering in queries
- Data expires after 90 days (auto-delete)

## Next Steps After Deployment

1. ✅ Verify DAG runs successfully end-to-end
2. Create Looker Studio dashboard (see `looker/` folder)
3. Run dbt models (see `dbt/` folder)
4. Set up production schedule (daily at midnight)
5. Configure email alerts for failures

## Support

See `BUGFIX_SUMMARY.md` for recent fixes and `TROUBLESHOOTING.md` for common issues.
