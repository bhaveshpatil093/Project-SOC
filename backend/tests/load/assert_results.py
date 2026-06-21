import csv
import sys
import os

def assert_load_test_results(csv_filepath):
    if not os.path.exists(csv_filepath):
        print(f"Error: Results file {csv_filepath} not found.")
        sys.exit(1)

    # Thresholds
    P50_ALERTS_MS = 200
    P95_ALERTS_MS = 500
    MAX_ERROR_RATE = 0.01

    failed = False

    with open(csv_filepath, mode='r') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            name = row.get("Name")
            reqs = int(row.get("Request Count", 0))
            fails = int(row.get("Failure Count", 0))
            p50 = float(row.get("50%", 0))
            p95 = float(row.get("95%", 0))
            
            # Skip the aggregate row
            if name == "Aggregated":
                continue
                
            error_rate = fails / reqs if reqs > 0 else 0

            # Global Error Rate Assertion
            if error_rate > MAX_ERROR_RATE:
                print(f"FAIL: {name} error rate {error_rate:.2%} > {MAX_ERROR_RATE:.2%}")
                failed = True
                
            # Specific assertions for GET /api/alerts
            if name == "GET /api/alerts":
                if p50 > P50_ALERTS_MS:
                    print(f"FAIL: {name} p50 response time {p50}ms > {P50_ALERTS_MS}ms")
                    failed = True
                if p95 > P95_ALERTS_MS:
                    print(f"FAIL: {name} p95 response time {p95}ms > {P95_ALERTS_MS}ms")
                    failed = True

    if failed:
        print("Load test assertions failed.")
        sys.exit(1)
    else:
        print("All load test assertions passed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python assert_results.py <path_to_locust_stats.csv>")
        sys.exit(1)
    
    assert_load_test_results(sys.argv[1])
