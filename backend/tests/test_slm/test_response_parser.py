import pytest
from app.slm.response_parser import (
    extract_summary,
    extract_evidence,
    extract_actions,
    extract_verdict,
    extract_mitre_ids,
    extract_urgency,
    parse_slm_response
)

def test_extract_summary_finds_summary_section():
    text = "Summary: This is the summary text.\n\nEvidence: Some evidence"
    assert extract_summary(text) == "This is the summary text."
    
    text_fallback = "This is a fallback summary that is longer than 20 characters.\n\nEvidence: Some evidence"
    assert extract_summary(text_fallback) == "This is a fallback summary that is longer than 20 characters."

def test_extract_evidence_handles_multiple_bullet_styles():
    text = "Evidence:\n- Point 1\n* Point 2\n• Point 3\n1. Point 4"
    evidence = extract_evidence(text)
    assert len(evidence) == 4
    assert evidence == ["Point 1", "Point 2", "Point 3", "Point 4"]

def test_extract_actions_numbered_list():
    text = "Recommended Action:\n1. Isolate host\n2. Reset password"
    actions = extract_actions(text)
    assert actions == ["Isolate host", "Reset password"]

def test_extract_verdict_true_positive():
    text = "This is a true positive. High confidence."
    verdict, conf = extract_verdict(text)
    assert verdict == "TRUE_POSITIVE"
    assert conf == "HIGH"

def test_extract_verdict_false_positive():
    text = "This appears to be a false positive with low confidence."
    verdict, conf = extract_verdict(text)
    assert verdict == "FALSE_POSITIVE"
    assert conf == "LOW"

def test_extract_mitre_ids_regex_matches():
    text = "Tactics used include T1059 and T1110.001."
    mitre_ids = extract_mitre_ids(text)
    assert mitre_ids == ["T1059", "T1110.001"]

def test_extract_urgency_immediate_keyword():
    assert extract_urgency("Immediate action required.") == "IMMEDIATE"
    assert extract_urgency("Urgent!") == "IMMEDIATE"
    assert extract_urgency("Just monitor this.") == "MONITOR"
    assert extract_urgency("Low priority alert.") == "LOW_PRIORITY"

def test_parse_handles_malformed_response_gracefully():
    text = "Just some random text with T1059 and it is a true positive."
    parsed = parse_slm_response(text)
    
    assert parsed.raw_text == text
    assert parsed.verdict == "TRUE_POSITIVE"
    assert parsed.mitre_techniques == ["T1059"]
    assert len(parsed.evidence_points) == 0
    assert len(parsed.action_items) == 0
