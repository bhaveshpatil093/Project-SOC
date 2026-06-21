# ISRO ISTRAC SOC Platform — Developer Commands
# Usage: make <target>

.PHONY: help install dev test lint format docker-up docker-down \
       train smoke-test docs clean reset

# Colors
CYAN  = \033[0;36m
GREEN = \033[0;32m
RESET = \033[0m

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'

# ─── Setup ────────────────────────────────────────────────────────────
install:  ## Install all dependencies (backend + frontend)
	cd backend && pip install -r requirements.txt
	cd frontend && npm ci
	@echo "$(GREEN)✅ Dependencies installed$(RESET)"

install-dev:  ## Install dev dependencies (adds ruff, mypy, pytest, locust)
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm ci
	pip install pre-commit && pre-commit install

# ─── Development ──────────────────────────────────────────────────────
dev-backend:  ## Start backend dev server with hot reload
	cd backend && SOC_ENVIRONMENT=development uvicorn app.main:app \
	  --host 0.0.0.0 --port 8000 --reload --log-level debug

dev-frontend:  ## Start frontend dev server
	cd frontend && npm run dev

dev:  ## Start both backend and frontend (requires tmux or two terminals)
	@echo "Starting backend on :8000 and frontend on :5173"
	@make -j2 dev-backend dev-frontend

# ─── Testing ──────────────────────────────────────────────────────────
test:  ## Run all tests
	cd backend && SOC_ENVIRONMENT=test pytest tests/ -v --tb=short

test-unit:  ## Run only unit tests (fast)
	cd backend && SOC_ENVIRONMENT=test pytest tests/test_models/ tests/test_features/ -v

test-api:  ## Run only API integration tests
	cd backend && SOC_ENVIRONMENT=test pytest tests/test_api/ -v --asyncio-mode=auto

test-e2e:  ## Run end-to-end journey test
	cd backend && SOC_ENVIRONMENT=test pytest tests/test_full_journey.py -v -s

test-security:  ## Run OWASP security tests
	cd backend && SOC_ENVIRONMENT=test pytest tests/security/ -v

test-frontend:  ## Run frontend tests
	cd frontend && npm test

test-coverage:  ## Run tests with coverage report
	cd backend && SOC_ENVIRONMENT=test pytest tests/ --cov=app \
	  --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report: backend/htmlcov/index.html$(RESET)"

load-test:  ## Run locust load test (headless, 5 users, 60s)
	cd backend && locust -f tests/load/locustfile.py \
	  --headless -u 5 -r 1 -t 60s --host http://localhost:8000

# ─── Code Quality ─────────────────────────────────────────────────────
lint:  ## Run ruff linter
	cd backend && ruff check app/
	cd frontend && npm run lint

format:  ## Auto-format code (ruff + prettier)
	cd backend && ruff format app/
	cd frontend && npx prettier --write src/

typecheck:  ## Run mypy type checker
	cd backend && mypy app/ --ignore-missing-imports

# ─── Docker ───────────────────────────────────────────────────────────
docker-up:  ## Start full stack with Docker Compose
	docker compose up -d
	@echo "$(GREEN)✅ Stack running: ES :9200 | Kibana :5601 | API :8000 | UI :3000$(RESET)"

docker-down:  ## Stop all services
	docker compose down

docker-logs:  ## Follow logs from all services
	docker compose logs -f

docker-rebuild:  ## Rebuild and restart all services
	docker compose down && docker compose build && docker compose up -d

# ─── ML Operations ────────────────────────────────────────────────────
train:  ## Trigger initial model training
	curl -X POST http://localhost:8000/api/training/initial \
	  -H "Authorization: Bearer $$(make get-token)" | python -m json.tool

retrain:  ## Trigger incremental retraining
	curl -X POST http://localhost:8000/api/training/retrain \
	  -H "Authorization: Bearer $$(make get-token)" | python -m json.tool

build-dataset:  ## Generate SLM fine-tuning dataset
	cd backend && python -m app.slm.training_data.dataset_builder

finetune:  ## Run SLM fine-tuning (WARNING: slow — GPU recommended)
	cd backend && python -m app.slm.finetune

benchmark:  ## Run performance benchmark
	cd backend && python scripts/benchmark.py

profile:  ## Run profiler on all pipeline stages
	cd backend && python scripts/profiler.py

# ─── Operations ───────────────────────────────────────────────────────
smoke-test:  ## Run smoke tests against running instance
	cd backend && python scripts/smoke_test.py \
	  --url http://localhost:8000 \
	  --username admin --password admin123

get-token:  ## Get admin JWT token (for curl commands)
	@curl -s -X POST http://localhost:8000/api/auth/login \
	  -H "Content-Type: application/json" \
	  -d '{"username":"admin","password":"admin123"}' | \
	  python -c "import sys,json; print(json.load(sys.stdin)['access_token'])"

reindex-rag:  ## Re-index all alerts into RAG vector store
	curl -X POST http://localhost:8000/api/slm/rag/reindex \
	  -H "Authorization: Bearer $$(make get-token)"

# ─── Documentation ────────────────────────────────────────────────────
docs:  ## Generate API documentation
	cd backend && python scripts/generate_api_docs.py
	@echo "$(GREEN)Docs written to docs/API_REFERENCE.md$(RESET)"

# ─── Cleanup ──────────────────────────────────────────────────────────
clean:  ## Remove generated files (models, cache, test artifacts)
	find backend -type d -name __pycache__ -exec rm -rf {} +
	find backend -name "*.pyc" -delete
	rm -rf backend/htmlcov backend/.coverage backend/.pytest_cache
	rm -rf frontend/dist frontend/node_modules/.cache

reset:  ## DANGER: Reset all data (ES indices, models, ChromaDB)
	@echo "⚠️  This will delete ALL data. Press Ctrl+C to cancel, Enter to continue."
	@read _
	curl -X DELETE "http://elastic:$${ES_PASSWORD}@localhost:9200/soc-*"
	rm -rf backend/models/saved/* data/chroma_db/* data/mlflow.db
	@echo "$(GREEN)Reset complete$(RESET)"
