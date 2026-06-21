import asyncio
import json
import time

from langchain_core.tools import tool

from app.ingestion.es_client import get_es_client
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

logger = get_logger(__name__)

# --- LangChain Tools ---

@tool
async def get_alert_details(alert_id: str) -> str:
    """Fetches full alert payload natively from Elasticsearch and returns structured JSON strings."""
    try:
        te = get_threat_engine()
        alert = await te.get_alert(alert_id)
        if not alert:
            return f"Error: Alert {alert_id} not found."
        return json.dumps(alert, indent=2)
    except Exception as e:
        return f"Error fetching alert bounds: {e}"

@tool
async def get_entity_history(entity_key: str, hours: int = 24) -> str:
    """Fetches all chronological alerts mapped to an entity_key over the past N hours. Returns counts and severities."""
    try:
        es = await get_es_client()
        from app.ingestion.es_client import INDEX_NAMES
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"entity_key.keyword": entity_key}},
                        {"range": {"timestamp": {"gte": f"now-{hours}h"}}}
                    ]
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 100
        }
        resp = await es.search(index=INDEX_NAMES["alerts_processed"], body=query, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])

        if not hits:
            return f"No alerts found tracking entity {entity_key} inside {hours}h."

        max_score = max([h["_source"].get("threat_score", 0) for h in hits])
        incidents = [f"[{h['_source'].get('timestamp')}] {h['_source'].get('top_rule')} (Score: {h['_source'].get('threat_score')})" for h in hits]

        return f"Count: {len(hits)}\nMax Threat Score: {max_score}\nIncidents:\n" + "\n".join(incidents)
    except Exception as e:
        return f"Error fetching temporal history: {e}"

@tool
async def search_similar_alerts(description: str) -> str:
    """Invokes ChromaDB RAG Engine mapping top 3 similar historical alerts visually matching anomalous descriptions."""
    try:
        rag = get_rag_pipeline()
        results = await rag.retrieve_similar(description, n_results=3)
        if not results:
            return "No similar RAG-mapped historical alerts detected."

        out = []
        for r in results:
            out.append(f"Alert ID: {r['metadata']['alert_id']} - {r['document']}")
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

@tool
async def get_raw_logs(entity_key: str, minutes: int = 30) -> str:
    """Executes log_fetcher extracting raw document logs explicitly across hosts bounding time vectors."""
    try:
        parts = entity_key.split("|")
        host_id = parts[0]
        user_name = parts[1] if len(parts) > 1 else ""

        es = await get_es_client()
        logs = await fetch_by_entity(es, host_id, user_name, since_minutes=minutes)

        out = []
        for log_type, entries in logs.items():
            if entries:
                out.append(f"Type: {log_type} (Count: {len(entries)})")
                for e in entries[:5]:
                    out.append(f"  - {json.dumps(e)}")

        if not out:
            return "No raw raw log streams matched entity bounds."
        return "\n".join(out)
    except Exception as e:
        return f"Error executing log extraction: {e}"

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
            # If no action is formatted correctly, force a stop
            return res.strip()

    return "Agent stopped after reaching max iterations."

# --- Primary Orchestrator ---

class SOCAgent:
    def __init__(self, slm_engine=None, rag_pipeline=None, es=None):
        self.slm_engine = slm_engine
        self.rag_pipeline = rag_pipeline
        self.es = es
        self.evaluator = get_slm_evaluator()
        self.cache = get_slm_cache()
        self.tools = [get_alert_details, get_entity_history, search_similar_alerts, get_mitre_info, get_raw_logs]
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
        alert = {}
        incident = {}
        rag_context = ""
        tokenizer = getattr(self.slm_engine, "tokenizer", None)

        te = get_threat_engine()

        if incident_id:
            # We fetch the incident from ES directly
            try:
                # get_incident_detail is not async directly, wait it is in routes but it uses async ES
                # we'll fetch from ES locally here
                es = await get_es_client()
                from app.ingestion.es_client import INDEX_NAMES
                resp = await es.get(index=INDEX_NAMES["incidents"], id=incident_id)
                incident = resp.get("_source", {})

                # Fetch alerts
                alert_ids = incident.get("alert_ids", [])
                alerts_query = {"query": {"terms": {"_id": alert_ids}}, "size": 100}
                al_resp = await es.search(index=INDEX_NAMES["alerts_processed"], body=alerts_query, ignore_unavailable=True)
                inc_alerts = [h["_source"] for h in al_resp.get("hits", {}).get("hits", [])]

                # RAG
                desc = " ".join(incident.get("mitre_tactics", [])) + " " + " ".join(incident.get("log_types_involved", []))
                rag_results = await self.rag_pipeline.retrieve_similar(desc, n_results=3)
                rag_context = self.rag_pipeline.build_rag_context(rag_results, incident)

            except Exception as e:
                logger.error("failed_to_fetch_incident_context", incident_id=incident_id, error=str(e))

        elif alert_id:
            alert = await te.get_alert(alert_id)
            if alert:
                desc = alert.get("human_explanation", "") or alert.get("top_rule", "")
                rag_results = await self.rag_pipeline.retrieve_similar(desc, n_results=3)
                rag_context = self.rag_pipeline.build_rag_context(rag_results, alert)

        # Intent Matching explicitly bound against template router
        q_lower = user_question.lower()
        q_type = "general"
        if incident:
            input_text = incident_investigation_prompt(
                incident=incident,
                alerts=inc_alerts,
                rag_context=rag_context,
                pattern_matches=incident.get("matched_patterns", []),
                tokenizer=tokenizer
            )
            q_type = "investigation"
        elif alert:
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

        # Cache Interception
        # Disable cache on multi-turn history strictly if conversation length > 0
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

                # Update Cache
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

        # Fire Evaluator safely off thread bounds implicitly
        if self.es:
            def bg_evaluate():
                metrics = self.evaluator.evaluate_response(
                    question=user_question,
                    response=answer,
                    alert=alert or {},
                    parsed=parsed_dict or {},
                    response_time_ms=resp_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    question_type=q_type
                )
                q_score = self.evaluator.compute_quality_score(metrics)
                asyncio.create_task(self.evaluator.store_metrics(self.es, metrics, q_score))

            try:
                bg_evaluate()
            except Exception as e:
                logger.error("evaluator_mapping_failed", error=str(e))

        return {
            "answer": answer,
            "sources": [],
            "tools_used": [t.name for t in self.tools],
            "parsed": parsed_dict,
            "from_cache": cache_level != "miss",
            "cache_level": cache_level
        }
