# Changelog

All notable changes to the ISRO ISTRAC SOC Platform are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/), versioning
follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-06-24

### 🎉 Initial Production Release

The complete ISRO ISTRAC SOC AI Platform — built across 150 development milestones covering ingestion, ML detection, explainability, correlation, analyst feedback loops, and an SLM-powered investigation assistant.

### Added — Data Pipeline
- Elasticsearch integration with async client and connection pooling
- Multi-source log ingestion (syslog, process events, security alerts)
- Regex-based syslog field extraction (SRC/DST/PROTO/SPT/DPT/IN)
- Unified log normalization schema across all 3 sources
- 5-minute sliding window feature engineering (50-dimensional vectors)

### Added — Machine Learning
- Isolation Forest for network anomaly detection
- Autoencoder (PyTorch) for process behavior anomaly detection
- LSTM sequence model for event pattern anomaly detection
- 10-rule deterministic MITRE ATT&CK rule engine
- Weighted voting ensemble with confidence intervals
- Score calibration (Platt scaling / isotonic regression)
- Model drift detection (PSI-based)
- Active learning for optimal analyst labeling
- Entity baseline behavior learning with temporal awareness

### Added — Explainability
- SHAP-based feature importance for all alerts
- Counterfactual explanations ("what would make this benign")
- Human-readable natural language explanations
- Model consensus and disagreement detection

### Added — Correlation & Intelligence
- Alert correlation engine grouping related events into incidents
- 8-pattern attack sequence library (multi-step attack detection)
- Offline threat intelligence enrichment (IP/process/domain reputation)
- Entity risk scoring with time-decay
- Alert deduplication and fingerprinting

### Added — Feedback & Learning
- Analyst feedback collection (TP/FP/Benign labeling)
- False positive suppression engine
- Incremental and full model retraining workflows
- MLflow experiment tracking

### Added — SLM Investigation Assistant
- Fine-tuned Phi-3-mini model (QLoRA) on SOC-specific dataset
- RAG pipeline with ChromaDB vector store
- LangChain agent with 5 investigation tools
- Multi-turn conversation management
- Response caching (exact + semantic)
- Guided investigation playbooks (5 attack types)
- Automated incident report generation

### Added — Frontend Application
- React 18 + Vite + TailwindCSS dashboard
- Real-time WebSocket alert streaming
- Analyst Workbench with keyboard-driven triage
- Interactive correlation graph (D3.js)
- Dark/light theme support
- Full mobile responsiveness
- PDF/CSV export capabilities
- User preference persistence

### Added — Platform Operations
- JWT authentication with RBAC (admin/analyst/viewer)
- Rate limiting and input sanitization
- Comprehensive audit logging
- Automated backup/restore (ES snapshots)
- Index migration system
- Prometheus metrics + Grafana dashboards
- Platform self-monitoring and alerting
- SLA tracking per threat level
- Webhook integrations for external systems

### Added — Testing & Quality
- 347+ automated tests across unit/integration/E2E/chaos/security
- Golden dataset regression suite (50 scenarios)
- Load testing framework (Locust)
- Cross-browser and accessibility testing (Playwright + axe)
- Full CI/CD pipeline (GitHub Actions)

### Documentation
- Complete architecture documentation
- Full API reference (auto-generated + manual examples)
- Developer onboarding guide
- SOC analyst user manual
- ML model cards (governance & transparency)
- Operational runbook
- Data governance and compliance documentation

### Known Limitations
- SLM performance on CPU-only deployments: ~2-4s response time (GPU recommended for production scale)
- LSTM model requires minimum 7 days of historical data for reliable baselines
- Pattern detection library covers 8 known attack patterns — novel multi-stage attacks may require manual correlation

### Security
- All data processed on-premises — no external API calls for ML/SLM
- TLS 1.2+ enforced in production configuration
- Comprehensive OWASP Top 10 test coverage

---

## [0.9.0] - Phases 1-18 (Development)
[Internal development milestones — see git history for detailed progression through prompts 1-140]
