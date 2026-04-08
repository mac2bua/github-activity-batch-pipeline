# Troubleshooting Guide

Common issues and solutions for the GitHub AI Contributions pipeline.

## Airflow Issues

### DAG Not Appearing in UI

**Symptoms**: DAG not visible in Airflow UI

**Causes**:
1. DAG file not in correct location
2. Python syntax errors
3. Missing dependencies
4. File permissions

**Solutions**:
```bash
# Check file location
ls -la airflow/dags/

# Check Python syntax
python3 -m py_compile airflow/dags/github_activity_pipeline.py

# Check Airflow logs
docker compose logs airflow-scheduler | grep -i github

# Restart scheduler
docker compose restart airflow-scheduler
```

### Task Failing: Download

**Symptoms**: `download_github_archive` task fails

**Causes**:
1. GHE Archive temporarily unavailable
2. Network timeout
3. Disk space full

**Solutions**:
```bash
# Check available disk space
df -h /tmp

# Clear temporary files
rm -rf /tmp/github_archive/*

# Retry task from Airflow UI

# Check GHE Archive status
curl -I https://gharchive.org/data/2024-01-01-00.json.gz
```

### Task Failing: Upload to GCS

**Symptoms**: `upload_to_gcs` task fails with authentication error

**Causes**:
1. Service account key not mounted
2. Wrong bucket name
3. Insufficient permissions

**Solutions**:
```bash
# Verify service account key path
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# Check bucket exists
gsutil ls gs://github-activity-batch-raw-<project_id>

# Verify permissions
gcloud projects get-iam-policy <project_id> \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:serviceAccount:<sa-email>"

# Restart worker with correct credentials
docker compose restart airflow-worker
```

### Task Failing: Load to BigQuery

**Symptoms**: `load_to_bigquery` task fails

**Causes**:
1. Schema mismatch
2. Invalid data format
3. Quota exceeded
4. Dataset doesn't exist

**Solutions**:
```bash
# Check table schema
bq show github_activity.github_events

# Check for bad records
bq query --use_legacy_sql=false \
  "SELECT * FROM github_activity.github_events LIMIT 10"

# Verify dataset exists
bq ls --dataset

# Check BigQuery quotas
# https://console.cloud.google.com/iam-admin/quotas

# Review task logs in Airflow UI for specific error
```

### DAG Stuck in "Running" State

**Symptoms**: DAG shows as running but no progress

**Causes**:
1. Worker not processing tasks
2. Database lock
3. Resource exhaustion

**Solutions**:
```bash
# Check worker status
docker compose ps

# Check worker logs
docker compose logs airflow-worker

# Restart all Airflow services
docker compose down
docker compose up -d

# Clear stuck task instances (last resort)
docker compose exec airflow-webserver \
  airflow tasks clear github_activity_batch_pipeline \
  --start-date 2024-01-01 --end-date 2024-01-01
```

## Terraform Issues

### Terraform Init Fails

**Symptoms**: `terraform init` fails

**Causes**:
1. Network connectivity
2. Provider version conflict
3. Corrupted .terraform directory

**Solutions**:
```bash
# Remove .terraform directory
rm -rf terraform/.terraform

# Re-initialize
cd terraform
terraform init

# Check network connectivity
curl -I https://registry.terraform.io
```

### Terraform Apply Fails: Permission Denied

**Symptoms**: `terraform apply` fails with 403 error

**Causes**:
1. Service account lacks permissions
2. Wrong project ID
3. Billing not enabled

**Solutions**:
```bash
# Verify active account
gcloud auth list

# Verify project
gcloud config get-value project

# Grant required permissions
gcloud projects add-iam-policy-binding <project_id> \
  --member="serviceAccount:<sa-email>" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding <project_id> \
  --member="serviceAccount:<sa-email>" \
  --role="roles/bigquery.admin"

# Check billing
gcloud beta billing projects describe <project_id>
```

### State File Locked

**Symptoms**: "Error acquiring the state lock"

**Solutions**:
```bash
# Force unlock (if safe)
terraform force-unlock <lock_id>

# Or remove local state lock
rm -rf terraform/.terraform/lock.hcl
```

## dbt Issues

### dbt Run Fails: Connection Error

**Symptoms**: `dbt run` fails with connection error

**Causes**:
1. profiles.yml not configured
2. Wrong credentials
3. Network issues

**Solutions**:
```bash
# Check profiles.yml location
ls -la ~/.dbt/profiles.yml

# Test BigQuery connection
bq query --use_legacy_sql=false "SELECT 1"

# Verify credentials in profiles.yml
cat ~/.dbt/profiles.yml

# Check service account has BigQuery access
gcloud projects get-iam-policy <project_id> \
  --filter="bindings.members:serviceAccount:<sa-email>"
```

### dbt Tests Failing

**Symptoms**: `dbt test` shows failures

**Causes**:
1. Data quality issues
2. Schema changes
3. Incorrect test definitions

**Solutions**:
```bash
# Run specific failing test
dbt test --select <model_name>

# View failing records
dbt run --select <model_name>
bq query "SELECT * FROM <dataset>.<model> WHERE <failing_condition>"

# Adjust test thresholds if needed
# Edit dbt/models/schema.yml
```

### Model Not Found

**Symptoms**: "Model 'X' not found"

**Solutions**:
```bash
# List available models
dbt ls

# Check model file exists
ls -la dbt/models/marts/

# Run dbt deps to ensure packages installed
dbt deps

# Clear target directory
rm -rf dbt/target
dbt deps
dbt run
```

## Docker Compose Issues

### Containers Won't Start

**Symptoms**: `docker compose up` fails

**Causes**:
1. Port already in use
2. Insufficient resources
3. Invalid compose file

**Solutions**:
```bash
# Check for port conflicts
lsof -i :8080
lsof -i :5432
lsof -i :6379

# Kill conflicting processes
kill -9 <pid>

# Check resources
docker stats

# Validate compose file
docker compose config

# Remove old containers
docker compose down -v
docker compose up -d
```

### Airflow Database Error

**Symptoms**: "Database not initialized"

**Solutions**:
```bash
# Re-run initialization
docker compose down
docker compose up airflow-init
docker compose up -d
```

## BigQuery Issues

### Query Costs Too High

**Symptoms**: BigQuery bills more than expected

**Causes**:
1. Not using partition filters
2. SELECT * queries
3. No clustering benefit

**Solutions**:
```sql
-- Always filter by partition
SELECT * FROM github_activity.github_events
WHERE event_date = '2024-01-01'  -- Partition filter

-- Select only needed columns
SELECT event_type, actor_login, created_at
FROM github_activity.github_events
WHERE event_date BETWEEN '2024-01-01' AND '2024-01-07'

-- Use clustering fields in WHERE
WHERE repo_name = 'owner/repo'
  AND actor_login = 'username'
```

### Table Not Partitioned

**Symptoms**: Queries scan entire table

**Solutions**:
```bash
# Check table configuration
bq show github_activity.github_events

# Recreate with partitioning (if needed)
# Edit terraform/main.tf and re-apply
terraform apply
```

## Looker Studio Issues

### Dashboard Shows No Data

**Symptoms**: Charts empty or error

**Causes**:
1. Wrong dataset selected
2. Date range has no data
3. Permissions issue

**Solutions**:
1. Check data source connection in Looker
2. Verify dataset name: `github_activity`
3. Expand date range to include available data
4. Check BigQuery access permissions

### Slow Dashboard Performance

**Symptoms**: Dashboard takes >10s to load

**Solutions**:
1. Add date filter (default: last 30 days)
2. Use aggregated tables (daily_stats, repo_health)
3. Avoid SELECT * in custom queries
4. Enable Looker caching

## Performance Issues

### Pipeline Running Slow

**Symptoms**: DAG takes >4 hours

**Solutions**:
```bash
# Check network speed
curl -o /dev/null -w "%{time_total}\n" \
  https://gharchive.org/data/2024-01-01-00.json.gz

# Increase Airflow parallelism
# Edit docker-compose.yml:
# AIRFLOW__CORE__PARALLELISM=64
# AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG=16

# Add more workers
docker compose up -d --scale airflow-worker=3
```

### BigQuery Queries Slow

**Solutions**:
```sql
-- Use partition pruning
WHERE event_date = CURRENT_DATE()

-- Use clustering fields
WHERE repo_name = '...' AND event_type = '...'

-- Avoid full table scans
-- Check bytes processed in query plan
```

## Common Error Messages

### "Bootstrap token invalid or expired"

**Fix**: Regenerate Airflow Fernet key
```bash
# Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Update docker-compose.yml AIRFLOW__CORE__FERNET_KEY
docker compose restart
```

### "Bucket not found"

**Fix**: Verify bucket name matches Terraform output
```bash
terraform output bucket_name
# Update GCS_BUCKET in Airflow DAG
```

### "Permission denied: gs://..."

**Fix**: Grant Storage Admin role to service account
```bash
gcloud projects add-iam-policy-binding <project_id> \
  --member="serviceAccount:<sa-email>" \
  --role="roles/storage.admin"
```

## DAG Operations

### Trigger DAG for a Specific Date

Run the pipeline for a specific date (useful for backfilling):

```bash
# Trigger for a single date
# Note: The DAG processes execution_date - 1 day (GH Archive delay)
# Example: --exec-date 2026-04-08 will process April 7 data
docker compose exec airflow-scheduler \
  airflow dags trigger github_activity_batch_pipeline --exec-date 2026-04-08

# Trigger for multiple dates (backfill)
for date in 2026-04-04 2026-04-05 2026-04-06; do
  docker compose exec airflow-scheduler \
    airflow dags trigger github_activity_batch_pipeline --exec-date $date
done
```

**Important**: The DAG is scheduled at 12:00 UTC and processes the **previous day's** data.
This is because GH Archive has a ~6-12 hour delay before data is available.

| Run Time | execution_date | Processes |
|----------|---------------|-----------|
| April 8, 12:00 UTC | April 8 | April 7 data |
| April 9, 12:00 UTC | April 9 | April 8 data |

### Check DAG Run Status

View recent runs and their states:

```bash
# List recent runs
docker compose exec airflow-scheduler \
  airflow dags list-runs -d github_activity_batch_pipeline | head -10

# Check specific run tasks
docker compose exec airflow-scheduler \
  airflow tasks states-for-dag-run github_activity_batch_pipeline 'scheduled__2026-04-07T00:00:00+00:00'
```

### Clear Failed Tasks

Retry a failed DAG run:

```bash
# Clear all tasks for a specific date
docker compose exec airflow-scheduler \
  airflow tasks clear github_activity_batch_pipeline -s 2026-04-07 -e 2026-04-07 -y

# Clear tasks for a date range
docker compose exec airflow-scheduler \
  airflow tasks clear github_activity_batch_pipeline -s 2026-04-01 -e 2026-04-07 -y
```

### Enable Automatic Backfill (Catchup)

By default, catchup is disabled. To enable automatic backfill for missing dates:

1. Edit `airflow/dags/github_activity_pipeline.py`:
   ```python
   'catchup': True,  # Change from False to True
   ```

2. Restart the scheduler:
   ```bash
   docker compose restart airflow-scheduler
   ```

The DAG will automatically schedule all missing runs from `start_date` to now.

### Handle Missing Data Dates

If a date has no data in BigQuery (e.g., GH Archive delay):

1. **Check if data exists on GH Archive**:
   ```bash
   curl -sI "https://data.gharchive.org/2026-04-04-12.json.gz" | head -1
   # HTTP/2 200 = data exists
   # HTTP/2 404 = data not available
   ```

2. **Re-run the DAG for that date**:
   ```bash
   docker compose exec airflow-scheduler \
     airflow dags trigger github_activity_batch_pipeline --exec-date 2026-04-04
   ```

3. **Verify data loaded**:
   ```bash
   bq query --use_legacy_sql=false \
     "SELECT COUNT(*) FROM github_activity.github_events WHERE event_date = '2026-04-04'"
   ```

### Handle Duplicate Data

If the same date was loaded twice (duplicate records):

1. **Delete duplicates from BigQuery**:
   ```bash
   bq query --use_legacy_sql=false \
     "DELETE FROM github_activity.github_events WHERE event_date = '2026-04-05'"
   ```

2. **Re-run DAG once**:
   ```bash
   docker compose exec airflow-scheduler \
     airflow dags trigger github_activity_batch_pipeline --exec-date 2026-04-05
   ```

3. **Verify count is correct**:
   ```bash
   bq query --use_legacy_sql=false \
     "SELECT event_date, COUNT(*) as events FROM github_activity.github_events
      WHERE event_date >= '2026-04-01' GROUP BY event_date ORDER BY event_date"
   ```

### Query Data by Date

Check data counts per day:

```bash
bq query --use_legacy_sql=false \
  "SELECT event_date, COUNT(*) as events
   FROM github_activity.github_events
   GROUP BY event_date ORDER BY event_date"
```

### Worker Volume Mount Issues

If tasks fail with `FileNotFoundError` for log directories:

```bash
# Check worker sees logs directory
docker compose exec airflow-worker ls -la /opt/airflow/logs

# If empty, restart worker to pick up volume mount
docker compose restart airflow-worker

# Then clear and retry failed tasks
docker compose exec airflow-scheduler \
  airflow tasks clear github_activity_batch_pipeline -s 2026-04-07 -e 2026-04-07 -y
```

## Getting Help

If issues persist:

1. **Check logs**: `docker compose logs -f`
2. **Review documentation**: README.md, CLAUDE.md
3. **Search issues**: GitHub Issues
4. **Contact team**: See CHECKLIST.md for contacts

---

**Last Updated**: 2026-04-08
