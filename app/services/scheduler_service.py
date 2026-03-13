"""Scheduler Service — background task scheduling with cron-like support.

Uses asyncio for lightweight scheduling without external dependencies.
Persists schedule config to disk for restart recovery.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Awaitable

from loguru import logger

_SCHEDULE_FILE = Path("./data/schedules.json")
_SCHEDULE_HISTORY = Path("./data/schedule_history")


class ScheduledTask:
    """A scheduled recurring task."""
    def __init__(
        self,
        name: str,
        handler_name: str,
        interval_minutes: int,
        kwargs: dict[str, Any] | None = None,
        enabled: bool = True,
    ):
        self.name = name
        self.handler_name = handler_name
        self.interval_minutes = interval_minutes
        self.kwargs = kwargs or {}
        self.enabled = enabled
        self.last_run: str | None = None
        self.next_run: str | None = None
        self._task: asyncio.Task | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "handler_name": self.handler_name,
            "interval_minutes": self.interval_minutes,
            "kwargs": self.kwargs,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "next_run": self.next_run,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduledTask:
        task = cls(
            name=data["name"],
            handler_name=data["handler_name"],
            interval_minutes=data["interval_minutes"],
            kwargs=data.get("kwargs", {}),
            enabled=data.get("enabled", True),
        )
        task.last_run = data.get("last_run")
        task.next_run = data.get("next_run")
        return task


class SchedulerService:
    """Background task scheduler with persistence."""

    def __init__(self):
        self._schedules: dict[str, ScheduledTask] = {}
        self._handlers: dict[str, Callable[..., Awaitable]] = {}
        _SCHEDULE_HISTORY.mkdir(parents=True, exist_ok=True)

    def register_handler(self, name: str, handler: Callable[..., Awaitable]) -> None:
        """Register a named handler that can be used in schedules."""
        self._handlers[name] = handler
        logger.debug(f"Registered schedule handler: {name}")

    async def add_schedule(
        self,
        name: str,
        handler_name: str,
        interval_minutes: int,
        kwargs: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict:
        """Create a new scheduled task."""
        if handler_name not in self._handlers:
            return {"status": "error", "message": f"Handler '{handler_name}' not registered. Available: {list(self._handlers.keys())}"}

        # Stop existing schedule with same name
        if name in self._schedules:
            await self.remove_schedule(name)

        task = ScheduledTask(
            name=name,
            handler_name=handler_name,
            interval_minutes=interval_minutes,
            kwargs=kwargs,
            enabled=enabled,
        )
        self._schedules[name] = task
        self._save_schedules()

        if enabled:
            self._start_task(task)

        logger.info(f"Added schedule '{name}': {handler_name} every {interval_minutes}min")
        return {"status": "created", "schedule": task.to_dict()}

    async def remove_schedule(self, name: str) -> bool:
        """Remove a scheduled task."""
        task = self._schedules.pop(name, None)
        if task and task._task:
            task._task.cancel()
        self._save_schedules()
        return task is not None

    async def run_now(self, name: str) -> dict:
        """Manually trigger a scheduled task immediately."""
        task = self._schedules.get(name)
        if not task:
            return {"status": "error", "message": f"Schedule '{name}' not found"}

        handler = self._handlers.get(task.handler_name)
        if not handler:
            return {"status": "error", "message": f"Handler '{task.handler_name}' not found"}

        try:
            result = await handler(**task.kwargs)
            task.last_run = datetime.now(timezone.utc).isoformat()
            self._save_schedules()
            self._save_history(task, "manual", result)
            return {"status": "ok", "result": result}
        except Exception as e:
            logger.error(f"Manual run of '{name}' failed: {e}")
            self._save_history(task, "manual_failed", str(e))
            return {"status": "error", "message": str(e)}

    def list_schedules(self) -> list[dict]:
        return [t.to_dict() for t in self._schedules.values()]

    def list_handlers(self) -> list[str]:
        return list(self._handlers.keys())

    def get_history(self, name: str, limit: int = 20) -> list[dict]:
        """Get execution history for a schedule."""
        history_file = _SCHEDULE_HISTORY / f"{name}.jsonl"
        if not history_file.exists():
            return []
        lines = history_file.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in reversed(lines[-limit:]):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    # --- Lifecycle ---

    async def start(self) -> None:
        """Load saved schedules and start them. Called on app startup."""
        self._load_schedules()
        for task in self._schedules.values():
            if task.enabled:
                self._start_task(task)
        logger.info(f"Scheduler started with {len(self._schedules)} schedules")

    async def stop(self) -> None:
        """Stop all scheduled tasks. Called on app shutdown."""
        for task in self._schedules.values():
            if task._task:
                task._task.cancel()
        logger.info("Scheduler stopped")

    # --- Internal ---

    def _start_task(self, task: ScheduledTask) -> None:
        """Start the asyncio background loop for a task."""
        async def loop():
            while True:
                await asyncio.sleep(task.interval_minutes * 60)
                handler = self._handlers.get(task.handler_name)
                if not handler:
                    continue
                try:
                    result = await handler(**task.kwargs)
                    task.last_run = datetime.now(timezone.utc).isoformat()
                    self._save_schedules()
                    self._save_history(task, "auto", result)
                    logger.info(f"Scheduled task '{task.name}' completed")
                except Exception as e:
                    logger.error(f"Scheduled task '{task.name}' failed: {e}")
                    self._save_history(task, "auto_failed", str(e))

        task._task = asyncio.create_task(loop())

    def _save_schedules(self) -> None:
        _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [t.to_dict() for t in self._schedules.values()]
        with open(_SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_schedules(self) -> None:
        if not _SCHEDULE_FILE.exists():
            return
        try:
            with open(_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                task = ScheduledTask.from_dict(item)
                self._schedules[task.name] = task
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load schedules: {e}")

    def _save_history(self, task: ScheduledTask, trigger: str, result: Any) -> None:
        history_file = _SCHEDULE_HISTORY / f"{task.name}.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "result": str(result)[:1000] if result else None,
        }
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
