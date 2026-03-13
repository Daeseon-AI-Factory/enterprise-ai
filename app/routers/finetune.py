"""Fine-tuning router — training data generation and pipeline management."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.finetune_service import FinetuneService

router = APIRouter()
service = FinetuneService()


class GenerateDataRequest(BaseModel):
    collection: str = "default"
    num_pairs_per_chunk: int = 3
    max_chunks: int = 50
    dataset_id: str | None = None


class ExportRequest(BaseModel):
    dataset_id: str
    format: str = "jsonl"  # jsonl, alpaca, chat
    system_prompt: str = ""


class TrainingConfigRequest(BaseModel):
    dataset_id: str
    base_model: str = "meta-llama/Llama-3.1-8B"
    lora_rank: int = 16
    epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4


@router.post("/generate-data")
async def generate_training_data(req: GenerateDataRequest):
    """Generate Q&A training pairs from RAG documents."""
    return await service.generate_qa_pairs(
        collection=req.collection,
        num_pairs_per_chunk=req.num_pairs_per_chunk,
        max_chunks=req.max_chunks,
        dataset_id=req.dataset_id,
    )


@router.post("/validate/{dataset_id}")
async def validate_dataset(dataset_id: str):
    """Validate training data quality."""
    return await service.validate_dataset(dataset_id)


@router.post("/export")
async def export_dataset(req: ExportRequest):
    """Export dataset in various formats (jsonl, alpaca, chat)."""
    return await service.export_dataset(
        dataset_id=req.dataset_id,
        format=req.format,
        system_prompt=req.system_prompt,
    )


@router.post("/config")
async def generate_config(req: TrainingConfigRequest):
    """Generate LoRA training configuration file."""
    return await service.generate_training_config(
        dataset_id=req.dataset_id,
        base_model=req.base_model,
        lora_rank=req.lora_rank,
        epochs=req.epochs,
        learning_rate=req.learning_rate,
        batch_size=req.batch_size,
    )


@router.get("/datasets")
async def list_datasets():
    """List all generated training datasets."""
    return await service.list_datasets()


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a training dataset."""
    deleted = await service.delete_dataset(dataset_id)
    return {"status": "deleted" if deleted else "not_found", "dataset_id": dataset_id}
