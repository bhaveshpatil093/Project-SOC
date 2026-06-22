import pytest
from datetime import datetime, timezone, timedelta
from app.models.temporal_analyzer import TemporalAnalyzer, TemporalBaseline

@pytest.fixture
def analyzer():
    # Use UTC for testing to avoid local time surprises if timezone is not strictly handled
    return TemporalAnalyzer(timezone="UTC")

def test_off_hours_detection_3am(analyzer):
    baseline = TemporalBaseline("user1", {}, (9, 18), True)
    dt = datetime(2026, 6, 22, 3, 0, tzinfo=timezone.utc) # Monday 3 AM
    is_off, severity = analyzer.is_off_hours(dt, baseline)
    assert is_off is True
    assert severity == 1.8 # Early morning

def test_business_hours_not_flagged(analyzer):
    baseline = TemporalBaseline("user1", {}, (9, 18), True)
    dt = datetime(2026, 6, 22, 14, 0, tzinfo=timezone.utc) # Monday 2 PM
    is_off, severity = analyzer.is_off_hours(dt, baseline)
    assert is_off is False
    assert severity == 1.0

def test_severity_multiplier_increases_at_night(analyzer):
    baseline = TemporalBaseline("user1", {}, (9, 18), True)
    dt_evening = datetime(2026, 6, 22, 20, 0, tzinfo=timezone.utc) # Monday 8 PM
    _, sev_evening = analyzer.is_off_hours(dt_evening, baseline)
    assert sev_evening == 1.3
    
    dt_night = datetime(2026, 6, 22, 23, 0, tzinfo=timezone.utc) # Monday 11 PM
    _, sev_night = analyzer.is_off_hours(dt_night, baseline)
    assert sev_night == 1.8

def test_temporal_anomaly_score_computation(analyzer):
    # Setup profile for Monday 10 AM (weekday 0, hour 10)
    baseline = TemporalBaseline(
        "user1", 
        {"0_10": {"conn_count_1m": (10.0, 2.0)}}, 
        (9, 18), 
        True
    )
    dt = datetime(2026, 6, 22, 10, 30, tzinfo=timezone.utc) # Monday 10:30 AM
    
    # Normal activity
    feature_row = {"conn_count_1m": 11.0}
    res = analyzer.compute_temporal_anomaly_score(feature_row, baseline, dt)
    assert res["temporal_score"] == 0.0
    
    # Anomalous activity (z-score > 2.0 -> (16-10)/2 = 3.0)
    feature_row_anom = {"conn_count_1m": 16.0}
    res_anom = analyzer.compute_temporal_anomaly_score(feature_row_anom, baseline, dt)
    # score = (3.0 / 10.0) * severity (1.0) = 0.3
    assert abs(res_anom["temporal_score"] - 0.3) < 0.01
    assert "conn_count_1m" in res_anom["most_anomalous_time_features"]
