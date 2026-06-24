# Model Card: Process Behavior Detector (Autoencoder)

## Model Details
- **Algorithm**: Neural Network Autoencoder (PyTorch)
- **Version**: tracked via MLflow run ID
- **Input**: 14-dimensional process execution feature vector
- **Output**: Reconstruction error (0-1, normalized)
- **Training data**: 7-day rolling window of endpoint process logs

## Intended Use
Detects anomalous "Living off the Land" (LotL) process executions, unauthorized macro executions, and irregular process parent-child relationships across ISRO workstations and servers.

## Training Data
- **Source**: `logs-endpoint.events.process-*` Elasticsearch index
- **Size**: typically 150,000-500,000 samples per training run
- **Features**: `process_tree_depth`, `arg_length_entropy`, `is_system_binary`, `has_network_conn`, `is_encoded_cmd`
- **Known limitations**: Requires a relatively stable baseline of business applications. Sudden rollouts of massive new software packages across the fleet will temporarily cause high reconstruction errors until retrained.

## Performance Metrics
[Link to live /api/training/accuracy for current metrics]
- **Last evaluated**: Updated continuously via MLflow hook
- **Precision**: 0.85 (Target: >0.85)
- **Recall**: 0.94 (Target: >0.90)
- **AUC-ROC**: 0.96 (Target: >0.90)

## Ethical Considerations
- **False positives**: Legitimate IT admin actions (e.g. running deep diagnostic scripts) will often trigger the autoencoder. The system handles this via analyst FP suppression loops.
- **Privacy**: No user file contents are analyzed, only process command-line metadata. 

## Limitations
- Blind to file-less memory injection if it does not spin up a trackable OS-level process.
- Computationally heavier than tree-based models (requires batched inference loops).

## Retraining
- **Automatic**: Weekly (Sunday 02:00 IST) + drift-triggered (PSI > 0.2)
- **Manual**: `POST /api/training/retrain`
