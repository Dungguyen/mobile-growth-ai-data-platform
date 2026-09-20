from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

from dotenv import load_dotenv
from google.cloud import bigquery


load_dotenv()


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


PROJECT_ID = required_env("GCP_PROJECT_ID")
LOCATION = required_env("GCP_LOCATION")
RAW_DATASET = required_env("BQ_RAW_DATASET")

EXTERNAL_TABLE = (
    f"{PROJECT_ID}.{RAW_DATASET}.firebase_events_external"
)

BRONZE_TABLE = (
    f"{PROJECT_ID}.{RAW_DATASET}.firebase_events"
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--expected-total-rows",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--expected-dates",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--start-date",
        required=True,
    )

    parser.add_argument(
        "--end-date",
        required=True,
    )

    args = parser.parse_args()

    expected_start = datetime.strptime(
        args.start_date,
        "%Y-%m-%d",
    ).date()

    expected_end = datetime.strptime(
        args.end_date,
        "%Y-%m-%d",
    ).date()

    client = bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )

    sql = f"""
    SELECT
        COUNT(*) AS total_rows,

        COUNT(DISTINCT source_date)
            AS source_dates,

        MIN(source_date)
            AS min_source_date,

        MAX(source_date)
            AS max_source_date,

        COUNTIF(
            event_date IS NULL
        ) AS missing_event_date,

        COUNTIF(
            event_timestamp IS NULL
        ) AS missing_event_timestamp,

        COUNTIF(
            event_name IS NULL
            OR event_name = ''
        ) AS missing_event_name,

        COUNTIF(
            user_pseudo_id IS NULL
            OR user_pseudo_id = ''
        ) AS missing_user_pseudo_id,

        COUNTIF(
            platform IS NULL
            OR platform = ''
        ) AS missing_platform,

        COUNTIF(
            source_file_uri IS NULL
            OR source_file_uri = ''
        ) AS missing_source_file_uri,

        COUNTIF(
            ingestion_run_id IS NULL
            OR ingestion_run_id = ''
        ) AS missing_ingestion_run_id,

        COUNTIF(
            pipeline_version IS NULL
            OR pipeline_version = ''
        ) AS missing_pipeline_version,

        COUNTIF(
            ARRAY_LENGTH(event_params) > 0
        ) AS rows_with_event_params

    FROM `{BRONZE_TABLE}`
    """

    result = list(
        client.query(
            sql,
            location=LOCATION,
        ).result()
    )[0]

    external_sql = f"""
    SELECT
        COUNT(*) AS total_rows
    FROM `{EXTERNAL_TABLE}`
    """

    external_rows = int(
        list(
            client.query(
                external_sql,
                location=LOCATION,
            ).result()
        )[0]["total_rows"]
    )

    table = client.get_table(
        BRONZE_TABLE
    )

    partition_field = (
        table.time_partitioning.field
        if table.time_partitioning
        else None
    )

    clustering_fields = (
        table.clustering_fields or []
    )

    summary = {
        "external_rows": external_rows,
        "bronze_rows": int(
            result["total_rows"]
        ),
        "source_dates": int(
            result["source_dates"]
        ),
        "min_source_date": str(
            result["min_source_date"]
        ),
        "max_source_date": str(
            result["max_source_date"]
        ),
        "missing_event_date": int(
            result["missing_event_date"]
        ),
        "missing_event_timestamp": int(
            result["missing_event_timestamp"]
        ),
        "missing_event_name": int(
            result["missing_event_name"]
        ),
        "missing_user_pseudo_id": int(
            result["missing_user_pseudo_id"]
        ),
        "missing_platform": int(
            result["missing_platform"]
        ),
        "missing_source_file_uri": int(
            result["missing_source_file_uri"]
        ),
        "missing_ingestion_run_id": int(
            result["missing_ingestion_run_id"]
        ),
        "missing_pipeline_version": int(
            result["missing_pipeline_version"]
        ),
        "rows_with_event_params": int(
            result["rows_with_event_params"]
        ),
        "partition_field": partition_field,
        "clustering_fields": clustering_fields,
    }

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    if external_rows != args.expected_total_rows:
        raise RuntimeError(
            "External table row count mismatch"
        )

    if result["total_rows"] != args.expected_total_rows:
        raise RuntimeError(
            "Bronze table row count mismatch"
        )

    if result["source_dates"] != args.expected_dates:
        raise RuntimeError(
            "Unexpected Bronze source-date count"
        )

    if result["min_source_date"] != expected_start:
        raise RuntimeError(
            "Unexpected minimum source date"
        )

    if result["max_source_date"] != expected_end:
        raise RuntimeError(
            "Unexpected maximum source date"
        )

    if result["missing_event_date"] != 0:
        raise RuntimeError(
            "Missing event_date values"
        )

    if result["missing_event_timestamp"] != 0:
        raise RuntimeError(
            "Missing event_timestamp values"
        )

    if result["missing_event_name"] != 0:
        raise RuntimeError(
            "Missing event_name values"
        )

    if result["missing_user_pseudo_id"] != 0:
        raise RuntimeError(
            "Missing user_pseudo_id values"
        )

    if result["missing_platform"] != 0:
        raise RuntimeError(
            "Missing platform values"
        )

    if result["missing_source_file_uri"] != 0:
        raise RuntimeError(
            "Missing source lineage"
        )

    if result["missing_ingestion_run_id"] != 0:
        raise RuntimeError(
            "Missing ingestion run ID"
        )

    if result["missing_pipeline_version"] != 0:
        raise RuntimeError(
            "Missing pipeline version"
        )

    if partition_field != "source_date":
        raise RuntimeError(
            "Bronze table is not partitioned by source_date"
        )

    if clustering_fields != [
        "event_name",
        "platform",
    ]:
        raise RuntimeError(
            "Unexpected clustering configuration"
        )


if __name__ == "__main__":
    main()