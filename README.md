# GitHub Activity Batch Processing Pipeline

A complete batch processing pipeline for GitHub activity data using GCP, Airflow, dbt, and Looker Studio.

## 📋 Overview

This pipeline:
1. **Downloads** daily GitHub activity archives from GHE Archive
2. **Uploads** raw data to Google Cloud Storage
3. **Loads** transformed data into BigQuery (partitioned & clustered)
4. **Models** data with dbt (staging + marts)
5. **Visualizes** insights in Looker Studio

## 🏗️ Architecture

```
GHE Archive → Airflow → GCS → BigQuery → dbt → Looker Studio
   ↓            ↓        ↓       ↓        ↓        ↓
Download    Orchestrate  Store  Warehouse  Model  Visualize
```

## 📁 Project Structure

```
github-activity-batch-pipeline/
├── terraform/
│   └── main.tf                 # GCS + BigQuery infrastructure
├── airflow/
│   ├── dags/
│   │   └── github_activity_pipeline.py  # ETL DAG (4 tasks)
│   ├── logs/                   # Airflow logs (auto-created)
│   └── plugins/                # Custom plugins (optional)
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_github_events.sql
│   │   └── marts/
│   │       ├── daily_stats.sql
│   │       └── repo_health.sql
│   └── dbt_project.yml
├── docker-compose.yml          # Airflow stack
├── .env.example                # Environment variables template
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Google Cloud Project with billing enabled
- Service account with: Storage Admin, BigQuery Admin, Airflow Worker roles
- Terraform >= 1.0
- Python 3.9+ (for dbt)

### 1. Clone & Setup

```bash
cd ~/Repositories/github-activity-batch-pipeline

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Provision GCP Infrastructure (Terraform)

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan and apply
terraform plan -var="project_id=your-project-id"
terraform apply -var="project_id=your-project-id"

# Note the outputs:
# - bucket_name: GCS bucket for raw data
# - bq_table_id: BigQuery table destination
```

### 3. Start Airflow

```bash
# Set permissions for Airflow volumes
mkdir -p airflow/logs airflow/dags airflow/plugins
chmod -R 777 airflow/logs

# Initialize and start
docker compose up airflow-init
docker compose up -d

# Access Airflow UI: http://localhost:8080
# Default credentials: admin / admin
```

### 4. Configure Airflow Variables

In Airflow UI:
1. Go to **Admin** → **Variables**
2. Add variable: `project_id` = `your-gcp-project-id`

### 5. Enable the DAG

1. In Airflow UI, toggle `github_activity_batch_pipeline` to **Active**
2. DAG runs daily at midnight (UTC)
3. Set `catchup=True` to backfill historical data

### 6. Run dbt Models

```bash
# Install dbt dependencies
pip install dbt-bigquery

# Configure BigQuery connection
# Create profiles.yml in ~/.dbt/profiles.yml

# Run dbt models
cd dbt
dbt deps
dbt run
dbt test
```

### 7. Create Looker Studio Dashboard

1. Open [Looker Studio](https://lookerstudio.google.com/)
2. Connect to BigQuery dataset: `github_activity`
3. Create two tiles:
   - **Categorical**: Event types by repo/actor (pie/bar chart)
   - **Temporal**: Activity trends over time (line chart)
4. Use `daily_stats` and `repo_health` tables for metrics

## 📊 Dashboard Tiles

### Tile 1: Categorical Analysis
- Event type distribution (pie chart)
- Top repositories by activity (bar chart)
- Top contributors (table)

### Tile 2: Temporal Analysis
- Daily event trends (line chart)
- Hourly activity heatmap
- Weekday vs weekend comparison

## 🔧 Configuration

### Environment Variables (.env)

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
AIRFLOW_UID=50000
```

### Airflow DAG Schedule

- **Default**: `@daily` (midnight UTC)
- **Backfill**: Set `catchup=True` and adjust `start_date`
- **Max concurrent runs**: 1 (prevents overlap)

### BigQuery Table

- **Partitioning**: By `event_date` (DAY)
- **Clustering**: `repo_name`, `actor_login`, `event_type`
- **Retention**: 90 days (configurable in Terraform)

## 🧪 Testing

### Validate Airflow DAG

```bash
# Check DAG syntax
docker compose exec airflow-webserver \
  airflow dags list

# Test DAG import
docker compose exec airflow-webserver \
  airflow dags test github_activity_batch_pipeline
```

### Validate dbt Models

```bash
# Run tests
dbt test

# Preview data
dbt run --select stg_github_events
dbt preview
```

### Validate Terraform

```bash
# Check infrastructure
terraform plan
terraform output
```

## 📈 Monitoring

### Airflow
- DAG run status in UI
- Task logs: `airflow/logs/`
- Alerts: Configure email on failure

### BigQuery
- Query costs: GCP Console → BigQuery → Information schema
- Data freshness: Check `MAX(loaded_at)` in table

### dbt
- Test results: `dbt test`
- Documentation: `dbt docs generate && dbt docs serve`

## 🛠️ Troubleshooting

### DAG Not Appearing
```bash
# Check file permissions
ls -la airflow/dags/

# Restart scheduler
docker compose restart airflow-scheduler
```

### GCS Upload Fails
- Verify service account has Storage Admin role
- Check bucket name matches Terraform output
- Review worker logs: `docker compose logs airflow-worker`

### BigQuery Load Errors
- Ensure table schema matches source data
- Check partition field exists in data
- Verify clustering fields are valid types

## 📝 Requirements Coverage

| Requirement | Status | Location |
|------------|--------|----------|
| Terraform: GCS bucket | ✅ | `terraform/main.tf` |
| Terraform: BQ partitioned/clustered | ✅ | `terraform/main.tf` |
| Airflow DAG: 3+ tasks | ✅ (4 tasks) | `airflow/dags/github_activity_pipeline.py` |
| dbt: staging model | ✅ | `dbt/models/staging/stg_github_events.sql` |
| dbt: daily_stats mart | ✅ | `dbt/models/marts/daily_stats.sql` |
| dbt: repo_health mart | ✅ | `dbt/models/marts/repo_health.sql` |
| Docker Compose | ✅ | `docker-compose.yml` |
| Looker Studio (2 tiles) | ✅ | Documented in README |
| Complete README | ✅ | `README.md` |

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

---

**Built with**: Terraform, Apache Airflow, dbt, Google Cloud Platform, Looker Studio
