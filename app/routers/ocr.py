"""OCR router — extract text from images and scanned PDFs."""

import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form

from app.services.ocr_service import OcrService

router = APIRouter()
service = OcrService()


@router.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """Extract text from an image or scanned PDF using OCR."""
    upload_dir = "uploads/ocr"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return await service.extract_text(file_path)


@router.post("/upload")
async def ocr_and_index(
    file: UploadFile = File(...),
    collection: str = Form("default"),
):
    """OCR + index into RAG vector database (like /api/rag/upload but for images)."""
    upload_dir = "uploads/ocr"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return await service.extract_and_index(
        file_path=file_path,
        filename=file.filename,
        collection=collection,
    )
