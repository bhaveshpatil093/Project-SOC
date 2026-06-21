import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

WEBHOOK_INDEX = "soc-webhooks"


@dataclass
class WebhookConfig:
    webhook_id: str
    name: str
    url: str
    secret: str
    events: List[str]
    filters: Dict[str, Any]
    is_active: bool
    created_at: str
    last_triggered: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0


class WebhookManager:

    async def initialize(self, es):
        exists = await es.indices.exists(index=WEBHOOK_INDEX)
        if not exists:
            await es.indices.create(index=WEBHOOK_INDEX, body={
                "mappings": {
                    "properties": {
                        "webhook_id": {"type": "keyword"},
                        "name": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "secret": {"type": "keyword"},
                        "events": {"type": "keyword"},
                        "is_active": {"type": "boolean"},
                        "created_at": {"type": "date"},
                        "last_triggered": {"type": "date"},
                        "success_count": {"type": "integer"},
                        "failure_count": {"type": "integer"},
                    }
                }
            })
            logger.info(f"Created index {WEBHOOK_INDEX}")

    async def register_webhook(self, es, config: WebhookConfig) -> WebhookConfig:
        await es.index(index=WEBHOOK_INDEX, id=config.webhook_id, body=asdict(config))
        return config

    async def list_webhooks(self, es) -> List[WebhookConfig]:
        try:
            resp = await es.search(
                index=WEBHOOK_INDEX,
                body={"query": {"match_all": {}}, "size": 100, "sort": [{"created_at": {"order": "desc"}}]},
                ignore_unavailable=True
            )
            return [WebhookConfig(**hit["_source"]) for hit in resp.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Error listing webhooks: {e}")
            return []

    async def get_webhook(self, es, webhook_id: str) -> Optional[WebhookConfig]:
        try:
            resp = await es.get(index=WEBHOOK_INDEX, id=webhook_id, ignore=[404])
            if resp and resp.get("found"):
                return WebhookConfig(**resp["_source"])
            return None
        except Exception as e:
            logger.error(f"Error fetching webhook {webhook_id}: {e}")
            return None

    async def update_webhook(self, es, webhook_id: str, updates: dict):
        await es.update(index=WEBHOOK_INDEX, id=webhook_id, body={"doc": updates})

    async def delete_webhook(self, es, webhook_id: str):
        await es.delete(index=WEBHOOK_INDEX, id=webhook_id, ignore=[404])

    async def dispatch_event(self, es, event_type: str, payload: dict):
        """Find matching webhooks and dispatch to all of them concurrently."""
        try:
            webhooks = await self.list_webhooks(es)
            matching = [
                w for w in webhooks
                if w.is_active and event_type in w.events and self._passes_filters(w, payload)
            ]
            if matching:
                tasks = [self._send_webhook(es, w, event_type, payload) for w in matching]
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error dispatching webhook event {event_type}: {e}")

    def _passes_filters(self, config: WebhookConfig, payload: dict) -> bool:
        filters = config.filters or {}
        alert = payload.get("alert", payload)  # handle both direct alert and wrapped

        level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = filters.get("min_threat_level", "")
        if min_level:
            alert_level = alert.get("threat_level", "low")
            if level_order.get(alert_level, 0) < level_order.get(min_level, 0):
                return False

        min_score = filters.get("min_score", 0.0)
        if min_score:
            alert_score = float(alert.get("threat_score", 0))
            if alert_score < min_score:
                return False

        return True

    def _sign_payload(self, secret: str, body: bytes) -> str:
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    async def _send_webhook(self, es, config: WebhookConfig, event_type: str, payload: dict):
        timestamp = datetime.utcnow().isoformat() + "Z"
        envelope = {
            "event_type": event_type,
            "timestamp": timestamp,
            "data": payload,
        }
        body_bytes = json.dumps(envelope).encode()
        signature = self._sign_payload(config.secret, body_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-SOC-Event": event_type,
            "X-SOC-Timestamp": timestamp,
            "X-SOC-Signature": f"sha256={signature}",
            "User-Agent": "ISRO-SOC-Platform/1.0",
        }

        success = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config.url,
                    data=body_bytes,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    success = resp.status < 400
                    if not success:
                        logger.warning(f"Webhook {config.webhook_id} returned HTTP {resp.status}")
        except asyncio.TimeoutError:
            logger.warning(f"Webhook {config.webhook_id} timed out")
        except Exception as e:
            logger.warning(f"Webhook {config.webhook_id} failed: {e}")

        # Update counts
        count_field = "success_count" if success else "failure_count"
        try:
            await es.update(
                index=WEBHOOK_INDEX,
                id=config.webhook_id,
                body={
                    "script": {
                        "source": f"ctx._source.{count_field}++; ctx._source.last_triggered = params.ts",
                        "params": {"ts": timestamp},
                    }
                },
            )
        except Exception:
            pass

    async def test_webhook(self, es, webhook_id: str) -> dict:
        config = await self.get_webhook(es, webhook_id)
        if not config:
            return {"success": False, "error": "Webhook not found"}

        test_payload = {
            "event_type": "test",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "message": "SOC Platform webhook test",
                "webhook_id": webhook_id,
                "webhook_name": config.name,
            },
        }
        body_bytes = json.dumps(test_payload).encode()
        signature = self._sign_payload(config.secret, body_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-SOC-Event": "test",
            "X-SOC-Timestamp": test_payload["timestamp"],
            "X-SOC-Signature": f"sha256={signature}",
            "User-Agent": "ISRO-SOC-Platform/1.0",
        }

        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config.url,
                    data=body_bytes,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    body = await resp.text()
                    elapsed = int((time.time() - start) * 1000)
                    return {
                        "success": resp.status < 400,
                        "http_status": resp.status,
                        "response_body": body[:500],
                        "latency_ms": elapsed,
                    }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Webhook timed out (10s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}


webhook_manager = WebhookManager()
