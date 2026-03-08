"""Persistent settings service — saves user configs to JSON files.

Stores: Confluence connections, Build presets, platform preferences.
All stored locally in ./data/settings/ for air-gapped environments.
"""

from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger

_SETTINGS_DIR = "./data/settings"


class SettingsService:
    def _path(self, key: str) -> str:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        return os.path.join(_SETTINGS_DIR, f"{key}.json")

    async def get(self, key: str) -> Any:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    async def save(self, key: str, data: Any) -> None:
        path = self._path(key)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Settings saved: {key}")

    async def delete(self, key: str) -> bool:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def list_keys(self) -> list[str]:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        return [f.replace(".json", "") for f in os.listdir(_SETTINGS_DIR) if f.endswith(".json")]
