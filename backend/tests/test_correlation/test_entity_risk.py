import pytest
from datetime import datetime, timedelta
from app.scoring.entity_risk import EntityRiskScorer, EntityRiskProfile

@pytest.fixture
def scorer():
    return EntityRiskScorer(decay_half_life_hours=48.0)

def test_risk_decay_over_time(scorer):
    # 48h half-life: score after 48h should be ~50% of original
    now = datetime.utcnow()
    last_alert_time = now - timedelta(hours=48)
    
    profile = EntityRiskProfile(
        entity_key="user1",
        current_risk_score=80.0,
        last_alert_at=last_alert_time.isoformat() + "Z"
    )
    
    new_alert = {"mitre_tactics": ["Tactic1"]}
    
    # Update with an alert score of 0.0 to see pure decay
    # decayed = 80.0 * (0.5 ^ (48/48)) = 40.0
    # cumulative = 40.0 + (0.0 * 20) = 40.0
    updated_profile = scorer.update_risk_profile(profile, 0.0, new_alert)
    
    assert abs(updated_profile.current_risk_score - 40.0) < 0.1

def test_risk_increases_with_new_alert(scorer):
    now = datetime.utcnow()
    last_alert_time = now - timedelta(hours=0) # No time passed
    
    profile = EntityRiskProfile(
        entity_key="user1",
        current_risk_score=50.0,
        last_alert_at=last_alert_time.isoformat() + "Z"
    )
    
    # 0.5 alert score -> 0.5 * 20 = 10 points
    updated = scorer.update_risk_profile(profile, 0.5, {})
    assert abs(updated.current_risk_score - 60.0) < 0.1

def test_risk_level_thresholds(scorer):
    assert scorer.compute_risk_level(10) == "low"
    assert scorer.compute_risk_level(30) == "medium"
    assert scorer.compute_risk_level(60) == "high"
    assert scorer.compute_risk_level(85) == "critical"

def test_watchlist_add_remove():
    import asyncio
    from unittest.mock import AsyncMock
    
    scorer = EntityRiskScorer()
    mock_es = AsyncMock()
    
    # Assume get_or_create_profile returns a fresh profile
    mock_es.get.return_value = {"found": False}
    
    async def run_test():
        await scorer.add_to_watchlist(mock_es, "user1", "Suspicious activity")
        mock_es.index.assert_called()
        doc = mock_es.index.call_args[1]["document"]
        assert doc["is_watchlisted"] is True
        assert doc["watchlist_reason"] == "Suspicious activity"
        
        await scorer.remove_from_watchlist(mock_es, "user1")
        doc2 = mock_es.index.call_args[1]["document"]
        assert doc2["is_watchlisted"] is False
        assert doc2["watchlist_reason"] is None

    asyncio.run(run_test())

def test_trend_detection_increasing(scorer):
    assert scorer._determine_trend([10.0, 10.0, 20.0, 20.0]) == "increasing"
    assert scorer._determine_trend([40.0, 40.0, 20.0, 20.0]) == "decreasing"
    assert scorer._determine_trend([10.0, 11.0, 10.0, 12.0]) == "stable"
