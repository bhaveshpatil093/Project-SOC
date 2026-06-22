import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.slm.rag_pipeline import RAGPipeline

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_st_model():
    model = MagicMock()
    emb_mock = MagicMock()
    emb_mock.tolist.return_value = [0.1, 0.2, 0.3]
    model.encode.return_value = emb_mock
    return model

@pytest.fixture
def rag_instance(mock_chroma, mock_st_model):
    rag = RAGPipeline(persist_dir="/tmp/fake")
    rag.collection = mock_chroma
    rag.client = MagicMock()
    rag.model = mock_st_model
    return rag

async def test_index_alert_stores_in_chromadb(rag_instance, mock_chroma):
    alert = {
        "id": "alert-123",
        "entity_key": "host1|user1",
        "threat_level": "high",
        "threat_score": 0.9,
        "mitre_tactics": ["T1059"],
        "human_explanation": "Test explanation",
        "top_rule": "rule1"
    }
    
    await rag_instance.index_alert(alert)
    
    mock_chroma.upsert.assert_called_once()
    kwargs = mock_chroma.upsert.call_args.kwargs
    assert kwargs["ids"][0] == "alert-123"
    assert kwargs["embeddings"][0] == [0.1, 0.2, 0.3]
    assert "alert-123" in kwargs["metadatas"][0]["alert_id"]

async def test_retrieve_similar_returns_relevant_results(rag_instance, mock_chroma):
    results = await rag_instance.retrieve_similar("Test query")
    
    assert len(results) == 2
    assert results[0]["document"] == "Document 1"
    assert results[0]["distance"] == 0.1
    mock_chroma.query.assert_called_once()

async def test_retrieve_similar_respects_n_results(rag_instance, mock_chroma):
    await rag_instance.retrieve_similar("Test query", n_results=5)
    
    kwargs = mock_chroma.query.call_args.kwargs
    assert kwargs["n_results"] == 5

def test_build_rag_context_truncates_at_2000_chars(rag_instance):
    current_alert = {"entity_key": "host1", "threat_level": "high", "threat_score": 0.9}
    
    # Create a very long document to force truncation
    long_doc = "A" * 1500
    retrieved = [
        {"document": long_doc},
        {"document": long_doc}
    ]
    
    context = rag_instance.build_rag_context(retrieved, current_alert)
    
    # Should contain the first document but skip the second one because it exceeds ~1800 chars
    assert len(context) < 2000
    assert context.count(long_doc) == 1

async def test_filter_by_entity_works(rag_instance, mock_chroma):
    await rag_instance.retrieve_similar("Test query", filter_entity="host1")
    
    kwargs = mock_chroma.query.call_args.kwargs
    assert kwargs["where"] == {"entity_key": "host1"}

async def test_reindex_from_elasticsearch_indexes_all(rag_instance):
    mock_es = AsyncMock()
    mock_es.search.return_value = {
        "hits": {
            "hits": [
                {"_id": "1", "_source": {"entity_key": "host1|user1"}},
                {"_id": "2", "_source": {"entity_key": "host2|user2"}}
            ]
        }
    }
    
    rag_instance.index_batch = AsyncMock()
    
    result = await rag_instance.reindex_from_elasticsearch(mock_es)
    
    assert result["indexed"] == 2
    rag_instance.index_batch.assert_called_once()
    
    args = rag_instance.index_batch.call_args.args[0]
    assert len(args) == 2
    assert args[0]["id"] == "1"

def test_clear_index_removes_all_docs(rag_instance):
    rag_instance.clear_index()
    rag_instance.client.delete_collection.assert_called_with("soc_alerts")
    rag_instance.client.get_or_create_collection.assert_called_with("soc_alerts")
