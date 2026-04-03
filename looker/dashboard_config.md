# Looker Studio Dashboard Configuration

## Data Source Connection

**Connector**: BigQuery
**Project**: `<your-project-id>`
**Dataset**: `github_activity`
**Tables**: 
- `daily_stats` (primary)
- `repo_health` (secondary)

---

## Tile 1: Categorical Analysis

### Chart 1.1: Event Type Distribution
- **Type**: Pie Chart
- **Dimension**: `event_type`
- **Metric**: `total_events` (SUM)
- **Filter**: `stats_date` = Last 30 days
- **Sort**: `total_events` DESC

### Chart 1.2: Top 10 Repositories by Activity
- **Type**: Bar Chart (Horizontal)
- **Dimension**: `repo_name` (from repo_health)
- **Metric**: `total_events` (SUM)
- **Filter**: 
  - `snapshot_date` = Last 30 days
  - Limit: 10
- **Sort**: `total_events` DESC
- **Color**: By `health_status`

### Chart 1.3: Top Contributors Table
- **Type**: Table
- **Dimensions**: `actor_login` (from daily_stats via join)
- **Metrics**: 
  - `unique_actors` (COUNT DISTINCT)
  - `total_events` (SUM)
- **Filter**: Last 30 days
- **Sort**: `total_events` DESC
- **Limit**: 20

---

## Tile 2: Temporal Analysis

### Chart 2.1: Daily Activity Trend
- **Type**: Time Series Line Chart
- **Dimension**: `stats_date`
- **Metric**: `total_daily_events` (SUM)
- **Date Range**: Last 90 days
- **Breakdown**: `event_type` (color)
- **Reference Line**: Average (90-day)

### Chart 2.2: Hourly Activity Heatmap
- **Type**: Pivot Table with Color Scale
- **Row Dimension**: `day_of_week` (from stg_github_events)
- **Column Dimension**: `event_hour` (0-23)
- **Metric**: `total_events` (COUNT)
- **Color Scale**: Blue (low) → Red (high)
- **Filter**: Last 30 days

### Chart 2.3: Weekday vs Weekend Comparison
- **Type**: Scorecard Comparison
- **Metric 1**: `weekday_events` (SUM) / Label: "Weekday"
- **Metric 2**: `weekend_events` (SUM) / Label: "Weekend"
- **Comparison**: Show % difference
- **Date Range**: Last 30 days

### Chart 2.4: Repository Health Trend
- **Type**: Area Chart
- **Dimension**: `snapshot_date`
- **Metric**: `overall_health_score` (AVG)
- **Breakdown**: `health_status` (stacked)
- **Date Range**: Last 90 days

---

## Dashboard Filters (Global)

1. **Date Range Control**
   - Default: Last 30 days
   - Range: 7 days - 1 year

2. **Event Type Filter**
   - Type: Dropdown (multi-select)
   - Values: All event types from data

3. **Repository Owner Filter**
   - Type: Dropdown (multi-select)
   - Values: Distinct `repo_owner`

4. **Health Status Filter**
   - Type: Dropdown
   - Values: Healthy, Moderate, At Risk, Critical

---

## Styling Guidelines

- **Theme**: Light background
- **Primary Color**: GitHub purple (#6f42c1)
- **Secondary Colors**: 
  - Success: Green (#28a745)
  - Warning: Yellow (#ffc107)
  - Danger: Red (#dc3545)
- **Font**: System default (clean, readable)
- **Grid**: 12-column layout

---

## Layout

```
┌─────────────────────────────────────────────────────┐
│  Dashboard Title: GitHub Activity Overview          │
│  [Date Filter] [Event Type] [Repo Owner]            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │             │  │                             │  │
│  │  Pie Chart  │  │    Line Chart (Trend)       │  │
│  │  (Events)   │  │    (Daily Activity)         │  │
│  │             │  │                             │  │
│  └─────────────┘  └─────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │                                               │  │
│  │    Horizontal Bar Chart (Top Repos)           │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │             │  │                             │  │
│  │  Heatmap    │  │    Area Chart (Health)      │  │
│  │  (Hourly)   │  │    (Repo Health Trend)      │  │
│  │             │  │                             │  │
│  └─────────────┘  └─────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │                                               │  │
│  │    Scorecards: Weekday vs Weekend             │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │                                               │  │
│  │    Table: Top Contributors                    │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Sharing & Permissions

- **View Access**: All team members
- **Edit Access**: Data Engineering team only
- **Schedule Email Report**: Weekly (Monday 9:00 AM)
- **Export Formats**: PDF, PNG, CSV (for tables)
