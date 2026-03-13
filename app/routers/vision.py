"""Vision router — image analysis using vision-capable LLM."""

import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form

from app.services.vision_service import VisionService

router = APIRouter()
service = VisionService()


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form("이 이미지를 분석해주세요."),
):
    """Analyze an image with a text prompt using vision model."""
    upload_dir = "uploads/vision"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return await service.analyze(image_path=file_path, prompt=prompt)


@router.post("/describe")
async def describe_image(file: UploadFile = File(...)):
    """Generate a description of an image."""
    upload_dir = "uploads/vision"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return await service.describe(image_path=file_path)
