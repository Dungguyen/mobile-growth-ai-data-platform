-- ============================================================
-- Mobile Growth & AI Data Platform
-- CP3 - Canonical Event Prototype
--
-- Purpose:
-- Validate canonical event identity and core field mapping.
--
-- This is a design prototype only.
-- It does NOT create production tables.
-- ============================================================


WITH source AS (

    SELECT
        t,

        TO_HEX(
            SHA256(
                CONCAT(
                    'firebase_floodit|',
                    TO_JSON_STRING(t)
                )
            )
        ) AS source_event_hash

    FROM `firebase-public-project.analytics_153293282.events_*` AS t

),

ranked AS (

    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY source_event_hash
            ORDER BY t.event_timestamp
        ) AS duplicate_rank

    FROM source

),

canonical AS (

    SELECT
        source_event_hash AS event_id,
        source_event_hash,

        PARSE_DATE(
            '%Y%m%d',
            t.event_date
        ) AS event_date,

        t.event_timestamp
            AS event_timestamp_raw,

        TIMESTAMP_MICROS(
            t.event_timestamp
        ) AS event_timestamp_utc,

        t.event_name,

        CASE

            WHEN t.event_name IN (
                'screen_view',
                'user_engagement',
                'session_start',
                'select_content'
            )
                THEN 'engagement'

            WHEN STARTS_WITH(
                t.event_name,
                'level_'
            )
                OR t.event_name IN (
                    'post_score',
                    'use_extra_steps',
                    'no_more_extra_steps',
                    'completed_5_levels'
                )
                THEN 'gameplay'

            WHEN t.event_name IN (
                'in_app_purchase',
                'spend_virtual_currency',
                'ad_reward'
            )
                THEN 'monetization'

            WHEN t.event_name IN (
                'firebase_campaign',
                'dynamic_link_app_open',
                'dynamic_link_first_open'
            )
                THEN 'acquisition'

            WHEN t.event_name IN (
                'first_open',
                'app_update',
                'app_remove',
                'os_update',
                'app_clear_data'
            )
                THEN 'lifecycle'

            WHEN t.event_name IN (
                'app_exception',
                'error'
            )
                THEN 'technical'

            WHEN t.event_name IN (
                'challenge_a_friend',
                'challenge_accepted'
            )
                THEN 'social'

            ELSE 'other'

        END AS event_category,

        t.user_pseudo_id,
        t.platform,

        t.app_info.id
            AS app_id,

        t.device.category
            AS device_category,

        t.device.operating_system
            AS operating_system,

        t.device.operating_system_version
            AS operating_system_version,

        t.device.language
            AS device_language,

        t.geo.country
            AS country,

        t.geo.region
            AS region,

        t.geo.city
            AS city,

        t.traffic_source.source
            AS traffic_source,

        t.traffic_source.medium
            AS traffic_medium,

        t.traffic_source.name
            AS traffic_campaign,

        TO_JSON_STRING(
            t.event_params
        ) AS event_params_json

    FROM ranked

    WHERE duplicate_rank = 1

)

SELECT *
FROM canonical
LIMIT 100;