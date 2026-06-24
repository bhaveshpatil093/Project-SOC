# ISRO ISTRAC SOC Platform — Documentation Master Index

Welcome to the central documentation hub for the SOC AI Platform. These documents have been meticulously curated to serve distinct roles within the organization, from Tier 1 operations to infrastructure disaster recovery. 

Please navigate to the section that best matches your role.

---

## 👨‍💻 For Developers & Contributors
Documentation regarding code architecture, API contracts, local development setup, and testing requirements.
- [Developer Onboarding Guide](DEVELOPER_GUIDE.md) - The mandatory Day-1 setup protocol for new engineers.
- [System Architecture](ARCHITECTURE.md) - Comprehensive technical breakdown of the 7 core macro-components (Ingestion, ML Ensemble, React SPA).
- [Data Flow Sequence Diagrams](DATA_FLOW_DIAGRAM.md) - Mermaid diagrams tracing exact logical pathways.
- [Complete API Reference](API_REFERENCE.md) - End-to-end catalog of every FastAPI route, including mocked cURL requests and JSON schemas.
- [API Contracts](API_CONTRACTS.md) - Data models shared between the Backend and Frontend.

## 🛡️ For SOC Analysts (L1 / L2)
Documentation focused on daily operational workflows and leveraging the AI capabilities.
- [Analyst User Manual](ANALYST_USER_MANUAL.md) - Non-technical, operational guide covering the daily 6-step triage workflow and interactive dashboards.
- [AI Assistant Guidelines](ANALYST_USER_MANUAL.md#using-the-ai-assistant-slm-chat) - How to extract maximum value from the Phi-3-mini SLM chat without falling for hallucinations.

## 🛠️ For Platform Operations (L3 / Infrastructure)
Documentation covering runtime failures, database tuning, and emergency recovery.
- [Disaster Recovery Runbook](RUNBOOK.md) - Execution paths for SEV1/SEV2 outages (e.g., Elasticsearch crashes, disk space critical, CUDA OOMs).
- [Troubleshooting Guide](TROUBLESHOOTING.md) - 14 highly specific diagnostic trees covering the most common Docker and Python environment failures.

## ⚖️ For Management & Compliance Officers
Documentation tracking AI ethics, open-source legal bounds, and data retention standards.
- [Model Governance Policy](MODEL_GOVERNANCE.md) - The overarching audit protocols dictating how ML models are trained, tested, deployed, and retired.
- [Model Cards Registry](model_cards/) - Specific statistical limitations, intended uses, and expected accuracy benchmarks for the 5 isolated AI subsystems.
- [Data Governance Policy](DATA_GOVERNANCE.md) - ISRO/CERT-In compliant regulations mapping exact data retention TTLs and PII masking protocols.
- [Third-Party Open Source Licenses](THIRD_PARTY_LICENSES.md) - Complete legal audit proving the absence of restrictive copyleft licenses in the proprietary codebase.
