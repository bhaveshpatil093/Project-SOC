# Data Governance Policy — ISRO ISTRAC SOC Platform

## Data Classification
| Data Type | Classification | Retention | Access Control |
|-----------|----------------|-----------|-----------------|
| Raw security logs | Restricted | 90 days (ES) | SOC team only |
| Processed alerts | Restricted | 1 year | SOC team only |
| Analyst feedback | Internal | Indefinite | SOC team only |
| Audit logs | Restricted | 90 days minimum | Admin only |
| ML model artifacts | Internal | Latest 10 versions | Admin only |
| SLM conversation history | Restricted | 24 hours (configurable) | Same analyst only |

## Personally Identifiable Information (PII) Handling
- `user.name` fields contain ISRO employee usernames — treated as Restricted.
- No external PII is collected (no customer data, no public-facing systems).
- SLM conversations may reference usernames — included in 24h TTL deletion policy.
- Audit logs track analyst actions for accountability — retained 90 days minimum per IT Act 2000 and CERT-In guidelines.

## Data Residency
- All data stored on-premises at ISRO ISTRAC Bengaluru.
- No data transmitted to external cloud services.
- SLM runs fully on-premises (Phi-3-mini, locally hosted — no API calls to external LLM providers).
- No telemetry sent to Anthropic, OpenAI, or any third party.

## Access Control Matrix
| Role | Alerts | Incidents | Feedback | Training | Admin | Audit Log |
|------|--------|-----------|----------|----------|-------|-----------|
| Viewer | Read | Read | Read | None | None | None |
| Analyst | Read/Write | Read/Write | Read/Write | Read | None | None |
| Admin | Full | Full | Full | Full | Full | Read |

## Data Deletion Procedures
- Conversation history: automatic TTL expiry (24h default) via `ConversationManager`.
- Old score history: automatic cleanup (30 day retention) via `cleanup.py`.
- Audit logs: automatic cleanup (90 day retention, configurable for compliance).
- Manual deletion: via `/api/admin/*` endpoints, all logged to audit trail.

## Incident Data Handling
- Generated incident reports may contain sensitive attack details.
- Reports classified as Restricted — access logged.
- PDF exports should be handled per ISRO document classification policy.

## Third-Party Dependencies — Data Flow Review
- Elasticsearch: on-premises, no external calls.
- HuggingFace models: downloaded once at setup, run fully offline thereafter.
- No external API calls during normal operation (verify: MLflow, ChromaDB, all models are local-only).

## Compliance Checklist
- [x] All data stored within ISRO network perimeter
- [x] No credentials in source control (verified via secrets_manager audit)
- [x] Audit logging enabled for all admin actions
- [x] Encryption at rest configured for Elasticsearch (production)
- [x] Encryption in transit (TLS) configured for production deployment
- [x] Access control matrix reviewed and approved by ISRO security team
- [x] Data retention periods approved by ISRO compliance officer
