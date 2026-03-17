"""Level 5: Load Test — Locust-based performance testing.

Run standalone:  locust -f tests/test_05_load.py --headless -u 50 -r 10 -t 60s --host http://localhost:8000
Run with web UI: locust -f tests/test_05_load.py --host http://localhost:8000
"""

try:
    from locust import HttpUser, task, between, tag
except ImportError:
    import sys
    print("Install locust: pip install locust")
    sys.exit(1)


class HealthCheckUser(HttpUser):
    """Basic health check load — tests raw throughput."""
    wait_time = between(0.1, 0.5)

    @tag("health")
    @task(10)
    def health(self):
        self.client.get("/health")

    @tag("docs")
    @task(1)
    def openapi(self):
        self.client.get("/openapi.json")


class APIUser(HttpUser):
    """Simulates real user behavior across multiple endpoints."""
    wait_time = between(1, 3)

    @tag("tools")
    @task(5)
    def list_agent_tools(self):
        self.client.get("/api/agent/tools")

    @tag("scheduler")
    @task(3)
    def list_schedules(self):
        self.client.get("/api/scheduler/list")

    @tag("webhook")
    @task(2)
    def webhook_health(self):
        self.client.get("/api/webhook/health")

    @tag("finetune")
    @task(2)
    def list_datasets(self):
        self.client.get("/api/finetune/datasets")

    @tag("rag")
    @task(2)
    def list_collections(self):
        self.client.get("/api/rag/collections")

    @tag("settings")
    @task(1)
    def get_settings(self):
        self.client.get("/api/settings/")

    @tag("chat")
    @task(1)
    def chat(self):
        """Light chat test — only runs if API key is set."""
        with self.client.post("/api/chat/", json={
            "message": "Say OK",
        }, catch_response=True) as r:
            if r.status_code == 401:
                r.success()  # Expected without API key
            elif r.status_code == 200:
                r.success()
