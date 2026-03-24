"""
Multi-Agent Orchestration Service

Manages agent definitions and orchestrates collaboration between
domain-specific agents (e.g., quality analyst, document searcher, inventory manager).

Each agent has:
  - name, role, system_prompt
  - tools: which capabilities it can use (rag, sql, confluence)
  - domain: tag for grouping (e.g., "MES", "WMS", "QC")

The orchestrator:
  1. Analyzes the user's question
  2. Selects relevant agents
  3. Executes them in sequence, passing context
  4. Synthesizes final answer
"""

import json
import time
from pathlib import Path

from loguru import logger

from app.llm_client import chat_completion
from app.core.vector_store import get_vector_store
from app.services.text2sql_service import Text2SqlService

AGENTS_FILE = Path("./data/agents.json")

# Default agents for manufacturing domain
DEFAULT_AGENTS = [
    {
        "id": "quality_analyst",
        "name": "품질 분석관",
        "name_en": "Quality Analyst",
        "role": "Analyzes defect data from Oracle DB, identifies patterns and root causes",
        "system_prompt": (
            "You are a Quality Analyst agent for a manufacturing execution system.\n"
            "Your job is to query the production database for defect/quality data and analyze patterns.\n"
            "Always provide specific numbers and percentages.\n"
            "Use the SQL tool to query the database. Write Oracle-compatible SQL.\n"
            "Respond in the same language as the user."
        ),
        "tools": ["sql"],
        "domain": "MES",
        "icon": "🔍",
    },
    {
        "id": "doc_searcher",
        "name": "문서 검색관",
        "name_en": "Document Searcher",
        "role": "Searches SOPs, manuals, and Confluence pages using RAG",
        "system_prompt": (
            "You are a Document Searcher agent.\n"
            "Your job is to find relevant documents, SOPs, manuals, and knowledge base articles.\n"
            "Use the RAG tool to search across all document collections.\n"
            "Always cite the source document filename.\n"
            "Respond in the same language as the user."
        ),
        "tools": ["rag"],
        "domain": "COMMON",
        "icon": "📄",
    },
    {
        "id": "inventory_manager",
        "name": "재고 관리자",
        "name_en": "Inventory Manager",
        "role": "Queries warehouse/inventory data and provides stock status",
        "system_prompt": (
            "You are an Inventory Manager agent for a warehouse management system.\n"
            "Your job is to query inventory, inbound, and outbound data.\n"
            "Provide current stock levels, movement trends, and alerts for low stock.\n"
            "Use the SQL tool to query the database. Write Oracle-compatible SQL.\n"
            "Respond in the same language as the user."
        ),
        "tools": ["sql"],
        "domain": "WMS",
        "icon": "📦",
    },
    {
        "id": "report_writer",
        "name": "보고서 작성자",
        "name_en": "Report Writer",
        "role": "Synthesizes results from other agents into a structured report",
        "system_prompt": (
            "You are a Report Writer agent.\n"
            "You receive analysis results from other agents and synthesize them into a clear, structured report.\n"
            "Include: Executive Summary, Key Findings, Data Evidence, Recommendations.\n"
            "Use markdown formatting. Include tables where appropriate.\n"
            "Respond in the same language as the user."
        ),
        "tools": [],
        "domain": "COMMON",
        "icon": "📝",
    },
]

ORCHESTRATOR_PROMPT = """You are an orchestration agent that decides which specialist agents to involve for a given question.

Available agents:
{agent_list}

Given the user's question, respond with a JSON array of agent IDs to involve, in execution order.
Only select agents that are actually needed. The last agent should be "report_writer" if multiple agents are involved.

Examples:
- "A라인 불량률 알려줘" → ["quality_analyst"]
- "납땜 불량 원인 분석하고 관련 SOP 찾아줘" → ["quality_analyst", "doc_searcher", "report_writer"]
- "현재 재고 현황이랑 입출고 추이 보여줘" → ["inventory_manager"]
- "A라인 불량 급증 원인 분석해서 보고서 써줘" → ["quality_analyst", "doc_searcher", "report_writer"]

Respond ONLY with the JSON array, nothing else."""


class MultiAgentService:
    def __init__(self):
        self._agents: list[dict] = self._load_agents()
        self._sql_service = Text2SqlService()
        self._vector_store = get_vector_store()

    def _load_agents(self) -> list[dict]:
        if AGENTS_FILE.exists():
            try:
                return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        # Initialize with defaults
        self._save_agents(DEFAULT_AGENTS)
        return DEFAULT_AGENTS

    def _save_agents(self, agents: list[dict]) -> None:
        AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        AGENTS_FILE.write_text(json.dumps(agents, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Agent CRUD ────────────────────────────────────

    def list_agents(self) -> list[dict]:
        return self._agents

    def get_agent(self, agent_id: str) -> dict | None:
        return next((a for a in self._agents if a["id"] == agent_id), None)

    def create_agent(self, agent: dict) -> dict:
        if any(a["id"] == agent["id"] for a in self._agents):
            raise ValueError(f"Agent '{agent['id']}' already exists")
        self._agents.append(agent)
        self._save_agents(self._agents)
        logger.info(f"[AGENT] 생성: {agent['id']} ({agent.get('name', '')})")
        return agent

    def update_agent(self, agent_id: str, updates: dict) -> dict:
        for i, a in enumerate(self._agents):
            if a["id"] == agent_id:
                self._agents[i] = {**a, **updates, "id": agent_id}
                self._save_agents(self._agents)
                logger.info(f"[AGENT] 수정: {agent_id}")
                return self._agents[i]
        raise ValueError(f"Agent '{agent_id}' not found")

    def delete_agent(self, agent_id: str) -> None:
        self._agents = [a for a in self._agents if a["id"] != agent_id]
        self._save_agents(self._agents)
        logger.info(f"[AGENT] 삭제: {agent_id}")

    # ── Tool Execution ─────────────────────────────────

    async def _execute_tool(self, tool: str, query: str, context: str = "") -> str:
        if tool == "sql":
            result = await self._sql_service.generate(question=query)
            sql = result.get("sql", "")
            if sql:
                exec_result = await self._sql_service.execute(sql=sql)
                rows = exec_result.get("rows", [])
                cols = exec_result.get("columns", [])
                if rows:
                    return f"SQL: {sql}\nColumns: {cols}\nRows ({len(rows)}):\n{json.dumps(rows[:20], ensure_ascii=False, default=str)}"
                return f"SQL: {sql}\nResult: No rows returned"
            return f"SQL generation failed: {result.get('explanation', 'unknown error')}"

        elif tool == "rag":
            try:
                results = self._vector_store.hybrid_search(
                    collection="all", query=query, top_k=5,
                )
                if not results:
                    return "No relevant documents found."
                parts = []
                for doc in results:
                    parts.append(f"[{doc.get('filename', '?')}] {doc['content'][:500]}")
                return "\n---\n".join(parts)
            except Exception as e:
                return f"RAG search failed: {e}"

        return ""

    # ── Single Agent Execution ─────────────────────────

    async def _run_agent(self, agent: dict, question: str, prior_context: str = "") -> dict:
        t0 = time.time()
        agent_id = agent["id"]
        logger.info(f"[AGENT] 실행 시작: {agent_id} ({agent.get('name', '')})")

        # Execute tools
        tool_results = []
        for tool in agent.get("tools", []):
            logger.info(f"[AGENT] {agent_id} → 도구 '{tool}' 호출 중...")
            result = await self._execute_tool(tool, question, prior_context)
            tool_results.append(f"[{tool.upper()} Result]\n{result}")
            logger.info(f"[AGENT] {agent_id} → 도구 '{tool}' 완료")

        # Build agent prompt
        tool_context = "\n\n".join(tool_results) if tool_results else ""

        user_content = f"Question: {question}"
        if prior_context:
            user_content = f"Previous agents' findings:\n{prior_context}\n\n{user_content}"
        if tool_context:
            user_content = f"{user_content}\n\nTool Results:\n{tool_context}"

        try:
            response = chat_completion(
                messages=[
                    {"role": "system", "content": agent["system_prompt"]},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
            )
            answer = response.choices[0].message.content or ""
            elapsed = time.time() - t0
            logger.info(f"[AGENT] {agent_id} 완료: {len(answer)}자 ({elapsed:.1f}초)")
        except Exception as e:
            logger.error(f"[AGENT] {agent_id} LLM 호출 실패: {e}")
            answer = f"Agent '{agent_id}' failed: {e}"

        return {
            "agent_id": agent_id,
            "agent_name": agent.get("name", agent_id),
            "icon": agent.get("icon", "🤖"),
            "answer": answer,
            "tools_used": agent.get("tools", []),
            "elapsed": round(time.time() - t0, 1),
        }

    # ── Orchestration ──────────────────────────────────

    async def orchestrate(self, question: str, agent_ids: list[str] | None = None) -> dict:
        t0 = time.time()
        logger.info(f"[ORCHESTRATOR] 질문: '{question[:80]}'")

        # Step 1: Select agents (auto or manual)
        if agent_ids:
            selected_ids = agent_ids
            logger.info(f"[ORCHESTRATOR] 수동 선택: {selected_ids}")
        else:
            selected_ids = await self._auto_select_agents(question)
            logger.info(f"[ORCHESTRATOR] 자동 선택: {selected_ids}")

        # Step 2: Execute agents in sequence, passing context
        results = []
        accumulated_context = ""
        for aid in selected_ids:
            agent = self.get_agent(aid)
            if not agent:
                logger.warning(f"[ORCHESTRATOR] 에이전트 '{aid}' 없음, 건너뜀")
                continue

            result = await self._run_agent(agent, question, accumulated_context)
            results.append(result)

            # Build accumulated context for next agent
            accumulated_context += f"\n\n[{result['agent_name']}의 분석]\n{result['answer']}"

        elapsed = time.time() - t0
        logger.info(f"[ORCHESTRATOR] 완료: {len(results)}개 에이전트, 총 {elapsed:.1f}초")

        return {
            "question": question,
            "agents_used": selected_ids,
            "results": results,
            "final_answer": results[-1]["answer"] if results else "No agents available.",
            "elapsed": round(elapsed, 1),
        }

    async def _auto_select_agents(self, question: str) -> list[str]:
        agent_list = "\n".join(
            f"- {a['id']}: {a['role']} (tools: {', '.join(a.get('tools', []))})"
            for a in self._agents
        )

        try:
            response = chat_completion(
                messages=[
                    {"role": "system", "content": ORCHESTRATOR_PROMPT.format(agent_list=agent_list)},
                    {"role": "user", "content": question},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content or "[]"
            # Parse JSON array from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            selected = json.loads(content)
            if isinstance(selected, list):
                return selected
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] 자동 선택 실패: {e}, 기본값 사용")

        # Fallback: use quality_analyst + doc_searcher
        return ["quality_analyst", "doc_searcher", "report_writer"]
