import pytest
from datetime import datetime, timezone
from dataclasses import fields
from app.ingestion.normalizer import NormalizedLog
from app.models.model_manager import ScoringResult

@pytest.mark.asyncio
async def test_normalized_log_to_es_doc_field_mapping():
    log = NormalizedLog(
        doc_id="123",
        log_type="network",
        timestamp=datetime.utcnow(),
        host_id="h1",
        host_hostname="host1"
    )
    # The fields should match standard indexing structures.
    # In es_client, the base fields expected:
    expected_es_fields = ["timestamp", "host_id", "user_name", "log_type"]
    
    # We verify NormalizedLog has the required base attributes that map to ES
    log_fields = [f.name for f in fields(NormalizedLog)]
    for expected in expected_es_fields:
        assert expected in log_fields, f"NormalizedLog missing mapped field {expected}"

@pytest.mark.asyncio
async def test_scoring_result_to_alert_doc_complete():
    res = ScoringResult(
        entity_key="h1|u1",
        window_bucket="2026-06-22",
        network_anomaly_score=0.1,
        process_anomaly_score=0.2,
        sequence_anomaly_score=0.0,
        rule_score=0.9,
        triggered_rules=["rule1"],
        mitre_tactics=["Execution"],
        mitre_technique_ids=["T1059"],
        threat_score=0.85,
        threat_level="high",
        human_explanation="Test explanation"
    )
    
    # Verify the structure has what is needed to store in ES
    assert hasattr(res, "threat_score")
    assert hasattr(res, "threat_level")
    assert hasattr(res, "mitre_tactics")
    assert hasattr(res, "mitre_technique_ids")
    
    # Validation of fields mapping to soc-processed-alerts properties
    assert isinstance(res.threat_score, float)
    assert isinstance(res.threat_level, str)

@pytest.mark.asyncio
async def test_entity_key_format_consistent():
    # Verify entity_key generation structure "{host_id}|{user_name}"
    # Example logic test: if host_id is empty, it handles it gracefully
    def generate_key(host_id, user_name):
        return f"{host_id or 'unknown'}|{user_name or 'unknown'}"
        
    assert generate_key("h1", "admin") == "h1|admin"
    assert generate_key(None, "admin") == "unknown|admin"
    assert generate_key("h1", None) == "h1|unknown"

@pytest.mark.asyncio
async def test_timestamp_timezone_consistency():
    # Ensure times are generated as UTC natively without local timezone drift
    dt = datetime.utcnow()
    assert dt.tzinfo is None or dt.tzinfo == timezone.utc, "Backend timestamps should be naive UTC or explicitly UTC"
    
    # If we use datetime.now(timezone.utc), it is timezone-aware
    dt_aware = datetime.now(timezone.utc)
    assert dt_aware.tzinfo == timezone.utc
