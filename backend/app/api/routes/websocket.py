import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ingestion.es_client import get_es_client

router = APIRouter()
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._alert_buffer = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def _flush_loop(self):
        while True:
            await asyncio.sleep(2.0)
            batch = []
            async with self._buffer_lock:
                if self._alert_buffer:
                    batch = self._alert_buffer.copy()
                    self._alert_buffer.clear()

            if batch:
                batch_msg = {
                    "type": "new_alerts_batch",
                    "data": batch,
                    "timestamp": datetime.utcnow().isoformat()
                }
                msg_str = json.dumps(batch_msg, default=str)
                for connection in list(self.active_connections):
                    try:
                        await connection.send_text(msg_str)
                    except Exception as e:
                        logger.error(f"Failed to broadcast batch to a client: {e}")
                        self.disconnect(connection)

    async def broadcast(self, message: dict):
        if message.get("type") == "new_alert":
            async with self._buffer_lock:
                self._alert_buffer.append(message.get("data"))
            return

        msg_str = json.dumps(message, default=str)
        # Convert to list to avoid modifying during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.error(f"Failed to broadcast to a client: {e}")
                self.disconnect(connection)

    async def send_personal(self, message: dict, ws: WebSocket):
        msg_str = json.dumps(message, default=str)
        try:
            await ws.send_text(msg_str)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(ws)

manager = ConnectionManager()

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        es = await get_es_client()
        query = {
            "query": {"term": {"status": "open"}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 10
        }
        try:
            res = await es.search(index="soc-processed-alerts", body=query, ignore_unavailable=True)
            hits = res.get("hits", {}).get("hits", [])
            initial_alerts = [{"id": h["_id"], **h["_source"]} for h in hits]

            await manager.send_personal({
                "type": "initial_alerts",
                "data": initial_alerts,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        except Exception as e:
            logger.warning(f"Could not fetch initial alerts for WS: {e}")
            await manager.send_personal({
                "type": "ping",
                "data": {"status": "connected", "message": "Initial fetch failed"},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)

        while True:
            # Keep connection alive natively
            data = await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
