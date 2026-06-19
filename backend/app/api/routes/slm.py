import uuid
import time
import json
import logging
import asyncio
import threading
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi import BackgroundTasks
from pydantic import BaseModel
from transformers import TextIteratorStreamer
from app.auth.jwt import require_role
import torch

from app.slm.model_loader import get_slm_engine, SOC_SYSTEM_PROMPT
from app.slm.rag_pipeline import get_rag_pipeline
from app.slm.agent import SOCAgent
from app.scoring.threat_engine import get_threat_engine
from app.ingestion.es_client import get_es_client
from app.slm.conversation_manager import get_conversation_manager

logger = logging.getLogger(__name__)

router = APIRouter()

class ReloadRequest(BaseModel):
    model: str # "auto" | "base" | "finetuned"

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime

class ChatRequest(BaseModel):
    message: str
    alert_id: str | None = None
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    sources: list[str]
    tools_used: list[str]
    response_time_ms: float
    parsed_response: dict | None = None

async def get_soc_agent() -> SOCAgent:
    slm = get_slm_engine()
    if not slm.is_loaded():
        raise HTTPException(status_code=503, detail="SLM Engine is currently offline or loading.")
    rag = get_rag_pipeline()
    es = await get_es_client()
    return SOCAgent(slm_engine=slm, rag_pipeline=rag, es=es)

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def chat_endpoint(req: ChatRequest, agent: SOCAgent = Depends(get_soc_agent)):
    start_t = time.time()
    cm = get_conversation_manager()
    
    conv = None
    if req.conversation_id:
        conv = cm.get_conversation(req.conversation_id)
        
    if not conv:
        conv = cm.create_conversation(alert_id=req.alert_id)
        
    if req.alert_id:
        conv.alert_id = req.alert_id
        
    history = cm.get_history_for_prompt(conv.conversation_id, max_turns=6)
    cm.add_turn(conv.conversation_id, role="user", content=req.message)
    
    res = await agent.investigate(user_question=req.message, alert_id=req.alert_id, conversation_history=history)
    
    resp_time = (time.time() - start_t) * 1000
    
    asst_turn = cm.add_turn(
        conv.conversation_id, 
        role="assistant", 
        content=res.get("answer", ""), 
        parsed_response=res.get("parsed"),
        alert_id=req.alert_id,
        tools_used=res.get("tools_used", []),
        response_time_ms=resp_time
    )
    
    asst_msg = ChatMessage(role="assistant", content=res.get("answer", ""), timestamp=asst_turn.timestamp)
    
    return ChatResponse(
        conversation_id=conv.conversation_id,
        message=asst_msg,
        sources=res.get("sources", []),
        tools_used=res.get("tools_used", []),
        response_time_ms=resp_time,
        parsed_response=res.get("parsed")
    )

@router.get("/conversations", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def list_conversations():
    cm = get_conversation_manager()
    return cm.list_conversations()

@router.delete("/conversations/{conversation_id}", dependencies=[Depends(require_role("admin", "analyst"))])
async def clear_conversation(conversation_id: str):
    cm = get_conversation_manager()
    cm.delete_conversation(conversation_id)
    return {"status": "cleared"}

@router.post("/explain/{alert_id}", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def explain_alert(alert_id: str, agent: SOCAgent = Depends(get_soc_agent)):
    prompt = "Explain this security alert in simple terms for a Level-1 SOC engineer."
    res = await agent.investigate(user_question=prompt, alert_id=alert_id, conversation_history=[])
    return {"explanation": res.get("answer", "")}

@router.get("/status", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def slm_status():
    slm = get_slm_engine()
    rag = get_rag_pipeline()
    
    indexed = 0
    if rag.collection:
        try:
            indexed = rag.collection.count()
        except:
            pass
            
    info = slm.get_model_info()
    info["rag_indexed_count"] = indexed
    return info

@router.post("/reload-model", dependencies=[Depends(require_role("admin"))])
async def reload_model(req: ReloadRequest):
    slm = get_slm_engine()
    try:
        res = await asyncio.wait_for(slm.reload(req.model), timeout=120.0)
        return res
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Model reload timed out.")

@router.get("/model-info", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def model_info():
    slm = get_slm_engine()
    return slm.get_model_info()

@router.post("/rag/reindex", dependencies=[Depends(require_role("admin", "analyst"))])
async def rag_reindex(background_tasks: BackgroundTasks):
    import uuid
    from app.ingestion.es_client import get_es_client
    
    rag = get_rag_pipeline()
    job_id = str(uuid.uuid4())
    
    async def run_reindex():
        try:
            es = await get_es_client()
            res = await rag.reindex_from_elasticsearch(es)
            logger.info(f"RAG Reindex Background Task [{job_id}] Completed: {res}")
        except Exception as e:
            logger.error(f"RAG Reindex Task [{job_id}] Failed: {e}")
            
    background_tasks.add_task(run_reindex)
    
    return {"job_id": job_id, "status": "started"}

@router.get("/rag/stats", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def rag_stats():
    rag = get_rag_pipeline()
    return await rag.get_index_stats()

@router.delete("/rag/clear", dependencies=[Depends(require_role("admin"))])
async def rag_clear(confirm: str = None):
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Must pass ?confirm=yes to safely execute destruction of the RAG ChromaDB vectors.")
    rag = get_rag_pipeline()
    rag.clear_index()
    return {"status": "cleared", "message": "ChromaDB mapped index fully destroyed successfully."}

@router.get("/metrics", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def get_slm_metrics(since_hours: int = 24):
    from app.slm.evaluator import get_slm_evaluator
    from app.ingestion.es_client import get_es_client
    
    es = await get_es_client()
    evaluator = get_slm_evaluator()
    
    return await evaluator.get_aggregate_stats(es, since_hours=since_hours)

@router.get("/cache/stats", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def cache_stats():
    from app.slm.cache import get_slm_cache
    cache = get_slm_cache()
    return cache.get_combined_stats()

@router.delete("/cache/clear", dependencies=[Depends(require_role("admin", "analyst"))])
async def cache_clear():
    from app.slm.cache import get_slm_cache
    cache = get_slm_cache()
    cache.clear()
    return {"status": "cleared", "message": "Exact and Semantic SLM caches completely destroyed."}

@router.post("/chat/stream", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def chat_stream(req: Request):
    """
    Streams raw SLMEngine outputs utilizing Transformers TextIteratorStreamer and Server-Sent Events natively.
    """
    body = await req.json()
    prompt = body.get("message", "")
    
    slm = get_slm_engine()
    if not slm.is_loaded():
        raise HTTPException(status_code=503, detail="SLM Engine is offline.")
        
    async def token_generator():
        tokenizer = slm.tokenizer
        model = slm.model
        
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        messages = [
            {"role": "system", "content": SOC_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=512,
            temperature=0.3,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        with torch.no_grad():
            thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
            thread.start()
            
            for new_text in streamer:
                if new_text:
                    payload = json.dumps({"type": "token", "data": new_text})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0.01)
                    
            yield f"data: {json.dumps({'type': 'done', 'data': ''})}\n\n"
            
    return StreamingResponse(token_generator(), media_type="text/event-stream")
