# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GitHub Activity Batch Pipeline                   │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  GHE Archive │────▶│   Airflow    │────▶│     GCS      │
│  (Source)    │     │ (Orchestrate)│     │   (Storage)  │
│              │     │              │     │              │
│ • JSON.gz    │     │ • Download   │     │ • Raw files  │
│ • Hourly     │     │ • Upload     │     │ • 90-day TTL │
│ • Public     │     │ • Validate   │     │ • Versioned  │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            │                    │
                            ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐
                     │    BigQuery  │◀────│     Load     │
                     │  (Warehouse) │     │  (Transfer)  │
                     │              │     │              │
                     │ • Partitioned│     │ • Schema     │
                     │ • Clustered  │     │ • Validation │
                     │ • 90-day     │     │ • Transform  │
                     └──────────────┘     └──────────────┘
                            │
                            │
                            ▼
                     ┌──────────────┐     ┌──────────────┐
                     │     dbt      │────▶│    Looker    │
                     │   (Transform)│     │   (Visualize)│
                     │              │     │              │
                     │ • Staging    │     │ • Categorical│
                     │ • Marts      │     │ • Temporal   │
                     │ • Tests      │     │ • Dashboards │
                     └──────────────┘     └──────────────┘
```

## Component Details

### 1. Data Source: GHE Archive

**What**: GitHub Public Events Archive (gharchive.org)
**Format**: Newline-delimited JSON, gzipped
**Frequency**: Hourly files, ~10-50MB each
**Schema**:
```json
{
  "id": "event_id",
  "type": "PushEvent|PullRequestEvent|...",
  "actor": {"login": "username", ...},
  "repo": {"name": "owner/repo", ...},
  "payload": {...},
  "public": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 2. Orchestration: Apache Airflow

**Role**: Schedule, execute, and monitor batch jobs

**DAG Structure**:
```
download_github_archive (PythonOperator)
    ↓
upload_to_gcs (PythonOperator)
    ↓
validate_data_quality (PythonOperator)
    ↓
load_to_bigquery (GCSToBigQueryOperator)
    ↓
cleanup_temp_files (BashOperator)
```

**Key Features**:
- Daily schedule (@daily)
- Catchup enabled for backfill
- Retry logic (2 retries, 5min delay)
- Email alerts on failure
- Max 1 concurrent run

### 3. Storage: Google Cloud Storage

**Purpose**: Temporary storage for raw data before BigQuery load

**Configuration**:
- Location: europe-west1
- Versioning: Enabled (90-day retention)
- Lifecycle: Delete objects > 90 days
- Access: Private (service account only)

**Path Structure**:
```
gs://github-activity-batch-raw-{project_id}/
└── raw/
    └── YYYY-MM-DD/
        ├── 2024-01-01-00.json.gz
        ├── 2024-01-01-01.json.gz
        └── ...
```

### 4. Data Warehouse: BigQuery

**Purpose**: Queryable storage for analytics

**Table**: `github_activity.github_events`

**Partitioning**:
- Field: `event_date` (DATE)
- Type: DAY
- Expiration: 90 days

**Clustering**:
- `repo_name`
- `actor_login`
- `event_type`

**Benefits**:
- Partition pruning reduces query costs
- Clustering improves filter performance
- Automatic schema evolution

### 5. Transformation: dbt

**Role**: Transform raw data into analytics-ready tables

**Model Hierarchy**:
```
Source: github_events (raw)
    ↓
Staging: stg_github_events (view)
    ├─ Clean and normalize
    ├─ Add data quality flags
    └─ Extract derived fields
    ↓
Marts:
    ├─ daily_stats (table, partitioned)
    │   ├─ Aggregated daily metrics
    │   ├─ Event type breakdowns
    │   └─ Time-based analysis
    └─ repo_health (table, partitioned)
        ├─ Repository activity scores
        ├─ Health classifications
        └─ Trend analysis
```

**Testing**:
- Uniqueness tests on IDs
- Not-null tests on required fields
- Accepted values for enums
- Range tests for metrics

### 6. Visualization: Looker Studio

**Dashboard Tiles**:

**Tile 1: Categorical Analysis**
- Event type distribution (pie)
- Top repositories (bar)
- Top contributors (table)

**Tile 2: Temporal Analysis**
- Daily activity trend (line)
- Hourly heatmap (pivot)
- Weekday vs weekend (scorecard)
- Health trend (area)

**Data Sources**:
- Primary: `daily_stats`
- Secondary: `repo_health`

## Data Flow

### Batch Processing (Daily)

1. **T-1 00:00 UTC**: Airflow DAG triggered
2. **00:00-00:30**: Download 24 hourly files from GHE Archive
3. **00:30-01:00**: Upload to GCS
4. **01:00-01:15**: Validate data quality
5. **01:15-02:00**: Load to BigQuery (partition T-1)
6. **02:00-02:15**: Cleanup temporary files
7. **02:15+**: dbt models refresh (on-demand or scheduled)

### Query Flow (User)

1. User opens Looker Studio dashboard
2. Looker queries `daily_stats` and `repo_health`
3. BigQuery uses partition pruning (date filter)
4. Results returned in < 5 seconds
5. Dashboard displays updated metrics

## Infrastructure Costs (Estimated)

**GCS Storage**:
- ~500MB/day × 90 days = 45GB
- Cost: ~$1/month

**BigQuery**:
- Storage: 45GB × 90 days = ~$1/month
- Queries: Depends on usage, ~$5-20/month for dashboards

**Airflow (Cloud Composer alternative)**:
- Self-hosted (Docker): Free (compute costs only)
- Cloud Composer: ~$400/month (not used here)

**Total**: ~$10-30/month for moderate usage

## Scalability

**Current Design**:
- Handles ~500MB/day comfortably
- Single DAG run per day
- BigQuery auto-scales queries

**Scaling Options**:
- Increase Airflow workers for parallel downloads
- Use BigQuery slots for heavy queries
- Add caching layer for Looker (optional)

## Failure Modes

| Failure Point | Impact | Mitigation |
|--------------|--------|------------|
| GHE Archive down | No new data | Retry logic, manual backfill |
| GCS upload fails | Data stuck locally | Retry, alert on failure |
| BigQuery load fails | No new data in BQ | Retry, check schema |
| dbt run fails | Stale metrics | Alert, manual run |
| Looker slow | Poor UX | Add partition filters |

## Monitoring

**Airflow**:
- DAG success/failure rate
- Task duration trends
- Retry frequency

**BigQuery**:
- Data freshness (MAX(loaded_at))
- Query costs
- Slot utilization

**dbt**:
- Test failure rate
- Model run duration
- Data quality trends

## Security Boundaries

```
┌─────────────────────────────────────┐
│         VPC / Private Network       │
│                                     │
│  ┌─────────┐    ┌─────────┐        │
│  │ Airflow │───▶│   GCS   │        │
│  └─────────┘    └─────────┘        │
│       │              │              │
│       ▼              ▼              │
│  ┌─────────────────────┐           │
│  │     BigQuery        │           │
│  │   (Google-managed)  │           │
│  └─────────────────────┘           │
│                                     │
└─────────────────────────────────────┘
         ▲
         │ (authenticated)
         │
┌─────────────────┐
│  Looker Studio  │
│  (Google Cloud) │
└─────────────────┘
```

---

For deployment instructions, see README.md.
For security details, see SECURITY.md.
