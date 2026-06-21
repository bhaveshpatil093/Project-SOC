import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from app.slm.engine import SLMEngine

logger = logging.getLogger(__name__)

INDEX_NAME = "soc-reports"

@dataclass
class IncidentReport:
    incident_id: str
    generated_at: str
    generated_by: str   # "SOC AI Platform v1.0.0"
    executive_summary: str
    technical_analysis: str
    attack_timeline: list[dict[str, Any]]
    affected_assets: list[str]
    mitre_coverage: dict[str, Any]
    recommended_actions: list[str]
    indicators_of_compromise: dict[str, list[str]]
    severity_justification: str
    analyst_notes: str

def extract_iocs(incident: dict, alerts: list[dict]) -> dict:
    ips = set()
    processes = set()
    techniques = set()

    for alert in alerts:
        # IPs
        if "src_ip" in alert and alert["src_ip"]:
            ips.add(alert["src_ip"])
        if "dst_ip" in alert and alert["dst_ip"]:
            ips.add(alert["dst_ip"])

        # Processes
        if "process_name" in alert and alert["process_name"]:
            processes.add(alert["process_name"])

        # Techniques
        if "mitre_technique_ids" in alert and alert["mitre_technique_ids"]:
            for t in alert["mitre_technique_ids"]:
                techniques.add(t)

    return {
        "ips": list(ips),
        "processes": list(processes),
        "techniques": list(techniques)
    }

async def draft_executive_summary(slm_engine: SLMEngine, incident: dict) -> str:
    prompt = f"""
Write a 3-sentence executive summary of this security incident for a non-technical audience.
Include: what happened, what systems were affected, and the recommended next step.
Max 100 words.

Incident Title: {incident.get('title')}
Severity: {incident.get('severity')}
Status: {incident.get('status')}
Entities: {', '.join(incident.get('entities', []))}
"""
    try:
        summary = await slm_engine.generate(prompt, max_tokens=150)
        return summary.strip()
    except Exception as e:
        logger.error(f"Failed to generate executive summary: {e}")
        return "Executive summary generation failed."

async def draft_technical_analysis(slm_engine: SLMEngine, incident: dict, alerts: list[dict]) -> str:
    # Prepare a condensed summary of alerts
    alert_summary = "\\n".join([f"- {a.get('log_type', 'Unknown')} at {a.get('timestamp')}: Threat Score {a.get('threat_score', 0):.2f}" for a in alerts[:5]])

    prompt = f"""
Write a technical analysis of this incident covering:
attack vector, techniques used, lateral movement path, and data potentially at risk.
Max 300 words.

Incident Entities: {', '.join(incident.get('entities', []))}
Top Alerts:
{alert_summary}
"""
    try:
        analysis = await slm_engine.generate(prompt, max_tokens=400)
        return analysis.strip()
    except Exception as e:
        logger.error(f"Failed to generate technical analysis: {e}")
        return "Technical analysis generation failed."

async def generate_incident_report(es, slm_engine: SLMEngine, incident_id: str, incident: dict, alerts: list[dict]) -> IncidentReport:
    logger.info(f"Generating incident report for {incident_id}")

    exec_summary = await draft_executive_summary(slm_engine, incident)
    tech_analysis = await draft_technical_analysis(slm_engine, incident, alerts)
    iocs = extract_iocs(incident, alerts)

    # Simple extraction for other fields
    timeline = [{"timestamp": a.get("timestamp"), "event": a.get("log_type"), "threat_level": a.get("threat_level")} for a in alerts[:10]]
    assets = list(set([a.get("host_id") for a in alerts if a.get("host_id")]))

    # Prompt for recommendations and severity justification
    rec_prompt = "Based on this incident, list 3 numbered recommended actions for the SOC team to remediate the threat."
    try:
        recs_text = await slm_engine.generate(rec_prompt, max_tokens=150)
        recs = [r.strip() for r in recs_text.split("\\n") if r.strip() and r.strip()[0].isdigit()]
        if not recs:
            recs = ["Isolate affected hosts immediately.", "Rotate compromised credentials.", "Review firewall rules for anomalous IP traffic."]
    except:
        recs = ["Isolate affected hosts immediately.", "Rotate compromised credentials.", "Review firewall rules for anomalous IP traffic."]

    sev_prompt = f"In one short paragraph, justify why this incident was classified as {incident.get('severity')}."
    try:
        sev_justification = await slm_engine.generate(sev_prompt, max_tokens=100)
    except:
        sev_justification = "Severity assigned based on aggregate threat scores of constituent alerts."

    report = IncidentReport(
        incident_id=incident_id,
        generated_at=datetime.utcnow().isoformat() + "Z",
        generated_by="SOC AI Platform v1.0.0",
        executive_summary=exec_summary,
        technical_analysis=tech_analysis,
        attack_timeline=timeline,
        affected_assets=assets,
        mitre_coverage={"tactics": incident.get("mitre_tactics", []), "techniques": iocs["techniques"]},
        recommended_actions=recs,
        indicators_of_compromise=iocs,
        severity_justification=sev_justification.strip(),
        analyst_notes=""
    )

    # Save to ES
    try:
        await es.index(index=INDEX_NAME, id=incident_id, document=asdict(report))
        logger.info(f"Saved incident report for {incident_id}")
    except Exception as e:
        logger.error(f"Failed to save incident report: {e}")

    return report

async def get_incident_report(es, incident_id: str) -> dict:
    try:
        res = await es.get(index=INDEX_NAME, id=incident_id)
        return res["_source"]
    except Exception:
        return None
