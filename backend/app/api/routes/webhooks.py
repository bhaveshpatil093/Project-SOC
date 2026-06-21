import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional, Any

from app.api.auth_deps import get_current_user, require_role
from app.ingestion.es_client import get_es_client
from app.integrations.webhook_manager import webhook_manager, WebhookConfig

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    secret: str = ""
    events: List[str] = ["new_alert"]
    filters: Dict[str, Any] = {}
    is_active: bool = True


class UpdateWebhookRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


@router.get("", dependencies=[Depends(require_role("admin"))])
async def list_webhooks():
    try:
        es = await get_es_client()
        webhooks = await webhook_manager.list_webhooks(es)
        return {"webhooks": [vars(w) for w in webhooks]}
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list webhooks")


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_webhook(payload: CreateWebhookRequest):
    try:
        es = await get_es_client()
        config = WebhookConfig(
            webhook_id=uuid.uuid4().hex,
            name=payload.name,
            url=payload.url,
            secret=payload.secret or uuid.uuid4().hex,
            events=payload.events,
            filters=payload.filters,
            is_active=payload.is_active,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        created = await webhook_manager.register_webhook(es, config)
        return {"webhook": vars(created)}
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to create webhook")


@router.put("/{webhook_id}", dependencies=[Depends(require_role("admin"))])
async def update_webhook(webhook_id: str, payload: UpdateWebhookRequest):
    try:
        es = await get_es_client()
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        await webhook_manager.update_webhook(es, webhook_id, updates)
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update webhook")


@router.delete("/{webhook_id}", dependencies=[Depends(require_role("admin"))])
async def delete_webhook(webhook_id: str):
    try:
        es = await get_es_client()
        await webhook_manager.delete_webhook(es, webhook_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete webhook")


@router.post("/{webhook_id}/test", dependencies=[Depends(require_role("admin"))])
async def test_webhook(webhook_id: str):
    try:
        es = await get_es_client()
        result = await webhook_manager.test_webhook(es, webhook_id)
        return result
    except Exception as e:
        logger.error(f"Error testing webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to test webhook")
