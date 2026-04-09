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

        -- AI Agent Detection
        -- Distinguishes between AI coding agents (write code) and automation bots (run tasks)
        case
            -- Known AI coding agents (write/review code, generate content)
            -- Claude appears as both "Claude" and "claude[bot]" depending on context
            when lower(actor_login) like 'claude%' then true
            when actor_login in ('Copilot', 'copilot[bot]', 'github-copilot[bot]', 'copilot-pull-request-review[bot]') then true
            when actor_login = 'cursor[bot]' then true
            when actor_login in ('coderabbitai[bot]', 'coderabbitai-qa[bot]', 'coderabbitaidev[bot]') then true
            when actor_login = 'lovable-dev[bot]' then true
            when actor_login in ('gemini[bot]', 'gemini-code-assist[bot]') then true
            when actor_login = 'chatgpt[bot]' then true
            else false
        end as is_ai_agent,

        -- Actor type classification
        -- Groups actors into meaningful categories for analytics
        case
            -- AI Coding Agents (write code, review PRs, generate content)
            -- Claude appears in multiple forms: "Claude" (app), "claude[bot]" (bot)
            when lower(actor_login) like 'claude%' then 'Claude'
            when actor_login in ('Copilot', 'copilot[bot]', 'github-copilot[bot]', 'copilot-pull-request-review[bot]') then 'Copilot'
            when actor_login = 'cursor[bot]' then 'Cursor'
            when actor_login in ('coderabbitai[bot]', 'coderabbitai-qa[bot]', 'coderabbitaidev[bot]') then 'CodeRabbit'
            when actor_login = 'lovable-dev[bot]' then 'Lovable'
            when actor_login in ('gemini[bot]', 'gemini-code-assist[bot]') then 'Gemini'
            when actor_login = 'chatgpt[bot]' then 'ChatGPT'

            -- Dependency Management
            when actor_login like 'dependabot%' then 'Dependabot'
            when actor_login in ('renovate[bot]', 'greenkeeper[bot]', 'pyup-bot', 'pyup%[bot]') then 'Dependabot'

            -- CI/CD & Automation
            when actor_login in ('github-actions[bot]', 'vercel[bot]', 'netlify[bot]', 'circleci[bot]', 'travis-ci[bot]') then 'CI/CD Bot'
            when actor_login in ('pull[bot]', 'mergify[bot]', 'pytorch-bot[bot]', 'kennethreitz-release-bot') then 'CI/CD Bot'

            -- Security & Quality
            when actor_login in ('snyk-bot', 'codecov-io[bot]', 'codecov[bot]', 'coveralls[bot]', 'imgbot', 'imgbot[bot]') then 'Security/Quality Bot'

            -- All other [bot] accounts
            when actor_login like '%[bot]' then 'Other Bot'

            else 'Human'
        end as actor_type

    from source
    where event_date is not null
)

select * from cleaned
where is_valid_event = true
