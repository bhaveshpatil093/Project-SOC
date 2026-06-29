from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.scoring.correlator import Incident

from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class PatternStep:
    step_id: int
    log_type: str
    required_features: dict[str, Any]
    required_mitre: list[str]
    max_gap_minutes: int

@dataclass
class AttackPattern:
    pattern_id: str
    name: str
    description: str
    severity: str
    steps: list[PatternStep]
    time_window_minutes: int
    confidence_threshold: float

@dataclass
class PatternMatch:
    pattern_id: str
    name: str
    severity: str
    confidence: float
    matched_alerts: list[str]
    explanation: str

PATTERNS = [
    AttackPattern(
        pattern_id="PAT-001",
        name="PowerShell Download & Execute",
        description="Encoded PowerShell downloads and executes payload.",
        severity="critical",
        steps=[
            PatternStep(1, "process", {"has_download_cradle": True}, ["T1105"], 5),
            PatternStep(2, "process", {"has_encoded_payload": True}, ["T1059.001"], 5),
            PatternStep(3, "network", {"is_internal_to_external": True}, ["T1041", "T1071"], 10),
        ],
        time_window_minutes=30,
        confidence_threshold=0.8
    ),
    AttackPattern(
        pattern_id="PAT-002",
        name="Credential Dump + Lateral Movement",
        description="Brute force attack followed by credential dumping and lateral movement.",
        severity="critical",
        steps=[
            PatternStep(1, "security_alert", {}, ["T1110"], 15),
            PatternStep(2, "process", {}, ["T1003", "T1055"], 15),
            PatternStep(3, "network", {"is_internal_to_internal": True}, ["T1021"], 20),
        ],
        time_window_minutes=60,
        confidence_threshold=0.8
    ),
    AttackPattern(
        pattern_id="PAT-003",
        name="Living off the Land + Persistence",
        description="Native system binary execution followed by establishing persistence.",
        severity="high",
        steps=[
            PatternStep(1, "process", {"has_lolbin": True}, ["T1059", "T1218"], 10),
            PatternStep(2, "process", {}, ["T1053", "T1543"], 20),
        ],
        time_window_minutes=45,
        confidence_threshold=0.75
    ),
    AttackPattern(
        pattern_id="PAT-004",
        name="Ransomware Encryption Sequence",
        description="Mass file modification followed by shadow copy deletion.",
        severity="critical",
        steps=[
            PatternStep(1, "process", {}, ["T1486"], 15),
            PatternStep(2, "process", {"process_name": "vssadmin.exe"}, ["T1490"], 15),
        ],
        time_window_minutes=30,
        confidence_threshold=0.9
    ),
    AttackPattern(
        pattern_id="PAT-005",
        name="Cloud Exfiltration via Rclone",
        description="Large outbound data transfer using cloud sync tools.",
        severity="high",
        steps=[
            PatternStep(1, "process", {"process_name": "rclone"}, ["T1567", "T1048"], 5),
            PatternStep(2, "network", {"is_internal_to_external": True}, ["T1567"], 60),
        ],
        time_window_minutes=120,
        confidence_threshold=0.8
    ),
    AttackPattern(
        pattern_id="PAT-006",
        name="Initial Access via Phishing + C2",
        description="Office document spawns script which calls out to C2.",
        severity="critical",
        steps=[
            PatternStep(1, "process", {"parent_process_name": "winword.exe"}, ["T1566", "T1059"], 5),
            PatternStep(2, "network", {"is_internal_to_external": True}, ["T1071"], 15),
        ],
        time_window_minutes=30,
        confidence_threshold=0.85
    ),
    AttackPattern(
        pattern_id="PAT-007",
        name="Kerberoasting & AD Discovery",
        description="Active Directory enumeration followed by TGS request anomalies.",
        severity="high",
        steps=[
            PatternStep(1, "process", {"process_name": "bloodhound.exe"}, ["T1087", "T1069"], 20),
            PatternStep(2, "security_alert", {}, ["T1558"], 30),
        ],
        time_window_minutes=60,
        confidence_threshold=0.8
    ),
    AttackPattern(
        pattern_id="PAT-008",
        name="Web Shell Drop and Execution",
        description="Web server process writing an executable file then spawning a shell.",
        severity="critical",
        steps=[
            PatternStep(1, "process", {"parent_process_name": "w3wp.exe"}, ["T1505"], 5),
            PatternStep(2, "process", {"process_name": "cmd.exe"}, ["T1059"], 10),
        ],
        time_window_minutes=30,
        confidence_threshold=0.85
    )
]

class PatternDetector:
    def __init__(self, patterns: list[AttackPattern] = PATTERNS):
        self.patterns = patterns

    def detect_patterns(self, incident: Incident, alerts: list[dict[str, Any]]) -> list[PatternMatch]:
        if not alerts:
            return []

        # Sort alerts chronologically
        sorted_alerts = sorted(alerts, key=lambda a: self._parse_date(a.get("timestamp", datetime.utcnow().isoformat())))

        matches = []
        for pattern in self.patterns:
            match = self.match_pattern(pattern, sorted_alerts)
            if match and match.confidence >= pattern.confidence_threshold:
                matches.append(match)

        return matches

    def match_pattern(self, pattern: AttackPattern, alerts: list[dict[str, Any]]) -> PatternMatch | None:
        matched_alerts = []
        explanation_parts = []

        current_step_idx = 0
        last_match_time = None
        first_match_time = None

        total_steps = len(pattern.steps)
        feature_match_score = 0.0

        for alert in alerts:
            if current_step_idx >= total_steps:
                break

            step = pattern.steps[current_step_idx]
            alert_time = self._parse_date(alert.get("timestamp", datetime.utcnow().isoformat()))

            # Check Time bounds
            if first_match_time and (alert_time - first_match_time).total_seconds() > pattern.time_window_minutes * 60:
                break
            if last_match_time and (alert_time - last_match_time).total_seconds() > step.max_gap_minutes * 60:
                continue

            # Check Criteria
            if step.log_type and alert.get("log_type") != step.log_type:
                continue

            # Check MITRE
            mitre_ok = False
            if not step.required_mitre:
                mitre_ok = True
            else:
                alert_mitre = set([alert.get("mitre_tactic"), alert.get("mitre_technique")])
                if any(m in alert_mitre for m in step.required_mitre):
                    mitre_ok = True

            if not mitre_ok:
                continue

            # Check Features
            feature_ok = True
            for feat, required_val in step.required_features.items():
                alert_val = alert.get(feat)
                # Loose matching, e.g. string matching or boolean presence
                if isinstance(required_val, str) and isinstance(alert_val, str):
                    if required_val.lower() not in alert_val.lower():
                        feature_ok = False
                        break
                elif required_val == True and not alert_val or required_val != alert_val:
                    feature_ok = False
                    break

            if feature_ok:
                feature_match_score += 1.0

            matched_alerts.append(alert.get("id") or alert.get("_id", "unknown"))

            # Format explanation
            if not first_match_time:
                first_match_time = alert_time
                time_str = "T+0"
            else:
                delta_m = int((alert_time - first_match_time).total_seconds() / 60)
                time_str = f"T+{delta_m}m"

            desc_hints = []
            if step.required_mitre: desc_hints.append(f"MITRE: {','.join(step.required_mitre)}")
            explanation_parts.append(f"Step {step.step_id} at {time_str} ({'; '.join(desc_hints)})")

            last_match_time = alert_time
            current_step_idx += 1

        if current_step_idx == 0:
            return None

        confidence = (current_step_idx / total_steps) * (feature_match_score / current_step_idx if current_step_idx > 0 else 0)

        if confidence >= pattern.confidence_threshold:
            return PatternMatch(
                pattern_id=pattern.pattern_id,
                name=pattern.name,
                severity=pattern.severity,
                confidence=confidence,
                matched_alerts=matched_alerts,
                explanation=self.get_pattern_explanation(pattern, explanation_parts)
            )

        return None

    def get_pattern_explanation(self, pattern: AttackPattern, explanation_parts: list[str]) -> str:
        return f"{pattern.pattern_id} matched: " + ", ".join(explanation_parts)

    def _parse_date(self, date_str: str | datetime) -> datetime:
        if isinstance(date_str, datetime):
            return date_str
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.utcnow()
