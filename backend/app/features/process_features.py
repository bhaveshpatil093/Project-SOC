import numpy as np
import pandas as pd

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

def extract_all_process_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pure pandas vectorized extraction of process features. No python loops over groups.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    if 'entity_key' not in df.columns or 'window_bucket' not in df.columns:
        return pd.DataFrame()

    df = df.copy()

    # Pre-compute column level flags to use in aggregations
    df['process_name_lower'] = df['process_name'].astype(str).str.lower() if 'process_name' in df.columns else ""
    df['process_executable_lower'] = df['process_executable'].astype(str).str.lower() if 'process_executable' in df.columns else ""
    df['process_parent_name_lower'] = df['process_parent_name'].astype(str).str.lower() if 'process_parent_name' in df.columns else ""
    df['cmd_lower'] = df['process_command_line'].astype(str).str.lower() if 'process_command_line' in df.columns else ""

    # Suspicious CMD
    df['is_suspicious_cmd'] = df['cmd_lower'].str.contains('|'.join(SUSPICIOUS_KEYWORDS), regex=True, na=False)
    df['is_valid_cmd'] = df['process_command_line'].notna() & (df['cmd_lower'] != "")

    # Encoded
    df['has_encoded_payload'] = df['cmd_lower'].str.contains('-enc|-encodedcommand|base64', regex=True, na=False)

    # Download Cradle
    df['has_download_cradle'] = df['cmd_lower'].str.contains('downloadstring|wget|curl|invoke-webrequest', regex=True, na=False)

    # Lolbin
    df['has_lolbin'] = df['process_name_lower'].isin(LOLBIN_LIST)

    # Parent-child anomaly
    # Create a Series of tuples
    if 'process_name' in df.columns and 'process_parent_name' in df.columns:
        # Use pandas merge or set intersection. Here, list of tuples vs set.
        # This can be vectorized by checking if the tuple is in the set.
        parent_child_series = pd.Series(list(zip(df['process_parent_name_lower'], df['process_name_lower'])))
        df['parent_child_anomaly'] = parent_child_series.isin(SUSPICIOUS_PAIRS)
    else:
        df['parent_child_anomaly'] = False

    # From temp dir
    df['from_temp_dir'] = df['process_executable_lower'].str.contains('temp|tmp|appdata\\\\roaming|appdata/roaming', regex=True, na=False)

    # Non-interactive shell
    if 'process_interactive' in df.columns and 'process_name' in df.columns:
        df['non_interactive_shell'] = (df['process_interactive'] == False) & df['process_name_lower'].isin(SHELL_NAMES)
    else:
        df['non_interactive_shell'] = False

    # Failed exits
    if 'process_exit_code' in df.columns:
        df['is_failed_exit'] = (df['process_exit_code'].notna()) & (df['process_exit_code'] != 0)
    else:
        df['is_failed_exit'] = False

    # Aggregate
    # For unique counts, use 'nunique'
    # For booleans (has_*), use 'max' (which acts like 'any')
    # For suspicious score, we sum suspicious and divide by sum of valid cmds

    aggs = {
        'entity_key': 'size', # Just to get count
        'process_name': 'nunique' if 'process_name' in df.columns else lambda x: 0,
        'process_executable': 'nunique' if 'process_executable' in df.columns else lambda x: 0,
        'has_encoded_payload': 'max',
        'has_download_cradle': 'max',
        'has_lolbin': 'max',
        'parent_child_anomaly': 'max',
        'from_temp_dir': 'max',
        'non_interactive_shell': 'max',
        'user_name': 'nunique' if 'user_name' in df.columns else lambda x: 0,
        'process_args_count': ['max', 'mean'] if 'process_args_count' in df.columns else [lambda x: 0, lambda x: 0],
        'is_failed_exit': 'sum',
        'event_action': 'nunique' if 'event_action' in df.columns else lambda x: 0,
        'is_suspicious_cmd': 'sum',
        'is_valid_cmd': 'sum'
    }

    grouped = df.groupby(['entity_key', 'window_bucket'])
    res = grouped.agg(aggs)

    # Flatten hierarchical columns if any
    res.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in res.columns.values]

    # Rename mapped columns
    # Depending on how aggs are named:
    # entity_key_size -> process_spawn_count
    # process_name_nunique -> unique_process_names
    # ...

    rename_map = {
        'entity_key_size': 'process_spawn_count',
        'process_name_nunique': 'unique_process_names',
        'process_name_<lambda>': 'unique_process_names',
        'process_executable_nunique': 'unique_executables',
        'process_executable_<lambda>': 'unique_executables',
        'has_encoded_payload_max': 'has_encoded_payload',
        'has_download_cradle_max': 'has_download_cradle',
        'has_lolbin_max': 'has_lolbin',
        'parent_child_anomaly_max': 'parent_child_anomaly',
        'from_temp_dir_max': 'from_temp_dir',
        'non_interactive_shell_max': 'non_interactive_shell',
        'user_name_nunique': 'unique_users',
        'user_name_<lambda>': 'unique_users',
        'process_args_count_max': 'max_args_count',
        'process_args_count_<lambda_0>': 'max_args_count',
        'process_args_count_mean': 'mean_args_count',
        'process_args_count_<lambda_1>': 'mean_args_count',
        'is_failed_exit_sum': 'failed_exit_count',
        'event_action_nunique': 'unique_event_actions',
        'event_action_<lambda>': 'unique_event_actions',
        'is_suspicious_cmd_sum': 'suspicious_cmd_sum',
        'is_valid_cmd_sum': 'valid_cmd_sum'
    }

    res = res.rename(columns=rename_map).reset_index()

    res['suspicious_cmd_score'] = np.where(
        res['valid_cmd_sum'] > 0,
        res['suspicious_cmd_sum'] / res['valid_cmd_sum'],
        0.0
    )

    # Convert booleans to 1/0
    bool_cols = ['has_encoded_payload', 'has_download_cradle', 'has_lolbin',
                 'parent_child_anomaly', 'from_temp_dir', 'non_interactive_shell']
    for col in bool_cols:
        if col in res.columns:
            res[col] = res[col].astype(int)

    # Drop temp cols
    res = res.drop(columns=['suspicious_cmd_sum', 'valid_cmd_sum'], errors='ignore')

    # Fill NaN
    numeric_cols = res.select_dtypes(include=[np.number]).columns
    res[numeric_cols] = res[numeric_cols].fillna(0)

    return res

