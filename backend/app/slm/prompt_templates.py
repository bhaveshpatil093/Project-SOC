import json


def count_tokens(text: str, tokenizer) -> int:
    """Accurately count tokens using the explicit model tokenizer."""
    if not tokenizer:
        # Fallback approximation (roughly 4 chars per token)
        return len(text) // 4
    return len(tokenizer.encode(text))

def truncate_to_tokens(text: str, max_tokens: int, tokenizer) -> str:
    """Truncate text explicitly preserving structural integrity under token boundaries."""
    if not tokenizer:
        # Fallback approximation
        return text[:max_tokens * 4]

    encoded = tokenizer.encode(text)
    if len(encoded) <= max_tokens:
        return text

    truncated_encoded = encoded[:max_tokens]
    return tokenizer.decode(truncated_encoded, skip_special_tokens=True)

def fits_in_context(prompt: str, max_tokens: int = 3000, tokenizer = None) -> bool:
    return count_tokens(prompt, tokenizer) <= max_tokens

def _enforce_constraints(prompt: str, question: str, max_tokens: int = 3000, tokenizer=None) -> str:
    instruction = "Answer in under 200 words unless more detail is needed."

    # We estimate instruction and question token length to dynamically truncate the payload
    base_overhead = count_tokens(instruction + "\n\n" + question, tokenizer)
    available_tokens = max_tokens - base_overhead - 50 # buffer

    if count_tokens(prompt, tokenizer) > available_tokens:
        prompt = truncate_to_tokens(prompt, available_tokens, tokenizer)

    return f"{prompt}\n\n{instruction}\n\nQuestion: {question}"

def alert_explanation_prompt(alert: dict, rag_context: str = "", tokenizer=None) -> str:
    sections = [
        "=== Alert Summary ===",
        f"Entity: {alert.get('entity_key')}",
        f"Threat Level: {alert.get('threat_level')} (Score: {alert.get('threat_score')})",
        f"Log Type: {alert.get('log_type')}",
        f"Rules Triggered: {', '.join(alert.get('triggered_rules', []))}",

        "\n=== SHAP Evidence ===",
        json.dumps(alert.get("shap_values", {}), indent=2),

        "\n=== MITRE Context ===",
        f"Tactics: {', '.join(alert.get('mitre_tactics', []))}",
        f"Techniques: {', '.join(alert.get('mitre_techniques', []))}",

        "\n=== Similar Past Incidents ===",
        rag_context or "No similar past incidents found."
    ]

    body = "\n".join(sections)
    question = "Explain this alert for a Level-1 SOC engineer."
    return _enforce_constraints(body, question, tokenizer=tokenizer)

def incident_investigation_prompt(incident: dict, alerts: list[dict], rag_context: str, pattern_matches: list[dict], tokenizer=None) -> str:
    # Build Attack Chain Summary
    alerts_sorted = sorted(alerts, key=lambda a: a.get("timestamp", ""))
    attack_chain_parts = []
    if alerts_sorted:
        first_time = None
        for a in alerts_sorted:
            try:
                import datetime
                ts = datetime.datetime.fromisoformat(a.get("timestamp", "").replace("Z", "+00:00"))
                if not first_time:
                    first_time = ts
                    delta_str = "T+0:00"
                else:
                    delta_m = int((ts - first_time).total_seconds() / 60)
                    delta_str = f"T+{delta_m}m"
                tech_str = f" ({', '.join(a.get('mitre_techniques', []))})" if a.get("mitre_techniques") else ""
                attack_chain_parts.append(f"{delta_str} - {a.get('log_type')} - {a.get('human_explanation', 'Anomaly detected')[:100]}{tech_str}")
            except Exception:
                pass

    chain_str = "\n".join(attack_chain_parts) if attack_chain_parts else "No alerts retrieved."

    # Build Matched Patterns Summary
    pattern_parts = []
    for p in pattern_matches:
        pattern_parts.append(f"{p.get('pattern_id', 'Unknown')}: {p.get('name', 'Unknown Pattern')} (confidence: {int(p.get('confidence', 0)*100)}%)")
    pattern_str = "\n".join(pattern_parts) if pattern_parts else "No known patterns matched."

    sections = [
        "=== [INCIDENT SUMMARY] ===",
        f"Incident ID: {incident.get('incident_id')} | Entity: {incident.get('entity_key')}",
        f"Attack Stage: {incident.get('attack_stage')} | Duration: {int(incident.get('duration_seconds', 0) / 60)} minutes",
        f"Threat Score: {incident.get('incident_threat_score')} ({incident.get('threat_level')})",

        "\n=== [ATTACK CHAIN] ===",
        chain_str,

        "\n=== [MATCHED ATTACK PATTERNS] ===",
        pattern_str,

        "\n=== [SIMILAR PAST INCIDENTS] ===",
        rag_context or "No similar past incidents found."
    ]

    body = "\n".join(sections)
    question = "Analyze this incident as a senior SOC analyst, evaluating the kill chain and prioritizing response actions."
    return _enforce_constraints(body, question, tokenizer=tokenizer)

def triage_decision_prompt(alert: dict, entity_history: str = "", tokenizer=None) -> str:
    sections = [
        "=== Alert Details ===",
        f"Entity: {alert.get('entity_key')}",
        f"Score: {alert.get('threat_score')} / Rules: {', '.join(alert.get('triggered_rules', []))}",

        "\n=== Behavioral Baseline (SHAP) ===",
        json.dumps(alert.get("shap_values", {}), indent=2),

        "\n=== Entity History ===",
        entity_history or "No significant history mapped for this entity."
    ]

    body = "\n".join(sections)
    question = "Is this a TRUE POSITIVE or a FALSE POSITIVE? Justify your decision strictly based on the provided evidence."
    return _enforce_constraints(body, question, tokenizer=tokenizer)

def investigation_steps_prompt(alert: dict, raw_logs_summary: str = "", tokenizer=None) -> str:
    sections = [
        "=== Alert Type ===",
        f"Category: {alert.get('log_type')} / {', '.join(alert.get('mitre_tactics', []))}",

        "\n=== Key Indicators ===",
        f"Top Rule: {alert.get('top_rule')}",
        json.dumps(alert.get("shap_values", {}), indent=2),

        "\n=== Raw Log Sample ===",
        raw_logs_summary or "No raw logs actively extracted for mapping context."
    ]

    body = "\n".join(sections)
    question = "List the step-by-step investigation actions required to analyze this alert in order."
    return _enforce_constraints(body, question, tokenizer=tokenizer)

def remediation_prompt(alert: dict, confirmed_threat: bool = False, tokenizer=None) -> str:
    sections = [
        "=== Threat Type ===",
        f"Log Type: {alert.get('log_type')} / Rules Fired: {alert.get('top_rule')}",
        f"Confirmed Threat: {confirmed_threat}",

        "\n=== Affected Entity ===",
        f"Target: {alert.get('entity_key')}",

        "\n=== MITRE Technique ===",
        f"Techniques: {', '.join(alert.get('mitre_techniques', []))}"
    ]

    body = "\n".join(sections)
    question = "Provide specific and actionable remediation steps to neutralize this threat."
    return _enforce_constraints(body, question, tokenizer=tokenizer)

def raw_log_analysis_prompt(logs: dict, entity_key: str, tokenizer=None) -> str:
    sections = [
        "=== Entity ===",
        entity_key,

        "\n=== Log Counts & Sample Entries ===",
        json.dumps(logs, indent=2)[:2000] # Hard structural trim before tokenizer
    ]

    body = "\n".join(sections)
    question = "Identify any suspicious patterns or anomalous artifacts in these logs."
    return _enforce_constraints(body, question, tokenizer=tokenizer)

def general_soc_question_prompt(question: str, context: str = "", tokenizer=None) -> str:
    body = ""
    if context:
        body = f"=== Context ===\n{context}"

    return _enforce_constraints(body, question, tokenizer=tokenizer)

def build_multi_turn_prompt(history: list[dict], new_question: str, context: str, tokenizer=None) -> str:
    if not history:
        return new_question

    parts = ["=== Previous Conversation ==="]

    # We trace backward truncating deeply trailing artifacts explicitly mapped
    # to protect 2500 context vectors implicitly bounding tokens natively.
    history_str = ""
    for turn in reversed(history):
        role_label = "User" if turn["role"] == "user" else "Assistant"
        turn_txt = f"{role_label}: {turn['content']}\n"

        if count_tokens(history_str + turn_txt, tokenizer) > 1500:
            break
        history_str = turn_txt + history_str

    parts.append(history_str.strip())
    parts.append("=== End of History ===")

    if context:
        parts.append("\n=== Context ===")
        parts.append(context)

    body = "\n".join(parts)
    return _enforce_constraints(body, f"Current question: {new_question}", tokenizer=tokenizer)
