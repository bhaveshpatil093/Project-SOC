import pytest
import time
from unittest.mock import patch, MagicMock
from app.slm.cache import SLMCache, ExactMatchCache, SemanticCache

@pytest.fixture
def cache():
    return SLMCache()

def test_exact_match_cache_hit(cache):
    cache.set("What is this?", "It is an alert", alert_id="1")
    
    ans, ctype = cache.get("What is this?", alert_id="1")
    assert ans == "It is an alert"
    assert ctype == "exact"
    
    stats = cache.exact.get_stats()
    assert stats["hits"] == 1

def test_exact_match_cache_miss_different_question(cache):
    cache.set("What is this?", "It is an alert", alert_id="1")
    
    ans, ctype = cache.get("Who is this?", alert_id="1")
    assert ans is None
    assert ctype == "miss"

@patch("app.slm.cache.time.time")
def test_exact_match_cache_ttl_expiry(mock_time, cache):
    mock_time.return_value = 1000.0
    cache.exact.ttl_seconds = 3600
    cache.set("What is this?", "It is an alert", alert_id="1")
    
    mock_time.return_value = 5000.0
    ans, ctype = cache.get("What is this?", alert_id="1")
    assert ans is None
    assert ctype == "miss"
    assert cache.exact.get_stats()["misses"] >= 1

@patch("app.slm.cache.SentenceTransformer")
def test_semantic_cache_finds_similar_question(mock_st, cache):
    mock_model = MagicMock()
    # Mock embeddings: first store returns [1,0], second get returns [1,0] (perfect match)
    mock_model.encode.side_effect = [[1.0, 0.0], [1.0, 0.0]]
    mock_st.return_value = mock_model
    
    cache.semantic._model = mock_model
    
    cache.semantic.store("What is X?", "X is 1", alert_id="1")
    
    ans = cache.semantic.find_similar("Tell me about X", alert_id="1")
    assert ans == "X is 1"

@patch("app.slm.cache.SentenceTransformer")
def test_semantic_cache_respects_threshold(mock_st, cache):
    mock_model = MagicMock()
    # Store: [1,0]. Search: [0,1]. Dot product = 0. Similarity = 0 (below 0.92)
    mock_model.encode.side_effect = [[1.0, 0.0], [0.0, 1.0]]
    mock_st.return_value = mock_model
    
    cache.semantic._model = mock_model
    cache.semantic.similarity_threshold = 0.92
    
    cache.semantic.store("What is X?", "X is 1", alert_id="1")
    
    ans = cache.semantic.find_similar("Unrelated", alert_id="1")
    assert ans is None

@patch("app.slm.cache.SentenceTransformer")
def test_semantic_cache_different_alert_id_no_match(mock_st, cache):
    mock_model = MagicMock()
    mock_model.encode.return_value = [1.0, 0.0]
    mock_st.return_value = mock_model
    
    cache.semantic._model = mock_model
    
    cache.semantic.store("What is X?", "X is 1", alert_id="1")
    
    ans = cache.semantic.find_similar("What is X?", alert_id="2")
    assert ans is None

@patch("app.slm.cache.SentenceTransformer")
def test_combined_cache_stats_accurate(mock_st, cache):
    mock_model = MagicMock()
    mock_model.encode.side_effect = [[1.0, 0.0], [1.0, 0.0]]
    mock_st.return_value = mock_model
    cache.semantic._model = mock_model
    
    # Miss -> store -> exact hit
    cache.get("Q1", "1")
    cache.set("Q1", "A1", "1")
    cache.get("Q1", "1")
    
    # Semantic hit: different key, but same embedding mocked
    cache.get("Q2", "1")
    
    stats = cache.get_combined_stats()
    assert stats["exact_hits"] == 1
    assert stats["semantic_hits"] == 1
    assert stats["misses"] >= 1
    assert stats["exact_size"] == 1
    assert stats["semantic_size"] == 1
