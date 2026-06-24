# Developer Onboarding Guide

Welcome to the ISRO ISTRAC SOC AI Platform project! This guide will get you running on day one and introduce you to our contribution standards.

## Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Docker & Docker Compose**
- **16GB+ RAM** recommended (SLM inference is memory-intensive; 32GB preferred for local training)
- **Git**

---

## Day 1: Environment Setup

1. **Clone repository**:
   ```bash
   git clone <repo-url>
   cd Project-SOC
   ```
2. **Install dependencies**:
   ```bash
   make install-dev
   ```
   *This command installs both the backend Python dependencies (including dev tools like `ruff` and `pytest`) and frontend NPM packages.*
3. **Configure Environment Variables**:
   Copy the example environment file and fill in your secure passwords:
   ```bash
   cp backend/.env.example backend/.env.development
   # Edit backend/.env.development and fill in ES_PASSWORD
   ```
4. **Start Elasticsearch Database**:
   ```bash
   docker compose up -d elasticsearch kibana
   ```
5. **Wait for ES healthy**:
   Poll the database until you receive a successful HTTP response:
   ```bash
   curl -u elastic:$ES_PASSWORD http://localhost:9200
   ```
6. **Run migrations**: 
   The backend automatically applies Elasticsearch index mappings (`soc-*`) on startup using `backend/app/ingestion/es_mappings.py`. No manual intervention is needed.
7. **Start Backend**:
   In a new terminal window:
   ```bash
   make dev-backend
   ```
8. **Start Frontend**:
   In another terminal window:
   ```bash
   make dev-frontend
   ```
9. **Verify**: 
   Open `http://localhost:5173` in your browser. Log in with `admin` / `admin123`.
10. **Run Smoke Test**:
    Ensure the ML and ingestion pipelines are healthy:
    ```bash
    make smoke-test
    ```

---

## Day 1: Codebase Tour

The repository is structured as a monorepo containing both the React frontend and the FastAPI backend.

- `backend/app/api/`: All FastAPI routing controllers.
- `backend/app/models/`: Machine learning models (`IsolationForest`, `Autoencoder`, `ThreatEngine`).
- `backend/app/slm/`: The Small Language Model engine, RAG pipeline, and Conversation manager.
- `backend/app/ingestion/`: The async log fetcher, normalizer, and `APScheduler` loop.
- `backend/app/correlation/`: Alert grouping and MITRE pattern graph analytics.
- `backend/tests/`: Pytest suite (organized into `/unit`, `/integration`, `/chaos`, `/regression`).
- `frontend/src/pages/`: Top-level React container views (Dashboard, Investigation, etc.).
- `frontend/src/components/`: Reusable Tailwind UI elements (Badges, Graphs).
- `frontend/src/store/`: Redux/Context state management and API slice.

---

## Understanding the Data Flow

Logs are pulled from Logstash indices asynchronously every 5 minutes, converted into 50-dimensional vectors, and scored through an ensemble of Unsupervised Machine Learning models. High-scoring anomalies are aggregated into Incidents, which analysts can investigate using a localized AI language model powered by historical RAG context. 

*(For a deep dive, read the full [ARCHITECTURE.md](./ARCHITECTURE.md) and [DATA_FLOW_DIAGRAM.md](./DATA_FLOW_DIAGRAM.md))*

---

## Making Your First Change

1. **Pick a task**: Select a small bug or feature ticket.
2. **Branch out**: `git checkout -b feature/your-feature-name`
3. **Write the test**: We follow TDD. Write your `pytest` or `vitest` assertions first.
4. **Implement**: Write the code to make the test pass.
5. **Run the local suite**:
   ```bash
   make test
   make format
   make lint
   ```
6. **Submit PR**: Push your branch and open a Pull Request using the `PULL_REQUEST_TEMPLATE.md`. Ensure you link the related ticket.

---

## Code Style Guide

- **Python**: 
  - Linting handled automatically via `ruff`. 
  - Type hints are strictly required (`mypy` must pass).
  - Use Google-style docstrings for all classes and complex functions.
- **React**: 
  - Functional components only. No class-based components.
  - Rely on React Hooks for state.
  - Use Tailwind utility classes for styling. Avoid custom `.css` files unless absolutely necessary.
- **Commit messages**: Follow Conventional Commits:
  - `feat: added new MITRE tactic mapping`
  - `fix: resolved race condition in WebSocket buffer`
  - `docs: updated developer guide`
  - `test: added e2e playwright flows`
  - `refactor: abstracted model loader`

---

## Testing Philosophy

- **Coverage**: Every new feature needs unit coverage. If it exposes an endpoint, it needs an integration test.
- **Pre-commit**: Always run `make test` and `make lint` before committing.
- **Pull Requests**: You must run the master suite before opening a PR:
  ```bash
  make test-full
  ```
  *Note: The `test-full` script enforces a 95% overall pass rate.*

---

## Common Development Tasks

### Adding a new ML feature
1. Add the extraction logic to `backend/app/models/feature_merger.py`.
2. Update the `FEATURE_COLUMNS` schema list to bump the vector dimensionality (e.g., 50 -> 51).
3. Wipe your local models: `make clean`.
4. Trigger a fresh training cycle: `make train`.
5. Write an assertion in `tests/test_features/` verifying the new dimension computes correctly.

### Adding a new API endpoint
1. Create the new route in `backend/app/api/routes/`.
2. Define the exact Request and Response Pydantic models in `backend/app/api/schemas/`.
3. Wrap the route in `@require_role(["Admin"])` if sensitive.
4. Add the route to `audit_logger.py` if it modifies state.
5. Write integration tests in `tests/test_api/`.
6. Regenerate the docs: `python backend/scripts/generate_full_api_docs.py`.

### Adding a new MITRE rule
1. Open `backend/app/models/rule_engine.py`.
2. Append your regex or logic to the `RULES` dictionary.
3. Add a test payload to the golden dataset (`backend/tests/regression/golden_dataset.py`) simulating the exact attack behavior.
4. Run `make test-full` to ensure the rule triggers correctly without breaking backward compatibility.

### Modifying the SLM prompt
1. Open `backend/app/slm/agent.py` and modify the `SYSTEM_PROMPT` string template.
2. Run the specialized SLM quality testing suite:
   ```bash
   pytest tests/test_slm/test_slm_quality.py -v
   ```
3. Verify that the changes did not degrade response accuracy or cause hallucination formatting errors.

---

## Debugging Tips

- **Backend Logs**: If the API is failing silently, view full JSON output using:
  ```bash
  make docker-logs
  ```
- **Frontend State**: Utilize the React DevTools browser extension. Monitor the Redux state and Network tab for dropped payload errors.
- **ES Queries**: If logs aren't fetching, write raw Elasticsearch queries to test your indices using the Kibana Dev Tools (`http://localhost:5601`).
- **Slow SLM**: If generation is crawling, hit `GET /api/slm/model-info`. Ensure `device` says `cuda` or `mps`. If it says `cpu`, verify your PyTorch hardware bindings.

---

## Who to Ask

*Contact information placeholder.*
- **Lead ML Architect**: [ISRO Staff Name / Email]
- **Platform Engineering Lead**: [ISRO Staff Name / Email]
- **SOC Operations Lead**: [ISRO Staff Name / Email]
