# E2E Test Guide - GitHub Activity Batch Pipeline

This guide walks you through running the complete end-to-end pipeline from infrastructure setup to data visualization.

## Prerequisites

Before starting, ensure you have:

1. **GCP Project** with billing enabled
2. **Service Account Key** at `keys/gcp-creds.json` with these roles:
   - BigQuery Admin
   - Storage Admin
   - Service Account User
3. **Docker** and **Docker Compose** installed
4. **Terraform** installed (for infrastructure)
5. **dbt** installed (for transformations)

## Quick Start

```bash
# 1. Validate environment (recommended)
./scripts/validate_environment.sh

# 2. Quick local validation (no GCP needed)
./scripts/quick_validate.sh
```

## Step-by-Step E2E Test

### Step 1: Configure Environment

Create `.env` file in project root:

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/keys/gcp-creds.json

# Airflow Configuration
AIRFLOW_UID=50000
AIRFLOW__CORE__FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

**Important**: Use absolute paths for credentials.

### Step 2: Deploy Infrastructure

```bash
# Initialize Terraform
make terraform-init

# Apply infrastructure (creates GCS bucket, BigQuery dataset, table)
make terraform-apply PROJECT_ID=your-project-id
```

Expected output:
- GCS bucket: `github-activity-batch-raw-{project-id}`
- BigQuery dataset: `github_activity`
- BigQuery table: `github_events` (partitioned, clustered)

### Step 3: Start Airflow

```bash
# Start Airflow stack
make airflow-up

# Wait ~60 seconds for Airflow to initialize
# Check logs if needed
make airflow-logs
```

Access Airflow UI: http://localhost:8080
- Username: `admin`
- Password: `admin`

### Step 4: Trigger Pipeline

1. In Airflow UI, find the DAG `github_activity_pipeline`
2. Toggle the DAG to "On"
3. Click "Trigger DAG" (play button)
4. Set `execution_date` to a past date with data (e.g., `2024-06-15`)

**Expected Duration**: 3-5 minutes (TEST MODE downloads only 1 hour)

### Step 5: Monitor Pipeline

Watch these tasks complete:
1. `download_github_archive` - Downloads hourly file
2. `upload_to_gcs` - Uploads to GCS
3. `validate_data_quality` - Validates JSON structure
4. `transform_data` - Transforms for BigQuery
5. `load_to_bigquery` - Loads to BigQuery
6. `cleanup_temp_files` - Removes temporary files

All tasks should show green checkmarks.

### Step 6: Run dbt Transformations

```bash
cd dbt

# Install dependencies (including dbt_utils)
dbt deps

# Run transformations
dbt run

# Run tests (23 tests)
dbt test

# Generate docs (optional)
dbt docs generate
```

Expected test results: All 23 tests pass

### Step 7: Verify Data

```bash
# Check event count
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) as event_count FROM github_activity.github_events WHERE event_date='2024-06-15'"

# Expected: 50,000+ events (varies by hour)
```

### Step 8: Second Run (Reproducibility)

To confirm reproducibility, run the pipeline again:

1. In Airflow UI, clear the DAG run
2. Trigger again with same or different date
3. Verify all tasks complete successfully
4. Re-run `dbt run && dbt test`

## Troubleshooting

### DAG Not Appearing

```bash
# Restart scheduler
docker compose restart airflow-scheduler

# Check for import errors
docker compose exec airflow-scheduler airflow dags list
```

### Authentication Errors

1. Verify `GOOGLE_APPLICATION_CREDENTIALS` path in `.env` is absolute
2. Check service account has required permissions
3. Ensure billing is enabled on GCP project

### BigQuery Schema Errors

The table is pre-created by Terraform. Use `autodetect=False` in operators.

### No Data in Dashboard

1. Check date range has data in GitHub Archive
2. Verify partition filter in queries
3. Check Airflow logs for download errors

### dbt Tests Fail

```bash
# Check dbt_utils is installed
cd dbt && dbt deps

# Verify source connection
dbt debug
```

## TEST MODE Details

The pipeline runs in **TEST MODE** by default:

- **Downloads**: Only 1 hourly file (hour 12)
- **Runtime**: ~3-5 minutes instead of ~30 minutes
- **Purpose**: Fast iteration during development

To switch to **PRODUCTION MODE**:

Edit `airflow/dags/github_activity_pipeline.py`:

```python
# Change this line:
test_hours = [12]

# To this:
test_hours = range(24)  # All 24 hours
```

## Cleanup

```bash
# Stop Airflow
make airflow-down

# Destroy infrastructure (removes all GCP resources)
make terraform-destroy PROJECT_ID=your-project-id
```

## Success Criteria

A successful E2E test shows:

1. ✅ All Python tests pass (`pytest tests/ -v`)
2. ✅ Terraform applies without errors
3. ✅ Airflow DAG completes all 6 tasks
4. ✅ BigQuery table has 50,000+ events
5. ✅ dbt run succeeds
6. ✅ All 23 dbt tests pass
7. ✅ Second run produces same results

## Next Steps

After successful E2E testing:

1. **Looker Studio Dashboard**: Connect to BigQuery dataset
2. **Production Mode**: Enable all 24 hours
3. **Schedule**: Set up daily automated runs
4. **Monitoring**: Configure alerts for pipeline failures

---

**Note**: This pipeline was developed for DE Zoomcamp 2026 final project (28/28 points).