#!/bin/bash
set -euo pipefail

echo "🚀 Deploying ISRO SOC Platform to production..."

# Pull the latest imagery explicitly tagged for production
docker compose -f docker-compose.production.yml pull

# Bring up the stack in detached mode
docker compose -f docker-compose.production.yml up -d

echo "⏳ Waiting for health checks..."
# Give the backend API and Elasticsearch shards time to stabilize
sleep 30

# Verify the HTTPS gateway is successfully routing to the Python backend
curl -k -f https://localhost/api/health || { echo "❌ Health check failed"; exit 1; }

echo "🧪 Executing Post-Deployment Smoke Tests..."
# Run the internal regression and sanity suite against the live cluster
python backend/scripts/smoke_test.py --url https://localhost --skip-ssl-verify

echo "✅ Deployment complete! Platform is LIVE."
