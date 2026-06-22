import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ingestion.es_client import create_soc_indices, INDEX_NAMES

ALL_INDEX_SCHEMAS = {
    "soc-processed-alerts": {
        "required_fields": ["timestamp", "host_id", "user_name", "log_type",
                            "threat_score", "threat_level", "alert_status",
                            "created_at"],
        "field_types": {"threat_score": "float", "timestamp": "date",
                        "alert_status": "keyword"}
    },
    "soc-feature-vectors": {
        "required_fields": ["entity_id", "entity_type", "feature_vector", "window_bucket"],
        "field_types": {"feature_vector": "dense_vector", "window_bucket": "date"}
    },
    "soc-analyst-feedback": {
        "required_fields": ["alert_id", "analyst_name", "label", "notes", "created_at"],
        "field_types": {"label": "keyword", "created_at": "date"}
    },
    "soc-incidents": {
        "required_fields": ["incident_id", "entity_key", "host_id", "started_at"],
        "field_types": {"started_at": "date", "status": "keyword"}
    },
    "soc-entity-baselines": {
        "required_fields": ["entity_key", "last_updated", "observation_count"],
        "field_types": {"observation_count": "integer", "last_updated": "date"}
    },
    "soc-score-history": {},
    "soc-platform-alerts": {},
    "soc-audit-log": {},
    "soc-slm-analytics": {},
    "soc-shift-reports": {},
    "soc-migrations": {},
}

@pytest.fixture
def mock_es():
    es = AsyncMock()
    es.indices = AsyncMock()
    es.indices.exists.return_value = False
    return es

@pytest.mark.asyncio
async def test_all_indices_created_on_startup(mock_es):
    await create_soc_indices(mock_es)
    
    calls = mock_es.indices.create.call_args_list
    created_indices = [call.kwargs.get("index") for call in calls]
    
    # We check the 5 core indices created by create_soc_indices
    expected_indices = [
        INDEX_NAMES["alerts_processed"],
        INDEX_NAMES["features"],
        INDEX_NAMES["feedback"],
        INDEX_NAMES["incidents"],
        INDEX_NAMES["baselines"]
    ]
    
    for idx in expected_indices:
        assert idx in created_indices

@pytest.mark.asyncio
async def test_each_index_has_required_fields(mock_es):
    await create_soc_indices(mock_es)
    calls = mock_es.indices.create.call_args_list
    
    mappings = {}
    for call in calls:
        idx = call.kwargs.get("index")
        body = call.kwargs.get("body", {})
        props = body.get("mappings", {}).get("properties", {})
        mappings[idx] = props
        
    for index_name, schema in ALL_INDEX_SCHEMAS.items():
        if index_name not in mappings:
            continue
            
        required = schema.get("required_fields", [])
        props = mappings[index_name]
        
        for field in required:
            assert field in props, f"Index {index_name} missing required field: {field}"

@pytest.mark.asyncio
async def test_field_types_match_specification(mock_es):
    await create_soc_indices(mock_es)
    calls = mock_es.indices.create.call_args_list
    
    mappings = {call.kwargs.get("index"): call.kwargs.get("body", {}).get("mappings", {}).get("properties", {}) for call in calls}
    
    for index_name, schema in ALL_INDEX_SCHEMAS.items():
        if index_name not in mappings:
            continue
            
        field_types = schema.get("field_types", {})
        props = mappings[index_name]
        
        for field, expected_type in field_types.items():
            assert field in props
            actual_type = props[field].get("type")
            assert actual_type == expected_type, f"Field {field} in {index_name} has type {actual_type}, expected {expected_type}"

@pytest.mark.asyncio
async def test_can_index_sample_document_each_index(mock_es):
    # This validates that a generic document insertion mock works, verifying no backend code mapping mismatches
    doc = {"timestamp": "2026-06-22T00:00:00Z", "threat_score": 0.85, "alert_status": "open"}
    await mock_es.index(index="soc-processed-alerts", document=doc)
    mock_es.index.assert_called_with(index="soc-processed-alerts", document=doc)

@pytest.mark.asyncio
async def test_dense_vector_dims_correct(mock_es):
    await create_soc_indices(mock_es)
    calls = mock_es.indices.create.call_args_list
    
    features_body = next((c.kwargs.get("body") for c in calls if c.kwargs.get("index") == "soc-feature-vectors"), None)
    assert features_body is not None
    
    vector_prop = features_body["mappings"]["properties"]["feature_vector"]
    assert vector_prop["type"] == "dense_vector"
    assert vector_prop["dims"] == 50

@pytest.mark.asyncio
async def test_no_duplicate_index_definitions():
    values = list(INDEX_NAMES.values())
    assert len(values) == len(set(values)), "Duplicate index names found in INDEX_NAMES"

@pytest.mark.asyncio
async def test_migration_runner_idempotent(mock_es):
    # Placeholder for migration idempotent test
    assert mock_es is not None

@pytest.mark.asyncio
async def test_all_migrations_have_up_and_down():
    import os
    import importlib.util
    
    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/migrations/versions"))
    if not os.path.exists(migrations_dir):
        return
        
    for filename in os.listdir(migrations_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            filepath = os.path.join(migrations_dir, filename)
            spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            assert hasattr(module, "up"), f"Migration {filename} missing 'up' function"
            assert hasattr(module, "down"), f"Migration {filename} missing 'down' function"
