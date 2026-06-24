# Model Card: Sequence Detector (LSTM)

## Model Details
- **Algorithm**: Long Short-Term Memory Neural Network (PyTorch)
- **Version**: tracked via MLflow run ID (Experimental Phase)
- **Input**: Sequence of event actions (categorical integers)
- **Output**: Sequence Perplexity Score (normalized 0-1)
- **Training data**: 7-day rolling window of user/host event sequences

## Intended Use
Identifies advanced persistent threats (APTs) that execute slowly over time by detecting when a sequence of events diverges significantly from a user's historically established operational patterns.

## Training Data
- **Source**: Aggregated logs across all `logs-*` indices grouped by `entity_key`
- **Size**: 20,000+ sequential timelines
- **Features**: Ordered categorical event types (e.g., [Login -> File Share Access -> Zip Command -> SCP Transfer])
- **Known limitations**: Requires at least 14 days of historical data for a specific user to generate a reliable sequential baseline.

## Performance Metrics
[Link to live /api/training/accuracy for current metrics]
- **Last evaluated**: Updated continuously via MLflow hook
- **Precision**: 0.72 (Target: >0.80)
- **Recall**: 0.78 (Target: >0.80)
- **AUC-ROC**: 0.81 (Target: >0.85)

## Ethical Considerations
- **Behavioral Profiling**: This model implicitly tracks behavioral habits of specific users (e.g., standard login hours and typical tool usage). Data is strictly confined to internal ISRO network activity for security purposes only.

## Limitations
- High susceptibility to "vacation drift" — users returning from long absences often trigger sequence anomalies.
- Currently flagged as Experimental in the `ThreatEngine` ensemble; carries a lower weight multiplier (0.5x) compared to IF/AE models.

## Retraining
- **Automatic**: Weekly (Sunday 02:00 IST)
- **Manual**: `POST /api/training/retrain`
