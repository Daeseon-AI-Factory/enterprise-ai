from fastapi import APIRouter
from pydantic import BaseModel

from app.services.text2sql_service import Text2SqlService

router = APIRouter()
service = Text2SqlService()


class SqlGenerateRequest(BaseModel):
    question: str
    schema_id: str | None = None


class SqlExecuteRequest(BaseModel):
    sql: str
    confirmed: bool = False
    connection: dict | None = None


class SchemaRegisterRequest(BaseModel):
    schema_id: str
    tables: list[dict]
    description: str = ""


class DbConnectionRequest(BaseModel):
    db_type: str = "oracle"
    host: str
    port: int = 1521
    name: str       # SID or database name
    user: str
    password: str


class DiscoverSchemaRequest(DbConnectionRequest):
    schema_id: str
    owner: str | None = None  # Oracle schema owner (e.g. "MES_USER")


@router.post("/generate")
async def generate_sql(req: SqlGenerateRequest):
    """Convert natural language to SQL."""
    return await service.generate(question=req.question, schema_id=req.schema_id)


@router.post("/execute")
async def execute_sql(req: SqlExecuteRequest):
    """Execute SELECT SQL (requires confirmed=true)."""
    if not req.confirmed:
        return {"error": "SQL execution requires user confirmation", "confirmed": False}
    return await service.execute(sql=req.sql, connection=req.connection)


@router.post("/connection/test")
async def test_connection(req: DbConnectionRequest):
    """Test DB connection."""
    return await service.test_connection(
        db_type=req.db_type, host=req.host, port=req.port,
        name=req.name, user=req.user, password=req.password,
    )


@router.post("/schema/discover")
async def discover_schema(req: DiscoverSchemaRequest):
    """Auto-discover schema from real DB (reads ALL_TABLES/ALL_COLUMNS)."""
    return await service.discover_schema(
        schema_id=req.schema_id,
        db_type=req.db_type, host=req.host, port=req.port,
        name=req.name, user=req.user, password=req.password,
        owner=req.owner,
    )


@router.post("/schema")
async def register_schema(req: SchemaRegisterRequest):
    """Manually register a schema."""
    return await service.register_schema(
        schema_id=req.schema_id, tables=req.tables, description=req.description,
    )


@router.get("/schemas")
async def list_schemas():
    return await service.list_schemas()


@router.get("/schemas/{schema_id}")
async def get_schema(schema_id: str):
    schema = await service.get_schema(schema_id)
    if not schema:
        from fastapi import HTTPException
        raise HTTPException(404, "Schema not found")
    return schema


@router.delete("/schemas/{schema_id}")
async def delete_schema(schema_id: str):
    return await service.delete_schema(schema_id)
