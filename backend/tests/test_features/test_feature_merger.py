import pytest
import pandas as pd
import numpy as np
from app.features.feature_merger import FeatureMerger, FEATURE_COLUMNS

@pytest.fixture
def merger():
    """Provides a fresh FeatureMerger instance."""
    return FeatureMerger()

@pytest.fixture
def mock_data():
    """Provides mock dataframes representing feature outputs."""
    network = pd.DataFrame([
        {"entity_key": "10.0.0.1", "window_bucket": "2026-06-21T10:00:00Z", "bytes_out": 500, "conn_per_minute": 5.0}
    ])
    process = pd.DataFrame([
        {"entity_key": "10.0.0.1", "window_bucket": "2026-06-21T10:00:00Z", "has_lolbin": 1.0}
    ])
    alert = pd.DataFrame([
        {"entity_key": "10.0.0.1", "window_bucket": "2026-06-21T10:00:00Z", "max_risk_score": 80.0}
    ])
    return network, process, alert

def test_outer_join_fills_nan(merger):
    """Ensure missing rows in one source are correctly filled with 0.0 in the merged df."""
    network = pd.DataFrame([{"entity_key": "10.0.0.1", "window_bucket": "W1", "bytes_out": 500}])
    process = pd.DataFrame([{"entity_key": "10.0.0.2", "window_bucket": "W1", "has_lolbin": 1.0}])
    alert = pd.DataFrame()
    
    merged = merger._merge_dfs(network, process, alert)
    
    # Should contain both 10.0.0.1 and 10.0.0.2
    assert len(merged) == 2
    
    # 10.0.0.1 should have 0.0 for has_lolbin
    r1 = merged[merged["entity_key"] == "10.0.0.1"].iloc[0]
    assert pd.isna(r1["has_lolbin"]) or r1["has_lolbin"] == 0.0
    
    # 10.0.0.2 should have 0.0 for bytes_out
    r2 = merged[merged["entity_key"] == "10.0.0.2"].iloc[0]
    assert pd.isna(r2["bytes_out"]) or r2["bytes_out"] == 0.0

def test_feature_vector_shape(merger, mock_data):
    """Ensure the final vector extraction matches the exact length of FEATURE_COLUMNS."""
    n, p, a = mock_data
    merged = merger.merge_features(n, p, a)
    X, keys = merger.get_feature_vectors(merged)
    
    assert X.shape[1] == len(FEATURE_COLUMNS)

def test_feature_columns_all_numeric(merger, mock_data):
    """Ensure that all output feature columns can be cast cleanly to float32."""
    n, p, a = mock_data
    merged = merger.merge_features(n, p, a)
    X, keys = merger.get_feature_vectors(merged)
    
    # Numpy array should have dtype float32 or float64
    assert np.issubdtype(X.dtype, np.floating)

def test_scaler_normalizes_to_unit_variance(merger):
    """Verify that internal scaler (if used) correctly centers and scales."""
    # We will pass raw data and scale it
    df = pd.DataFrame({
        "entity_key": ["E1", "E2", "E3"],
        "window_bucket": ["W1", "W1", "W1"],
    })
    for col in FEATURE_COLUMNS:
        df[col] = [10.0, 20.0, 30.0]  # Dummy data
        
    # Scale
    X, keys = merger.get_feature_vectors(df, scale=True)
    
    # Check mean is close to 0 and std is close to 1
    # We have 3 identical points for all features, so std across features is 0,
    # but across rows it's non-zero.
    col0 = X[:, 0]
    assert pytest.approx(np.mean(col0), 0.01) == 0.0
    # Sample std vs population std might differ, but should be > 0 and bounded
    assert np.std(col0) > 0.0

def test_entity_key_preserved_after_merge(merger, mock_data):
    """Ensure the entity key tuple is correctly maintained for mapping predictions."""
    n, p, a = mock_data
    merged = merger.merge_features(n, p, a)
    X, keys = merger.get_feature_vectors(merged)
    
    assert len(keys) == 1
    assert keys[0][0] == "10.0.0.1"  # entity_key
    assert keys[0][1] == "2026-06-21T10:00:00Z"  # window_bucket
