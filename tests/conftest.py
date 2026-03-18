"""Shared fixtures for all test levels."""

collect_ignore = ["test_05_load.py"]

import os
import pytest
from httpx import AsyncClient, ASGITransport

# Force test env before importing app
os.environ.setdefault("MODE", "local")
os.environ.setdefault("LLM_API_KEY", os.environ.get("LLM_API_KEY", "sk-test"))
os.environ.setdefault("CHROMA_PORT", "0")  # local ChromaDB, no Docker needed

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """Synchronous TestClient — fast, no event loop overhead."""
    from starlette.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client():
    """Async TestClient for testing async endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def has_api_key():
    """Check if real OpenAI API key is available."""
    key = os.environ.get("LLM_API_KEY", "")
    return key.startswith("sk-") and key != "sk-test" and key != "sk-xxx"
