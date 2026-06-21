from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

@dataclass
class PlaybookStep:
    step_id: int
    title: str
    instruction: str
    soc_question: Optional[str] = None
    suggested_slm_query: Optional[str] = None

@dataclass
class Playbook:
    id: str
    name: str
    trigger_rules: List[str]
    trigger_tactics: List[str]
    steps: List[PlaybookStep]
    escalation_criteria: str

PLAYBOOKS = {
    "port_scan": Playbook(
        id="PB-001",
        name="Port Scan Investigation",
        trigger_rules=["RULE-002", "NETWORK-SCAN"],
        trigger_tactics=["Reconnaissance", "Discovery"],
        steps=[
            PlaybookStep(
                step_id=1,
                title="Verify the scan",
                instruction="Check if the source IP is a known internal scanner (vulnerability scanner, monitoring tool).",
                soc_question="Is IP {src_ip} a known scanning tool? Check the asset register.",
                suggested_slm_query="Is {src_ip} a known asset in our network? Show me its history.",
            ),
            PlaybookStep(
                step_id=2,
                title="Assess scope",
                instruction="Determine how many hosts were scanned and if any responded.",
                suggested_slm_query="How many unique destination IPs did {entity_key} contact in the last hour?",
            ),
            PlaybookStep(
                step_id=3,
                title="Check for follow-up activity",
                instruction="Port scans are often followed by exploitation attempts.",
                suggested_slm_query="Show me any process events or alerts for {entity_key} in the last 30 minutes.",
            ),
            PlaybookStep(
                step_id=4, 
                title="Make triage decision",
                instruction="Based on steps 1–3, determine if this is TP, FP, or needs escalation.",
                suggested_slm_query="Based on the evidence, is this port scan a true threat or a false positive?",
            ),
        ],
        escalation_criteria="Escalate to L2 if: scan > 1000 ports, OR source IP is external, OR follow-up exploitation detected",
    ),
    "encoded_powershell": Playbook(
        id="PB-002",
        name="Encoded PowerShell Activity",
        trigger_rules=["PROC-001", "PS-ENCODED"],
        trigger_tactics=["Execution", "Defense Evasion"],
        steps=[
            PlaybookStep(
                step_id=1,
                title="Decode Payload",
                instruction="Extract the base64 payload and decode it.",
                suggested_slm_query="Extract and decode the PowerShell command line payload triggered by {entity_key}.",
            ),
            PlaybookStep(
                step_id=2,
                title="Analyze Intent",
                instruction="Review the decoded command for malicious intent (e.g., downloading payloads, executing shellcode).",
                suggested_slm_query="Analyze the decoded PowerShell script. What does it do? Does it reach out to external domains?",
            ),
            PlaybookStep(
                step_id=3,
                title="Check Process Tree",
                instruction="Check the parent process that spawned this PowerShell instance.",
                suggested_slm_query="What process spawned the PowerShell activity for {entity_key}? Is it typical like Explorer.exe, or suspicious like WINWORD.exe?",
            )
        ],
        escalation_criteria="Escalate to L2 if: payload downloads unknown executables OR connects to unknown C2 IPs.",
    ),
    "brute_force": Playbook(
        id="PB-003",
        name="Brute Force Authentication",
        trigger_rules=["AUTH-005", "AUTH-FAIL-BURST"],
        trigger_tactics=["Credential Access"],
        steps=[
            PlaybookStep(
                step_id=1,
                title="Verify Source",
                instruction="Identify if the auth failures are from a single IP or distributed.",
                suggested_slm_query="Show me the distinct source IPs generating authentication failures against {entity_key}.",
            ),
            PlaybookStep(
                step_id=2,
                title="Check for Success",
                instruction="A brute force is only critical if it eventually succeeds.",
                suggested_slm_query="Did {entity_key} have any successful authentication events immediately following the failures?",
            )
        ],
        escalation_criteria="Escalate to Incident Response immediately if a successful login occurred after the failure burst.",
    ),
    "lateral_movement": Playbook(
        id="PB-004",
        name="Lateral Movement via WMI/SMB",
        trigger_rules=["LAT-001", "SMB-EXEC"],
        trigger_tactics=["Lateral Movement"],
        steps=[
            PlaybookStep(
                step_id=1,
                title="Identify the Source",
                instruction="Determine which host initiated the connection.",
                suggested_slm_query="Which host initiated the lateral movement activity targeting {entity_key}?",
            ),
            PlaybookStep(
                step_id=2,
                title="Check Executed Commands",
                instruction="Determine what was executed over SMB/WMI.",
                suggested_slm_query="What processes or commands were executed on {entity_key} remotely?",
            )
        ],
        escalation_criteria="Escalate to L2 immediately. Lateral movement often indicates active adversary presence.",
    ),
    "data_exfiltration": Playbook(
        id="PB-005",
        name="Data Exfiltration",
        trigger_rules=["NET-EXFIL", "HIGH-BYTES-OUT"],
        trigger_tactics=["Exfiltration"],
        steps=[
            PlaybookStep(
                step_id=1,
                title="Analyze Outbound Traffic",
                instruction="Determine the total volume and destination of the outbound traffic.",
                suggested_slm_query="How many bytes were transferred from {entity_key}, and to what external IP?",
            ),
            PlaybookStep(
                step_id=2,
                title="Check Destination Reputation",
                instruction="Determine if the destination is a known cloud provider (e.g. AWS, Mega) or suspicious.",
                suggested_slm_query="Is the destination IP associated with a known file sharing service or a malicious C2?",
            )
        ],
        escalation_criteria="Escalate to L3 if large volumes of data left the network to an untrusted external entity.",
    )
}

def substitute_context(text: str, alert: dict) -> str:
    if not text:
        return text
    
    src_ip = alert.get("src_ip", "UNKNOWN_IP")
    entity_key = alert.get("entity_key", "UNKNOWN_ENTITY")
    
    # Safe substitution
    res = text.replace("{src_ip}", src_ip)
    res = res.replace("{entity_key}", entity_key)
    return res

def get_playbook_for_alert(alert: dict) -> Optional[dict]:
    # Match logic
    triggered_rules = set()
    if alert.get("triggered_rules"):
        for r in alert.get("triggered_rules", []):
            if isinstance(r, dict) and r.get("id"):
                triggered_rules.add(r["id"])
            elif isinstance(r, str):
                triggered_rules.add(r)
                
    mitre_tactics = set(alert.get("mitre_tactics", []))
    
    matched_pb = None
    
    # Simple evaluation: If any rule matches or any tactic matches
    for pb_key, pb in PLAYBOOKS.items():
        if any(tr in pb.trigger_rules for tr in triggered_rules) or \
           any(mt in pb.trigger_tactics for mt in mitre_tactics):
            matched_pb = pb
            break
            
    if not matched_pb:
        # Fallback to port scan for purely anomalous network spikes if no rule triggers but its purely network
        if "network" in alert.get("top_features", [{}])[0] if alert.get("top_features") else []:
             matched_pb = PLAYBOOKS["port_scan"]
             
    if not matched_pb:
        return None
        
    # Serialize and substitute context into the steps
    pb_dict = asdict(matched_pb)
    
    for step in pb_dict["steps"]:
        if step.get("instruction"):
            step["instruction"] = substitute_context(step["instruction"], alert)
        if step.get("soc_question"):
            step["soc_question"] = substitute_context(step["soc_question"], alert)
        if step.get("suggested_slm_query"):
            step["suggested_slm_query"] = substitute_context(step["suggested_slm_query"], alert)
            
    return pb_dict
