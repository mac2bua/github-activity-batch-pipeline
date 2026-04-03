{{ config(materialized='view', tags=['staging']) }}

WITH raw_events AS (
    SELECT * FROM {{ source('github', 'github_events') }}
),

cleaned AS (
    SELECT
        id,
        type AS event_type,
        actor_login,
        repo_name,
        action,
        created_at,
        date_partition,
        payload,
        org_login,
        file_url,
        CASE 
            WHEN type = 'PushEvent' THEN 'push'
            WHEN type = 'PullRequestEvent' THEN 'pull_request'
            WHEN type = 'IssuesEvent' THEN 'issues'
            WHEN type = 'WatchEvent' THEN 'star'
            WHEN type = 'ForkEvent' THEN 'fork'
            ELSE LOWER(type)
        END AS standardized_event_type
    FROM raw_events
    WHERE id IS NOT NULL AND date_partition IS NOT NULL
)

SELECT * FROM cleaned
