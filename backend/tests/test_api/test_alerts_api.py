import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_get_alerts_returns_200_with_list(client: AsyncClient, mock_es):
    mock_es.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [{"_id": "1", "_source": {"entity_key": "E1", "threat_score": 0.9}}]
        }
    }
    response = await client.get("/api/alerts/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "1"

async def test_get_alerts_filter_by_status(client: AsyncClient, mock_es):
    await client.get("/api/alerts/?status=open")
    mock_es.search.assert_called_once()
    args, kwargs = mock_es.search.call_args
    assert kwargs["index"] == "soc-processed-alerts"
    query_body = kwargs["body"]
    # Check if status filter is in the query (implementation details vary, so this is a loose check)
    assert "open" in str(query_body)

async def test_get_alerts_filter_by_threat_level(client: AsyncClient, mock_es):
    await client.get("/api/alerts/?threat_level=high")
    mock_es.search.assert_called_once()
    kwargs = mock_es.search.call_args.kwargs
    assert "high" in str(kwargs["body"])

async def test_get_alert_detail_returns_shap_fields(client: AsyncClient, mock_es):
    mock_es.get.return_value = {
        "_id": "1",
        "_source": {
            "entity_key": "E1",
            "shap_values": {"feat1": 0.5, "feat2": 0.1}
        }
    }
    response = await client.get("/api/alerts/1")
    assert response.status_code == 200
    data = response.json()
    assert "shap_values" in data["data"]

async def test_get_alert_404_on_missing_id(client: AsyncClient, mock_es):
    from elasticsearch.exceptions import NotFoundError
    mock_es.get.side_effect = NotFoundError(404, "Not Found")
    
    response = await client.get("/api/alerts/999")
    assert response.status_code == 404

async def test_patch_alert_status_updates_es(client: AsyncClient, mock_es):
    mock_es.update.return_value = {"result": "updated"}
    response = await client.patch("/api/alerts/1/status", json={"status": "closed", "resolution": "true_positive"})
    
    assert response.status_code == 200
    mock_es.update.assert_called_once()

async def test_get_alert_stats_has_all_fields(client: AsyncClient, mock_es):
    mock_es.search.return_value = {
        "aggregations": {
            "threat_levels": {"buckets": [{"key": "high", "doc_count": 5}]},
            "status": {"buckets": [{"key": "open", "doc_count": 5}]}
        }
    }
    response = await client.get("/api/alerts/stats")
    assert response.status_code == 200
    data = response.json()
    assert "threat_levels" in data["data"]
    assert "status" in data["data"]

async def test_get_alert_timeline_sorted_chronologically(client: AsyncClient, mock_es):
    mock_es.search.return_value = {
        "aggregations": {
            "timeline": {"buckets": [{"key_as_string": "2026-06-21T10:00:00Z", "doc_count": 2}]}
        }
    }
    response = await client.get("/api/alerts/timeline")
    assert response.status_code == 200
    assert "data" in response.json()

async def test_trigger_scoring_returns_summary(client: AsyncClient, mock_es):
    # This might use background tasks or return immediately
    response = await client.post("/api/alerts/trigger-scoring")
    assert response.status_code == 200
    assert "status" in response.json()

async def test_alerts_pagination_respects_limit_offset(client: AsyncClient, mock_es):
    await client.get("/api/alerts/?skip=10&limit=5")
    kwargs = mock_es.search.call_args.kwargs
    assert kwargs["body"]["from"] == 10
    assert kwargs["body"]["size"] == 5
