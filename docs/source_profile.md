# Source Data Profile

## Dataset

Source:

`firebase-public-project.analytics_153293282.events_*`

Domain:

Mobile game analytics.

The dataset contains historical Firebase / Google Analytics application
events from the Flood-It! mobile game.

---

## Dataset Grain

Initial source grain:

> One row represents one application event.

The source contains nested and repeated structures, especially:

- event_params
- user_properties
- device
- geo
- app_info
- traffic_source

The final canonical event grain has not yet been defined.

---

## Baseline

Initial profiling result:

| Metric | Result |
|---|---:|
| Total events | 5,700,000 |
| Distinct users | 15,175 |
| Active dates | 114 |
| Minimum event date | 2018-06-12 |
| Maximum event date | 2018-10-03 |

---

## Top Events

Initial observations:

| Event | Events | Users |
|---|---:|---:|
| screen_view | 2,247,623 | 14,077 |
| user_engagement | 1,358,958 | 13,588 |
| level_start_quickplay | 523,430 | 10,166 |
| level_end_quickplay | 349,729 | 8,168 |
| post_score | 242,051 | 8,580 |

These counts show that the source contains both:

- application/system analytics events
- gameplay-specific business events

These categories should not automatically be modeled identically.

---

## Event Timestamp

`event_timestamp` is stored as an integer representing Unix time in
microseconds.

Example transformation:

```sql
TIMESTAMP_MICROS(event_timestamp)

The raw integer should be retained in the ingestion layer while a typed
timestamp can be created in the standardized layer.

User Identifier

Primary observed anonymous user identifier:

user_pseudo_id

This field will initially be treated as the source user identifier.

It is not yet assumed to represent a permanent business-level user ID.

Nested Event Parameters

event_params is a repeated nested structure.

Conceptually:

event
 |
 +-- event_params[]
       |
       +-- key
       |
       +-- value
             |
             +-- string_value
             +-- int_value
             +-- float_value
             +-- double_value

Different event types can contain different parameter keys.

Therefore, the pipeline must profile event parameters before deciding
which attributes should become standardized Silver columns.

Initial Modeling Observations

The source should not immediately be flattened into one very wide table.

Potential event groups include:

Application lifecycle
Engagement
Screen navigation
Gameplay
Progression
Monetization
Acquisition

The exact classification will be determined after full event-name and
event-parameter profiling.

Duplicate Strategy

The source does not currently expose a confirmed globally unique
event_id.

A candidate duplicate signature being investigated is:

user_pseudo_id
+
event_name
+
event_timestamp

However, records sharing these values must not automatically be deleted.

Additional parameters and event context must be investigated before
defining a deduplication rule.

CP2 Questions

The profiling stage must answer:

Which event types exist?
Which events are relevant to Product and Growth analytics?
Which parameter keys belong to each event type?
Which parameter data types are actually used?
How complete are the core event fields?
What platforms, devices, applications, and countries exist?
What does user activity distribution look like?
Are apparent duplicate events true duplicates?
Which fields should remain nested in Raw?
Which fields should be promoted into the canonical Silver event model?
Status

Source discovery:

IN PROGRESS

Canonical event schema:

NOT YET APPROVED

Transformation implementation:

BLOCKED UNTIL SOURCE PROFILING IS COMPLETE

## Duplicate Investigation

An initial duplicate candidate signature was tested:

```text
user_pseudo_id
+
event_name
+
event_timestamp

Results:

Metric	Result
Candidate duplicate groups	207
Rows in candidate groups	414
Potential extra rows	207

A second validation compared complete event rows using a fingerprint of
the full JSON representation.

Results:

Metric	Result
Exact duplicate groups	59
Rows in exact duplicate groups	118
Exact duplicate rows	59

Therefore:

user_pseudo_id + event_name + event_timestamp must not be used as
the final deduplication key.

Only 59 of the 207 potential duplicate rows were exact full-row
duplicates.

The remaining candidate rows contain differences elsewhere in the event
payload or context.

Raw/Bronze data will preserve all source records.

Exact-row deduplication may be applied in Silver after the canonical
event strategy is defined.

```markdown
## Event Parameter Findings

Event parameters are event-type specific.

Examples:

### ad_reward

Important parameters:

```text
value         -> INT64
type          -> STRING
ad_unit_code  -> STRING
ad_event_id   -> INT64
in_app_purchase

Important parameters:

product_id    -> STRING
product_name  -> STRING
quantity      -> INT64
price         -> INT64
value         -> INT64
currency      -> STRING
validated     -> INT64
level_complete

Important parameters:

level_name    -> STRING
level         -> DOUBLE
value         -> DOUBLE

Parameter physical types are not always globally stable.

For example, firebase_screen_id under level_complete appears as both
integer and double values.

Therefore, parameter normalization must inspect the populated value
field rather than assuming a universal physical type for every key.