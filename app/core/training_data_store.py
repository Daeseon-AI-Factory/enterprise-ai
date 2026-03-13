"""Training Data Store — file-based storage for fine-tuning datasets."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

_FINETUNE_DIR = Path("./data/finetune")


class TrainingDataStore:
    """Stores and manages fine-tuning datasets as JSONL files."""

    def __init__(self):
        _FINETUNE_DIR.mkdir(parents=True, exist_ok=True)

    def save_dataset(
        self,
        dataset_id: str,
        pairs: list[dict],
        metadata: dict | None = None,
    ) -> dict:
        """Save a dataset of Q&A pairs."""
        data_path = _FINETUNE_DIR / f"{dataset_id}.jsonl"
        meta_path = _FINETUNE_DIR / f"{dataset_id}.meta.json"

        # Write JSONL
        with open(data_path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        # Write metadata
        meta = {
            "dataset_id": dataset_id,
            "pair_count": len(pairs),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved dataset '{dataset_id}': {len(pairs)} pairs")
        return meta

    def load_dataset(self, dataset_id: str) -> list[dict]:
        """Load a dataset by ID."""
        path = _FINETUNE_DIR / f"{dataset_id}.jsonl"
        if not path.exists():
            return []
        pairs = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    pairs.append(json.loads(line))
        return pairs

    def load_metadata(self, dataset_id: str) -> dict | None:
        """Load dataset metadata."""
        path = _FINETUNE_DIR / f"{dataset_id}.meta.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_datasets(self) -> list[dict]:
        """List all datasets with metadata."""
        results = []
        for f in sorted(_FINETUNE_DIR.glob("*.meta.json"), key=os.path.getmtime, reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    results.append(json.load(fh))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and its metadata."""
        data_path = _FINETUNE_DIR / f"{dataset_id}.jsonl"
        meta_path = _FINETUNE_DIR / f"{dataset_id}.meta.json"
        deleted = False
        for p in [data_path, meta_path]:
            if p.exists():
                p.unlink()
                deleted = True
        return deleted

    def export_as_alpaca(self, dataset_id: str) -> list[dict]:
        """Export dataset in Alpaca format (instruction, input, output)."""
        pairs = self.load_dataset(dataset_id)
        return [
            {
                "instruction": p.get("question", p.get("instruction", "")),
                "input": p.get("context", p.get("input", "")),
                "output": p.get("answer", p.get("output", "")),
            }
            for p in pairs
        ]

    def export_as_chat(self, dataset_id: str, system_prompt: str = "") -> list[dict]:
        """Export dataset in OpenAI chat format (messages array)."""
        pairs = self.load_dataset(dataset_id)
        result = []
        for p in pairs:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            q = p.get("question", p.get("instruction", ""))
            ctx = p.get("context", p.get("input", ""))
            if ctx:
                q = f"Context: {ctx}\n\nQuestion: {q}"
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": p.get("answer", p.get("output", ""))})
            result.append({"messages": messages})
        return result
