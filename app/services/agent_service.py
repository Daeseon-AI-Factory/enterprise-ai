"""Agent Service — wires existing services as tools for the AI Agent."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from loguru import logger

from app.core.tool_registry import Tool, ToolRegistry
from app.core.agent_executor import AgentExecutor, AgentStep, AgentResult
from app.services.rag_service import RagService
from app.services.text2sql_service import Text2SqlService
from app.services.codegen_service import CodegenService
from app.services.review_service import ReviewService
from app.core.vector_store import VectorStore


class AgentService:
    def __init__(self):
        self._registry = ToolRegistry()
        self._rag = RagService()
        self._text2sql = Text2SqlService()
        self._codegen = CodegenService()
        self._review = ReviewService()
        self._vector_store = VectorStore()
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all available tools from existing services."""

        # 1. Document Search (RAG)
        self._registry.register(Tool(
            name="search_docs",
            description="Search through uploaded documents using semantic similarity. Returns relevant document chunks with source info.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in natural language"},
                    "collection": {"type": "string", "description": "Document collection to search (default: 'default')"},
                    "top_k": {"type": "integer", "description": "Number of results to return (default: 5)"},
                },
                "required": ["query"],
            },
            handler=self._tool_search_docs,
        ))

        # 2. Database Query (Text2SQL)
        self._registry.register(Tool(
            name="query_database",
            description="Generate and optionally execute SQL from a natural language question. Only SELECT queries are allowed.",
            parameters={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Natural language question about the database"},
                    "execute": {"type": "boolean", "description": "Whether to execute the generated SQL (default: false)"},
                    "schema_id": {"type": "string", "description": "Database schema ID to use"},
                },
                "required": ["question"],
            },
            handler=self._tool_query_database,
        ))

        # 3. Generate Code
        self._registry.register(Tool(
            name="generate_code",
            description="Generate code in a specified programming language based on a prompt.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the code to generate"},
                    "language": {"type": "string", "description": "Programming language (python, java, javascript, sql, etc.)"},
                    "framework": {"type": "string", "description": "Framework to use (fastapi, spring, vue, etc.)"},
                },
                "required": ["prompt"],
            },
            handler=self._tool_generate_code,
        ))

        # 4. Code Review
        self._registry.register(Tool(
            name="review_code",
            description="Review code for bugs, security issues, performance problems, and best practices.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "language": {"type": "string", "description": "Programming language"},
                    "context": {"type": "string", "description": "Context about what the code does"},
                },
                "required": ["code"],
            },
            handler=self._tool_review_code,
        ))

        # 5. List Collections
        self._registry.register(Tool(
            name="list_collections",
            description="List all available document collections in the vector database.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self._tool_list_collections,
        ))

        # 6. List DB Schemas
        self._registry.register(Tool(
            name="list_schemas",
            description="List all registered database schemas available for Text-to-SQL.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self._tool_list_schemas,
        ))

        logger.info(f"Agent initialized with {len(self._registry.list_names())} tools: {self._registry.list_names()}")

    # --- Tool Handlers ---

    async def _tool_search_docs(self, query: str, collection: str = "default", top_k: int = 5) -> str:
        result = await self._rag.query(query=query, collection=collection, top_k=int(top_k))
        if not result["sources"]:
            return f"No documents found for query: '{query}' in collection '{collection}'"
        parts = [f"Answer: {result['answer']}\n\nSources:"]
        for src in result["sources"]:
            parts.append(f"- {src['filename']} (score: {src.get('score', 'N/A')})")
        return "\n".join(parts)

    async def _tool_query_database(self, question: str, execute: bool = False, schema_id: str | None = None) -> str:
        result = await self._text2sql.generate(question=question, schema_id=schema_id)
        output = f"Generated SQL:\n```sql\n{result['sql']}\n```\n\nExplanation: {result['explanation']}"

        if execute and result["sql"]:
            exec_result = await self._text2sql.execute(result["sql"])
            if exec_result.get("error"):
                output += f"\n\nExecution Error: {exec_result['error']}"
            else:
                rows = exec_result.get("rows", [])
                output += f"\n\nResults ({len(rows)} rows):\n"
                if rows:
                    output += json.dumps(rows[:20], ensure_ascii=False, indent=2)
                    if len(rows) > 20:
                        output += f"\n... and {len(rows) - 20} more rows"
        return output

    async def _tool_generate_code(self, prompt: str, language: str = "python", framework: str | None = None) -> str:
        result = await self._codegen.generate(
            prompt=prompt,
            language=language,
            framework=framework,
        )
        return f"```{language}\n{result['code']}\n```"

    async def _tool_review_code(self, code: str, language: str = "", context: str = "") -> str:
        result = await self._review.code_review(code=code, language=language, context=context)
        return result["review"]

    async def _tool_list_collections(self) -> str:
        collections = await self._rag.list_collections()
        if not collections:
            return "No document collections found."
        lines = ["Document Collections:"]
        for col in collections:
            lines.append(f"- {col['name']}: {col['count']} documents")
        return "\n".join(lines)

    async def _tool_list_schemas(self) -> str:
        schemas = await self._text2sql.list_schemas()
        if not schemas:
            return "No database schemas registered."
        lines = ["Registered Schemas:"]
        for s in schemas:
            lines.append(f"- {s['schema_id']}: {s['tables']} tables ({s.get('description', '')})")
        return "\n".join(lines)

    # --- Public API ---

    async def run(
        self,
        task: str,
        tools: list[str] | None = None,
        max_iterations: int = 10,
    ) -> AgentResult:
        """Run agent to completion."""
        executor = AgentExecutor(
            registry=self._registry,
            max_iterations=max_iterations,
        )
        return await executor.run(task, tools)

    async def run_stream(
        self,
        task: str,
        tools: list[str] | None = None,
        max_iterations: int = 10,
    ) -> AsyncGenerator[AgentStep, None]:
        """Run agent with step-by-step streaming."""
        executor = AgentExecutor(
            registry=self._registry,
            max_iterations=max_iterations,
        )
        async for step in executor.run_stream(task, tools):
            yield step

    def list_tools(self) -> list[dict]:
        """List all available tools."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._registry.list_tools()
        ]

    @property
    def registry(self) -> ToolRegistry:
        return self._registry
