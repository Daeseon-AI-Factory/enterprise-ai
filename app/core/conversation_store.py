import json
import os
from pathlib import Path
from loguru import logger

STORE_DIR = Path("./data/conversations")


class ConversationStore:
    """File-based conversation persistence. Each conversation is a JSON file."""

    def __init__(self):
        STORE_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, conversation_id: str) -> Path:
        # Sanitize filename
        safe_id = conversation_id.replace("/", "_").replace("..", "_")
        return STORE_DIR / f"{safe_id}.json"

    def load(self, conversation_id: str) -> list[dict]:
        path = self._path(conversation_id)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load conversation {conversation_id}: {e}")
            return []

    def save(self, conversation_id: str, messages: list[dict]) -> None:
        path = self._path(conversation_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"Failed to save conversation {conversation_id}: {e}")

    def append(self, conversation_id: str, message: dict) -> None:
        messages = self.load(conversation_id)
        messages.append(message)
        self.save(conversation_id, messages)

    def list_conversations(self) -> list[dict]:
        results = []
        for path in sorted(STORE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    msgs = json.load(f)
                if msgs:
                    # Get first user message as preview
                    preview = next((m["content"][:100] for m in msgs if m["role"] == "user"), "")
                    results.append({
                        "id": path.stem,
                        "preview": preview,
                        "message_count": len(msgs),
                        "modified": os.path.getmtime(path),
                    })
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def delete(self, conversation_id: str) -> None:
        path = self._path(conversation_id)
        if path.exists():
            path.unlink()
