import asyncio
import json
import time
from dataclasses import asdict

from langchain_core.tools import tool

from app.ingestion.kibana_client import KibanaProxyClient
from app.ingestion.log_fetcher import fetch_by_entity
from app.logging_config import get_logger
from app.scoring.threat_engine import get_threat_engine
from app.slm.cache import get_slm_cache
from app.slm.evaluator import get_slm_evaluator
from app.slm.prompt_templates import (
    alert_explanation_prompt,
    build_multi_turn_prompt,
    general_soc_question_prompt,
    incident_investigation_prompt,
    investigation_steps_prompt,
    remediation_prompt,
    triage_decision_prompt,
)
from app.slm.rag_pipeline import get_rag_pipeline
from app.slm.response_parser import parse_slm_response
from app.storage import local_db
from app.config import settings

logger = get_logger(__name__)

# --- LangChain Tools ---

@tool
async def get_recent_logs_for_entity(host_id: str, user_name: str, minutes: int = 60) -> str:
    """Fetches recent raw logs for a specific entity from Kibana."""
    try:
        kibana_client = KibanaProxyClient()
        logs = await fetch_by_entity(kibana_client, host_id, user_name, since_minutes=minutes)
        
        out = [f"Last {minutes}min logs for host={host_id} user={user_name}:"]
        for log_type, entries in logs.items():
            for e in entries[:20]:
                ts = e.get('@timestamp', e.get('timestamp', ''))
                out.append(f"[{log_type}] {ts} {json.dumps(e)}")
        
        if len(out) == 1:
            return "No recent logs found."
        return "\n".join(out)
    except Exception as e:
        return f"Error fetching logs: {e}"

@tool
async def get_alert_context(alert_id: str) -> str:
    """Fetches full context for a specific alert from local database."""
    try:
        alert = await local_db.get_alert(settings.DB_PATH, alert_id)
        if not alert:
            return f"Error: Alert {alert_id} not found."
        return json.dumps(alert, indent=2)
    except Exception as e:
        return f"Error fetching alert context: {e}"

@tool
async def get_entity_alert_history(entity_key: str, limit: int = 10) -> str:
    """Fetches historical alerts for an entity from local database."""
    try:
        alerts = await local_db.list_alerts(settings.DB_PATH, limit=100)
        
        entity_alerts = [a for a in alerts if a.get("entity_key") == entity_key]
        entity_alerts = entity_alerts[:limit]
        
        if not entity_alerts:
            return f"No historical alerts found for entity {entity_key}."
            
        out = []
        for a in entity_alerts:
            tactic = a.get("mitre_tactic", "")
            level = a.get("threat_level", "")
            date = a.get("created_at", "")
            out.append(f"- Date: {date}, Level: {level}, Tactic: {tactic}, ID: {a.get('alert_id')}")
            
        return f"Past alerts for {entity_key}:\n" + "\n".join(out)
    except Exception as e:
        return f"Error fetching alert history: {e}"

@tool
async def search_similar_alerts(description: str) -> str:
    """Invokes FAISS RAG Engine mapping top similar historical alerts visually matching anomalous descriptions."""
    try:
        rag = get_rag_pipeline()
        results = await rag.retrieve_similar(description, n_results=3)
        if not results:
            return "No similar RAG-mapped historical alerts detected."

        out = []
        for r in results:
            out.append(f"Alert Context: {r['document']}")
        return "\n".join(out)
    except Exception as e:
        return f"Error invoking vector boundaries: {e}"

@tool
def get_mitre_info(technique_id: str) -> str:
    """Returns explicit dictionary strings mapping MITRE ATT&CK technique details identically."""
    db = {
        "T1059": {"name": "Command and Scripting Interpreter", "tactic": "Execution", "desc": "Abuse of interpreters to execute commands.", "mit": "Restrict PowerShell execution policy."},
        "T1110": {"name": "Brute Force", "tactic": "Credential Access", "desc": "Guessing passwords to gain access.", "mit": "Account lockout policies."},
        "T1046": {"name": "Network Service Discovery", "tactic": "Discovery", "desc": "Scanning for open ports.", "mit": "Network segmentation."},
        "T1055": {"name": "Process Injection", "tactic": "Defense Evasion", "desc": "Injecting code into processes.", "mit": "Endpoint protection (EDR)."},
        "T1041": {"name": "Exfiltration Over C2 Channel", "tactic": "Exfiltration", "desc": "Stealing data over existing C2.", "mit": "Network intrusion detection."},
        "T1021": {"name": "Remote Services", "tactic": "Lateral Movement", "desc": "Moving laterally via SMB/RDP.", "mit": "Disable unnecessary services."},
        "T1053": {"name": "Scheduled Task/Job", "tactic": "Execution", "desc": "Persistence via cron/tasks.", "mit": "Monitor task creation."},
        "T1105": {"name": "Ingress Tool Transfer", "tactic": "Command and Control", "desc": "Downloading tools to compromised host.", "mit": "Proxy filtering."},
        "T1059.001": {"name": "PowerShell", "tactic": "Execution", "desc": "Execution via PowerShell.", "mit": "Enable Script Block Logging."}
    }

    tech = db.get(technique_id.upper())
    if not tech:
        return f"No documentation mapped natively for technique {technique_id}."

    return f"Technique {technique_id}: {tech['name']}. Tactic: {tech['tactic']}. Description: {tech['desc']}. Mitigation: {tech['mit']}."

# --- Manual ReAct Loop ---

async def run_react_loop(engine, tools, prompt_template: str, input_text: str, max_iterations: int = 5) -> str:
    tool_descs = "\n".join([f"{t.name}: {t.description}" for t in tools])
    tool_names = ", ".join([t.name for t in tools])

    current_prompt = prompt_template.format(
        tools=tool_descs,
        tool_names=tool_names,
        input=input_text,
        agent_scratchpad=""
    )

    for _ in range(max_iterations):
        res = engine.generate(
            prompt=current_prompt,
            system_prompt="You are an autonomous ReAct AI agent investigating anomalies. Think step by step securely.",
            max_new_tokens=512
        )

        current_prompt += res

        if "Final Answer:" in res:
            return res.split("Final Answer:")[-1].strip()

        if "Action:" in res and "Action Input:" in res:
            action_line = [line for line in res.split("\n") if line.strip().startswith("Action:")][-1]
            action_input_line = [line for line in res.split("\n") if line.strip().startswith("Action Input:")][-1]

            action_name = action_line.replace("Action:", "").strip()
            action_input = action_input_line.replace("Action Input:", "").strip()

            tool = next((t for t in tools if t.name == action_name), None)
            if tool:
                try:
                    observation = await tool.ainvoke({"__arg1": action_input}) if hasattr(tool, "ainvoke") else tool.invoke({"__arg1": action_input})
                except Exception as e:
                    observation = str(e)
            else:
                observation = f"Error: Tool '{action_name}' not found."

            current_prompt += f"\nObservation: {observation}\nThought:"
        else:
            return res.strip()

    return "Agent stopped after reaching max iterations."

# --- Primary Orchestrator ---

class SOCAgent:
    def __init__(self, slm_engine=None, rag_pipeline=None, kibana_client=None):
        self.slm_engine = slm_engine
        self.rag_pipeline = rag_pipeline
        self.kibana_client = kibana_client
        self.evaluator = get_slm_evaluator()
        self.cache = get_slm_cache()
        self.tools = [get_recent_logs_for_entity, get_alert_context, get_entity_alert_history, search_similar_alerts, get_mitre_info]
        self.prompt_template = (
            "Answer the following questions as best you can. You have access to the following tools:\n\n"
            "{tools}\n\n"
            "Use the following format explicitly:\n\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take, should be one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            "Begin!\n\n"
            "Question: {input}\n"
            "Thought:{agent_scratchpad}"
        )

    async def investigate(self, user_question: str, alert_id: str = None, incident_id: str = None, conversation_history: list[dict] = None) -> dict:
        start_time = time.time()
        alert = {}
        incident = {}
        rag_context = ""
        tokenizer = getattr(self.slm_engine, "tokenizer", None)

        te = get_threat_engine()

        if incident_id:
            try:
                # Currently we don't have local_db.get_incident, so this is skipped or we mock it.
                pass
            except Exception as e:
                logger.error("failed_to_fetch_incident_context", incident_id=incident_id, error=str(e))

        elif alert_id:
            alert = await te.get_alert(alert_id)
            if alert:
                desc = alert.get("human_explanation", "") or alert.get("top_rule", "")
                rag_results = await self.rag_pipeline.retrieve_similar(desc, n_results=3)
                rag_context = self.rag_pipeline.build_rag_context(rag_results, alert)

        q_lower = user_question.lower()
        q_type = "general"
        if alert:
            if any(k in q_lower for k in ["explain", "what is"]):
                input_text = alert_explanation_prompt(alert, rag_context, tokenizer)
                q_type = "explanation"
            elif any(k in q_lower for k in ["true positive", "real", "false"]):
                input_text = triage_decision_prompt(alert, "", tokenizer)
                q_type = "triage"
            elif any(k in q_lower for k in ["investigate", "steps", "how"]):
                input_text = investigation_steps_prompt(alert, "", tokenizer)
                q_type = "investigation"
            elif any(k in q_lower for k in ["remediat", "fix", "action"]):
                input_text = remediation_prompt(alert, False, tokenizer)
                q_type = "remediation"
            else:
                input_text = general_soc_question_prompt(user_question, rag_context, tokenizer)
        else:
            input_text = general_soc_question_prompt(user_question, "", tokenizer)

        if conversation_history:
            input_text = build_multi_turn_prompt(conversation_history, input_text, rag_context, tokenizer)

        input_tokens = 0
        if tokenizer:
            try:
                input_tokens = len(tokenizer.encode(input_text))
            except: pass

        t0 = time.time()
        cached_val = None
        cache_level = "miss"
        if not conversation_history:
            cached_val, cache_level = self.cache.get(user_question, alert_id)

        if cached_val:
            answer = cached_val
            logger.info("slm_cache_hit", cache_level=cache_level, alert_id=alert_id)
        else:
            try:
                answer = await run_react_loop(self.slm_engine, self.tools, self.prompt_template, input_text)
                if not conversation_history:
                    self.cache.set(user_question, answer, alert_id)
            except Exception as e:
                logger.error("agent_execution_failed", error=str(e))
                answer = f"I apologize, but I encountered an error during investigation: {str(e)}"

        t1 = time.time()
        resp_ms = (t1 - t0) * 1000.0

        output_tokens = 0
        if tokenizer:
            try:
                output_tokens = len(tokenizer.encode(answer))
            except: pass

        parsed_dict = None
        try:
            parsed = parse_slm_response(answer)
            parsed_dict = asdict(parsed) if parsed else None
        except Exception as e:
            logger.error("slm_response_parse_error", error=str(e))

        elapsed = time.time() - start_time
        try:
            from app.monitoring.metrics import slm_inference_duration, slm_queries_total
            slm_inference_duration.observe(elapsed)
            q_type_out = parsed_dict.get("question_type", "unknown") if parsed_dict else "unknown"
            slm_queries_total.labels(question_type=q_type_out).inc()
        except:
            pass

        return {
            "answer": answer,
            "sources": [],
            "tools_used": [t.name for t in self.tools],
            "parsed": parsed_dict,
            "from_cache": cache_level != "miss",
            "cache_level": cache_level
        }
