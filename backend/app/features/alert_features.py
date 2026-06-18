import pandas as pd
import numpy as np

MITRE_TACTIC_ENCODE = {
    "Reconnaissance": 0,
    "Resource Development": 1,
    "Initial Access": 2,
    "Execution": 3,
    "Persistence": 4,
    "Privilege Escalation": 5,
    "Defense Evasion": 6,
    "Credential Access": 7,
    "Discovery": 8,
    "Lateral Movement": 9,
    "Collection": 10,
    "Command and Control": 11,
    "Exfiltration": 12,
    "Impact": 13
}

def compute_severity_score(severities: list[str]) -> float:
    """Computes the mean severity score for a list of string severity levels."""
    score_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    scores = []
    
    for s in severities:
        if pd.notna(s) and isinstance(s, str):
            val = score_map.get(s.lower().strip())
            if val is not None:
                scores.append(val)
                
    if not scores:
        return 0.0
        
    return float(sum(scores) / len(scores))

def extract_alert_features(df: pd.DataFrame, entity_key: str, window_bucket: str) -> dict:
    """
    Extracts security alert features mapping directly from normalized SIEM/EDR alerts.
    """
    if df.empty:
        return {}
        
    alert_count = len(df)
    
    risk_scores = df['alert_risk_score'].dropna().astype(float) if 'alert_risk_score' in df.columns else pd.Series(dtype=float)
    max_risk_score = float(risk_scores.max()) if not risk_scores.empty else 0.0
    mean_risk_score = float(risk_scores.mean()) if not risk_scores.empty else 0.0
    
    severities = df['alert_severity'].dropna().astype(str).str.lower() if 'alert_severity' in df.columns else pd.Series(dtype=str)
    critical_alert_count = int((severities == "critical").sum())
    high_alert_count = int((severities == "high").sum())
    
    rule_names = df['alert_rule_name'].dropna().astype(str) if 'alert_rule_name' in df.columns else pd.Series(dtype=str)
    unique_rule_names = int(rule_names.nunique())
    
    statuses = df['alert_workflow_status'].dropna().astype(str).str.lower() if 'alert_workflow_status' in df.columns else pd.Series(dtype=str)
    open_alert_count = int((statuses == "open").sum())
    
    tactics = df['alert_mitre_tactic'].dropna().astype(str) if 'alert_mitre_tactic' in df.columns else pd.Series(dtype=str)
    mitre_tactic_count = int(tactics.nunique())
    
    techniques = df['alert_mitre_technique_id'].dropna().astype(str) if 'alert_mitre_technique_id' in df.columns else pd.Series(dtype=str)
    mitre_technique_count = int(techniques.nunique())
    
    tactics_lower = tactics.str.lower()
    has_execution_tactic = 1 if (tactics_lower == "execution").any() else 0
    has_persistence_tactic = 1 if (tactics_lower == "persistence").any() else 0
    has_exfiltration_tactic = 1 if (tactics_lower == "exfiltration").any() else 0
    has_credential_access = 1 if (tactics_lower == "credential access").any() else 0
    has_lateral_movement = 1 if (tactics_lower == "lateral movement").any() else 0
    
    alert_burst_flag = 1 if alert_count > 10 else 0
    
    top_tactic = ""
    if not tactics.empty:
        mode_t = tactics.mode()
        if not mode_t.empty:
            top_tactic = str(mode_t.iloc[0])
            
    top_technique_id = ""
    if not techniques.empty:
        mode_tech = techniques.mode()
        if not mode_tech.empty:
            top_technique_id = str(mode_tech.iloc[0])
            
    severity_score = compute_severity_score(severities.tolist())
    
    return {
        "entity_key": entity_key,
        "window_bucket": window_bucket,
        "alert_count": alert_count,
        "max_risk_score": max_risk_score,
        "mean_risk_score": mean_risk_score,
        "critical_alert_count": critical_alert_count,
        "high_alert_count": high_alert_count,
        "unique_rule_names": unique_rule_names,
        "open_alert_count": open_alert_count,
        "mitre_tactic_count": mitre_tactic_count,
        "mitre_technique_count": mitre_technique_count,
        "has_execution_tactic": has_execution_tactic,
        "has_persistence_tactic": has_persistence_tactic,
        "has_exfiltration_tactic": has_exfiltration_tactic,
        "has_credential_access": has_credential_access,
        "has_lateral_movement": has_lateral_movement,
        "alert_burst_flag": alert_burst_flag,
        "top_tactic": top_tactic,
        "top_technique_id": top_technique_id,
        "severity_score": severity_score
    }

def extract_all_alert_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by (entity_key, window_bucket) and executes the security alert feature mapping.
    Resolves NaN to 0 for numerical statistical normalization.
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    if 'entity_key' not in df.columns or 'window_bucket' not in df.columns:
        return pd.DataFrame()
        
    features_list = []
    grouped = df.groupby(['entity_key', 'window_bucket'])
    
    for (entity_key, window_bucket), group_df in grouped:
        features = extract_alert_features(group_df, str(entity_key), str(window_bucket))
        if features:
            features_list.append(features)
            
    result_df = pd.DataFrame(features_list)
    if result_df.empty:
        return result_df
        
    numeric_cols = result_df.select_dtypes(include=[np.number]).columns
    result_df[numeric_cols] = result_df[numeric_cols].fillna(0)
    
    return result_df
