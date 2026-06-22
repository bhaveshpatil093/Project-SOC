import pytest
from datetime import datetime, timedelta
from app.models.pattern_detector import PatternDetector, PATTERNS, PatternStep

@pytest.fixture
def detector():
    return PatternDetector()

def test_pat001_matches_full_sequence(detector):
    now = datetime.utcnow()
    alerts = [
        {"id": "1", "log_type": "process", "timestamp": now.isoformat(), "has_download_cradle": True, "mitre_technique": "T1105"},
        {"id": "2", "log_type": "process", "timestamp": (now + timedelta(minutes=1)).isoformat(), "has_encoded_payload": True, "mitre_technique": "T1059.001"},
        {"id": "3", "log_type": "network", "timestamp": (now + timedelta(minutes=2)).isoformat(), "is_internal_to_external": True, "mitre_technique": "T1041"}
    ]
    
    matches = detector.detect_patterns(None, alerts)
    assert len(matches) == 1
    assert matches[0].pattern_id == "PAT-001"
    assert matches[0].confidence >= 0.8
    assert matches[0].matched_alerts == ["1", "2", "3"]

def test_pat001_no_match_missing_step(detector):
    now = datetime.utcnow()
    # Missing step 2
    alerts = [
        {"id": "1", "log_type": "process", "timestamp": now.isoformat(), "has_download_cradle": True, "mitre_technique": "T1105"},
        {"id": "3", "log_type": "network", "timestamp": (now + timedelta(minutes=2)).isoformat(), "is_internal_to_external": True, "mitre_technique": "T1041"}
    ]
    
    matches = detector.detect_patterns(None, alerts)
    # Shouldn't reach 0.8 confidence for a 3-step pattern with only 1 match (since step 2 fails and breaks loop)
    # Wait, the loop breaks or skips?
    # if feature_ok fails, it doesn't break, it continues checking other alerts for step 2.
    # Since no alert matches step 2, step 2 is never matched.
    assert len(matches) == 0

def test_pattern_confidence_calculation(detector):
    now = datetime.utcnow()
    alerts = [
        {"id": "1", "log_type": "process", "timestamp": now.isoformat(), "has_download_cradle": True, "mitre_technique": "T1105"},
        {"id": "2", "log_type": "process", "timestamp": (now + timedelta(minutes=1)).isoformat(), "has_encoded_payload": False, "mitre_technique": "T1059.001"},
        {"id": "3", "log_type": "network", "timestamp": (now + timedelta(minutes=2)).isoformat(), "is_internal_to_external": True, "mitre_technique": "T1041"}
    ]
    # In step 2, has_encoded_payload is False, so feature_match_score isn't incremented.
    # We might not meet the confidence threshold depending on implementation.
    matches = detector.detect_patterns(None, alerts)
    assert len(matches) == 0  # Should be below 0.8

def test_pattern_respects_time_window(detector):
    now = datetime.utcnow()
    # PAT-001 time window is 30 mins
    alerts = [
        {"id": "1", "log_type": "process", "timestamp": now.isoformat(), "has_download_cradle": True, "mitre_technique": "T1105"},
        {"id": "2", "log_type": "process", "timestamp": (now + timedelta(minutes=5)).isoformat(), "has_encoded_payload": True, "mitre_technique": "T1059.001"},
        {"id": "3", "log_type": "network", "timestamp": (now + timedelta(minutes=45)).isoformat(), "is_internal_to_external": True, "mitre_technique": "T1041"}
    ]
    matches = detector.detect_patterns(None, alerts)
    assert len(matches) == 0

def test_get_pattern_explanation_format(detector):
    now = datetime.utcnow()
    alerts = [
        {"id": "1", "log_type": "process", "timestamp": now.isoformat(), "process_name": "vssadmin.exe", "mitre_technique": "T1486"},
        {"id": "2", "log_type": "process", "timestamp": (now + timedelta(minutes=1)).isoformat(), "process_name": "vssadmin.exe", "mitre_technique": "T1490"}
    ]
    matches = detector.detect_patterns(None, alerts)
    assert len(matches) == 1
    assert "PAT-004 matched:" in matches[0].explanation
    assert "Step 1 at T+0" in matches[0].explanation

def test_all_8_patterns_have_valid_steps():
    assert len(PATTERNS) >= 8
    for p in PATTERNS:
        assert len(p.steps) >= 2
        for s in p.steps:
            assert type(s) is PatternStep
            assert len(s.required_mitre) > 0
