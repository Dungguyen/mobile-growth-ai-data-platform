from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
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
BUCKET_NAME = required_env("GCS_RAW_BUCKET")
RAW_DATASET = required_env("BQ_RAW_DATASET")

EXTERNAL_TABLE = (
    f"{PROJECT_ID}.{RAW_DATASET}.firebase_events_external"
)

BRONZE_TABLE = (
    f"{PROJECT_ID}.{RAW_DATASET}.firebase_events"
)

RAW_URI = (
    f"gs://{BUCKET_NAME}/raw/firebase/events/*.parquet"
)

HIVE_PREFIX = (
    f"gs://{BUCKET_NAME}/raw/firebase/events"
)

PIPELINE_VERSION = "cp6-v1"


def table_exists(
    client: bigquery.Client,
    table_id: str,
) -> bool:
    try:
        client.get_table(table_id)
        return True
    except NotFound:
        return False


def execute(
    client: bigquery.Client,
    sql: str,
) -> bigquery.QueryJob:
    job = client.query(
        sql,
        location=LOCATION,
    )

    job.result()

    return job


def create_external_table(
    client: bigquery.Client,
) -> None:
    sql = f"""
    CREATE OR REPLACE EXTERNAL TABLE `{EXTERNAL_TABLE}`
    WITH PARTITION COLUMNS (
        source_date DATE
    )
    OPTIONS (
        format = 'PARQUET',
        uris = ['{RAW_URI}'],
        hive_partition_uri_prefix = '{HIVE_PREFIX}',
        require_hive_partition_filter = false
    )
    """

    print(
        "[CREATE] external table "
        f"{EXTERNAL_TABLE}"
    )

    execute(
        client,
        sql,
    )


def validate_external_table(
    client: bigquery.Client,
) -> dict:
    sql = f"""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(DISTINCT source_date)
            AS source_dates,
        MIN(source_date)
            AS min_source_date,
        MAX(source_date)
            AS max_source_date
    FROM `{EXTERNAL_TABLE}`
    """

    rows = list(
        client.query(
            sql,
            location=LOCATION,
        ).result()
    )

    result = dict(rows[0])

    print(
        "[EXTERNAL] "
        f"rows={result['total_rows']:,}, "
        f"dates={result['source_dates']}"
    )

    return result


def create_bronze_table(
    client: bigquery.Client,
    rebuild: bool,
) -> str:
    exists = table_exists(
        client,
        BRONZE_TABLE,
    )

    if exists and not rebuild:
        raise RuntimeError(
            f"{BRONZE_TABLE} already exists. "
            "Use --rebuild to replace it."
        )

    ingestion_run_id = (
        "historical_"
        + datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%SZ")
    )

    create_keyword = (
        "CREATE OR REPLACE TABLE"
        if rebuild
        else "CREATE TABLE"
    )

    sql = f"""
    {create_keyword} `{BRONZE_TABLE}`

    PARTITION BY source_date

    CLUSTER BY
        event_name,
        platform

    OPTIONS (
        description =
        'Bronze Firebase events loaded from GCS Raw Parquet'
    )

    AS

    SELECT
        e.* EXCEPT(source_date),

        e.source_date,

        'firebase_floodit'
            AS source_system,

        _FILE_NAME
            AS source_file_uri,

        '{ingestion_run_id}'
            AS ingestion_run_id,

        CURRENT_TIMESTAMP()
            AS ingested_at_utc,

        '{PIPELINE_VERSION}'
            AS pipeline_version

    FROM `{EXTERNAL_TABLE}` AS e
    """

    print(
        "[LOAD] Bronze table "
        f"{BRONZE_TABLE}"
    )

    job = execute(
        client,
        sql,
    )

    print(
        f"[SUCCESS] job_id={job.job_id}"
    )

    return ingestion_run_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Load Firebase GCS Raw Parquet "
            "into BigQuery Bronze."
        )
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Replace the existing Bronze table."
        ),
    )

    args = parser.parse_args()

    client = bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )

    print(
        f"Project: {PROJECT_ID}"
    )

    print(
        f"External table: {EXTERNAL_TABLE}"
    )

    print(
        f"Bronze table: {BRONZE_TABLE}"
    )

    print(
        f"Source: {RAW_URI}"
    )

    create_external_table(
        client
    )

    external_summary = validate_external_table(
        client
    )

    if external_summary["total_rows"] != 5_700_000:
        raise RuntimeError(
            "External row count mismatch: "
            f"{external_summary['total_rows']:,}"
        )

    if external_summary["source_dates"] != 114:
        raise RuntimeError(
            "External source-date count mismatch: "
            f"{external_summary['source_dates']}"
        )

    ingestion_run_id = create_bronze_table(
        client=client,
        rebuild=args.rebuild,
    )

    print(
        "[DONE] "
        f"ingestion_run_id={ingestion_run_id}"
    )


if __name__ == "__main__":
    main()