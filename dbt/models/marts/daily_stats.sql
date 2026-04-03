{{ config(
    materialized='table',
    partition_by={"field": "date", "data_type": "date", "granularity": "day"},
    tags=['marts', 'daily']
) }}

WITH stg_events AS (SELECT * FROM {{ ref('stg_github_events') }})

SELECT
    date_partition AS date,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS active_users,
    COUNT(DISTINCT repo_name) AS active_repos,
    COUNTIF(standardized_event_type = 'push') AS push_events,
    COUNTIF(standardized_event_type = 'pull_request') AS pull_request_events,
    COUNTIF(standardized_event_type = 'issues') AS issues_events,
    COUNTIF(standardized_event_type = 'star') AS star_events,
    COUNTIF(standardized_event_type = 'fork') AS fork_events,
    SAFE_DIVIDE(COUNT(*), COUNT(DISTINCT actor_login)) AS events_per_user
FROM stg_events
GROUP BY date_partition
ORDER BY date DESC
