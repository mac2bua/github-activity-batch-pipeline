-- Staging model for GitHub events
-- Cleans and normalizes raw GitHub activity data

{{
    config(
        materialized='view',
        tags=['staging', 'github']
    )
}}

with source as (
    select * from {{ source('github', 'github_events') }}
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
        end as is_valid_repo,

        -- AI Agent Detection (strict matching - no false positives)
        -- Only classify as AI agent if it's a verified bot account
        case
            -- Known AI coding agents (exact matches only)
            when actor_login in ('Copilot', 'copilot[bot]', 'github-copilot[bot]') then true
            when actor_login = 'claude[bot]' then true
            when actor_login = 'cursor[bot]' then true
            when actor_login in ('coderabbitai[bot]', 'coderabbitai-qa[bot]', 'coderabbitaidev[bot]') then true
            when actor_login = 'lovable-dev[bot]' then true
            when actor_login like 'dependabot%' then true
            -- CI/CD and automation bots
            when actor_login in ('github-actions[bot]', 'renovate[bot]', 'vercel[bot]', 'pull[bot]', 'swa-runner-app[bot]') then true
            -- All other bots with [bot] suffix
            when actor_login like '%[bot]' then true
            else false
        end as is_ai_agent,

        -- Actor type classification (strict matching to avoid false positives)
        case
            -- AI Coding Agents (verified bot accounts only)
            when actor_login in ('Copilot', 'copilot[bot]', 'github-copilot[bot]') then 'Copilot'
            when actor_login = 'claude[bot]' then 'Claude'
            when actor_login = 'cursor[bot]' then 'Cursor'
            when actor_login in ('coderabbitai[bot]', 'coderabbitai-qa[bot]', 'coderabbitaidev[bot]') then 'CodeRabbit'
            when actor_login = 'lovable-dev[bot]' then 'Lovable'
            when actor_login like 'dependabot%' then 'Dependabot'

            -- CI/CD Bots (grouped category)
            when actor_login in ('github-actions[bot]', 'renovate[bot]', 'vercel[bot]', 'pull[bot]', 'swa-runner-app[bot]') then 'CI/CD Bot'

            -- Other automation with [bot] suffix
            when actor_login like '%[bot]' then 'Other Bot'

            else 'Human'
        end as actor_type

    from source
    where event_date is not null
)

select * from cleaned
where is_valid_event = true
