import os
import joblib
import dataclasses
import numpy as np
import pandas as pd
from typing import Any
from sklearn.preprocessing import StandardScaler
from elasticsearch import AsyncElasticsearch

from app.ingestion.log_fetcher import fetch_all_sources
from app.ingestion.normalizer import normalize_batch
from app.features.network_features import extract_all_network_features
from app.features.process_features import extract_all_process_features
from app.features.alert_features import extract_all_alert_features
from app.ingestion.es_client import INDEX_NAMES
from app.ingestion.scheduler import get_window_bucket, bulk_index

# The 50 carefully selected numeric ML input vectors representing 
# network flow, endpoint execution, and semantic alert severity aggregations.
# 8 synthesized interaction ratios have been injected to balance out exactly 50 dimensions.
FEATURE_COLUMNS = [
    # --- Network (11) ---
    "conn_per_minute",
    "unique_dst_ip_count",
    "unique_dst_port_count",
    "unique_src_port_count",
    "rare_port_flag",
    "rare_protocol_flag",
    "is_internal_to_external",
    "port_scan_score",
    "top_dst_port",
    "has_icmp",
    "has_high_port",
    # --- Process (15) ---
    "process_spawn_count",
    "unique_process_names",
    "unique_executables",
    "suspicious_cmd_score",
    "has_encoded_payload",
    "has_download_cradle",
    "has_lolbin",
    "parent_child_anomaly",
    "from_temp_dir",
    "non_interactive_shell",
    "unique_users",
    "max_args_count",
    "mean_args_count",
    "failed_exit_count",
    "unique_event_actions",
    # --- Alerts (16) ---
    "alert_count",
    "max_risk_score",
    "mean_risk_score",
    "critical_alert_count",
    "high_alert_count",
    "unique_rule_names",
    "open_alert_count",
    "mitre_tactic_count",
    "mitre_technique_count",
    "has_execution_tactic",
    "has_persistence_tactic",
    "has_exfiltration_tactic",
    "has_credential_access",
    "has_lateral_movement",
    "alert_burst_flag",
    "severity_score",
    # --- Synthesized ML Interactions (8) ---
    "network_to_process_ratio",
    "alert_to_network_ratio",
    "alert_to_process_ratio",
    "critical_alert_ratio",
    "suspicious_process_ratio",
    "high_risk_flag",
    "complex_attack_flag",
    "lateral_movement_network_flag"
]

def merge_features(network_df: pd.DataFrame, process_df: pd.DataFrame, alert_df: pd.DataFrame) -> pd.DataFrame:
    """
    Outer join all three on (entity_key, window_bucket)
    Fill NaN: 0 for numeric, "unknown" for strings
    """
    dfs = []
    for df in [network_df, process_df, alert_df]:
        if df is not None and not df.empty:
            if 'entity_key' in df.columns and 'window_bucket' in df.columns:
                dfs.append(df)
                
    if not dfs:
        return pd.DataFrame()
        
    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=['entity_key', 'window_bucket'], how='outer')
        
    # Generate the 8 synthetic interaction features required to satisfy the 50-dim ML constraint
    if 'conn_per_minute' in merged_df.columns and 'process_spawn_count' in merged_df.columns:
        merged_df['network_to_process_ratio'] = merged_df['conn_per_minute'] / merged_df['process_spawn_count'].clip(lower=1)
    else:
        merged_df['network_to_process_ratio'] = 0.0

    if 'alert_count' in merged_df.columns and 'conn_per_minute' in merged_df.columns:
        merged_df['alert_to_network_ratio'] = merged_df['alert_count'] / merged_df['conn_per_minute'].clip(lower=1)
    else:
        merged_df['alert_to_network_ratio'] = 0.0

    if 'alert_count' in merged_df.columns and 'process_spawn_count' in merged_df.columns:
        merged_df['alert_to_process_ratio'] = merged_df['alert_count'] / merged_df['process_spawn_count'].clip(lower=1)
    else:
        merged_df['alert_to_process_ratio'] = 0.0

    if 'critical_alert_count' in merged_df.columns and 'alert_count' in merged_df.columns:
        merged_df['critical_alert_ratio'] = merged_df['critical_alert_count'] / merged_df['alert_count'].clip(lower=1)
    else:
        merged_df['critical_alert_ratio'] = 0.0

    if all(col in merged_df.columns for col in ['has_encoded_payload', 'has_download_cradle', 'has_lolbin', 'unique_process_names']):
        merged_df['suspicious_process_ratio'] = (merged_df['has_encoded_payload'].fillna(0) + merged_df['has_download_cradle'].fillna(0) + merged_df['has_lolbin'].fillna(0)) / merged_df['unique_process_names'].clip(lower=1)
    else:
        merged_df['suspicious_process_ratio'] = 0.0

    if 'max_risk_score' in merged_df.columns:
        merged_df['high_risk_flag'] = (merged_df['max_risk_score'] > 80).astype(int)
    else:
        merged_df['high_risk_flag'] = 0

    if 'mitre_tactic_count' in merged_df.columns:
        merged_df['complex_attack_flag'] = (merged_df['mitre_tactic_count'] > 2).astype(int)
    else:
        merged_df['complex_attack_flag'] = 0

    if 'has_lateral_movement' in merged_df.columns and 'is_internal_to_external' in merged_df.columns:
        merged_df['lateral_movement_network_flag'] = (merged_df['has_lateral_movement'].fillna(0) * merged_df['is_internal_to_external'].fillna(0)).clip(upper=1)
    else:
        merged_df['lateral_movement_network_flag'] = 0

    # Handle explicit NaN filling
    numeric_cols = merged_df.select_dtypes(include=[np.number]).columns
    string_cols = merged_df.select_dtypes(exclude=[np.number]).columns
    
    merged_df[numeric_cols] = merged_df[numeric_cols].fillna(0)
    merged_df[string_cols] = merged_df[string_cols].fillna("unknown")
    
    return merged_df

def get_feature_vector(merged_row: pd.Series) -> np.ndarray:
    """Extract FEATURE_COLUMNS, return np.float32 array of shape (50,)."""
    vec = []
    for col in FEATURE_COLUMNS:
        val = merged_row.get(col, 0.0)
        try:
            vec.append(float(val))
        except (ValueError, TypeError):
            vec.append(0.0)
    return np.array(vec, dtype=np.float32)

def build_feature_matrix(merged_df: pd.DataFrame) -> np.ndarray:
    """Extract matrix of shape (N, 50)."""
    if merged_df is None or merged_df.empty:
        return np.empty((0, 50), dtype=np.float32)
        
    matrix = []
    for _, row in merged_df.iterrows():
        matrix.append(get_feature_vector(row))
    return np.vstack(matrix)

def fit_scaler(X: np.ndarray) -> StandardScaler:
    """Fit a new standard scaler to the feature matrix."""
    scaler = StandardScaler()
    scaler.fit(X)
    return scaler

def scale_features(X: np.ndarray, scaler: StandardScaler) -> np.ndarray:
    """Scale the feature matrix using the fit scaler."""
    if len(X) == 0:
        return X
    return scaler.transform(X)

def save_scaler(scaler: StandardScaler, path: str):
    """Save the scaler wrapper to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(scaler, path)

def load_scaler(path: str) -> StandardScaler:
    """Load an existing scaler wrapper, or return an uncalibrated default."""
    if os.path.exists(path):
        return joblib.load(path)
    return StandardScaler()

import asyncio

async def extract_network_async(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return await asyncio.to_thread(extract_all_network_features, df)

async def extract_process_async(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return await asyncio.to_thread(extract_all_process_features, df)

async def extract_alert_async(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return await asyncio.to_thread(extract_all_alert_features, df)

async def run_feature_pipeline_parallel(es: AsyncElasticsearch, since_minutes: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Full pipeline: fetch -> normalize -> extract all three feature sets concurrently -> merge
    """
    raw_results = await fetch_all_sources(es, since_minutes=since_minutes)
    
    network_raw = raw_results.get("network", [])
    process_raw = raw_results.get("process", [])
    alert_raw = raw_results.get("security_alert", [])
    
    network_norm = normalize_batch(network_raw, "network")
    process_norm = normalize_batch(process_raw, "process")
    alert_norm = normalize_batch(alert_raw, "security_alert")
    
    def enrich_normalized(logs):
        if not logs:
            return pd.DataFrame()
            
        enriched = []
        for log in logs:
            doc = dataclasses.asdict(log)
            # Add ML grouping constraints identically to the ingestion scheduler
            doc["window_bucket"] = get_window_bucket(log.timestamp).isoformat() + "Z"
            user = log.user_name or "system"
            doc["entity_key"] = f"{log.host_id}|{user}"
            enriched.append(doc)
        return pd.DataFrame(enriched)
        
    network_df_in = enrich_normalized(network_norm)
    process_df_in = enrich_normalized(process_norm)
    alert_df_in = enrich_normalized(alert_norm)
    
    # Extract all 3 feature sets concurrently
    network_task = asyncio.create_task(extract_network_async(network_df_in))
    process_task = asyncio.create_task(extract_process_async(process_df_in))
    alert_task = asyncio.create_task(extract_alert_async(alert_df_in))
    
    network_features, process_features, alert_features = await asyncio.gather(
        network_task, process_task, alert_task
    )
    
    merged_df = merge_features(network_features, process_features, alert_features)
    
    valid_dfs = [df for df in [network_df_in, process_df_in, alert_df_in] if not df.empty]
    normalized_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()
    
    return merged_df, normalized_df

async def store_feature_vectors(es: AsyncElasticsearch, feature_df: pd.DataFrame):
    """
    Bulk-index into soc-feature-vectors: entity_key, window_bucket, all feature columns, feature_vector as list
    """
    if feature_df is None or feature_df.empty:
        return {"indexed": 0, "errors": []}
        
    index_name = INDEX_NAMES["features"]
    docs = []
    
    for _, row in feature_df.iterrows():
        doc = row.to_dict()
        vec = get_feature_vector(row).tolist()
        doc["feature_vector"] = vec
        docs.append(doc)
        
    return await bulk_index(es, docs, index_name)

# Alias for backwards compatibility
run_feature_pipeline = run_feature_pipeline_parallel
