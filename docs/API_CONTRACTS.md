# API Contracts

This document defines the strict field schemas expected across the frontend and backend for Project SOC. Tests in both environments enforce these contracts. If an entity needs to be updated, update the contract here, the backend Pydantic models, and the frontend mock schemas and test files.

## Alerts

Endpoint: `/api/alerts`
Backend Model: `AlertResponse`

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique Alert ID (used in frontend for routing/tables). Note: Backend ES uses `_id` and maps to `id` |
| `entity_key` | `str` | Subject of alert (Host\|User) |
| `threat_score` | `float` | ML severity score (0.0 - 1.0) |
| `threat_level` | `str` | Categorical level (critical, high, medium, low) |
| `top_features` | `list[str]` | SHAP derived reasoning features |
| `triggered_rules` | `list[str]` | Suricata/Yara rule hits |
| `mitre_tactics` | `list[str]` | Linked MITRE tactics |
| `human_explanation` | `str` | Plaintext explanation of anomaly |
| `timestamp` | `str` | ISO-8601 timestamp |
| `status` | `str` | Alert state (open, in_progress, closed) |

## Incidents

Endpoint: `/api/incidents`
Backend Model: `IncidentResponse`

| Field | Type | Description |
|---|---|---|
| `incident_id` | `str` | Unique Incident ID |
| `entity_key` | `str` | Host/User string identifier |
| `host_id` | `str` | Host portion |
| `user_name` | `str` | User portion (nullable) |
| `started_at` | `str` | ISO-8601 initial alert time |
| `last_seen` | `str` | ISO-8601 latest alert time |
| `duration_seconds` | `float` | Seconds duration of incident |
| `alert_count` | `int` | Number of correlated alerts |
| `log_types_involved` | `list[str]` | Data sources hit |
| `max_threat_score` | `float` | Highest score among alerts |
| `incident_threat_score` | `float` | Calculated composite score |
| `threat_level` | `str` | Mapped threat severity |
| `mitre_tactics` | `list[str]` | Array of tactics observed |
| `mitre_techniques` | `list[str]` | Array of specific techniques |
| `attack_stage` | `str` | Current Kill-Chain stage |
| `is_multi_stage` | `bool` | True if spanning multiple tactics |
| `status` | `str` | active, resolved, escalated |
| `created_at` | `str` | Time incident created |

## Chat / SLM

Endpoint: `/api/slm/chat`
Backend Model: `ChatResponse`

| Field | Type | Description |
|---|---|---|
| `conversation_id` | `str` | ID of the conversation thread |
| `message` | `dict` | Contains `role`, `content`, `timestamp` |
| `sources` | `list[str]` | Contextual data chunks used |
| `tools_used` | `list[str]` | Internal tools invoked |
| `response_time_ms` | `float` | Generation timing |
