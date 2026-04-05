# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Activity Batch Pipeline - A DE Zoomcamp 2026 final project (28/28 points). Ingests GitHub Archive data via Airflow, stores in BigQuery (partitioned/clustered), transforms with dbt, and visualizes in Looker Studio.

**Architecture Flow:**
```
GHE Archive → Airflow (Docker) → GCS → BigQuery → dbt → Looker Studio
```

## Common Commands

```bash
# Full deployment
make deploy                         # validate → terraform-apply → airflow-up → dbt-build

# Infrastructure
make terraform-init                  # Initialize Terraform
make terraform-apply PROJECT_ID=x   # Apply infrastructure
make terraform-destroy PROJECT_ID=x  # Destroy all resources

# Airflow
make airflow-up                      # Start Airflow stack (localhost:8080, admin/admin)
make airflow-down                    # Stop Airflow
make airflow-logs                    # View logs
make airflow-init                    # Initialize database

# dbt
make dbt-build                       # deps + run + test
make dbt-run                         # Run models
make dbt-test                        # Run tests
make dbt-docs                        # Generate docs

# Testing
make test                            # Run all pytest tests
make test-airflow                    # Airflow DAG tests only
make validate                        # Run all validation scripts
```

## Required Environment

Create `.env` file with:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/keys/gcp-creds.json
AIRFLOW_UID=50000
AIRFLOW__CORE__FERNET_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```

## Key Architecture Details

### Airflow DAG (6 tasks)
```
download_github_archive → upload_to_gcs → validate_data_quality → transform_data → load_to_bigquery → cleanup_temp_files
```

**Critical Implementation Notes:**
- DAG is in TEST MODE: downloads only 1 hourly file (hour 12) to keep runs fast (~2-5 min)
- Change `test_hours = [12]` to `range(24)` in production for all 24 hours
- `GCSToBigQueryOperator` in Airflow 2.8+ Google provider 10.x does NOT accept `schema_fields`, `clustering_fields`, or `time_partitioning` parameters - schema is pre-created via Terraform
- `autodetect=False` is required to prevent schema type inference errors

### BigQuery Table Schema
Pre-created via Terraform with:
- **Partitioning**: DAY on `event_date` field (90-day expiration)
- **Clustering**: `repo_name`, `actor_login`, `event_type`
- **Key fields**: event_id (STRING), event_type, actor_login, repo_name, created_at (TIMESTAMP), payload (JSON)

### dbt Models
```
Source: github_events (raw)
    ↓
stg_github_events (view) - cleans and adds quality flags
    ↓
Marts:
  ├── daily_stats (table, partitioned by stats_date)
  └── repo_health (table, partitioned by snapshot_date)
```

### GCS Paths
- Raw data: `gs://github-activity-batch-raw-{project_id}/data/{date}-{hour}.json.gz`
- Transformed: `gs://github-activity-batch-raw-{project_id}/transformed/{date}-{hour}.json.gz`

## Testing Structure

```
tests/
├── test_airflow_dag.py          # DAG structure, task existence, dependencies
├── test_airflow_integration.py  # Operator initialization with actual params
├── test_terraform.py            # Terraform validation
├── test_dbt_models.py           # dbt model tests
├── test_pipeline_tasks.py       # Pipeline task tests
├── test_project_id_config.py    # Configuration tests
└── test_gcs_source_objects.py   # GCS path tests
```

Run tests: `pytest tests/ -v`

## Project Conventions

**Python:**
- Type hints required for function signatures
- Docstrings for all functions
- PEP 8 formatting

**Terraform:**
- Variables in `variables.tf`, outputs in `outputs.tf`
- Resource naming: `{resource_name}-{var.project_id}`

**dbt:**
- Staging models as views
- Mart models as tables with partitioning
- All models must have tests in `schema.yml`

**DAG Files:**
- Two DAG files: `github_activity_pipeline.py` (main, 6 tasks) and `github_archive_dag.py` (3 tasks)
- Both import at module level, requiring `project_id` to be configured via Airflow Variable or env var

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| DAG not appearing | `docker compose restart airflow-scheduler` |
| Auth errors | Check `GOOGLE_APPLICATION_CREDENTIALS` path in `.env` |
| BigQuery schema errors | Table pre-created by Terraform; use `autodetect=False` |
| No data in dashboard | Verify date range has data; check partition filter |
| Pipeline slow | TEST MODE uses 1 hour; change to `range(24)` for production |

See `TROUBLESHOOTING.md` for detailed solutions.

## Development Workflow

1. **Infrastructure changes**: Edit `terraform/`, run `make terraform-apply`
2. **DAG changes**: Edit `airflow/dags/`, restart scheduler
3. **dbt changes**: Edit `dbt/models/`, run `make dbt-build`
4. **Before committing**: Run `make validate && make test`