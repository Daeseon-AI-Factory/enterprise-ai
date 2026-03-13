"""Webhook Service — receives events from n8n and other external systems."""

from __future__ import annotations

import hashlib
import hmac

from loguru import logger

from app.config import settings
from app.services.confluence_service import ConfluenceService
from app.services.rag_service import RagService
from app.services.text2sql_service import Text2SqlService


class WebhookService:
    def __init__(self):
        self._confluence = ConfluenceService()
        self._rag = RagService()
        self._text2sql = Text2SqlService()

    def validate_secret(self, payload: bytes, signature: str) -> bool:
        """Validate webhook HMAC signature."""
        if not settings.WEBHOOK_SECRET:
            return True  # No secret configured, allow all
        expected = hmac.new(
            settings.WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_confluence_sync(
        self,
        base_url: str,
        username: str,
        api_token: str,
        space_key: str,
        collection: str | None = None,
        full_sync: bool = False,
    ) -> dict:
        """Trigger Confluence sync (callable from n8n or scheduler)."""
        logger.info(f"Webhook: Confluence sync triggered for space '{space_key}'")
        return await self._confluence.sync_space(
            base_url=base_url,
            username=username,
            api_token=api_token,
            space_key=space_key,
            collection=collection,
            full_sync=full_sync,
        )

    async def handle_rag_query(self, query: str, collection: str = "default", top_k: int = 5) -> dict:
        """Simplified RAG query for n8n integration."""
        logger.info(f"Webhook: RAG query '{query[:50]}...'")
        return await self._rag.query(query=query, collection=collection, top_k=top_k)

    async def handle_text2sql(self, question: str, schema_id: str | None = None) -> dict:
        """Simplified Text2SQL for n8n integration."""
        logger.info(f"Webhook: Text2SQL '{question[:50]}...'")
        return await self._text2sql.generate(question=question, schema_id=schema_id)
