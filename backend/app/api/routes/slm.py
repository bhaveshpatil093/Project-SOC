import uuid
import time
import json
import logging
import asyncio
import threading
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import TextIteratorStreamer
import torch

from app.slm.model_loader import get_slm_engine, SOC_SYSTEM_PROMPT
from app.slm.rag_pipeline import get_rag_pipeline
from app.slm.agent import SOCAgent
from app.scoring.threat_engine import get_threat_engine
from app.ingestion.es_client import get_es_client

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory conversation store isolating chat histories natively
# Format: { "conv_id": {"messages": [...], "started_at": ..., "last_alert_id": ...} }
CONVERSATIONS = {}

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

def get_soc_agent() -> SOCAgent:
    slm = get_slm_engine()
    if not slm.is_loaded():
        raise HTTPException(status_code=503, detail="SLM Engine is currently offline or loading.")
    rag = get_rag_pipeline()
    return SOCAgent(slm_engine=slm, rag_pipeline=rag, es=None)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, agent: SOCAgent = Depends(get_soc_agent)):
    start_t = time.time()
    
    conv_id = req.conversation_id or str(uuid.uuid4())
    
    if conv_id not in CONVERSATIONS:
        CONVERSATIONS[conv_id] = {
            "started_at": datetime.utcnow(),
            "messages": [],
            "last_alert_id": req.alert_id
        }
    
    conv = CONVERSATIONS[conv_id]
    if req.alert_id:
        conv["last_alert_id"] = req.alert_id
        
    user_msg = ChatMessage(role="user", content=req.message, timestamp=datetime.utcnow())
    conv["messages"].append(user_msg.model_dump())
    
    if len(conv["messages"]) > 20:
        conv["messages"] = conv["messages"][-20:]
        
    history = conv["messages"][:-1]
    
    res = await agent.investigate(user_question=req.message, alert_id=req.alert_id, conversation_history=history)
    
    asst_msg = ChatMessage(role="assistant", content=res.get("answer", ""), timestamp=datetime.utcnow())
    conv["messages"].append(asst_msg.model_dump())
    
    resp_time = (time.time() - start_t) * 1000
    
    return ChatResponse(
        conversation_id=conv_id,
        message=asst_msg,
        sources=res.get("sources", []),
        tools_used=res.get("tools_used", []),
        response_time_ms=resp_time
    )

@router.get("/conversations")
async def list_conversations():
    res = []
    for cid, data in CONVERSATIONS.items():
        res.append({
            "id": cid,
            "started_at": data["started_at"],
            "message_count": len(data["messages"]),
            "last_alert_id": data["last_alert_id"]
        })
    return sorted(res, key=lambda x: x["started_at"], reverse=True)

@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    if conversation_id in CONVERSATIONS:
        del CONVERSATIONS[conversation_id]
    return {"status": "cleared"}

@router.post("/explain/{alert_id}")
async def explain_alert(alert_id: str, agent: SOCAgent = Depends(get_soc_agent)):
    prompt = "Explain this security alert in simple terms for a Level-1 SOC engineer."
    res = await agent.investigate(user_question=prompt, alert_id=alert_id, conversation_history=[])
    return {"explanation": res.get("answer", "")}

@router.get("/status")
async def slm_status():
    slm = get_slm_engine()
    rag = get_rag_pipeline()
    
    indexed = 0
    if rag.collection:
        try:
            indexed = rag.collection.count()
        except:
            pass
            
    return {
        "model_loaded": slm.is_loaded(),
        "model_name": slm.model_name,
        "device": slm.device,
        "rag_indexed_count": indexed
    }

@router.post("/chat/stream")
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
