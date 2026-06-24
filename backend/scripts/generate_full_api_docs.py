import json
import requests
import os

API_URL = "http://localhost:8000/openapi.json"
LOCAL_FALLBACK = os.path.abspath(os.path.join(os.path.dirname(__file__), "../docs/openapi.json"))
OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/API_REFERENCE.md"))

CATEGORIES = [
    "Authentication",
    "Health & Monitoring",
    "Ingestion",
    "Features",
    "Alerts",
    "Incidents",
    "Entities",
    "Feedback",
    "Training",
    "SLM",
    "Hunting",
    "Reports",
    "Admin",
    "Webhooks",
]

# Hardcoded rules for mapping paths to roles and rate limits
ROLE_MAPPING = {
    "/api/admin": "Admin",
    "/api/auth/login": "None",
    "/health": "None",
    "/metrics": "None"
}

RATE_LIMITS = {
    "/api/slm/chat": "60 requests/minute",
    "/api/alerts": "300 requests/minute",
    "/api/auth/login": "5 requests/minute"
}

def resolve_ref(ref_str, components):
    # ref_str looks like "#/components/schemas/AlertResponse"
    parts = ref_str.split("/")
    if len(parts) == 4 and parts[1] == "components" and parts[2] == "schemas":
        return components.get("schemas", {}).get(parts[3], {})
    return {}

def generate_example_from_schema(schema, components, depth=0):
    if depth > 5:  # Prevent infinite recursion
        return {}
        
    if not isinstance(schema, dict):
        return schema if isinstance(schema, (str, int, float, bool)) else {}
        
    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], components)
        return generate_example_from_schema(resolved, components, depth + 1)
        
    type_ = schema.get("type", "object")
    
    if "anyOf" in schema:
        # Just pick the first
        return generate_example_from_schema(schema["anyOf"][0], components, depth + 1)
        
    if type_ == "object":
        if "properties" in schema:
            obj = {}
            for k, v in schema["properties"].items():
                obj[k] = generate_example_from_schema(v, components, depth + 1)
            return obj
        elif "additionalProperties" in schema:
            return {"key1": generate_example_from_schema(schema["additionalProperties"], components, depth + 1)}
        else:
            return {}
            
    elif type_ == "array":
        items = schema.get("items", {})
        return [generate_example_from_schema(items, components, depth + 1)]
        
    elif type_ == "string":
        if schema.get("format") == "date-time":
            return "2026-06-24T18:00:00Z"
        return "string"
        
    elif type_ == "integer":
        return 0
        
    elif type_ == "number":
        return 0.0
        
    elif type_ == "boolean":
        return True
        
    return None

def get_role_for_path(path):
    for k, v in ROLE_MAPPING.items():
        if path.startswith(k):
            return v
    return "Any Valid User"

def get_rate_limit(path):
    for k, v in RATE_LIMITS.items():
        if path.startswith(k):
            return v
    return "Standard"

def generate_curl(method, path, req_example):
    base = "http://localhost:8000"
    cmd = f"curl -X '{method}' \\ \n  '{base}{path}' \\ \n  -H 'accept: application/json' \\ \n  -H 'Authorization: Bearer <YOUR_JWT_TOKEN>'"
    
    if req_example and method in ["POST", "PUT", "PATCH"]:
        cmd += f" \\ \n  -H 'Content-Type: application/json' \\ \n  -d '{json.dumps(req_example)}'"
        
    return cmd

def load_openapi():
    try:
        response = requests.get(API_URL, timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Could not load live openapi from {API_URL}. Trying static fallback...")
        if os.path.exists(LOCAL_FALLBACK):
            with open(LOCAL_FALLBACK, 'r') as f:
                return json.load(f)
        raise RuntimeError("Failed to load OpenAPI JSON from live server and fallback file.")

def generate_docs():
    openapi = load_openapi()
    components = openapi.get("components", {})
    paths = openapi.get("paths", {})

    md_lines = []
    md_lines.append("# ISRO SOC Platform — Complete API Reference")
    md_lines.append("")
    md_lines.append("Base URL: `http://localhost:8000` (dev) | `https://soc.istrac.isro.gov.in` (prod)")
    md_lines.append("Authentication: Bearer JWT token (obtain via POST `/api/auth/login`)")
    md_lines.append("")
    
    # 1. Generate Auth Table up top
    md_lines.append("## Authentication")
    md_lines.append("| Method | Endpoint | Description | Role Required |")
    md_lines.append("|--------|----------|--------------|----------------|")
    
    for path, methods in paths.items():
        if path.startswith("/api/auth"):
            for m_key, m_val in methods.items():
                m_upper = m_key.upper()
                desc = m_val.get("summary", "")
                role = get_role_for_path(path)
                md_lines.append(f"| {m_upper} | {path} | {desc} | {role} |")
    md_lines.append("")
    
    # Map endpoints to categories
    grouped_paths = {c: [] for c in CATEGORIES}
    grouped_paths["Uncategorized"] = []
    
    for path, methods in paths.items():
        if path.startswith("/api/auth"):
            continue # already handled loosely in table, though we'll generate full docs if we want? The prompt says Auth is a table, but let's just categorize everything.
            
        category = "Uncategorized"
        if path.startswith("/health"): category = "Health & Monitoring"
        elif path.startswith("/api/ingestion"): category = "Ingestion"
        elif path.startswith("/api/features"): category = "Features"
        elif path.startswith("/api/alerts"): category = "Alerts"
        elif path.startswith("/api/incidents"): category = "Incidents"
        elif path.startswith("/api/entities"): category = "Entities"
        elif path.startswith("/api/feedback"): category = "Feedback"
        elif path.startswith("/api/training"): category = "Training"
        elif path.startswith("/api/slm"): category = "SLM"
        elif path.startswith("/api/hunting"): category = "Hunting"
        elif path.startswith("/api/reports"): category = "Reports"
        elif path.startswith("/api/admin"): category = "Admin"
        elif path.startswith("/api/webhooks"): category = "Webhooks"
        
        grouped_paths[category].append((path, methods))
        
    for cat in CATEGORIES:
        endpoints = grouped_paths.get(cat, [])
        if not endpoints:
            continue
            
        md_lines.append(f"## {cat}")
        md_lines.append("")
        
        for path, methods in endpoints:
            for method, details in methods.items():
                m_upper = method.upper()
                summary = details.get("summary", path)
                
                md_lines.append(f"### {m_upper} {path}")
                md_lines.append(f"**{summary}**")
                md_lines.append("")
                
                desc = details.get("description", "")
                if desc:
                    md_lines.append(desc)
                    md_lines.append("")
                    
                md_lines.append(f"- **Role Required**: {get_role_for_path(path)}")
                md_lines.append(f"- **Rate Limit**: {get_rate_limit(path)}")
                md_lines.append("")
                
                # Parameters
                parameters = details.get("parameters", [])
                if parameters:
                    md_lines.append("**Query Parameters:**")
                    for p in parameters:
                        name = p.get("name")
                        req = "(Required)" if p.get("required") else "(Optional)"
                        p_desc = p.get("description", "")
                        md_lines.append(f"- `{name}` {req}: {p_desc}")
                    md_lines.append("")
                
                # Request Body
                req_example = None
                req_body = details.get("requestBody", {})
                if req_body:
                    content = req_body.get("content", {}).get("application/json", {})
                    schema = content.get("schema", {})
                    if schema:
                        req_example = generate_example_from_schema(schema, components)
                        md_lines.append("**Request Body:**")
                        md_lines.append("```json")
                        md_lines.append(json.dumps(req_example, indent=2))
                        md_lines.append("```")
                        md_lines.append("")
                        
                # Response
                responses = details.get("responses", {})
                succ_res = responses.get("200", {})
                if succ_res:
                    md_lines.append("**Response (200 OK):**")
                    content = succ_res.get("content", {}).get("application/json", {})
                    schema = content.get("schema", {})
                    if schema:
                        res_example = generate_example_from_schema(schema, components)
                        md_lines.append("```json")
                        md_lines.append(json.dumps(res_example, indent=2))
                        md_lines.append("```")
                        md_lines.append("")
                        
                # Errors
                errs = [k for k in responses.keys() if k != "200"]
                if errs:
                    md_lines.append("**Possible Errors:**")
                    for e in errs:
                        e_desc = responses[e].get("description", "")
                        md_lines.append(f"- **{e}**: {e_desc}")
                    md_lines.append("")
                    
                # cURL
                md_lines.append("**cURL Example:**")
                md_lines.append("```bash")
                md_lines.append(generate_curl(m_upper, path, req_example))
                md_lines.append("```")
                md_lines.append("")
                md_lines.append("---")
                md_lines.append("")

    # WebSockets Section
    md_lines.append("## WebSocket")
    md_lines.append("The platform pushes real-time events via `ws://localhost:8000/api/ws/alerts`.")
    md_lines.append("")
    md_lines.append("### Connection")
    md_lines.append("To connect, pass your JWT token as a query parameter (or header):")
    md_lines.append("`ws://localhost:8000/api/ws/alerts?token=<JWT_TOKEN>`")
    md_lines.append("")
    md_lines.append("### Event: `stats_update`")
    md_lines.append("Emitted every 60 seconds with global threat counts.")
    md_lines.append("```json")
    md_lines.append(json.dumps({
        "type": "stats_update",
        "data": {
            "critical": 2,
            "high": 14,
            "medium": 45,
            "low": 120,
            "total": 181
        }
    }, indent=2))
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("### Event: `sla_warning`")
    md_lines.append("Emitted when critical incidents are nearing response breach.")
    md_lines.append("```json")
    md_lines.append(json.dumps({
        "type": "sla_warning",
        "data": [
            {
                "incident_id": "INC-889",
                "time_remaining_minutes": 10,
                "assigned_team": "Team Alpha"
            }
        ]
    }, indent=2))
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("### Event: `scoring_complete`")
    md_lines.append("Emitted after an ML cycle finishes.")
    md_lines.append("```json")
    md_lines.append(json.dumps({
        "type": "scoring_complete",
        "data": {
            "scored": 450,
            "critical": 1,
            "high": 3,
            "medium": 12,
            "low": 434,
            "cycle_time_ms": 1405.2,
            "timestamp": "2026-06-24T18:00:00Z"
        }
    }, indent=2))
    md_lines.append("```")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        f.write("\n".join(md_lines))
        
    print(f"Generated complete API Reference at {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_docs()
