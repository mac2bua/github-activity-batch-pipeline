# Looker Studio Dashboard Specification
## AI Coding Agent Activity Dashboard - DE Zoomcamp 2026

## Dashboard Overview
- **Title:** AI Coding Agent Contributions on GitHub
- **Data Source:** BigQuery `github_activity.ai_agent_stats` + `github_activity.daily_stats` + `github_activity.ai_ratio_timeline`
- **Refresh:** Daily
- **Default Date Range:** Last 30 days
- **Focus:** Track AI coding agent (Copilot, Claude, Cursor, etc.) contributions to open source

---

## Key Metrics (Score Cards)

| Tile | Metric | Data Source |
|------|--------|-------------|
| Total AI Events | `SUM(total_events)` | ai_agent_stats |
| Unique AI Agents | `COUNT(DISTINCT actor_type)` | ai_agent_stats |
| Repos Touched by AI | `SUM(repos_touched)` | ai_agent_stats |
| AI Contribution Ratio | `AI events / Total events` | combined |

---

## Tile 1: AI Agent Activity Distribution

**Type:** Donut Chart

| Setting | Value |
|---------|-------|
| Dimension | `actor_type` |
| Metric | `SUM(total_events)` |
| Sort | Descending by count |

**Purpose:** Show which AI coding agents are most active on GitHub

**Insight:** Copilot dominates, but CI/CD bots (github-actions, renovate) are significant

---

## Tile 2: AI Agent Activity Timeline

**Type:** Time Series Line Chart

| Setting | Value |
|---------|-------|
| Dimension | `stats_date` |
| Metric | `SUM(total_events)` |
| Breakdown | `actor_type` |
| Granularity | Day |
| Smoothing | 7-day moving average |

**Purpose:** Track adoption trends of different AI coding agents over time

---

## Tile 3: Top AI-Touched Repositories

**Type:** Horizontal Bar Chart

**Data Source:** `stg_github_events` (filtered: `is_ai_agent = true`)

| Setting | Value |
|---------|-------|
| Dimension | `repo_name` |
| Metric | `COUNT(*)` |
| Sort | Top 20 by count |

**Purpose:** Identify which open-source projects receive the most AI contributions

---

## Tile 4: AI Adoption Over Time (NEW)

**Type:** Time Series Line Chart

**Data Source:** `ai_ratio_timeline`

| Setting | Value |
|---------|-------|
| Dimension | `event_date` |
| Metric | `ai_percentage` |
| Style | Show as percentage (0-100 scale) |
| Reference Line | 20% baseline |

**Purpose:** Show the trend of AI contribution percentage over time

**Insight:** Track how AI adoption is growing in open source development

---

## Tile 5: AI vs Human Ratio

**Type:** Gauge Chart

**Data Source:** `ai_ratio_timeline`

```sql
SELECT
  SUM(ai_events) as ai_events,
  SUM(human_events) as human_events,
  ROUND(SUM(ai_events) * 100.0 / SUM(total_events), 2) as ai_ratio
FROM `github_activity.ai_ratio_timeline`
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```

**Purpose:** Show the proportion of GitHub activity from AI agents (last 7 days)

---

## Tile 6: Event Type Breakdown by Agent

**Type:** Stacked Bar Chart

| Setting | Value |
|---------|-------|
| Dimension | `actor_type` |
| Metrics | `push_events`, `pr_events`, `comment_events`, `star_events` |
| Stack | 100% stacked |

**Purpose:** Understand what types of activities each AI agent performs

---

## Tile 7: Activity Heatmap (IMPROVED)

**Type:** Heatmap Grid

**Data Source:** `stg_github_events` (filtered: `is_ai_agent = true`)

| Setting | Value |
|---------|-------|
| Rows | `actor_type` |
| Columns | `EXTRACT(HOUR FROM created_at)` (0-23) |
| Metric | `COUNT(*)` |
| Color Scale | Gradient (light to dark based on count) |

**Purpose:** Show when AI agents are most active (hourly patterns)

**Visual Design:**
- X-axis: Hours 0-23
- Y-axis: Agent types (Copilot, Claude, Cursor, CI/CD Bot, etc.)
- Cell color intensity: Event count (darker = more active)

---

## Dashboard Controls

1. **Date Range Picker** - Default: Last 7 days (for clean time-series)
2. **Agent Type Filter** - Multi-select: Copilot, Claude, Cursor, CodeRabbit, Lovable, Dependabot, CI/CD Bot, Other Bot
3. **Repository Filter** - Multi-select dropdown
4. **Event Type Filter** - Multi-select: Push, PR, Issues, etc.

---

## Data Requirements

### BigQuery Tables

| Table | Purpose |
|-------|---------|
| `ai_agent_stats` | Primary source for AI agent metrics |
| `ai_ratio_timeline` | Time-series for AI adoption trend |
| `stg_github_events` | Raw events for detailed analysis |
| `daily_stats` | Overall activity context |

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| stats_date | DATE | Partition date |
| actor_type | STRING | AI agent classification |
| total_events | INT64 | Event count |
| unique_agents | INT64 | Unique agent accounts |
| repos_touched | INT64 | Unique repositories |
| push_events | INT64 | Push event count |
| pr_events | INT64 | PR event count |
| avg_activity_hour | FLOAT64 | Average activity hour |

---

## Sample Queries

### AI Agent Event Distribution (Last 30 Days)

```sql
SELECT
  actor_type,
  SUM(total_events) as total_events,
  SUM(unique_agents) as unique_agents,
  SUM(repos_touched) as repos_touched
FROM `github_activity.ai_agent_stats`
WHERE stats_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY actor_type
ORDER BY total_events DESC
```

### AI Adoption Timeline

```sql
SELECT
  event_date,
  ai_percentage,
  ai_events,
  human_events,
  copilot_events,
  claude_events,
  cicd_events
FROM `github_activity.ai_ratio_timeline`
ORDER BY event_date
```

### AI vs Human Ratio (Last 7 Days)

```sql
SELECT
  actor_type,
  COUNT(*) as events,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM `github_activity.stg_github_events`
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY actor_type
ORDER BY events DESC
```

### Top AI-Touched Repos

```sql
SELECT
  repo_name,
  COUNT(*) as ai_events,
  COUNT(DISTINCT actor_login) as unique_agents
FROM `github_activity.stg_github_events`
WHERE is_ai_agent = true
  AND event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY repo_name
ORDER BY ai_events DESC
LIMIT 20
```

---

## Implementation Steps

1. **Create Data Source**
   - Connect Looker Studio to BigQuery
   - Select `github_activity` dataset
   - Add `ai_agent_stats`, `ai_ratio_timeline`, and `stg_github_events` tables

2. **Add Score Cards**
   - Create 4 score cards at top
   - Use blended data for AI ratio

3. **Create Charts**
   - Add each tile following specifications above
   - Apply consistent color scheme

4. **Add Filters**
   - Date range control
   - Agent type dropdown
   - Repository filter

5. **Style Dashboard**
   - Use dark theme (professional look)
   - Add logo/branding
   - Include refresh timestamp

---

## Actor Type Classification

### AI Coding Agents (Strict Matching)
| Actor Type | Bot Accounts |
|------------|--------------|
| Copilot | `Copilot`, `copilot[bot]`, `github-copilot[bot]` |
| Claude | `claude[bot]` |
| Cursor | `cursor[bot]` |
| CodeRabbit | `coderabbitai[bot]`, `coderabbitai-qa[bot]`, `coderabbitaidev[bot]` |
| Lovable | `lovable-dev[bot]` |
| Dependabot | `dependabot*` (wildcard) |

### CI/CD Bots (Grouped)
| Actor Type | Bot Accounts |
|------------|--------------|
| CI/CD Bot | `github-actions[bot]`, `renovate[bot]`, `vercel[bot]`, `pull[bot]`, `swa-runner-app[bot]` |

### Other
| Actor Type | Pattern |
|------------|---------|
| Other Bot | Any account ending in `[bot]` not classified above |
| Human | All other accounts |