-- Mart: Repository Health Metrics
-- Repository-level activity and health indicators

{{
    config(
        materialized='table',
        partition_by={
            "field": "snapshot_date",
            "data_type": "date",
            "granularity": "day"
        },
        cluster_by=['repo_owner', 'repo_name_parsed'],
        tags=['mart', 'repository', 'health']
    )
}}

with stg_events as (
    select * from {{ ref('stg_github_events') }}
),

repo_daily_activity as (
    select
        event_date as snapshot_date,
        repo_owner_parsed as repo_owner,
        repo_name_parsed as repo_name,
        concat(repo_owner_parsed, '/', repo_name_parsed) as repo_full_name,
        event_type,
        
        count(*) as daily_events,
        count(distinct actor_login) as daily_contributors,
        
    from stg_events
    where repo_name_parsed is not null
    group by event_date, repo_owner_parsed, repo_name_parsed, event_type
),

repo_aggregates as (
    select
        snapshot_date,
        repo_owner,
        repo_name,
        repo_full_name,
        
        -- Activity volume
        sum(daily_events) as total_events,
        sum(case when event_type = 'PushEvent' then daily_events else 0 end) as push_events,
        sum(case when event_type = 'PullRequestEvent' then daily_events else 0 end) as pr_events,
        sum(case when event_type = 'IssueCommentEvent' then daily_events else 0 end) as comment_events,
        sum(case when event_type = 'WatchEvent' then daily_events else 0 end) as watch_events,
        sum(case when event_type = 'ForkEvent' then daily_events else 0 end) as fork_events,
        
        -- Contributor metrics
        sum(daily_contributors) as total_contributor_activity,
        count(distinct case when event_type = 'PushEvent' then concat(snapshot_date, repo_full_name) end) as days_with_pushes,
        
        -- Time-based patterns
        avg(daily_events) as avg_daily_events,
        stddev(daily_events) as event_volatility,
        max(daily_events) as peak_daily_events
        
    from repo_daily_activity
    group by snapshot_date, repo_owner, repo_name, repo_full_name
),

health_scores as (
    select
        *,
        
        -- Activity health score (0-100)
        case
            when total_events = 0 then 0
            when total_events < 10 then 20
            when total_events < 50 then 40
            when total_events < 100 then 60
            when total_events < 500 then 80
            else 100
        end as activity_score,
        
        -- Diversity score (based on event types)
        case
            when (push_events + pr_events + comment_events) = 0 then 0
            else safe_divide(
                (case when push_events > 0 then 1 else 0 end) +
                (case when pr_events > 0 then 1 else 0 end) +
                (case when comment_events > 0 then 1 else 0 end) +
                (case when watch_events > 0 then 1 else 0 end) +
                (case when fork_events > 0 then 1 else 0 end),
                5
            ) * 100
        end as diversity_score,
        
        -- Consistency score (inverse of volatility)
        case
            when avg_daily_events = 0 then 0
            else greatest(0, 100 - (safe_divide(event_volatility, avg_daily_events) * 100))
        end as consistency_score
        
    from repo_aggregates
)

select
    *,
    
    -- Overall health score (weighted average)
    round(
        (activity_score * 0.4) +
        (diversity_score * 0.3) +
        (consistency_score * 0.3),
        2
    ) as overall_health_score,
    
    -- Health classification
    case
        when overall_health_score >= 80 then 'Healthy'
        when overall_health_score >= 50 then 'Moderate'
        when overall_health_score >= 20 then 'At Risk'
        else 'Critical'
    end as health_status
    
from health_scores
order by snapshot_date desc, overall_health_score desc
