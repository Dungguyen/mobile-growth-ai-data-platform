# Batch Extraction

## Purpose

Extract historical Firebase / GA4 Flood-It events from the Google
public BigQuery dataset into the project-owned GCS raw landing layer.

## Source

Project:

`firebase-public-project`

Dataset:

`analytics_153293282`

Tables:

`events_YYYYMMDD`

Historical range:

`2018-06-12` through `2018-10-03`

Expected:

- 114 source dates
- 5,700,000 source rows

## Destination

Bucket:

`gs://mobile-growth-ai-dung-2026-raw`

Layout:

```text
raw/firebase/events/
└── source_date=YYYY-MM-DD/
    └── part-*.parquet

manifests/firebase/events/
└── source_date=YYYY-MM-DD.json
```

## File Format

Format:

PARQUET

Compression:

SNAPPY

Parquet is used because the Firebase source contains nested and
repeated structures that must be retained in the Raw layer.

Extraction Grain

One extraction unit represents one source date.

Each Firebase daily source table is exported independently.

This allows:

date-level retries
historical backfills
failure isolation
data lineage
source-count reconciliation
Idempotency Strategy

A successful date produces a manifest.

If a successful manifest already exists, the exporter skips that date.

If a rerun is explicitly forced, existing objects under that source
date prefix are deleted before the date is exported again.

This prevents stale Parquet objects from surviving a re-export.

Manifest

Each successful source date records:

source system
source table
source date
source row count
BigQuery job ID
output URI
output format
compression
output file count
output bytes
export timestamp
pipeline version

The manifest is written only after the export succeeds and Parquet
objects are confirmed to exist.

Raw Data Policy

The extraction process does not:

deduplicate events
flatten nested event parameters
classify events
convert business attributes
apply Silver transformations

Raw preserves source semantics.

Exact duplicate removal belongs to Silver.

Validation

Pilot date:

2018-06-12

Expected rows:

50,000

Full historical load:

114 dates

Expected rows:

5,700,000

CP5 Decision

Batch extraction:

VALIDATED

Historical backfill:

COMPLETE

