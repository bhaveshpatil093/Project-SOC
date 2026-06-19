import json
import requests
import os
from textwrap import dedent

# URL to the running FastAPI openapi.json
# Ensure your backend is running on port 8000
API_URL = "http://localhost:8000/openapi.json"
OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/API_REFERENCE.md"))

def generate_docs():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        openapi = response.json()
    except Exception as e:
        print(f"Failed to fetch OpenAPI JSON from {API_URL}. Is the backend running?")
        print(f"Error: {e}")
        return

    info = openapi.get("info", {})
    title = info.get("title", "API Reference")
    version = info.get("version", "1.0.0")
    description = info.get("description", "")

    md_lines = []
    md_lines.append(f"# {title} (v{version})")
    md_lines.append("")
    md_lines.append(description.strip())
    md_lines.append("")
    md_lines.append("## Endpoints")
    md_lines.append("")

    paths = openapi.get("paths", {})
    
    # Group by tags
    tags_map = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            tags = details.get("tags", ["Untagged"])
            for t in tags:
                if t not in tags_map:
                    tags_map[t] = []
                tags_map[t].append((path, method.upper(), details))

    for tag, endpoints in sorted(tags_map.items()):
        md_lines.append(f"### {tag}")
        md_lines.append("")
        
        for path, method, details in endpoints:
            summary = details.get("summary", path)
            md_lines.append(f"#### `{method}` {path}")
            md_lines.append(f"**{summary}**")
            md_lines.append("")
            
            desc = details.get("description", "")
            if desc:
                md_lines.append(desc)
                md_lines.append("")
                
            parameters = details.get("parameters", [])
            if parameters:
                md_lines.append("**Parameters:**")
                md_lines.append("| Name | In | Type | Required | Description |")
                md_lines.append("|---|---|---|---|---|")
                for p in parameters:
                    name = p.get("name", "")
                    in_loc = p.get("in", "")
                    req = "Yes" if p.get("required") else "No"
                    schema_type = p.get("schema", {}).get("type", "string")
                    p_desc = p.get("description", "")
                    md_lines.append(f"| `{name}` | {in_loc} | {schema_type} | {req} | {p_desc} |")
                md_lines.append("")
                
            req_body = details.get("requestBody", {})
            if req_body:
                md_lines.append("**Request Body:** (application/json)")
                md_lines.append("```json")
                md_lines.append("// Check OpenAPI schema for detailed request structure")
                md_lines.append("```")
                md_lines.append("")
                
            responses = details.get("responses", {})
            if responses:
                md_lines.append("**Responses:**")
                for status, r_details in responses.items():
                    r_desc = r_details.get("description", "")
                    md_lines.append(f"- **{status}**: {r_desc}")
                md_lines.append("")
                
            md_lines.append("---")
            md_lines.append("")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(md_lines))
        
    print(f"API documentation successfully generated at {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_docs()
