from fastapi import APIRouter
from pydantic import BaseModel

from app.services.multi_agent_service import MultiAgentService

router = APIRouter()
service = MultiAgentService()


class AgentCreate(BaseModel):
    id: str
    name: str
    name_en: str = ""
    role: str
    system_prompt: str
    tools: list[str] = []
    domain: str = "COMMON"
    icon: str = "🤖"


class AgentUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None
    domain: str | None = None
    icon: str | None = None


class AskRequest(BaseModel):
    question: str
    agent_ids: list[str] | None = None  # None = auto-select


# ── Agent CRUD ────────────────────────────────

@router.get("/agents")
async def list_agents():
    """List all registered agents."""
    return service.list_agents()


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = service.get_agent(agent_id)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(404, "Agent not found")
    return agent


@router.post("/agents")
async def create_agent(req: AgentCreate):
    """Create a new agent."""
    return service.create_agent(req.model_dump())


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, req: AgentUpdate):
    """Update an existing agent."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    return service.update_agent(agent_id, updates)


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent."""
    service.delete_agent(agent_id)
    return {"status": "deleted", "agent_id": agent_id}


# ── Orchestration ─────────────────────────────

@router.post("/ask")
async def ask(req: AskRequest):
    """Execute multi-agent orchestration for a business question."""
    return await service.orchestrate(
        question=req.question,
        agent_ids=req.agent_ids,
    )
