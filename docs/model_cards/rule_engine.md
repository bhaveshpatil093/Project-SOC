# Model Card: Deterministic Threat Rules (Rule Engine)

## Model Details
- **Algorithm**: Hand-coded Python Regex & Boolean Logic
- **Version**: N/A (Maintained directly in source control)
- **Input**: Full raw JSON log fields (pre-normalization)
- **Output**: Binary Trigger (True/False) + Threat Score Penalty (+0.0 to +1.0)
- **Training data**: N/A

## Intended Use
Acts as the ultimate deterministic backstop to ensure that explicitly known-bad indicators (e.g., "mimikatz", specific CVE exploit strings, restricted admin port access) are always flagged immediately, regardless of what the unsupervised ML models decide.

## Ruleset Maintenance
- **Source**: `backend/app/models/rule_engine.py`
- **Size**: 50+ hand-coded heuristics
- **Features**: Exact string matching, IP CIDR boundaries, regex pattern matching (e.g., base64 encoded PowerShell).

## Performance Metrics
- **Precision**: 0.99 (Rules are highly specific)
- **Recall**: N/A (Rules only catch what they are explicitly coded to catch)
- **Latency**: <5ms per log batch

## Ethical Considerations
- **Exclusion Lists**: Hardcoded exclusion lists exist to prevent critical security scanning infrastructure (e.g., ISRO Qualys scanners) from triggering alerts.

## Limitations
- Completely blind to zero-day attacks or polymorphic threats that slightly modify their execution strings.
- Requires constant manual curation to stay relevant.

## Retraining
- **Automatic**: None.
- **Manual**: Update `RULES` dictionary and deploy code.
