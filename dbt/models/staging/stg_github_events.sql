-- Staging model for GitHub events
-- Cleans and normalizes raw GitHub activity data

{{
    config(
        materialized='view',
        tags=['staging', 'github']
    )
}}

with source as (
    select * from {{ source('github_activity', 'github_events') }}
),

cleaned as (
    select
        -- Unique identifiers
        event_id,
        event_type,
        
        -- Actor information
        actor_login,
        lower(actor_login) as actor_login_lower,
        
        -- Repository information
        repo_name,
        repo_owner,
        split(repo_name, '/')[offset(0)] as repo_owner_parsed,
        split(repo_name, '/')[safe_offset(1)] as repo_name_parsed,
        
        -- Temporal fields
        created_at,
        event_date,
        date_trunc(event_date, week) as event_week,
        date_trunc(event_date, month) as event_month,
        extract(hour from created_at) as event_hour,
        extract(dayofweek from created_at) as day_of_week,
        
        -- Event metadata
        payload,
        public,
        loaded_at,
        
        -- Data quality flags
        case 
            when event_id is null or event_id = '' then false 
            else true 
        end as is_valid_event,
        
        case 
            when actor_login is null or actor_login = '' then false 
            else true 
        end as is_valid_actor,
        
        case 
            when repo_name is null or repo_name = '' then false 
            else true 
        end as is_valid_repo
        
    from source
    where event_date is not null
)

select * from cleaned
where is_valid_event = true
