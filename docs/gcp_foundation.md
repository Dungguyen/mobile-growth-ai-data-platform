# GCP Foundation

## Project

Project ID:

`mobile-growth-ai-dung-2026`

Purpose:

Dedicated development project for the Mobile Growth & AI Data Platform.

The project is isolated from other portfolio workloads such as Glamira.

## Location

Primary batch-data location:

`US`

Reason:

The Flood-It public BigQuery source is hosted in the source dataset
location used by the extraction workload.

BigQuery source, raw landing storage, and initial BigQuery datasets are
co-located to avoid unsupported or unnecessary cross-location batch
operations.

## Cloud Storage

Raw landing bucket:

`gs://mobile-growth-ai-dung-2026-raw`

Uniform bucket-level access:

Enabled.

Expected layout:

```text
raw/firebase/events/source_date=YYYY-MM-DD/
manifests/firebase/
quality/

BigQuery

Datasets:

raw
staging
raw

Purpose:

Preserve source-aligned data after landing/loading with minimal
transformation.

staging

Purpose:

Provide the standardized transformation boundary for dbt models.

Runtime Identity

Service account:

mobile-growth-ingestion@mobile-growth-ai-dung-2026.iam.gserviceaccount.com

Initial development permissions:

BigQuery Job User
BigQuery Data Editor
Storage Object Admin on the dedicated raw bucket

No long-lived service-account JSON key is stored in the repository.

Enabled Services
BigQuery
Cloud Storage
Pub/Sub
IAM
Cloud Resource Manager
Source

Public source:

firebase-public-project.analytics_153293282.events_*

The source remains read-only.

Security Decisions
Secrets are excluded from Git.
No service-account key files are committed.
Human credentials are used only for local development.
Runtime workloads will use a dedicated service account.
Raw bucket uses uniform bucket-level access.
CP4 Status

GCP project:

READY

Cloud Storage raw landing:

READY

BigQuery datasets:

READY

Runtime identity:

READY

Source connectivity:

VALIDATED

Decision:

GO TO BATCH EXTRACTION