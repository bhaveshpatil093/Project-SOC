import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.baseline_learner import BaselineLearner, EntityBaseline
from datetime import datetime
import math

pytestmark = pytest.mark.asyncio

@pytest.fixture
def learner():
    return BaselineLearner(min_observations=3, decay_factor=0.9)

@pytest.fixture
def mock_es():
    return AsyncMock()

async def test_update_baseline_exponential_moving_average(learner, mock_es):
    mock_es.get.return_value = {
        "_source": {
            "entity_key": "user1",
            "last_updated": datetime.utcnow().isoformat(),
            "observation_count": 5,
            "avg_conn_per_minute": 10.0,
            "std_conn_per_minute": 2.0,
            "avg_unique_dst_ports": 0.0,
            "std_unique_dst_ports": 0.0,
            "typical_protocols": [],
            "typical_dst_ports": [],
            "avg_process_spawn_count": 0.0,
            "std_process_spawn_count": 0.0,
            "known_process_names": [],
            "avg_args_count": 0.0,
            "avg_alert_count": 0.0,
            "std_alert_count": 0.0,
            "avg_risk_score": 0.0
        }
    }
    
    # 0.9 * 10.0 + 0.1 * 20.0 = 9.0 + 2.0 = 11.0
    await learner.update_baseline(mock_es, "user1", {"conn_count_1m": 20.0})
    
    # Verify index was called
    mock_es.index.assert_called_once()
    args, kwargs = mock_es.index.call_args
    doc = kwargs["document"]
    
    assert doc["observation_count"] == 6
    assert abs(doc["avg_conn_per_minute"] - 11.0) < 0.01

async def test_new_entity_creates_baseline(learner, mock_es):
    # Simulate not found exception
    mock_es.get.side_effect = Exception("Not found")
    
    await learner.update_baseline(mock_es, "new_user", {"conn_count_1m": 5.0})
    
    mock_es.index.assert_called_once()
    args, kwargs = mock_es.index.call_args
    doc = kwargs["document"]
    
    assert doc["entity_key"] == "new_user"
    assert doc["observation_count"] == 1
    assert doc["avg_conn_per_minute"] == 5.0
    assert doc["std_conn_per_minute"] == 0.0

def test_compute_deviation_ratios_correct_math(learner):
    baseline = EntityBaseline(
        entity_key="user1", last_updated=datetime.utcnow(), observation_count=10,
        avg_conn_per_minute=10.0, std_conn_per_minute=2.0,
        avg_unique_dst_ports=0.0, std_unique_dst_ports=0.0, typical_protocols=[], typical_dst_ports=[],
        avg_process_spawn_count=0.0, std_process_spawn_count=0.0, known_process_names=[],
        avg_args_count=0.0, avg_alert_count=0.0, std_alert_count=0.0, avg_risk_score=0.0
    )
    
    ratios = learner.compute_deviation_ratios(baseline, {"conn_count_1m": 16.0})
    # abs(16 - 10) / 2 = 3.0
    assert "conn_count_1m" in ratios
    assert abs(ratios["conn_count_1m"] - 3.0) < 0.01

def test_deviation_capped_at_10x(learner):
    baseline = EntityBaseline(
        entity_key="user1", last_updated=datetime.utcnow(), observation_count=10,
        avg_conn_per_minute=10.0, std_conn_per_minute=1.0,
        avg_unique_dst_ports=0.0, std_unique_dst_ports=0.0, typical_protocols=[], typical_dst_ports=[],
        avg_process_spawn_count=0.0, std_process_spawn_count=0.0, known_process_names=[],
        avg_args_count=0.0, avg_alert_count=0.0, std_alert_count=0.0, avg_risk_score=0.0
    )
    
    ratios = learner.compute_deviation_ratios(baseline, {"conn_count_1m": 100.0})
    # abs(100 - 10) / 1 = 90.0, should be capped at 10.0
    assert ratios["conn_count_1m"] == 10.0

def test_format_deviation_context_only_significant(learner):
    baseline = EntityBaseline(
        entity_key="user1", last_updated=datetime.utcnow(), observation_count=10,
        avg_conn_per_minute=10.0, std_conn_per_minute=2.0,
        avg_unique_dst_ports=5.0, std_unique_dst_ports=1.0, typical_protocols=[], typical_dst_ports=[],
        avg_process_spawn_count=0.0, std_process_spawn_count=0.0, known_process_names=[],
        avg_args_count=0.0, avg_alert_count=0.0, std_alert_count=0.0, avg_risk_score=0.0
    )
    
    # conn_count_1m dev = 1.0 (<=2.0) so shouldn't be included
    # unique_dst_ports_1m dev = 5.0 (>2.0) so should be included
    deviations = {
        "conn_count_1m": 1.0,
        "unique_dst_ports_1m": 5.0
    }
    
    context = learner.format_deviation_context(deviations, {"conn_count_1m": 12.0, "unique_dst_ports_1m": 10.0}, baseline)
    
    assert "conn_per_minute" not in context
    assert "unique_dst_ports is 5.0x above baseline" in context
