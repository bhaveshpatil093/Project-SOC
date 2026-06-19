import asyncio
import time
import os
import sys
from datetime import datetime
from collections import defaultdict

# Add backend dir to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.slm.model_loader import _slm_engine
from app.slm.evaluator import get_slm_evaluator, ResponseMetrics
from app.slm.agent import SOCAgent
from app.slm.response_parser import parse_slm_response, asdict

MOCK_ALERTS = {
    "port_scan": {
        "id": "A-1001",
        "entity_key": "10.1.2.3|system",
        "threat_level": "medium",
        "threat_score": 0.65,
        "mitre_tactics": ["Discovery"],
        "top_rule": "Nmap Scan Detected",
        "human_explanation": "A port scan was detected from internal IP 10.1.2.3 targeting multiple hosts."
    },
    "encoded_payload": {
        "id": "A-1002",
        "entity_key": "WIN-SRV-01|admin",
        "threat_level": "high",
        "threat_score": 0.88,
        "mitre_tactics": ["Execution"],
        "top_rule": "Suspicious PowerShell Encoded Command",
        "human_explanation": "PowerShell process spawned with base64 encoded payload."
    },
    "lolbin": {
        "id": "A-1003",
        "entity_key": "USER-LAPTOP-05|jdoe",
        "threat_level": "low",
        "threat_score": 0.35,
        "mitre_tactics": ["Defense Evasion"],
        "top_rule": "Certutil Network Connection",
        "human_explanation": "Certutil.exe was used to download a file from an external IP."
    },
    "lateral_movement": {
        "id": "A-1004",
        "entity_key": "10.1.5.50|svc_account",
        "threat_level": "critical",
        "threat_score": 0.95,
        "mitre_tactics": ["Lateral Movement"],
        "top_rule": "WMI Remote Execution",
        "human_explanation": "WMI was used to remotely execute a script on a domain controller."
    },
    "brute_force": {
        "id": "A-1005",
        "entity_key": "VPN-GW-01|unknown",
        "threat_level": "high",
        "threat_score": 0.82,
        "mitre_tactics": ["Credential Access"],
        "top_rule": "Multiple Failed Logins",
        "human_explanation": "Over 50 failed login attempts detected within 2 minutes for user 'admin'."
    }
}

TEST_CASES = [
    # Explanation
    {"question": "Explain this alert", "alert_type": "port_scan", "expected_keywords": ["port", "scan", "discovery"], "expected_has": ["summary", "evidence"]},
    {"question": "What is happening here?", "alert_type": "port_scan", "expected_keywords": ["10.1.2.3"], "expected_has": ["summary"]},
    {"question": "Break down this alert for me", "alert_type": "encoded_payload", "expected_keywords": ["powershell", "encoded"], "expected_has": ["summary", "evidence"]},
    {"question": "Can you summarize this incident?", "alert_type": "encoded_payload", "expected_keywords": ["execution"], "expected_has": ["summary"]},
    {"question": "Explain the alert on WIN-SRV-01", "alert_type": "encoded_payload", "expected_keywords": ["win-srv-01"], "expected_has": ["summary"]},
    {"question": "What does this Lolbin alert mean?", "alert_type": "lolbin", "expected_keywords": ["certutil", "download"], "expected_has": ["summary"]},
    {"question": "Explain the lateral movement", "alert_type": "lateral_movement", "expected_keywords": ["wmi", "domain controller"], "expected_has": ["summary", "evidence"]},
    {"question": "What is the threat here?", "alert_type": "lateral_movement", "expected_keywords": ["wmi", "remote"], "expected_has": ["summary"]},
    {"question": "Why did brute force trigger?", "alert_type": "brute_force", "expected_keywords": ["failed", "login", "admin"], "expected_has": ["summary", "evidence"]},
    {"question": "Summarize the credential access attempt", "alert_type": "brute_force", "expected_keywords": ["credential access", "attempts"], "expected_has": ["summary"]},

    # Triage
    {"question": "Is this a real threat or a false positive?", "alert_type": "lolbin", "expected_has": ["verdict"]},
    {"question": "Should I escalate this?", "alert_type": "port_scan", "expected_has": ["verdict"]},
    {"question": "Is this powershell command malicious?", "alert_type": "encoded_payload", "expected_has": ["verdict"]},
    {"question": "Could this certutil execution be benign?", "alert_type": "lolbin", "expected_has": ["verdict"]},
    {"question": "Is this a true positive?", "alert_type": "lateral_movement", "expected_has": ["verdict"]},
    {"question": "Rate the severity and verdict", "alert_type": "brute_force", "expected_has": ["verdict"]},
    {"question": "Is the WMI remote execution normal?", "alert_type": "lateral_movement", "expected_has": ["verdict"]},
    {"question": "False positive check on failed logins", "alert_type": "brute_force", "expected_has": ["verdict"]},

    # Investigation
    {"question": "What should I investigate first?", "alert_type": "lateral_movement", "expected_has": ["action_items"], "min_actions": 3},
    {"question": "How do I hunt for more evidence?", "alert_type": "encoded_payload", "expected_has": ["action_items"], "min_actions": 2},
    {"question": "List 3 steps to investigate this.", "alert_type": "lolbin", "expected_has": ["action_items"], "min_actions": 3},
    {"question": "What logs should I check?", "alert_type": "brute_force", "expected_has": ["action_items"], "min_actions": 2},
    {"question": "Provide a runbook for investigating this", "alert_type": "port_scan", "expected_has": ["action_items"], "min_actions": 3},
    {"question": "Next steps for SOC engineer", "alert_type": "lateral_movement", "expected_has": ["action_items"], "min_actions": 2},

    # Remediation
    {"question": "What actions should I take to fix this?", "alert_type": "brute_force", "expected_has": ["action_items"], "min_actions": 3},
    {"question": "How do I remediate the encoded payload?", "alert_type": "encoded_payload", "expected_has": ["action_items"], "min_actions": 2},
    {"question": "Give me a mitigation strategy", "alert_type": "lateral_movement", "expected_has": ["action_items"], "min_actions": 3},
    {"question": "How do I block this port scan?", "alert_type": "port_scan", "expected_has": ["action_items"], "min_actions": 2},
    {"question": "Containment steps for the domain controller", "alert_type": "lateral_movement", "expected_has": ["action_items"], "min_actions": 3},
    {"question": "How to resolve the brute force alert?", "alert_type": "brute_force", "expected_has": ["action_items"], "min_actions": 2},
]

async def run_tests():
    print("Initializing SLM Engine...")
    await _slm_engine.load("finetuned") # Enforce fine-tuned if available, else base
    
    agent = SOCAgent(slm_engine=_slm_engine, rag_pipeline=None, es=None)
    evaluator = get_slm_evaluator()
    
    results = []
    
    total_time = 0.0
    total_words = 0
    total_tps = 0.0
    total_score = 0.0
    
    fails = []
    
    print(f"\nRunning {len(TEST_CASES)} tests...")
    
    for i, tc in enumerate(TEST_CASES):
        sys.stdout.write(f"\rTesting [{i+1}/{len(TEST_CASES)}]... ")
        sys.stdout.flush()
        
        q = tc["question"]
        atype = tc.get("alert_type")
        alert = MOCK_ALERTS.get(atype, {})
        
        t0 = time.time()
        res = await agent.investigate(q, alert_id=alert.get("id"))
        t1 = time.time()
        
        ms = (t1 - t0) * 1000.0
        total_time += ms
        
        ans = res.get("answer", "")
        parsed = res.get("parsed") or {}
        
        words = len(ans.split())
        total_words += words
        
        tokens = len(_slm_engine.tokenizer.encode(ans))
        tps = tokens / (ms / 1000.0) if ms > 0 else 0
        total_tps += tps
        
        metrics = evaluator.evaluate_response(
            question=q, response=ans, alert=alert, parsed=parsed,
            response_time_ms=ms, input_tokens=10, output_tokens=tokens
        )
        score = evaluator.compute_quality_score(metrics)
        total_score += score
        
        # Validation
        passed = True
        reasons = []
        
        req_keys = tc.get("expected_keywords", [])
        for rk in req_keys:
            if rk.lower() not in ans.lower():
                passed = False
                reasons.append(f"missing expected keyword '{rk}'")
                
        req_has = tc.get("expected_has", [])
        if "summary" in req_has and not metrics.has_summary:
            passed = False; reasons.append("missing summary")
        if "evidence" in req_has and not metrics.has_evidence:
            passed = False; reasons.append("missing evidence")
        if "action_items" in req_has and not metrics.has_action_items:
            passed = False; reasons.append("missing action items")
        if "verdict" in req_has and not metrics.verdict_confidence:
            passed = False; reasons.append("missing verdict")
            
        min_act = tc.get("min_actions", 0)
        if metrics.action_item_count < min_act:
            passed = False; reasons.append(f"action_items count {metrics.action_item_count} < required {min_act}")
            
        if not passed:
            fails.append((i+1, reasons))
            
        results.append(passed)

    print("\n\nISRO SOC SLM Quality Report")
    print("============================")
    info = _slm_engine.get_model_info()
    print(f"Model: {info.get('model_name')} ({'fine-tuned' if info.get('is_finetuned') else 'base'})")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total test cases: {len(TEST_CASES)}\n")
    
    passed_cnt = sum(1 for r in results if r)
    failed_cnt = len(TEST_CASES) - passed_cnt
    
    print("Results:")
    print(f"  Passed:  {passed_cnt}/{len(TEST_CASES)}  ({(passed_cnt/len(TEST_CASES)*100):.1f}%)")
    print(f"  Failed:   {failed_cnt}/{len(TEST_CASES)}  ({(failed_cnt/len(TEST_CASES)*100):.1f}%)\n")
    
    print("Performance:")
    print(f"  Avg response time:  {int(total_time/len(TEST_CASES))} ms")
    print(f"  Avg quality score:  {(total_score/len(TEST_CASES)):.2f} / 1.00")
    print(f"  Avg word count:     {int(total_words/len(TEST_CASES))} words")
    print(f"  Tokens/sec:         {(total_tps/len(TEST_CASES)):.1f}\n")
    
    if fails:
        print("Failed cases:")
        for idx, reasons in fails:
            print(f"  [FAIL] Test {idx}: {', '.join(reasons)}")
            
    print("\nRecommendation: ", end="")
    if failed_cnt > 5:
        print("Re-run fine-tuning with more targeted samples.")
    else:
        print("Model is performing optimally for production deployment.")
        
if __name__ == "__main__":
    asyncio.run(run_tests())
