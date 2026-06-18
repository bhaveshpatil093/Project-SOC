import pandas as pd
import numpy as np

LOLBIN_LIST = {
    "powershell.exe", "cmd.exe", "wscript.exe", "cscript.exe",
    "mshta.exe", "rundll32.exe", "regsvr32.exe", "certutil.exe",
    "bitsadmin.exe", "wmic.exe"
}

SUSPICIOUS_PAIRS = {
    ("winword.exe", "powershell.exe"), 
    ("excel.exe", "cmd.exe"),
    ("outlook.exe", "wscript.exe"), 
    ("explorer.exe", "powershell.exe"),
    ("svchost.exe", "cmd.exe")
}

SUSPICIOUS_KEYWORDS = [
    "invoke-expression", "iex", "bypass", "hidden", "noprofile",
    "encodedcommand", "-enc", "downloadstring", "shellcode", "mimikatz",
    "whoami", "net user", "net localgroup"
]

SHELL_NAMES = {
    "powershell.exe", "cmd.exe", "pwsh.exe", "bash", "sh", "zsh", 
    "wscript.exe", "cscript.exe"
}

def compute_suspicious_cmd_score(commands: list[str]) -> float:
    """Computes the fraction of non-empty command lines containing suspicious keywords."""
    valid_cmds = [str(c).lower() for c in commands if pd.notna(c) and str(c).strip()]
    if not valid_cmds:
        return 0.0
        
    suspicious_count = sum(
        1 for cmd in valid_cmds 
        if any(kw in cmd for kw in SUSPICIOUS_KEYWORDS)
    )
    return float(suspicious_count / len(valid_cmds))

def extract_process_features(df: pd.DataFrame, entity_key: str, window_bucket: str) -> dict:
    """
    Extracts process behavior features from a localized subset mapping to a single window bucket.
    """
    if df.empty:
        return {}
        
    process_spawn_count = len(df)
    
    # Safe series retrieval
    process_names = df['process_name'].dropna().astype(str).str.lower() if 'process_name' in df.columns else pd.Series(dtype=str)
    unique_process_names = int(process_names.nunique())
    
    executables = df['process_executable'].dropna().astype(str).str.lower() if 'process_executable' in df.columns else pd.Series(dtype=str)
    unique_executables = int(executables.nunique())
    
    cmd_lines = df['process_command_line'].tolist() if 'process_command_line' in df.columns else []
    suspicious_cmd_score = compute_suspicious_cmd_score(cmd_lines)
    
    # Encoded payload check
    has_encoded_payload = 0
    encoded_keywords = ["-enc", "-encodedcommand", "base64"]
    for cmd in cmd_lines:
        if pd.notna(cmd) and isinstance(cmd, str):
            cmd_lower = cmd.lower()
            if any(kw in cmd_lower for kw in encoded_keywords):
                has_encoded_payload = 1
                break
                
    # Download cradle check
    has_download_cradle = 0
    download_keywords = ["downloadstring", "wget", "curl", "invoke-webrequest"]
    for cmd in cmd_lines:
        if pd.notna(cmd) and isinstance(cmd, str):
            cmd_lower = cmd.lower()
            if any(kw in cmd_lower for kw in download_keywords):
                has_download_cradle = 1
                break
                
    # LOLBIN usage
    has_lolbin = 1 if any(p in LOLBIN_LIST for p in process_names) else 0
    
    # Parent-child anomaly check
    parent_child_anomaly = 0
    if 'process_name' in df.columns and 'process_parent_name' in df.columns:
        pairs = df[['process_parent_name', 'process_name']].dropna()
        for _, row in pairs.iterrows():
            parent = str(row['process_parent_name']).lower()
            child = str(row['process_name']).lower()
            if (parent, child) in SUSPICIOUS_PAIRS:
                parent_child_anomaly = 1
                break
                
    # From Temp dir check
    from_temp_dir = 0
    temp_keywords = ["temp", "tmp", "appdata\\roaming", "appdata/roaming"]
    for exe in executables:
        if any(kw in exe for kw in temp_keywords):
            from_temp_dir = 1
            break
            
    # Non-interactive shell execution
    non_interactive_shell = 0
    if 'process_interactive' in df.columns and 'process_name' in df.columns:
        mask = (df['process_interactive'] == False) & (df['process_name'].astype(str).str.lower().isin(SHELL_NAMES))
        if mask.any():
            non_interactive_shell = 1
            
    # Standard metrics
    unique_users = int(df['user_name'].nunique(dropna=True) if 'user_name' in df.columns else 0)
    
    args_counts = df['process_args_count'].dropna().astype(float) if 'process_args_count' in df.columns else pd.Series(dtype=float)
    max_args_count = int(args_counts.max()) if not args_counts.empty else 0
    mean_args_count = float(args_counts.mean()) if not args_counts.empty else 0.0
    
    failed_exit_count = 0
    if 'process_exit_code' in df.columns:
        exits = df['process_exit_code'].dropna().astype(float)
        failed_exit_count = int((exits != 0).sum())
        
    unique_event_actions = int(df['event_action'].nunique(dropna=True) if 'event_action' in df.columns else 0)
    
    return {
        "entity_key": entity_key,
        "window_bucket": window_bucket,
        "process_spawn_count": process_spawn_count,
        "unique_process_names": unique_process_names,
        "unique_executables": unique_executables,
        "suspicious_cmd_score": suspicious_cmd_score,
        "has_encoded_payload": has_encoded_payload,
        "has_download_cradle": has_download_cradle,
        "has_lolbin": has_lolbin,
        "parent_child_anomaly": parent_child_anomaly,
        "from_temp_dir": from_temp_dir,
        "non_interactive_shell": non_interactive_shell,
        "unique_users": unique_users,
        "max_args_count": max_args_count,
        "mean_args_count": mean_args_count,
        "failed_exit_count": failed_exit_count,
        "unique_event_actions": unique_event_actions
    }

def extract_all_process_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by (entity_key, window_bucket) and executes the feature mapping.
    Resolves NaN to 0 for statistical normalization.
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    if 'entity_key' not in df.columns or 'window_bucket' not in df.columns:
        return pd.DataFrame()
        
    features_list = []
    grouped = df.groupby(['entity_key', 'window_bucket'])
    
    for (entity_key, window_bucket), group_df in grouped:
        features = extract_process_features(group_df, str(entity_key), str(window_bucket))
        if features:
            features_list.append(features)
            
    result_df = pd.DataFrame(features_list)
    if result_df.empty:
        return result_df
        
    numeric_cols = result_df.select_dtypes(include=[np.number]).columns
    result_df[numeric_cols] = result_df[numeric_cols].fillna(0)
    
    return result_df
