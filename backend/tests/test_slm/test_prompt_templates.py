import pytest
from unittest.mock import MagicMock
from app.slm.prompt_templates import (
    count_tokens,
    truncate_to_tokens,
    alert_explanation_prompt,
    build_multi_turn_prompt
)

@pytest.fixture
def mock_tokenizer():
    tokenizer = MagicMock()
    # Mock encode to just split by spaces for testing
    tokenizer.encode.side_effect = lambda text: text.split()
    tokenizer.decode.side_effect = lambda tokens, **kwargs: " ".join(tokens)
    return tokenizer

def test_token_counter_accurate(mock_tokenizer):
    text = "one two three four five"
    assert count_tokens(text, mock_tokenizer) == 5
    
    # Without tokenizer fallback: 23 chars // 4 = 5
    assert count_tokens(text, None) == 5

def test_truncate_to_tokens_preserves_question(mock_tokenizer):
    text = "word1 word2 word3 word4 word5"
    truncated = truncate_to_tokens(text, 3, mock_tokenizer)
    assert truncated == "word1 word2 word3"
    
    # If smaller than max_tokens, should return original
    assert truncate_to_tokens(text, 10, mock_tokenizer) == text

def test_alert_explanation_prompt_includes_all_sections(mock_tokenizer):
    alert = {
        "entity_key": "host1",
        "threat_level": "high",
        "threat_score": 0.9,
        "log_type": "network",
        "triggered_rules": ["rule1"],
        "shap_values": {"feat": 1},
        "mitre_tactics": ["Tactic1"],
        "mitre_techniques": ["Tech1"]
    }
    
    prompt = alert_explanation_prompt(alert, "RAG Context Data", mock_tokenizer)
    
    assert "host1" in prompt
    assert "high" in prompt
    assert "rule1" in prompt
    assert "feat" in prompt
    assert "Tactic1" in prompt
    assert "RAG Context Data" in prompt
    assert "Question: Explain this alert" in prompt

def test_multi_turn_prompt_includes_history(mock_tokenizer):
    history = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"}
    ]
    
    prompt = build_multi_turn_prompt(history, "Question 2", "Context", mock_tokenizer)
    
    assert "Previous Conversation" in prompt
    assert "Question 1" in prompt
    assert "Answer 1" in prompt
    assert "Context" in prompt
    assert "Current question: Question 2" in prompt
