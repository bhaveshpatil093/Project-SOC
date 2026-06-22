import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.slm.agent import SOCAgent, run_react_loop

pytestmark = pytest.mark.asyncio

@pytest.fixture
def agent_instance(mock_slm_engine):
    rag = MagicMock()
    rag.retrieve_similar = AsyncMock(return_value=[])
    rag.build_rag_context = MagicMock(return_value="Context")
    
    agent = SOCAgent(slm_engine=mock_slm_engine, rag_pipeline=rag, es=None)
    # Mock the cache to always miss
    agent.cache = MagicMock()
    agent.cache.get.return_value = (None, "miss")
    return agent

@patch("app.slm.agent.get_threat_engine")
@patch("app.slm.agent.parse_slm_response")
@patch("app.slm.agent.asdict", create=True)
async def test_investigate_returns_answer_and_sources(mock_asdict, mock_parse, mock_te, agent_instance, mock_slm_engine):
    mock_te_instance = AsyncMock()
    mock_te_instance.get_alert.return_value = {"id": "1", "human_explanation": "Test"}
    mock_te.return_value = mock_te_instance
    
    mock_slm_engine.generate.return_value = "Thought: I know it\nFinal Answer: Test Answer"
    
    res = await agent_instance.investigate("What is this?", alert_id="1")
    
    assert res["answer"] == "Test Answer"
    assert "tools_used" in res

@patch("app.slm.agent.get_threat_engine")
async def test_investigate_uses_tools_for_complex_questions(mock_te, agent_instance, mock_slm_engine):
    mock_te_instance = AsyncMock()
    mock_te_instance.get_alert.return_value = {}
    mock_te.return_value = mock_te_instance
    
    # First response attempts to use a tool, second gives final answer
    mock_slm_engine.generate.side_effect = [
        "Thought: Let's use a tool\nAction: get_mitre_info\nAction Input: T1059",
        "Thought: I know now\nFinal Answer: PowerShell used"
    ]
    
    res = await agent_instance.investigate("Explain MITRE T1059")
    
    assert res["answer"] == "PowerShell used"
    assert mock_slm_engine.generate.call_count == 2

@patch("app.slm.agent.get_threat_engine")
async def test_investigate_handles_missing_alert_id(mock_te, agent_instance, mock_slm_engine):
    mock_slm_engine.generate.return_value = "Thought: \nFinal Answer: General answer"
    
    res = await agent_instance.investigate("What is SOC?")
    
    assert res["answer"] == "General answer"
    mock_te.assert_not_called()

@patch("app.slm.agent.alert_explanation_prompt")
@patch("app.slm.agent.get_threat_engine")
async def test_build_investigation_prompt_includes_shap(mock_te, mock_explain, agent_instance, mock_slm_engine):
    mock_te_instance = AsyncMock()
    mock_te_instance.get_alert.return_value = {"id": "1", "shap_values": {"feature1": 0.5}}
    mock_te.return_value = mock_te_instance
    
    mock_slm_engine.generate.return_value = "Thought: \nFinal Answer: ok"
    
    await agent_instance.investigate("Explain this alert", alert_id="1")
    
    mock_explain.assert_called_once()
    args = mock_explain.call_args.args
    assert "shap_values" in args[0]

@patch("app.slm.agent.triage_decision_prompt")
@patch("app.slm.agent.get_threat_engine")
async def test_intent_detection_routes_to_correct_template(mock_te, mock_triage, agent_instance, mock_slm_engine):
    mock_te_instance = AsyncMock()
    mock_te_instance.get_alert.return_value = {"id": "1"}
    mock_te.return_value = mock_te_instance
    
    mock_slm_engine.generate.return_value = "Thought: \nFinal Answer: ok"
    
    await agent_instance.investigate("Is this a true positive?", alert_id="1")
    
    mock_triage.assert_called_once()
