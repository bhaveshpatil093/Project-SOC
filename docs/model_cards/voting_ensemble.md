# Model Card: Voting Ensemble (Threat Engine)

## Model Details
- **Architecture**: Weighted Dynamic Voting Ensemble
- **Version**: N/A (Maintained directly in source control)
- **Input**: Raw unnormalized anomaly scores from Isolation Forest (0-1), Autoencoder (0-1), and LSTM (0-1), plus boolean Rule Engine triggers.
- **Output**: Final Normalized Threat Score (0.0 to 1.0)
- **Training data**: N/A (Rule-based weights)

## Intended Use
Consolidates the fragmented predictions of the underlying unsupervised models into a single, cohesive threat probability score. This prevents analysts from having to interpret multiple disparate probability distributions for a single event.

## Aggregation Logic
- **Isolation Forest Weight**: `0.40`
- **Autoencoder Weight**: `0.40`
- **LSTM Weight**: `0.20`
- **Rule Trigger Modifier**: `+0.50` (forces the score into High/Critical instantly)

## Performance Metrics
- **Calibration Error**: Evaluated weekly to ensure that a score of 0.8 actually corresponds to an 80% True Positive probability in historical datasets.
- **Target Distribution**: Designed to funnel 95% of traffic into the <0.3 (Low) bucket, ensuring that High/Critical alerts remain sparse.

## Ethical Considerations
- **Masking**: A poorly performing sub-model (e.g. LSTM experiencing severe drift) could artificially suppress or inflate the ensemble score. 

## Limitations
- Static weights mean the ensemble cannot dynamically down-vote a sub-model that is currently undergoing statistical drift.

## Retraining
- **Automatic**: None.
- **Manual**: Code-level modification required in `backend/app/models/threat_engine.py`.
