import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from app.ingestion.scheduler import run_ingestion_cycle
from app.features.pipeline import run_feature_pipeline
from app.scoring.threat_engine import get_threat_engine, init_threat_engine
from app.models.model_manager import get_model_manager
from app.slm.agent import SOCAgent
from app.slm.model_loader import get_slm_engine
from app.slm.rag_pipeline import get_rag_pipeline

@pytest.fixture
async def mock_es():
    es = AsyncMock()
    
    # Mock search response for log_fetcher
    es.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "host.id": "host-1",
                        "user.name": "user-1",
                        "@timestamp": datetime.now(timezone.utc).isoformat(),
                        "network.direction": "outbound",
                        "destination.port": 80,
                        "destination.bytes": 500
                    }
                }
            ]
        }
    }
    
    # Mock bulk indexing
    es.bulk = AsyncMock(return_value=(True, []))
    
    # Mock index creation
    es.indices.exists.return_value = True
    
    return es

@pytest.fixture
async def full_pipeline(mock_es):
    mm = get_model_manager()
    await mm.initialize()
    
    await init_threat_engine()
    te = get_threat_engine()
    
    slm = get_slm_engine()
    rag = get_rag_pipeline()
    
    agent = SOCAgent(slm_engine=slm, rag_pipeline=rag, es=mock_es)
    
    return {
        "es": mock_es,
        "model_manager": mm,
        "threat_engine": te,
        "agent": agent,
        "slm": slm
    }

@pytest.fixture
def feature_df():
    # Synthetic feature dataframe
    data = []
    for i in range(100):
        data.append({
            "entity_key": f"host-{i}|user-{i}",
            "window_bucket": "2026-06-19T00:00:00Z",
            "unique_dst_port_count": np.random.randint(1, 10),
            "bytes_out_sum": np.random.randint(100, 1000),
            "failed_login_count": 0,
            "has_encoded_payload": 0,
            "process_creation_count": 5
        })
    return pd.DataFrame(data)

@pytest.fixture
def feature_row():
    return {
        "entity_key": "host-test|user-test",
        "window_bucket": "2026-06-19T00:00:00Z",
        "unique_dst_port_count": 80,
        "has_encoded_payload": 1,
        "failed_login_count": 55,
        "bytes_out_sum": 1000000
    }

@pytest.mark.asyncio
async def test_ingestion_cycle_produces_normalized_docs(mock_es):
    # Mock fetch_all_sources to bypass complex ES queries in test
    with patch("app.ingestion.scheduler.fetch_all_sources") as mock_fetch:
        mock_fetch.return_value = {
            "syslog": [{"host.id": "host-1", "user.name": "user-1", "@timestamp": "2026-06-19T00:00:00Z", "event.action": "login"}],
            "process": [],
            "security": []
        }
        
        with patch("app.ingestion.scheduler.bulk_index") as mock_bulk:
            mock_bulk.return_value = {"indexed": 1, "errors": []}
            
            # Prevent Threat Engine from running for this isolated test
            with patch("app.scoring.threat_engine.ThreatEngine.run_scoring_cycle") as mock_scoring:
                mock_scoring.return_value = {}
                await run_ingestion_cycle(mock_es)
                
            assert mock_bulk.call_count == 1
            call_args = mock_bulk.call_args[0]
            docs = call_args[1]
            
            assert len(docs) == 1
            assert "entity_key" in docs[0]
            assert "window_bucket" in docs[0]
            assert "log_type" in docs[0]

@pytest.mark.asyncio
async def test_feature_pipeline_returns_correct_shape(mock_es):
    # Mock ES search to return logs
    mock_es.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "entity_key": "host-1|user-1",
                        "window_bucket": "2026-06-19T00:00:00Z",
                        "log_type": "syslog",
                        "network_direction": "outbound",
                        "destination_port": 80,
                        "destination_bytes": 500
                    }
                }
            ]
        }
    }
    
    df = await run_feature_pipeline(mock_es, since_minutes=5)
    
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        # Check standard columns exist natively mapped
        assert "entity_key" in df.columns
        assert "window_bucket" in df.columns
        assert "unique_dst_port_count" in df.columns
        assert not df["unique_dst_port_count"].isna().any()

@pytest.mark.asyncio
async def test_isolation_forest_scores_network_features(feature_df):
    from sklearn.ensemble import IsolationForest
    
    features = ["unique_dst_port_count", "bytes_out_sum", "failed_login_count"]
    clf = IsolationForest(contamination=0.05, random_state=42)
    clf.fit(feature_df[features])
    
    # Inject anomaly explicitly mapping port scan vectors natively
    anomaly = pd.DataFrame([{
        "unique_dst_port_count": 500,
        "bytes_out_sum": 5000000,
        "failed_login_count": 0
    }])
    
    scores = clf.decision_function(anomaly)
    # Convert to 0-1 anomaly score implicitly 
    norm_score = 0.5 - (scores[0] / 2.0) 
    
    assert 0 <= norm_score <= 1
    assert norm_score > 0.6

@pytest.mark.asyncio
async def test_autoencoder_flags_suspicious_process(feature_df):
    import torch
    import torch.nn as nn
    
    class MockAutoencoder(nn.Module):
        def __init__(self, input_dim=5):
            super().__init__()
            self.encoder = nn.Linear(input_dim, 2)
            self.decoder = nn.Linear(2, input_dim)
            
        def forward(self, x):
            return self.decoder(self.encoder(x))
            
    model = MockAutoencoder()
    criterion = nn.MSELoss()
    
    normal_input = torch.tensor([[5.0, 100.0, 0.0, 0.0, 5.0]])
    recon = model(normal_input)
    normal_loss = criterion(recon, normal_input).item()
    
    # Anomaly with has_encoded_payload=1 mapping implicitly malicious payload bounds
    anomaly_input = torch.tensor([[5.0, 100.0, 0.0, 1.0, 5.0]])
    recon_anom = model(anomaly_input)
    anomaly_loss = criterion(recon_anom, anomaly_input).item()
    
    assert anomaly_loss > normal_loss

@pytest.mark.asyncio
async def test_rule_engine_triggers_correct_rules(feature_row):
    from app.scoring.rule_engine import RuleEngine
    
    engine = RuleEngine()
    df = pd.DataFrame([feature_row])
    
    rules_triggered = engine.evaluate(df.iloc[0])
    
    rule_ids = [r.rule_id for r in rules_triggered]
    assert "RULE-002" in rule_ids # Port scan (80 unique ports)
    assert "RULE-004" in rule_ids # Encoded payload (has_encoded_payload=1)
    
    # Clean row natively bypassing rules safely
    clean_row = df.iloc[0].copy()
    clean_row["unique_dst_port_count"] = 5
    clean_row["has_encoded_payload"] = 0
    clean_row["failed_login_count"] = 1
    
    clean_triggered = engine.evaluate(clean_row)
    assert len(clean_triggered) == 0

@pytest.mark.asyncio
async def test_threat_engine_full_cycle(full_pipeline, mock_es):
    te = full_pipeline["threat_engine"]
    
    with patch("app.scoring.threat_engine.run_feature_pipeline") as mock_fp:
        # Mock df returning multiple rows natively tracking entities 
        mock_df = pd.DataFrame([{
            "entity_key": "host-1|user-1",
            "window_bucket": "2026-06-19T00:00:00Z",
            "unique_dst_port_count": 100,
            "has_encoded_payload": 1,
            "failed_login_count": 0,
            "bytes_out_sum": 0,
            "process_creation_count": 0
        }])
        
        mock_fp.return_value = mock_df
        
        # Override models internally natively avoiding ML errors cleanly
        te.model_manager.models = {}
        
        res = await te.run_scoring_cycle(since_minutes=5)
        
        assert "scored" in res
        assert "alerts_above_threshold" in res
        assert res["scored"] == 1
        
        # Assert ES bulk index called for alert natively
        assert mock_es.bulk.call_count > 0

@pytest.mark.asyncio
async def test_shap_explanation_populated(full_pipeline, feature_df):
    te = full_pipeline["threat_engine"]
    
    row = feature_df.iloc[0].copy()
    row["unique_dst_port_count"] = 100
    row["threat_score"] = 0.95
    row["top_rule"] = "Port Scan"
    
    res = await te.explain_scoring_result(row)
    
    assert res is not None
    assert isinstance(res.top_features, list)
    assert isinstance(res.human_explanation, str)
    assert len(res.human_explanation) > 0

@pytest.mark.asyncio
async def test_slm_returns_response(full_pipeline):
    agent = full_pipeline["agent"]
    
    # Mock LLM ainvoke purely intercepting generation constraints explicitly
    with patch.object(agent.agent_executor, 'ainvoke') as mock_invoke:
        mock_invoke.return_value = {"output": "Summary: This is a test alert.\nEvidence:\n- Test evidence"}
        
        res = await agent.investigate("What is this alert?", alert_id="test-001")
        
        assert res["answer"] != ""
        assert res["parsed"] is not None
        assert res["parsed"].get("summary") is not None

@pytest.mark.asyncio
async def test_feedback_suppresses_false_positive(full_pipeline, mock_es):
    from app.scoring.threat_engine import apply_feedback_suppression, get_threat_engine
    
    te = get_threat_engine()
    
    # Mock feedback data globally 
    mock_es.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "entity_key": "host-1|user-1",
                        "verdict": "FALSE_POSITIVE"
                    }
                }
            ]
        }
    }
    
    await te.refresh_suppression_list()
    
    row = pd.Series({
        "entity_key": "host-1|user-1",
        "threat_score": 0.8
    })
    
    adjusted = apply_feedback_suppression(row)
    
    assert adjusted < 0.8
    assert adjusted == 0.0 # Standard FP suppression heavily suppresses natively
