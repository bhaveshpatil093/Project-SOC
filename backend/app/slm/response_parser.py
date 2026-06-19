import re
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

@dataclass
class ParsedSLMResponse:
    raw_text: str
    summary: Optional[str]
    evidence_points: List[str]
    action_items: List[str]
    verdict: Optional[str]
    confidence: Optional[str]
    mitre_techniques: List[str]
    urgency: Optional[str]
    referenced_alerts: List[str]

def extract_summary(text: str) -> Optional[str]:
    # Look for "Summary:" block
    match = re.search(r"Summary:(.*?)(?=\n\n|\n(?:Evidence|Action|Recommended Action|Steps):|$)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback to first non-empty paragraph
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        # Don't pick headers or very short things
        for p in paragraphs:
            if not p.lower().startswith(("evidence:", "action:", "recommended action:", "steps:")) and len(p) > 20:
                return p
    return None

def extract_evidence(text: str) -> List[str]:
    match = re.search(r"(?:Evidence|Key Indicators):(.*?)(\n\n|\n(?:Action|Recommended Action|Steps):|$)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    
    block = match.group(1).strip()
    points = []
    for line in block.split('\n'):
        line = line.strip()
        # Handle "- ", "• ", "* ", "1. "
        clean_line = re.sub(r"^[-•*]|\d+\.", "", line).strip()
        if clean_line:
            points.append(clean_line)
    return points

def extract_actions(text: str) -> List[str]:
    match = re.search(r"(?:Action|Recommended Action|Steps|Remediation):(.*)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
        
    block = match.group(1).strip()
    actions = []
    for line in block.split('\n'):
        line = line.strip()
        clean_line = re.sub(r"^[-•*]|\d+\.", "", line).strip()
        if clean_line:
            actions.append(clean_line)
    return actions

def extract_verdict(text: str) -> Tuple[Optional[str], Optional[str]]:
    text_lower = text.lower()
    verdict = None
    if "true positive" in text_lower or "true_positive" in text_lower:
        verdict = "TRUE_POSITIVE"
    elif "false positive" in text_lower or "false_positive" in text_lower:
        verdict = "FALSE_POSITIVE"
    else:
        verdict = "UNKNOWN"
        
    confidence = "MEDIUM"
    if "high confidence" in text_lower or "highly confident" in text_lower:
        confidence = "HIGH"
    elif "low confidence" in text_lower or "unsure" in text_lower:
        confidence = "LOW"
        
    return verdict, confidence

def extract_mitre_ids(text: str) -> List[str]:
    matches = re.findall(r"T\d{4}(?:\.\d{3})?", text, re.IGNORECASE)
    return sorted(list(set(m.upper() for m in matches)))

def extract_urgency(text: str) -> Optional[str]:
    text_lower = text.lower()
    if "immediate" in text_lower or "urgent" in text_lower or "critical" in text_lower:
        return "IMMEDIATE"
    elif "monitor" in text_lower or "watch" in text_lower:
        return "MONITOR"
    elif "low priority" in text_lower or "ignore" in text_lower:
        return "LOW_PRIORITY"
    return None
    
def extract_referenced_alerts(text: str) -> List[str]:
    # Alert IDs are UUIDs or purely numeric (in our system, they are string UUIDs generally)
    # Simple UUID regex fallback matching
    matches = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text, re.IGNORECASE)
    return sorted(list(set(matches)))

def parse_slm_response(raw_text: str) -> ParsedSLMResponse:
    verdict, confidence = extract_verdict(raw_text)
    
    return ParsedSLMResponse(
        raw_text=raw_text,
        summary=extract_summary(raw_text),
        evidence_points=extract_evidence(raw_text),
        action_items=extract_actions(raw_text),
        verdict=verdict,
        confidence=confidence,
        mitre_techniques=extract_mitre_ids(raw_text),
        urgency=extract_urgency(raw_text),
        referenced_alerts=extract_referenced_alerts(raw_text)
    )

def format_for_display(parsed: ParsedSLMResponse) -> dict:
    return asdict(parsed)
