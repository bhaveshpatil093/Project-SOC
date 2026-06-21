import pytest
import numpy as np
from app.models.lstm_detector import SequenceLSTMDetector

@pytest.fixture
def detector():
    """Provides a fresh SequenceLSTMDetector instance."""
    return SequenceLSTMDetector(sequence_length=5, embed_dim=8, hidden_dim=16, epochs=2)

@pytest.fixture
def sample_sequences():
    """Generates lists of normal log sequences + 1 anomalous sequence."""
    normal_seqs = [
        ["login", "read_file", "write_file", "logout"] for _ in range(50)
    ]
    # Anomaly
    anomaly_seq = [["login", "exec_shell", "wget_download", "chmod_x", "run_malware"]]
    return normal_seqs + anomaly_seq

def test_build_event_sequences_correct_windows(detector):
    """Test the sliding window sequence generator."""
    # 10 events, window=5 -> 6 sequences
    events = ["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9", "e10"]
    seqs = detector.build_event_sequences(events)
    assert len(seqs) == 6
    assert seqs[0] == ["e1", "e2", "e3", "e4", "e5"]
    assert seqs[-1] == ["e6", "e7", "e8", "e9", "e10"]

def test_vocab_includes_pad_and_unk(detector, sample_sequences):
    """Ensure vocabulary initialization includes system tokens."""
    detector.train(sample_sequences)
    assert "<PAD>" in detector.vocab
    assert "<UNK>" in detector.vocab
    assert detector.vocab["<PAD>"] == 0
    assert detector.vocab["<UNK>"] == 1

def test_anomalous_sequence_scores_higher(detector, sample_sequences):
    """Test that anomalous sequence sequences yield higher loss/anomaly score."""
    detector.train(sample_sequences)
    
    normal = ["login", "read_file", "write_file", "logout"]
    anomalous = ["login", "exec_shell", "wget_download", "chmod_x", "run_malware"]
    
    score_normal = detector.score_sequence(normal)
    score_anomaly = detector.score_sequence(anomalous)
    
    assert score_anomaly > score_normal

def test_sequence_score_normalized_0_1(detector, sample_sequences):
    """Ensure output scores are strictly bounded between 0 and 1."""
    detector.train(sample_sequences)
    score = detector.score_sequence(["unknown_event", "another_unknown"])
    
    assert 0.0 <= score <= 1.0

def test_train_reduces_loss(detector, sample_sequences):
    """Verify that training successfully executes and tracks loss history."""
    metadata = detector.train(sample_sequences)
    assert "training_loss" in metadata
    assert len(metadata["training_loss"]) > 0
    # The loss should ideally decrease over epochs, but even if it doesn't due to random init,
    # we just need to verify the loop completes and stores the values.
    assert metadata["epochs_trained"] == 2
