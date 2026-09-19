-- ============================================================
-- Mobile Growth & AI Data Platform
-- CP2 - Source Data Profiling
--
-- Source:
-- firebase-public-project.analytics_153293282.events_*
--
-- Purpose:
-- Understand the source before defining the canonical event model.
-- ============================================================


-- ------------------------------------------------------------
-- 1. Dataset baseline
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_events,
    COUNT(DISTINCT user_pseudo_id) AS total_users,
    COUNT(DISTINCT event_date) AS active_dates,
    MIN(event_date) AS min_event_date,
    MAX(event_date) AS max_event_date
FROM `firebase-public-project.analytics_153293282.events_*`;


-- ------------------------------------------------------------
-- 2. Event distribution
-- ------------------------------------------------------------

SELECT
    event_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users,
    ROUND(
        100 * COUNT(*) /
        SUM(COUNT(*)) OVER (),
        2
    ) AS event_pct
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY event_name
ORDER BY event_count DESC;


-- ------------------------------------------------------------
-- 3. Platform distribution
-- ------------------------------------------------------------

SELECT
    platform,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY platform
ORDER BY event_count DESC;


-- ------------------------------------------------------------
-- 4. Operating-system distribution
-- ------------------------------------------------------------

SELECT
    device.operating_system AS operating_system,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY operating_system
ORDER BY event_count DESC;


-- ------------------------------------------------------------
-- 5. Device-category distribution
-- ------------------------------------------------------------

SELECT
    device.category AS device_category,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY device_category
ORDER BY event_count DESC;


-- ------------------------------------------------------------
-- 6. Country distribution
-- ------------------------------------------------------------

SELECT
    geo.country AS country,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY country
ORDER BY event_count DESC
LIMIT 50;


-- ------------------------------------------------------------
-- 7. Application distribution
-- ------------------------------------------------------------

SELECT
    app_info.id AS app_id,
    platform,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY
    app_id,
    platform
ORDER BY event_count DESC;


-- ------------------------------------------------------------
-- 8. Traffic-source distribution
-- ------------------------------------------------------------

SELECT
    traffic_source.source AS source,
    traffic_source.medium AS medium,
    traffic_source.name AS campaign_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY
    source,
    medium,
    campaign_name
ORDER BY event_count DESC
LIMIT 100;


-- ------------------------------------------------------------
-- 9. All event parameter keys
-- ------------------------------------------------------------

SELECT
    ep.key AS parameter_key,
    COUNT(*) AS parameter_occurrences,
    COUNT(DISTINCT event_name) AS used_by_event_types
FROM `firebase-public-project.analytics_153293282.events_*`,
UNNEST(event_params) AS ep
GROUP BY parameter_key
ORDER BY parameter_occurrences DESC;


-- ------------------------------------------------------------
-- 10. Parameter keys by event type
-- ------------------------------------------------------------

SELECT
    event_name,
    ep.key AS parameter_key,
    COUNT(*) AS parameter_occurrences
FROM `firebase-public-project.analytics_153293282.events_*`,
UNNEST(event_params) AS ep
GROUP BY
    event_name,
    parameter_key
ORDER BY
    event_name,
    parameter_occurrences DESC;


-- ------------------------------------------------------------
-- 11. Detect parameter value types
-- ------------------------------------------------------------
--
-- Helps determine how each event parameter should be normalized.
-- ------------------------------------------------------------

SELECT
    event_name,
    ep.key AS parameter_key,

    COUNTIF(
        ep.value.string_value IS NOT NULL
    ) AS string_values,

    COUNTIF(
        ep.value.int_value IS NOT NULL
    ) AS integer_values,

    COUNTIF(
        ep.value.float_value IS NOT NULL
    ) AS float_values,

    COUNTIF(
        ep.value.double_value IS NOT NULL
    ) AS double_values

FROM `firebase-public-project.analytics_153293282.events_*`,
UNNEST(event_params) AS ep

GROUP BY
    event_name,
    parameter_key

ORDER BY
    event_name,
    parameter_key;


-- ------------------------------------------------------------
-- 12. Event parameters for important gameplay events
-- ------------------------------------------------------------

SELECT
    event_name,
    ep.key AS parameter_key,

    ep.value.string_value,
    ep.value.int_value,
    ep.value.float_value,
    ep.value.double_value

FROM `firebase-public-project.analytics_153293282.events_*`,
UNNEST(event_params) AS ep

WHERE event_name IN (
    'level_start_quickplay',
    'level_end_quickplay',
    'post_score',
    'level_up'
)

LIMIT 500;


-- ------------------------------------------------------------
-- 13. User activity distribution
-- ------------------------------------------------------------

WITH user_activity AS (

    SELECT
        user_pseudo_id,
        COUNT(*) AS event_count,
        COUNT(DISTINCT event_date) AS active_days,
        MIN(event_timestamp) AS first_event_timestamp,
        MAX(event_timestamp) AS last_event_timestamp

    FROM `firebase-public-project.analytics_153293282.events_*`

    WHERE user_pseudo_id IS NOT NULL

    GROUP BY user_pseudo_id

)

SELECT
    MIN(event_count) AS min_events_per_user,
    APPROX_QUANTILES(event_count, 100)[OFFSET(25)]
        AS p25_events_per_user,
    APPROX_QUANTILES(event_count, 100)[OFFSET(50)]
        AS median_events_per_user,
    APPROX_QUANTILES(event_count, 100)[OFFSET(75)]
        AS p75_events_per_user,
    APPROX_QUANTILES(event_count, 100)[OFFSET(95)]
        AS p95_events_per_user,
    MAX(event_count) AS max_events_per_user,

    AVG(active_days) AS avg_active_days

FROM user_activity;


-- ------------------------------------------------------------
-- 14. Events by day
-- ------------------------------------------------------------

SELECT
    event_date,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_pseudo_id) AS daily_active_users
FROM `firebase-public-project.analytics_153293282.events_*`
GROUP BY event_date
ORDER BY event_date;


-- ------------------------------------------------------------
-- 15. Required-field completeness
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_events,

    COUNTIF(event_date IS NULL) AS missing_event_date,

    COUNTIF(event_timestamp IS NULL)
        AS missing_event_timestamp,

    COUNTIF(event_name IS NULL OR event_name = '')
        AS missing_event_name,

    COUNTIF(
        user_pseudo_id IS NULL
        OR user_pseudo_id = ''
    ) AS missing_user_pseudo_id,

    COUNTIF(platform IS NULL OR platform = '')
        AS missing_platform

FROM `firebase-public-project.analytics_153293282.events_*`;


-- ------------------------------------------------------------
-- 16. Timestamp validation
-- ------------------------------------------------------------

SELECT
    MIN(
        TIMESTAMP_MICROS(event_timestamp)
    ) AS first_event_timestamp,

    MAX(
        TIMESTAMP_MICROS(event_timestamp)
    ) AS last_event_timestamp

FROM `firebase-public-project.analytics_153293282.events_*`;


-- ------------------------------------------------------------
-- 17. Potential duplicate-event investigation
-- ------------------------------------------------------------
--
-- There is no guaranteed event_id in this historical source.
-- This query looks for repeated combinations that may represent
-- duplicates, but DOES NOT yet define the final deduplication rule.
-- ------------------------------------------------------------

WITH candidate_duplicates AS (

    SELECT
        user_pseudo_id,
        event_name,
        event_timestamp,
        COUNT(*) AS row_count

    FROM `firebase-public-project.analytics_153293282.events_*`

    GROUP BY
        user_pseudo_id,
        event_name,
        event_timestamp

    HAVING COUNT(*) > 1

)

SELECT
    COUNT(*) AS duplicate_groups,
    SUM(row_count) AS rows_in_duplicate_groups,
    SUM(row_count - 1) AS potential_duplicate_rows
FROM candidate_duplicates;


-- ------------------------------------------------------------
-- 18. Top duplicate candidates
-- ------------------------------------------------------------

SELECT
    user_pseudo_id,
    event_name,
    event_timestamp,
    COUNT(*) AS row_count

FROM `firebase-public-project.analytics_153293282.events_*`

GROUP BY
    user_pseudo_id,
    event_name,
    event_timestamp

HAVING COUNT(*) > 1

ORDER BY row_count DESC

LIMIT 100;


-- ------------------------------------------------------------
-- 19. Sample raw records
-- ------------------------------------------------------------

SELECT *
FROM `firebase-public-project.analytics_153293282.events_*`
LIMIT 20;

-- 20. Exact full-row duplicate validation
-- ------------------------------------------------------------
--
-- Result:
--   exact duplicate groups = 59
--   exact duplicate rows   = 59
--
-- This proves that user_pseudo_id + event_name +
-- event_timestamp is NOT sufficient as a deduplication key.
-- ------------------------------------------------------------

WITH row_fingerprints AS (

    SELECT
        FARM_FINGERPRINT(
            TO_JSON_STRING(t)
        ) AS row_fingerprint

    FROM `firebase-public-project.analytics_153293282.events_*` AS t

),

duplicates AS (

    SELECT
        row_fingerprint,
        COUNT(*) AS row_count

    FROM row_fingerprints

    GROUP BY row_fingerprint

    HAVING COUNT(*) > 1

)

SELECT
    COUNT(*) AS exact_duplicate_groups,
    SUM(row_count) AS rows_in_exact_duplicate_groups,
    SUM(row_count - 1) AS exact_duplicate_rows

FROM duplicates;

-- 21. Business-event parameter map
-- ------------------------------------------------------------
--
-- Purpose:
-- Identify parameter names and physical value types for
-- Product, Growth, Gameplay and Monetization events.
-- ------------------------------------------------------------

SELECT
    event_name,
    ep.key AS parameter_key,

    COUNT(*) AS occurrences,

    COUNTIF(
        ep.value.string_value IS NOT NULL
    ) AS string_count,

    COUNTIF(
        ep.value.int_value IS NOT NULL
    ) AS int_count,

    COUNTIF(
        ep.value.float_value IS NOT NULL
    ) AS float_count,

    COUNTIF(
        ep.value.double_value IS NOT NULL
    ) AS double_count

FROM `firebase-public-project.analytics_153293282.events_*`,
UNNEST(event_params) AS ep

WHERE event_name IN (
    'session_start',
    'first_open',
    'user_engagement',

    'level_start',
    'level_end',
    'level_complete',
    'level_fail',
    'level_retry',
    'level_up',

    'level_start_quickplay',
    'level_end_quickplay',
    'level_complete_quickplay',
    'level_fail_quickplay',
    'level_retry_quickplay',

    'post_score',
    'spend_virtual_currency',
    'ad_reward',
    'in_app_purchase',
    'firebase_campaign'
)

GROUP BY
    event_name,
    parameter_key

ORDER BY
    event_name,
    occurrences DESC;