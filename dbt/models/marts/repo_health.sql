{{ config(
    materialized='table',
    partition_by={"field": "date", "data_type": "date", "granularity": "day"},
    tags=['marts', 'repo_health']
) }}

WITH stg_events AS (SELECT * FROM {{ ref('stg_github_events') }})

SELECT
    date_partition AS date,
    repo_name,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS contributors,
    COUNTIF(standardized_event_type = 'push') AS pushes,
    COUNTIF(standardized_event_type = 'pull_request') AS pull_requests,
    COUNTIF(standardized_event_type = 'star') AS stars,
    COUNTIF(standardized_event_type = 'fork') AS forks,
    LEAST(100, (COUNTIF(standardized_event_type = 'push') * 2) + 
        (COUNTIF(standardized_event_type = 'pull_request') * 3) + 
        (COUNTIF(standardized_event_type = 'star') * 5)) AS activity_score,
    CASE 
        WHEN COUNTIF(standardized_event_type = 'push') >= 10 AND COUNT(DISTINCT actor_login) >= 5 THEN 'high_activity'
        WHEN COUNTIF(standardized_event_type = 'push') >= 5 THEN 'medium_activity'
        WHEN COUNTIF(standardized_event_type = 'push') >= 1 THEN 'low_activity'
        ELSE 'inactive'
    END AS activity_level
FROM stg_events
WHERE repo_name IS NOT NULL
GROUP BY date_partition, repo_name
ORDER BY date DESC, activity_score DESC
