import pytest
from datetime import datetime, timedelta
from app.scoring.correlator import AlertCorrelator, Incident

def test_correlate_groups_by_entity_and_time():
    correlator = AlertCorrelator(time_window_minutes=15, min_alerts_for_incident=2, score_threshold=0.4)
    now = datetime.utcnow()
    
    alerts = [
        {"id": "1", "host_id": "h1", "user_name": "u1", "timestamp": now.isoformat(), "threat_score": 0.5},
        {"id": "2", "host_id": "h1", "user_name": "u1", "timestamp": (now + timedelta(minutes=5)).isoformat(), "threat_score": 0.5},
        {"id": "3", "host_id": "h1", "user_name": "u1", "timestamp": (now + timedelta(minutes=20)).isoformat(), "threat_score": 0.5},
        {"id": "4", "host_id": "h2", "user_name": "u2", "timestamp": now.isoformat(), "threat_score": 0.5},
        {"id": "5", "host_id": "h2", "user_name": "u2", "timestamp": (now + timedelta(minutes=10)).isoformat(), "threat_score": 0.5},
    ]
    
    incidents = correlator.correlate(alerts)
    # Expected: 
    # h1:u1 -> [1, 2] (cluster 1, 2 alerts), [3] (cluster 2, 1 alert, dropped)
    # h2:u2 -> [4, 5] (cluster 1, 2 alerts)
    assert len(incidents) == 2
    entity_keys = sorted([inc.entity_key for inc in incidents])
    assert entity_keys == ["h1:u1", "h2:u2"]
    
    h1_inc = next(inc for inc in incidents if inc.entity_key == "h1:u1")
    assert len(h1_inc.alert_ids) == 2
    assert "1" in h1_inc.alert_ids and "2" in h1_inc.alert_ids

def test_correlate_respects_min_alerts_threshold():
    correlator = AlertCorrelator(min_alerts_for_incident=2)
    now = datetime.utcnow()
    
    alerts = [
        {"id": "1", "host_id": "h1", "user_name": "u1", "timestamp": now.isoformat(), "threat_score": 0.5}
    ]
    
    incidents = correlator.correlate(alerts)
    assert len(incidents) == 0

def test_correlate_single_critical_alert_becomes_incident():
    correlator = AlertCorrelator(min_alerts_for_incident=2)
    now = datetime.utcnow()
    
    alerts = [
        {"id": "1", "host_id": "h1", "user_name": "u1", "timestamp": now.isoformat(), "threat_score": 1.0}
    ]
    
    incidents = correlator.correlate(alerts)
    assert len(incidents) == 1
    assert incidents[0].threat_level == "critical"

def test_composite_score_formula():
    correlator = AlertCorrelator(min_alerts_for_incident=2)
    now = datetime.utcnow()
    
    alerts = [
        {"id": "1", "host_id": "h1", "user_name": "u1", "timestamp": now.isoformat(), "threat_score": 0.9, "log_type": "typeA"},
        {"id": "2", "host_id": "h1", "user_name": "u1", "timestamp": (now + timedelta(minutes=1)).isoformat(), "threat_score": 0.3, "log_type": "typeB"}
    ]
    
    incidents = correlator.correlate(alerts)
    assert len(incidents) == 1
    inc = incidents[0]
    
    # max = 0.9, mean = 0.6, types >= 2 -> bonus 0.2
    # score = (0.9 * 0.5) + (0.6 * 0.3) + 0.2 = 0.45 + 0.18 + 0.2 = 0.83
    assert abs(inc.incident_threat_score - 0.83) < 0.001

def test_determine_attack_stage_single_tactic():
    correlator = AlertCorrelator()
    assert correlator.determine_attack_stage(["Reconnaissance"]) == "reconnaissance"
    assert correlator.determine_attack_stage(["Lateral Movement"]) == "lateral_movement"

def test_determine_attack_stage_multi_stage():
    correlator = AlertCorrelator()
    tactics = ["Reconnaissance", "Initial Access", "Lateral Movement"]
    assert correlator.determine_attack_stage(tactics) == "multi_stage"

def test_merge_incidents_extends_alert_list():
    correlator = AlertCorrelator()
    now = datetime.utcnow()
    
    inc = correlator._create_incident_from_cluster([
        {"id": "1", "host_id": "h1", "user_name": "u1", "timestamp": now.isoformat(), "threat_score": 0.5, "log_type": "A", "mitre_tactic": "Reconnaissance"}
    ])
    
    new_alerts = [
        {"id": "2", "host_id": "h1", "user_name": "u1", "timestamp": (now + timedelta(minutes=5)).isoformat(), "threat_score": 0.8, "log_type": "B", "mitre_tactic": "Initial Access"}
    ]
    
    merged = correlator.merge_incidents(inc, new_alerts)
    assert len(merged.alert_ids) == 2
    assert set(merged.alert_ids) == {"1", "2"}
    assert set(merged.log_types_involved) == {"A", "B"}
    assert set(merged.mitre_tactics) == {"Reconnaissance", "Initial Access"}
    # duration = 5 minutes = 300 seconds
    assert merged.duration_seconds == 300.0

def test_time_window_boundary():
    correlator = AlertCorrelator(time_window_minutes=15, min_alerts_for_incident=1)
    now = datetime.utcnow()
    
    alerts = [
        {"id": "1", "host_id": "h1", "user_name": "u1", "timestamp": now.isoformat(), "threat_score": 0.5},
        {"id": "2", "host_id": "h1", "user_name": "u1", "timestamp": (now + timedelta(minutes=14)).isoformat(), "threat_score": 0.5},
        {"id": "3", "host_id": "h1", "user_name": "u1", "timestamp": (now + timedelta(minutes=30)).isoformat(), "threat_score": 0.5},
    ]
    
    incidents = correlator.correlate(alerts)
    # T+0 and T+14 are within 15 minutes of T+0
    # T+30 is in a new cluster
    assert len(incidents) == 2
    assert len(incidents[0].alert_ids) == 2
    assert set(incidents[0].alert_ids) == {"1", "2"}
    assert len(incidents[1].alert_ids) == 1
    assert incidents[1].alert_ids == ["3"]
