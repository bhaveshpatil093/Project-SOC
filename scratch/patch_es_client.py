import os

with open("backend/app/ingestion/es_client.py", "r") as f:
    content = f.read()

mapping_patch = """                        "sla_status": {"type": "keyword"},
                        "tags": {"type": "keyword"}
"""

if '"tags": {"type": "keyword"}' not in content:
    content = content.replace('"sla_status": {"type": "keyword"}', mapping_patch)

with open("backend/app/ingestion/es_client.py", "w") as f:
    f.write(content)
