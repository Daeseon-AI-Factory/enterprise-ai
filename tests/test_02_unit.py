"""Level 2: Unit Tests — test internal logic without external calls."""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestToolRegistry:
    """Test the core ToolRegistry."""

    def _make_registry(self):
        from app.core.tool_registry import ToolRegistry, Tool
        return ToolRegistry(), Tool

    def test_register_and_list(self):
        registry, Tool = self._make_registry()

        async def dummy_handler(x: str) -> str:
            return f"got {x}"

        registry.register(Tool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            handler=dummy_handler,
        ))
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    def test_execute(self):
        registry, Tool = self._make_registry()

        async def adder(a: int, b: int) -> str:
            return str(a + b)

        registry.register(Tool(
            name="adder",
            description="Add numbers",
            parameters={},
            handler=adder,
        ))
        result = run_async(registry.execute("adder", {"a": 2, "b": 3}))
        assert result == "5"

    def test_execute_unknown_tool(self):
        registry, Tool = self._make_registry()
        result = run_async(registry.execute("nonexistent", {}))
        assert "error" in result.lower() or "not found" in result.lower()

    def test_openai_format(self):
        registry, Tool = self._make_registry()

        async def greet(name: str) -> str:
            return f"hi {name}"

        registry.register(Tool(
            name="greet",
            description="Say hello",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}},
            handler=greet,
        ))
        fmt = registry.to_openai_tools()
        assert len(fmt) == 1
        assert fmt[0]["type"] == "function"
        assert fmt[0]["function"]["name"] == "greet"

    def test_prompt_format(self):
        registry, Tool = self._make_registry()

        async def greet() -> str:
            return "hi"

        registry.register(Tool(
            name="greet",
            description="Say hello",
            parameters={"type": "object", "properties": {}},
            handler=greet,
        ))
        text = registry.to_prompt_block()
        assert "greet" in text
        assert "Say hello" in text

    def test_list_names(self):
        registry, Tool = self._make_registry()

        async def noop() -> str:
            return ""

        registry.register(Tool(name="a", description="", parameters={}, handler=noop))
        registry.register(Tool(name="b", description="", parameters={}, handler=noop))
        assert registry.list_names() == ["a", "b"]


class TestParseToolArguments:
    """Test argument parsing utility."""

    def test_json_args(self):
        from app.core.tool_registry import parse_tool_arguments
        result = parse_tool_arguments('{"name": "Alice", "age": 30}')
        assert result == {"name": "Alice", "age": 30}

    def test_kv_args(self):
        from app.core.tool_registry import parse_tool_arguments
        result = parse_tool_arguments('name=Alice, city=Seoul')
        assert result["name"] == "Alice"
        assert result["city"] == "Seoul"


class TestTrainingDataStore:
    """Test file-based training data storage."""

    def test_save_and_load(self):
        from app.core.training_data_store import TrainingDataStore

        store = TrainingDataStore()
        pairs = [{"question": "What is Python?", "answer": "A programming language."}]
        meta = store.save_dataset("unit_test_ds", pairs)
        assert meta["pair_count"] == 1

        loaded = store.load_dataset("unit_test_ds")
        assert len(loaded) == 1
        assert loaded[0]["question"] == "What is Python?"

        # Cleanup
        store.delete_dataset("unit_test_ds")

    def test_export_alpaca(self):
        from app.core.training_data_store import TrainingDataStore

        store = TrainingDataStore()
        store.save_dataset("unit_alpaca", [
            {"question": "Q1", "context": "C1", "answer": "A1"}
        ])
        data = store.export_as_alpaca("unit_alpaca")
        assert isinstance(data, list)
        assert data[0]["instruction"] == "Q1"
        assert data[0]["output"] == "A1"

        store.delete_dataset("unit_alpaca")

    def test_export_chat(self):
        from app.core.training_data_store import TrainingDataStore

        store = TrainingDataStore()
        store.save_dataset("unit_chat", [
            {"question": "Q1", "answer": "A1"}
        ])
        data = store.export_as_chat("unit_chat", system_prompt="You are a helper")
        assert isinstance(data, list)
        assert data[0]["messages"][0]["role"] == "system"
        assert data[0]["messages"][1]["role"] == "user"

        store.delete_dataset("unit_chat")

    def test_list_datasets(self):
        from app.core.training_data_store import TrainingDataStore

        store = TrainingDataStore()
        store.save_dataset("unit_list1", [{"question": "x", "answer": "y"}])
        store.save_dataset("unit_list2", [{"question": "a", "answer": "b"}])
        datasets = store.list_datasets()
        ids = [d["dataset_id"] for d in datasets]
        assert "unit_list1" in ids
        assert "unit_list2" in ids

        store.delete_dataset("unit_list1")
        store.delete_dataset("unit_list2")


class TestConfig:
    """Test config loading."""

    def test_settings_defaults(self):
        from app.config import settings
        assert settings.MODE in ("local", "airgap")
        assert settings.FUNCTION_CALLING_MODE in ("native", "prompt", "auto")

    def test_settings_model_field(self):
        from app.config import settings
        assert settings.LLM_MODEL


class TestSchedulerService:
    """Test scheduler registration and listing (sync-safe parts only)."""

    def test_register_handler(self):
        from app.services.scheduler_service import SchedulerService

        svc = SchedulerService()

        async def dummy():
            pass

        svc.register_handler("test_handler", dummy)
        assert "test_handler" in svc.list_handlers()

    def test_list_schedules_empty(self):
        from app.services.scheduler_service import SchedulerService

        svc = SchedulerService()
        assert svc.list_schedules() == []
