from fastapi import APIRouter
from pydantic import BaseModel

from app.services.build_service import BuildService

router = APIRouter()
service = BuildService()


class BuildRequest(BaseModel):
    project_path: str
    command: str = "npm run build"
    name: str = ""


class DeployRequest(BaseModel):
    project_path: str
    command: str
    name: str = ""


@router.post("/run")
async def run_build(req: BuildRequest):
    """Run a build command and return the result."""
    return await service.run_build(
        project_path=req.project_path,
        build_command=req.command,
        name=req.name,
    )


@router.post("/deploy")
async def run_deploy(req: DeployRequest):
    """Run a deploy command and return the result."""
    return await service.run_deploy(
        project_path=req.project_path,
        deploy_command=req.command,
        name=req.name,
    )


@router.get("/history")
async def build_history(limit: int = 20):
    """List recent build/deploy history."""
    return await service.list_history(limit=limit)


@router.get("/history/{build_id}")
async def build_detail(build_id: str):
    """Get full build detail including logs."""
    result = await service.get_build_detail(build_id)
    if result is None:
        return {"error": "Build not found"}
    return result
