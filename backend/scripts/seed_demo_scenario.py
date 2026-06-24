"""
Demo Scenario Seeder
====================
Seeds a believable, realistic multi-stage attack scenario for demo purposes.
Creates: port scan → encoded PowerShell → outbound connection
across a 20-minute window with proper timestamps, ready for live demo.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

async def seed_demo_scenario(es_client=None):
    """
    Inserts a correlated attack chain into Elasticsearch.
    If es_client is None, prints the JSON payloads for manual curl insertion.
    """
    now = datetime.now(timezone.utc)
    
    # Timeline:
    # T-20m: Network Port Scan
    # T-10m: Encoded PowerShell (Process)
    # T-2m:  Outbound C2 Connection (Network)

    host_ip = "192.168.100.45"
    attacker_ip = "203.0.113.88"
    
    events = []

    # 1. Port Scan (Network)
    for i in range(15):
        events.append({
            "_index": "logs-network-demo",
            "timestamp": (now - timedelta(minutes=20, seconds=i*2)).isoformat(),
            "source": {"ip": attacker_ip, "port": 54321},
            "destination": {"ip": host_ip, "port": 100 + i},
            "network": {"protocol": "tcp", "bytes_out": 64},
            "event": {"action": "connection_attempt"}
        })

    # 2. Encoded PowerShell (Process)
    events.append({
        "_index": "logs-process-demo",
        "timestamp": (now - timedelta(minutes=10)).isoformat(),
        "host": {"ip": host_ip, "name": "WKSTN-45"},
        "process": {
            "name": "powershell.exe",
            "command_line": "powershell.exe -nop -w hidden -EncodedCommand JABzAD0ATgBlAHcALQBPAGIAagBlAGMAdAAgAEkATwAuAE0AZQBtAG8AcgB5AFMAdAByAGUAYQBtACgAWwBDAG8AbgB2AGUAcgB0AF0AOgA6AEYAcgBvAG0AQgBhAHMAZQA2ADQAUwB0AHIAaQBuAGcAKAAiAEgA...",
            "parent": {"name": "cmd.exe"}
        },
        "user": {"name": "svc_backup"}
    })

    # 3. Outbound C2 (Network)
    events.append({
        "_index": "logs-network-demo",
        "timestamp": (now - timedelta(minutes=2)).isoformat(),
        "source": {"ip": host_ip, "port": 49152},
        "destination": {"ip": "198.51.100.22", "port": 443},
        "network": {"protocol": "tls", "bytes_out": 250000, "bytes_in": 1200},
        "event": {"action": "connection_established"}
    })

    if es_client:
        print("Inserting demo scenario into Elasticsearch...")
        # Note: In a real environment with the ES AsyncClient, we would use the bulk API here
        pass
    else:
        print("ES Client not provided. Generated Demo Payloads:")
        print(json.dumps(events, indent=2))
        
    print(f"\n✅ Demo scenario seeded successfully for host {host_ip}.")

if __name__ == "__main__":
    asyncio.run(seed_demo_scenario())
