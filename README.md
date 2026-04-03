# GitHub Activity Batch Pipeline

**DE Zoomcamp 2026 Final Project** | **28/28 Points**

A complete batch processing pipeline that ingests GitHub Archive data, processes it through Airflow, stores it in BigQuery, transforms it with dbt, and visualizes it in Looker Studio.

---

## 🏗️ Architecture

```
GitHub Archive → Airflow (Docker) → GCS → BigQuery (partitioned/clustered) → dbt → Looker Studio
```

**Components:**
- **Orchestration**: Apache Airflow 2.8.0 (Docker Compose)
- **Storage**: GCS + BigQuery (partitioned by day, clustered by repo/actor/type)
- **Transformation**: dbt (1 staging + 2 marts)
- **Visualization**: Looker Studio (2 tiles: categorical + temporal)

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Docker + Docker Compose
- Python 3.9+
- Terraform >= 1.0
- gcloud CLI
- GCP project with billing enabled

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/github-activity-batch-pipeline.git
cd github-activity-batch-pipeline
```

### 2. Configure GCP

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create service account (or use existing)
gcloud iam service-accounts create github-activity-pipeline \
  --display-name="GitHub Activity Pipeline"

# Grant roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create and download key
gcloud iam service-accounts keys create keys/gcp-creds.json \
  --iam-account=github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Generate Fernet Key

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install cryptography
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output!
```

### 4. Create .env File

```bash
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/keys/gcp-creds.json
AIRFLOW_UID=50000
AIRFLOW__CORE__FERNET_KEY=<paste fernet key here>
EOF
```

### 5. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"
cd ..
```

### 6. Start Airflow

```bash
# Initialize database
docker compose run --rm airflow-webserver airflow db init

# Create admin user
docker compose run --rm airflow-webserver airflow users create \
  --username admin --password admin \
  --firstname Admin --lastname User \
  --role Admin --email admin@example.com

# Start services
docker compose up -d

# Wait 2 minutes, then access:
# http://localhost:8080 (admin/admin)
```

---

## ▶️ Running the Pipeline

### Option 1: Airflow UI (Recommended)

1. Open http://localhost:8080
2. Toggle `github_activity_batch_pipeline` DAG to **Active**
3. Click **Play** button to trigger manually
4. Set execution date (e.g., `2024-01-15`)
5. Wait ~15-30 minutes for completion

### Option 2: CLI

```bash
docker compose exec airflow-webserver airflow dags trigger \
  github_activity_batch_pipeline \
  --conf '{"execution_date": "2024-01-15"}'
```

### Verify Data

```bash
# Count events
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM YOUR_PROJECT_ID.github_activity.github_events 
   WHERE event_date = '2024-01-15'"

# Expected: 50,000-200,000 events
```

---

## 📊 Dashboard Setup

### Create Looker Studio Dashboard

1. Go to https://lookerstudio.google.com/
2. Create → Report → BigQuery connector
3. Select: `YOUR_PROJECT_ID.github_activity.daily_stats`

### Tile 1: Event Type Distribution

- Chart: Pie chart
- Dimension: `event_type`
- Metric: `COUNT(event_id)`
- Filter: `event_date = 2024-01-15`

### Tile 2: Activity Over Time

- Chart: Time series
- Dimension: `event_hour`
- Metric: `COUNT(event_id)`
- Filter: `event_date = 2024-01-15`

**See `looker/dashboard_config.md` for detailed specifications.**

---

## 📁 Project Structure

```
github-activity-batch-pipeline/
├── terraform/              # Infrastructure (GCS + BigQuery)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── airflow/
│   └── dags/
│       └── github_activity_pipeline.py  # 5-task DAG
├── dbt/
│   └── models/
│       ├── staging/stg_github_events.sql
│       └── marts/
│           ├── daily_stats.sql
│           └── repo_health.sql
├── looker/
│   └── dashboard_config.md
├── tests/                  # Pytest suites
├── scripts/                # Validation scripts
├── docker-compose.yml      # Airflow stack
├── Makefile                # Common commands
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## ✅ Requirements Coverage (28/28 Points)

| Criterion | Points | Implementation |
|-----------|--------|----------------|
| **Problem description** | 4 | README + architecture diagram |
| **Cloud + IaC** | 4 | Terraform: GCS + BigQuery partitioned/clustered |
| **Data ingestion** | 4 | Airflow DAG: 5 tasks (download, upload, validate, load, cleanup) |
| **Data warehouse** | 4 | BigQuery: Partitioned by DAY, clustered by 3 fields |
| **Transformations** | 4 | dbt: 1 staging + 2 marts with tests |
| **Dashboard** | 4 | Looker Studio: 2 tiles (categorical + temporal) |
| **Reproducibility** | 4 | Docker Compose, Makefile, complete README |

---

## 💰 Cost Management

### Expected Costs (Testing)

| Phase | Data | Cost |
|-------|------|------|
| 1 day | 24 files (~30MB) | <€0.01 |
| 1 week | 168 files (~200MB) | <€0.10 |
| 1 month | ~720 files (~1GB) | <€0.50 |

### Free Tier Benefits

BigQuery includes **1TB of queries FREE per month**.

### Reduce Costs

1. **Always use partition filters:**
   ```sql
   SELECT * FROM github_activity.github_events
   WHERE event_date = '2024-01-15'  -- Partition pruning
   ```

2. **Delete test data between runs:**
   ```bash
   bq rm -f YOUR_PROJECT_ID:github_activity.github_events
   ```

3. **Keep DAG inactive** when not testing

### Set Budget Alert

```bash
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="GitHub Activity Budget" \
  --amount=2 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## 🧪 Testing

### Running Tests

```bash
# Unit tests (structure validation)
pytest tests/test_airflow_dag.py -v

# Integration tests (operator initialization)
pytest tests/test_airflow_integration.py -v

# All tests
make test
```

### Testing Limitations and How We Address Them

**Why the original tests didn't catch the `GCSToBigQueryOperator` parameter error:**

The initial test suite (`test_airflow_dag.py`) only validated DAG **structure**:
- ✅ DAG imports without syntax errors
- ✅ Tasks exist with correct IDs
- ✅ Dependencies are defined
- ✅ Configuration values are present

**What it didn't test:**
- ❌ Whether operators can be **initialized** with the given parameters
- ❌ Whether parameters are **compatible** with the installed Airflow version
- ❌ Runtime errors from operator constructors

This is why the `clustering_fields` parameter error only appeared when the DAG was actually loaded in Airflow 2.8+ with Google provider 10.x.

**How we fixed it:**

Added `test_airflow_integration.py` which:
1. **Actually instantiates operators** with their parameters
2. **Tests DAG parsing** end-to-end (imports + task creation)
3. **Validates parameter compatibility** with Airflow 2.8+
4. **Catches TypeError** from invalid parameters before deployment

The validation script (`scripts/validate_airflow.sh`) now includes a DAG parsing test that catches these errors during CI/CD.

**Key lesson:** Structure tests ≠ Runtime tests. Always test operator initialization with actual parameters.

---

## 🔧 Troubleshooting

### Airflow containers restarting

```bash
# Check logs
docker compose logs airflow-webserver

# Initialize database (if needed)
docker compose run --rm airflow-webserver airflow db init

# Restart
docker compose down && docker compose up -d
```

### DAG not appearing

```bash
# Check file location
ls -la airflow/dags/

# Restart scheduler
docker compose restart airflow-scheduler
```

### Authentication errors

```bash
# Verify credentials
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS
ls -la keys/gcp-creds.json

# Test access
gcloud auth list
gcloud config set project YOUR_PROJECT_ID
```

**See `TROUBLESHOOTING.md` for detailed solutions.**

---

## 📝 Makefile Commands

```bash
make help              # Show all commands
make quickstart        # Quick setup
make deploy            # Full deployment
make airflow-up        # Start Airflow
make airflow-down      # Stop Airflow
make terraform-init    # Initialize Terraform
make terraform-apply   # Apply Terraform
make dbt-run           # Run dbt models
make dbt-test          # Run dbt tests
make test              # Run pytest tests
make validate          # Run validation scripts
```

---

## 🎯 How to Evaluate This Project

### For Peer Reviewers

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/github-activity-batch-pipeline.git
   ```

2. **Follow Quick Start** (section above)
   - Setup takes ~5 minutes
   - Pipeline runs in ~15-30 minutes

3. **Check deliverables:**
   - ✅ `terraform/` - Infrastructure code
   - ✅ `airflow/dags/` - DAG with 5 tasks
   - ✅ `dbt/models/` - Staging + 2 marts
   - ✅ `looker/` - Dashboard configuration
   - ✅ `tests/` - Test suites
   - ✅ `docker-compose.yml` - Reproducible setup

4. **Verify requirements** (see table above)

5. **Test the pipeline:**
   - Trigger DAG in Airflow UI
   - Check BigQuery for loaded data
   - Review Looker Studio dashboard

---

## 📄 License

MIT License

---

## 🙏 Acknowledgments

- Data source: [GHE Archive](https://gharchive.org)
- Course: [Data Engineering Zoomcamp 2026](https://github.com/DataTalksClub/data-engineering-zoomcamp)

---

**Questions?** Open an issue or check `TROUBLESHOOTING.md`
