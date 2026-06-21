#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def print_result(check_name, status, details=None):
    if status == "PASS":
        print(f"[{GREEN}PASS{RESET}] {check_name}")
    elif status == "WARN":
        print(f"[{YELLOW}WARN{RESET}] {check_name}")
        if details:
            print(f"       {details}")
    elif status == "FAIL":
        print(f"[{RED}FAIL{RESET}] {check_name}")
        if details:
            print(f"       {details}")

def audit_env_files():
    print("\n--- Auditing .env files ---")
    failed = False
    project_root = Path(__file__).parent.parent.parent
    
    env_files = list(project_root.glob("backend/.env*")) + list(project_root.glob("frontend/.env*"))
    
    for env_file in env_files:
        if not env_file.is_file() or env_file.name == ".env.example":
            continue
            
        with open(env_file, 'r') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split('=', 1)
            if len(parts) != 2:
                continue
                
            key, val = parts[0].strip(), parts[1].strip()
            
            if "PASSWORD" in key.upper():
                if val.lower() in ["password", "admin", "test", ""] or len(val) < 8:
                    if "development" in env_file.name or "test" in env_file.name:
                        print_result(f"Weak password in {env_file.name}:{i}", "WARN", f"{key}={val}")
                    else:
                        print_result(f"Weak password in {env_file.name}:{i}", "FAIL", f"{key}={val}")
                        failed = True
                        
            if "JWT_SECRET" in key.upper():
                if len(val) < 32:
                    if "development" in env_file.name or "test" in env_file.name:
                        print_result(f"Weak JWT secret in {env_file.name}:{i}", "WARN")
                    else:
                        print_result(f"Weak JWT secret in {env_file.name}:{i}", "FAIL")
                        failed = True
                        
            if "ES_VERIFY_CERTS" in key.upper():
                if val.lower() == "false" and "production" in env_file.name:
                    print_result(f"ES_VERIFY_CERTS is false in production {env_file.name}:{i}", "FAIL")
                    failed = True
                    
    if not failed:
        print_result("All .env file checks passed", "PASS")
    return failed

def audit_source_code():
    print("\n--- Auditing source code ---")
    failed = False
    project_root = Path(__file__).parent.parent.parent
    
    pattern = re.compile(r'(?i)(password|secret|api_key|token)\s*=\s*(["\'])(?!\\2)(?!\s*\\2)(.+?)\2')
    
    for py_file in project_root.rglob("*.py"):
        if "venv" in py_file.parts or ".pytest_cache" in py_file.parts or py_file.name.endswith("_test.py") or py_file.name.startswith("test_"):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                match = pattern.search(line)
                if match:
                    val = match.group(3).lower()
                    if val not in ["none", "", "true", "false", "password", "secret", "dev-secret-key-not-for-production"]:
                        print_result(f"Hardcoded secret detected", "FAIL", f"{py_file.relative_to(project_root)}:{i} -> {line.strip()}")
                        failed = True
        except Exception:
            pass
            
    if not failed:
        print_result("No hardcoded secrets found in Python source", "PASS")
    return failed

def audit_git_history():
    print("\n--- Auditing Git history ---")
    try:
        project_root = Path(__file__).parent.parent.parent
        cmd = 'git log --all -p | grep -E -i "^\\+.*(password|secret|api_key)\\s*=\\s*[\'\\"][^\'\\"]+[\'\\"]" || true'
        result = subprocess.run(cmd, shell=True, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            print_result("Potential secrets found in git history", "WARN")
            lines = result.stdout.strip().split('\n')
            for line in lines[:5]:
                print(f"       {line}")
            if len(lines) > 5:
                print(f"       ... and {len(lines) - 5} more.")
            return False 
        else:
            print_result("No obvious secrets found in git history", "PASS")
            return False
    except Exception as e:
        print_result("Failed to audit git history", "WARN", str(e))
        return False

def run_full_audit(source_only=False):
    print(f"🚀 Running SOC Security Audit...")
    failed1 = audit_env_files() if not source_only else False
    failed2 = audit_source_code()
    failed3 = audit_git_history() if not source_only else False
    
    print("\n--- Audit Complete ---")
    if failed1 or failed2 or failed3:
        print(f"[{RED}FAILED{RESET}] Security issues detected. Please fix them.")
        sys.exit(1)
    else:
        print(f"[{GREEN}SUCCESS{RESET}] All security checks passed.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SOC Security Audit")
    parser.add_argument("--source-only", action="store_true", help="Only audit source code (for pre-commit hooks)")
    args = parser.parse_args()
    
    run_full_audit(source_only=args.source_only)
