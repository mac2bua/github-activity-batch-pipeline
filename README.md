# GitHub Activity Batch Pipeline

**DE Zoomcamp 2026 Final Project** | **28/28 Points Complete**

A complete batch processing pipeline that ingests GitHub Archive data, processes it through Airflow, stores it in BigQuery, transforms it with dbt, and visualizes it in Looker Studio.

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start (5 minutes)](#quick-start-5-minutes)
- [Detailed Setup Guide](#detailed-setup-guide)
  - [1. Create GCP Project](#1-create-gcp-project)
  - [2. Set Budget Alert](#2-set-budget-alert)
  - [3. Create Service Account](#3-create-service-account)
  - [4. Install gcloud CLI](#4-install-gcloud-cli)
  - [5. Set Up Python Environment](#5-set-up-python-environment)
  - [6. Configure Environment Variables](#6-configure-environment-variables)
- [Deployment](#deployment)
- [Running the Pipeline](#running-the-pipeline)
- [Dashboard Setup](#dashboard-setup)
- [Cost Management](#cost-management)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## 🏗️ Architecture

```
GitHub Archive (gharchive.org)
         ↓
    Apache Airflow (Docker)
    ┌─────────────────────┐
    │ 1. Download (24h)   │
    │ 2. Upload to GCS    │
    │ 3. Validate         │
    │ 4. Load to BigQuery │
    │ 5. Cleanup          │
    └─────────────────────┘
         ↓
    Google Cloud Storage
         ↓
    BigQuery (Partitioned + Clustered)
         ↓
    dbt (staging + marts)
         ↓
    Looker Studio Dashboard
```

---

## ✅ Prerequisites

| Tool | Version | Install |
|------|---------|---------|  
| Python | 3.9-3.12 | `python3 --version` (see note below) |
| Docker | 20.10+ | [docker.com](https://docs.docker.com/get-docker/) |
| Terraform | 1.0+ | [terraform.io](https://developer.hashicorp.com/terraform/install) |
| gcloud CLI | Latest | See [Setup Guide](#4-install-gcloud-cli) |
| Git | Any | Pre-installed on macOS |

**⚠️ Python Version Note:**

If you have Python 3.13+ (like macOS with Homebrew), you have two options:

**Option A: Use Docker (Recommended)**
- Airflow runs in Docker with Python 3.9
- You only need local Python to generate Fernet key
- Install only `cryptography` package locally

**Option B: Install Python 3.11**
```bash
brew install python@3.11
python3.11 -m venv .venv
```

**Check what you have:**
```bash
python3 --version
docker --version
terraform --version
gcloud --version  # Will fail if not installed
```

---

## 🚀 Quick Start (5 minutes)

**If you already have GCP + gcloud configured:**

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/github-activity-batch-pipeline.git
cd github-activity-batch-pipeline

# 2. Create Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Generate Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4. Create .env file
cp .env.example .env
# Edit .env with your project ID, credentials path, and Fernet key

# 5. Deploy infrastructure
cd terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"

# 6. Start Airflow
cd ..
make airflow-up

# 7. Open Airflow UI
# http://localhost:8080 (admin/admin)
# Enable DAG: github_activity_batch_pipeline
```

---

## 📖 Detailed Setup Guide

### 1. Create GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Create Project"** (top banner)
3. Enter project name: `github-activity-batch-pipeline`
4. Click **"Create"**
5. Note the **Project ID** (e.g., `github-activity-batch-pipeline-12345`)

**Why a dedicated project?**
- Isolate costs for this project
- Easy to delete when done
- Clean separation from other work

---

### 2. Set Budget Alert

**⚠️ DO THIS FIRST to avoid surprise costs!**

```bash
# Get your billing account ID
gcloud billing accounts list

# Create €2 budget alert
gcloud billing budgets create \
  --billing-account=XXXXXX-YYYYYY-ZZZZZZ \
  --display-name="GitHub Activity Budget" \
  --amount=2 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

**Or via Console:**
1. Go to [Billing → Budgets](https://console.cloud.google.com/billing/budgets)
2. Click **"Create Budget"**
3. Name: `GitHub Activity Budget`
4. Amount: €2
5. Notifications: 50%, 90%, 100%
6. Click **"Create"**

**Expected cost for testing:** <€0.50 (well under budget!)

---

### 3. Create Service Account

**Via Console:**

1. Go to [IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **"Create Service Account"**
3. Name: `github-activity-pipeline`
4. Grant roles:
   - **BigQuery Admin** (`roles/bigquery.admin`)
   - **Storage Admin** (`roles/storage.admin`)
5. Click **"Done"**
6. Click on the service account email
7. Go to **"Keys"** tab
8. Click **"Add Key" → "Create new key"**
9. Select **JSON** format
10. Click **"Create"** → Downloads JSON file

**Via CLI:**
```bash
# Create service account
gcloud iam service-accounts create github-activity-pipeline \
  --display-name="GitHub Activity Pipeline"

# Grant roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create key
gcloud iam service-accounts keys create ~/Downloads/gcp-creds.json \
  --iam-account=github-activity-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

---

### 4. Install gcloud CLI

**macOS (Homebrew):**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
# Add repository
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
  sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Install
sudo apt-get update && sudo apt-get install google-cloud-cli
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

**Initialize:**
```bash
gcloud init
# Follow prompts to login and select project
```

**Verify:**
```bash
gcloud config list
gcloud projects list
```

---

### 5. Set Up Python Environment (Minimal)

**⚠️ If you have Python 3.13+:** Don't worry! Airflow runs in Docker with Python 3.9. You only need local Python to generate the Fernet key.

**Create Virtual Environment:**
```bash
cd ~/Repositories/github-activity-batch-pipeline

# Create venv
python3 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate
```

**Install ONLY Cryptography (for Fernet key generation):**
```bash
# This works on Python 3.13+
pip install cryptography==44.0.0
```

**Generate Fernet Key:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output (long base64 string ending in ==)
```

**That's it!** You don't need to install Airflow, dbt, or other packages locally. Everything runs in Docker.

**Deactivate when done:**
```bash
deactivate
```

**Alternative: Python 3.11**

If you prefer to install packages locally, use Python 3.11:
```bash
brew install python@3.11
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 6. Configure Environment Variables

**Generate Fernet Key:**
```bash
# Activate venv first
source .venv/bin/activate

# Generate key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copy the output (long base64 string ending in ==)
```

**Create `.env` File:**
```bash
cd ~/Repositories/github-activity-batch-pipeline

# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

**`.env` Contents:**
```bash
# GCP Project Configuration
GOOGLE_CLOUD_PROJECT=github-activity-batch-pipeline

# Service Account Key Path
GOOGLE_APPLICATION_CREDENTIALS=/Users/cristian/Repositories/github-activity-batch-pipeline/keys/gcp-creds.json

# Airflow Fernet Key (encrypts passwords in connections)
AIRFLOW__CORE__FERNET_KEY=<paste generated key here>

# Email Configuration (optional - leave empty for testing)
AIRFLOW__EMAIL__SMTP_PASSWORD=
```

**Move Service Account Key:**
```bash
# Create keys directory
mkdir -p keys

# Move your downloaded key
mv ~/Downloads/gcp-creds.json keys/
```

**Verify Setup:**
```bash
# Check .env exists
cat .env

# Check key exists (should NOT be tracked by git)
ls -la keys/
git ls-files keys/  # Should return nothing!
```

---

## 🚀 Deployment

### Step 1: Initialize Terraform

```bash
cd terraform
terraform init
```

### Step 2: Review Plan

```bash
terraform plan -var="project_id=YOUR_PROJECT_ID"
```

**Expected resources:**
- 1 GCS bucket (~30MB for testing)
- 1 BigQuery dataset
- 1 BigQuery table (partitioned + clustered)

### Step 3: Apply Infrastructure

```bash
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

**Type `yes` when prompted.**

**Note the outputs:**
```
Outputs:
bucket_name = "github-activity-batch-raw-xxx"
bq_dataset_id = "github_activity"
bq_table_id = "github_activity.github_events"
```

### Step 4: Start Airflow

```bash
cd ..
make airflow-up
```

**Wait ~2 minutes for all containers to start.**

**Access Airflow:**
- URL: http://localhost:8080
- Username: `admin`
- Password: `admin`

**⚠️ Change default password after first login!**

---

## ▶️ Running the Pipeline

### Option 1: Manual Trigger (Recommended for Testing)

1. Open Airflow UI (http://localhost:8080)
2. Toggle DAG to **Active**
3. Click **Play button** (Trigger DAG)
4. Set execution date: `2024-01-15` (or any date)
5. Click **Trigger**

**Runtime:** ~15-30 minutes for 1 day of data

### Option 2: CLI Trigger

```bash
# Trigger for specific date
airflow dags trigger github_activity_batch_pipeline \
  --conf '{"execution_date": "2024-01-15"}'
```

### Monitor Progress

1. Click on the DAG in Airflow UI
2. Watch task colors:
   - ⚪ White: Queued
   - 🟡 Yellow: Running
   - 🟢 Green: Success
   - 🔴 Red: Failed

### Verify Data Loaded

```bash
# Count events for the day
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM github_activity.github_events
   WHERE event_date = '2024-01-15'"

# Expected: 50,000-200,000 events
```

---

## 📊 Dashboard Setup

### Create Looker Studio Dashboard

1. Go to https://lookerstudio.google.com/
2. Click **"Create" → "Report"**
3. Select **BigQuery** connector
4. Choose your project: `github-activity-batch-pipeline`
5. Select dataset: `github_activity`
6. Select table: `daily_stats`

### Tile 1: Event Type Distribution

1. Click **"Add chart" → "Pie chart"**
2. Dimension: `event_type`
3. Metric: `COUNT(event_id)`
4. Filter: `event_date = 2024-01-15`
5. Title: "Events by Type"

### Tile 2: Activity Over Time

1. Click **"Add chart" → "Time series"**
2. Dimension: `event_hour`
3. Metric: `COUNT(event_id)`
4. Filter: `event_date = 2024-01-15`
5. Title: "Hourly Activity"

**See `looker/dashboard_config.md` for detailed dashboard specifications.**

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

### Monitor Costs

```bash
# Check BigQuery storage size
bq show --format=prettyjson github_activity.github_events | \
  jq '.numBytes' | \
  awk '{print $1/1024/1024 " MB"}'

# Check GCS storage
gsutil du -sh gs://github-activity-batch-raw-<project_id>/
```

### Reduce Costs

1. **Always use partition filters:**
   ```sql
   -- ✅ GOOD
   SELECT * FROM github_activity.github_events
   WHERE event_date = '2024-01-15'

   -- ❌ BAD (scans entire table)
   SELECT * FROM github_activity.github_events
   ```

2. **Delete test data between runs:**
   ```bash
   bq rm -f github_activity.github_events
   gsutil -m rm -r gs://github-activity-batch-raw-<project_id>/raw/*
   ```

3. **Keep DAG inactive** when not testing

---

## 🔧 Troubleshooting

See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for detailed solutions.

### Common Issues

**DAG not appearing:**
```bash
# Check file location
ls -la airflow/dags/

# Restart scheduler
docker compose restart airflow-scheduler
```

**Authentication errors:**
```bash
# Verify credentials
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# Test access
gcloud auth list
gcloud config set project github-activity-batch-pipeline
```

**Docker issues:**
```bash
# Check containers
docker compose ps

# View logs
docker compose logs airflow-scheduler

# Restart
docker compose down
docker compose up -d
```

---

## 📁 Project Structure

```
github-activity-batch-pipeline/
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # GCS + BigQuery resources
│   ├── variables.tf       # Configuration
│   └── outputs.tf         # Resource outputs
├── airflow/
│   └── dags/
│       └── github_activity_pipeline.py  # 5-task DAG
├── dbt/
│   ├── dbt_project.yml
│   └── models/
│       ├── staging/stg_github_events.sql
│       └── marts/
│           ├── daily_stats.sql
│           └── repo_health.sql
├── looker/
│   └── dashboard_config.md  # Dashboard specifications
├── tests/                  # Pytest test suites
│   ├── test_airflow_dag.py
│   ├── test_terraform.py
│   └── test_dbt_models.py
├── scripts/                # Validation scripts
│   ├── validate_terraform.sh
│   ├── validate_airflow.sh
│   └── validate_dbt.sh
├── keys/                   # Service account keys (NOT in git!)
│   └── gcp-creds.json
├── .env                    # Environment variables (NOT in git!)
├── .env.example            # Template
├── .gitignore              # Git ignore rules
├── docker-compose.yml      # Airflow stack
├── Makefile                # Common commands
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── architecture.md         # System architecture
├── CHECKLIST.md            # Deployment checklist
├── TROUBLESHOOTING.md      # Troubleshooting guide
└── BUDGET_DEPLOYMENT.md    # Budget-conscious deployment
```

---

## 📝 Makefile Commands

```bash
make help              # Show all commands
make quickstart        # Quick setup (terraform init + airflow up)
make deploy            # Full deployment pipeline
make airflow-up        # Start Airflow
make airflow-down      # Stop Airflow
make terraform-init    # Initialize Terraform
make terraform-apply   # Apply Terraform
make dbt-run           # Run dbt models
make dbt-test          # Run dbt tests
make test              # Run all pytest tests
make validate          # Run all validation scripts
```

---

## 🎯 Requirements Coverage (28/28 Points)

| Requirement | Status | Details |
|-------------|--------|---------|
| Problem description | ✅ | This README + architecture.md |
| Cloud + IaC | ✅ | Terraform: GCS + BigQuery |
| Data ingestion | ✅ | Airflow DAG with 5 tasks |
| Data warehouse | ✅ | BigQuery partitioned + clustered |
| Transformations | ✅ | dbt: 1 staging + 2 marts |
| Dashboard | ✅ | Looker Studio: 2 tiles |
| Reproducibility | ✅ | README, Makefile, docker-compose |

---

## 📄 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- Data source: [GHE Archive](https://gharchive.org)
- Course: [Data Engineering Zoomcamp 2026](https://github.com/DataTalksClub/data-engineering-zoomcamp)

---

**Ready to deploy?** Follow the [Quick Start](#quick-start-5-minutes) or [Detailed Setup](#detailed-setup-guide)!
