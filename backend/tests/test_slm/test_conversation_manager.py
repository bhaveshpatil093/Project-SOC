import pytest
from datetime import datetime, timedelta
from app.slm.conversation_manager import ConversationManager

@pytest.fixture
def manager():
    return ConversationManager(max_conversations=5, max_turns_per_conv=3, ttl_hours=24)

def test_create_conversation_generates_uuid(manager):
    conv = manager.create_conversation(alert_id="123")
    assert conv.conversation_id is not None
    assert type(conv.conversation_id) is str
    assert conv.alert_id == "123"
    assert len(manager._store) == 1

def test_add_turn_appends_correctly(manager):
    conv = manager.create_conversation()
    manager.add_turn(conv.conversation_id, "user", "Hello")
    
    retrieved = manager.get_conversation(conv.conversation_id)
    assert len(retrieved.turns) == 1
    assert retrieved.turns[0].role == "user"
    assert retrieved.turns[0].content == "Hello"

def test_max_turns_trims_oldest(manager):
    conv = manager.create_conversation()
    
    manager.add_turn(conv.conversation_id, "user", "T1")
    manager.add_turn(conv.conversation_id, "user", "T2")
    manager.add_turn(conv.conversation_id, "user", "T3")
    
    # Adding a 4th turn should drop T1 because max_turns_per_conv=3
    manager.add_turn(conv.conversation_id, "user", "T4")
    
    retrieved = manager.get_conversation(conv.conversation_id)
    assert len(retrieved.turns) == 3
    assert retrieved.turns[0].content == "T2"
    assert retrieved.turns[-1].content == "T4"

def test_get_history_for_prompt_format(manager):
    conv = manager.create_conversation()
    manager.add_turn(conv.conversation_id, "user", "Question")
    manager.add_turn(conv.conversation_id, "assistant", "Answer")
    
    history = manager.get_history_for_prompt(conv.conversation_id)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Question"}
    assert history[1] == {"role": "assistant", "content": "Answer"}

def test_cleanup_expired_removes_old_conversations(manager):
    conv1 = manager.create_conversation()
    conv2 = manager.create_conversation()
    
    # Manually set conv1 to be 25 hours old
    conv1.last_active = datetime.utcnow() - timedelta(hours=25)
    
    manager.cleanup_expired()
    
    assert manager.get_conversation(conv1.conversation_id) is None
    assert manager.get_conversation(conv2.conversation_id) is not None

def test_get_stats_accurate_counts(manager):
    conv1 = manager.create_conversation()
    manager.add_turn(conv1.conversation_id, "user", "H", response_time_ms=100.0)
    manager.add_turn(conv1.conversation_id, "assistant", "A", response_time_ms=200.0)
    
    stats = manager.get_stats()
    assert stats["total_conversations"] == 1
    assert stats["active_last_1h"] == 1
    assert stats["avg_turns"] == 2.0
    assert stats["avg_response_time_ms"] == 150.0
