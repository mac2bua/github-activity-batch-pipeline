# Budget Deployment Guide (Max €5)

## 🎯 Strategy: Start Tiny, Scale Later

**Phase 1**: 1 day of data → Verify pipeline works (Cost: <€0.01)
**Phase 2**: 1 week of data → Test partitioning (Cost: <€0.10)
**Phase 3**: 1 month of data → Full dashboard (Cost: <€0.50)
**Phase 4**: Production (3-6 months) → Monitor costs (Cost: €1-3/month)

---

## 📊 BigQuery Free Tier (Key!)

BigQuery includes **1TB of queries FREE per month**. This is your best friend.

| What | Free Tier | Your Usage (1 day) |
|------|-----------|-------------------|
| Queries | 1TB/month | ~100MB |
| Storage | 10GB | ~30MB |
| Load jobs | 1/month free | 1 |

**Partition pruning is critical**: Always filter by `event_date` to avoid full table scans.

---

## 🛡️ Budget Controls

### 1. Set BigQuery Budget Alerts

```bash
# Create budget alert at €1
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="GitHub Activity - €1 Alert" \
  --amount=1 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

**Do this FIRST before any deployment!**

### 2. Use Partition Filters ALWAYS

```sql
-- ✅ GOOD: Uses partition pruning (~100MB scanned)
SELECT * FROM github_activity.github_events
WHERE event_date = '2024-01-15'

-- ❌ BAD: Full table scan (costs money)
SELECT * FROM github_activity.github_events
```

### 3. Manual DAG Execution (No Auto-Schedule)

Don't enable auto-schedule initially. Run manually for specific dates:

```python
# In Airflow UI: Trigger DAG with config
{
    "execution_date": "2024-01-15",
    "hours": [0, 1, 2, ..., 23]  # All 24 hours
}
```

### 4. Delete Resources Between Tests (Optional)

If you want to test multiple times:

```bash
# Delete BigQuery table (keeps schema)
bq rm -f github_activity.github_events

# Empty GCS bucket
gsutil -m rm -r gs://github-activity-batch-raw-<project_id>/raw/*

# Re-run DAG
```

---

## 🚀 Phase 1: 1 Day Deployment (<€0.01)

### Step 1: Set Budget Alert (5 min)

```bash
# Get your billing account
gcloud billing accounts list

# Create €1 budget alert
gcloud billing budgets create \
  --billing-account=XXXXXX-YYYYYY-ZZZZZZ \
  --display-name="GitHub Activity Budget" \
  --amount=1 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

### Step 2: Deploy Infrastructure (10 min)

```bash
cd ~/Repositories/github-activity-batch-pipeline

# Edit .env
cp .env.example .env
# Edit: GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS

# Terraform (creates GCS + BigQuery)
cd terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"

# Note outputs:
# - bucket_name
# - bq_dataset_id
# - bq_table_id
```

### Step 3: Start Airflow (5 min)

```bash
cd ..
make airflow-up
# Access: http://localhost:8080 (admin/admin)
```

### Step 4: Configure DAG Variables (2 min)

In Airflow UI:
1. Admin → Variables
2. Create:
   - `project_id` = `YOUR_PROJECT_ID`
   - `gcs_bucket` = `github-activity-batch-raw-YOUR_PROJECT_ID`
   - `bq_dataset` = `github_activity`
   - `target_date` = `2024-01-15`  # ← Single day!

### Step 5: Run DAG for 1 Day (30 min)

In Airflow UI:
1. Toggle DAG to **Active**
2. Click **Play** button (trigger manually)
3. Wait for all 5 tasks to complete

**Expected runtime:** 15-30 minutes

### Step 6: Verify Data Loaded (2 min)

```bash
# Check table exists
bq show github_activity.github_events

# Check row count for the day
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM github_activity.github_events 
   WHERE event_date = '2024-01-15'"

# Expected: ~50,000-200,000 events (varies by day)
```

### Step 7: Run dbt Models (5 min)

```bash
make dbt-build

# Verify models created
bq show github_activity.daily_stats
bq show github_activity.repo_health
```

### Step 8: Create Looker Dashboard (15 min)

1. Go to https://lookerstudio.google.com/
2. Create new report → BigQuery connector
3. Select dataset: `github_activity`
4. Create Tile 1: Event type pie chart
   - Dimension: `event_type`
   - Metric: `COUNT(event_id)`
   - Filter: `event_date = 2024-01-15`
5. Create Tile 2: Hourly trend
   - Dimension: `event_hour`
   - Metric: `COUNT(event_id)`
   - Filter: `event_date = 2024-01-15`

---

## ✅ Phase 1 Success Criteria

- [ ] Budget alert created (€1)
- [ ] Terraform applied successfully
- [ ] Airflow DAG runs without errors
- [ ] Data loaded to BigQuery (1 day)
- [ ] dbt models created successfully
- [ ] Looker dashboard shows data
- [ ] **Total spent: <€0.01**

---

## 📈 Phase 2: 1 Week (<€0.10)

Once Phase 1 works, expand to 1 week:

```bash
# Update target_date range
# In Airflow DAG, set:
start_date = "2024-01-15"
end_date = "2024-01-21"  # 7 days

# Trigger DAG
# Wait ~2-3 hours for completion
```

**Cost:** ~€0.05-0.10 (still negligible)

---

## 📊 Phase 3: 1 Month (<€0.50)

```bash
# Full month
start_date = "2024-01-01"
end_date = "2024-01-31"
```

**Cost:** ~€0.30-0.50

---

## 🎯 Cost Monitoring Commands

```bash
# Check BigQuery storage size
bq show --format=prettyjson github_activity.github_events | \
  jq '.numBytes' | \
  awk '{print $1/1024/1024 " MB"}'

# Check query costs (last 7 days)
# Go to: https://console.cloud.google.com/bigquery/quotas

# Check GCS storage
gsutil du -sh gs://github-activity-batch-raw-<project_id>/
```

---

## 🚨 If Costs Exceed Expectations

### Immediate Actions:

1. **Pause DAG**: Toggle to Inactive in Airflow
2. **Delete BigQuery table**: 
   ```bash
   bq rm -f github_activity.github_events
   ```
3. **Empty GCS bucket**:
   ```bash
   gsutil -m rm -r gs://github-activity-batch-raw-<project_id>/raw/*
   ```
4. **Review what went wrong**

### Common Cost Issues:

| Issue | Symptom | Fix |
|-------|---------|-----|
| No partition filter | Query scans TBs | Always add `WHERE event_date = ...` |
| Auto-schedule enabled | DAG runs daily | Toggle to Inactive |
| SELECT * in queries | Scans full table | Select specific columns |
| No budget alert | Surprise costs | Create alert immediately |

---

## 💡 Pro Tips

1. **Use BigQuery Sandbox** (if available): Completely free, no credit card needed
   - Limit: 10GB storage, 1TB queries/month
   - Perfect for testing!

2. **Test with 1 hour first**: Before running 24 hours, test with 1 hour
   ```python
   # In DAG config
   "hours": [12]  # Just noon data
   ```

3. **Use bq estimate before running**:
   ```bash
   bq query --use_legacy_sql=false --dry_run \
     "SELECT COUNT(*) FROM github_activity.github_events 
      WHERE event_date = '2024-01-15'"
   # Shows bytes processed before running
   ```

4. **Keep Terraform state local**: Don't use remote state (adds complexity, no cost benefit for testing)

---

## 📝 Checklist: Before First Run

- [ ] Budget alert created (€1)
- [ ] BigQuery Sandbox enabled (if available)
- [ ] `.env` configured with correct project ID
- [ ] Terraform outputs noted
- [ ] Airflow variables set
- [ ] `target_date` set to single day (e.g., `2024-01-15`)
- [ ] DAG toggle set to **Inactive** (manual trigger only)
- [ ] Looker Studio ready for dashboard creation

---

## 🎉 Expected Total Cost

| Phase | Data | Runtime | Cost |
|-------|------|---------|------|
| **Phase 1** | 1 day | 30 min | <€0.01 |
| **Phase 2** | 1 week | 2-3 hours | <€0.10 |
| **Phase 3** | 1 month | 8-12 hours | <€0.50 |
| **Buffer** | Retries, tests | - | €0.39 |
| **TOTAL** | | | **€1.00** |

**Well under your €5 budget!** 🎯

---

**Ready to start? Run Phase 1 and report back!**
