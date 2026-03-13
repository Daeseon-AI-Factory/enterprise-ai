"""Agent router — autonomous AI agent that uses multiple tools."""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.agent_service import AgentService

router = APIRouter()
service = AgentService()


class AgentRequest(BaseModel):
    task: str
    tools: list[str] | None = None  # None = use all tools
    max_iterations: int = 10


class AgentStepResponse(BaseModel):
    step_number: int
    thought: str
    action: str
    action_input: str
    observation: str
    is_final: bool
    final_answer: str


class AgentResponse(BaseModel):
    task: str
    answer: str
    steps: list[AgentStepResponse]
    total_iterations: int
    status: str


@router.post("/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest):
    """Run an autonomous agent to complete a task."""
    result = await service.run(
        task=req.task,
        tools=req.tools,
        max_iterations=req.max_iterations,
    )
    return AgentResponse(
        task=result.task,
        answer=result.answer,
        steps=[
            AgentStepResponse(
                step_number=s.step_number,
                thought=s.thought,
                action=s.action,
                action_input=s.action_input,
                observation=s.observation,
                is_final=s.is_final,
                final_answer=s.final_answer,
            )
            for s in result.steps
        ],
        total_iterations=result.total_iterations,
        status=result.status,
    )


@router.post("/stream")
async def stream_agent(req: AgentRequest):
    """Run agent with SSE streaming of each step."""

    async def event_generator():
        async for step in service.run_stream(
            task=req.task,
            tools=req.tools,
            max_iterations=req.max_iterations,
        ):
            data = json.dumps({
                "step_number": step.step_number,
                "thought": step.thought,
                "action": step.action,
                "action_input": step.action_input,
                "observation": step.observation[:1000] if step.observation else "",
                "is_final": step.is_final,
                "final_answer": step.final_answer,
            }, ensure_ascii=False)
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/tools")
async def list_tools():
    """List all tools available to the agent."""
    return service.list_tools()
