import pytest
from unittest.mock import MagicMock
from app.models.model_manager import ModelManager

@pytest.fixture
def manager():
    """Provides a fresh ModelManager with mocked internal models."""
    mgr = ModelManager()
    
    # Mock the internal models
    mgr.if_detector = MagicMock()
    mgr.if_detector.score_single.return_value = 0.5
    
    mgr.ae_detector = MagicMock()
    mgr.ae_detector.score_single.return_value = 0.6
    
    mgr.lstm_detector = MagicMock()
    mgr.lstm_detector.score_sequence.return_value = 0.7
    
    mgr.rule_engine = MagicMock()
    mgr.rule_engine.evaluate.return_value = {"score": 0.8, "triggered_rules": ["RULE-001"]}
    
    mgr.calibrator = MagicMock()
    mgr.calibrator.calibrate.return_value = 0.55
    
    # Enable models
    mgr.models_loaded["isolation_forest"] = True
    mgr.models_loaded["autoencoder"] = True
    mgr.models_loaded["lstm"] = True
    mgr.models_loaded["rules"] = True
    
    return mgr

def test_graceful_degradation_missing_model(manager):
    """Test weight redistribution when a model fails to load."""
    # Default weights: IF=0.35, AE=0.15, LSTM=0.25, Rules=0.25
    # If IF goes missing, weights should redistribute proportionally among the others.
    manager.models_loaded["isolation_forest"] = False
    
    scores = manager._calculate_ensemble_score({
        "isolation_forest": 0.5,  # Should be ignored
        "autoencoder": 0.6,
        "lstm": 0.7,
        "rules": 0.8
    })
    
    # New weights should sum to 1.0
    # Original sum without IF = 0.15 + 0.25 + 0.25 = 0.65
    # New AE = 0.15 / 0.65 = ~0.23
    # New LSTM = 0.25 / 0.65 = ~0.385
    # New Rules = 0.25 / 0.65 = ~0.385
    expected_score = (0.6 * 0.23) + (0.7 * 0.385) + (0.8 * 0.385)
    
    assert pytest.approx(scores["ensemble_score"], 0.1) == expected_score

def test_threat_level_thresholds(manager):
    """Verify threat score maps correctly to qualitative risk tiers."""
    # Low: < 0.3
    assert manager._get_threat_level(0.29) == "low"
    # Medium: 0.3 - 0.6
    assert manager._get_threat_level(0.31) == "medium"
    assert manager._get_threat_level(0.59) == "medium"
    # High: 0.6 - 0.8
    assert manager._get_threat_level(0.61) == "high"
    assert manager._get_threat_level(0.79) == "high"
    # Critical: > 0.8
    assert manager._get_threat_level(0.81) == "critical"

def test_score_all_entities_returns_list(manager):
    """Test bulk entity scoring orchestration."""
    features = [
        {"entity_key": "10.0.0.1", "feat1": 1},
        {"entity_key": "10.0.0.2", "feat1": 2}
    ]
    sequences = {
        "10.0.0.1": ["login", "logout"],
        "10.0.0.2": ["login", "fail"]
    }
    
    results = manager.score_all_entities(features, sequences)
    
    assert len(results) == 2
    # Check that it returns ScoringResult objects
    assert hasattr(results[0], "entity_key")
    assert hasattr(results[0], "threat_score")
    assert results[0].entity_key == "10.0.0.1"

def test_ensemble_score_bounded_0_1(manager):
    """Ensure the final blended ensemble score never breaches bounds."""
    scores = manager._calculate_ensemble_score({
        "isolation_forest": 0.99,
        "autoencoder": 0.99,
        "lstm": 0.99,
        "rules": 0.99
    })
    assert 0.0 <= scores["ensemble_score"] <= 1.0
    
    scores_low = manager._calculate_ensemble_score({
        "isolation_forest": 0.0,
        "autoencoder": 0.0,
        "lstm": 0.0,
        "rules": 0.0
    })
    assert 0.0 <= scores_low["ensemble_score"] <= 1.0
