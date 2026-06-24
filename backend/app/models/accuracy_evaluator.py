from dataclasses import dataclass
from datetime import datetime
import numpy as np
from typing import List, Dict, Any
from sklearn.metrics import (
    confusion_matrix, roc_curve, auc, precision_recall_curve,
    f1_score, precision_score, recall_score, accuracy_score
)

@dataclass
class EvaluationReport:
    evaluated_at: datetime
    n_samples: int
    # Confusion matrix at default threshold
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    # Per-threshold analysis
    roc_auc: float
    pr_auc: float
    optimal_threshold: float
    threshold_curve: List[Dict[str, float]]
    # Per-model breakdown
    per_model_auc: Dict[str, float]
    # Per-rule breakdown
    per_rule_precision: Dict[str, float]
    # Confidence calibration
    calibration_error: float

class AccuracyEvaluator:
    def __init__(self, default_threshold: float = 0.3):
        self.default_threshold = default_threshold

    async def evaluate_against_feedback(self, es, model_manager) -> EvaluationReport:
        # Fetch labeled feedback
        query = {
            "query": {
                "terms": {
                    "label.keyword": ["TP", "FP", "Benign"]
                }
            },
            "size": 10000
        }
        resp = await es.search(index="soc-analyst-feedback", body=query, ignore_unavailable=True)
        hits = resp.get("hits", {}).get("hits", [])
        
        if len(hits) < 30:
            raise ValueError("Insufficient data: minimum 30 labeled samples required.")

        y_true = []
        y_scores = []
        rule_data = []
        model_scores = {"isolation_forest": [], "autoencoder": []} # Add other models if needed

        # We need the original alert for each feedback to get the score and triggered rules
        # To avoid N+1 queries, we could fetch all alerts with one mget, or just query alerts that match these IDs
        alert_ids = [h["_source"]["alert_id"] for h in hits]
        
        alert_resp = await es.search(index="soc-alerts", body={
            "query": {"terms": {"_id": alert_ids}},
            "size": 10000
        }, ignore_unavailable=True)
        
        alerts_map = {a["_id"]: a["_source"] for a in alert_resp.get("hits", {}).get("hits", [])}

        for h in hits:
            source = h["_source"]
            alert_id = source["alert_id"]
            label = source["label"]
            
            if alert_id not in alerts_map:
                continue
                
            alert = alerts_map[alert_id]
            score = alert.get("threat_score", 0.0)
            
            # Label mapping: TP -> 1, FP/Benign -> 0
            # A 'Benign' might be a true negative (system scored it low, user confirmed it's benign)
            # An 'FP' is the system scoring it high, but user says it's false positive.
            # In either case, the true ground truth label is 0 (not a threat).
            true_label = 1 if label == "TP" else 0
            
            y_true.append(true_label)
            y_scores.append(score)
            
            rules = alert.get("triggered_rules", [])
            rule_data.append({"label": true_label, "rules": rules})
            
            # Extract per-model scores if available
            ml_scores = alert.get("ml_scores", {})
            for model_name in model_scores.keys():
                model_scores[model_name].append(ml_scores.get(model_name, 0.0))

        y_true = np.array(y_true)
        y_scores = np.array(y_scores)

        # Compute confusion matrix
        cm_stats = self.compute_confusion_matrix(y_true, y_scores, self.default_threshold)
        
        # Compute ROC
        roc_stats = self.compute_roc_curve(y_true, y_scores)
        
        # Compute PR
        pr_stats = self.compute_pr_curve(y_true, y_scores)
        
        # Optimal threshold
        optimal_thresh = self.find_optimal_threshold(y_true, y_scores)
        
        # Threshold curve
        threshold_curve = []
        precisions, recalls, thresholds = pr_stats["precisions"], pr_stats["recalls"], pr_stats["thresholds"]
        for p, r, t in zip(precisions[:-1], recalls[:-1], thresholds):
            f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
            threshold_curve.append({
                "threshold": float(t),
                "precision": float(p),
                "recall": float(r),
                "f1": float(f1)
            })

        # Per model AUC
        per_model_auc = {}
        for m_name, m_scores in model_scores.items():
            if len(m_scores) == len(y_true):
                try:
                    per_model_auc[m_name] = float(roc_curve(y_true, np.array(m_scores))[1] if len(np.unique(y_true)) > 1 else 0.0) # Actually auc
                    fpr, tpr, _ = roc_curve(y_true, np.array(m_scores))
                    per_model_auc[m_name] = float(auc(fpr, tpr))
                except:
                    per_model_auc[m_name] = 0.0

        # Per rule precision
        per_rule_precision = self._compute_per_rule_precision(rule_data)
        
        # Calibration error
        ece = self.compute_expected_calibration_error(y_true, y_scores)

        return self.EvaluationReport(
            evaluated_at=datetime.utcnow(),
            n_samples=len(y_true),
            true_positives=cm_stats["TP"],
            false_positives=cm_stats["FP"],
            true_negatives=cm_stats["TN"],
            false_negatives=cm_stats["FN"],
            precision=cm_stats["precision"],
            recall=cm_stats["recall"],
            f1_score=cm_stats["f1_score"],
            accuracy=cm_stats["accuracy"],
            roc_auc=roc_stats["auc"],
            pr_auc=pr_stats["auc"],
            optimal_threshold=optimal_thresh,
            threshold_curve=threshold_curve,
            per_model_auc=per_model_auc,
            per_rule_precision=per_rule_precision,
            calibration_error=ece
        )

    def compute_confusion_matrix(self, y_true: np.ndarray, y_scores: np.ndarray, threshold: float) -> dict:
        y_pred = (y_scores >= threshold).astype(int)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
        else:
            tn, fp, fn, tp = 0, 0, 0, 0
            
        return {
            "TN": int(tn),
            "FP": int(fp),
            "FN": int(fn),
            "TP": int(tp),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
            "accuracy": float(accuracy_score(y_true, y_pred))
        }

    def compute_roc_curve(self, y_true: np.ndarray, y_scores: np.ndarray) -> dict:
        try:
            fpr, tpr, thresholds = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)
        except:
            fpr, tpr, thresholds, roc_auc = [], [], [], 0.0
            
        return {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thresholds.tolist(),
            "auc": float(roc_auc)
        }

    def compute_pr_curve(self, y_true: np.ndarray, y_scores: np.ndarray) -> dict:
        try:
            precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
            pr_auc = auc(recalls, precisions)
        except:
            precisions, recalls, thresholds, pr_auc = [], [], [], 0.0
            
        return {
            "precisions": precisions.tolist(),
            "recalls": recalls.tolist(),
            "thresholds": thresholds.tolist(),
            "auc": float(pr_auc)
        }

    def find_optimal_threshold(self, y_true: np.ndarray, y_scores: np.ndarray) -> float:
        try:
            precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
            f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
            optimal_idx = np.argmax(f1_scores)
            if optimal_idx < len(thresholds):
                return float(thresholds[optimal_idx])
            return 0.3
        except:
            return 0.3

    def compute_per_model_contribution(self, results: list, labels: list[int]) -> dict:
        # Implemented inline in evaluate_against_feedback for simplicity with ES data
        pass

    def compute_expected_calibration_error(self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
        try:
            bins = np.linspace(0., 1., n_bins + 1)
            binids = np.digitize(y_prob, bins) - 1
            
            bin_sums = np.bincount(binids, weights=y_prob, minlength=len(bins))
            bin_true = np.bincount(binids, weights=y_true, minlength=len(bins))
            bin_total = np.bincount(binids, minlength=len(bins))
            
            nonzero = bin_total != 0
            prob_true = bin_true[nonzero] / bin_total[nonzero]
            prob_pred = bin_sums[nonzero] / bin_total[nonzero]
            
            ece = np.sum(np.abs(prob_true - prob_pred) * (bin_total[nonzero] / len(y_true)))
            return float(ece)
        except:
            return 0.0
            
    def _compute_per_rule_precision(self, rule_data: List[Dict]) -> Dict[str, float]:
        rule_stats = {}
        for rd in rule_data:
            label = rd["label"]
            for r in rd["rules"]:
                if r not in rule_stats:
                    rule_stats[r] = {"tp": 0, "total": 0}
                rule_stats[r]["total"] += 1
                if label == 1:
                    rule_stats[r]["tp"] += 1
                    
        return {
            rule: float(stats["tp"] / stats["total"]) 
            for rule, stats in rule_stats.items() 
            if stats["total"] > 0
        }
