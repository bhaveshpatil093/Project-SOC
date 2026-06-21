import pytest
from app.models.rule_engine import RuleEngine

@pytest.fixture
def engine():
    """Provides a fresh RuleEngine instance."""
    return RuleEngine()

def test_rule_002_triggers_on_port_scan(engine):
    """Test RULE-002: unique_dst_port_count > 50 and conn_per_minute > 20."""
    features = {
        "unique_dst_port_count": 80,
        "conn_per_minute": 25
    }
    result = engine.evaluate(features)
    assert "RULE-002" in result["triggered_rules"]

def test_no_rules_trigger_on_clean_data(engine):
    """Test that safe data returns empty rule arrays and zero score."""
    features = {
        "unique_dst_port_count": 5,
        "conn_per_minute": 10,
        "failed_logins": 0,
        "bytes_out": 1000
    }
    result = engine.evaluate(features)
    assert len(result["triggered_rules"]) == 0
    assert result["score"] == 0.0

def test_rule_score_is_max_of_triggered(engine):
    """Test that the composite rule score equals the highest severity triggered rule."""
    features = {
        "unique_dst_port_count": 80,  # RULE-002 (Medium -> score 0.6)
        "failed_logins": 15           # RULE-003 (High -> score 0.85)
    }
    result = engine.evaluate(features)
    assert "RULE-002" in result["triggered_rules"]
    assert "RULE-003" in result["triggered_rules"]
    assert result["score"] == 0.85

def test_get_rule_explanation_non_empty(engine):
    """Ensure the engine provides human-readable explanations."""
    explanation = engine.get_rule_explanation("RULE-001")
    assert explanation is not None
    assert "High volume of outbound data" in explanation

def test_all_10_rules_trigger_correctly(engine):
    """Verify trigger conditions for all 10 mapped rules."""
    # R1: Data Exfil
    assert "RULE-001" in engine.evaluate({"bytes_out": 2e9, "conn_per_minute": 1})["triggered_rules"]
    # R2: Port Scan
    assert "RULE-002" in engine.evaluate({"unique_dst_port_count": 55, "conn_per_minute": 25})["triggered_rules"]
    # R3: Brute Force
    assert "RULE-003" in engine.evaluate({"failed_logins": 11})["triggered_rules"]
    # R4: Privilege Escalation
    assert "RULE-004" in engine.evaluate({"privilege_escalation_attempts": 2})["triggered_rules"]
    # R5: Lateral Movement
    assert "RULE-005" in engine.evaluate({"lateral_movement_flags": 3, "unique_dst_ip_count": 15})["triggered_rules"]
    # R6: Ransomware
    assert "RULE-006" in engine.evaluate({"file_modifications_per_min": 1500, "entropy_score": 0.95})["triggered_rules"]
    # R7: Command & Control
    assert "RULE-007" in engine.evaluate({"beaconing_score": 0.9, "rare_protocol_flag": 1})["triggered_rules"]
    # R8: Credential Dumping
    assert "RULE-008" in engine.evaluate({"lsass_access_flag": 1, "suspicious_process_count": 2})["triggered_rules"]
    # R9: Persistence
    assert "RULE-009" in engine.evaluate({"registry_modifications": 55, "scheduled_task_creations": 2})["triggered_rules"]
    # R10: Defense Evasion
    assert "RULE-010" in engine.evaluate({"log_clearing_flag": 1})["triggered_rules"]
