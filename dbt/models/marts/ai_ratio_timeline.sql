-- AI Adoption Timeline View
-- Daily aggregated AI vs Human ratio for time-series visualization

{{
    config(
        materialized='view',
        tags=['marts', 'ai_analysis']
    )
}}

SELECT
    event_date,
    COUNT(*) as total_events,
    COUNTIF(is_ai_agent = true) as ai_events,
    COUNTIF(is_ai_agent = false) as human_events,
    ROUND(SAFE_DIVIDE(COUNTIF(is_ai_agent = true), COUNT(*)) * 100, 2) as ai_percentage,

    -- Breakdown by AI agent type
    COUNTIF(actor_type = 'Copilot') as copilot_events,
    COUNTIF(actor_type = 'Claude') as claude_events,
    COUNTIF(actor_type = 'Cursor') as cursor_events,
    COUNTIF(actor_type = 'CodeRabbit') as coderabbit_events,
    COUNTIF(actor_type = 'Lovable') as lovable_events,
    COUNTIF(actor_type = 'Dependabot') as dependabot_events,
    COUNTIF(actor_type = 'CI/CD Bot') as cicd_events,
    COUNTIF(actor_type = 'Other Bot') as other_bot_events,

    -- Human events
    COUNTIF(actor_type = 'Human') as human_only_events

FROM {{ ref('stg_github_events') }}
GROUP BY event_date
ORDER BY event_date