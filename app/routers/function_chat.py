"""Smart Chat router — chat with automatic function calling / tool use."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.agent_service import AgentService
from app.services.function_chat_service import FunctionChatService

router = APIRouter()

# Share the tool registry from agent service
_agent = AgentService()
service = FunctionChatService(registry=_agent.registry)


class SmartChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    enabled_tools: list[str] | None = None  # None = all tools


class SmartChatResponse(BaseModel):
    reply: str
    conversation_id: str
    tools_used: list[dict] = []


@router.post("", response_model=SmartChatResponse)
async def smart_chat(req: SmartChatRequest):
    """Chat with automatic tool use — LLM decides when to call tools."""
    result = await service.chat(
        message=req.message,
        conversation_id=req.conversation_id,
        enabled_tools=req.enabled_tools,
    )
    return result


@router.post("/stream")
async def smart_chat_stream(req: SmartChatRequest):
    """Streaming smart chat with tool use."""
    return StreamingResponse(
        service.chat_stream(
            message=req.message,
            conversation_id=req.conversation_id,
            enabled_tools=req.enabled_tools,
        ),
        media_type="text/event-stream",
    )
