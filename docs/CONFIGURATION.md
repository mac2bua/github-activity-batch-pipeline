# Configuration Guide

This document explains how to configure the GitHub Activity Batch Pipeline.

## Required Configuration

### 1. GCP Project ID

The pipeline needs your GCP project ID to create bucket names and BigQuery table references.

**Option A: Airflow Variable (Recommended)**

1. In Airflow UI, go to **Admin → Variables**
2. Click **+** to add a new variable
3. Set:
   - **Key**: `project_id`
   - **Value**: Your GCP project ID (e.g., `my-gcp-project-123`)

**Option B: Environment Variable**

Set `GOOGLE_CLOUD_PROJECT` in your `.env` file:

```bash
GOOGLE_CLOUD_PROJECT=my-gcp-project-123
```

**Important**: The pipeline will **fail immediately** if project_id is not configured. This is intentional - we fail fast with a clear error rather than silently using a placeholder value.

### 2. GCP Credentials

The service account key must be mounted in the Airflow container:

```bash
# In .env file
GOOGLE_APPLICATION_CREDENTIALS=/files/keys/gcp-creds.json
```

In `docker-compose.yml`, ensure the keys directory is mounted:

```yaml
volumes:
  - ./keys:/files/keys
```

## How Configuration Works

### Project ID Resolution

The `get_project_id()` function resolves project ID in this order:

1. **Airflow Variable** `project_id` (highest priority)
2. **Environment variable** `GOOGLE_CLOUD_PROJECT`
3. **Error** if neither is configured

Placeholder values like `your-project-id` or `your-gcp-project-id` are explicitly rejected.

### Bucket Name

The GCS bucket name is constructed as:
```
github-activity-batch-raw-{PROJECT_ID}
```

Example: `github-activity-batch-raw-my-gcp-project-123`

This bucket should be created via Terraform:

```bash
cd terraform
terraform apply -var="project_id=my-gcp-project-123"
```

### BigQuery Table Reference

The destination table is:
```
{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}
```

Which resolves to:
```
my-gcp-project-123.github_activity.github_events
```

## Common Errors

### "project_id not configured"

**Error**: `ValueError: project_id not configured. Set Airflow Variable 'project_id' or environment variable 'GOOGLE_CLOUD_PROJECT'.`

**Cause**: Neither Airflow Variable nor environment variable is set.

**Fix**: 
- Set Airflow Variable `project_id` in the UI, OR
- Add `GOOGLE_CLOUD_PROJECT=your-project` to `.env` and restart Airflow

### "Dataset not found: your-project-id:github_activity"

**Error**: `google.api_core.exceptions.NotFound: Not found: Dataset your-project-id:github_activity`

**Cause**: Old bug where placeholder value was used silently. Fixed in commit `cd7d8d7`.

**Fix**: Update to latest code and configure project_id properly (see above).

### "Bucket not found"

**Error**: `NotFound: 404 GET https://storage.googleapis.com/...`

**Cause**: Terraform hasn't been run to create the bucket.

**Fix**:
```bash
cd terraform
terraform apply -var="project_id=your-project-id"
```

## Verification

After configuration, verify in Airflow UI:

1. Go to **Admin → Variables** - confirm `project_id` exists
2. Trigger the DAG manually
3. Check the first task logs - should show correct project ID
4. Verify bucket name in logs matches: `github-activity-batch-raw-{your-project-id}`

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Yes* | GCP project ID (if not using Airflow Variable) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to service account key |
| `AIRFLOW_UID` | Yes | User ID for Airflow containers |
| `AIRFLOW__CORE__FERNET_KEY` | Yes | Encryption key for Airflow |

*Required if `project_id` Airflow Variable is not set.
