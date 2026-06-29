import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from app.logging_config import get_logger
logger = get_logger(__name__)

def build_event_sequences(df: pd.DataFrame, entity_key: str, sequence_len: int = 20) -> list[list[str]]:
    """
    Filter to entity_key, sort chronologically, extract event_action, 
    and construct sliding windows of length sequence_len.
    """
    if df.empty or 'entity_key' not in df.columns:
        return []

    entity_df = df[df['entity_key'] == entity_key]
    if entity_df.empty:
        return []

    if 'timestamp' in entity_df.columns:
        entity_df = entity_df.sort_values('timestamp')
    elif '@timestamp' in entity_df.columns:
        entity_df = entity_df.sort_values('@timestamp')

    if 'event_action' not in entity_df.columns:
        return []

    actions = entity_df['event_action'].fillna("unknown").astype(str).tolist()

    sequences = []
    # Sliding window extraction
    for i in range(len(actions) - sequence_len + 1):
        sequences.append(actions[i:i+sequence_len])

    # Bind residual sequences scaling below max_len threshold
    if len(actions) > 0 and len(actions) < sequence_len:
        sequences.append(actions)

    return sequences

def build_vocab(all_sequences: list[list[str]]) -> dict[str, int]:
    """Map each unique event_action to int. Include PAD=0, UNK=1."""
    vocab = {"<PAD>": 0, "<UNK>": 1}
    idx = 2
    for seq in all_sequences:
        for token in seq:
            if token not in vocab:
                vocab[token] = idx
                idx += 1
    return vocab

def encode_sequence(seq: list[str], vocab: dict[str, int], max_len: int = 20) -> np.ndarray:
    """Pad or truncate to exactly max_len dimensional sequence vectors."""
    encoded = [vocab.get(token, vocab["<UNK>"]) for token in seq]
    if len(encoded) >= max_len:
        encoded = encoded[:max_len]
    else:
        encoded = encoded + [vocab["<PAD>"]] * (max_len - len(encoded))
    return np.array(encoded, dtype=np.int64)

class SequenceLSTM(nn.Module):
    def __init__(self, vocab_size: int):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, 16, padding_idx=0)
        self.lstm = nn.LSTM(16, 32, num_layers=2, batch_first=True)
        self.fc = nn.Linear(32, vocab_size)

    def forward(self, x):
        embedded = self.embedding(x)
        lstm_out, _ = self.lstm(embedded)
        logits = self.fc(lstm_out)
        return logits

class LSTMDetector:
    def __init__(self, vocab: dict[str, int] = None, max_len: int = 20):
        self.vocab = vocab or {"<PAD>": 0, "<UNK>": 1}
        self.max_len = max_len
        self.vocab_size = len(self.vocab)
        self.model = SequenceLSTM(self.vocab_size)
        self.threshold = 0.0

    def train(self, sequences: list[list[str]], epochs=50, lr=1e-3, batch_size=64) -> dict:
        if not sequences:
            raise ValueError("No sequences provided for LSTM training.")

        self.vocab = build_vocab(sequences)
        self.vocab_size = len(self.vocab)
        self.model = SequenceLSTM(self.vocab_size)

        encoded_seqs = [encode_sequence(seq, self.vocab, self.max_len) for seq in sequences]
        X_data = np.array(encoded_seqs)
        X_tensor = torch.tensor(X_data, dtype=torch.long)

        # Sequence shifting: model attempts to predict token t+1 given token t
        inputs = X_tensor[:, :-1]
        targets = X_tensor[:, 1:]

        dataset = TensorDataset(inputs, targets)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        criterion = nn.CrossEntropyLoss(ignore_index=0) # Mask PAD tokens dynamically
        optimizer = optim.Adam(self.model.parameters(), lr=lr)

        self.model.train()
        final_loss = 0.0
        for epoch in range(epochs):
            epoch_loss = 0.0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                logits = self.model(batch_x)
                loss = criterion(logits.reshape(-1, self.vocab_size), batch_y.reshape(-1))
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * batch_x.size(0)
            final_loss = epoch_loss / len(dataset)

        # Post-training: establish the sequence anomaly baseline threshold statically mapping to the 95th Percentile
        self.model.eval()
        scores = self.predict_batch(sequences, raw=True)
        if len(scores) > 0:
            self.threshold = float(np.percentile(scores, 95))
        else:
            self.threshold = 0.0

        return {
            "status": "trained",
            "epochs": epochs,
            "final_loss": final_loss,
            "vocab_size": self.vocab_size,
            "threshold": self.threshold
        }

    def sequence_anomaly_score(self, sequence: list[str]) -> float:
        """Returns 0 to 1 bounded single anomaly sequence inference mapping."""
        score_arr = self.predict_batch([sequence], raw=False)
        return float(score_arr[0])

    def predict_batch(self, sequences: list[list[str]], raw=False) -> np.ndarray:
        """
        Executes native LSTM Sequence bounding evaluating negative log-probabilities.
        Higher outputs correlate to more anomalous sequences.
        """
        self.model.eval()
        encoded = [encode_sequence(seq, self.vocab, self.max_len) for seq in sequences]
        X_tensor = torch.tensor(encoded, dtype=torch.long)

        inputs = X_tensor[:, :-1]
        targets = X_tensor[:, 1:]

        with torch.no_grad():
            logits = self.model(inputs)
            log_probs = nn.functional.log_softmax(logits, dim=-1)

            batch_size, seq_len, vocab_size = logits.shape

            flat_targets = targets.reshape(-1)
            flat_log_probs = log_probs.reshape(batch_size * seq_len, vocab_size)

            # Isolate exact log_prob probability arrays bound directly to the actual target labels
            target_log_probs = flat_log_probs[torch.arange(batch_size * seq_len), flat_targets]
            target_log_probs = target_log_probs.reshape(batch_size, seq_len)

            mask = (targets != 0).float()
            sum_log_probs = torch.sum(target_log_probs * mask, dim=1)
            valid_tokens = torch.sum(mask, dim=1)
            valid_tokens = torch.clamp(valid_tokens, min=1.0)

            # Negate scaling probabilities mapping inverse likelihood to raw anomaly bound
            avg_neg_log_prob = - (sum_log_probs / valid_tokens)
            raw_scores = avg_neg_log_prob.numpy()

        if raw:
            return raw_scores

        # Normalize bounds safely isolating to maximum 1.0 boundary caps
        if self.threshold <= 0:
            scores = np.zeros_like(raw_scores)
        else:
            scores = raw_scores / self.threshold
        return np.clip(scores, 0.0, 1.0)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "model_state": self.model.state_dict(),
            "vocab": self.vocab,
            "max_len": self.max_len,
            "threshold": self.threshold
        }
        torch.save(state, path)

    @classmethod
    def load(cls, path: str) -> "LSTMDetector":
        state = torch.load(path, map_location=torch.device('cpu'))
        instance = cls(vocab=state["vocab"], max_len=state["max_len"])
        instance.model.load_state_dict(state["model_state"])
        instance.threshold = state["threshold"]
        instance.model.eval()
        return instance

def train_lstm(normalized_logs_df: pd.DataFrame) -> LSTMDetector | None:
    import mlflow

    from app.config import settings

    mlflow.set_experiment("soc-anomaly-detection")

    with mlflow.start_run():
        if normalized_logs_df.empty or 'entity_key' not in normalized_logs_df.columns:
            logger.warning("Empty dataframe or missing entity_key. Cannot train LSTM.")
            return None

        all_sequences = []
        for entity_key in normalized_logs_df['entity_key'].unique():
            seqs = build_event_sequences(normalized_logs_df, entity_key, sequence_len=20)
            all_sequences.extend(seqs)

        if not all_sequences:
            logger.warning("No sequences extracted across entity_keys. Cannot train LSTM.")
            return None

        start_time = time.time()
        detector = LSTMDetector(max_len=20)
        train_stats = detector.train(all_sequences, epochs=50, lr=1e-3)
        train_time = time.time() - start_time

        mlflow.log_params({
            "model_type": "LSTM",
            "sequence_len": 20,
            "vocab_size": train_stats["vocab_size"],
            "epochs": train_stats["epochs"]
        })
        mlflow.log_metrics({
            "final_loss": train_stats["final_loss"],
            "threshold": train_stats["threshold"],
            "train_time": train_time
        })

        # Saves explicitly via generic torch.save dicts mapped identically to requested path requirements
        model_path = os.path.join(settings.MODEL_DIR, "lstm_detector.pkl")
        detector.save(model_path)

        logger.info(f"LSTM trained in {train_time:.2f}s, vocab_size={train_stats['vocab_size']}, saved to {model_path}.")
        return detector
