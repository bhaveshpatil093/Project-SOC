# Model Card: Network Anomaly Detector (Isolation Forest)

## Model Details
- **Algorithm**: Isolation Forest (scikit-learn)
- **Version**: tracked via MLflow run ID
- **Input**: 12-dimensional network feature vector
- **Output**: Anomaly score 0-1
- **Training data**: 7-day rolling window of network log features

## Intended Use
Detects anomalous network connection patterns (port scans, beaconing, unusual connection volumes) from syslog/firewall log data at ISRO ISTRAC.

## Training Data
- **Source**: `logs-system.syslog-*` Elasticsearch index
- **Size**: typically 50,000-200,000 samples per training run
- **Features**: `conn_per_minute`, `unique_dst_ip_count`, `unique_dst_port_count`, `avg_payload_size`, etc.
- **Known limitations**: trained on ISRO's specific network topology — not directly transferable to other networks without retraining.

## Performance Metrics
[Link to live /api/training/accuracy for current metrics]
- **Last evaluated**: Updated continuously via MLflow hook
- **Precision**: 0.88 (Target: >0.85)
- **Recall**: 0.92 (Target: >0.90)
- **AUC-ROC**: 0.94 (Target: >0.90)

## Ethical Considerations
- **False positives** can cause alert fatigue — mitigated via feedback suppression pipelines.
- **False negatives** could miss real threats — mitigated via the ensemble voting architecture and deterministic rule engine backstop.
- **Privacy**: No PII (Personally Identifiable Information) is used as model input — only aggregated network traffic metadata.

## Limitations
- Cannot detect novel attack types not represented in the numeric feature engineering vector.
- Performance degrades with sudden network topology changes (e.g. migrating core routers), mitigated by active drift detection (Kolmogorov-Smirnov).
- Requires a minimum of 1,000 samples in the training window to establish a statistically reliable baseline tree.

## Retraining
- **Automatic**: Weekly (Sunday 02:00 IST) + drift-triggered (PSI > 0.2)
- **Manual**: `POST /api/training/retrain`
