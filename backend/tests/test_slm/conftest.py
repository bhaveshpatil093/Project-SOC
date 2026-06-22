import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import torch

@pytest.fixture
def mock_tokenizer():
    tokenizer = MagicMock()
    tokenizer.eos_token_id = 2
    
    # Mock return values for calling the tokenizer (inputs)
    inputs = MagicMock()
    inputs.input_ids = torch.tensor([[1, 2, 3]])
    inputs.to.return_value = inputs
    tokenizer.return_value = inputs
    
    tokenizer.apply_chat_template.return_value = "prompt string"
    tokenizer.decode.return_value = "This is a mock SLM response."
    
    return tokenizer

@pytest.fixture
def mock_model():
    model = MagicMock()
    model.device = "cpu"
    # Mock the generate function to return tensor of shape [1, N]
    # N must be > inputs.input_ids.shape[1] (which is 3 in mock_tokenizer)
    model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
    return model

@pytest.fixture
def mock_chroma():
    chroma = MagicMock()
    chroma.query.return_value = {
        "documents": [["Document 1", "Document 2"]],
        "metadatas": [[{"id": "doc1", "entity": "host1"}, {"id": "doc2", "entity": "host1"}]],
        "distances": [[0.1, 0.2]]
    }
    return chroma

@pytest.fixture
def mock_slm_engine(mock_tokenizer, mock_model):
    engine = MagicMock()
    engine.tokenizer = mock_tokenizer
    engine.model = mock_model
    engine.model_name = "test-model"
    engine.is_finetuned = False
    engine.device = "cpu"
    
    engine.generate.return_value = "Mocked engine response"
    
    # Needs to be an AsyncMock for awaitable functions
    engine.generate_async = AsyncMock(return_value="Mocked engine response")
    engine.load = AsyncMock(return_value={"loaded": True})
    engine.reload = AsyncMock(return_value={"loaded": True})
    
    engine.is_loaded.return_value = True
    
    return engine
