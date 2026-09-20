# Canonical Event Schema

## 1. Purpose

This document defines the canonical event contract between the raw
Firebase / GA4 source data and downstream analytical models.

Source:

`firebase-public-project.analytics_153293282.events_*`

The canonical model is designed after profiling:

- 5,700,000 events
- 15,175 users
- 114 active dates
- 37 event types
- nested and repeated event parameters
- heterogeneous parameter value types
- 207 candidate duplicate rows
- 59 confirmed exact duplicate rows

---

## 2. Layer Responsibilities

### Bronze

Bronze preserves source-aligned data.

Grain:

> One row represents one source row exactly as received from the
> Firebase public dataset.

Bronze does not remove exact duplicates.

Responsibilities:

- preserve nested source structures
- preserve source timestamps
- preserve event parameters
- preserve user properties
- add ingestion metadata
- support replay and audit

Expected Bronze row count for the initial historical load:

`5,700,000`

---

### Silver

Silver provides the canonical analytical event model.

Grain:

> One row represents one unique source application event after
> exact full-row duplicate removal.

Silver responsibilities:

- remove confirmed exact duplicates
- convert source dates and timestamps
- normalize commonly used attributes
- promote important event parameters
- classify events into analytical categories
- preserve source-level traceability
- retain access to non-promoted event parameters

Silver must NOT deduplicate using only:

`user_pseudo_id + event_name + event_timestamp`

Source profiling showed that this combination identifies 207 candidate
duplicate rows while only 59 rows are exact full-row duplicates.

---

## 3. Event Identity Strategy

The historical source does not provide a guaranteed globally unique
event ID.

A deterministic source-event fingerprint will therefore be generated
from the complete source row before ingestion metadata is added.

Conceptually:

```text
source_event_hash =
SHA256(
    source_system
    +
    canonical representation of complete source row
)

For this project:

source_system = firebase_floodit

The canonical event identifier will be derived from the same source
payload:

event_id = source_event_hash

Properties:

deterministic
reproducible
independent of ingestion run
identical exact source rows generate the same identifier
reprocessing the same event does not create a new event identity

Ingestion metadata must NOT participate in event ID generation.

4. Canonical Event Grain

Silver canonical event grain:

One unique source event payload.

Examples:

one screen_view
one user_engagement
one level_start
one post_score
one purchase
one ad_reward

Multiple events from the same user at the same timestamp may remain
separate when their complete source payloads differ.

5. Core Canonical Fields
Field	Type	Required	Description
event_id	STRING	Yes	Deterministic source event identifier
source_event_hash	STRING	Yes	SHA256 fingerprint of source payload
event_date	DATE	Yes	Source reporting date
event_timestamp_utc	TIMESTAMP	Yes	Event timestamp converted from microseconds
event_timestamp_raw	INT64	Yes	Original source timestamp
event_name	STRING	Yes	Source event name
event_category	STRING	Yes	Analytical event classification
user_pseudo_id	STRING	Yes	Anonymous source user identifier
platform	STRING	Yes	ANDROID or IOS
app_id	STRING	No	Source application identifier
6. Device Attributes

Promoted device fields:

Field	Type
device_category	STRING
operating_system	STRING
operating_system_version	STRING
device_language	STRING
mobile_brand_name	STRING
mobile_model_name	STRING

Device attributes remain descriptive event context.

A future Gold device dimension may be created after validating
cardinality and analytical requirements.

7. Geography Attributes

Promoted geography fields:

Field	Type
country	STRING
region	STRING
city	STRING
continent	STRING
sub_continent	STRING

Geographic attributes are retained at event level in Silver.

Gold dimensional modeling will determine which geographic fields belong
in reusable dimensions.

8. Acquisition Attributes

Promoted source acquisition fields:

Field	Type
traffic_source	STRING
traffic_medium	STRING
traffic_campaign	STRING

These fields describe the acquisition information available in the real
Firebase source.

They are not treated as complete MMP attribution data.

A separate synthetic MMP dataset will later provide richer campaign,
ad group, creative and attribution information.

9. Promoted Event Parameters

The source stores business attributes inside the repeated
event_params structure.

Frequently used analytical parameters will be promoted into typed
Silver columns.

Engagement
Parameter	Canonical Field	Type
engagement_time_msec	engagement_time_msec	INT64
Gameplay
Parameter	Canonical Field	Type
board	board	STRING
level	level	FLOAT64
level_name	level_name	STRING
score	score	FLOAT64
value	event_value	FLOAT64
time	gameplay_time	FLOAT64
Monetization
Parameter	Canonical Field	Type
product_id	product_id	STRING
product_name	product_name	STRING
quantity	quantity	INT64
price	price	FLOAT64
currency	currency	STRING
validated	purchase_validated	BOOL
Advertising Reward
Parameter	Canonical Field	Type
ad_unit_code	ad_unit_code	STRING
type	ad_reward_type	STRING
ad_event_id	ad_event_id	INT64
10. Event Parameter Normalization

Event parameter values may physically appear in:

string_value
int_value
float_value
double_value

A parameter key cannot always be assumed to use only one physical
value field.

Therefore Silver transformations must extract values according to the
expected analytical type.

Example numeric normalization:

int_value
float_value
double_value
      ↓
FLOAT64 canonical business value

Example string normalization:

string_value
      ↓
STRING canonical business value

Raw event parameters remain available for fields that are not promoted.

11. Event Categories

Canonical events will initially be classified into the following
analytical groups.

engagement

Examples:

screen_view
user_engagement
session_start
select_content
gameplay

Examples:

level_start
level_end
level_complete
level_fail
level_retry
level_reset
level_up

level_start_quickplay
level_end_quickplay
level_complete_quickplay
level_fail_quickplay
level_retry_quickplay
level_reset_quickplay

post_score
use_extra_steps
no_more_extra_steps
completed_5_levels
monetization

Examples:

in_app_purchase
spend_virtual_currency
ad_reward
acquisition

Examples:

firebase_campaign
dynamic_link_app_open
dynamic_link_first_open
lifecycle

Examples:

first_open
app_update
app_remove
os_update
app_clear_data
technical

Examples:

app_exception
error
social

Examples:

challenge_a_friend
challenge_accepted

Events not explicitly mapped will use:

other

The event category is an analytical convenience and does not replace
the original event_name.

12. Timestamp Strategy

The source contains:

event_date
event_timestamp

These fields represent different concepts and must both be preserved.

Canonical fields:

event_date
event_timestamp_raw
event_timestamp_utc

Transformation:

PARSE_DATE('%Y%m%d', event_date)

TIMESTAMP_MICROS(event_timestamp)

The source event_date must not be overwritten using the UTC timestamp,
because source reporting-date semantics may differ from UTC calendar
date.

13. Exact Duplicate Strategy

Profiling found:

candidate duplicate rows = 207
exact duplicate rows     = 59

Bronze:

keep all source rows

Silver:

partition by source_event_hash
order deterministically
keep one row

This removes only exact source duplicates.

The pipeline must not deduplicate events merely because they have the
same user, event name and timestamp.

14. Raw Parameter Preservation

Promoting frequently used parameters must not discard the original
semi-structured information.

Silver will retain a serialized representation of source parameters:

event_params_json

This supports:

debugging
schema evolution
future parameter promotion
replay
auditing

Bronze remains the authoritative raw copy.

15. Ingestion Metadata

The Bronze layer will later add metadata such as:

Field	Purpose
ingestion_run_id	Identify ingestion execution
ingested_at	Load timestamp
source_system	Source identifier
source_table	Physical source table
source_date	Source partition/date
pipeline_version	Pipeline/code version

These fields support operational lineage.

They do NOT participate in event_id.

16. Expected Flow
Firebase daily tables
        |
        v
GCS landing
        |
        v
BigQuery Bronze
5.7M raw rows
        |
        | exact-row fingerprint
        | type normalization
        | parameter extraction
        | event classification
        v
Silver canonical_event
        |
        +-------------------------+
        |                         |
        v                         v
Product / Growth Gold       ML Feature Models
17. Data Contract Rules

The following Silver fields are mandatory:

event_id
source_event_hash
event_date
event_timestamp_raw
event_timestamp_utc
event_name
event_category
user_pseudo_id
platform

A canonical Silver row must satisfy:

event_id is not null.
event_name is not null.
user_pseudo_id is not null.
platform is not null.
event_timestamp_utc is valid.
event_date is valid.
event_category is assigned.
source_event_hash is unique after exact deduplication.
18. CP3 Decision

Canonical event grain:

APPROVED

Event identity strategy:

APPROVED

Exact duplicate strategy:

APPROVED

Parameter promotion strategy:

APPROVED

Transformation implementation:

NOT STARTED

Decision:

GO TO BATCH INGESTION DESIGN

## 19. CP3 Validation Results

Canonical event identity and classification were validated against the
complete 5.7M-event source.

### Event Identity

| Metric | Result |
|---|---:|
| Bronze source rows | 5,700,000 |
| Expected Silver rows | 5,699,941 |
| Exact duplicate rows removed | 59 |

The deterministic full-source-payload fingerprint therefore produces
the expected canonical Silver grain.

### Event Categories

| Category | Events |
|---|---:|
| engagement | 3,786,073 |
| gameplay | 1,877,038 |
| lifecycle | 12,741 |
| monetization | 11,302 |
| technical | 6,870 |
| acquisition | 5,446 |
| social | 529 |
| other | 1 |

The only event currently using the fallback `other` category is:

`notification_foreground`

The fallback category is intentionally retained so previously unseen
event types are not silently misclassified.

### CP3 Status

Canonical event grain:

**VALIDATED**

Event identity strategy:

**VALIDATED**

Exact duplicate strategy:

**VALIDATED**

Event classification:

**VALIDATED**

Decision:

**CP3 PASS**