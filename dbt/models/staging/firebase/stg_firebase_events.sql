{{ config(
    materialized = "view",
    tags = ["cp6", "staging", "firebase"]
) }}

with raw_events as (

    select *
    from {{ source("raw", "firebase_events") }}

),

normalized as (

    select
        -- Event identity inputs and time
        event_date as event_date_raw,
        safe.parse_date("%Y%m%d", event_date) as event_date,

        event_timestamp as event_timestamp_raw,
        timestamp_micros(event_timestamp) as event_timestamp_utc,

        event_previous_timestamp as event_previous_timestamp_raw,
        timestamp_micros(
            event_previous_timestamp
        ) as event_previous_timestamp_utc,

        event_name,
        event_value_in_usd,
        event_bundle_sequence_id,
        event_server_timestamp_offset,

        -- Preserve the original Parquet wrapper for exact hashing
        event_params as event_params_source,

        -- Normalize list.element without dropping any parameter
        array(
            select as struct
                parameter.element.key as key,
                parameter.element.value.string_value as string_value,
                parameter.element.value.int_value as int_value,
                parameter.element.value.float_value as float_value,
                parameter.element.value.double_value as double_value
            from unnest(
                coalesce(event_params.list, [])
            ) as parameter
        ) as event_params,

        -- User identity and properties
        user_id,
        user_pseudo_id,

        user_properties as user_properties_source,

        array(
            select as struct
                property.element.key as key,
                property.element.value.string_value as string_value,
                property.element.value.int_value as int_value,
                property.element.value.float_value as float_value,
                property.element.value.double_value as double_value,
                property.element.value.set_timestamp_micros
                    as set_timestamp_micros
            from unnest(
                coalesce(user_properties.list, [])
            ) as property
        ) as user_properties,

        user_first_touch_timestamp
            as user_first_touch_timestamp_raw,

        timestamp_micros(
            user_first_touch_timestamp
        ) as user_first_touch_timestamp_utc,

        -- Preserve source structs for exact source-row hashing
        user_ltv as user_ltv_source,
        device as device_source,
        geo as geo_source,
        app_info as app_info_source,
        traffic_source as traffic_source_source,
        event_dimensions as event_dimensions_source,

        -- Canonical promoted attributes
        user_ltv.revenue as user_ltv_revenue,
        user_ltv.currency as user_ltv_currency,

        device.category as device_category,
        device.operating_system as operating_system,
        device.operating_system_version as operating_system_version,
        device.language as device_language,
        device.mobile_brand_name as mobile_brand_name,
        device.mobile_model_name as mobile_model_name,

        geo.country as country,
        geo.region as region,
        geo.city as city,
        geo.continent as continent,
        geo.sub_continent as sub_continent,

        app_info.id as app_id,
        app_info.version as app_version,

        traffic_source.source as traffic_source,
        traffic_source.medium as traffic_medium,
        traffic_source.name as traffic_campaign,

        event_dimensions.hostname as event_hostname,

        stream_id,
        platform,

        -- Operational lineage; excluded from event identity
        source_date,
        source_system,
        source_file_uri,
        ingestion_run_id,
        ingested_at_utc,
        pipeline_version

    from raw_events

),

final as (

    select
        *,
        to_json_string(event_params) as event_params_json
    from normalized

)

select *
from final