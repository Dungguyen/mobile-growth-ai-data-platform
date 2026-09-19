# Mobile Growth & AI Data Platform — Scope Confirmation

## 1. Project Objective

Build an end-to-end data engineering platform for a simulated mobile
apps/games company.

The platform will combine:

- real mobile application event data
- simulated MMP attribution data
- simulated advertising-network data
- simulated monetization data

The final platform will support:

- Product analytics
- Growth analytics
- acquisition reporting
- retention analysis
- ROAS analysis
- LTV and payback analysis
- ML-ready feature datasets
- data observability
- internal self-service analytics
- AI/MCP access to data-platform metadata and metrics

---

## 2. Primary Source Dataset

Primary source:

Google Flood-It! Firebase / GA4 public gaming dataset.

BigQuery source:

`firebase-public-project.analytics_153293282.events_*`

The source represents real mobile-game analytics events from Android
and iOS clients.

Primary source grain:

> One row represents one application event.

The source contains nested structures such as:

- event parameters
- user properties
- device metadata
- geographic metadata
- app metadata
- traffic-source metadata

The public source remains read-only.

The project will copy required source data into a project-owned raw
landing layer before transformation.

---

## 3. Additional Data Sources

The following datasets will be generated specifically for the project.

### MMP Attribution

Simulates data that could originate from platforms such as Adjust.

Example fields:

- install_id
- user_id
- install_timestamp
- platform
- country
- network
- campaign_id
- adgroup_id
- creative_id
- attribution_type

This dataset will be generated from users observed in the real gaming
dataset to maintain referential integrity.

### Ad Network Performance

Simulates daily reporting from networks such as:

- Google Ads
- AppLovin
- Mintegral
- Apple Search Ads

Example metrics:

- impressions
- clicks
- installs
- spend
- ad revenue

### Monetization

Simulates user monetization events:

- purchase
- subscription start
- renewal
- cancellation
- refund

Synthetic monetization will be generated using real users from the
event source and behavior-dependent probabilities.

Synthetic data must always be clearly labeled as simulated data.

---

## 4. Initial Architecture

```text
                REAL SOURCE
         Google Flood-It! Events
                BigQuery
                   |
                   v
            Batch Extraction
                   |
                   v
                GCS Raw
                   |
                   v
             BigQuery Raw
                   |
                   v
                  dbt
          Staging -> Core -> Marts
                   |
          +--------+---------+
          |                  |
          v                  v
     Growth Analytics     ML Features
          |                  |
          v                  v
    Streamlit / BI       BigQuery ML


      SIMULATED SOURCES
   MMP / Ads / Monetization
              |
              +------> GCS / BigQuery Raw


       ORCHESTRATION
     Apache Airflow
     Celery + Redis


    NEAR-REALTIME PATH
 Event Replay -> Pub/Sub -> BigQuery


       OBSERVABILITY
 Quality / Freshness / Volume / Cost


         AI ACCESS
       MCP Server
           |
   BigQuery / Airflow / Docs

5. Medallion / Modeling Strategy

The project will separate data into three logical processing stages.

Raw / Bronze

Preserve source-aligned events and ingestion metadata.

Responsibilities:

source traceability
replayability
ingestion audit metadata
minimal transformation
Silver

Create standardized analytical events.

Responsibilities:

flatten required nested attributes
normalize data types
standardize timestamps
normalize dimensions
deduplicate events
validate business rules
validate required fields
Gold

Create analytics-ready dimensional models and marts.

Expected fact tables:

fact_app_event
fact_install
fact_ad_spend
fact_ad_revenue
fact_purchase

Expected dimensions:

dim_user
dim_app
dim_campaign
dim_network
dim_country
dim_device
dim_date

Expected marts:

mart_daily_active_users
mart_user_acquisition
mart_campaign_performance
mart_retention_cohort
mart_roas
mart_ltv
mart_payback

The final dimensions and fact grains will only be confirmed after
source profiling.

6. Engineering Principles

The project will follow these principles:

Understand data before transformation.
Define grain before designing fact tables.
Validate business keys before building dimensions.
Preserve raw source information.
Separate ingestion from transformation.
Synthetic data must preserve referential integrity.
Synthetic data must be clearly identified.
Data quality checks are part of the pipeline.
Pipelines must be idempotent where practical.
Secrets must never be committed to Git.
Cost and performance are treated as engineering concerns.
Every major component must include documentation and validation.
7. Initial Technology Stack
Language
Python
SQL
Cloud
Google Cloud Platform
Google Cloud Storage
BigQuery
Pub/Sub
Compute Engine
Transformation
dbt
BigQuery SQL
Orchestration
Apache Airflow
Celery
Redis
Runtime
Docker
Docker Compose
Analytics
Streamlit
Looker Studio or Metabase
ML
BigQuery ML
Python where necessary
AI Integration
Model Context Protocol
custom read-only data tools
Engineering
Git
GitHub
GitHub Actions
8. Out of Scope for Initial Checkpoints

The following will not be implemented before the batch data foundation
is validated:

MCP server
Streamlit application
ML models
CeleryExecutor
near-real-time Pub/Sub pipeline
production deployment
CI/CD deployment

These components depend on a stable data foundation.

9. Success Criteria

The project is considered complete when it demonstrates:

real mobile event ingestion
batch data pipeline
near-real-time event processing
BigQuery partitioning and clustering
dbt transformations
dimensional modeling
Growth / AdTech metrics
Airflow orchestration
Celery / Redis distributed execution
automated data quality
operational observability
ML-ready user features
at least one ML use case
internal analytics application
secured MCP data tools
CI/CD
cloud deployment
architecture and data-dictionary documentation
10. CP0 Decision

Primary real dataset:

firebase-public-project.analytics_153293282.events_*

Decision:

GO

Reason:

The dataset represents real mobile-game event behavior and provides a
sufficient foundation for ingestion, behavioral analytics, retention,
ML features, nested-data processing, and event modeling.

MMP attribution, advertising, and monetization datasets will be added
later as controlled synthetic sources rather than falsely presented as
production third-party API data.