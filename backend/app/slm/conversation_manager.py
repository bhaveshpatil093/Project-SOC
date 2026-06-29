import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class ConversationTurn:
    turn_id: str
    role: str
    content: str
    parsed_response: dict | None
    alert_id: str | None
    tools_used: list[str]
    timestamp: datetime
    response_time_ms: float | None

@dataclass
class Conversation:
    conversation_id: str
    started_at: datetime
    last_active: datetime
    alert_id: str | None
    entity_key: str | None
    turns: list[ConversationTurn]
    metadata: dict = field(default_factory=dict)

class ConversationManager:
    def __init__(self, max_conversations: int = 100, max_turns_per_conv: int = 20, ttl_hours: int = 24):
        self.max_conversations = max_conversations
        self.max_turns_per_conv = max_turns_per_conv
        self.ttl_hours = ttl_hours
        self._store: dict[str, Conversation] = {}

    def create_conversation(self, alert_id: str = None, entity_key: str = None) -> Conversation:
        # Enforce max memory bound globally
        if len(self._store) >= self.max_conversations:
            self._evict_oldest()

        conv_id = str(uuid.uuid4())
        now = datetime.utcnow()
        conv = Conversation(
            conversation_id=conv_id,
            started_at=now,
            last_active=now,
            alert_id=alert_id,
            entity_key=entity_key,
            turns=[]
        )
        self._store[conv_id] = conv
        return conv

    def _evict_oldest(self):
        if not self._store:
            return
        oldest_id = min(self._store.keys(), key=lambda k: self._store[k].last_active)
        del self._store[oldest_id]

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        conv = self._store.get(conversation_id)
        if conv:
            conv.last_active = datetime.utcnow()
        return conv

    def add_turn(self, conversation_id: str, role: str, content: str,
                 parsed_response: dict = None, alert_id: str = None,
                 tools_used: list = None, response_time_ms: float = None) -> ConversationTurn:
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found natively inside state map.")

        # Track sliding window vectors natively dropping deepest tokens
        if len(conv.turns) >= self.max_turns_per_conv:
            conv.turns.pop(0)

        turn = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            role=role,
            content=content,
            parsed_response=parsed_response,
            alert_id=alert_id,
            tools_used=tools_used or [],
            timestamp=datetime.utcnow(),
            response_time_ms=response_time_ms
        )
        conv.turns.append(turn)
        conv.last_active = datetime.utcnow()
        return turn

    def get_history_for_prompt(self, conversation_id: str, max_turns: int = 6) -> list[dict[str, str]]:
        conv = self.get_conversation(conversation_id)
        if not conv:
            return []

        # We slice exactly N sequential bounding objects natively
        recent = conv.turns[-max_turns:]
        return [{"role": t.role, "content": t.content} for t in recent]

    def list_conversations(self) -> list[dict]:
        out = []
        for c in sorted(self._store.values(), key=lambda x: x.last_active, reverse=True):
            out.append({
                "conversation_id": c.conversation_id,
                "started_at": c.started_at.isoformat(),
                "last_active": c.last_active.isoformat(),
                "alert_id": c.alert_id,
                "turns_count": len(c.turns)
            })
        return out

    def delete_conversation(self, conversation_id: str):
        if conversation_id in self._store:
            del self._store[conversation_id]

    def cleanup_expired(self):
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self.ttl_hours)
        expired = [cid for cid, conv in self._store.items() if conv.last_active < cutoff]
        for cid in expired:
            del self._store[cid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired conversation envelopes securely.")

    def get_stats(self) -> dict:
        total_convs = len(self._store)
        now = datetime.utcnow()
        active_1h = len([c for c in self._store.values() if c.last_active > now - timedelta(hours=1)])

        total_turns = sum(len(c.turns) for c in self._store.values())
        avg_turns = total_turns / total_convs if total_convs > 0 else 0.0

        resp_times = []
        for c in self._store.values():
            for t in c.turns:
                if t.response_time_ms:
                    resp_times.append(t.response_time_ms)

        avg_resp = sum(resp_times) / len(resp_times) if resp_times else 0.0

        return {
            "total_conversations": total_convs,
            "active_last_1h": active_1h,
            "avg_turns": round(avg_turns, 2),
            "avg_response_time_ms": round(avg_resp, 2)
        }

# Global Singleton mapping runtime tracking boundaries
_conversation_manager = ConversationManager()

def get_conversation_manager() -> ConversationManager:
    return _conversation_manager
