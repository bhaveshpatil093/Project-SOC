# Load Test Scenarios

## Scenario 1: Normal SOC Shift
- **Duration:** 8 hours
- **Users:** 5 `SOCAnalystUser`, 1 `SOCSLMUser`, 1 `BackgroundSystemUser`
- **Target:** p95 response time < 500ms for alert endpoints.
- **Command:** `locust -f locustfile.py --users 7 --spawn-rate 1 --run-time 8h --headless --csv=results_shift`

## Scenario 2: Incident Surge (Major Attack Detected)
- **Duration:** 5 minutes
- **Users:** 20 concurrent users (mix of Analyst and SLM)
- **Target:** no 5xx errors, p95 < 2000ms.
- **Command:** `locust -f locustfile.py --users 20 --spawn-rate 5 --run-time 5m --headless --csv=results_surge`

## Scenario 3: SLM Load (Multiple Concurrent Chat Sessions)
- **Duration:** 10 minutes
- **Users:** 10 `SOCSLMUser`
- **Target:** p95 < 30s (SLM inference is slow).
- **Command:** `locust -f locustfile.py SOCSLMUser --users 10 --spawn-rate 2 --run-time 10m --headless --csv=results_slm`
