from fastapi import APIRouter
from pydantic import BaseModel

from app.services.codegen_service import CodegenService

router = APIRouter()
service = CodegenService()


class CodegenRequest(BaseModel):
    prompt: str
    project_id: str | None = None
    language: str = "python"  # python, java, javascript, sql
    framework: str | None = None  # fastapi, spring, vue


class CodegenResponse(BaseModel):
    code: str
    language: str
    explanation: str


class ProjectTemplateRequest(BaseModel):
    project_id: str
    tech_stack: str  # e.g. "FastAPI + SQLAlchemy + Oracle"
    conventions: str = ""  # coding conventions
    sample_code: str = ""  # existing code patterns


@router.post("/generate", response_model=CodegenResponse)
async def generate_code(req: CodegenRequest):
    """Generate code based on prompt and project context."""
    result = await service.generate(
        prompt=req.prompt,
        project_id=req.project_id,
        language=req.language,
        framework=req.framework,
    )
    return result


@router.post("/templates")
async def register_template(req: ProjectTemplateRequest):
    """Register a project template for context-aware code generation."""
    result = await service.register_template(
        project_id=req.project_id,
        tech_stack=req.tech_stack,
        conventions=req.conventions,
        sample_code=req.sample_code,
    )
    return result


@router.get("/templates")
async def list_templates():
    """List registered project templates."""
    return await service.list_templates()
