from dataclasses import dataclass

import numpy as np

from app.logging_config import get_logger
logger = get_logger(__name__)

@dataclass
class FeatureChange:
    feature_name: str
    original_value: float
    counterfactual_value: float
    direction: str
    change_magnitude: float
    human_readable: str

@dataclass
class CounterfactualResult:
    original_score: float
    counterfactual_score: float
    changes_needed: list[FeatureChange]
    is_feasible: bool
    confidence: float

class CounterfactualExplainer:
    def __init__(self, isolation_forest_detector=None, autoencoder_detector=None, feature_names: list[str] = None, score_threshold: float = 0.5):
        self.if_detector = isolation_forest_detector
        self.ae_detector = autoencoder_detector
        self.feature_names = feature_names or []
        self.score_threshold = score_threshold

        # Determine global baseline for all features. In a robust system, this comes from training data medians.
        # Here we default to 0.0 for anomalies, as 0 typically indicates baseline non-activity in scaled features.
        self.feature_medians = dict.fromkeys(self.feature_names, 0.0)

    def _predict_score(self, x: np.ndarray) -> float:
        """Helper to get a composite threat score for a given feature vector."""
        if self.if_detector and self.ae_detector:
            try:
                # We assume x is [1, num_features] scaled
                if_score = self.if_detector.predict(x)[0]
                ae_score = self.ae_detector.predict(x)[0]
                return float((0.5 * if_score) + (0.5 * ae_score))
            except Exception:
                return 1.0
        elif self.if_detector:
            return float(self.if_detector.predict(x)[0])
        elif self.ae_detector:
            return float(self.ae_detector.predict(x)[0])
        return 0.0

    def _find_counterfactual(self, x: np.ndarray, target_score: float, max_changes: int = 3) -> tuple[np.ndarray, list[int]]:
        """Greedy perturbation algorithm."""
        x_cf = x.copy().astype(float)
        current_score = self._predict_score(x_cf)
        changed_indices = []

        for _ in range(max_changes):
            if current_score <= target_score:
                break

            best_improvement = 0
            best_feature_idx = -1
            best_candidate_x = None

            # Try perturbing each feature not yet changed
            for i in range(x_cf.shape[1]):
                if i in changed_indices:
                    continue

                # Perturb to baseline (median)
                temp_x = x_cf.copy()
                baseline_val = 0.0  # Assumed baseline
                if abs(temp_x[0, i] - baseline_val) < 1e-4:
                    continue  # Already at baseline

                temp_x[0, i] = baseline_val
                new_score = self._predict_score(temp_x)

                improvement = current_score - new_score
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_feature_idx = i
                    best_candidate_x = temp_x.copy()

            if best_feature_idx != -1 and best_improvement > 0.01:
                x_cf = best_candidate_x
                current_score -= best_improvement
                changed_indices.append(best_feature_idx)
            else:
                break

        return x_cf, changed_indices

    def generate_counterfactual(self, feature_row: dict, current_score: float, max_changes: int = 3) -> CounterfactualResult:
        if current_score < self.score_threshold:
            return CounterfactualResult(current_score, current_score, [], True, 1.0)

        if not self.feature_names:
            return CounterfactualResult(current_score, current_score, [], False, 0.0)

        # Build raw vector
        x_raw = np.array([float(feature_row.get(f, 0.0)) for f in self.feature_names]).reshape(1, -1)

        # Calculate counterfactual
        x_cf, changed_indices = self._find_counterfactual(x_raw, target_score=self.score_threshold - 0.1, max_changes=max_changes)

        new_score = self._predict_score(x_cf)

        changes = []
        for idx in changed_indices:
            feat = self.feature_names[idx]
            orig_val = float(x_raw[0, idx])
            new_val = float(x_cf[0, idx])
            direction = "decreased" if new_val < orig_val else "increased"
            magnitude = abs(orig_val - new_val)

            # Format nicely
            orig_fmt = f"{orig_val:.1f}" if orig_val % 1 != 0 else f"{int(orig_val)}"
            new_fmt = f"{new_val:.1f}" if new_val % 1 != 0 else f"{int(new_val)}"

            human_readable = f"{feat} {direction} from {orig_fmt} to {new_fmt}"

            changes.append(FeatureChange(
                feature_name=feat,
                original_value=orig_val,
                counterfactual_value=new_val,
                direction=direction,
                change_magnitude=magnitude,
                human_readable=human_readable
            ))

        is_feasible = new_score < self.score_threshold
        confidence = 0.9 if is_feasible else 0.4

        return CounterfactualResult(
            original_score=current_score,
            counterfactual_score=new_score,
            changes_needed=changes,
            is_feasible=is_feasible,
            confidence=confidence
        )

    def format_counterfactual(self, result: CounterfactualResult) -> str:
        if not result.changes_needed:
            return ""

        lines = ["This alert would be BENIGN if:"]
        for i, change in enumerate(result.changes_needed, 1):
            action = "reduce" if change.direction == "decreased" else "increase"
            lines.append(f"  {i}. {change.human_readable}")
            lines.append(f"     ({action} activity related to {change.feature_name})")

        if not result.is_feasible:
            lines.append("\nNote: Even with these changes, the anomaly score remains elevated.")

        return "\n".join(lines)
