import os
import logging
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from app.config import settings
from app.features.feature_merger import scale_features, load_scaler
from app.models.isolation_forest import IsolationForestDetector, NETWORK_FEATURE_COLS
from app.models.autoencoder import AutoencoderDetector, PROCESS_FEATURE_COLS
from app.models.lstm_detector import LSTMDetector, build_event_sequences
from app.models.rule_engine import evaluate_rules, get_rule_explanation

logger = logging.getLogger(__name__)

@dataclass
class ScoringResult:
    entity_key: str
    window_bucket: str
    network_anomaly_score: float
    process_anomaly_score: float
    sequence_anomaly_score: float
    rule_score: float
    triggered_rules: list[str]
    mitre_tactics: list[str]
    mitre_technique_ids: list[str]
    threat_score: float
    threat_level: str
    top_features: list[str] = field(default_factory=list)
    human_explanation: str = ""

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance.if_detector = None
            cls._instance.ae_detector = None
            cls._instance.lstm_detector = None
            cls._instance.net_scaler = None
            cls._instance.proc_scaler = None
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        """Loads all detectors. If missing, applies graceful degradation bounding components."""
        if self._initialized:
            return
            
        logger.info("Initializing ModelManager: loading ML models.")
        
        if_path = os.path.join(settings.MODEL_DIR, "isolation_forest.pkl")
        if os.path.exists(if_path):
            self.if_detector = IsolationForestDetector.load(if_path)
            self.net_scaler = load_scaler(os.path.join(settings.MODEL_DIR, "network_scaler.pkl"))
            logger.info("IsolationForest model loaded.")
        else:
            logger.warning("IsolationForest model not found. Graceful degradation active.")

        ae_path = os.path.join(settings.MODEL_DIR, "autoencoder.pt")
        if os.path.exists(ae_path):
            self.ae_detector = AutoencoderDetector.load(ae_path)
            self.proc_scaler = load_scaler(os.path.join(settings.MODEL_DIR, "process_scaler.pkl"))
            logger.info("Autoencoder model loaded.")
        else:
            logger.warning("Autoencoder model not found. Graceful degradation active.")

        lstm_path = os.path.join(settings.MODEL_DIR, "lstm_detector.pkl")
        if os.path.exists(lstm_path):
            self.lstm_detector = LSTMDetector.load(lstm_path)
            logger.info("LSTM Sequence model loaded.")
        else:
            logger.warning("LSTM Sequence model not found. Graceful degradation active.")
            
        self._initialized = True

    def score_entity(self, feature_row: dict, event_sequences: list[list[str]] = None) -> ScoringResult:
        """Executes targeted unified ML inference aggregating isolated scores mapped sequentially into a weighted ensemble framework."""
        net_score = 0.0
        proc_score = 0.0
        seq_score = 0.0
        
        # 1. Network IF scoring
        if self.if_detector and self.net_scaler:
            raw_net_vec = np.array([float(feature_row.get(c, 0.0)) for c in NETWORK_FEATURE_COLS]).reshape(1, -1)
            scaled_net_vec = scale_features(raw_net_vec, self.net_scaler)
            net_score = self.if_detector.score_single(scaled_net_vec.flatten())
            
        # 2. Process Autoencoder scoring
        if self.ae_detector and self.proc_scaler:
            raw_proc_vec = np.array([float(feature_row.get(c, 0.0)) for c in PROCESS_FEATURE_COLS]).reshape(1, -1)
            scaled_proc_vec = scale_features(raw_proc_vec, self.proc_scaler)
            proc_score = self.ae_detector.score_single(scaled_proc_vec.flatten())
            
        # 3. Sequence LSTM scoring
        if self.lstm_detector and event_sequences:
            scores = [self.lstm_detector.sequence_anomaly_score(seq) for seq in event_sequences]
            seq_score = float(max(scores)) if scores else 0.0
            
        # 4. Deterministic Rule Engine Scoring
        rule_eval = evaluate_rules(feature_row)
        rule_score = rule_eval["rule_score"]
        
        # Determine active analytical layers
        weights = {"network": 0.25, "process": 0.35, "sequence": 0.15, "rule": 0.25}
        active_models = ["rule"]
        if self.if_detector: active_models.append("network")
        if self.ae_detector: active_models.append("process")
        if self.lstm_detector: active_models.append("sequence")
        
        # Graceful weight redistribution logic
        inactive = set(weights.keys()) - set(active_models)
        total_inactive_weight = sum(weights[m] for m in inactive)
        
        for m in inactive:
            weights[m] = 0.0
            
        if total_inactive_weight > 0 and len(active_models) > 0:
            redist = total_inactive_weight / len(active_models)
            for m in active_models:
                weights[m] += redist
                
        threat_score = (
            weights["network"] * net_score +
            weights["process"] * proc_score +
            weights["sequence"] * seq_score +
            weights["rule"] * rule_score
        )
        
        if threat_score < 0.3:
            threat_level = "low"
        elif threat_score < 0.6:
            threat_level = "medium"
        elif threat_score < 0.8:
            threat_level = "high"
        else:
            threat_level = "critical"
            
        return ScoringResult(
            entity_key=str(feature_row.get("entity_key", "unknown")),
            window_bucket=str(feature_row.get("window_bucket", "unknown")),
            network_anomaly_score=net_score,
            process_anomaly_score=proc_score,
            sequence_anomaly_score=seq_score,
            rule_score=rule_score,
            triggered_rules=[r.rule_id for r in rule_eval["triggered_rules"]],
            mitre_tactics=rule_eval["mitre_tactics"],
            mitre_technique_ids=rule_eval["mitre_techniques"],
            threat_score=float(threat_score),
            threat_level=threat_level,
            top_features=[], # Feature importance attribution loaded selectively down-range via SHAP explainer
            human_explanation=get_rule_explanation(rule_eval["triggered_rules"])
        )

    async def score_all_entities(self, feature_df: pd.DataFrame, normalized_df: pd.DataFrame) -> list[ScoringResult]:
        """Pushes massive Pandas datasets extracting chronological execution boundaries per-entity inside parallel ML evaluations."""
        if feature_df.empty:
            return []
            
        results = []
        for _, row in feature_df.iterrows():
            row_dict = row.to_dict()
            entity_key = row_dict.get("entity_key")
            seqs = []
            if not normalized_df.empty and entity_key:
                seqs = build_event_sequences(normalized_df, entity_key, sequence_len=20)
                
            res = self.score_entity(row_dict, seqs)
            results.append(res)
            
        return results

    async def train_all_models(self, feature_df: pd.DataFrame, normalized_df: pd.DataFrame):
        """Orchestrates comprehensive cross-system local training loops executing isolation forests, autoencoders, and LSTMs!"""
        from app.models.isolation_forest import train_isolation_forest
        from app.models.autoencoder import train_autoencoder
        from app.models.lstm_detector import train_lstm
        
        logger.info("Initiating model training for all ML detectors.")
        self.if_detector = train_isolation_forest(feature_df)
        self.ae_detector = train_autoencoder(feature_df)
        self.lstm_detector = train_lstm(normalized_df)
        
        self.net_scaler = load_scaler(os.path.join(settings.MODEL_DIR, "network_scaler.pkl"))
        self.proc_scaler = load_scaler(os.path.join(settings.MODEL_DIR, "process_scaler.pkl"))
        
        logger.info("All ML models trained and loaded successfully into ModelManager.")

def get_model_manager() -> ModelManager:
    """Injectable globally scoped dependency mapping retrieving the orchestration ModelManager logic!"""
    return ModelManager()
