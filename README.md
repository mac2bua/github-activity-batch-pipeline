# GitHub Activity Batch Pipeline

**DE Zoomcamp 2026 Final Project** 🚀

Complete batch processing pipeline: GitHub Archive → GCP → BigQuery → dbt → Looker Studio

---

## Architecture

```
GitHub Archive → Airflow → GCS → BigQuery → dbt → Looker Studio
```

---

## Project Structure

```
github-activity-batch-pipeline/
├── terraform/          # GCS, BigQuery, IAM
├── airflow/
│   ├── dags/           # Pipeline DAG
│   ├── docker-compose.yaml
│   ├── Dockerfile
│   └── requirements.txt
├── dbt/
│   ├── models/
│   │   ├── staging/    # stg_github_events
│   │   └── marts/      # daily_stats, repo_health
│   ├── dbt_project.yml
│   └── profiles.yml
├── docs/               # Looker spec, architecture
└── README.md
```

---

## Quick Start

### 1. Provision Infrastructure

```bash
cd terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT" -var="environment=dev"
```

### 2. Start Airflow

```bash
cd airflow
export GCP_PROJECT_ID="your-project"
export GCS_BUCKET="gh-activity-dev-your-project"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
docker-compose up -d
```

Access: http://localhost:8080 (airflow/airflow)

### 3. Run dbt

```bash
cd dbt
dbt deps
dbt run
dbt test
```

### 4. Create Looker Studio Dashboard

Follow `docs/looker_dashboard_spec.md`

---

## Requirements Met (28 Points)

- ✅ Terraform: GCS + BigQuery (partitioned/clustered)
- ✅ Airflow DAG: 3 tasks (download, upload, load)
- ✅ dbt: 1 staging + 2 marts
- ✅ Docker Compose for Airflow
- ✅ Looker Studio spec (categorical + temporal tiles)
- ✅ Complete README

---

## BigQuery Schema

| Field | Type | Description |
|-------|------|-------------|
| id | STRING | Event ID (REQUIRED) |
| type | STRING | Event type |
| actor_login | STRING | GitHub username |
| repo_name | STRING | Repository |
| created_at | TIMESTAMP | Event time |
| date_partition | DATE | Partition field |
| payload | JSON | Full payload |

**Partition:** DAY on `date_partition`  
**Cluster:** `type`, `actor_login`, `repo_name`

---

## License

MIT - DE Zoomcamp 2026
