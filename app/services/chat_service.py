import json
import uuid
from typing import AsyncGenerator

from loguru import logger

from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_CHAT
from app.core.conversation_store import ConversationStore


class ChatService:
    def __init__(self):
        self._store = ConversationStore()

    async def chat(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> dict:
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)

        messages = [{"role": "system", "content": SYSTEM_CHAT}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        response = chat_completion(messages=messages)
        reply = response.choices[0].message.content

        # Persist
        self._store.append(conv_id, {"role": "user", "content": message})
        self._store.append(conv_id, {"role": "assistant", "content": reply})

        logger.info(f"Chat [{conv_id[:8]}]: {message[:50]}...")
        return {"reply": reply, "conversation_id": conv_id}

    async def chat_stream(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)

        messages = [{"role": "system", "content": SYSTEM_CHAT}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        stream = chat_completion(messages=messages, stream=True)
        full_reply = ""

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full_reply += delta
            yield f"data: {json.dumps({'content': delta, 'conversation_id': conv_id})}\n\n"

        # Persist
        self._store.append(conv_id, {"role": "user", "content": message})
        self._store.append(conv_id, {"role": "assistant", "content": full_reply})

        yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"

    async def chat_with_context(
        self,
        message: str,
        conversation_id: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Chat with additional page/code context from the widget."""
        context = context or {}
        context_str = ""
        if context.get("page_url"):
            context_str += f"\nCurrent page: {context['page_url']}"
        if context.get("component"):
            context_str += f"\nComponent: {context['component']}"

        enhanced_message = message
        if context_str:
            enhanced_message = f"[Context]{context_str}\n\n[Question] {message}"

        return await self.chat(
            message=enhanced_message,
            conversation_id=conversation_id,
        )

    async def list_conversations(self) -> list[dict]:
        return self._store.list_conversations()

    async def get_conversation(self, conversation_id: str) -> list[dict]:
        return self._store.load(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> None:
        self._store.delete(conversation_id)
