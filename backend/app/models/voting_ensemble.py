import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ModelVote:
    model_name: str
    raw_score: float
    weight: float
    weighted_contribution: float
    is_outlier: bool

@dataclass
class EnsembleVote:
    final_score: float
    confidence_interval: tuple[float, float]
    vote_details: dict[str, ModelVote]
    consensus_level: str
    dominant_model: str

class VotingEnsemble:
    def __init__(self):
        pass

    def compute_consensus_level(self, scores: list[float]) -> str:
        if not scores:
            return "strong"
        std = np.std(scores)
        if std < 0.1:
            return "strong"
        if std < 0.2:
            return "moderate"
        if std < 0.35:
            return "weak"
        return "split"

    def compute_confidence_interval(self, scores: list[float], weights: list[float]) -> tuple[float, float]:
        if not scores:
            return (0.0, 0.0)
        # Fast approximation using weighted variance
        weighted_mean = np.average(scores, weights=weights)
        variance = np.average((scores - weighted_mean)**2, weights=weights)
        # Using 1.96 standard errors for approx 95% CI (treating weights sum to 1 as N=len)
        std_err = np.sqrt(variance) / max(1, np.sqrt(len(scores)))
        margin = 1.96 * std_err
        return (max(0.0, float(weighted_mean - margin)), min(1.0, float(weighted_mean + margin)))

    def detect_outlier_model(self, scores: dict[str, float]) -> str | None:
        vals = list(scores.values())
        if len(vals) < 3:
            return None
        mean = np.mean(vals)
        std = np.std(vals)
        if std == 0:
            return None
        for model, score in scores.items():
            if abs(score - mean) > 2 * std:
                return model
        return None

    def vote(self, model_scores: dict[str, float], model_weights: dict[str, float], model_confidences: dict[str, float] = None) -> EnsembleVote:
        scores_list = list(model_scores.values())
        weights_list = [model_weights.get(m, 0.0) for m in model_scores]

        # Normalize weights
        total_w = sum(weights_list)
        if total_w > 0:
            weights_list = [w / total_w for w in weights_list]
        else:
            weights_list = [1.0 / len(scores_list)] * len(scores_list)

        final_score = float(np.average(scores_list, weights=weights_list))

        ci = self.compute_confidence_interval(scores_list, weights_list)
        consensus = self.compute_consensus_level(scores_list)
        outlier = self.detect_outlier_model(model_scores)

        dominant = max(model_scores.keys(), key=lambda m: model_scores[m] * model_weights.get(m, 0.0))

        details = {}
        for idx, (model, score) in enumerate(model_scores.items()):
            w = weights_list[idx]
            details[model] = ModelVote(
                model_name=model,
                raw_score=score,
                weight=w,
                weighted_contribution=score * w,
                is_outlier=(model == outlier)
            )

        return EnsembleVote(
            final_score=final_score,
            confidence_interval=ci,
            vote_details=details,
            consensus_level=consensus,
            dominant_model=dominant
        )

    def get_recommendation(self, vote: EnsembleVote) -> str:
        score = vote.final_score
        consensus = vote.consensus_level

        if score > 0.8 and consensus == "strong":
            return "ESCALATE"
        if score > 0.5 or consensus == "split":
            return "INVESTIGATE"
        if score > 0.3:
            return "MONITOR"
        if consensus == "strong":
            return "SAFE"
        return "MONITOR"
