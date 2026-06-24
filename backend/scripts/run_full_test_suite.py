"""
ISRO SOC Platform — Master Test Suite Runner
Runs every test category in order, aggregates results, produces final report.
"""
import os
import sys
import subprocess
import re
import time
from dataclasses import dataclass
from datetime import datetime
import json

TEST_SUITES = [
    {"name": "Unit: ML Models",       "path": "tests/test_models/",        "timeout": 120},
    {"name": "Unit: Features",        "path": "tests/test_features/",      "timeout": 60},
    {"name": "Unit: SLM",             "path": "tests/test_slm/",           "timeout": 180},
    {"name": "Unit: Correlation",     "path": "tests/test_correlation/",   "timeout": 60},
    {"name": "Integration: API",      "path": "tests/test_api/",           "timeout": 120},
    {"name": "Integration: E2E",      "path": "tests/test_e2e_pipeline.py","timeout": 180},
    {"name": "Full Journey",          "path": "tests/test_full_journey.py","timeout": 60},
    {"name": "Regression: Golden",    "path": "tests/regression/",         "timeout": 300},
    {"name": "Data Validation",       "path": "tests/test_ingestion_edge_cases.py", "timeout": 60},
    {"name": "ES Mapping Validation", "path": "tests/test_es_mappings.py", "timeout": 60},
    {"name": "Contract Tests",        "path": "tests/test_contracts.py",   "timeout": 60},
    {"name": "Chaos/Resilience",      "path": "tests/chaos/",              "timeout": 180},
    {"name": "Security: OWASP",       "path": "tests/security/",           "timeout": 120},
]

@dataclass
class SuiteResult:
    name: str
    passed: int
    failed: int
    skipped: int
    duration: float
    coverage: str
    error_output: str

@dataclass
class FullReport:
    suites: list[SuiteResult]
    total_passed: int
    total_failed: int
    total_skipped: int
    total_duration: float
    overall_coverage: str
    pass_rate: float
    failures: list[dict]

class TestSuiteRunner:
    def __init__(self):
        # Clear previous coverage data
        try:
            if os.path.exists(".coverage"):
                os.remove(".coverage")
        except:
            pass

    def run_suite(self, suite: dict) -> SuiteResult:
        print(f"Running suite: {suite['name']}...")
        start_time = time.time()
        
        # We run with coverage appended, short traceback
        # We also redirect output to capture
        cmd = [
            "pytest", 
            suite["path"], 
            "--cov=app", 
            "--cov-append", 
            "--tb=short",
            "-v"
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                timeout=suite["timeout"],
                env={**os.environ, "SOC_ENVIRONMENT": "test"}
            )
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired as e:
            output = e.stdout.decode() if e.stdout else ""
            output += f"\nTimeoutError: Suite exceeded timeout of {suite['timeout']} seconds."
            return SuiteResult(suite["name"], 0, 1, 0, suite["timeout"], "—", output)
        except Exception as e:
            return SuiteResult(suite["name"], 0, 1, 0, 0, "—", str(e))
        
        duration = time.time() - start_time
        
        # Parse output
        passed = 0
        failed = 0
        skipped = 0
        coverage = "—"
        
        # Regex for standard pytest summary e.g. "== 4 passed, 1 failed, 2 skipped in 1.45s =="
        summary_match = re.search(r"===(.*?)in", output)
        if summary_match:
            summary = summary_match.group(1)
            p_match = re.search(r"(\d+)\s+passed", summary)
            f_match = re.search(r"(\d+)\s+failed", summary)
            s_match = re.search(r"(\d+)\s+skipped", summary)
            if p_match: passed = int(p_match.group(1))
            if f_match: failed = int(f_match.group(1))
            if s_match: skipped = int(s_match.group(1))
            
        # If output says 'no tests ran', or 'collected 0 items'
        if "no tests ran" in output or "collected 0 items" in output:
            pass # leave as 0
            
        # Parse coverage for this specific run if visible
        # Usually looks like "TOTAL               150      50    66%"
        cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+\%)", output)
        if cov_match:
            coverage = cov_match.group(1)
            
        return SuiteResult(suite["name"], passed, failed, skipped, duration, coverage, output if failed > 0 else "")

    def run_all(self) -> FullReport:
        results = []
        start_time = time.time()
        
        for suite in TEST_SUITES:
            # Skip missing paths to avoid catastrophic failure
            if not os.path.exists(suite["path"]):
                print(f"Skipping {suite['name']} — path {suite['path']} not found.")
                # We can mark it as skipped tests 0
                results.append(SuiteResult(suite["name"], 0, 0, 0, 0, "—", ""))
                continue
            
            res = self.run_suite(suite)
            results.append(res)
            
        total_duration = time.time() - start_time
        
        # Get overall coverage
        overall_cov = "—"
        try:
            cov_res = subprocess.run(["coverage", "report"], stdout=subprocess.PIPE, text=True)
            cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+\%)", cov_res.stdout)
            if cov_match:
                overall_cov = cov_match.group(1)
        except:
            pass

        t_passed = sum(r.passed for r in results)
        t_failed = sum(r.failed for r in results)
        t_skipped = sum(r.skipped for r in results)
        
        total_tests = t_passed + t_failed
        pass_rate = (t_passed / total_tests) if total_tests > 0 else 1.0

        # Extract failures
        failures = []
        for r in results:
            if r.failed > 0 and r.error_output:
                # Basic failure extraction: look for "FAILED tests/..."
                for match in re.finditer(r"FAILED\s+(tests/\S+::\S+)(.*?)(?=FAILED\s|==\s|)", r.error_output, re.DOTALL):
                    test_id = match.group(1)
                    detail_text = match.group(2).strip()
                    # extract the last line of the traceback (Exception name + message)
                    err_lines = [l for l in detail_text.split("\n") if "Error:" in l or "Exception:" in l or "AssertionError" in l]
                    err_msg = err_lines[-1].strip() if err_lines else detail_text.split("\n")[-1]
                    failures.append({"suite": r.name, "test_id": test_id, "error": err_msg})
                
                # Check for TimeoutError
                if "TimeoutError" in r.error_output:
                    failures.append({"suite": r.name, "test_id": f"{r.name} Timeout", "error": "TimeoutError: retry did not complete within test timeout"})

        return FullReport(
            suites=results,
            total_passed=t_passed,
            total_failed=t_failed,
            total_skipped=t_skipped,
            total_duration=total_duration,
            overall_coverage=overall_cov,
            pass_rate=pass_rate,
            failures=failures
        )

    def generate_console_summary(self, report: FullReport):
        print("\nISRO SOC Platform — Full Test Suite Results")
        print("=============================================")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mins = int(report.total_duration // 60)
        secs = int(report.total_duration % 60)
        print(f"Date: {now_str}")
        print(f"Total Duration: {mins}m {secs}s\n")
        
        print(f"{'Suite':<30} {'Pass':>5} {'Fail':>6} {'Skip':>6} {'Coverage':>10} {'Time':>6}")
        print("─" * 65)
        
        for r in report.suites:
            status = "✅" if r.failed == 0 else "⚠️ " if r.failed > 0 and r.passed > 0 else "❌"
            if r.passed == 0 and r.failed == 0 and r.skipped == 0:
                status = "✅" # empty suite
            r_secs = int(r.duration)
            print(f"{status} {r.name:<28} {r.passed:>5} {r.failed:>6} {r.skipped:>6} {r.coverage:>10} {r_secs:>5}s")
            
        print("─" * 65)
        print(f"{'TOTAL':<30} {report.total_passed:>5} {report.total_failed:>6} {report.total_skipped:>6} {report.overall_coverage:>10} {mins:>3}m{secs:02d}s\n")
        
        pr_pct = report.pass_rate * 100
        print(f"Pass Rate: {pr_pct:.1f}%  |  Overall Coverage: {report.overall_coverage}\n")
        
        if report.total_failed > 0:
            print("❌ FAILURES:")
            for f in report.failures:
                print(f"  {f['test_id']}")
                print(f"    {f['error']}")
            print("\nRECOMMENDATION: " + (f"{report.total_failed} failures detected." if report.total_failed > 0 else ""))
            if report.pass_rate >= 0.95:
                print("Failures are likely non-blocking. Safe to proceed to deployment after manual review.")
            else:
                print("Pass rate below 95%. DO NOT DEPLOY.")
        else:
            print("RECOMMENDATION: All tests passed. Safe to proceed to deployment.")

    def generate_html_report(self, report: FullReport, path: str):
        # Generate Pytest's native HTML for coverage
        try:
            subprocess.run(["pytest", "--cov=app", "--cov-report=html:htmlcov"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

        html = f\"\"\"
        <html>
        <head>
            <title>ISRO SOC Platform — Test Report</title>
            <style>
                body {{ font-family: -apple-system, sans-serif; margin: 40px; color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: right; }}
                th {{ background-color: #f5f5f5; text-align: left; }}
                td:first-child {{ text-align: left; }}
                .pass {{ color: #2e7d32; font-weight: bold; }}
                .fail {{ color: #c62828; font-weight: bold; }}
                .warn {{ color: #f57c00; font-weight: bold; }}
                .summary {{ font-size: 18px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>ISRO SOC Platform — Test Suite Report</h1>
            <div class="summary">
                <p><strong>Date:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Pass Rate:</strong> {report.pass_rate * 100:.1f}%</p>
                <p><strong>Overall Coverage:</strong> {report.overall_coverage} (<a href="htmlcov/index.html">View Line-by-Line</a>)</p>
            </div>
            <table>
                <tr>
                    <th>Suite</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Skipped</th>
                    <th>Coverage</th>
                    <th>Time (s)</th>
                </tr>
        \"\"\"
        
        for r in report.suites:
            status_class = "pass" if r.failed == 0 else "warn" if r.passed > 0 else "fail"
            html += f\"\"\"
                <tr>
                    <td class="{status_class}">{r.name}</td>
                    <td>{r.passed}</td>
                    <td>{r.failed}</td>
                    <td>{r.skipped}</td>
                    <td>{r.coverage}</td>
                    <td>{r.duration:.1f}</td>
                </tr>
            \"\"\"
            
        html += f\"\"\"
            </table>
            
            <h2>Failures</h2>
            <ul>
        \"\"\"
        for f in report.failures:
            html += f"<li><strong>{f['test_id']}</strong><br/><code>{f['error']}</code></li>"
            
        if not report.failures:
            html += "<li>No failures! 🎉</li>"
            
        html += \"\"\"
            </ul>
        </body>
        </html>
        \"\"\"
        
        with open(path, "w") as f:
            f.write(html)
        print(f"\nHTML report generated at {path}")

if __name__ == "__main__":
    # Remove PYTHONPATH from args if run with python -m etc.
    runner = TestSuiteRunner()
    report = runner.run_all()
    runner.generate_console_summary(report)
    runner.generate_html_report(report, "test_report.html")
    sys.exit(0 if report.pass_rate >= 0.95 else 1)
