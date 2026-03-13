"""Speech-to-Text Service — transcribe audio using Whisper.

Supports local Whisper model (for airgap) and OpenAI Whisper API.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services.chat_service import ChatService

_AUDIO_DIR = Path("./uploads/audio")


class SttService:
    def __init__(self):
        self._model = None
        self._chat = ChatService()
        _AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    def _get_model(self):
        """Lazy-load Whisper model."""
        if self._model is not None:
            return self._model

        whisper_path = settings.WHISPER_MODEL_PATH

        # Try local whisper model
        if os.path.isdir(whisper_path):
            try:
                import whisper
                self._model = whisper.load_model(whisper_path)
                logger.info(f"Loaded local Whisper model from {whisper_path}")
                return self._model
            except Exception as e:
                logger.warning(f"Failed to load local Whisper: {e}")

        # Try whisper package with model name
        try:
            import whisper
            model_name = "base"  # small enough for CPU
            self._model = whisper.load_model(model_name)
            logger.info(f"Loaded Whisper model: {model_name}")
            return self._model
        except ImportError:
            logger.warning("openai-whisper not installed")
        except Exception as e:
            logger.warning(f"Failed to load Whisper: {e}")

        return None

    async def transcribe(
        self,
        file_path: str,
        language: str | None = None,
    ) -> dict:
        """Transcribe audio file to text."""
        model = self._get_model()

        if model is None:
            # Fall back to OpenAI Whisper API
            return await self._transcribe_api(file_path, language)

        # Local Whisper
        try:
            import whisper
            options = {}
            if language:
                options["language"] = language

            result = model.transcribe(file_path, **options)
            text = result["text"]

            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                })

            return {
                "status": "ok",
                "text": text,
                "language": result.get("language", language or "unknown"),
                "segments": segments,
            }
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return {"status": "error", "message": str(e)}

    async def transcribe_and_chat(
        self,
        file_path: str,
        conversation_id: str | None = None,
        language: str | None = None,
    ) -> dict:
        """Transcribe audio then send to chat."""
        # Step 1: Transcribe
        result = await self.transcribe(file_path, language)
        if result["status"] != "ok":
            return result

        text = result["text"]
        if not text.strip():
            return {"status": "error", "message": "Transcription produced empty text"}

        # Step 2: Chat
        chat_result = await self._chat.chat(
            message=text,
            conversation_id=conversation_id,
        )

        return {
            "status": "ok",
            "transcription": text,
            "language": result.get("language", "unknown"),
            "reply": chat_result["reply"],
            "conversation_id": chat_result["conversation_id"],
        }

    async def _transcribe_api(self, file_path: str, language: str | None) -> dict:
        """Fallback: use OpenAI Whisper API."""
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=settings.LLM_API_BASE,
                api_key=settings.LLM_API_KEY,
            )
            with open(file_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language,
                )
            return {
                "status": "ok",
                "text": result.text,
                "language": language or "auto",
                "segments": [],
            }
        except Exception as e:
            logger.error(f"Whisper API fallback failed: {e}")
            return {"status": "error", "message": f"No Whisper model available. Install openai-whisper or configure API. Error: {e}"}
