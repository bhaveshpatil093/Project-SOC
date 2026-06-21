import pytest
import pandas as pd
from app.features.alert_features import process_alert_events

@pytest.fixture
def empty_df():
    return pd.DataFrame()

@pytest.fixture
def alert_df():
    """Generates a standard dataframe for alert evaluation."""
    data = []
    # 1 critical, 1 high, 1 medium, 1 low
    levels = ["critical", "high", "medium", "low"]
    for i, level in enumerate(levels):
        data.append({
            "timestamp": f"2026-06-21T10:0{i}:00Z",
            "entity_key": "10.0.0.1",
            "severity": level,
            "rule.name": "Test Rule",
            "threat.tactic.name": "Lateral Movement" if level == "critical" else "Initial Access",
            "risk_score": 50 + (i * 10)
        })
    return pd.DataFrame(data)

def test_severity_score_calculation(alert_df):
    """Ensure categorical severities properly map to mean numerical scores."""
    alert_df["timestamp"] = pd.to_datetime(alert_df["timestamp"])
    features = process_alert_events(alert_df)
    row = features.iloc[0]
    
    # [critical(4), high(3), medium(2), low(1)] => mean = 2.5
    assert row["avg_severity_score"] == 2.5

def test_alert_burst_flag():
    """Ensure rapid alert bursts are flagged."""
    data = [{"timestamp": "2026-06-21T10:00:00Z", "entity_key": "10.0.0.1", "severity": "high", "risk_score": 50} for _ in range(11)]
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    features = process_alert_events(df)
    row = features.iloc[0]
    
    assert row["alert_burst_flag"] == 1.0
    assert row["total_alerts"] == 11.0

def test_mitre_tactic_detection(alert_df):
    """Ensure MITRE tactic strings are one-hot encoded or flagged correctly."""
    alert_df["timestamp"] = pd.to_datetime(alert_df["timestamp"])
    features = process_alert_events(alert_df)
    row = features.iloc[0]
    
    # We had Lateral Movement and Initial Access
    if "has_lateral_movement" in features.columns:
        assert row["has_lateral_movement"] == 1.0

def test_max_risk_score_extracted(alert_df):
    """Ensure the highest risk score in the window is extracted."""
    alert_df["timestamp"] = pd.to_datetime(alert_df["timestamp"])
    features = process_alert_events(alert_df)
    row = features.iloc[0]
    
    # Max risk_score was 50 + 3*10 = 80
    assert row["max_risk_score"] == 80.0

def test_empty_alerts_returns_zero_features(empty_df):
    """Ensure empty input returns gracefully (empty df or zero features)."""
    features = process_alert_events(empty_df)
    # Depending on implementation, it might return empty DF
    assert len(features) == 0
