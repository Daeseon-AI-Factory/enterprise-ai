"""Webhook router — receives events from n8n and external systems."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services.webhook_service import WebhookService

router = APIRouter()
service = WebhookService()


class ConfluenceSyncWebhook(BaseModel):
    base_url: str
    username: str
    api_token: str
    space_key: str
    collection: str | None = None
    full_sync: bool = False


class RagQueryWebhook(BaseModel):
    query: str
    collection: str = "default"
    top_k: int = 5


class Text2SqlWebhook(BaseModel):
    question: str
    schema_id: str | None = None


@router.post("/confluence-sync")
async def webhook_confluence_sync(req: ConfluenceSyncWebhook):
    """Trigger Confluence sync via webhook (n8n compatible)."""
    return await service.handle_confluence_sync(
        base_url=req.base_url,
        username=req.username,
        api_token=req.api_token,
        space_key=req.space_key,
        collection=req.collection,
        full_sync=req.full_sync,
    )


@router.post("/rag-query")
async def webhook_rag_query(req: RagQueryWebhook):
    """RAG query via webhook (n8n compatible)."""
    return await service.handle_rag_query(
        query=req.query,
        collection=req.collection,
        top_k=req.top_k,
    )


@router.post("/text2sql")
async def webhook_text2sql(req: Text2SqlWebhook):
    """Text2SQL via webhook (n8n compatible)."""
    return await service.handle_text2sql(
        question=req.question,
        schema_id=req.schema_id,
    )


@router.get("/health")
async def webhook_health():
    """Health check for n8n monitoring."""
    return {"status": "ok", "service": "enterprise-llm-webhook"}
