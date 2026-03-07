import re
from loguru import logger

from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_TEXT2SQL


class Text2SqlService:
    def __init__(self):
        # In-memory schema store (swap for DB in production)
        self._schemas: dict[str, dict] = {}

    async def generate(
        self,
        question: str,
        schema_id: str | None = None,
    ) -> dict:
        """Generate SQL from natural language question."""
        # Build schema context
        schema_context = ""
        if schema_id and schema_id in self._schemas:
            schema = self._schemas[schema_id]
            schema_context = self._format_schema(schema)
        elif self._schemas:
            # Use first available schema if none specified
            first_key = next(iter(self._schemas))
            schema_context = self._format_schema(self._schemas[first_key])

        messages = [
            {"role": "system", "content": SYSTEM_TEXT2SQL},
            {"role": "user", "content": f"Schema:\n{schema_context}\n\nQuestion: {question}"},
        ]

        response = chat_completion(messages=messages, temperature=0.1)
        content = response.choices[0].message.content

        # Parse SQL and explanation from response
        sql, explanation = self._parse_response(content)

        # Safety check: only SELECT allowed
        if not self._is_safe_sql(sql):
            return {
                "sql": "",
                "explanation": "ERROR: Only SELECT queries are allowed. The generated query was blocked.",
            }

        logger.info(f"Text2SQL: {question[:50]}... -> {sql[:50]}...")
        return {"sql": sql, "explanation": explanation}

    async def execute(self, sql: str) -> dict:
        """Execute a confirmed SQL query. SELECT only."""
        if not self._is_safe_sql(sql):
            return {"error": "Only SELECT queries are allowed", "rows": []}

        # TODO: Connect to actual database (Oracle/PostgreSQL)
        logger.info(f"Executing SQL: {sql[:100]}...")
        return {
            "status": "not_implemented",
            "message": "Database connection not configured yet. Set DB_* in .env.",
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
        # Try to extract SQL from markdown code block
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
