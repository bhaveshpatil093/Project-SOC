import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd
from dateutil import parser


@dataclass
class NormalizedLog:
    doc_id: str
    log_type: str               # "network" | "process" | "security_alert"
    timestamp: datetime
    host_id: str
    host_hostname: str
    host_ip: str | None = None
    host_os_type: str | None = None
    user_name: str | None = None

    # Network fields (syslog)
    src_ip: str | None = None
    dst_ip: str | None = None
    protocol: str | None = None
    src_port: int | None = None
    dst_port: int | None = None
    network_interface: str | None = None

    # Process fields
    process_name: str | None = None
    process_executable: str | None = None
    process_command_line: str | None = None
    process_pid: int | None = None
    process_args: list[str] = field(default_factory=list)
    process_args_count: int = 0
    process_interactive: bool | None = None
    process_exit_code: int | None = None
    process_parent_name: str | None = None
    process_parent_executable: str | None = None
    process_parent_command_line: str | None = None
    event_action: str | None = None
    event_category: list[str] = field(default_factory=list)

    # Security alert fields
    winlog_event_id: int | None = None
    alert_severity: str | None = None
    alert_risk_score: float | None = None
    alert_rule_name: str | None = None
    alert_mitre_tactic: str | None = None
    alert_mitre_technique_id: str | None = None
    alert_status: str | None = None
    alert_workflow_status: str | None = None
    alert_reason: str | None = None

def _parse_timestamp(ts_str: Any) -> datetime:
    if not ts_str:
        return datetime.utcnow()
    try:
        if isinstance(ts_str, datetime):
            return ts_str
        return parser.parse(str(ts_str))
    except Exception:
        return datetime.utcnow()

def _extract_base_fields(raw: dict) -> dict:
    host_data = raw.get("host", {})
    user_data = raw.get("user", {})

    host_ip_raw = host_data.get("ip")
    host_ip = None
    if isinstance(host_ip_raw, list) and len(host_ip_raw) > 0:
        host_ip = str(host_ip_raw[0])
    elif host_ip_raw:
        host_ip = str(host_ip_raw)

    return {
        "doc_id": str(raw.get("_id", "")),
        "timestamp": _parse_timestamp(raw.get("@timestamp")),
        "host_id": str(host_data.get("id", "")),
        "host_hostname": str(host_data.get("hostname", host_data.get("name", ""))),
        "host_ip": host_ip,
        "host_os_type": host_data.get("os", {}).get("type") if isinstance(host_data.get("os"), dict) else None,
        "user_name": str(user_data.get("name")) if user_data.get("name") is not None else None
    }

def normalize_syslog(raw: dict) -> NormalizedLog:
    base = _extract_base_fields(raw)
    base["log_type"] = "network"

    message = str(raw.get("message", ""))

    # Parse syslog message field with exact regex patterns
    src_match = re.search(r"SRC=([^\s]+)", message)
    dst_match = re.search(r"DST=([^\s]+)", message)
    proto_match = re.search(r"PROTO=([^\s]+)", message)
    spt_match = re.search(r"SPT=([^\s]+)", message)
    dpt_match = re.search(r"DPT=([^\s]+)", message)
    in_match = re.search(r"IN=([^\s]+)", message)

    return NormalizedLog(
        **base,
        src_ip=src_match.group(1) if src_match else None,
        dst_ip=dst_match.group(1) if dst_match else None,
        protocol=proto_match.group(1) if proto_match else None,
        src_port=int(spt_match.group(1)) if spt_match and spt_match.group(1).isdigit() else None,
        dst_port=int(dpt_match.group(1)) if dpt_match and dpt_match.group(1).isdigit() else None,
        network_interface=in_match.group(1) if in_match else None,
    )

def normalize_process(raw: dict) -> NormalizedLog:
    base = _extract_base_fields(raw)
    base["log_type"] = "process"

    process_data = raw.get("process", {})
    parent_data = process_data.get("parent", {})
    event_data = raw.get("event", {})

    process_args = process_data.get("args", [])
    if not isinstance(process_args, list):
        process_args = [str(process_args)] if process_args else []

    event_category = event_data.get("category", [])
    if not isinstance(event_category, list):
        event_category = [str(event_category)] if event_category else []

    cmd_line = process_data.get("command_line")
    if cmd_line and len(cmd_line) > 32766:
        cmd_line = cmd_line[:32766]
        
    return NormalizedLog(
        **base,
        process_name=process_data.get("name"),
        process_executable=process_data.get("executable"),
        process_command_line=cmd_line,
        process_pid=process_data.get("pid"),
        process_args=[str(x) for x in process_args],
        process_args_count=process_data.get("args_count", len(process_args)),
        process_interactive=process_data.get("interactive"),
        process_exit_code=process_data.get("exit_code"),
        process_parent_name=parent_data.get("name"),
        process_parent_executable=parent_data.get("executable"),
        process_parent_command_line=parent_data.get("command_line"),
        event_action=event_data.get("action"),
        event_category=[str(x) for x in event_category]
    )

def normalize_security_alert(raw: dict) -> NormalizedLog:
    base = _extract_base_fields(raw)
    base["log_type"] = "security_alert"

    winlog_data = raw.get("winlog", {})
    kibana_data = raw.get("kibana", {})
    alert_data = kibana_data.get("alert", {})
    rule_data = alert_data.get("rule", {})

    # Extract threat context (tactic and technique)
    threats = rule_data.get("threat", [])
    alert_mitre_tactic = None
    alert_mitre_technique_id = None

    if isinstance(threats, list) and len(threats) > 0:
        first_threat = threats[0]
        if isinstance(first_threat, dict):
            tactic = first_threat.get("tactic", {})
            if isinstance(tactic, dict):
                alert_mitre_tactic = tactic.get("name")

            techniques = first_threat.get("technique", [])
            if isinstance(techniques, list) and len(techniques) > 0:
                first_tech = techniques[0]
                if isinstance(first_tech, dict):
                    alert_mitre_technique_id = first_tech.get("id")

    # Safe float parsing
    risk_score_raw = alert_data.get("risk_score")
    risk_score = None
    if risk_score_raw is not None:
        try:
            risk_score = float(risk_score_raw)
        except ValueError:
            pass

    # Safe int parsing
    winlog_event_id_raw = winlog_data.get("event_id")
    winlog_event_id = None
    if winlog_event_id_raw is not None:
        try:
            winlog_event_id = int(winlog_event_id_raw)
        except ValueError:
            pass

    return NormalizedLog(
        **base,
        winlog_event_id=winlog_event_id,
        alert_severity=alert_data.get("severity"),
        alert_risk_score=risk_score,
        alert_rule_name=rule_data.get("name"),
        alert_mitre_tactic=alert_mitre_tactic,
        alert_mitre_technique_id=alert_mitre_technique_id,
        alert_status=alert_data.get("status"),
        alert_workflow_status=alert_data.get("workflow_status"),
        alert_reason=alert_data.get("reason")
    )

def normalize_batch(raw_docs: list[dict], log_type: str) -> list[NormalizedLog]:
    if not raw_docs:
        return []

    if log_type == "network":
        # Vectorized parsing for network logs (syslog regex)
        # Using list comprehension for simple dict lookups (faster than json_normalize on highly nested dicts)
        base_dicts = [_extract_base_fields(doc) for doc in raw_docs]
        base_df = pd.DataFrame(base_dicts)
        base_df["log_type"] = "network"

        # Extract messages
        messages = pd.Series([str(doc.get("message", "")) for doc in raw_docs])

        # Pure pandas vectorized regex extraction (No python loops)
        extracted = pd.DataFrame({
            "src_ip": messages.str.extract(r"SRC=([^\s]+)", expand=False),
            "dst_ip": messages.str.extract(r"DST=([^\s]+)", expand=False),
            "protocol": messages.str.extract(r"PROTO=([^\s]+)", expand=False),
            "src_port": pd.to_numeric(messages.str.extract(r"SPT=([^\s]+)", expand=False), errors="coerce").astype("Int64"),
            "dst_port": pd.to_numeric(messages.str.extract(r"DPT=([^\s]+)", expand=False), errors="coerce").astype("Int64"),
            "network_interface": messages.str.extract(r"IN=([^\s]+)", expand=False)
        })

        # Combine base fields and extracted regex fields
        combined = pd.concat([base_df, extracted], axis=1)

        # Convert back to dataclass objects (cleaning pd.NaT / pd.NA)
        records = combined.to_dict('records')

        normalized = []
        for rec in records:
            cleaned = {k: (None if pd.isna(v) else v) for k, v in rec.items()}
            normalized.append(NormalizedLog(**cleaned))

        return normalized
    # Process and Security Alerts: list comprehension is extremely fast for direct dict mapping
    normalized = []
    for doc in raw_docs:
        try:
            if log_type == "process":
                normalized.append(normalize_process(doc))
            elif log_type == "security_alert":
                normalized.append(normalize_security_alert(doc))
        except Exception:
            pass
    return normalized

def to_dataframe(logs: list[NormalizedLog]) -> pd.DataFrame:
    data = [asdict(log) for log in logs]
    return pd.DataFrame(data)
