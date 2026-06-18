import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ingestion.normalizer import normalize_batch
from app.features.network_features import extract_all_network_features
from app.features.feature_merger import merge_features, get_feature_vector, FEATURE_COLUMNS

MOCK_NETWORK_DOC = {
    "_id": "net1",
    "@timestamp": "2024-01-01T12:00:00Z",
    "host": {"id": "host1"},
    "user": {"name": "user1"},
    "message": "SRC=192.168.1.100 DST=8.8.8.8 PROTO=TCP SPT=50000 DPT=443 IN=eth0"
}

MOCK_PROCESS_DOC = {
    "_id": "proc1",
    "@timestamp": "2024-01-01T12:00:00Z",
    "host": {"id": "host1"},
    "user": {"name": "user1"},
    "process": {
        "name": "powershell.exe",
        "command_line": "powershell.exe -enc ZWNobyBoZWxsbw==",
        "args_count": 2,
        "interactive": False
    }
}

MOCK_ALERT_DOC = {
    "_id": "alert1",
    "@timestamp": "2024-01-01T12:00:00Z",
    "host": {"id": "host1"},
    "user": {"name": "user1"},
    "kibana": {
        "alert": {
            "severity": "high",
            "risk_score": 75.0,
            "rule": {
                "threat": [
                    {
                        "tactic": {"name": "Execution"},
                        "technique": [{"id": "T1059"}]
                    }
                ]
            }
        }
    }
}

def test_normalize_batch():
    net_norm = normalize_batch([MOCK_NETWORK_DOC], "network")
    assert len(net_norm) == 1
    assert net_norm[0].dst_ip == "8.8.8.8"
    assert net_norm[0].protocol == "TCP"

    proc_norm = normalize_batch([MOCK_PROCESS_DOC], "process")
    assert len(proc_norm) == 1
    assert proc_norm[0].process_name == "powershell.exe"

    alert_norm = normalize_batch([MOCK_ALERT_DOC], "security_alert")
    assert len(alert_norm) == 1
    assert alert_norm[0].alert_severity == "high"

def test_extract_all_network_features():
    net_norm = normalize_batch([MOCK_NETWORK_DOC], "network")
    import dataclasses
    doc = dataclasses.asdict(net_norm[0])
    doc["entity_key"] = "host1|user1"
    doc["window_bucket"] = "2024-01-01T12:00:00Z"
    df = pd.DataFrame([doc])
    
    features = extract_all_network_features(df)
    assert not features.empty
    assert "conn_per_minute" in features.columns
    assert features.iloc[0]["unique_dst_ip_count"] == 1

def test_merge_features_fills_nan():
    net_norm = normalize_batch([MOCK_NETWORK_DOC], "network")
    import dataclasses
    doc = dataclasses.asdict(net_norm[0])
    doc["entity_key"] = "host1|user1"
    doc["window_bucket"] = "2024-01-01T12:00:00Z"
    net_df = pd.DataFrame([doc])
    net_features = extract_all_network_features(net_df)
    
    proc_features = pd.DataFrame()
    alert_features = pd.DataFrame()
    
    merged = merge_features(net_features, proc_features, alert_features)
    assert not merged.empty
    
    assert "process_spawn_count" in merged.columns
    assert merged.iloc[0]["process_spawn_count"] == 0.0

def test_get_feature_vector():
    row = pd.Series({col: 1.0 for col in FEATURE_COLUMNS})
    vec = get_feature_vector(row)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (50,)
    assert vec[0] == 1.0

@pytest.mark.asyncio
async def test_api_features_run():
    with patch("app.api.routes.features.run_feature_pipeline", new_callable=AsyncMock) as mock_pipeline, \
         patch("app.api.routes.features.store_feature_vectors", new_callable=AsyncMock) as mock_store, \
         patch("app.api.routes.features.get_es_client", new_callable=AsyncMock) as mock_es:
        
        mock_es.return_value = AsyncMock()
        mock_pipeline.return_value = pd.DataFrame([
            {"entity_key": "h1|u1", "window_bucket": "test", "conn_per_minute": 5.0}
        ])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/features/run")
            assert response.status_code == 200
            data = response.json()
            assert data["entities_processed"] == 1
            assert data["window"] == "test"
            assert "h1|u1" in data["top_entities"]
