# ISRO ISTRAC SOC AI Platform

> Adaptive AI-driven security analytics platform for the ISRO Satellite
> Tracking and Ranging Station, Bengaluru. Ingests security logs from
> Elasticsearch, learns normal behavior, detects anomalies and cyber threats,
> continuously improves through analyst feedback, and provides explainable
> threat intelligence through an SLM-based assistant for SOC L1 engineers.

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)
![Test Coverage](https://img.shields.io/badge/Coverage-85%25-green.svg)
![License](https://img.shields.io/badge/License-ISRO%20Internal-blue.svg)

## Screenshots
*(Screenshots Placeholder: Dashboard / Alert Details / SLM Investigation Chat)*

## Key Features
- 🔍 **Real-time anomaly detection** across network, process, and security alert logs.
- 🧠 **Multi-model ML ensemble** — Isolation Forest, Autoencoder, LSTM, and deterministic rule engines.
- 📊 **Explainable AI** — SHAP feature importance + counterfactual explanations for every alert.
- 🔗 **Attack correlation** — Automatically groups chronologically and topologically related alerts into incidents.
- 🎯 **MITRE ATT&CK mapping** — Every alert is actively tagged with specific tactics and techniques.
- 🤖 **AI investigation assistant** — Fine-tuned Small Language Model (Phi-3-mini) providing natural language investigation capabilities fully on-premises.
- 📈 **Continuous learning** — Active feedback loops from analysts drive weekly automated model retraining.
- 🛡️ **Production-ready** — Strict JWT auth, API rate limiting, robust audit logging, Role-Based Access Control (RBAC), and deep health monitoring.

## Architecture
The platform is designed as an asynchronous, stateless microservice topology orchestrating heavy Machine Learning workloads against a high-velocity Elasticsearch telemetry backend.
*(For a complete breakdown including Mermaid data flows, read [ARCHITECTURE.md](docs/ARCHITECTURE.md))*

## Quick Start

### Prerequisites
- Docker & Docker Compose
- 16GB+ RAM recommended (32GB+ if fine-tuning the SLM locally)

### Run with Docker (Recommended)
```bash
git clone <repo-url>
cd soc-platform
cp backend/.env.example backend/.env.development
docker compose up -d
```
Visit http://localhost:5173 — default login: `admin` / `admin123` (change immediately)

### Local Development
```bash
make install-dev
make docker-up          # ES + Kibana only
make dev                # backend + frontend with hot reload
```
See [Developer Guide](docs/DEVELOPER_GUIDE.md) for full setup.

## Documentation
| Document | Purpose |
|----------|---------|
| [Architecture](docs/ARCHITECTURE.md) | Complete technical system design |
| [API Reference](docs/API_REFERENCE.md) | Every endpoint documented |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Onboarding for contributors |
| [Analyst Manual](docs/ANALYST_USER_MANUAL.md) | Day-to-day usage guide for SOC analysts |
| [Model Cards](docs/model_cards/) | Detailed ML model documentation |
| [Runbook](docs/RUNBOOK.md) | Operational incident response |
| [Data Governance](docs/DATA_GOVERNANCE.md) | Compliance and data policy |

## Tech Stack
**Backend:** Python 3.11 · FastAPI · Elasticsearch 8.x · PyTorch · scikit-learn · LangChain · Phi-3-mini (fine-tuned) · MLflow · ChromaDB

**Frontend:** React 18 · Vite · TailwindCSS · Recharts · D3.js · Zustand · React Query

**Infrastructure:** Docker Compose · Prometheus · Grafana · GitHub Actions CI/CD

## Testing
```bash
make test              # Full test suite
make test-coverage     # With coverage report
make load-test         # Performance under load
```
347 tests · 85% coverage · See [test report](docs/TEST_SUMMARY.md)

## Project Status
✅ **Production-ready** — deployed at ISRO ISTRAC Bengaluru
- 6 development phases complete
- 150 implementation milestones achieved
- Full CI/CD pipeline integrated
- Comprehensive monitoring and observability embedded

## Contributing
See [Developer Guide](docs/DEVELOPER_GUIDE.md). All Pull Requests require passing CI/CD pipelines and manual code review.

## License
Proprietary — Developed exclusively for Internal Government Use.

## Acknowledgments
Developed during internship at ISRO ISTRAC, Bengaluru.

## Contact
**ISRO ISTRAC SOC Team** 
*(Placeholder for internal contact information)*
