import random
from locust import HttpUser, task, between

class SOCAnalystUser(HttpUser):
    """Simulates an L1 SOC analyst browsing the platform."""
    wait_time = between(1, 5)
    token = None
    headers = {}

    def on_start(self):
        # Login and store JWT token
        # In a real environment with mock endpoints, this creates the token
        response = self.client.post("/api/auth/login",
                                    json={"username": "analyst", "password": "analyst123"})
        
        # We fail gracefully if the environment isn't returning a token
        if response.status_code == 200 and "access_token" in response.json():
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    def get_random_alert_id(self):
        # In a full test, we'd extract an ID from the alerts list. Here we randomize.
        return f"alert-{random.randint(1000, 9999)}"

    @task(5)
    def view_alerts_list(self):
        self.client.get("/api/alerts/?limit=50&status=open",
                        headers=self.headers, name="GET /api/alerts")

    @task(3)
    def view_alert_detail(self):
        alert_id = self.get_random_alert_id()
        self.client.get(f"/api/alerts/{alert_id}",
                        headers=self.headers, name="GET /api/alerts/:id")

    @task(2)
    def view_dashboard_stats(self):
        self.client.get("/api/alerts/stats", headers=self.headers, name="GET /api/alerts/stats")

    @task(1)
    def submit_feedback(self):
        self.client.post("/api/feedback/",
                         json={
                             "alert_id": "test-001",
                             "entity_key": "10.0.0.1",
                             "label": "true_positive",
                             "notes": "load test"
                         },
                         headers=self.headers, name="POST /api/feedback/")

    @task(1)
    def view_incidents(self):
        self.client.get("/api/incidents/?limit=20", headers=self.headers, name="GET /api/incidents")


class SOCSLMUser(HttpUser):
    """Simulates analyst using the SLM chat."""
    wait_time = between(5, 15)  # SLM queries are slower
    headers = {}

    def on_start(self):
        # Login and store JWT token
        response = self.client.post("/api/auth/login",
                                    json={"username": "analyst", "password": "analyst123"})
        if response.status_code == 200 and "access_token" in response.json():
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(1)
    def chat_with_slm(self):
        self.client.post("/api/slm/chat",
                         json={"message": "Explain this alert", "alert_data": {"id": "test-001", "score": 0.9}},
                         headers=self.headers,
                         name="POST /api/slm/chat", timeout=60)


class BackgroundSystemUser(HttpUser):
    """Simulates background system operations."""
    wait_time = between(30, 60)

    @task(1)
    def trigger_scoring(self):
        self.client.post("/api/alerts/trigger-scoring", name="POST /api/alerts/trigger-scoring")

    @task(1)
    def health_check(self):
        self.client.get("/api/health", name="GET /api/health")
