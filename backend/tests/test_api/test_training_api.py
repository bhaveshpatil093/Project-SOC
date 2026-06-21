import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_initial_training_starts_background_job(client: AsyncClient):
    response = await client.post("/api/training/start")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "started" in data["status"].lower() or "queued" in data["status"].lower()

async def test_training_status_returns_progress(client: AsyncClient):
    response = await client.get("/api/training/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_training" in data
    assert "progress" in data

async def test_training_history_returns_mlflow_runs(client: AsyncClient):
    response = await client.get("/api/training/history")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

async def test_calibration_endpoint_returns_stats(client: AsyncClient):
    response = await client.get("/api/training/calibration")
    assert response.status_code == 200
    data = response.json()
    # It should return metrics like brier_score, expected_calibration_error
    assert "brier_score" in data["data"] or "method" in data["data"]

async def test_drift_endpoint_returns_report(client: AsyncClient):
    response = await client.get("/api/training/drift-report")
    assert response.status_code == 200
    data = response.json()
    assert "drift_detected" in data["data"]
