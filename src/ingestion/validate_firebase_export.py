from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from google.cloud import storage


load_dotenv()


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


PROJECT_ID = required_env("GCP_PROJECT_ID")
BUCKET_NAME = required_env("GCS_RAW_BUCKET")


def parse_date(value: str) -> date:
    return datetime.strptime(
        value,
        "%Y-%m-%d",
    ).date()


def date_range(start_date: date, end_date: date):
    current = start_date

    while current <= end_date:
        yield current
        current += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start-date",
        required=True,
    )

    parser.add_argument(
        "--end-date",
        required=True,
    )

    parser.add_argument(
        "--expected-total-rows",
        type=int,
    )

    args = parser.parse_args()

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    storage_client = storage.Client(
        project=PROJECT_ID,
    )

    bucket = storage_client.bucket(
        BUCKET_NAME
    )

    missing_manifests: list[str] = []
    invalid_dates: list[str] = []

    total_rows = 0
    total_files = 0
    total_bytes = 0
    successful_dates = 0

    for current_date in date_range(
        start_date,
        end_date,
    ):
        date_text = current_date.isoformat()

        manifest_path = (
            "manifests/firebase/events/"
            f"source_date={date_text}.json"
        )

        manifest_blob = bucket.blob(
            manifest_path
        )

        if not manifest_blob.exists():
            missing_manifests.append(date_text)
            continue

        manifest = json.loads(
            manifest_blob.download_as_text()
        )

        if manifest.get("status") != "SUCCESS":
            invalid_dates.append(date_text)
            continue

        prefix = (
            "raw/firebase/events/"
            f"source_date={date_text}/"
        )

        parquet_files = [
            blob
            for blob in storage_client.list_blobs(
                BUCKET_NAME,
                prefix=prefix,
            )
            if blob.name.endswith(".parquet")
        ]

        actual_file_count = len(
            parquet_files
        )

        actual_bytes = sum(
            blob.size or 0
            for blob in parquet_files
        )

        if (
            actual_file_count
            != manifest["output_file_count"]
        ):
            invalid_dates.append(date_text)
            continue

        if (
            actual_bytes
            != manifest["output_total_bytes"]
        ):
            invalid_dates.append(date_text)
            continue

        successful_dates += 1
        total_rows += int(
            manifest["source_row_count"]
        )
        total_files += actual_file_count
        total_bytes += actual_bytes

    expected_dates = (
        end_date - start_date
    ).days + 1

    summary = {
        "expected_dates": expected_dates,
        "successful_dates": successful_dates,
        "missing_manifests": missing_manifests,
        "invalid_dates": invalid_dates,
        "total_source_rows": total_rows,
        "total_parquet_files": total_files,
        "total_bytes": total_bytes,
    }

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    if missing_manifests:
        raise SystemExit(1)

    if invalid_dates:
        raise SystemExit(1)

    if successful_dates != expected_dates:
        raise SystemExit(1)

    if (
        args.expected_total_rows is not None
        and total_rows
        != args.expected_total_rows
    ):
        raise RuntimeError(
            "Unexpected total row count: "
            f"{total_rows:,}"
        )


if __name__ == "__main__":
    main()