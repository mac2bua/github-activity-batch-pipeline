# Peer Review Checklist

## GitHub Activity Batch Pipeline - DE Zoomcamp 2026 Final Project

Use this checklist to verify the project meets all requirements.

---

## Prerequisites Setup (5 minutes)

- [ ] Docker + Docker Compose installed
- [ ] Python 3.9+ installed
- [ ] Terraform >= 1.0 installed
- [ ] gcloud CLI installed and configured
- [ ] GCP project with billing enabled

---

## Section 1: Infrastructure (Terraform)

### Files to Check
- [ ] `terraform/main.tf` - GCS bucket + BigQuery dataset definitions
- [ ] `terraform/variables.tf` - Project ID variable
- [ ] `terraform/outputs.tf` - Resource outputs

### Verification Steps
```bash
cd terraform
terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID"
# Should show:
# - google_storage_bucket.github-activity-raw
# - google_bigquery_dataset.github_activity
# - google_bigquery_table.github_events
```

### Expected Resources
- [ ] GCS bucket with versioning enabled
- [ ] BigQuery dataset created
- [ ] BigQuery table partitioned by `event_date` (DAY)
- [ ] BigQuery table clustered by `repo_name`, `actor_login`, `event_type`

---

## Section 2: Data Ingestion (Airflow DAG)

### Files to Check
- [ ] `airflow/dags/github_activity_pipeline.py` - Main DAG (6 tasks)
- [ ] `airflow/dags/github_archive_dag.py` - Archive DAG (3 tasks)

### DAG Structure Verification

**Main DAG (github_activity_batch_pipeline):**
```
download_github_archive (HttpOperator)
    ↓
upload_to_gcs (GCSUploadOperator)
    ↓
validate_data_quality (PythonOperator)
    ↓
transform_data (PythonOperator)
    ↓
load_to_bigquery (GCSToBigQueryOperator)
    ↓
cleanup_temp_files (PythonOperator)
```

### Verification Steps
```bash
# Start Airflow
make airflow-up

# Check DAG loads without errors
docker compose exec airflow-webserver airflow dags list | grep github_activity

# Expected: 2 DAGs listed
# - github_activity_batch_pipeline
# - github_archive_pipeline
```

### Expected Behavior
- [ ] DAG has 6 tasks (not 5)
- [ ] All tasks have valid operators
- [ ] Dependencies are correctly ordered
- [ ] TEST_MODE limits to 1 hour of data

---

## Section 3: Data Warehouse (BigQuery)

### Table Schema Verification

```sql
-- Run in BigQuery console
SELECT column_name, data_type, is_partitioning_column
FROM `YOUR_PROJECT_ID.github_activity.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'github_events'
ORDER BY ordinal_position
```

### Expected Columns
- [ ] `event_id` (STRING)
- [ ] `event_type` (STRING)
- [ ] `actor_login` (STRING)
- [ ] `repo_name` (STRING)
- [ ] `created_at` (TIMESTAMP)
- [ ] `event_date` (DATE) - **Partition column**
- [ ] `payload` (JSON)

### Clustering Fields
```sql
SELECT table_name, clustering_column_names
FROM `YOUR_PROJECT_ID.github_activity.INFORMATION_SCHEMA.TABLES`
WHERE table_name = 'github_events'
```

- [ ] Clustering: `repo_name`, `actor_login`, `event_type`

---

## Section 4: Transformations (dbt)

### Files to Check
- [ ] `dbt/models/staging/stg_github_events.sql` - Staging view
- [ ] `dbt/models/marts/daily_stats.sql` - Daily aggregation
- [ ] `dbt/models/marts/repo_health.sql` - Repository health
- [ ] `dbt/models/marts/ai_agent_stats.sql` - AI agent analytics
- [ ] `dbt/models/schema.yml` - Tests

### Model Structure
```
Source: github_events (raw)
    ↓
stg_github_events (view)
    ├── is_ai_agent column ✓
    └── actor_type column ✓
    ↓
Marts:
  ├── daily_stats (table, partitioned)
  ├── repo_health (table, partitioned)
  └── ai_agent_stats (table, partitioned)
```

### Verification Steps
```bash
cd dbt
dbt deps
dbt run
dbt test
```

### Expected Results
- [ ] `dbt run` succeeds for all 4 models
- [ ] `dbt test` passes all tests (check schema.yml for test count)
- [ ] `ai_agent_stats` table created with actor_type column

---

## Section 5: Dashboard (Looker Studio)

### Data Source Connection
- [ ] Looker Studio connected to BigQuery
- [ ] `ai_agent_stats` table available
- [ ] `daily_stats` table available

### Dashboard Tiles (per spec)
- [ ] AI Agent Activity (Donut) - Events by actor_type
- [ ] Agent Timeline (Line) - Activity over time
- [ ] Top AI-Touched Repos (Bar) - Repos by AI events
- [ ] AI vs Human Ratio (Gauge) - AI percentage
- [ ] Event Breakdown (Stacked Bar) - Event types by agent
- [ ] Activity Heatmap (Heatmap) - Hour × Agent type

### Sample Query Test
```sql
-- Verify AI agent data exists
SELECT actor_type, SUM(total_events) as events
FROM `YOUR_PROJECT_ID.github_activity.ai_agent_stats`
GROUP BY actor_type
ORDER BY events DESC
```

Expected actor types:
- [ ] Copilot
- [ ] Claude
- [ ] Cursor
- [ ] CodeRabbit
- [ ] Lovable
- [ ] Human

---

## Section 6: Testing

### Run All Tests
```bash
make test
# or
pytest tests/ -v
```

### Test Files
- [ ] `tests/test_airflow_dag.py` - DAG structure tests
- [ ] `tests/test_airflow_integration.py` - Operator tests
- [ ] `tests/test_terraform.py` - Terraform validation
- [ ] `tests/test_dbt_models.py` - dbt model tests

### Expected Test Results
- [ ] All tests pass (no failures)
- [ ] Test coverage includes:
  - DAG structure validation
  - Operator initialization
  - dbt model compilation
  - Terraform syntax

---

## Section 7: Reproducibility

### Makefile Commands
```bash
make help
# Should list all available commands

make deploy
# Should run: validate → terraform-apply → airflow-up → dbt-build
```

### Docker Compose
- [ ] `docker-compose.yml` defines Airflow services
- [ ] Environment variables documented in `.env.example`
- [ ] Volumes mounted correctly for DAGs and logs

### Documentation
- [ ] README.md has complete Quick Start
- [ ] TROUBLESHOOTING.md exists (if needed)
- [ ] All file paths in docs are correct

---

## Section 8: AI Agent Analytics

### Verify AI Agent Detection
```sql
-- Check staging model
SELECT DISTINCT actor_type, COUNT(*) as cnt
FROM `YOUR_PROJECT_ID.github_activity.stg_github_events`
GROUP BY actor_type
ORDER BY cnt DESC
```

Expected:
- [ ] Human appears as actor_type
- [ ] At least one AI agent type appears
- [ ] is_ai_agent column has true/false values

### Verify AI Agent Stats
```sql
SELECT *
FROM `YOUR_PROJECT_ID.github_activity.ai_agent_stats`
LIMIT 10
```

Expected columns:
- [ ] stats_date
- [ ] actor_type
- [ ] total_events
- [ ] unique_agents
- [ ] repos_touched
- [ ] push_events, pr_events, comment_events
- [ ] avg_activity_hour

---

## Scoring Guide

| Criterion | Points | Verification |
|-----------|--------|--------------|
| Problem description | 4 | README + AI focus |
| Cloud + IaC | 4 | Terraform resources |
| Data ingestion | 4 | 6-task DAG running |
| Data warehouse | 4 | Partitioned/clustered table |
| Transformations | 4 | dbt models + tests |
| Dashboard | 4 | Looker Studio tiles |
| Reproducibility | 4 | Docker + Makefile + docs |
| **Total** | **28** | |

---

## Quick Validation Commands

```bash
# Full validation in one command
make validate && make test && make dbt-run && make dbt-test

# Check data
bq query "SELECT COUNT(*) FROM github_activity.github_events"
# Expected: > 0

# Check AI agent stats
bq query "SELECT actor_type, SUM(total_events) FROM github_activity.ai_agent_stats GROUP BY actor_type"
# Expected: Multiple actor types
```

---

## Notes for Reviewers

1. **TEST_MODE**: The DAG processes only 1 hour by default for fast runs (~2-5 min). Change `test_hours = [12]` to `range(24)` for full day.

2. **AI Agent Focus**: This project tracks AI coding agent contributions. The dashboard highlights Copilot, Claude, Cursor, CodeRabbit, and other AI agents.

3. **Sample Data**: Test runs produce ~50K events. Production runs (~1-2M events) require disabling TEST_MODE.

4. **Costs**: Estimated <€0.05/month for test data. BigQuery free tier (1TB/month) covers dashboard queries.

---

**Questions?** Open an issue or check `TROUBLESHOOTING.md`