from fastapi import APIRouter
from pydantic import BaseModel

from app.services.text2sql_service import Text2SqlService

router = APIRouter()
service = Text2SqlService()


class SqlGenerateRequest(BaseModel):
    question: str
    schema_id: str | None = None


class SqlGenerateResponse(BaseModel):
    sql: str
    explanation: str


class SqlExecuteRequest(BaseModel):
    sql: str
    confirmed: bool = False


class SchemaRegisterRequest(BaseModel):
    schema_id: str
    tables: list[dict]  # [{name, columns: [{name, type, description}]}]
    description: str = ""


@router.post("/generate", response_model=SqlGenerateResponse)
async def generate_sql(req: SqlGenerateRequest):
    """Convert natural language to SQL query."""
    result = await service.generate(
        question=req.question,
        schema_id=req.schema_id,
    )
    return result


@router.post("/execute")
async def execute_sql(req: SqlExecuteRequest):
    """Execute a generated SQL query (SELECT only, requires confirmation)."""
    if not req.confirmed:
        return {"error": "SQL execution requires user confirmation", "confirmed": False}
    result = await service.execute(sql=req.sql)
    return result


@router.post("/schema")
async def register_schema(req: SchemaRegisterRequest):
    """Register a database schema for Text-to-SQL."""
    result = await service.register_schema(
        schema_id=req.schema_id,
        tables=req.tables,
        description=req.description,
    )
    return result


@router.get("/schemas")
async def list_schemas():
    """List registered database schemas."""
    return await service.list_schemas()
