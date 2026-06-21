import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_submit_feedback_tp_stores_correctly(client: AsyncClient, mock_es):
    payload = {
        "alert_id": "test_alert_1",
        "entity_key": "10.0.0.1",
        "label": "true_positive",
        "notes": "Verified malicious scan"
    }
    response = await client.post("/api/feedback/", json=payload)
    assert response.status_code == 200
    
    # Verify index mapping to soc-alert-feedback
    mock_es.index.assert_called_once()
    kwargs = mock_es.index.call_args.kwargs
    assert kwargs["index"] == "soc-alert-feedback"
    assert kwargs["document"]["label"] == "true_positive"

async def test_submit_feedback_fp_stores_correctly(client: AsyncClient, mock_es):
    payload = {
        "alert_id": "test_alert_2",
        "entity_key": "10.0.0.2",
        "label": "false_positive",
        "notes": "Benign scanner"
    }
    response = await client.post("/api/feedback/", json=payload)
    assert response.status_code == 200
    mock_es.index.assert_called_once()
    assert mock_es.index.call_args.kwargs["document"]["label"] == "false_positive"

async def test_get_feedback_stats_returns_counts(client: AsyncClient, mock_es):
    mock_es.search.return_value = {
        "hits": {"total": {"value": 10}},
        "aggregations": {
            "labels": {"buckets": [{"key": "true_positive", "doc_count": 6}, {"key": "false_positive", "doc_count": 4}]}
        }
    }
    response = await client.get("/api/feedback/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 10
    assert "labels" in data["data"]

async def test_get_suppression_rules_returns_list(client: AsyncClient, mock_es):
    mock_es.search.return_value = {
        "hits": {"hits": [{"_source": {"rule_id": "R1"}}]}
    }
    response = await client.get("/api/feedback/suppression-rules")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

async def test_get_labeling_queue_returns_sorted_by_uncertainty(client: AsyncClient, mock_es):
    # Mock alerts with high uncertainty
    mock_es.search.return_value = {
        "hits": {"hits": [{"_id": "1", "_source": {"uncertainty": 0.9}}]}
    }
    response = await client.get("/api/feedback/queue")
    assert response.status_code == 200
    
    kwargs = mock_es.search.call_args.kwargs
    # Should sort by uncertainty or active learning score
    assert "uncertainty" in str(kwargs["body"]["sort"]) or "active_learning_score" in str(kwargs["body"]["sort"])

async def test_submit_feedback_requires_auth(mock_es):
    # Create an unauthenticated client by not overriding auth
    from app.main import app
    from httpx import ASGITransport
    
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as unauth_client:
        response = await unauth_client.post("/api/feedback/", json={
            "alert_id": "1", "entity_key": "E", "label": "true_positive"
        })
        assert response.status_code == 401
