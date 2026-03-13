"""Speech-to-Text router — transcribe audio files."""

import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form

from app.services.stt_service import SttService

router = APIRouter()
service = SttService()


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(None),
):
    """Transcribe audio file to text."""
    upload_dir = "uploads/audio"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return await service.transcribe(file_path, language)


@router.post("/chat")
async def transcribe_and_chat(
    file: UploadFile = File(...),
    conversation_id: str = Form(None),
    language: str = Form(None),
):
    """Transcribe audio then send to AI chat in one call."""
    upload_dir = "uploads/audio"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return await service.transcribe_and_chat(
        file_path=file_path,
        conversation_id=conversation_id,
        language=language,
    )
