import logging
from dataclasses import dataclass
from typing import Callable, Any

logger = logging.getLogger(__name__)

@dataclass
class Rule:
    rule_id: str
    name: str
    description: str
    mitre_tactic: str
    mitre_technique_id: str
    severity: str
    condition: Callable[[dict], bool]
    score: float

RULES = [
    Rule(
        rule_id="RULE-001",
        name="Brute Force",
        description="Multiple alerts combined with credential access signals.",
        mitre_tactic="Credential Access",
        mitre_technique_id="T1110",
        severity="high",
        condition=lambda f: float(f.get("alert_count", 0)) > 5 and float(f.get("has_credential_access", 0)) == 1,
        score=0.75
    ),
    Rule(
        rule_id="RULE-002",
        name="Port Scan",
        description="High volume of unique destination ports accessed rapidly.",
        mitre_tactic="Discovery",
        mitre_technique_id="T1046",
        severity="medium",
        condition=lambda f: float(f.get("unique_dst_port_count", 0)) > 50 and float(f.get("conn_per_minute", 0)) > 20,
        score=0.70
    ),
    Rule(
        rule_id="RULE-003",
        name="LOLBin Execution",
        description="Living off the land binary executed in a non-interactive shell.",
        mitre_tactic="Execution",
        mitre_technique_id="T1059",
        severity="high",
        condition=lambda f: float(f.get("has_lolbin", 0)) == 1 and float(f.get("non_interactive_shell", 0)) == 1,
        score=0.80
    ),
    Rule(
        rule_id="RULE-004",
        name="Encoded Payload",
        description="Process executed with base64 or encoded command line arguments.",
        mitre_tactic="Defense Evasion",
        mitre_technique_id="T1059.001",
        severity="high",
        condition=lambda f: float(f.get("has_encoded_payload", 0)) == 1,
        score=0.85
    ),
    Rule(
        rule_id="RULE-005",
        name="Download Cradle",
        description="Execution of known download cradles like wget, curl, or Invoke-WebRequest.",
        mitre_tactic="Command and Control",
        mitre_technique_id="T1105",
        severity="high",
        condition=lambda f: float(f.get("has_download_cradle", 0)) == 1,
        score=0.80
    ),
    Rule(
        rule_id="RULE-006",
        name="Suspicious Parent",
        description="Process launched by an anomalous parent (e.g., word launching powershell).",
        mitre_tactic="Defense Evasion",
        mitre_technique_id="T1055",
        severity="critical",
        condition=lambda f: float(f.get("parent_child_anomaly", 0)) == 1,
        score=0.90
    ),
    Rule(
        rule_id="RULE-007",
        name="Exfiltration Signal",
        description="Exfiltration tactic alert correlated with internal-to-external network flow.",
        mitre_tactic="Exfiltration",
        mitre_technique_id="T1041",
        severity="critical",
        condition=lambda f: float(f.get("has_exfiltration_tactic", 0)) == 1 and float(f.get("is_internal_to_external", 0)) == 1,
        score=0.85
    ),
    Rule(
        rule_id="RULE-008",
        name="Persistence",
        description="Persistence alert correlated with execution from a temporary or appdata directory.",
        mitre_tactic="Persistence",
        mitre_technique_id="T1053",
        severity="high",
        condition=lambda f: float(f.get("has_persistence_tactic", 0)) == 1 and float(f.get("from_temp_dir", 0)) == 1,
        score=0.80
    ),
    Rule(
        rule_id="RULE-009",
        name="Lateral Movement",
        description="Lateral movement alert correlated with connections to multiple unique internal hosts.",
        mitre_tactic="Lateral Movement",
        mitre_technique_id="T1021",
        severity="critical",
        condition=lambda f: float(f.get("has_lateral_movement", 0)) == 1 and float(f.get("unique_dst_ip_count", 0)) > 5,
        score=0.90
    ),
    Rule(
        rule_id="RULE-010",
        name="Alert Burst",
        description="Massive spike in alert volume accompanied by high risk scores.",
        mitre_tactic="Impact",
        mitre_technique_id="TA0040",
        severity="medium",
        condition=lambda f: float(f.get("alert_burst_flag", 0)) == 1 and float(f.get("max_risk_score", 0)) > 70,
        score=0.70
    )
]

def evaluate_rules(feature_row: dict) -> dict:
    """
    Evaluates a flat ML feature mapping against deterministic SOC signatures.
    Returns tracking context and maximum normalized risk mapping.
    """
    triggered = []
    tactics = set()
    techniques = set()
    max_score = 0.0
    
    for rule in RULES:
        try:
            if rule.condition(feature_row):
                triggered.append(rule)
                tactics.add(rule.mitre_tactic)
                techniques.add(rule.mitre_technique_id)
                if rule.score > max_score:
                    max_score = rule.score
        except Exception as e:
            logger.error(f"Error evaluating deterministic rule {rule.rule_id}: {e}")
            
    return {
        "triggered_rules": triggered,
        "rule_score": float(max_score),
        "mitre_tactics": list(tactics),
        "mitre_techniques": list(techniques)
    }

def get_rule_explanation(triggered_rules: list[Rule]) -> str:
    """Provides a human-readable threat summary formatted for SLM injection."""
    if not triggered_rules:
        return "No deterministic threat rules triggered."
        
    lines = ["Deterministic rules triggered:"]
    for r in triggered_rules:
        lines.append(f"- {r.rule_id} ({r.name}): {r.description} (MITRE {r.mitre_technique_id} - {r.mitre_tactic}, Severity: {r.severity.upper()})")
        
    return "\n".join(lines)
