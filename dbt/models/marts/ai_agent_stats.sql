-- AI Agent Statistics Mart Model
-- Aggregates activity metrics by AI agent type per day
-- Supports AI coding agent analytics dashboard

{{
    config(
        materialized='table',
        partition_by={
            'field': 'stats_date',
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['actor_type'],
        tags=['marts', 'ai_agents']
    )
}}

with ai_events as (
    select
        event_date as stats_date,
        actor_type,
        actor_login,
        repo_name,
        event_type,
        created_at,
        is_ai_agent
    from {{ ref('stg_github_events') }}
    where is_ai_agent = true
),

daily_agent_stats as (
    select
        stats_date,
        actor_type,

        -- Counts
        count(*) as total_events,
        count(distinct actor_login) as unique_agents,
        count(distinct repo_name) as repos_touched,

        -- Event breakdown
        countif(event_type = 'PushEvent') as push_events,
        countif(event_type = 'PullRequestEvent') as pr_events,
        countif(event_type = 'IssueCommentEvent') as comment_events,
        countif(event_type = 'WatchEvent') as star_events,
        countif(event_type = 'ForkEvent') as fork_events,

        -- Activity patterns
        avg(extract(hour from created_at)) as avg_activity_hour,

        -- Ratios
        safe_divide(countif(event_type = 'PushEvent'), count(*)) as push_ratio,
        safe_divide(countif(event_type = 'PullRequestEvent'), count(*)) as pr_ratio

    from ai_events
    group by stats_date, actor_type
)

select * from daily_agent_stats