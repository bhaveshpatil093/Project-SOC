import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

from app.logging_config import get_logger
logger = get_logger(__name__)

PROCESS_FEATURE_COLS = [
    "process_spawn_count",
    "unique_process_names",
    "unique_executables",
    "suspicious_cmd_score",
    "has_encoded_payload",
    "has_download_cradle",
    "has_lolbin",
    "parent_child_anomaly",
    "from_temp_dir",
    "non_interactive_shell",
    "unique_users",
    "max_args_count",
    "mean_args_count",
    "failed_exit_count",
    "unique_event_actions"
]

class SOCAutoencoder(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

class AutoencoderDetector:
    def __init__(self, input_dim: int, threshold_percentile: float = 95.0):
        self.input_dim = input_dim
        self.threshold_percentile = threshold_percentile
        self.model = SOCAutoencoder(input_dim)
        self.threshold = 0.0

    def train(self, X: np.ndarray, epochs=100, lr=1e-3, batch_size=64) -> dict:
        if len(X) < 5:
            # Duplicate array ensuring the 80/20 train_test_split does not crash on extreme edge cases
            logger.warning("Limited samples available. Duplicating tensor to establish holdout baseline.")
            X = np.tile(X, (5, 1))

        X_train, X_val = train_test_split(X, test_size=0.2, random_state=42)

        train_tensor = torch.tensor(X_train, dtype=torch.float32)
        val_tensor = torch.tensor(X_val, dtype=torch.float32)

        train_dataset = TensorDataset(train_tensor, train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        val_dataset = TensorDataset(val_tensor, val_tensor)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=lr)

        best_val_loss = float('inf')
        patience = 10
        patience_counter = 0
        final_epoch = 0
        final_loss = 0.0

        self.model.train()
        for epoch in range(epochs):
            train_loss = 0.0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * batch_x.size(0)

            train_loss /= len(train_loader.dataset)

            # Validation Holdout
            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    outputs = self.model(batch_x)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item() * batch_x.size(0)
            val_loss /= len(val_loader.dataset)
            self.model.train()

            # Early stopping bounds execution dynamically
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                final_loss = val_loss
            else:
                patience_counter += 1

            final_epoch = epoch
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch}. Best val_loss: {best_val_loss:.6f}")
                break

        # Lock in anomaly threshold mapping over the full input sequence array
        self.model.eval()
        with torch.no_grad():
            full_train_tensor = torch.tensor(X, dtype=torch.float32)
            reconstructions = self.model(full_train_tensor)
            mse = torch.mean((full_train_tensor - reconstructions) ** 2, dim=1).numpy()
            self.threshold = float(np.percentile(mse, self.threshold_percentile))

        return {
            "status": "trained",
            "threshold": self.threshold,
            "final_loss": final_loss,
            "epochs": final_epoch + 1
        }

    def reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        """Returns per-sample Mean Squared Error representing the autoencoder anomaly bounds."""
        self.model.eval()
        with torch.no_grad():
            tensor_x = torch.tensor(X, dtype=torch.float32)
            outputs = self.model(tensor_x)
            mse = torch.mean((tensor_x - outputs) ** 2, dim=1).numpy()
        return mse

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Score = error / threshold, safely capped at 1.0 (Highest Anomaly Index)."""
        errors = self.reconstruction_error(X)
        if self.threshold <= 0:
            scores = np.zeros_like(errors)
        else:
            scores = errors / self.threshold
        return np.clip(scores, 0.0, 1.0)

    def score_single(self, feature_vector: np.ndarray) -> float:
        X = feature_vector.reshape(1, -1)
        scores = self.predict(X)
        return float(scores[0])

    def score_batch(self, feature_matrix: np.ndarray) -> np.ndarray:
        return self.predict(feature_matrix)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "model_state": self.model.state_dict(),
            "input_dim": self.input_dim,
            "threshold_percentile": self.threshold_percentile,
            "threshold": self.threshold
        }
        torch.save(state, path)

    @classmethod
    def load(cls, path: str) -> "AutoencoderDetector":
        state = torch.load(path, map_location=torch.device('cpu'))
        instance = cls(input_dim=state["input_dim"], threshold_percentile=state["threshold_percentile"])
        instance.model.load_state_dict(state["model_state"])
        instance.threshold = state["threshold"]
        instance.model.eval()
        return instance

def train_autoencoder(feature_df: pd.DataFrame) -> AutoencoderDetector | None:
    import mlflow

    from app.config import settings
    from app.features.feature_merger import fit_scaler, save_scaler, scale_features

    mlflow.set_experiment("soc-anomaly-detection")

    with mlflow.start_run():
        if feature_df.empty:
            logger.warning("Empty dataframe provided to train_autoencoder. Cannot train.")
            return None

        for col in PROCESS_FEATURE_COLS:
            if col not in feature_df.columns:
                feature_df[col] = 0.0

        X_df = feature_df[PROCESS_FEATURE_COLS].fillna(0)
        X_raw = X_df.values
        input_dim = len(PROCESS_FEATURE_COLS)

        # Deploy localized PyTorch Process scalar bounds
        scaler = fit_scaler(X_raw)
        X_scaled = scale_features(X_raw, scaler)

        scaler_path = os.path.join(settings.MODEL_DIR, "process_scaler.pkl")
        save_scaler(scaler, scaler_path)

        start_time = time.time()
        detector = AutoencoderDetector(input_dim=input_dim)

        train_stats = detector.train(X_scaled)
        train_time = time.time() - start_time

        mlflow.log_params({
            "input_dim": input_dim,
            "epochs_run": train_stats["epochs"],
            "threshold_percentile": detector.threshold_percentile
        })
        mlflow.log_metrics({
            "threshold": detector.threshold,
            "final_loss": train_stats["final_loss"],
            "train_time": train_time
        })

        model_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")
        detector.save(model_path)

        logger.info(f"Autoencoder trained in {train_time:.2f}s and saved to {model_path}.")
        return detector

def load_or_train(feature_df: pd.DataFrame, model_path: str) -> AutoencoderDetector:
    if os.path.exists(model_path):
        logger.info(f"Loading existing Autoencoder model from {model_path}")
        return AutoencoderDetector.load(model_path)
    logger.info(f"Model not found at {model_path}. Training fresh Autoencoder.")
    return train_autoencoder(feature_df)
