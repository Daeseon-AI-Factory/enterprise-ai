"""Fine-tuning Service — training data preparation and pipeline orchestration.

Builds Q&A pairs from RAG documents, validates data quality,
and generates training configs for LoRA/QLoRA fine-tuning.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from loguru import logger

from app.llm_client import chat_completion
from app.core.vector_store import get_vector_store
from app.core.training_data_store import TrainingDataStore


QA_GENERATION_PROMPT = """You are a training data generator. Given a text chunk from a document,
generate {num_pairs} diverse question-answer pairs that could be used to fine-tune an AI model.

Rules:
- Questions should be natural and diverse (what, how, why, when, etc.)
- Answers must be accurate and based ONLY on the provided text
- Include both simple factual questions and more complex reasoning questions
- Use the same language as the source text
- Return ONLY valid JSON array, no other text

Format:
[
  {{"question": "...", "answer": "...", "context": "...relevant part of the text..."}},
  ...
]

Text chunk:
{text}
"""


class FinetuneService:
    def __init__(self):
        self._vector_store = get_vector_store()
        self._data_store = TrainingDataStore()

    async def generate_qa_pairs(
        self,
        collection: str = "default",
        num_pairs_per_chunk: int = 3,
        max_chunks: int = 50,
        dataset_id: str | None = None,
    ) -> dict:
        """Generate Q&A training pairs from RAG document chunks."""
        dataset_id = dataset_id or f"qa_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Get chunks from vector store
        try:
            col = self._vector_store._get_collection(collection)
            result = col.get(limit=max_chunks, include=["documents", "metadatas"])
        except Exception as e:
            return {"status": "error", "message": f"Collection '{collection}' not found: {e}"}

        if not result["documents"]:
            return {"status": "error", "message": f"No documents in collection '{collection}'"}

        all_pairs = []
        errors = 0

        for i, (doc, meta) in enumerate(zip(result["documents"], result["metadatas"])):
            if not doc or len(doc.strip()) < 50:
                continue

            prompt = QA_GENERATION_PROMPT.format(
                num_pairs=num_pairs_per_chunk,
                text=doc[:2000],  # Limit input size
            )

            try:
                response = chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2048,
                )
                content = response.choices[0].message.content

                # Parse JSON from response
                pairs = self._extract_json_array(content)
                for pair in pairs:
                    pair["source_filename"] = meta.get("filename", "unknown")
                    pair["source_collection"] = collection
                    all_pairs.append(pair)

            except Exception as e:
                logger.warning(f"Failed to generate pairs for chunk {i}: {e}")
                errors += 1

            if i % 10 == 0:
                logger.info(f"Processing chunk {i+1}/{len(result['documents'])}, {len(all_pairs)} pairs so far")

        # Save dataset
        metadata = {
            "source_collection": collection,
            "chunks_processed": len(result["documents"]),
            "errors": errors,
            "pairs_per_chunk": num_pairs_per_chunk,
        }
        self._data_store.save_dataset(dataset_id, all_pairs, metadata)

        return {
            "status": "completed",
            "dataset_id": dataset_id,
            "total_pairs": len(all_pairs),
            "chunks_processed": len(result["documents"]),
            "errors": errors,
        }

    async def validate_dataset(self, dataset_id: str) -> dict:
        """Validate training data quality."""
        pairs = self._data_store.load_dataset(dataset_id)
        if not pairs:
            return {"status": "error", "message": "Dataset not found or empty"}

        issues = []
        valid_count = 0

        seen_questions = set()
        for i, pair in enumerate(pairs):
            q = pair.get("question", "").strip()
            a = pair.get("answer", "").strip()

            if not q:
                issues.append(f"Pair {i}: empty question")
                continue
            if not a:
                issues.append(f"Pair {i}: empty answer")
                continue
            if len(q) < 5:
                issues.append(f"Pair {i}: question too short ({len(q)} chars)")
                continue
            if len(a) < 10:
                issues.append(f"Pair {i}: answer too short ({len(a)} chars)")
                continue
            if q in seen_questions:
                issues.append(f"Pair {i}: duplicate question")
                continue

            seen_questions.add(q)
            valid_count += 1

        return {
            "dataset_id": dataset_id,
            "total_pairs": len(pairs),
            "valid_pairs": valid_count,
            "issues": issues[:50],  # Limit issues list
            "quality_score": round(valid_count / max(len(pairs), 1) * 100, 1),
        }

    async def export_dataset(
        self,
        dataset_id: str,
        format: str = "jsonl",
        system_prompt: str = "",
    ) -> dict:
        """Export dataset in various formats."""
        if format == "alpaca":
            data = self._data_store.export_as_alpaca(dataset_id)
        elif format == "chat":
            data = self._data_store.export_as_chat(dataset_id, system_prompt)
        else:  # jsonl (default)
            data = self._data_store.load_dataset(dataset_id)

        if not data:
            return {"status": "error", "message": "Dataset not found"}

        return {
            "status": "ok",
            "dataset_id": dataset_id,
            "format": format,
            "count": len(data),
            "data": data,
        }

    async def generate_training_config(
        self,
        dataset_id: str,
        base_model: str = "meta-llama/Llama-3.1-8B",
        lora_rank: int = 16,
        epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 4,
    ) -> dict:
        """Generate training configuration for LoRA fine-tuning."""
        meta = self._data_store.load_metadata(dataset_id)
        if not meta:
            return {"status": "error", "message": "Dataset not found"}

        # Axolotl config
        config = {
            "base_model": base_model,
            "model_type": "AutoModelForCausalLM",
            "tokenizer_type": "AutoTokenizer",
            "load_in_8bit": True,
            "adapter": "lora",
            "lora_r": lora_rank,
            "lora_alpha": lora_rank * 2,
            "lora_dropout": 0.05,
            "lora_target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
            "datasets": [{
                "path": f"data/finetune/{dataset_id}.jsonl",
                "type": "alpaca",
            }],
            "dataset_prepared_path": f"data/finetune/{dataset_id}_prepared",
            "num_epochs": epochs,
            "micro_batch_size": batch_size,
            "gradient_accumulation_steps": 4,
            "learning_rate": learning_rate,
            "optimizer": "adamw_torch",
            "lr_scheduler": "cosine",
            "warmup_steps": 10,
            "output_dir": f"./models/finetune/{dataset_id}",
            "logging_steps": 10,
            "save_steps": 100,
            "eval_steps": 50,
            "bf16": True,
            "tf32": True,
            "gradient_checkpointing": True,
            "flash_attention": True,
        }

        # Save config
        import yaml
        config_path = f"data/finetune/{dataset_id}_config.yml"
        try:
            import yaml
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
        except ImportError:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

        return {
            "status": "ok",
            "config": config,
            "config_path": config_path,
            "instructions": [
                f"1. 데이터셋 위치: data/finetune/{dataset_id}.jsonl ({meta['pair_count']} pairs)",
                f"2. 설정 파일: {config_path}",
                f"3. GPU 서버에서 실행: accelerate launch -m axolotl.cli.train {config_path}",
                "4. 학습 완료 후 LoRA 어댑터가 output_dir에 저장됩니다",
                "5. 추론 시 base_model + LoRA adapter를 결합하여 사용",
            ],
        }

    async def list_datasets(self) -> list[dict]:
        return self._data_store.list_datasets()

    async def delete_dataset(self, dataset_id: str) -> bool:
        return self._data_store.delete_dataset(dataset_id)

    @staticmethod
    def _extract_json_array(text: str) -> list[dict]:
        """Extract JSON array from LLM response text."""
        # Try to find JSON array in the text
        text = text.strip()
        # Remove markdown code blocks
        text = text.replace("```json", "").replace("```", "")

        # Find first [ and last ]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Try parsing entire text
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        return []
