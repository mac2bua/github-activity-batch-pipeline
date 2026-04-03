# Changelog

All notable changes to the GitHub Activity Batch Pipeline project.

## [1.0.0] - 2024-04-03

### Added

#### Infrastructure (Terraform)
- GCS bucket for raw GitHub data with versioning
- BigQuery table with DAY partitioning on event_date
- BigQuery clustering on repo_name, actor_login, event_type
- 90-day data retention policy
- Lifecycle rules for automatic cleanup

#### Orchestration (Airflow)
- DAG with 5 tasks: download, upload, validate, load, cleanup
- Daily schedule with catchup enabled
- Error handling and retry logic
- Data quality validation before load
- GCS to BigQuery transfer with schema enforcement

#### Data Modeling (dbt)
- Staging model: `stg_github_events` with data quality flags
- Mart: `daily_stats` with aggregated daily metrics
- Mart: `repo_health` with health scores and classifications
- Schema tests for uniqueness, null checks, and accepted values
- Partitioned and clustered mart tables

#### Visualization (Looker Studio)
- Dashboard configuration for 2 tiles
- Categorical analysis: event types, top repos, contributors
- Temporal analysis: trends, heatmaps, comparisons
- Global filters for date, event type, repo owner

#### Documentation
- Complete README with setup instructions
- Architecture diagram
- Troubleshooting guide
- Requirements coverage matrix
- Looker Studio dashboard configuration guide

#### Testing
- pytest tests for Airflow DAG structure
- pytest tests for Terraform configuration
- pytest tests for dbt models
- Validation scripts for all components

#### DevOps
- Docker Compose for Airflow stack
- Environment variable templates
- Git ignore configuration
- Validation scripts (terraform, airflow, dbt)

### Technical Details

**Airflow Tasks:**
1. `download_github_archive` - Fetch 24 hourly files from GHE Archive
2. `upload_to_gcs` - Upload to GCS bucket
3. `validate_data_quality` - Verify files before load
4. `load_to_bigquery` - Load with partitioning/clustering
5. `cleanup_temp_files` - Remove temporary files

**BigQuery Schema:**
- event_id (STRING, REQUIRED)
- event_type (STRING, REQUIRED)
- actor_login (STRING, REQUIRED)
- repo_name (STRING, REQUIRED)
- repo_owner (STRING, REQUIRED)
- payload (JSON, NULLABLE)
- public (BOOLEAN, REQUIRED)
- created_at (TIMESTAMP, REQUIRED)
- event_date (DATE, REQUIRED) - Partition field
- loaded_at (TIMESTAMP, REQUIRED)

**dbt Models:**
- 1 staging model (view)
- 2 mart models (partitioned tables)
- 15+ data quality tests

### Requirements Coverage

| Requirement | Status | Details |
|------------|--------|---------|
| Terraform: GCS bucket | ✅ | Versioning, lifecycle rules |
| Terraform: BQ partitioned/clustered | ✅ | DAY partition, 3-field cluster |
| Airflow DAG: 3+ tasks | ✅ | 5 tasks implemented |
| dbt: staging model | ✅ | stg_github_events.sql |
| dbt: daily_stats mart | ✅ | Aggregated daily metrics |
| dbt: repo_health mart | ✅ | Health scores 0-100 |
| Docker Compose | ✅ | Full Airflow stack |
| Looker Studio (2 tiles) | ✅ | Categorical + Temporal |
| Complete README | ✅ | Setup, troubleshooting, coverage |

---

## Future Enhancements

- [ ] Add incremental dbt models for real-time updates
- [ ] Implement Slack/email alerts for pipeline failures
- [ ] Add data freshness monitoring dashboard
- [ ] Support multiple GHE Archive sources
- [ ] Add cost monitoring for BigQuery queries
- [ ] Implement row-level security in BigQuery
- [ ] Add dbt snapshots for slowly changing dimensions
