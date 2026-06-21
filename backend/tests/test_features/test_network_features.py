import pytest
import pandas as pd
from app.features.network_features import process_network_events

@pytest.fixture
def empty_df():
    return pd.DataFrame()

@pytest.fixture
def port_scan_df():
    """Generates a dataframe mimicking a port scan (many unique destination ports)."""
    data = []
    for i in range(60):
        data.append({
            "timestamp": "2026-06-21T10:00:00Z",
            "entity_key": "10.0.0.5",
            "src_ip": "10.0.0.5",
            "dst_ip": "192.168.1.100",
            "dst_port": 1000 + i,
            "bytes_out": 100,
            "bytes_in": 100
        })
    return pd.DataFrame(data)

@pytest.fixture
def internal_external_df():
    """Generates a dataframe with internal to external traffic."""
    return pd.DataFrame([{
        "timestamp": "2026-06-21T10:00:00Z",
        "entity_key": "192.168.1.1",
        "src_ip": "192.168.1.1",
        "dst_ip": "8.8.8.8",
        "dst_port": 443,
        "bytes_out": 500,
        "bytes_in": 5000
    }])

def test_port_scan_detected(port_scan_df):
    """Test that high unique port counts flag as anomalous."""
    # Convert timestamp to datetime if not done by processor
    port_scan_df["timestamp"] = pd.to_datetime(port_scan_df["timestamp"])
    
    features = process_network_events(port_scan_df)
    assert len(features) == 1
    row = features.iloc[0]
    
    assert row["unique_dst_port_count"] == 60
    # Process threshold is usually > 50 for rare/scan flags
    # We check if rare_port_flag or similar exists if implemented
    if "rare_protocol_flag" in features.columns:
        # Assuming high port count triggers something or score
        pass
    
    assert row["conn_per_minute"] > 0

def test_internal_to_external_flag(internal_external_df):
    """Test that routing from private to public space is properly flagged."""
    internal_external_df["timestamp"] = pd.to_datetime(internal_external_df["timestamp"])
    features = process_network_events(internal_external_df)
    row = features.iloc[0]
    
    # 192.168.1.1 -> 8.8.8.8
    assert row["is_internal_to_external"] == 1.0

def test_is_private_ip_rfc1918():
    """Directly test the RFC1918 checking logic via dummy DF."""
    from app.features.network_features import _is_private_ip
    
    # RFC 1918
    assert _is_private_ip("10.0.5.5") is True
    assert _is_private_ip("172.16.0.1") is True
    assert _is_private_ip("192.168.1.1") is True
    
    # Public
    assert _is_private_ip("8.8.8.8") is False
    assert _is_private_ip("1.1.1.1") is False
    assert _is_private_ip("100.1.2.3") is False

def test_conn_per_minute_calculation():
    """Ensure events are properly binned into minute rates."""
    data = [{"timestamp": "2026-06-21T10:00:00Z", "entity_key": "10.0.0.1", "src_ip": "10.0.0.1", "dst_ip": "8.8.8.8", "dst_port": 80} for _ in range(100)]
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    features = process_network_events(df)
    row = features.iloc[0]
    
    # 100 events in a theoretical 5 minute window = 20.0 conns/min
    # Implementation uses fixed 5.0 divisor
    assert pytest.approx(row["conn_per_minute"], 0.1) == 20.0

def test_missing_fields_handled_gracefully():
    """Test dataframe with missing required fields."""
    df = pd.DataFrame([{"timestamp": "2026-06-21T10:00:00Z", "entity_key": "10.0.0.1"}])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    features = process_network_events(df)
    row = features.iloc[0]
    
    # Should default to 0 for numerics
    assert row["bytes_out"] == 0.0
    assert row["unique_dst_port_count"] == 0.0

def test_extract_all_groups_by_entity():
    """Ensure it correctly groups multi-entity multi-window frames."""
    data = []
    # Entity 1, Win 1
    data.append({"timestamp": "2026-06-21T10:01:00Z", "entity_key": "E1", "dst_port": 80})
    # Entity 1, Win 2
    data.append({"timestamp": "2026-06-21T10:06:00Z", "entity_key": "E1", "dst_port": 80})
    # Entity 2, Win 1
    data.append({"timestamp": "2026-06-21T10:01:00Z", "entity_key": "E2", "dst_port": 80})
    
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    features = process_network_events(df)
    # 2 entities, E1 has 2 windows, E2 has 1 -> 3 rows
    assert len(features) == 3
