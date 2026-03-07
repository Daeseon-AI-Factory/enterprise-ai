from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.chat_service import ChatService

router = APIRouter()
service = ChatService()


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    context: dict | None = None  # page URL, component name from widget


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Basic chat completion."""
    result = await service.chat(
        message=req.message,
        conversation_id=req.conversation_id,
    )
    return result


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """Streaming chat via SSE."""
    return StreamingResponse(
        service.chat_stream(
            message=req.message,
            conversation_id=req.conversation_id,
        ),
        media_type="text/event-stream",
    )


@router.post("/with-context", response_model=ChatResponse)
async def chat_with_context(req: ChatRequest):
    """Chat with page/code context (used by widget)."""
    result = await service.chat_with_context(
        message=req.message,
        conversation_id=req.conversation_id,
        context=req.context or {},
    )
    return result


@router.get("/conversations")
async def list_conversations():
    """List all saved conversations."""
    return await service.list_conversations()


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history."""
    return await service.get_conversation(conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    await service.delete_conversation(conversation_id)
    return {"status": "deleted"}
