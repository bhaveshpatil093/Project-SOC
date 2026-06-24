# ISRO ISTRAC SOC AI Platform — Data Flow Diagrams

This document contains detailed sequence diagrams mapping the core logical pathways within the SOC AI Platform. These diagrams are critical for understanding how state propagates between the Python ingestion engine, the Elasticsearch backend, the ML processes, and the React frontend.

---

## 1. Single Log to Alert Flow (Happy Path)
This represents the asynchronous, 5-minute batch pipeline where raw endpoint logs are transformed into mathematically scored threat alerts.

```mermaid
sequenceDiagram
    autonumber
    participant Endpoint as Endpoints / Firewalls
    participant LS as Logstash
    participant ESRaw as Elasticsearch (Raw)
    participant Fetcher as Log Fetcher (APScheduler)
    participant Normalizer as Normalizer / Merger
    participant ML as Threat Engine (IF / AE)
    participant DB as Elasticsearch (soc-alerts)

    Endpoint->>LS: Push raw syslog / process telemetry
    LS->>ESRaw: Index into logs-system-*
    loop Every 5 Minutes
        Fetcher->>ESRaw: Query new documents (timestamp > last_run)
        ESRaw-->>Fetcher: Return raw JSON logs
        Fetcher->>Normalizer: Pass batch to normalizer
        Normalizer->>Normalizer: Map to internal dataclasses
        Normalizer->>Normalizer: Engineer 50-D Entity Vector
        Normalizer->>ML: Pass Feature Vectors
        ML->>ML: Isolation Forest Inference (Anomaly Score)
        ML->>ML: Autoencoder Inference (Recon Error)
        ML->>ML: Apply Rule Engine Modifiers
        ML->>ML: Calculate Final Threat Score & SHAP Values
        ML->>DB: Bulk Index fully enriched Alerts
    end
```

---

## 2. Alert to Incident Correlation Flow
Alerts are often components of a larger attack chain. This flow demonstrates how isolated alerts are clustered temporally and topologically into macro-Incidents.

```mermaid
sequenceDiagram
    autonumber
    participant AlertQueue as Threat Engine Output
    participant Correlator as Alert Correlator
    participant DB as Elasticsearch (soc-incidents)
    participant Pattern as Pattern Detector
    participant UI as React Dashboard

    AlertQueue->>Correlator: Trigger post-scoring hook
    Correlator->>DB: Query open incidents for Entity_Key (Host+User)
    alt Open Incident Exists within 4-hour window
        DB-->>Correlator: Return Incident ID
        Correlator->>DB: Append Alert ID & update max_threat_score
    else No Open Incident
        Correlator->>DB: Create new Incident record
    end
    Correlator->>Pattern: Pass updated Incident Alerts list
    Pattern->>Pattern: Graph analysis (e.g., Initial Access -> Lateral Mvmt)
    Pattern->>DB: Update Incident with MITRE Tactics
    DB-->>UI: WebSocket push: New / Updated Incident
```

---

## 3. Analyst Feedback to Retraining Flow
A critical component of reducing false positives is the continuous active learning loop.

```mermaid
sequenceDiagram
    autonumber
    participant Analyst as L1/L2 Analyst
    participant UI as React UI
    participant API as FastAPI Backend
    participant LabelDB as ES (soc-feedback)
    participant Trainer as Retraining Job (Weekly)
    participant ModelStore as MLflow / Local Disk

    Analyst->>UI: Clicks "Mark as False Positive" on Alert
    UI->>API: POST /api/feedback { alert_id, label="FP" }
    API->>LabelDB: Store analyst label
    LabelDB-->>API: ACK
    API-->>UI: Success 200 OK
    
    loop Every Sunday 2:00 AM
        Trainer->>LabelDB: Query recent labels
        Trainer->>ESRaw: Fetch historical feature vectors for labeled alerts
        Trainer->>Trainer: Append FP vectors to "normal" baseline data
        Trainer->>Trainer: Retrain Isolation Forest & Autoencoder
        Trainer->>ModelStore: Save new .pkl / .pt models
        Trainer->>API: Signal hot-reload to ModelManager
    end
```

---

## 4. SLM Investigation Flow with RAG
When an analyst requires plain-English context regarding a complex alert, the local Small Language Model uses Retrieval-Augmented Generation (RAG) to ensure accuracy and prevent hallucination.

```mermaid
sequenceDiagram
    autonumber
    participant Analyst as Analyst
    participant UI as React Chatbox
    participant API as SLM Router
    participant RAG as ChromaDB Pipeline
    participant SLM as Phi-3-mini Engine
    
    Analyst->>UI: "Is this mimikatz alert related to previous attacks?"
    UI->>API: POST /api/slm/chat { message, alert_id }
    API->>RAG: embed_text(message)
    RAG->>RAG: Query Vector DB (limit=3)
    RAG-->>API: Return top 3 similar historical alerts
    API->>API: Construct unified Prompt (Context + History + Query)
    API->>SLM: model.generate(prompt)
    SLM-->>API: Stream tokens (Yield)
    API-->>UI: Server-Sent Events (SSE) stream
    UI-->>Analyst: Renders Markdown response in real-time
```
