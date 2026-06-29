from datetime import datetime

import numpy as np
import shap

from app.models.model_manager import ScoringResult

from app.logging_config import get_logger
logger = get_logger(__name__)

class ExplainabilityEngine:
    """Orchestrates SHAP analytical mapping identifying key baseline deviations driving Anomaly flags."""

    def explain_network_anomaly(self, X: np.ndarray, feature_names: list[str]) -> dict:
        try:
            from app.models.model_manager import get_model_manager
            mm = get_model_manager()
            if not mm.if_detector:
                raise ValueError("IsolationForest detector not loaded.")

            # Maps natively mapping explicitly onto Sklearn estimators
            explainer = shap.TreeExplainer(mm.if_detector.model)
            shap_values_raw = explainer.shap_values(X)

            # IsolationForest decision limits natively bias towards lower limits for Anomalies.
            # We invert scalar logic natively mapping higher impact onto increased threat signatures.
            shap_values = -np.array(shap_values_raw)

            shap_dict = {}
            top_3 = []

            sv = shap_values[0] if len(shap_values.shape) == 2 else shap_values

            for i, name in enumerate(feature_names):
                shap_dict[name] = float(sv[i])

            # Extract top 3 features pulling anomaly index maximally from centerline
            sorted_indices = np.argsort(np.abs(sv))[::-1][:3]
            for i in sorted_indices:
                val = float(X[0][i]) if len(X.shape) == 2 else float(X[i])
                direction = "increases_risk" if sv[i] > 0 else "decreases_risk"
                top_3.append((feature_names[i], val, direction))

            return {"shap_values": shap_dict, "top_3": top_3}
        except Exception as e:
            logger.warning(f"SHAP explanation failed for network anomaly: {e}")
            return self._fallback_explanation(X, feature_names)

    def explain_process_anomaly(self, X: np.ndarray, feature_names: list[str]) -> dict:
        try:
            from app.models.model_manager import get_model_manager
            mm = get_model_manager()
            if not mm.ae_detector:
                raise ValueError("Autoencoder detector not loaded.")

            # PyTorch Deep Learning Models demand arbitrary KernelExplainer integrations
            background = np.zeros((1, len(feature_names)))

            def predict_fn(x):
                return mm.ae_detector.predict(x)

            explainer = shap.KernelExplainer(predict_fn, background)
            shap_values_raw = explainer.shap_values(X, silent=True)

            if isinstance(shap_values_raw, list):
                sv = shap_values_raw[0][0]
            elif len(shap_values_raw.shape) == 2:
                sv = shap_values_raw[0]
            else:
                sv = shap_values_raw

            shap_dict = {}
            top_3 = []

            for i, name in enumerate(feature_names):
                shap_dict[name] = float(sv[i])

            sorted_indices = np.argsort(np.abs(sv))[::-1][:3]
            for i in sorted_indices:
                val = float(X[0][i]) if len(X.shape) == 2 else float(X[i])
                direction = "increases_risk" if sv[i] > 0 else "decreases_risk"
                top_3.append((feature_names[i], val, direction))

            return {"shap_values": shap_dict, "top_3": top_3}
        except Exception as e:
            logger.warning(f"SHAP explanation failed for process anomaly: {e}")
            return self._fallback_explanation(X, feature_names)

    def _fallback_explanation(self, X: np.ndarray, feature_names: list[str]) -> dict:
        """Graceful degradation fallback identifying pure highest scalar deviations."""
        shap_dict = {}
        top_3 = []
        sv = X[0] if len(X.shape) == 2 else X
        sorted_indices = np.argsort(np.abs(sv))[::-1][:3]

        for i in sorted_indices:
            shap_dict[feature_names[i]] = 0.0
            top_3.append((feature_names[i], float(sv[i]), "increases_risk_fallback"))

        return {"shap_values": shap_dict, "top_3": top_3}

    def get_human_explanation(self, shap_result: dict, rule_result: dict, log_type: str) -> str:
        """Formats comprehensive structured analytical reasoning sentences natively matching payload configurations."""
        top_3 = shap_result.get("top_3", [])
        triggered = rule_result.get("triggered_rules", [])

        parts = []
        for feat, val, direction in top_3:
            parts.append(f"{feat} ({val:.2f})")

        explanation = "Alert triggered because: "
        if parts:
            explanation += ", ".join(parts) + " strongly deviated from baseline."
        else:
            explanation += "multiple complex feature interactions occurred."

        if triggered:
            explanation += f" Additionally, deterministic rules were triggered: {', '.join(triggered)}."

        return explanation

def explain_scoring_result(result: ScoringResult, feature_row: dict, engine: ExplainabilityEngine) -> ScoringResult:
    """Populates tracking elements and language reasoning blocks directly against the scoring output result."""
    from app.models.autoencoder import PROCESS_FEATURE_COLS
    from app.models.isolation_forest import NETWORK_FEATURE_COLS

    log_type = "network"
    shap_res = {}

    # We trace and explain explicitly the model carrying the absolute highest deviation tracking signature!
    if result.network_anomaly_score > result.process_anomaly_score:
        log_type = "network"
        X = np.array([float(feature_row.get(c, 0.0)) for c in NETWORK_FEATURE_COLS]).reshape(1, -1)
        from app.features.feature_merger import scale_features
        from app.models.model_manager import get_model_manager
        mm = get_model_manager()
        if mm.net_scaler:
            X = scale_features(X, mm.net_scaler)
        shap_res = engine.explain_network_anomaly(X, NETWORK_FEATURE_COLS)
    else:
        log_type = "process"
        X = np.array([float(feature_row.get(c, 0.0)) for c in PROCESS_FEATURE_COLS]).reshape(1, -1)
        from app.features.feature_merger import scale_features
        from app.models.model_manager import get_model_manager
        mm = get_model_manager()
        if mm.proc_scaler:
            X = scale_features(X, mm.proc_scaler)
        shap_res = engine.explain_process_anomaly(X, PROCESS_FEATURE_COLS)

    # Counterfactual Explanations
    cf_explanation = ""
    if result.threat_level in ["critical", "high"]:
        from app.models.model_manager import get_model_manager
        from app.scoring.counterfactual import CounterfactualExplainer
        mm = get_model_manager()
        features = NETWORK_FEATURE_COLS if log_type == "network" else PROCESS_FEATURE_COLS
        cf_explainer = CounterfactualExplainer(
            isolation_forest_detector=mm.if_detector,
            autoencoder_detector=mm.ae_detector,
            feature_names=features,
            score_threshold=0.5
        )
        try:
            cf_result = cf_explainer.generate_counterfactual(feature_row, result.threat_score)
            cf_explanation = cf_explainer.format_counterfactual(cf_result)
        except Exception:
            cf_explanation = ""

    rule_res = {"triggered_rules": result.triggered_rules}

    human_exp = engine.get_human_explanation(shap_res, rule_res, log_type)
    top_features = [feat for feat, _, _ in shap_res.get("top_3", [])]

    if result.human_explanation:
        result.human_explanation = human_exp + "\n\n" + result.human_explanation
    else:
        result.human_explanation = human_exp

    result.top_features = top_features
    return result

def build_explanation_context(result: ScoringResult) -> dict:
    """Wraps ML payloads natively into JSON tracking mappings specifically optimized for dynamic LLM injection pipelines."""
    return {
        "entity_key": result.entity_key,
        "threat_score": result.threat_score,
        "threat_level": result.threat_level,
        "top_features": result.top_features,
        "triggered_rules": result.triggered_rules,
        "mitre_tactics": result.mitre_tactics,
        "human_explanation": result.human_explanation,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
