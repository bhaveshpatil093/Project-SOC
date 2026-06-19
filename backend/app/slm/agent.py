import json
import logging
import asyncio
from typing import Any, List, Optional

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.llms.base import LLM
from pydantic import Field
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from app.slm.model_loader import SLMEngine, get_slm_engine
from app.slm.rag_pipeline import RAGPipeline, get_rag_pipeline
from app.scoring.threat_engine import get_threat_engine
from app.ingestion.es_client import get_es_client
from app.ingestion.log_fetcher import fetch_by_entity
from app.slm.prompt_templates import (
    alert_explanation_prompt,
    triage_decision_prompt,
    investigation_steps_prompt,
    remediation_prompt,
    general_soc_question_prompt,
    build_multi_turn_prompt
)
from app.slm.response_parser import parse_slm_response, format_for_display
from app.slm.evaluator import get_slm_evaluator
from app.slm.cache import get_slm_cache
import time
import asyncio

logger = logging.getLogger(__name__)

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

# --- Custom SLM ReAct LLM Wrapper ---

class SLMLangChainWrapper(LLM):
    """Wraps explicit SLMEngine bounds mapping seamlessly inside LangChain execution loops."""
    engine: Any = Field(description="Instance of the running SLMEngine")
    
    @property
    def _llm_type(self) -> str:
        return "slm_phi3"
        
    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> str:
        res = self.engine.generate(prompt=prompt, system_prompt="You are an autonomous ReAct AI agent investigating anomalies. Think step by step securely.", max_new_tokens=512)
        
        # Phi-3 generation loops might hallucinate beyond bounds if stop tokens aren't respected natively
        if stop:
            for s in stop:
                if s in res:
                    res = res.split(s)[0]
                    
        return res

# --- Primary Orchestrator ---

class SOCAgent:
    def __init__(self, slm_engine=None, rag_pipeline=None, es=None):
        self.slm_engine = slm_engine
        self.rag_pipeline = rag_pipeline
        self.es = es
        self.evaluator = get_slm_evaluator()
        self.cache = get_slm_cache()
        self.llm = SLMLangChainWrapper(engine=self.slm_engine)
        self.tools = [get_alert_details, get_entity_history, search_similar_alerts, get_mitre_info, get_raw_logs]
        
        self.prompt = PromptTemplate.from_template(
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
        
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, handle_parsing_errors=True)

    async def investigate(self, user_question: str, alert_id: str = None, conversation_history: list[dict] = None) -> dict:
        alert = {}
        rag_context = ""
        tokenizer = getattr(self.slm_engine, "tokenizer", None)
        
        if alert_id:
            te = get_threat_engine()
            alert = await te.get_alert(alert_id)
            if alert:
                desc = alert.get("human_explanation", "") or alert.get("top_rule", "")
                rag_results = await self.rag_pipeline.retrieve_similar(desc, n_results=3)
                rag_context = self.rag_pipeline.build_rag_context(rag_results, alert)
                
        # Intent Matching explicitly bound against template router
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

        # Cache Interception
        # Disable cache on multi-turn history strictly if conversation length > 0
        cached_val = None
        cache_level = "miss"
        if not conversation_history:
            cached_val, cache_level = self.cache.get(user_question, alert_id)
            
        if cached_val:
            answer = cached_val
            logger.info(f"SLM Cache Hit ({cache_level}): Served seamlessly without generation penalty.")
        else:
            try:
                res = await self.agent_executor.ainvoke({"input": input_text})
                answer = res.get("output", "")
                
                # Update Cache
                if not conversation_history:
                    self.cache.set(user_question, answer, alert_id)
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
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
            logger.error(f"Error parsing SLM response: {e}")

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
                logger.error(f"Evaluator mapping failed implicitly: {e}")

        return {
            "answer": answer,
            "sources": [],
            "tools_used": [t.name for t in self.tools],
            "parsed": parsed_dict,
            "from_cache": cache_level != "miss",
            "cache_level": cache_level
        }
