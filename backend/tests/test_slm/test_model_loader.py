import pytest
from unittest.mock import patch, MagicMock
from app.slm.model_loader import SLMEngine

pytestmark = pytest.mark.asyncio

@patch("app.slm.model_loader.os.path.exists")
@patch("app.slm.model_loader.AutoTokenizer.from_pretrained")
@patch("app.slm.model_loader.AutoModelForCausalLM.from_pretrained")
async def test_auto_mode_loads_finetuned_if_exists(mock_model, mock_tokenizer, mock_exists):
    mock_exists.return_value = True
    engine = SLMEngine(model_name="auto")
    await engine.load()
    assert engine.is_finetuned is True
    assert "phi3-soc-finetuned/merged" in engine.finetuned_path

@patch("app.slm.model_loader.os.path.exists")
@patch("app.slm.model_loader.AutoTokenizer.from_pretrained")
@patch("app.slm.model_loader.AutoModelForCausalLM.from_pretrained")
async def test_auto_mode_loads_base_if_no_finetuned(mock_model, mock_tokenizer, mock_exists):
    mock_exists.return_value = False
    engine = SLMEngine(model_name="auto")
    await engine.load()
    assert engine.is_finetuned is False
    assert engine.finetuned_path is None

@patch("app.slm.model_loader.AutoTokenizer.from_pretrained")
@patch("app.slm.model_loader.AutoModelForCausalLM.from_pretrained")
async def test_generate_returns_non_empty_string(mock_model_pt, mock_tokenizer_pt, mock_tokenizer, mock_model):
    # Setup mock tokenizer and model internally
    engine = SLMEngine(model_name="base")
    engine.tokenizer = mock_tokenizer
    engine.model = mock_model
    
    response = await engine.generate_async("Hello")
    assert response == "This is a mock SLM response."

@patch("app.slm.model_loader.AutoTokenizer.from_pretrained")
@patch("app.slm.model_loader.AutoModelForCausalLM.from_pretrained")
async def test_generate_respects_max_new_tokens(mock_model_pt, mock_tokenizer_pt, mock_tokenizer, mock_model):
    engine = SLMEngine(model_name="base")
    engine.tokenizer = mock_tokenizer
    engine.model = mock_model
    
    await engine.generate_async("Hello", max_new_tokens=50)
    mock_model.generate.assert_called_once()
    _, kwargs = mock_model.generate.call_args
    assert kwargs.get("max_new_tokens") == 50

@patch("app.slm.model_loader.os.path.exists")
@patch("app.slm.model_loader.AutoTokenizer.from_pretrained")
@patch("app.slm.model_loader.AutoModelForCausalLM.from_pretrained")
async def test_reload_swaps_model_correctly(mock_model, mock_tokenizer, mock_exists):
    mock_exists.return_value = False
    engine = SLMEngine(model_name="base")
    await engine.load()
    
    assert engine.model_name == "microsoft/Phi-3-mini-4k-instruct"
    
    mock_exists.return_value = True
    await engine.reload("auto")
    
    assert engine.is_finetuned is True

def test_get_model_info_returns_all_fields():
    engine = SLMEngine()
    info = engine.get_model_info()
    assert "model_name" in info
    assert "is_finetuned" in info
    assert "device" in info
    assert "loaded" in info
    assert "load_time_seconds" in info
    assert "estimated_memory_mb" in info

@patch("app.slm.model_loader.torch")
def test_unload_frees_memory(mock_torch):
    engine = SLMEngine()
    engine.model = MagicMock()
    engine.tokenizer = MagicMock()
    
    engine.unload()
    assert engine.model is None
    assert engine.tokenizer is None
    # Depending on availability, it either calls cuda empty_cache or mps empty_cache or neither.
    # It shouldn't crash.

def test_is_loaded_false_before_load():
    engine = SLMEngine()
    assert engine.is_loaded() is False
