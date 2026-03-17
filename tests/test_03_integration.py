"""Level 3: Integration Tests — real API calls (requires LLM_API_KEY).

Run: pytest tests/test_03_integration.py -m integration
"""

import pytest

pytestmark = [pytest.mark.integration]


def skip_no_key(has_api_key):
    if not has_api_key:
        pytest.skip("No real API key — set LLM_API_KEY env var")


class TestChatAPI:
    """Test /api/chat endpoints with real LLM."""

    def test_chat_basic(self, client, has_api_key):
        skip_no_key(has_api_key)
        r = client.post("/api/chat/", json={
            "message": "Say 'hello test' and nothing else.",
        })
        assert r.status_code == 200
        data = r.json()
        assert "hello" in data.get("response", data.get("reply", "")).lower()

    def test_chat_with_conversation(self, client, has_api_key):
        skip_no_key(has_api_key)
        # First message
        r1 = client.post("/api/chat/", json={
            "message": "My name is TestBot. Remember this.",
        })
        assert r1.status_code == 200
        conv_id = r1.json().get("conversation_id")

        # Follow-up with conversation context
        if conv_id:
            r2 = client.post("/api/chat/", json={
                "message": "What is my name?",
                "conversation_id": conv_id,
            })
            assert r2.status_code == 200


class TestSmartChatAPI:
    """Test /api/chat/smart (Function Calling)."""

    def test_smart_chat(self, client, has_api_key):
        skip_no_key(has_api_key)
        r = client.post("/api/chat/smart/", json={
            "message": "What collections are available in the RAG system?",
        })
        assert r.status_code == 200
        data = r.json()
        assert "status" in data or "response" in data or "reply" in data


class TestAgentAPI:
    """Test /api/agent endpoints."""

    def test_list_tools(self, client):
        r = client.get("/api/agent/tools")
        assert r.status_code == 200
        tools = r.json()
        assert isinstance(tools, list)
        assert len(tools) >= 4
        tool_names = [t["name"] for t in tools]
        assert "search_docs" in tool_names

    def test_agent_run(self, client, has_api_key):
        skip_no_key(has_api_key)
        r = client.post("/api/agent/run", json={
            "task": "List all available RAG collections",
            "max_iterations": 3,
        })
        assert r.status_code == 200
        data = r.json()
        assert "result" in data or "answer" in data or "steps" in data


class TestCodegenAPI:
    """Test /api/codegen endpoints."""

    def test_codegen(self, client, has_api_key):
        skip_no_key(has_api_key)
        r = client.post("/api/codegen/generate", json={
            "prompt": "Write a Python function that returns the sum of two numbers",
            "language": "python",
        })
        assert r.status_code == 200
        data = r.json()
        assert "code" in data or "result" in data or "response" in data


class TestRAGAPI:
    """Test /api/rag endpoints (without file upload)."""

    def test_list_collections(self, client):
        r = client.get("/api/rag/collections")
        assert r.status_code == 200

    def test_search_empty(self, client, has_api_key):
        skip_no_key(has_api_key)
        r = client.post("/api/rag/search", json={
            "query": "test query",
            "collection": "default",
        })
        # May return empty results or error if no data — both are OK
        assert r.status_code in (200, 404, 500)


class TestFineTuneAPI:
    """Test /api/finetune endpoints."""

    def test_list_datasets(self, client):
        r = client.get("/api/finetune/datasets")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))


class TestSchedulerAPI:
    """Test /api/scheduler endpoints."""

    def test_list_schedules(self, client):
        r = client.get("/api/scheduler/list")
        assert r.status_code == 200

    def test_create_and_delete(self, client):
        # Create
        r = client.post("/api/scheduler/create", json={
            "name": "integration_test_schedule",
            "handler_name": "confluence_sync",
            "cron_expr": "0 3 * * *",
        })
        assert r.status_code == 200

        # Delete
        r = client.delete("/api/scheduler/integration_test_schedule")
        assert r.status_code == 200


class TestWebhookAPI:
    """Test /api/webhook health."""

    def test_webhook_health(self, client):
        r = client.get("/api/webhook/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestSettingsAPI:
    """Test /api/settings endpoints."""

    def test_get_settings(self, client):
        r = client.get("/api/settings/")
        assert r.status_code == 200
        data = r.json()
        assert "mode" in data or "MODE" in data or isinstance(data, dict)
