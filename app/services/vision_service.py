"""Vision Service — image analysis using vision-capable LLM.

Uses OpenAI vision API format. Only works if the LLM supports vision
(GPT-4o, LLaVA, etc.). Gated behind VISION_MODEL config.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from loguru import logger

from app.config import settings
from app.llm_client import chat_completion


class VisionService:
    def _is_available(self) -> bool:
        """Check if vision model is configured."""
        return bool(settings.VISION_MODEL)

    async def analyze(self, image_path: str, prompt: str) -> dict:
        """Analyze an image with a text prompt."""
        if not self._is_available():
            return {
                "status": "error",
                "message": "Vision model not configured. Set VISION_MODEL in .env",
            }

        if not os.path.exists(image_path):
            return {"status": "error", "message": f"Image not found: {image_path}"}

        # Encode image as base64
        image_data = self._encode_image(image_path)
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }.get(ext, "image/png")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}",
                        },
                    },
                ],
            }
        ]

        try:
            response = chat_completion(
                messages=messages,
                model=settings.VISION_MODEL,
                max_tokens=2048,
            )
            return {
                "status": "ok",
                "analysis": response.choices[0].message.content,
                "model": settings.VISION_MODEL,
            }
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {"status": "error", "message": str(e)}

    async def describe(self, image_path: str) -> dict:
        """Generate a description of an image."""
        return await self.analyze(
            image_path=image_path,
            prompt="Describe this image in detail. If there is text in the image, transcribe it. Use the same language as any text found in the image, or Korean by default.",
        )

    @staticmethod
    def _encode_image(image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
