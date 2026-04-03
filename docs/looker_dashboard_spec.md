# Looker Studio Dashboard Specification
## GitHub Activity Batch Pipeline - DE Zoomcamp 2026

## Dashboard Overview
- **Data Source:** BigQuery `gh_activity_dev.github_events`
- **Refresh:** Daily
- **Default Date Range:** Last 30 days

---

## Tile 1: Categorical (Event Type Distribution)

**Type:** Pie Chart / Donut Chart

| Setting | Value |
|---------|-------|
| Dimension | `standardized_event_type` |
| Metric | `COUNT(id)` |
| Sort | Descending by count |
| Limit | Top 10 types |

**Purpose:** Show distribution of GitHub activity types (push, PR, issues, stars, forks)

---

## Tile 2: Temporal (Activity Over Time)

**Type:** Time Series Line Chart

| Setting | Value |
|---------|-------|
| Dimension | `date_partition` |
| Metric 1 | `COUNT(id)` (Total Events) |
| Metric 2 | `COUNT(DISTINCT actor_login)` (Active Users) |
| Granularity | Day |
| Smoothing | 7-day moving average |

**Purpose:** Track activity trends and identify peak periods

---

## Dashboard Controls

1. **Date Range Picker** - Default: Last 30 days
2. **Repository Filter** - Multi-select dropdown
3. **Event Type Filter** - Multi-select dropdown

---

## BigQuery Fields Required

| Field | Type | Description |
|-------|------|-------------|
| id | STRING | Event ID |
| standardized_event_type | STRING | Normalized type |
| actor_login | STRING | Username |
| repo_name | STRING | Repository |
| date_partition | DATE | Partition date |
