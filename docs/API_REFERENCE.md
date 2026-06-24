# ISRO SOC Platform — Complete API Reference

Base URL: `http://localhost:8000` (dev) | `https://soc.istrac.isro.gov.in` (prod)
Authentication: Bearer JWT token (obtain via POST `/api/auth/login`)

## Authentication
| Method | Endpoint | Description | Role Required |
|--------|----------|--------------|----------------|
| POST | /api/auth/login | Login | None |
| GET | /api/auth/me | Read Users Me | Any Valid User |
| POST | /api/auth/logout | Logout | Any Valid User |

## Health & Monitoring

### GET /health
**Liveness Probe**

Returns 200 OK instantly.

- **Role Required**: None
- **Rate Limit**: Standard

**Response (200 OK):**
```json
{
  "key1": true
}
```

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/health' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /health/ready
**Readiness Probe**

- **Role Required**: None
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/health/ready' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /health/deep
**Deep Health Check**

- **Role Required**: None
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/health/deep' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /health/metrics
**System Resource Metrics**

- **Role Required**: None
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/health/metrics' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## Ingestion

### GET /api/ingestion/status
**Get Ingestion Status**

Returns the live in-memory state of the ingestion scheduler.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/ingestion/status' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/ingestion/run
**Trigger Ingestion Cycle**

Manually triggers the ingestion pipeline synchronously.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/ingestion/run' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## Features

### GET /api/features/api/features/run
**Run Features Manually**

Triggers run_feature_pipeline manually.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/features/api/features/run' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/features/api/features/latest
**Get Latest Features**

Queries soc-feature-vectors for most recent window_bucket, returns up to 100 records.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/features/api/features/latest' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/features/api/features/{entity_key}
**Get Entity Features**

Returns feature vector history for entity (last 24h).

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `entity_key` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/features/api/features/{entity_key}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## Alerts

### GET /api/alerts
**Get Alerts List**

Fetches ML processed alerts querying across elastic fields scaling with deep pagination arrays.

- **Role Required**: Any Valid User
- **Rate Limit**: 300 requests/minute

**Query Parameters:**
- `status` (Optional): Filter by status (open, closed)
- `threat_level` (Optional): Filter by level (critical, high, medium, low)
- `host_id` (Optional): Filter by origin host ID
- `user_name` (Optional): Filter by active user context
- `from_time` (Optional): ISO timestamp baseline
- `to_time` (Optional): ISO timestamp ceiling
- `limit` (Optional): 
- `offset` (Optional): 

**Response (200 OK):**
```json
{
  "total": 0,
  "alerts": [
    {
      "id": "string",
      "entity_key": "string",
      "threat_score": 0.0,
      "threat_level": "string",
      "top_features": [
        {}
      ],
      "triggered_rules": [
        {}
      ],
      "mitre_tactics": [
        {}
      ],
      "human_explanation": "string",
      "timestamp": "string",
      "status": "string"
    }
  ],
  "page": 0
}
```

**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/alerts' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/alerts/stats
**Get Stats**

Generates complex ES aggregations tracking pipeline security throughput explicitly mapping to React UI dashboards.

- **Role Required**: Any Valid User
- **Rate Limit**: 300 requests/minute

**Response (200 OK):**
```json
{
  "total_open": 0,
  "critical": 0,
  "high": 0,
  "medium": 0,
  "low": 0,
  "top_tactics": [
    {
      "key1": true
    }
  ],
  "top_hosts": [
    {
      "key1": true
    }
  ],
  "alerts_last_24h": 0
}
```

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/alerts/stats' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/alerts/trigger-scoring
**Trigger Scoring**

Manually forces Threat Engine execution spanning the whole extraction pipeline synchronously.

- **Role Required**: Any Valid User
- **Rate Limit**: 300 requests/minute

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/alerts/trigger-scoring' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/alerts/{alert_id}
**Get Alert**

Resolves singular specific alerts returning precise SHAP features and translation mappings.

- **Role Required**: Any Valid User
- **Rate Limit**: 300 requests/minute

**Query Parameters:**
- `alert_id` (Required): 

**Response (200 OK):**
```json
{
  "id": "string",
  "entity_key": "string",
  "threat_score": 0.0,
  "threat_level": "string",
  "top_features": [
    "string"
  ],
  "triggered_rules": [
    "string"
  ],
  "mitre_tactics": [
    "string"
  ],
  "human_explanation": "string",
  "timestamp": "string",
  "status": "string"
}
```

**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/alerts/{alert_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### PATCH /api/alerts/{alert_id}/status
**Update Status**

Allows UI triage handlers mapping interactive state flows directly natively over ES document fields.

- **Role Required**: Any Valid User
- **Rate Limit**: 300 requests/minute

**Query Parameters:**
- `alert_id` (Required): 

**Request Body:**
```json
{
  "status": "string"
}
```

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'PATCH' \ 
  'http://localhost:8000/api/alerts/{alert_id}/status' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \ 
  -H 'Content-Type: application/json' \ 
  -d '{"status": "string"}'
```

---

### GET /api/alerts/{alert_id}/timeline
**Get Timeline**

Constructs localized chronological execution limits tracking identically mapped anomalies spanning exact same entities.

- **Role Required**: Any Valid User
- **Rate Limit**: 300 requests/minute

**Query Parameters:**
- `alert_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/alerts/{alert_id}/timeline' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## Incidents

### GET /api/incidents
**List Incidents**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `status` (Optional): 
- `attack_stage` (Optional): 
- `threat_level` (Optional): 
- `host_id` (Optional): 
- `limit` (Optional): 
- `offset` (Optional): 

**Response (200 OK):**
```json
{
  "key1": true
}
```

**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/incidents' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/incidents/stats
**Get Incident Stats**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
```json
{
  "total_active": 0,
  "multi_stage_count": 0,
  "by_attack_stage": {
    "key1": 0
  },
  "by_threat_level": {
    "key1": 0
  },
  "avg_duration_minutes": 0.0,
  "top_targeted_hosts": [
    {
      "key1": true
    }
  ]
}
```

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/incidents/stats' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/incidents/{incident_id}
**Get Incident Detail**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `incident_id` (Required): 

**Response (200 OK):**
```json
{
  "incident_id": "string",
  "entity_key": "string",
  "host_id": "string",
  "user_name": "string",
  "started_at": "2026-06-24T18:00:00Z",
  "last_seen": "2026-06-24T18:00:00Z",
  "duration_seconds": 0.0,
  "alert_count": 0,
  "log_types_involved": [
    "string"
  ],
  "max_threat_score": 0.0,
  "incident_threat_score": 0.0,
  "threat_level": "string",
  "mitre_tactics": [
    "string"
  ],
  "mitre_techniques": [
    "string"
  ],
  "attack_stage": "string",
  "is_multi_stage": true,
  "status": "string",
  "created_at": "2026-06-24T18:00:00Z",
  "matched_patterns": [
    {
      "key1": true
    }
  ],
  "alerts": [
    {
      "key1": true
    }
  ],
  "timeline": [
    {
      "key1": true
    }
  ],
  "attack_chain": [
    {
      "key1": true
    }
  ]
}
```

**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/incidents/{incident_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### PATCH /api/incidents/{incident_id}/status
**Update Incident Status**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `incident_id` (Required): 

**Request Body:**
```json
{
  "status": "string",
  "notes": "string"
}
```

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'PATCH' \ 
  'http://localhost:8000/api/incidents/{incident_id}/status' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \ 
  -H 'Content-Type: application/json' \ 
  -d '{"status": "string", "notes": "string"}'
```

---

### POST /api/incidents/{incident_id}/escalate
**Escalate Incident**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `incident_id` (Required): 

**Request Body:**
```json
{
  "escalated_to": "string",
  "reason": "string"
}
```

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/incidents/{incident_id}/escalate' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \ 
  -H 'Content-Type: application/json' \ 
  -d '{"escalated_to": "string", "reason": "string"}'
```

---

### GET /api/incidents/{incident_id}/investigate
**Investigate Incident**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `incident_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/incidents/{incident_id}/investigate' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## Feedback

### POST /api/feedback
**Post Feedback**

Submits manual triage labels dropping mapped boundaries sequentially matching ES indices.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Request Body:**
```json
{
  "alert_id": "string",
  "analyst_name": "string",
  "label": "string",
  "notes": "string",
  "mitre_override": [
    "string"
  ]
}
```

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/feedback' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \ 
  -H 'Content-Type: application/json' \ 
  -d '{"alert_id": "string", "analyst_name": "string", "label": "string", "notes": "string", "mitre_override": ["string"]}'
```

---

### GET /api/feedback
**Fetch Feedback**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `label` (Optional): 
- `limit` (Optional): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/feedback' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/feedback/stats
**Get Stats**

Calculates active system efficacy identifying accurate TP vs FP suppression bounds.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/feedback/stats' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/feedback/suppressed
**Fetch Suppression Rules**

Generates transparency exposing tracking metrics identifying blocked mapping entities.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/feedback/suppressed' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/feedback/labeling-queue
**Get Labeling Queue Api**

Returns prioritized list from get_labeling_queue

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `n` (Optional): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/feedback/labeling-queue' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/feedback/labeling-stats
**Get Labeling Stats Api**

Returns stats from get_labeling_stats

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/feedback/labeling-stats' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## Training

### POST /api/training/initial
**Trigger Initial Training**

Triggers complete baseline ML training pipeline executing arrays synchronously asynchronously in background routines.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/training/initial' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/training/incremental
**Trigger Incremental Retraining**

Executes incremental bounds retraining overlapping existing artifacts mapping new specific explicit feature vectors.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/training/incremental' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/status/{job_id}
**Get Job Status**

Retrieves ephemeral background ML training job contexts safely tracking local execution metrics.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `job_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/status/{job_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/status
**Get Training Status**

Generates complete model versioning mapping cleanly leveraging underlying MLFlow experiment log pipelines.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/status' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/drift
**Get Drift Status**

Returns the latest model drift report.

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/drift' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/interpretability
**Get Interpretability Report**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/interpretability' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/mlflow/experiments
**List Experiments**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/mlflow/experiments' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/mlflow/runs/{experiment_id}
**List Runs**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `experiment_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/mlflow/runs/{experiment_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/mlflow/runs/detail/{run_id}
**Get Run Details**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `run_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/mlflow/runs/detail/{run_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/mlflow/compare
**Compare Runs**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `run_ids` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/mlflow/compare' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/training/calibration
**Get Calibration Stats**

Returns calibration stats, AUC-ROC, Brier score, n_samples

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/training/calibration' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/training/calibration
**Trigger Calibration Training**

Manually trigger calibration training

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/training/calibration' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## SLM

### POST /api/slm/chat
**Chat Endpoint**

- **Role Required**: Any Valid User
- **Rate Limit**: 60 requests/minute

**Request Body:**
```json
{
  "message": "string",
  "alert_id": "string",
  "incident_id": "string",
  "conversation_id": "string"
}
```

**Response (200 OK):**
```json
{
  "conversation_id": "string",
  "message": {
    "role": "string",
    "content": "string",
    "timestamp": "2026-06-24T18:00:00Z"
  },
  "sources": [
    "string"
  ],
  "tools_used": [
    "string"
  ],
  "response_time_ms": 0.0,
  "parsed_response": {
    "key1": true
  }
}
```

**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/slm/chat' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \ 
  -H 'Content-Type: application/json' \ 
  -d '{"message": "string", "alert_id": "string", "incident_id": "string", "conversation_id": "string"}'
```

---

### GET /api/slm/conversations
**List Conversations**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/slm/conversations' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### DELETE /api/slm/conversations/{conversation_id}
**Clear Conversation**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `conversation_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'DELETE' \ 
  'http://localhost:8000/api/slm/conversations/{conversation_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/slm/explain/{alert_id}
**Explain Alert**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `alert_id` (Required): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/slm/explain/{alert_id}' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/slm/status
**Slm Status**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/slm/status' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/slm/reload-model
**Reload Model**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Request Body:**
```json
{
  "model": "string"
}
```

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/slm/reload-model' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>' \ 
  -H 'Content-Type: application/json' \ 
  -d '{"model": "string"}'
```

---

### GET /api/slm/model-info
**Model Info**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/slm/model-info' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/slm/rag/reindex
**Rag Reindex**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/slm/rag/reindex' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/slm/rag/stats
**Rag Stats**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/slm/rag/stats' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### DELETE /api/slm/rag/clear
**Rag Clear**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `confirm` (Optional): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'DELETE' \ 
  'http://localhost:8000/api/slm/rag/clear' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/slm/metrics
**Get Slm Metrics**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Query Parameters:**
- `since_hours` (Optional): 

**Response (200 OK):**
**Possible Errors:**
- **422**: Validation Error

**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/slm/metrics' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### GET /api/slm/cache/stats
**Cache Stats**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'GET' \ 
  'http://localhost:8000/api/slm/cache/stats' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### DELETE /api/slm/cache/clear
**Cache Clear**

- **Role Required**: Any Valid User
- **Rate Limit**: Standard

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'DELETE' \ 
  'http://localhost:8000/api/slm/cache/clear' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

### POST /api/slm/chat/stream
**Chat Stream**

Streams raw SLMEngine outputs utilizing Transformers TextIteratorStreamer and Server-Sent Events natively.

- **Role Required**: Any Valid User
- **Rate Limit**: 60 requests/minute

**Response (200 OK):**
**cURL Example:**
```bash
curl -X 'POST' \ 
  'http://localhost:8000/api/slm/chat/stream' \ 
  -H 'accept: application/json' \ 
  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'
```

---

## WebSocket
The platform pushes real-time events via `ws://localhost:8000/api/ws/alerts`.

### Connection
To connect, pass your JWT token as a query parameter (or header):
`ws://localhost:8000/api/ws/alerts?token=<JWT_TOKEN>`

### Event: `stats_update`
Emitted every 60 seconds with global threat counts.
```json
{
  "type": "stats_update",
  "data": {
    "critical": 2,
    "high": 14,
    "medium": 45,
    "low": 120,
    "total": 181
  }
}
```

### Event: `sla_warning`
Emitted when critical incidents are nearing response breach.
```json
{
  "type": "sla_warning",
  "data": [
    {
      "incident_id": "INC-889",
      "time_remaining_minutes": 10,
      "assigned_team": "Team Alpha"
    }
  ]
}
```

### Event: `scoring_complete`
Emitted after an ML cycle finishes.
```json
{
  "type": "scoring_complete",
  "data": {
    "scored": 450,
    "critical": 1,
    "high": 3,
    "medium": 12,
    "low": 434,
    "cycle_time_ms": 1405.2,
    "timestamp": "2026-06-24T18:00:00Z"
  }
}
```