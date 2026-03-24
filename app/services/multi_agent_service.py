"""
Multi-Agent Orchestration Service

Each agent has:
  - name, role, system_prompt, domain, icon
  - tools: ["sql", "rag"]
  - tables: ["DEFECTS", "PRODUCTION_ORDERS"] — SQL scope (empty = all)
  - collections: ["confluence_mes"] — RAG scope (empty = all)
"""

import json
import time
from pathlib import Path

from loguru import logger

from app.llm_client import chat_completion
from app.core.vector_store import get_vector_store
from app.services.text2sql_service import Text2SqlService

AGENTS_FILE = Path("./data/agents.json")

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
        "tables": ["PRODUCTION_LINES", "PRODUCTION_ORDERS", "WORK_RESULTS", "DEFECTS", "EQUIPMENT"],
        "collections": ["confluence_mes"],
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
            "Use the RAG tool to search across document collections.\n"
            "Always cite the source document filename.\n"
            "Respond in the same language as the user."
        ),
        "tools": ["rag"],
        "tables": [],
        "collections": [],
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
        "tables": ["WAREHOUSES", "ITEMS", "INVENTORY", "INBOUND", "OUTBOUND"],
        "collections": ["confluence_wms"],
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
        "tables": [],
        "collections": [],
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
        logger.info(f"[AGENT-MGMT] 생성: {agent['id']} ({agent.get('name', '')})")
        return agent

    def update_agent(self, agent_id: str, updates: dict) -> dict:
        for i, a in enumerate(self._agents):
            if a["id"] == agent_id:
                self._agents[i] = {**a, **updates, "id": agent_id}
                self._save_agents(self._agents)
                logger.info(f"[AGENT-MGMT] 수정: {agent_id}")
                return self._agents[i]
        raise ValueError(f"Agent '{agent_id}' not found")

    def delete_agent(self, agent_id: str) -> None:
        self._agents = [a for a in self._agents if a["id"] != agent_id]
        self._save_agents(self._agents)
        logger.info(f"[AGENT-MGMT] 삭제: {agent_id}")

    # ── Scoped Schema for Agent ────────────────────────

    def _get_scoped_schema(self, agent: dict) -> str:
        """Get schema text filtered to agent's allowed tables."""
        allowed_tables = agent.get("tables", [])
        self._sql_service._schemas = self._sql_service._load_schemas()

        if not self._sql_service._schemas:
            logger.warning(f"[AGENT] {agent['id']}: 등록된 스키마 없음")
            return ""

        first_key = next(iter(self._sql_service._schemas))
        schema = self._sql_service._schemas[first_key]

        if not allowed_tables:
            # No restriction — use all tables
            return self._sql_service._format_schema(schema)

        # Filter to allowed tables only
        filtered = {
            "schema_id": schema.get("schema_id", first_key),
            "tables": [t for t in schema.get("tables", [])
                       if t.get("name", "").upper() in [x.upper() for x in allowed_tables]],
        }
        if not filtered["tables"]:
            logger.warning(f"[AGENT] {agent['id']}: 허용 테이블 {allowed_tables} 중 매칭 없음")
            return self._sql_service._format_schema(schema)

        logger.info(f"[AGENT] {agent['id']}: 스키마 범위 제한 → {[t['name'] for t in filtered['tables']]}")
        return self._sql_service._format_schema(filtered)

    # ── Tool Execution (Scoped) ────────────────────────

    async def _execute_tool(self, tool: str, query: str, agent: dict) -> str:
        t0 = time.time()

        if tool == "sql":
            # Generate SQL with scoped schema
            scoped_schema = self._get_scoped_schema(agent)
            if not scoped_schema:
                msg = "DB 스키마 미등록. SQL 메뉴에서 스키마를 먼저 등록해주세요."
                logger.error(f"[AGENT-TOOL] {agent['id']} SQL 실패: {msg}")
                return msg

            from app.core.prompts import SYSTEM_TEXT2SQL
            try:
                response = chat_completion(
                    messages=[
                        {"role": "system", "content": SYSTEM_TEXT2SQL},
                        {"role": "user", "content": f"Schema:\n{scoped_schema}\n\nQuestion: {query}"},
                    ],
                    temperature=0.1,
                )
                content = response.choices[0].message.content or ""
                sql, explanation = self._sql_service._parse_response(content)
            except Exception as e:
                msg = f"SQL 생성 LLM 호출 실패: {e}"
                logger.error(f"[AGENT-TOOL] {agent['id']} {msg}")
                return msg

            if not sql or not self._sql_service._is_safe_sql(sql):
                msg = f"SQL 생성 실패 또는 안전하지 않은 쿼리: {sql[:100]}"
                logger.warning(f"[AGENT-TOOL] {agent['id']} {msg}")
                return msg

            logger.info(f"[AGENT-TOOL] {agent['id']} SQL 생성: {sql[:100]}")

            exec_result = await self._sql_service.execute(sql=sql)
            if "error" in exec_result and exec_result["error"]:
                msg = f"SQL 실행 에러: {exec_result['error']}"
                logger.error(f"[AGENT-TOOL] {agent['id']} {msg}")
                return f"SQL: {sql}\n{msg}"

            rows = exec_result.get("rows", [])
            cols = exec_result.get("columns", [])
            elapsed = time.time() - t0
            logger.info(f"[AGENT-TOOL] {agent['id']} SQL 실행 완료: {len(rows)}행 ({elapsed:.1f}초)")

            if rows:
                return f"SQL: {sql}\nColumns: {cols}\nRows ({len(rows)}):\n{json.dumps(rows[:20], ensure_ascii=False, default=str)}"
            return f"SQL: {sql}\nResult: No rows returned (0행)"

        elif tool == "rag":
            allowed_collections = agent.get("collections", [])
            try:
                if allowed_collections:
                    # Search only allowed collections
                    all_results = []
                    for col_name in allowed_collections:
                        try:
                            hits = self._vector_store.hybrid_search(
                                collection=col_name, query=query, top_k=3,
                            )
                            for h in hits:
                                h["collection"] = col_name
                            all_results.extend(hits)
                        except Exception as e:
                            logger.warning(f"[AGENT-TOOL] {agent['id']} RAG '{col_name}' 검색 실패: {e}")
                    all_results.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
                    results = all_results[:5]
                    logger.info(f"[AGENT-TOOL] {agent['id']} RAG 범위 제한: {allowed_collections} → {len(results)}건")
                else:
                    # Search all collections
                    results = self._vector_store.hybrid_search(
                        collection="all", query=query, top_k=5,
                    )
                    logger.info(f"[AGENT-TOOL] {agent['id']} RAG 전체 검색 → {len(results)}건")

                if not results:
                    msg = "관련 문서를 찾지 못했습니다."
                    logger.info(f"[AGENT-TOOL] {agent['id']} RAG: {msg}")
                    return msg

                elapsed = time.time() - t0
                parts = []
                for doc in results:
                    col = doc.get("collection", "?")
                    fname = doc.get("filename", "?")
                    parts.append(f"[{col}/{fname}]\n{doc['content'][:500]}")
                logger.info(f"[AGENT-TOOL] {agent['id']} RAG 완료: {len(results)}건 ({elapsed:.1f}초)")
                return "\n---\n".join(parts)

            except Exception as e:
                msg = f"RAG 검색 실패: {e}"
                logger.error(f"[AGENT-TOOL] {agent['id']} {msg}")
                return msg

        msg = f"알 수 없는 도구: {tool}"
        logger.error(f"[AGENT-TOOL] {agent['id']} {msg}")
        return msg

    # ── Single Agent Execution ─────────────────────────

    async def _run_agent(self, agent: dict, question: str, prior_context: str = "") -> dict:
        t0 = time.time()
        agent_id = agent["id"]
        tables = agent.get("tables", [])
        collections = agent.get("collections", [])
        logger.info(
            f"[AGENT] 실행 시작: {agent_id} ({agent.get('name', '')})"
            f" | 도구: {agent.get('tools', [])}"
            f" | 테이블: {tables or '전체'}"
            f" | 컬렉션: {collections or '전체'}"
        )

        # Execute tools with scope
        tool_results = []
        for tool in agent.get("tools", []):
            logger.info(f"[AGENT] {agent_id} → 도구 '{tool}' 호출 중...")
            result = await self._execute_tool(tool, question, agent)
            tool_results.append(f"[{tool.upper()} Result]\n{result}")

        # Build agent prompt
        tool_context = "\n\n".join(tool_results) if tool_results else ""

        user_content = f"Question: {question}"
        if prior_context:
            user_content = f"Previous agents' findings:\n{prior_context}\n\n{user_content}"
        if tool_context:
            user_content = f"{user_content}\n\nTool Results:\n{tool_context}"

        try:
            t1 = time.time()
            response = chat_completion(
                messages=[
                    {"role": "system", "content": agent["system_prompt"]},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
            )
            answer = response.choices[0].message.content or ""
            elapsed = time.time() - t0
            logger.info(f"[AGENT] {agent_id} 완료: {len(answer)}자, LLM {time.time()-t1:.1f}초, 총 {elapsed:.1f}초")
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"[AGENT] {agent_id} LLM 호출 실패 ({elapsed:.1f}초): {e}")
            answer = f"에이전트 '{agent.get('name', agent_id)}' 실행 실패: {e}"

        return {
            "agent_id": agent_id,
            "agent_name": agent.get("name", agent_id),
            "icon": agent.get("icon", "🤖"),
            "answer": answer,
            "tools_used": agent.get("tools", []),
            "tables_scope": tables or ["ALL"],
            "collections_scope": collections or ["ALL"],
            "elapsed": round(time.time() - t0, 1),
        }

    # ── Orchestration ──────────────────────────────────

    async def orchestrate(self, question: str, agent_ids: list[str] | None = None) -> dict:
        t0 = time.time()
        logger.info(f"[ORCHESTRATOR] ========== 새 질의 ==========")
        logger.info(f"[ORCHESTRATOR] 질문: '{question[:80]}'")

        # Step 1: Select agents
        if agent_ids:
            selected_ids = agent_ids
            logger.info(f"[ORCHESTRATOR] 수동 선택: {selected_ids}")
        else:
            selected_ids = await self._auto_select_agents(question)
            logger.info(f"[ORCHESTRATOR] 자동 선택: {selected_ids}")

        # Step 2: Execute agents in sequence
        results = []
        accumulated_context = ""
        for i, aid in enumerate(selected_ids):
            agent = self.get_agent(aid)
            if not agent:
                logger.warning(f"[ORCHESTRATOR] 에이전트 '{aid}' 없음, 건너뜀")
                continue

            logger.info(f"[ORCHESTRATOR] [{i+1}/{len(selected_ids)}] {aid} 실행 중...")
            result = await self._run_agent(agent, question, accumulated_context)
            results.append(result)
            accumulated_context += f"\n\n[{result['agent_name']}의 분석]\n{result['answer']}"

        elapsed = time.time() - t0
        logger.info(f"[ORCHESTRATOR] ========== 완료: {len(results)}개 에이전트, 총 {elapsed:.1f}초 ==========")

        return {
            "question": question,
            "agents_used": selected_ids,
            "results": results,
            "final_answer": results[-1]["answer"] if results else "실행 가능한 에이전트가 없습니다.",
            "elapsed": round(elapsed, 1),
        }

    async def _auto_select_agents(self, question: str) -> list[str]:
        agent_list = "\n".join(
            f"- {a['id']}: {a['role']} (tools: {', '.join(a.get('tools', []))}, "
            f"tables: {a.get('tables', []) or 'ALL'}, "
            f"collections: {a.get('collections', []) or 'ALL'})"
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
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            selected = json.loads(content)
            if isinstance(selected, list):
                logger.info(f"[ORCHESTRATOR] AI 선택 결과: {selected}")
                return selected
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] 자동 선택 실패: {e}")

        fallback = ["quality_analyst", "doc_searcher", "report_writer"]
        logger.warning(f"[ORCHESTRATOR] 기본값 사용: {fallback}")
        return fallback
