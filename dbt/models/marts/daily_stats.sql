-- Mart: Daily GitHub Activity Statistics
-- Aggregated daily metrics for dashboard consumption

{{
    config(
        materialized='table',
        partition_by={
            "field": "stats_date",
            "data_type": "date",
            "granularity": "day"
        },
        cluster_by=['event_type'],
        tags=['mart', 'daily', 'statistics']
    )
}}

with stg_events as (
    select * from {{ ref('stg_github_events') }}
),

daily_aggregates as (
    select
        event_date as stats_date,
        event_type,
        
        -- Count metrics
        count(*) as total_events,
        count(distinct actor_login) as unique_actors,
        count(distinct repo_name) as unique_repos,
        count(distinct repo_owner_parsed) as unique_owners,
        
        -- Time-based metrics
        min(created_at) as first_event_at,
        max(created_at) as last_event_at,
        
        -- Activity distribution
        sum(case when event_hour between 9 and 17 then 1 else 0 end) as business_hours_events,
        sum(case when event_hour not between 9 and 17 then 1 else 0 end) as off_hours_events,
        sum(case when day_of_week in (1, 7) then 1 else 0 end) as weekend_events,
        sum(case when day_of_week not in (1, 7) then 1 else 0 end) as weekday_events,
        
        -- Public vs private
        sum(case when public = true then 1 else 0 end) as public_events,
        sum(case when public = false then 1 else 0 end) as private_events
        
    from stg_events
    group by event_date, event_type
),

daily_totals as (
    select
        event_date as stats_date,
        
        count(*) as total_daily_events,
        count(distinct actor_login) as total_unique_actors,
        count(distinct repo_name) as total_unique_repos,
        count(distinct event_type) as event_type_diversity
        
    from stg_events
    group by event_date
)

select
    da.*,
    dt.total_daily_events,
    dt.total_unique_actors,
    dt.total_unique_repos,
    dt.event_type_diversity,
    
    -- Calculated metrics
    safe_divide(da.total_events, dt.total_daily_events) as event_type_share,
    safe_divide(da.unique_actors, dt.total_unique_actors) as actor_concentration,
    safe_divide(da.business_hours_events, da.total_events) as business_hours_ratio,
    safe_divide(da.weekend_events, da.total_events) as weekend_ratio
    
from daily_aggregates da
join daily_totals dt on da.stats_date = dt.stats_date
order by da.stats_date desc, da.total_events desc
