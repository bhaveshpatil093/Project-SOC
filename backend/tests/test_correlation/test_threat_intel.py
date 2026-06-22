import pytest
from app.scoring.threat_intel import ThreatIntelEnricher

@pytest.fixture
def enricher():
    return ThreatIntelEnricher()

def test_known_bad_ip_detected(enricher):
    # Tor exit node range in KNOWN_BAD_IP_RANGES (185.220.0.0/16)
    res = enricher.check_ip_reputation("185.220.10.5")
    assert res["is_bad"] is True
    assert "185.220.0.0" in res["matching_range"]

def test_safe_process_not_flagged(enricher):
    res = enricher.check_process_reputation("svchost.exe")
    assert res["is_known_safe"] is True
    assert res["is_known_malicious"] is False

def test_known_malicious_process_flagged(enricher):
    res = enricher.check_process_reputation("mimikatz.exe")
    assert res["is_known_malicious"] is True
    assert res["is_known_safe"] is False

def test_suspicious_tld_detected(enricher):
    res = enricher.check_domain_reputation("malicious-c2.xyz")
    assert res["has_suspicious_tld"] is True
    assert res["has_c2_pattern"] is True  # because 'c2' is in KNOWN_C2_PATTERNS

def test_intel_score_boost_capped_at_1(enricher):
    # All bad triggers
    feature_row = {
        "src_ip": "185.220.10.5",     # Bad IP (+0.1)
        "process_name": "mimikatz.exe", # Bad Process (+0.15)
        "dns_query": "malicious-c2.xyz" # Bad Domain (+0.1)
    }
    
    alert = {"threat_score": 0.8}
    enriched = enricher.enrich_alert(alert, feature_row)
    
    # 0.1 + 0.15 + 0.1 = 0.35 boost
    assert enriched["threat_intel"]["intel_score_boost"] == 0.35
    
    # Max score is 1.0
    final_score = enricher.adjust_threat_score(0.8, enriched["threat_intel"])
    assert final_score == 1.0

def test_intel_score_decreased_for_safe_process(enricher):
    feature_row = {
        "process_name": "svchost.exe" # Safe Process (-0.1)
    }
    
    alert = {"threat_score": 0.5}
    enriched = enricher.enrich_alert(alert, feature_row)
    
    assert enriched["threat_intel"]["intel_score_boost"] == -0.1
    
    final_score = enricher.adjust_threat_score(0.5, enriched["threat_intel"])
    assert final_score == 0.4
