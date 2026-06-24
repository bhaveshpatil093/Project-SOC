# Model Governance Policy

This document outlines the strict governance protocols managing the lifecycle, bias auditing, and deployment of machine learning algorithms within the ISRO SOC Platform.

## 1. Model Lifecycle

The lifecycle of any Unsupervised or Generative model must adhere strictly to the following progression:

1. **Development**: Feature engineering and hyperparameter tuning occur locally against anonymized snapshots of `soc-feature-vectors`.
2. **Validation**: The model must exceed baseline accuracy metrics (Precision > 0.85, Recall > 0.90) against a 30-day historical holdout dataset.
3. **Staging**: Deployed silently in "Shadow Mode." It receives live ingestion data and generates scores, but its scores are **not** routed to the Analyst Dashboard.
4. **Production**: Active deployment. Alerts are routed to Tier 1 analysts.
5. **Monitoring**: Continuous tracking via MLflow. Drift detectors (e.g., Kolmogorov-Smirnov metrics) measure the divergence between inference traffic and the training baseline.
6. **Retirement**: Forced expiration of model artifacts after 90 days, mandating a full retrain to prevent catastrophic long-term drift.

## 2. Approval Process for Model Updates

### Weekly Unsupervised Retraining
The `IsolationForest` and `Autoencoder` models are designed to learn business rhythms autonomously.
- **Approval**: Pre-approved and automated via `APScheduler` (Sunday 02:00 AM).
- **Gate**: The new model is automatically benchmarked against the `backend/tests/regression/golden_dataset.py`. If the golden scenarios fail to score accurately, the deployment is aborted, and the previous week's model remains active.

### Generative AI / SLM Fine-Tuning
The Phi-3-mini SLM dictates analyst directives and requires strict oversight.
- **Approval**: Requires manual sign-off from the Lead ML Architect and the SOC Operations Lead.
- **Gate**: The `test_slm_quality.py` suite must demonstrate a hallucination rate of < 3% and zero regressions on the primary ISRO policy prompt benchmarks.

## 3. Rollback Procedure

If a deployed model begins misclassifying benign traffic (causing an alert storm) or missing known true positives:
1. Identify the previous successful run ID via the MLflow UI (`http://localhost:5000`).
2. Utilize the fallback API route to forcefully revert the pointer:
   ```bash
   curl -X POST http://localhost:8000/api/admin/models/rollback \
     -d '{"model_name": "isolation_forest", "run_id": "<PREVIOUS_ID>"}'
   ```
3. The `ModelManager` immediately hot-swaps the `.pkl` / `.pt` files without requiring an API restart.

## 4. Bias and Fairness Considerations

Machine learning models within security contexts are susceptible to bias, particularly regarding user-based anomaly detection.
- **Audit Process**: Every quarter, an automated script evaluates false positive rates segmented by `entity_key` subsets (e.g., Engineering vs. HR domains).
- **Mitigation**: If the system is found to systematically over-flag specific departments due to their unique operational software, custom exclusion rules are injected into the Rule Engine, and their specific baseline feature weightings are recalibrated in the training sets.

## 5. Audit Trail

All AI-driven decisions are forensically tracked.
- **MLflow DB**: The `data/mlflow.db` SQLite database permanently archives every training run, logging hyperparameter sets, resulting AUC-ROC metrics, and the precise Git commit hash active during training.
- **ES Audit Logs**: The `soc-audit-logs` Elasticsearch index immutably records any API request that manually retrains, rolls back, or modifies model parameters, tracking the executing Admin user and their IP address.
