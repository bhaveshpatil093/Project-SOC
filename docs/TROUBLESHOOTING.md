# Common Issues and Solutions

This troubleshooting guide covers the most frequent errors encountered when setting up or running the ISRO SOC Platform locally or in production.

---

## 1. "Elasticsearch connection refused"

**Symptoms:**
- Backend fails to start, throwing `ConnectionError` on `127.0.0.1:9200`.
- Terminal shows: `elasticsearch.exceptions.ConnectionError: ConnectionError(<urllib3.connection.HTTPConnection object at ...>)`

**Diagnosis & Fix:**
1. Check if the Docker container is running:
   ```bash
   docker ps | grep elasticsearch
   ```
2. If it's not running, start it:
   ```bash
   docker compose up -d elasticsearch
   ```
3. Check container logs for boot failures (often caused by low `vm.max_map_count` on Linux hosts):
   ```bash
   docker logs elasticsearch
   ```
   *Fix:* Run `sudo sysctl -w vm.max_map_count=262144` on the host machine.
4. Verify your `.env.development` has the correct `ES_PASSWORD`.

---

## 2. "SLM model fails to load — out of memory"

**Symptoms:**
- The FastAPI server hangs during startup while loading `app.slm.model_loader`.
- Terminal prints `torch.cuda.OutOfMemoryError` or the OS sends a `SIGKILL` (OOM Killer).

**Diagnosis & Fix:**
1. **Check Available RAM**: Phi-3-mini requires at least 8GB of free memory to load natively in float16.
2. **Enable 4-bit Quantization**: Edit your `.env` file to forcefully load the model in a smaller footprint:
   ```env
   SLM_LOAD_IN_4BIT=true
   ```
3. **Use Fallback Model**: If you are on an extremely constrained laptop, switch the model entirely to a tiny variant for dev purposes:
   ```env
   SLM_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0
   ```

---

## 3. "Frontend shows blank dashboard"

**Symptoms:**
- Navigating to `http://localhost:5173` yields a white screen.
- No network errors are obvious in the terminal.

**Diagnosis & Fix:**
1. **Check Backend Health**: Ensure `make dev-backend` is running and accessible at `http://localhost:8000/health`.
2. **Check Browser Console**: Press F12. If you see `CORS Error`, ensure your frontend URL is listed in the `BACKEND_CORS_ORIGINS` array in `backend/.env.development`.
3. **Vite Cache**: Stop the frontend terminal, delete `.vite` cache, and restart:
   ```bash
   rm -rf frontend/node_modules/.vite
   make dev-frontend
   ```

---

## 4. "Tests fail with 'index already exists'"

**Symptoms:**
- Running `make test` throws `elasticsearch.BadRequestError: resource_already_exists_exception`.

**Diagnosis & Fix:**
This occurs when a previous test run was interrupted (e.g., via Ctrl+C) before the teardown fixtures could delete the temporary `test-soc-*` indices.
1. Run the cleanup script forcefully:
   ```bash
   make clean
   ```
2. Alternatively, manually delete them via curl:
   ```bash
   curl -X DELETE "http://elastic:$ES_PASSWORD@localhost:9200/test-soc-*"
   ```

---

## 5. "MLflow UI shows no experiments"

**Symptoms:**
- You ran `make train`, the terminal showed success, but opening `http://localhost:5000` shows a blank workspace.

**Diagnosis & Fix:**
1. Check that the `MLFLOW_TRACKING_URI` in your backend `.env` perfectly matches the path MLflow is serving from.
2. If using local SQLite (default dev setup), ensure the file path is absolute:
   ```env
   MLFLOW_TRACKING_URI=sqlite:////absolute/path/to/Project-SOC/backend/data/mlflow.db
   ```
3. Restart the MLflow UI server to force it to re-read the `.db` file.

---

## 6. "WebSocket connection failing (Code 1006)"

**Symptoms:**
- The React UI displays a red disconnected icon. 
- Browser console prints: `WebSocket connection to 'ws://localhost:8000/api/ws/alerts' failed`.

**Diagnosis & Fix:**
1. Check your Auth token. WebSockets require the JWT token passed as a query parameter (`?token=xxx`). If the token expired, you must refresh the page.
2. Check Nginx configuration (if in production). Ensure proxy headers are set correctly for Upgrade requests:
   ```nginx
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```

---

## 7. "Missing NLTK or HuggingFace tokenizers during RAG"

**Symptoms:**
- Chatting with the SLM assistant throws `Resource punkt not found` or `OSError: Can't load tokenizer`.

**Diagnosis & Fix:**
The host machine is missing cached NLP dependency files.
1. Download NLTK data manually:
   ```bash
   python -c "import nltk; nltk.download('punkt')"
   ```
2. If offline, copy the `nltk_data` folder directly into `~/nltk_data/`.

---

## 8. "Ingestion Pipeline is not pulling new logs"

**Symptoms:**
- `GET /api/ingestion/status` shows `is_running: true` but `events_processed: 0`.

**Diagnosis & Fix:**
1. Check Logstash. The pipeline relies on Logstash forwarding actual endpoint telemetry into the raw indices (`logs-system-*`). If endpoints are disconnected, there is no data to fetch.
2. Check the `last_run` watermark. If you manually backdated your clock, the fetcher might be searching for logs in the future. Reset the cursor using:
   ```bash
   curl -X POST http://localhost:8000/api/ingestion/run?force_full=true
   ```

---

## 9. "ChromaDB throws sqlite3 syntax error"

**Symptoms:**
- Starting the API throws `sqlite3.OperationalError` originating from `chromadb`.

**Diagnosis & Fix:**
ChromaDB requires a modern version of SQLite. Older Linux distributions (or outdated Python compiles) ship with ancient SQLite binaries.
1. Ensure your Python was compiled with SQLite > 3.35.
2. If using Docker, ensure the base image is `python:3.11-slim-bookworm` or newer, avoiding older Ubuntu LTS bases.

---

## 10. "Ruff formatter complaints in pre-commit"

**Symptoms:**
- `git commit` aborts with red text citing formatting errors.

**Diagnosis & Fix:**
1. The pre-commit hook runs `ruff check` and `ruff format`. You can fix 99% of these issues automatically:
   ```bash
   make format
   ```
2. If it's a typing error (`mypy`), you must manually add the correct type annotations to your Python function signatures.

---

## 11. "No module named 'app.something'"

**Symptoms:**
- Running a script directly via `python backend/scripts/generate_full_api_docs.py` throws `ModuleNotFoundError`.

**Diagnosis & Fix:**
The python interpreter isn't aware of the `backend/` root directory.
1. Always prefix scripts with `PYTHONPATH`:
   ```bash
   cd backend
   PYTHONPATH=. python scripts/generate_full_api_docs.py
   ```

---

## 12. "Missing 'mps' device error on Mac"

**Symptoms:**
- Running on Apple Silicon, but PyTorch throws `RuntimeError: MPS backend out of memory` or `Attempting to use MPS but unavailable`.

**Diagnosis & Fix:**
1. Ensure you installed the PyTorch nightly/specific build that supports Metal Performance Shaders.
2. To fallback to CPU, edit your environment file:
   ```env
   PYTORCH_ENABLE_MPS_FALLBACK=1
   # OR
   FORCE_CPU=true
   ```

---

## 13. "Playwright tests failing — browser not found"

**Symptoms:**
- `make test-frontend` fails complaining about missing Chromium.

**Diagnosis & Fix:**
Playwright needs its native browser binaries installed, which NPM does not do automatically.
1. Install the binaries:
   ```bash
   cd frontend
   npx playwright install --with-deps
   ```

---

## 14. "Port 8000 already in use"

**Symptoms:**
- `make dev-backend` fails with `[Errno 98] Address already in use`.

**Diagnosis & Fix:**
Another process (or a crashed uvicorn instance) is holding the port.
1. Find the PID holding port 8000:
   ```bash
   lsof -i :8000
   ```
2. Kill it:
   ```bash
   kill -9 <PID>
   ```
