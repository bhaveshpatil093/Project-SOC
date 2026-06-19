# ISRO ISTRAC SOC AI Platform Architecture

## System Overview Diagram

```text
    [ Raw Log Sources ]                 [ Security Analysts (UI) ]
     | (syslog, win, process)                  ^
     v                                         |
+--------------------------------------------------------------+
|                    ISRO ISTRAC SOC PLATFORM                  |
+--------------------------------------------------------------+
     |                                         ^
     v                                         |
 [ Elasticsearch ] (Raw Logs)             [ React Frontend ]
     |                                         ^
     | (1. Ingestion Cycle)                    | (WebSocket / REST)
     v                                         |
 [ Scheduler (APScheduler) ]                   |
     |                                         |
     v                                         |
 [ Normalizer & Enrichment ]                   |
     |                                         |
     | (2. Feature Extraction)                 |
     v                                         |
 [ Feature Pipeline (Pandas) ]                 |
     |                                         |
     v                                         |
 [ ML Threat Engine ]                          |
   |- Isolation Forest (Network/Volume)        |
   |- Autoencoder (Process/Payload)            |
   |- LSTM (Time-series)                       |
   |- Rule Engine (Heuristics)                 |
     |                                         |
     | (3. Scoring & Thresholds)               |
     v                                         |
 [ SHAP Explainability ]                       |
     |                                         |
     v                                         |
 [ Elasticsearch ] (Alerts Processed)          |
     |                                         |
     | (4. Investigation & RAG)                |
     v                                         |
 [ SOCAgent (LangChain) ] ---------------------+
   |- Phi-3-mini-4k (Fine-tuned SLM)
   |- RAG Vector DB (ChromaDB)
   |- Dual-Tier Cache (Exact & Semantic)
   |- SLMEvaluator (Metrics mapping)
```

---

## Core Components

### 1. Ingestion Engine
- **Responsibility**: Fetch raw logs from Elasticsearch (syslog, windows, process), normalize them into a standard schema, and assign an `entity_key` hash.
- **Technology**: `elasticsearch-dsl`, `APScheduler` (5-min intervals).
- **Index**: Reads from raw cluster indices, writes pre-processed payloads back to `soc-alerts-processed` dynamically.

### 2. Feature Pipeline
- **Responsibility**: Aggregates categorical and numerical data into highly structured numeric matrices (e.g., `unique_dst_port_count`, `has_encoded_payload`, `failed_login_count`).
- **Technology**: `pandas`, vectorized NumPy arrays tracking 5-minute sliding `window_bucket` states.

### 3. ML Threat Engine
- **Responsibility**: Detect anomalies across all structured vectors.
- **Models**:
  - **Isolation Forest**: Detects volume-based anomalies (e.g., Port scans, massive outbound data transfers).
  - **Autoencoder (PyTorch)**: Detects deep payload anomalies using reconstruction loss matrices (e.g., encoded powershell).
  - **Rule Engine**: Standard SOC heuristic boundaries mapping explicit IF/THEN constraints (e.g., `RULE-002` for exactly >50 failed logins).
- **Output**: Generates a unified `threat_score` ranging between 0.0 and 1.0. Alerts > 0.3 trigger SHAP.

### 4. SHAP Explainability Engine
- **Responsibility**: Automatically computes partial dependency boundaries assigning weight contributions to the highest triggering features.
- **Output**: Populates `human_explanation` (e.g., "Alert triggered heavily due to unique_dst_port_count = 80").

### 5. SLM Assistant (Phi-3-mini)
- **Responsibility**: Read security matrices and chat dynamically with L1 analysts providing triage, investigation, and remediation boundaries natively.
- **Components**:
  - **SLMEngine**: Manages `fp16` quantization and model hot-swapping natively.
  - **RAG Pipeline**: Vectorizes historical alerts allowing the agent to dynamically reference past attacks natively via `ChromaDB`.
  - **Cache System**: Two-layer structure mapping explicit Exact hashes and `>0.92` cosine similarity semantic matches cleanly.
  - **Evaluator**: Dynamically reads response structs tracking latency and quality scores securely.

---

## Index Schemas

| Index Name | Purpose | Retention |
|---|---|---|
| `logs-system.syslog-*` | Raw Linux/network syslogs | 30 Days |
| `logs-endpoint.events.*` | Raw Process creation telemetry | 30 Days |
| `logs-windows.*` | Raw Windows security events | 30 Days |
| `soc-alerts-processed` | Normalized entities enriched with `threat_score` | 90 Days |
| `soc-feedback-loop` | User generated FALSE_POSITIVE suppression matrices | 1 Year |
| `soc-slm-metrics` | Telemetry mapping Latency, Tokens, Quality | 1 Year |

---

## API Summary (Key Endpoints)

| Endpoint | Method | Component | Description |
|---|---|---|---|
| `/api/ingestion/run` | POST | Scheduler | Triggers an immediate log fetch and normalization cycle. |
| `/api/features/run` | GET | Feature Pipeline | Dumps the active numeric ML vector constraints. |
| `/api/alerts/trigger-scoring` | POST | Threat Engine | Forces the ML models to score all recent entities natively. |
| `/api/alerts` | GET | Alert Store | Retrieves the paginated table of prioritized alerts. |
| `/api/slm/chat/stream` | POST | SLM Engine | Connects the generative LLM stream over SSE dynamically. |
| `/api/slm/rag/reindex` | POST | RAG DB | Background task extracting ES histories into ChromaDB vectors. |
| `/api/slm/metrics` | GET | Evaluator | Surfaces throughput, latency, and quality matrices dynamically. |
