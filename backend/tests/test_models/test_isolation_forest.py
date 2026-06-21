import pytest
import numpy as np
import os
import pandas as pd
from app.models.isolation_forest import IsolationForestDetector

@pytest.fixture
def detector():
    """Fixture providing a fresh IsolationForestDetector instance."""
    return IsolationForestDetector(n_estimators=100, contamination=0.05)

@pytest.fixture
def sample_data():
    """Generate synthetic normal data with one clear anomaly."""
    # 99 normal points around 0
    normal = np.random.normal(0, 0.1, (99, 5))
    # 1 extreme anomalous point
    anomaly = np.array([[10.0, -10.0, 5.0, 15.0, -5.0]])
    return pd.DataFrame(np.vstack([normal, anomaly]), columns=[f"feat_{i}" for i in range(5)])

def test_train_returns_correct_metadata(detector, sample_data):
    """Ensure training returns the correct dict keys."""
    metadata = detector.train(sample_data)
    assert "n_estimators" in metadata
    assert "contamination" in metadata
    assert "feature_names" in metadata
    assert metadata["feature_names"] == list(sample_data.columns)

def test_predict_scores_in_range_0_1(detector, sample_data):
    """Test that anomaly scores are normalized correctly between 0 and 1."""
    detector.train(sample_data)
    scores = detector.predict(sample_data)
    assert len(scores) == 100
    assert all(0.0 <= s <= 1.0 for s in scores)
    
    # The anomaly (last element) should have a high score
    assert scores[-1] > 0.6

def test_score_single_matches_batch(detector, sample_data):
    """Ensure score_single produces same result as predict for a single row."""
    detector.train(sample_data)
    
    # Extract the anomaly row as a dict
    anomaly_dict = sample_data.iloc[-1].to_dict()
    
    # Batch predict
    batch_scores = detector.predict(sample_data)
    anomaly_batch_score = batch_scores[-1]
    
    # Single predict
    single_score = detector.score_single(anomaly_dict)
    
    # Floating point precision might vary slightly, but should be very close
    assert pytest.approx(single_score, 0.001) == anomaly_batch_score

def test_save_and_load_preserves_predictions(detector, sample_data, tmp_path):
    """Verify that serialization and deserialization do not alter model behavior."""
    detector.train(sample_data)
    original_scores = detector.predict(sample_data)
    
    # Save to temp path
    save_path = tmp_path / "test_if.pkl"
    detector.save(str(save_path))
    
    # Load into new instance
    new_detector = IsolationForestDetector()
    new_detector.load(str(save_path))
    
    loaded_scores = new_detector.predict(sample_data)
    np.testing.assert_array_almost_equal(original_scores, loaded_scores)

def test_contamination_affects_anomaly_rate(sample_data):
    """Test that higher contamination leads to higher baseline scores for outliers."""
    detector_low = IsolationForestDetector(contamination=0.01)
    detector_high = IsolationForestDetector(contamination=0.2)
    
    detector_low.train(sample_data)
    detector_high.train(sample_data)
    
    scores_low = detector_low.predict(sample_data)
    scores_high = detector_high.predict(sample_data)
    
    # The sum of scores should be generally higher for higher contamination
    assert np.sum(scores_high) > np.sum(scores_low)
