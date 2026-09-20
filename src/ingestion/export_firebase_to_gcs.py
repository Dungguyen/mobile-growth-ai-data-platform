from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
from google.cloud import bigquery, storage


load_dotenv()


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


PROJECT_ID = required_env("GCP_PROJECT_ID")
LOCATION = required_env("GCP_LOCATION")
BUCKET_NAME = required_env("GCS_RAW_BUCKET")

SOURCE_PROJECT = required_env("SOURCE_GCP_PROJECT")
SOURCE_DATASET = required_env("SOURCE_BQ_DATASET")
SOURCE_TABLE_PATTERN = required_env("SOURCE_TABLE_PATTERN")

SOURCE_TABLE_PREFIX = SOURCE_TABLE_PATTERN.removesuffix("*")

PIPELINE_VERSION = "cp5-v1"


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def date_range(start_date: date, end_date: date):
    current = start_date

    while current <= end_date:
        yield current
        current += timedelta(days=1)


def source_table(source_date: date) -> str:
    table_suffix = source_date.strftime("%Y%m%d")

    return (
        f"{SOURCE_PROJECT}."
        f"{SOURCE_DATASET}."
        f"{SOURCE_TABLE_PREFIX}{table_suffix}"
    )


def raw_prefix(source_date: date) -> str:
    return (
        "raw/firebase/events/"
        f"source_date={source_date.isoformat()}/"
    )


def manifest_name(source_date: date) -> str:
    return (
        "manifests/firebase/events/"
        f"source_date={source_date.isoformat()}.json"
    )


def delete_prefix(
    storage_client: storage.Client,
    prefix: str,
) -> int:
    deleted = 0

    for blob in storage_client.list_blobs(
        BUCKET_NAME,
        prefix=prefix,
    ):
        blob.delete()
        deleted += 1

    return deleted


def get_source_row_count(
    bq_client: bigquery.Client,
    table_name: str,
) -> int:
    sql = f"""
        SELECT COUNT(*) AS row_count
        FROM `{table_name}`
    """

    rows = list(
        bq_client.query(
            sql,
            location=LOCATION,
        ).result()
    )

    return int(rows[0]["row_count"])


def export_source_date(
    bq_client: bigquery.Client,
    storage_client: storage.Client,
    source_date: date,
    force: bool,
) -> dict:
    table_name = source_table(source_date)
    prefix = raw_prefix(source_date)
    manifest_path = manifest_name(source_date)

    bucket = storage_client.bucket(BUCKET_NAME)
    manifest_blob = bucket.blob(manifest_path)

    if manifest_blob.exists() and not force:
        print(
            f"[SKIP] {source_date} "
            "successful manifest already exists"
        )

        return {
            "source_date": source_date.isoformat(),
            "status": "SKIPPED",
        }

    existing_files = list(
        storage_client.list_blobs(
            BUCKET_NAME,
            prefix=prefix,
        )
    )

    if existing_files:
        print(
            f"[CLEANUP] {source_date}: "
            f"{len(existing_files)} existing objects"
        )

        deleted = delete_prefix(
            storage_client,
            prefix,
        )

        print(
            f"[CLEANUP] deleted {deleted} objects"
        )

    print(
        f"[COUNT] {source_date}: "
        f"{table_name}"
    )

    source_row_count = get_source_row_count(
        bq_client,
        table_name,
    )

    destination_uri = (
        f"gs://{BUCKET_NAME}/"
        f"{prefix}"
        "part-*.parquet"
    )

    export_sql = f"""
        EXPORT DATA OPTIONS(
            uri='{destination_uri}',
            format='PARQUET',
            compression='SNAPPY',
            overwrite=true
        )
        AS
        SELECT *
        FROM `{table_name}`
    """

    print(
        f"[EXPORT] {source_date}: "
        f"{source_row_count:,} rows"
    )

    export_job = bq_client.query(
        export_sql,
        location=LOCATION,
    )

    export_job.result()

    parquet_blobs = [
        blob
        for blob in storage_client.list_blobs(
            BUCKET_NAME,
            prefix=prefix,
        )
        if blob.name.endswith(".parquet")
    ]

    if not parquet_blobs:
        raise RuntimeError(
            f"No parquet files produced for {source_date}"
        )

    total_bytes = sum(
        blob.size or 0
        for blob in parquet_blobs
    )

    manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "status": "SUCCESS",
        "source_system": "firebase_floodit",
        "source_project": SOURCE_PROJECT,
        "source_dataset": SOURCE_DATASET,
        "source_table": table_name,
        "source_date": source_date.isoformat(),
        "source_row_count": source_row_count,
        "destination_uri": destination_uri,
        "output_format": "PARQUET",
        "compression": "SNAPPY",
        "output_file_count": len(parquet_blobs),
        "output_total_bytes": total_bytes,
        "bigquery_job_id": export_job.job_id,
        "exported_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    manifest_blob.upload_from_string(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ),
        content_type="application/json",
    )

    print(
        f"[SUCCESS] {source_date}: "
        f"{len(parquet_blobs)} files, "
        f"{total_bytes:,} bytes"
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Export Firebase Flood-It events "
            "from BigQuery to GCS Raw."
        )
    )

    parser.add_argument(
        "--start-date",
        required=True,
        help="YYYY-MM-DD",
    )

    parser.add_argument(
        "--end-date",
        required=True,
        help="YYYY-MM-DD",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-export dates even when a "
            "successful manifest already exists."
        ),
    )

    args = parser.parse_args()

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    if start_date > end_date:
        raise ValueError(
            "start-date must be <= end-date"
        )

    bq_client = bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )

    storage_client = storage.Client(
        project=PROJECT_ID,
    )

    print(
        f"Project: {PROJECT_ID}"
    )

    print(
        f"Bucket: gs://{BUCKET_NAME}"
    )

    print(
        f"Range: {start_date} -> {end_date}"
    )

    for current_date in date_range(
        start_date,
        end_date,
    ):
        export_source_date(
            bq_client=bq_client,
            storage_client=storage_client,
            source_date=current_date,
            force=args.force,
        )


if __name__ == "__main__":
    main()