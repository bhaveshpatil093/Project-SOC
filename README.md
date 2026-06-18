# SOC Security Analytics Platform

A security analytics platform with a Python (FastAPI) backend and a React frontend, using Elasticsearch for data storage and analysis.

## Structure

- `backend/`: FastAPI application, ML models, and data ingestion services
- `frontend/`: React-based user interface
- `docker-compose.yml`: Infrastructure services (Elasticsearch, Kibana)

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker and Docker Compose

## Quick Start

1. Start Infrastructure:
   ```bash
   docker-compose up -d
   ```

2. Setup Backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Start server
   uvicorn app.main:app --reload
   ```
