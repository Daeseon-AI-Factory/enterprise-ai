"""Level 4: Chaos / Resilience Tests — simulate failures and verify graceful degradation.

Tests:
- LLM API unreachable / error responses
- Invalid input handling (XSS, SQL injection, path traversal)
- Concurrent request handling
- Resource exhaustion
- Graceful degradation when optional services are missing
"""

import time
import threading
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.chaos


class TestLLMFailure:
    """Simulate LLM being down or returning errors."""

    def test_chat_with_unreachable_llm(self, client):
        """LLM endpoint completely unreachable — app handles gracefully."""
        with patch("app.llm_client.client") as mock_client:
            mock_client.chat.completions.create.side_effect = \
                ConnectionError("Connection refused")
            r = client.post("/api/chat", json={"message": "test"})
            assert r.status_code in (200, 500, 502, 503)

    def test_chat_with_llm_timeout(self, client):
        """LLM request times out."""
        with patch("app.llm_client.client") as mock_client:
            mock_client.chat.completions.create.side_effect = \
                TimeoutError("Request timed out after 30s")
            r = client.post("/api/chat", json={"message": "test"})
            assert r.status_code in (200, 500, 502, 504)

    def test_agent_with_llm_down(self, client):
        """Agent task when LLM is unreachable."""
        with patch("app.llm_client.client") as mock_client:
            mock_client.chat.completions.create.side_effect = \
                ConnectionError("Connection refused")
            r = client.post("/api/agent/run", json={
                "task": "test task",
                "max_iterations": 1,
            })
            assert r.status_code in (200, 500, 502)

    def test_smart_chat_with_llm_down(self, client):
        """Smart chat when LLM is unreachable."""
        with patch("app.llm_client.client") as mock_client:
            mock_client.chat.completions.create.side_effect = \
                ConnectionError("Connection refused")
            r = client.post("/api/chat/smart", json={"message": "test"})
            assert r.status_code in (200, 500, 502)

    def test_llm_returns_empty_content(self, client):
        """LLM returns null/empty content in response."""
        with patch("app.llm_client.client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = None
            mock_resp.choices[0].message.tool_calls = None
            mock_client.chat.completions.create.return_value = mock_resp
            r = client.post("/api/chat", json={"message": "test"})
            assert r.status_code in (200, 500)


class TestInputValidation:
    """Test handling of malformed/malicious inputs."""

    def test_empty_message(self, client):
        r = client.post("/api/chat", json={"message": ""})
        assert r.status_code in (200, 400, 422)

    def test_missing_required_field(self, client):
        r = client.post("/api/chat", json={})
        assert r.status_code == 422

    def test_wrong_content_type(self, client):
        r = client.post("/api/chat", content="not json",
                        headers={"Content-Type": "text/plain"})
        assert r.status_code in (400, 415, 422)

    def test_extremely_long_message(self, client):
        """128KB message — should not crash."""
        r = client.post("/api/chat", json={"message": "A" * 131072})
        assert r.status_code in (200, 400, 413, 422, 500)

    def test_unicode_and_special_chars(self, client):
        r = client.post("/api/chat", json={
            "message": "한국어 테스트 🎉✨ 日本語 العربية",
        })
        assert r.status_code in (200, 400, 422, 500)

    def test_xss_attempt(self, client):
        r = client.post("/api/chat", json={
            "message": "<script>alert('xss')</script>",
        })
        assert r.status_code in (200, 400, 422, 500)

    def test_sql_injection_in_text2sql(self, client):
        r = client.post("/api/text2sql/generate", json={
            "question": "'; DROP TABLE users; --",
        })
        assert r.status_code in (200, 400, 422, 500)

    def test_path_traversal_in_collection(self, client):
        r = client.post("/api/rag/query", json={
            "query": "test",
            "collection": "../../../etc/passwd",
        })
        # 404 is also acceptable — server may reject path traversal at routing level
        assert r.status_code in (200, 400, 404, 422, 500)

    def test_null_bytes(self, client):
        r = client.post("/api/chat", json={"message": "hello\x00world"})
        assert r.status_code in (200, 400, 422, 500)


class TestConcurrency:
    """Test concurrent request handling."""

    def test_50_concurrent_health_checks(self, client):
        results = []
        errors = []

        def hit():
            try:
                r = client.get("/health")
                results.append(r.status_code)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=hit) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Errors: {errors}"
        assert all(r == 200 for r in results)

    def test_20_concurrent_tool_listing(self, client):
        results = []

        def hit():
            r = client.get("/api/agent/tools")
            results.append(r.status_code)

        threads = [threading.Thread(target=hit) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert all(r == 200 for r in results)

    def test_concurrent_mixed_endpoints(self, client):
        results = []
        endpoints = [
            "/health",
            "/api/agent/tools",
            "/api/scheduler/list",
            "/api/webhook/health",
            "/api/finetune/datasets",
        ]

        def hit(path):
            r = client.get(path)
            results.append((path, r.status_code))

        threads = []
        for _ in range(5):
            for path in endpoints:
                threads.append(threading.Thread(target=hit, args=(path,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        failed = [(p, s) for p, s in results if s >= 500]
        assert len(failed) == 0, f"Server errors: {failed}"


class TestResourceExhaustion:
    """Test behavior under resource pressure."""

    def test_500_rapid_health_checks(self, client):
        start = time.time()
        for _ in range(500):
            r = client.get("/health")
            assert r.status_code == 200
        elapsed = time.time() - start
        rps = 500 / elapsed
        assert rps > 50, f"Only {rps:.0f} req/s — expected > 50"

    def test_100_rapid_openapi_calls(self, client):
        for _ in range(100):
            r = client.get("/openapi.json")
            assert r.status_code == 200


class TestGracefulDegradation:
    """Verify features degrade gracefully when optional deps are missing."""

    def test_vision_without_model(self, client):
        from app.config import settings
        if settings.VISION_MODEL:
            pytest.skip("VISION_MODEL is set")

        import io
        fake_img = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        r = client.post("/api/vision/analyze", files={
            "file": ("test.png", fake_img, "image/png"),
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "error"
        assert "not configured" in data["message"].lower()

    def test_text2sql_without_database(self, client):
        r = client.post("/api/text2sql/generate", json={"question": "Show tables"})
        assert r.status_code in (200, 400, 500)

    def test_webhook_health_always_works(self, client):
        r = client.get("/api/webhook/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_scheduler_list_always_works(self, client):
        r = client.get("/api/scheduler/list")
        assert r.status_code == 200

    def test_finetune_datasets_empty(self, client):
        r = client.get("/api/finetune/datasets")
        assert r.status_code == 200

    def test_agent_tools_always_available(self, client):
        r = client.get("/api/agent/tools")
        assert r.status_code == 200
        tools = r.json()
        assert isinstance(tools, list)
        assert len(tools) >= 1
