import ipaddress
import pandas as pd
import numpy as np

def is_private_ip(ip: str) -> bool:
    """Check if the given IP address is a private RFC1918 address."""
    if not ip or pd.isna(ip):
        return False
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False

def extract_network_features(df: pd.DataFrame, entity_key: str, window_bucket: str) -> dict:
    """
    Extract network features from a grouped subset of syslog network events
    matching a unique entity and time window.
    """
    if df.empty:
        return {}
        
    COMMON_PORTS = {80, 443, 22, 3389, 8080, 8443, 21, 25, 53}
    COMMON_PROTOCOLS = {"TCP", "UDP", "ICMP"}
    
    total_events = len(df)
    conn_per_minute = float(total_events / 5.0)
    
    unique_dst_ip_count = int(df['dst_ip'].nunique(dropna=True) if 'dst_ip' in df.columns else 0)
    unique_dst_port_count = int(df['dst_port'].nunique(dropna=True) if 'dst_port' in df.columns else 0)
    unique_src_port_count = int(df['src_port'].nunique(dropna=True) if 'src_port' in df.columns else 0)
    
    dst_ports = df['dst_port'].dropna().unique() if 'dst_port' in df.columns else []
    rare_port_flag = 1 if any(p not in COMMON_PORTS for p in dst_ports) else 0
    
    if 'protocol' in df.columns:
        protocols = df['protocol'].dropna().astype(str).str.upper().unique()
    else:
        protocols = []
        
    rare_protocol_flag = 1 if any(p not in COMMON_PROTOCOLS for p in protocols) else 0
    
    # Internal to external logic
    if 'src_ip' in df.columns and 'dst_ip' in df.columns:
        src_is_private = df['src_ip'].apply(is_private_ip)
        dst_is_private = df['dst_ip'].apply(is_private_ip)
        is_internal_to_external = 1 if ((src_is_private) & (~dst_is_private & df['dst_ip'].notna())).any() else 0
    else:
        is_internal_to_external = 0
    
    port_scan_score = float(unique_dst_port_count / max(conn_per_minute, 1.0))
    
    top_dst_port = 0
    if 'dst_port' in df.columns:
        mode_s = df['dst_port'].mode()
        if not mode_s.empty:
            top_dst_port = int(mode_s.iloc[0])
            
    top_protocol = ""
    if 'protocol' in df.columns:
        mode_p = df['protocol'].mode()
        if not mode_p.empty:
            top_protocol = str(mode_p.iloc[0])
            
    has_icmp = 1 if "ICMP" in protocols else 0
    has_high_port = 1 if any(p > 49151 for p in dst_ports) else 0
    
    return {
        "entity_key": entity_key,
        "window_bucket": window_bucket,
        "conn_per_minute": conn_per_minute,
        "unique_dst_ip_count": unique_dst_ip_count,
        "unique_dst_port_count": unique_dst_port_count,
        "unique_src_port_count": unique_src_port_count,
        "rare_port_flag": rare_port_flag,
        "rare_protocol_flag": rare_protocol_flag,
        "is_internal_to_external": is_internal_to_external,
        "port_scan_score": port_scan_score,
        "top_dst_port": top_dst_port,
        "top_protocol": top_protocol,
        "has_icmp": has_icmp,
        "has_high_port": has_high_port
    }

def extract_all_network_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups the dataframe by (entity_key, window_bucket) and applies the network extractor
    returning a DataFrame comprising 1 record per group.
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    if 'entity_key' not in df.columns or 'window_bucket' not in df.columns:
        return pd.DataFrame()
        
    features_list = []
    grouped = df.groupby(['entity_key', 'window_bucket'])
    
    for (entity_key, window_bucket), group_df in grouped:
        # Cast index scalars explicitly to string
        features = extract_network_features(group_df, str(entity_key), str(window_bucket))
        if features:
            features_list.append(features)
            
    result_df = pd.DataFrame(features_list)
    if result_df.empty:
        return result_df
        
    # Fill NaN with 0 for all numeric columns as requested
    numeric_cols = result_df.select_dtypes(include=[np.number]).columns
    result_df[numeric_cols] = result_df[numeric_cols].fillna(0)
    
    return result_df
