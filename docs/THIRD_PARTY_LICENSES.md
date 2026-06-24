# Third-Party Open Source Licenses

To ensure strict legal and governmental compliance for the ISRO ISTRAC SOC Platform, all third-party dependencies utilized across the backend Python and frontend Node.js ecosystems have been audited. 

The platform relies strictly on permissive open-source licenses (MIT, Apache 2.0, BSD). No GPL, AGPL, or restrictive copyleft licenses are bundled in the production application, allowing for secure internal proprietary usage.

## Backend Dependencies (Python)

| Library | Version | Purpose | License Type |
|---|---|---|---|
| **FastAPI** | Current | API Routing Framework | MIT |
| **Uvicorn** | Current | ASGI Web Server | BSD-3-Clause |
| **Elasticsearch[async]** | Current | Database Client | Apache 2.0 / Elastic License |
| **Pydantic / Settings** | Current | Data Validation | MIT |
| **Pandas** | Current | Data Manipulation | BSD-3-Clause |
| **NumPy** | Current | Array Operations | BSD-3-Clause |
| **Scikit-Learn** | Current | Isolation Forest / Trees | BSD-3-Clause |
| **PyOD** | Current | Outlier Detection | BSD-2-Clause |
| **PyTorch (torch)** | Current | Deep Learning / Autoencoder | BSD-3-Clause |
| **SHAP** | Current | Explainability | MIT |
| **LangChain** | Current | AI Orchestration | MIT |
| **Sentence-Transformers**| Current | Text Embeddings | Apache 2.0 |
| **Transformers (HF)** | Current | Phi-3 Inference | Apache 2.0 |
| **MLflow** | Current | Model Tracking | Apache 2.0 |
| **APScheduler** | Current | Background Jobs | MIT |
| **ChromaDB** | Current | Vector Database | Apache 2.0 |
| **SlowAPI** | 0.1.9 | Rate Limiting | MIT |
| **Structlog** | >=24.1.0 | JSON Logging | MIT/Apache 2.0 |
| **Passlib / Bcrypt** | >=1.7.4 | Password Hashing | BSD |
| **Python-Jose** | >=3.3.0 | JWT Authentication | MIT |
| **Pytest** | Current | Testing Framework | MIT |
| **Locust** | 2.24.1 | Load Testing | MIT |

## Frontend Dependencies (Node.js/React)

| Library | Version | Purpose | License Type |
|---|---|---|---|
| **React** | ^19.2.6 | UI Framework | MIT |
| **React DOM** | ^19.2.6 | Virtual DOM | MIT |
| **React Router DOM** | ^7.18.0 | Client-side Routing | MIT |
| **Vite** | ^8.0.12 | Build Tool / Bundler | MIT |
| **Zustand** | ^5.0.14 | State Management | MIT |
| **Tailwind CSS** | ^3.4.19 | Utility Styling | MIT |
| **Recharts** | ^3.8.1 | Charting / Visualizations | MIT |
| **D3** | ^7.9.0 | Advanced Graph Data Rendering | ISC |
| **Axios** | ^1.18.0 | HTTP Client | MIT |
| **Lucide React** | ^1.21.0 | SVG Icons | ISC |
| **jsPDF** | ^4.2.1 | PDF Report Generation | MIT |
| **TanStack React Query** | ^5.101.0 | Server State Management | MIT |
| **date-fns** | ^4.4.0 | Date formatting | MIT |
| **Playwright** | ^1.61.1 | E2E Testing | Apache 2.0 |
| **Vitest** | ^4.1.9 | Unit Testing | MIT |
| **MSW** | ^2.14.6 | Mock Service Worker | MIT |

## AI Models
| Model | Creator | Purpose | License Type |
|---|---|---|---|
| **Phi-3-mini-4k-instruct** | Microsoft | SLM / Analyst Assistant | MIT License |
| **all-MiniLM-L6-v2** | HuggingFace | Text Embeddings for RAG | Apache 2.0 |

> **Compliance Note**: All network calls to external telemetry, usage tracking, or crash analytics (such as HuggingFace Hub telemetry) have been explicitly disabled within the application configuration to ensure true air-gapped data residency compliance.
