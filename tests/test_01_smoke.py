"""Level 1: Smoke Tests — verify the app boots and all routes exist."""

import pytest

pytestmark = pytest.mark.smoke


class TestAppBoot:
    """Verify the application starts and responds."""

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "mode" in data
        assert "model" in data

    def test_openapi_schema(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema["info"]["title"] == "Enterprise LLM Platform"
        assert schema["info"]["version"] == "0.2.0"

    def test_docs_page(self, client):
        r = client.get("/docs")
        assert r.status_code == 200


class TestRoutesRegistered:
    """Verify all API route prefixes are registered."""

    EXPECTED_PREFIXES = [
        "/api/chat",
        "/api/rag",
        "/api/text2sql",
        "/api/codegen",
        "/api/confluence",
        "/api/review",
        "/api/build",
        "/api/settings",
        "/api/agent",
        "/api/chat/smart",
        "/api/finetune",
        "/api/webhook",
        "/api/scheduler",
        "/api/ocr",
        "/api/stt",
        "/api/vision",
    ]

    def test_all_prefixes_exist(self, client):
        r = client.get("/openapi.json")
        paths = list(r.json()["paths"].keys())
        for prefix in self.EXPECTED_PREFIXES:
            matched = [p for p in paths if p.startswith(prefix)]
            assert matched, f"No routes found for prefix: {prefix}"

    def test_route_count(self, client):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        # Should have at least 25 endpoints
        total = sum(len(methods) for methods in paths.values())
        assert total >= 25, f"Only {total} endpoints found, expected >= 25"
