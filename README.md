# GitHub AI Contributions

**DE Zoomcamp 2026 Final Project**

A batch processing pipeline analyzing **AI coding agent contributions** on GitHub. Ingests GitHub Archive data via Airflow, stores in BigQuery (partitioned/clustered), transforms with dbt, and visualizes in Looker Studio.

---

## Architecture

```
+---------------------+     +---------------------+     +---------------------+
|   GitHub Archive    |     |   Apache Airflow    |     |    GCS Bucket       |
|   gharchive.org     |---->|   Docker Compose    |---->|   Raw JSON.gz       |
|   24 files/day      |     |   Celery Executor   |     |   90-day TTL        |
+---------------------+     +---------------------+     +----------+----------+
                                                                   |
                                                                   v
                                                        +----------+----------+
                                                        |    BigQuery         |
                                                        |   Partitioned DAY   |
                                                        |   Clustered 3 fields|
                                                        +----------+----------+
                                                                   |
                                                                   v
                                                        +----------+----------+
                                                        |    dbt 1.9+         |
                                                        |   1 Staging View    |
                                                        |   3 Mart Tables     |
                                                        +----------+----------+
                                                                   |
                                                                   v
                                                        +----------+----------+
                                                        |   Looker Studio     |
                                                        |   AI Agent Dashboard|
                                                        |   7+ Charts         |
                                                        +---------------------+
```

| Component | Technology | Purpose |
|-----------|------------|---------|
| Orchestration | Apache Airflow 2.8.0 (Docker Compose) | DAG scheduling, data pipeline |
| Storage | GCS + BigQuery | Raw files + partitioned warehouse |
| Transformation | dbt 1.9+ | 1 staging + 3 mart models |
| Visualization | Looker Studio | 7+ interactive charts |

---

## Project Structure

```
github-ai-contributions/
+-- airflow/
|   +-- dags/                    # Airflow DAG files
|       +-- github_activity_pipeline.py
+-- dbt/
|   +-- models/                  # dbt transformation models
|       +-- staging/
|       +-- marts/
+-- terraform/                   # Infrastructure as Code
|   +-- main.tf
|   +-- variables.tf
|   +-- outputs.tf
+-- tests/                       # Pytest test suites
+-- scripts/                     # Validation scripts
+-- Makefile                     # Build automation
+-- docker-compose.yml           # Airflow stack config
+-- README.md
```

---

## Pipeline Workflow

```
+------------------------+     +------------------------+     +------------------------+
| download_github_archive|     | upload_to_gcs          |     | validate_data_quality  |
|                        |---->|                        |---->|                        |
| Download 24 hourly     |     | Upload raw JSON.gz     |     | Check JSON structure   |
| files from GH Archive  |     | to GCS bucket           |     | Verify required fields |
+------------------------+     +------------------------+     +-----------+------------+
                                                            |
                                                            v
+------------------------+     +------------------------+     +------------------------+
| cleanup_temp_files     |     | load_to_bigquery       |     | transform_data         |
|                        |<----|                        |<----|                        |
| Remove local temp      |     | Load to partitioned    |     | Flatten nested JSON   |
| files, free disk       |     | BigQuery table         |     | Convert to BQ schema   |
+------------------------+     +------------------------+     +------------------------+
```

| Task | Description |
|------|-------------|
| `download_github_archive` | Downloads GitHub Archive JSON for specified date (24 hours) |
| `upload_to_gcs` | Uploads raw data to GCS |
| `validate_data_quality` | Validates JSON structure and required fields |
| `transform_data` | Transforms to BigQuery-compatible schema |
| `load_to_bigquery` | Loads to partitioned BigQuery table |
| `cleanup_temp_files` | Removes temporary files |

**Note:** DAG runs in TEST_MODE (50k records per file) for faster execution. See `airflow/dags/github_activity_pipeline.py` for production configuration.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Terraform >= 1.0
- gcloud CLI + GCP project with billing enabled
- Python 3.12+ (for dbt)

### 1. Configure Environment

Create a GCP service account with BigQuery and Storage permissions:

```bash
# Create service account
gcloud iam service-accounts create github-activity-pipeline

# Grant BigQuery admin role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

# Grant Storage admin role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Download credentials
gcloud iam service-accounts keys create keys/gcp-creds.json \
  --iam-account=github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 2. Create `.env` File

Copy the example file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/keys/gcp-creds.json
AIRFLOW_UID=50000
AIRFLOW__CORE__FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 3. Deploy Infrastructure

1. Initialize Terraform:

   ```bash
   make terraform-init
   ```

2. Review planned changes:

   ```bash
   make terraform-plan PROJECT_ID=YOUR_PROJECT_ID
   ```

   This shows what resources will be created (GCS bucket, BigQuery dataset/table).

3. Apply changes:

   ```bash
   make terraform-apply PROJECT_ID=YOUR_PROJECT_ID
   ```

### 4. Start Airflow

1. Start the Airflow stack:

   ```bash
   make airflow-up
   ```

2. Wait for Airflow to initialize (~2 minutes). Check status:

   ```bash
   docker compose ps
   ```

   All services should show "running" status.

3. Access the Airflow UI:

   - URL: http://localhost:8080
   - Username: `admin`
   - Password: `admin`

4. If DAGs don't appear, restart the scheduler:

   ```bash
   docker compose restart airflow-scheduler
   ```

5. Set the Airflow Variable for GCP project:
   - Go to Admin -> Variables
   - Add variable: `project_id` = `YOUR_PROJECT_ID`

### 5. Set Up dbt

1. Authenticate with GCP:

   ```bash
   gcloud auth application-default login
   ```

2. Create virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure dbt profile (if not auto-detected):

   ```bash
   mkdir -p ~/.dbt
   cat > ~/.dbt/profiles.yml << EOF
   github_activity:
     target: dev
     outputs:
       dev:
         type: bigquery
         project: YOUR_PROJECT_ID
         dataset: github_activity
         method: oauth
   EOF
   ```

4. Load environment variables for dbt:

   ```bash
   set -a && source .env && set +a
   ```

   This exports the `.env` variables to your shell so dbt can read them. The project's `dbt/profiles.yml` and `dbt/models/staging/sources.yml` use `{{ env_var('GOOGLE_CLOUD_PROJECT') }}` which requires the variable to be exported.

**Note:** Airflow runs in Docker with the official `apache/airflow:2.8.0` image.
The `requirements.txt` is for local dbt transformations and testing only.

### 6. Run Pipeline

1. **Trigger Airflow DAG:**
   - Open http://localhost:8080
   - Toggle `github_activity_batch_pipeline` DAG to **Active**
   - Click **Play** -> **Trigger DAG w/ config** -> set `execution_date` (e.g., `2026-03-28`)
   - Each run downloads 24 hours of data (~5 min)

2. **Run dbt transformations:**

   ```bash
   make dbt-build   # Runs: deps + run + test
   ```

3. **Verify data:**

   ```bash
   bq query --use_legacy_sql=false \
     "SELECT event_date, COUNT(*) as events
      FROM github_activity.github_events
      GROUP BY event_date ORDER BY event_date"
   ```

---

## dbt Transformations

After Airflow loads data, run dbt to create analytics models:

```bash
make dbt-build   # deps + run + test
```

**Models created:**

| Model | Type | Description |
|-------|------|-------------|
| `stg_github_events` | View | Cleaned events with quality flags |
| `daily_stats` | Table | Daily aggregated metrics |
| `repo_health` | Table | Repository health scores |
| `ai_agent_stats` | Table | AI agent activity analytics |

Verify: `bq query "SELECT * FROM github_activity.ai_agent_stats LIMIT 10"`

---

## Dashboard Setup

### Looker Studio

1. Go to https://lookerstudio.google.com/
2. Create -> Report -> BigQuery connector
3. Select: `YOUR_PROJECT_ID.github_activity.ai_agent_stats`

**Dashboard Visualizations (7+ charts):**

| Visualization | Type | Data Source | Metrics |
|--------------|------|-------------|---------|
| Key Metrics | Score Cards (4) | ai_agent_stats | Total AI Events, Unique Agents, Repos Touched, AI Ratio |
| AI Agent Activity | Donut | ai_agent_stats | actor_type, SUM(total_events) |
| Agent Timeline | Line | ai_agent_stats | stats_date, SUM(total_events) by actor_type |
| Top AI-Touched Repos | Bar | stg_github_events | repo_name, COUNT(*) WHERE actor_type='AI' |
| AI Adoption Over Time | Line | ai_ratio_timeline | event_date, ai_percentage |
| AI vs Human Ratio | Gauge | ai_agent_stats | ai_events/total_events |
| Event Type Breakdown | Stacked Bar | ai_agent_stats | actor_type, push/pr/comment/star events |
| Activity Heatmap | Grid | stg_github_events | HOUR(created_at), actor_type, COUNT(*) |

**[View Live Dashboard](https://lookerstudio.google.com/reporting/5417917d-21ab-43c6-bf16-c1a13d8976af)**

![Dashboard](images/github_ai_activity_dashboard.png)

---

## Testing

```bash
make test              # All tests
make test-airflow      # DAG structure tests
make test-terraform    # Terraform validation
make test-dbt          # dbt model tests
```

---

## Peer-Review Guide

This section helps reviewers verify the project meets DE Zoomcamp criteria.

### Checklist for Reviewers

| Criterion | Location | How to Verify |
|-----------|----------|---------------|
| Problem description | README.md, CLAUDE.md | Read project overview |
| Cloud + IaC | terraform/ | Run `make terraform-plan` |
| Data ingestion | airflow/dags/ | Check DAG structure with `make test-airflow` |
| Data warehouse | BigQuery console | Verify table is partitioned & clustered |
| Transformations | dbt/models/ | Run `make dbt-test` |
| Dashboard | Looker Studio link | Open dashboard URL |
| Reproducibility | All files | Run `make validate && make test` |

### Verification Commands

```bash
# Run all validations
make validate

# Run all tests
make test

# Full deployment test
make deploy
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| DAG not appearing | `docker compose restart airflow-scheduler` |
| Auth errors | Check `GOOGLE_APPLICATION_CREDENTIALS` path in `.env` |
| BigQuery schema errors | Table pre-created by Terraform; use `autodetect=False` |
| dbt env var error | Run `set -a && source .env && set +a` before dbt commands |
| dbt won't run | Ensure Python 3.12-3.13 (not 3.14+) |

See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for detailed solutions.

---

## License

MIT License

## Acknowledgments

- Data source: [GHE Archive](https://gharchive.org)
- Course: [Data Engineering Zoomcamp 2026](https://github.com/DataTalksClub/data-engineering-zoomcamp)