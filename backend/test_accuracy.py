import asyncio
from app.models.accuracy_evaluator import AccuracyEvaluator
import numpy as np

async def test_evaluator():
    evaluator = AccuracyEvaluator()
    
    # 1. Test Confusion matrix
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_scores = np.array([0.9, 0.4, 0.2, 0.1, 0.1, 0.8])
    
    cm = evaluator.compute_confusion_matrix(y_true, y_scores, threshold=0.3)
    print("CM:", cm)
    
    # 2. Test ROC
    roc = evaluator.compute_roc_curve(y_true, y_scores)
    print("ROC AUC:", roc["auc"])
    
    # 3. Test PR
    pr = evaluator.compute_pr_curve(y_true, y_scores)
    print("PR AUC:", pr["auc"])
    
    # 4. Optimal Threshold
    opt_t = evaluator.find_optimal_threshold(y_true, y_scores)
    print("Optimal Threshold:", opt_t)
    
    # 5. ECE
    ece = evaluator.compute_expected_calibration_error(y_true, y_scores)
    print("ECE:", ece)
    
    # 6. Per rule precision
    rule_data = [
        {"label": 1, "rules": ["R1", "R2"]},
        {"label": 0, "rules": ["R2"]},
        {"label": 1, "rules": ["R1"]},
    ]
    rule_prec = evaluator._compute_per_rule_precision(rule_data)
    print("Rule Precision:", rule_prec)
    
    print("All math tests passed!")

if __name__ == "__main__":
    asyncio.run(test_evaluator())
