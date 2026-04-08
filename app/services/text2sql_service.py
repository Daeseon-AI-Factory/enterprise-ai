import json
import re
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_TEXT2SQL

SCHEMA_FILE = Path("./data/schemas.json")


def _build_db_url(
    db_type: str | None = None,
    host: str | None = None,
    port: int | None = None,
    name: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> str | None:
    from urllib.parse import quote_plus

    t = db_type or settings.DB_TYPE
    h = host or settings.DB_HOST
    p = port or settings.DB_PORT
    n = name or settings.DB_NAME
    u = quote_plus(user or settings.DB_USER or "")
    pw = quote_plus(password or settings.DB_PASSWORD or "")

    if not u:
        return None
    if t == "oracle":
        return f"oracle+oracledb://{u}:{pw}@{h}:{p}/?service_name={n}"
    elif t == "postgresql":
        return f"postgresql://{u}:{pw}@{h}:{p}/{n}"
    elif t == "mysql":
        return f"mysql+pymysql://{u}:{pw}@{h}:{p}/{n}"
    elif t == "sqlite":
        return f"sqlite:///{n}"
    return None


class Text2SqlService:
    def __init__(self):
        self._schemas: dict[str, dict] = self._load_schemas()
        self._engine = None
        db_url = _build_db_url()
        if db_url:
            try:
                self._engine = create_engine(db_url, pool_pre_ping=True)
                logger.info(f"DB engine created: {settings.DB_TYPE}@{settings.DB_HOST}")
            except Exception as e:
                logger.warning(f"Failed to create DB engine: {e}")

    # ── Schema persistence ───────────────────────────────

    def _load_schemas(self) -> dict:
        SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
        if SCHEMA_FILE.exists():
            try:
                return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_schemas(self) -> None:
        try:
            SCHEMA_FILE.write_text(
                json.dumps(self._schemas, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save schemas: {e}")

    # ── DB Connection test ───────────────────────────────

    async def test_connection(
        self,
        db_type: str, host: str, port: int, name: str, user: str, password: str
    ) -> dict:
        url = _build_db_url(db_type, host, port, name, user, password)
        logger.info(f"Testing connection: {db_type}@{host}:{port}/{name} user={user}")
        if not url:
            return {"ok": False, "error": "Invalid connection parameters"}
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL" if db_type == "oracle" else "SELECT 1"))
            logger.info("DB connection test: OK")
            return {"ok": True}
        except Exception as e:
            error_msg = str(e).split("\n")[0]
            logger.error(f"DB connection failed: {error_msg}")
            return {"ok": False, "error": error_msg}

    # ── Schema auto-discovery ────────────────────────────

    async def discover_schema(
        self,
        schema_id: str,
        db_type: str | None = None,
        host: str | None = None,
        port: int | None = None,
        name: str | None = None,
        user: str | None = None,
        password: str | None = None,
        owner: str | None = None,   # Oracle schema owner (e.g. "MES_USER")
    ) -> dict:
        """Auto-discover tables/columns from real DB and register as schema."""
        url = _build_db_url(db_type, host, port, name, user, password)
        if not url:
            return {"error": "DB not configured"}

        try:
            engine = create_engine(url, pool_pre_ping=True)
            inspector = inspect(engine)

            t = db_type or settings.DB_TYPE
            if t == "oracle":
                table_names = inspector.get_table_names(schema=owner)
            else:
                table_names = inspector.get_table_names()

            tables = []
            for table_name in table_names[:100]:  # cap at 100 tables
                try:
                    cols = inspector.get_columns(table_name, schema=owner)
                    tables.append({
                        "name": f"{owner}.{table_name}" if owner else table_name,
                        "columns": [
                            {"name": c["name"], "type": str(c["type"])}
                            for c in cols
                        ],
                    })
                except Exception:
                    continue

            await self.register_schema(
                schema_id=schema_id,
                tables=tables,
                description=f"Auto-discovered from {t}@{host or settings.DB_HOST}/{name or settings.DB_NAME}",
            )
            logger.info(f"Schema discovered: {schema_id} → {len(tables)} tables")
            return {"schema_id": schema_id, "tables": len(tables), "status": "discovered"}

        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            return {"error": str(e).split("\n")[0]}

    # ── Generate SQL ─────────────────────────────────────

    async def generate(self, question: str, schema_id: str | None = None) -> dict:
        import time
        t0 = time.time()
        # 항상 파일에서 최신 스키마 로드 (다른 인스턴스가 저장했을 수 있음)
        self._schemas = self._load_schemas()
        schema_context = ""
        used_schema = None
        if schema_id and schema_id in self._schemas:
            schema_context = self._format_schema(self._schemas[schema_id])
            used_schema = schema_id
        elif self._schemas:
            first_key = next(iter(self._schemas))
            schema_context = self._format_schema(self._schemas[first_key])
            used_schema = first_key

        logger.info(f"[SQL] 질문: '{question[:80]}' (스키마: {used_schema})")

        messages = [
            {"role": "system", "content": SYSTEM_TEXT2SQL},
            {"role": "user", "content": f"Schema:\n{schema_context}\n\nQuestion: {question}"},
        ]

        try:
            t1 = time.time()
            response = chat_completion(messages=messages, temperature=0.1)
            content = response.choices[0].message.content or ""
            logger.info(f"[SQL] LLM 응답: {time.time()-t1:.1f}초")
        except Exception as e:
            logger.error(f"[SQL] LLM 호출 실패: {e}")
            return {"sql": "", "explanation": f"LLM 호출 실패: {e}"}

        sql, explanation = self._parse_response(content)

        if not self._is_safe_sql(sql):
            logger.warning(f"[SQL] 안전하지 않은 SQL 차단: {sql[:80]}")
            return {"sql": "", "explanation": "ERROR: Only SELECT queries are allowed."}

        logger.info(f"[SQL] 생성 완료: {sql[:100]} ({time.time()-t0:.1f}초)")
        return {"sql": sql, "explanation": explanation}

    # ── Execute SQL ──────────────────────────────────────

    async def execute(self, sql: str, connection: dict | None = None) -> dict:
        import time
        t0 = time.time()
        logger.info(f"[SQL] 실행 요청: {sql[:100]}")

        if not self._is_safe_sql(sql):
            logger.warning(f"[SQL] 차단됨: SELECT가 아닌 쿼리")
            return {"error": "Only SELECT queries are allowed", "rows": [], "columns": []}

        engine = self._engine
        if connection:
            conn_info = f"{connection.get('db_type')}@{connection.get('host')}:{connection.get('port')}"
            logger.info(f"[SQL] 외부 DB 연결: {conn_info}")
            url = _build_db_url(**connection)
            if url:
                try:
                    engine = create_engine(url, pool_pre_ping=True)
                except Exception as e:
                    logger.error(f"[SQL] DB 연결 실패: {e}")
                    return {"error": str(e), "rows": [], "columns": []}

        result = self._run_query(engine, sql)
        row_count = result.get("row_count", len(result.get("rows", [])))
        logger.info(f"[SQL] 실행 완료: {row_count}행 반환 ({time.time()-t0:.1f}초)")
        return result

    def _run_query(self, engine, sql: str) -> dict:
        if engine is None:
            return {
                "error": "DB not configured. Set DB_TYPE, DB_HOST, DB_USER, DB_PASSWORD in .env",
                "rows": [], "columns": [],
            }
        # Oracle은 세미콜론을 허용하지 않음
        sql = sql.rstrip().rstrip(";")
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                logger.info(f"Query: {len(rows)} rows, {len(columns)} cols")
                return {"sql": sql, "columns": columns, "rows": rows, "row_count": len(rows)}
        except SQLAlchemyError as e:
            error_msg = str(e).split("\n")[0]
            logger.error(f"SQL error: {error_msg}")
            return {"error": error_msg, "sql": sql, "rows": [], "columns": []}

    # ── Schema management ────────────────────────────────

    async def register_schema(self, schema_id: str, tables: list[dict], description: str = "") -> dict:
        self._schemas[schema_id] = {
            "schema_id": schema_id, "tables": tables, "description": description,
        }
        self._save_schemas()
        logger.info(f"Registered schema: {schema_id} ({len(tables)} tables)")
        return {"status": "registered", "schema_id": schema_id}

    async def delete_schema(self, schema_id: str) -> dict:
        if schema_id in self._schemas:
            del self._schemas[schema_id]
            self._save_schemas()
        return {"status": "deleted", "schema_id": schema_id}

    async def list_schemas(self) -> list[dict]:
        return [
            {"schema_id": k, "tables": len(v["tables"]), "description": v["description"]}
            for k, v in self._schemas.items()
        ]

    async def get_schema(self, schema_id: str) -> dict | None:
        return self._schemas.get(schema_id)

    # ── Helpers ──────────────────────────────────────────

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
        """Validate SQL safety using AST parsing, not regex.

        Why AST over regex: regex-based checks are trivially bypassed with
        comments (-- \\nDELETE), whitespace, or CTEs. sqlparse tokenizes
        the SQL into an AST and identifies the actual statement type,
        regardless of formatting tricks.

        Only SELECT and WITH (CTE followed by SELECT) are allowed.
        """
        if not sql or not sql.strip():
            return False

        import sqlparse

        # Parse all statements (handles "SELECT 1; DROP TABLE x" injection)
        statements = sqlparse.parse(sql)
        if not statements:
            return False

        # Reject multi-statement SQL — only one statement allowed
        # (filters out "SELECT 1; DROP TABLE users" attacks)
        real_statements = [s for s in statements if s.get_type() is not None]
        if len(real_statements) > 1:
            logger.warning(f"[SQL] Multi-statement SQL blocked: {len(real_statements)} statements")
            return False

        for stmt in statements:
            stmt_type = stmt.get_type()
            # Allow SELECT and UNKNOWN (WITH/CTE parses as UNKNOWN in sqlparse)
            if stmt_type == "SELECT":
                continue
            if stmt_type == "UNKNOWN":
                # WITH (CTE) + SELECT is valid — verify no DML keywords in tokens
                flat = sql.strip().upper()
                # Strip comments to prevent hiding DML inside them
                stripped = sqlparse.format(sql, strip_comments=True).strip().upper()
                for dangerous in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
                                  "CREATE", "TRUNCATE", "EXEC", "MERGE", "GRANT", "REVOKE"]:
                    if dangerous in stripped.split():
                        logger.warning(f"[SQL] Dangerous keyword '{dangerous}' in statement")
                        return False
                continue
            # Any other statement type (DML, DDL) → block
            logger.warning(f"[SQL] Blocked statement type: {stmt_type}")
            return False

        return True
