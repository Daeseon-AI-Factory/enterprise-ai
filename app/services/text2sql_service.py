import re

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_TEXT2SQL


def _build_db_url() -> str | None:
    """Build SQLAlchemy connection URL from settings."""
    if not settings.DB_USER:
        return None

    if settings.DB_TYPE == "oracle":
        return (
            f"oracle+oracledb://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
    elif settings.DB_TYPE == "postgresql":
        return (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
    elif settings.DB_TYPE == "sqlite":
        return f"sqlite:///{settings.DB_NAME}"
    return None


class Text2SqlService:
    def __init__(self):
        self._schemas: dict[str, dict] = {}
        self._engine = None
        db_url = _build_db_url()
        if db_url:
            try:
                self._engine = create_engine(db_url, pool_pre_ping=True)
                logger.info(f"DB engine created: {settings.DB_TYPE}@{settings.DB_HOST}")
            except Exception as e:
                logger.warning(f"Failed to create DB engine: {e}")

    async def generate(
        self,
        question: str,
        schema_id: str | None = None,
    ) -> dict:
        """Generate SQL from natural language question."""
        schema_context = ""
        if schema_id and schema_id in self._schemas:
            schema = self._schemas[schema_id]
            schema_context = self._format_schema(schema)
        elif self._schemas:
            first_key = next(iter(self._schemas))
            schema_context = self._format_schema(self._schemas[first_key])

        messages = [
            {"role": "system", "content": SYSTEM_TEXT2SQL},
            {"role": "user", "content": f"Schema:\n{schema_context}\n\nQuestion: {question}"},
        ]

        try:
            response = chat_completion(messages=messages, temperature=0.1)
            content = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Text2SQL LLM call failed: {e}")
            return {"sql": "", "explanation": f"LLM 호출 실패: {e}"}

        sql, explanation = self._parse_response(content)

        if not self._is_safe_sql(sql):
            return {
                "sql": "",
                "explanation": "ERROR: Only SELECT queries are allowed.",
            }

        logger.info(f"Text2SQL: {question[:50]}... -> {sql[:50]}...")
        return {"sql": sql, "explanation": explanation}

    async def execute(self, sql: str) -> dict:
        """Execute a confirmed SQL query. SELECT only."""
        if not self._is_safe_sql(sql):
            return {"error": "Only SELECT queries are allowed", "rows": [], "columns": []}

        logger.info(f"Executing SQL: {sql[:100]}...")
        return self._execute_query(sql)

    def _execute_query(self, sql: str) -> dict:
        """Execute SQL against the configured database."""
        if self._engine is None:
            return {
                "error": "Database not configured. Set DB_TYPE, DB_HOST, DB_USER, DB_PASSWORD in .env",
                "sql": sql,
                "rows": [],
                "columns": [],
            }

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

                logger.info(f"Query returned {len(rows)} rows, {len(columns)} columns")
                return {
                    "sql": sql,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                }
        except SQLAlchemyError as e:
            error_msg = str(e).split("\n")[0]  # First line only
            logger.error(f"SQL execution error: {error_msg}")
            return {
                "error": f"SQL execution error: {error_msg}",
                "sql": sql,
                "rows": [],
                "columns": [],
            }

    async def register_schema(
        self,
        schema_id: str,
        tables: list[dict],
        description: str = "",
    ) -> dict:
        self._schemas[schema_id] = {
            "schema_id": schema_id,
            "tables": tables,
            "description": description,
        }
        logger.info(f"Registered schema: {schema_id} with {len(tables)} tables")
        return {"status": "registered", "schema_id": schema_id}

    async def list_schemas(self) -> list[dict]:
        return [
            {"schema_id": k, "tables": len(v["tables"]), "description": v["description"]}
            for k, v in self._schemas.items()
        ]

    def _format_schema(self, schema: dict) -> str:
        lines = [f"-- Schema: {schema['schema_id']}"]
        if schema.get("description"):
            lines.append(f"-- {schema['description']}")
        for table in schema["tables"]:
            cols = ", ".join(
                f"{c['name']} {c.get('type', 'VARCHAR2')}" for c in table.get("columns", [])
            )
            lines.append(f"CREATE TABLE {table['name']} ({cols});")
        return "\n".join(lines)

    def _parse_response(self, content: str) -> tuple[str, str]:
        sql_match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
            explanation = content.replace(sql_match.group(0), "").strip()
        else:
            sql = content.strip()
            explanation = ""
        return sql, explanation

    def _is_safe_sql(self, sql: str) -> bool:
        if not sql:
            return False
        normalized = sql.strip().upper()
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC"]
        for keyword in dangerous:
            if normalized.startswith(keyword):
                return False
        return True
