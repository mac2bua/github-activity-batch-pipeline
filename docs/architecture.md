# Architecture Documentation

## Data Flow

```
GitHub Archive → Airflow DAG → GCS → BigQuery → dbt → Looker Studio
```

## Components

### 1. Terraform Infrastructure
- GCS bucket with 90-day lifecycle
- BigQuery dataset with partitioned/clustered table
- Service account with least-privilege IAM

### 2. Airflow DAG (3 Tasks)
1. **download_github_archive** - Fetch 24 hourly files from gharchive.org
2. **upload_to_gcs** - Upload compressed files to Cloud Storage
3. **load_to_bigquery** - MERGE data with deduplication

### 3. dbt Models
- **staging:** `stg_github_events` - Clean and standardize
- **mart 1:** `daily_stats` - Daily aggregations
- **mart 2:** `repo_health` - Repository health scores

### 4. Looker Studio
- Tile 1: Categorical pie chart (event types)
- Tile 2: Temporal line chart (trends)

## BigQuery Schema

**Partition:** `date_partition` (DAY)  
**Cluster:** `type`, `actor_login`, `repo_name`  
**Retention:** 90 days
