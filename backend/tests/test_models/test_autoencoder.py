import pytest
import numpy as np
import pandas as pd
from app.models.autoencoder import AutoencoderDetector

@pytest.fixture
def detector():
    """Provides a fresh AutoencoderDetector instance."""
    return AutoencoderDetector(hidden_dims=[16, 8], epochs=5)

@pytest.fixture
def sample_data():
    """Generates synthetic data: normal cluster + 1 anomaly."""
    # 200 normal samples, 10 features
    normal = np.random.normal(0, 0.5, (200, 10))
    # 1 anomalous sample far from distribution
    anomaly = np.random.normal(10, 1.0, (1, 10))
    df = pd.DataFrame(np.vstack([normal, anomaly]), columns=[f"f_{i}" for i in range(10)])
    return df

def test_reconstruction_error_higher_for_anomalies(detector, sample_data):
    """Ensure the model struggles to reconstruct anomalous data."""
    detector.train(sample_data)
    
    # Extract normal and anomaly
    normal_sample = sample_data.iloc[[0]].to_dict(orient="records")[0]
    anomaly_sample = sample_data.iloc[[-1]].to_dict(orient="records")[0]
    
    normal_score = detector.score_single(normal_sample)
    anomaly_score = detector.score_single(anomaly_sample)
    
    assert anomaly_score > normal_score
    # Anomaly should be close to 1.0, normal should be lower
    assert anomaly_score > 0.8
    assert normal_score < 0.5

def test_threshold_set_at_correct_percentile(detector, sample_data):
    """Check that the dynamic threshold aligns with the 95th percentile."""
    metadata = detector.train(sample_data)
    threshold = detector.threshold
    
    # Calculate reconstruction errors for training data
    import torch
    detector.model.eval()
    X = detector.scaler.transform(sample_data)
    tensor_X = torch.FloatTensor(X)
    with torch.no_grad():
        reconstructed = detector.model(tensor_X)
        errors = torch.mean((tensor_X - reconstructed) ** 2, dim=1).numpy()
    
    p95 = np.percentile(errors, 95)
    assert pytest.approx(threshold, 0.01) == p95

def test_early_stopping_halts_training(sample_data):
    """Test that early stopping interrupts training before max epochs."""
    # Intentionally set high patience and epochs
    detector = AutoencoderDetector(hidden_dims=[8], epochs=1000, patience=2)
    # Give it very little data so it overfits quickly
    metadata = detector.train(sample_data.head(20))
    
    # Should stop long before 1000 epochs
    assert metadata["epochs_trained"] < 100

def test_predict_caps_at_1_0(detector, sample_data):
    """Test that extreme anomalies do not result in scores > 1.0."""
    detector.train(sample_data)
    
    # Create extreme anomaly
    extreme = {f"f_{i}": 9999.0 for i in range(10)}
    score = detector.score_single(extreme)
    
    assert score <= 1.0
    assert score >= 0.99

def test_save_load_cycle(detector, sample_data, tmp_path):
    """Verify weights and scaler parameters persist across save/load."""
    detector.train(sample_data)
    
    # Save
    save_path = tmp_path / "test_ae"
    detector.save(str(save_path))
    
    # Load
    new_detector = AutoencoderDetector()
    new_detector.load(str(save_path))
    
    # Test identical scoring
    sample = sample_data.iloc[[0]].to_dict(orient="records")[0]
    score1 = detector.score_single(sample)
    score2 = new_detector.score_single(sample)
    
    assert score1 == score2
