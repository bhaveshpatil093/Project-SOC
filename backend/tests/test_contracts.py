import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.routes.alerts import AlertResponse
from app.api.routes.incidents import IncidentResponse
from app.api.routes.slm import ChatResponse

CONTRACT_ALERT_FIELDS = {
    "id", "entity_key", "threat_score", "threat_level",
    "top_features", "triggered_rules", "mitre_tactics",
    "human_explanation", "timestamp", "status"
}

CONTRACT_INCIDENT_FIELDS = {
    "incident_id", "entity_key", "host_id", "user_name",
    "started_at", "last_seen", "duration_seconds", "alert_count",
    "log_types_involved", "max_threat_score", "incident_threat_score",
    "threat_level", "mitre_tactics", "mitre_techniques",
    "attack_stage", "is_multi_stage", "status", "created_at"
}

CONTRACT_CHAT_FIELDS = {"conversation_id", "message", "sources", "tools_used", "response_time_ms"}

@pytest.mark.asyncio(loop_scope="session")
async def test_openapi_schema_generates_without_errors():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema

@pytest.mark.asyncio(loop_scope="session")
async def test_all_routes_have_response_models():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        resp = await client.get("/openapi.json")
        schema = resp.json()
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                responses = details.get("responses", {})
                if "200" in responses:
                    assert "content" in responses["200"] or "schema" in responses["200"]

@pytest.mark.asyncio(loop_scope="session")
async def test_alert_response_model_matches_frontend_expectations():
    fields = set(AlertResponse.model_fields.keys())
    missing = CONTRACT_ALERT_FIELDS - fields
    assert not missing, f"Missing contract fields in AlertResponse: {missing}"

@pytest.mark.asyncio(loop_scope="session")
async def test_incident_response_model_matches_frontend():
    fields = set(IncidentResponse.model_fields.keys())
    missing = CONTRACT_INCIDENT_FIELDS - fields
    assert not missing, f"Incident model missing fields: {missing}"

@pytest.mark.asyncio(loop_scope="session")
async def test_chat_response_model_matches_frontend():
    fields = set(ChatResponse.model_fields.keys())
    missing = CONTRACT_CHAT_FIELDS - fields
    assert not missing, f"Chat response missing fields: {missing}"

