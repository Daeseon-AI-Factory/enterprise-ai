"""Scheduler router — manage recurring background tasks."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.scheduler_service import SchedulerService

router = APIRouter()
service = SchedulerService()


class CreateScheduleRequest(BaseModel):
    name: str
    handler_name: str
    interval_minutes: int  # Run every N minutes
    kwargs: dict | None = None
    enabled: bool = True


@router.post("/create")
async def create_schedule(req: CreateScheduleRequest):
    """Create a recurring scheduled task."""
    return await service.add_schedule(
        name=req.name,
        handler_name=req.handler_name,
        interval_minutes=req.interval_minutes,
        kwargs=req.kwargs,
        enabled=req.enabled,
    )


@router.delete("/{name}")
async def remove_schedule(name: str):
    """Remove a scheduled task."""
    removed = await service.remove_schedule(name)
    return {"status": "removed" if removed else "not_found", "name": name}


@router.get("/list")
async def list_schedules():
    """List all scheduled tasks."""
    return {
        "schedules": service.list_schedules(),
        "handlers": service.list_handlers(),
    }


@router.post("/{name}/run-now")
async def run_now(name: str):
    """Manually trigger a scheduled task."""
    return await service.run_now(name)


@router.get("/{name}/history")
async def get_history(name: str, limit: int = 20):
    """Get execution history for a scheduled task."""
    return service.get_history(name, limit)
