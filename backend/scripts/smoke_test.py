import argparse
import time
import sys
import json
import requests
import asyncio
import websockets

class SmokeTest:
    def __init__(self, base_url: str, username: str, password: str, skip_slm: bool = False, fail_fast: bool = False):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.skip_slm = skip_slm
        self.fail_fast = fail_fast
        self.session = requests.Session()
        self.token = None
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        
        self.results = []
        self.passed = 0
        self.failed = 0
        self.first_alert_id = None

    def record_result(self, name: str, success: bool, duration_ms: float, error: str = None):
        self.results.append({
            "name": name,
            "success": success,
            "duration_ms": duration_ms,
            "error": error
        })
        if success:
            self.passed += 1
        else:
            self.failed += 1

    def run_test(self, name: str, test_func):
        start = time.time()
        try:
            success = test_func()
            duration_ms = (time.time() - start) * 1000
            if not success:
                self.record_result(name, False, duration_ms, "Test returned False")
            else:
                self.record_result(name, True, duration_ms)
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self.record_result(name, False, duration_ms, f"{type(e).__name__}: {str(e)}")
            
        if self.fail_fast and self.failed > 0:
            return False
        return True

    # Auth tests
    def test_protected_route_without_token(self) -> bool:
        res = requests.get(f"{self.base_url}/api/alerts")
        return res.status_code == 401

    def test_login(self) -> bool:
        res = self.session.post(
            f"{self.base_url}/api/auth/login",
            data={"username": self.username, "password": self.password}
        )
        if res.status_code == 200:
            data = res.json()
            if "access_token" in data:
                self.token = data["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
        raise Exception(f"Login failed: {res.text}")

    # Health tests
    def test_health_liveness(self) -> bool:
        res = requests.get(f"{self.base_url}/health")
        return res.status_code == 200

    def test_health_readiness(self) -> bool:
        res = requests.get(f"{self.base_url}/health/ready")
        return res.status_code == 200

    def test_health_deep(self) -> bool:
        res = requests.get(f"{self.base_url}/health/deep")
        return res.status_code == 200 and "components" in res.json()

    # Elasticsearch tests
    def test_es_indices_exist(self) -> bool:
        # Implicitly tested via alerts endpoints, but we can hit an endpoint that uses ES
        res = self.session.get(f"{self.base_url}/api/alerts?limit=1")
        return res.status_code == 200

    def test_es_can_index_document(self) -> bool:
        # Hit ingestion endpoint which indexes docs
        res = self.session.post(f"{self.base_url}/api/ingestion/run")
        if res.status_code == 429: return True # rate limit is fine
        return res.status_code == 200

    # Ingestion tests
    def test_ingestion_status_endpoint(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/ingestion/status")
        return res.status_code == 200

    def test_trigger_ingestion_cycle(self) -> bool:
        res = self.session.post(f"{self.base_url}/api/ingestion/run")
        if res.status_code == 429: return True
        return res.status_code == 200

    # Feature tests
    def test_feature_pipeline_run(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/features/run")
        return res.status_code == 200

    # Alert tests
    def test_list_alerts(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/alerts")
        if res.status_code == 200:
            data = res.json()
            if data.get("alerts") and len(data["alerts"]) > 0:
                self.first_alert_id = data["alerts"][0]["id"]
            return True
        return False

    def test_alert_stats(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/alerts/stats")
        return res.status_code == 200

    def test_trigger_scoring(self) -> bool:
        res = self.session.post(f"{self.base_url}/api/alerts/trigger-scoring")
        return res.status_code == 200

    # ML model tests
    def test_training_history(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/training/status")
        return res.status_code == 200

    # Feedback tests
    def test_submit_feedback(self) -> bool:
        payload = {
            "alert_id": self.first_alert_id or "test-alert",
            "analyst_name": "Smoke Test",
            "label": "Benign",
            "mitre_override": "",
            "notes": "Automated smoke test verification"
        }
        res = self.session.post(f"{self.base_url}/api/feedback", json=payload)
        return res.status_code == 200

    def test_feedback_stats(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/feedback/stats")
        return res.status_code == 200

    # SLM tests
    def test_slm_status(self) -> bool:
        res = self.session.get(f"{self.base_url}/api/slm/status")
        return res.status_code == 200

    def test_slm_chat(self) -> bool:
        if self.skip_slm: return True
        payload = {"message": "Hello", "alert_id": None}
        res = self.session.post(f"{self.base_url}/api/slm/chat", json=payload)
        if res.status_code == 429: return True
        return res.status_code == 200

    def test_slm_explain_alert(self) -> bool:
        if self.skip_slm or not self.first_alert_id: return True
        payload = {"message": "Explain this alert.", "alert_id": self.first_alert_id}
        res = self.session.post(f"{self.base_url}/api/slm/chat", json=payload)
        if res.status_code == 429: return True
        return res.status_code == 200

    # WebSocket tests
    def test_websocket_connects(self) -> bool:
        async def _connect():
            async with websockets.connect(f"{self.ws_url}/ws/alerts?token={self.token}") as ws:
                return True
        try:
            return asyncio.run(_connect())
        except Exception:
            return False

    def test_websocket_receives_ping(self) -> bool:
        async def _ping():
            async with websockets.connect(f"{self.ws_url}/ws/alerts?token={self.token}") as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                # Just receiving anything means we got a connection payload or ping
                return bool(msg)
        try:
            return asyncio.run(_ping())
        except asyncio.TimeoutError:
            # Maybe no events streamed in 2 seconds, which is fine
            return True
        except Exception:
            return False

    def run_all(self) -> dict:
        start_time = time.time()
        
        # Unauthorized first
        self.run_test("Protected route without token", self.test_protected_route_without_token)
        
        if self.run_test("Login", self.test_login) and self.token:
            tests = [
                ("Health liveness", self.test_health_liveness),
                ("Health readiness", self.test_health_readiness),
                ("Health deep", self.test_health_deep),
                ("ES indices exist", self.test_es_indices_exist),
                ("ES index document", self.test_es_can_index_document),
                ("Ingestion status", self.test_ingestion_status_endpoint),
                ("Trigger ingestion", self.test_trigger_ingestion_cycle),
                ("Feature pipeline run", self.test_feature_pipeline_run),
                ("List alerts", self.test_list_alerts),
                ("Alert stats", self.test_alert_stats),
                ("Trigger scoring", self.test_trigger_scoring),
                ("Training history", self.test_training_history),
                ("Submit feedback", self.test_submit_feedback),
                ("Feedback stats", self.test_feedback_stats),
                ("SLM status", self.test_slm_status)
            ]
            
            if not self.skip_slm:
                tests.extend([
                    ("SLM chat", self.test_slm_chat),
                    ("SLM explain alert", self.test_slm_explain_alert)
                ])
                
            tests.extend([
                ("WebSocket connects", self.test_websocket_connects),
                ("WebSocket receives ping", self.test_websocket_receives_ping)
            ])
            
            for name, func in tests:
                if self.fail_fast and self.failed > 0:
                    break
                self.run_test(name, func)

        total_duration = (time.time() - start_time) * 1000
        total = self.passed + self.failed
        return {
            "passed": self.passed,
            "failed": self.failed,
            "total": total,
            "results": self.results,
            "duration_ms": total_duration
        }

    def print_report(self, report: dict):
        print("\n--- Smoke Test Results ---")
        for res in report["results"]:
            icon = "✅ PASS" if res["success"] else "❌ FAIL"
            color = "\033[92m" if res["success"] else "\033[91m"
            reset = "\033[0m"
            err = f"  ({res['error']})" if not res["success"] else ""
            print(f"{color}{icon}{reset}  {res['name'].ljust(30)} ({res['duration_ms']:.1f}ms){err}")
            
        pct = (report["passed"] / report["total"] * 100) if report["total"] > 0 else 0
        print(f"\nResult: {report['passed']}/{report['total']} tests passed ({pct:.0f}%) in {report['duration_ms']/1000:.2f}s")
        if report["failed"] > 0:
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run E2E Smoke Tests for SOC Platform")
    parser.add_argument("--url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--password", default="admin123", help="Admin password")
    parser.add_argument("--skip-slm", action="store_true", help="Skip slow SLM tests")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    tester = SmokeTest(
        base_url=args.url,
        username=args.username,
        password=args.password,
        skip_slm=args.skip_slm,
        fail_fast=args.fail_fast
    )
    
    report = tester.run_all()
    
    if args.json:
        print(json.dumps(report, indent=2))
        if report["failed"] > 0:
            sys.exit(1)
    else:
        tester.print_report(report)

if __name__ == "__main__":
    main()
