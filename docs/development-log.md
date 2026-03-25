# Development Log — Troubleshooting, Improvements & Differentiators

This document records every major decision, bug fix, and architectural improvement made during the development of the Enterprise LLM Platform.

---

## 1. Troubleshooting Log

### 1.1 passlib + bcrypt 4.x Incompatibility
- **Symptom**: `module 'bcrypt' has no attribute '__about__'` on login
- **Root Cause**: passlib internally checks `bcrypt.__about__`, removed in bcrypt 4.x
- **Fix**: Removed passlib entirely, use bcrypt directly in `app/core/auth.py`
- **File**: `app/core/auth.py`

### 1.2 Python 3.11 f-string Backslash Error
- **Symptom**: `SyntaxError: f-string expression part cannot include a backslash`
- **Root Cause**: Python 3.11 restricts backslashes inside f-string expressions
- **Fix**: Extract variable before f-string: `stripped = path.rstrip('/\\')` then use in f-string
- **File**: `app/routers/git_rag.py`

### 1.3 Oracle CDB vs PDB Connection (ORA-01017)
- **Symptom**: `ORA-01017: invalid username/password` when connecting to Oracle XE Docker
- **Root Cause**: gvenzl/oracle-xe image creates APP_USER in XEPDB1 (PDB), not XE (CDB root). Connecting to XE with MESADMIN credentials fails.
- **Fix**: Changed DB_SERVICE from XE to XEPDB1 in docker-compose.yml
- **Key Learning**: Oracle 21c CDB/PDB architecture — users created in PDB are not visible from CDB root

### 1.4 Oracle SID vs Service Name (DPY-6003)
- **Symptom**: `DPY-6003: SID "XEPDB1" is not registered with the listener`
- **Root Cause**: SQLAlchemy URL `oracle+oracledb://user:pass@host:1521/XEPDB1` treats XEPDB1 as SID, but XEPDB1 is a service name (PDB)
- **Fix**: Changed URL format to `oracle+oracledb://user:pass@host:1521/?service_name=XEPDB1`
- **File**: `app/services/text2sql_service.py` `_build_db_url()`
- **Key Learning**: SID format = `/NAME`, Service Name format = `/?service_name=NAME`

### 1.5 VectorStore OOM — Duplicate Model Loading
- **Symptom**: Backend crashes with out-of-memory after multiple requests
- **Root Cause**: 9 different services each created their own VectorStore instance, loading the 4.3GB embedding model 9 times
- **Fix**: Singleton pattern `get_vector_store()` — all services share one instance
- **File**: `app/core/vector_store.py`

### 1.6 Text2SQL Schema Not Found in Analyze
- **Symptom**: `/api/analyze` generates wrong SQL with Korean placeholder table names
- **Root Cause**: Text2SqlService caches schemas in memory at init. Schemas registered via `/api/text2sql/schema/discover` are saved to file but not visible to other service instances.
- **Fix**: Reload schemas from file on each `generate()` call
- **File**: `app/services/text2sql_service.py`

### 1.7 Offline Package Version Mismatch (Python 3.11 vs 3.12)
- **Symptom**: `Could not find a version that satisfies the requirement tiktoken==0.8.0`
- **Root Cause**: Pip packages downloaded on Python 3.11 (dev PC) are not compatible with Python 3.12 (VDI)
- **Fix**: Download with explicit target: `pip download --python-version 3.12 --platform win_amd64 --only-binary=:all:`
- **Key Learning**: Always confirm target Python version BEFORE building offline packages

### 1.8 Missing python-jose in requirements.txt
- **Symptom**: `No module named jose` on VDI
- **Root Cause**: `app/core/auth.py` imports `jose` but it was never added to requirements.txt. Virtual env freeze missed it because it was installed separately.
- **Fix**: Added python-jose[cryptography] + all sub-dependencies (ecdsa, pyasn1, rsa)
- **Key Learning**: grep all imports against requirements.txt before declaring "done"

### 1.9 Missing Tailwind/PostCSS Config in ZIP
- **Symptom**: CSS completely broken on VDI — no styles applied
- **Root Cause**: ZIP was built with manual file list, missed `postcss.config.js` and `tailwind.config.ts`
- **Fix**: Added missing config files; future ZIPs include `platform/` directory entirely
- **Key Learning**: Never manually enumerate files for ZIP — use directory-level inclusion

### 1.10 Vite Proxy Not Working on VDI
- **Symptom**: `/api/health` returns 404 through Vite dev server, works directly on :8080
- **Root Cause**: Unknown VDI environment issue (possibly Node.js version or network config)
- **Fix**: Made `baseURL` configurable via `VITE_API_URL` env var. Set to `http://localhost:8080/api` for direct connection, bypassing proxy.
- **File**: `platform/src/lib/api.ts`
- **Key Learning**: Always provide direct-connection fallback for proxy-dependent architectures

### 1.11 Chat Freezing — Embedding Model Blocking
- **Symptom**: AI Chat hangs for 10+ seconds on first message
- **Root Cause**: Chat service called `_search_all_collections()` on every message, which triggers embedding model loading (4.3GB, ~10 seconds). Even for simple "hello" messages.
- **Fix**: Separated pure chat (no RAG) from knowledge-based queries. Chat uses only LLM, RAG is handled by dedicated `/ask` and `/analyze` endpoints.
- **Result**: Response time 10+ seconds → 2 seconds
- **File**: `app/services/chat_service.py`

---

## 2. Architectural Improvements

### 2.1 Conversation Memory Compression
- **Problem**: Long conversations exceed LLM token limit, responses get slow/fail
- **Solution**: Hybrid approach
  - Recent 10 messages: sent verbatim (preserves context flow)
  - Older messages: LLM-generated summary (2-3 sentences)
  - Summary cached per conversation to avoid regeneration
- **Config**: `RECENT_MSG_COUNT=10`, `SUMMARY_THRESHOLD=16`
- **File**: `app/services/chat_service.py` `_compress_history()`

### 2.2 Frontend Message Windowing
- **Problem**: 500+ messages in DOM causes browser lag/scroll jank
- **Solution**: Render only last 30 messages. "Load older" button adds 30 more on demand.
- **No external library needed** — pure React state management
- **File**: `platform/src/pages/ChatPage.tsx`

### 2.3 Structured Logging with Tags
- **Problem**: Logs were generic, hard to filter by feature
- **Solution**: Tagged logging: `[CHAT]`, `[SQL]`, `[RAG]`, `[UPLOAD]`
  ```
  [UPLOAD] 파일 수신: report.pdf (2.3MB) → 컬렉션 'default'
  [UPLOAD] 텍스트 추출 + 청킹 완료: 12개 청크 (평균 376자)
  [UPLOAD] 임베딩 + 저장 완료 → 컬렉션 'default' | 총 3.2초
  [CHAT]   질문: 'hello' (conv: db1d178f, 히스토리: 0→0개)
  [CHAT]   LLM 호출: 메시지 2개, 약 433자
  [CHAT]   LLM 응답: 34자 (2.0초)
  [SQL]    질문: 'show defect rate' (스키마: mes_oracle)
  [SQL]    실행 완료: 5행 반환 (0.08초)
  ```
- **Files**: `chat_service.py`, `rag_service.py`, `text2sql_service.py`

### 2.4 Configurable API Base URL
- **Problem**: Frontend assumes Vite proxy on same port. Breaks in production/air-gapped environments.
- **Solution**: `VITE_API_URL` environment variable. Defaults to `/api` (proxy), can be set to `http://localhost:8080/api` (direct).
- **File**: `platform/src/lib/api.ts`

### 2.5 Dashboard Stats Endpoint
- **Problem**: Dashboard made 4 separate API calls, some failed silently
- **Solution**: Single `/api/stats` endpoint aggregates collections, conversations, schemas with error handling per section
- **File**: `app/main.py`

### 2.6 SQL Execute with Connection Pass-through
- **Problem**: SQL execute only worked with .env DB credentials. Users who connected via UI couldn't execute queries.
- **Solution**: Accept optional `connection` dict in execute request. If provided, creates temporary engine for that connection.
- **Files**: `app/routers/text2sql.py`, `app/services/text2sql_service.py`, `platform/src/lib/api.ts`

### 2.7 Embedding Model Warmup on Startup
- **Problem**: First RAG query takes 10+ seconds (embedding model cold start)
- **Solution**: Background async warmup task on server startup
- **File**: `app/main.py` `_warmup()`

---

## 3. Product Differentiators

### 3.1 Air-gapped Deployment (폐쇄망 배포)
- Dual mode: `MODE=local` (OpenAI API) / `MODE=airgap` (self-hosted LLM)
- Single `.env` variable change switches between modes
- All dependencies packaged for offline install (Python + Node + embedding model)
- No cloud dependency — runs entirely on-premise

### 3.2 Text-to-SQL with Schema Auto-Discovery
- User connects DB → Platform automatically reads all tables/columns
- Schema stored as JSON, injected into LLM prompt at query time
- Supports Oracle, PostgreSQL, MySQL
- FK relationship hints in system prompt for accurate JOINs
- Safety: Only SELECT queries allowed, validated before execution

### 3.3 Hybrid RAG (Dense + BM25 + Reranker)
- Not simple vector search — three-stage retrieval:
  1. Dense embedding search (BGE-M3, multilingual)
  2. BM25 keyword search (exact term matching)
  3. Cross-encoder reranking (precision boost)
- Cross-collection search: queries all collections simultaneously
- Supports: PDF, Word, Excel, code files, Confluence pages

### 3.4 Separation of Chat vs Knowledge Query
- AI Chat: Pure LLM conversation, fast (no embedding overhead)
- Knowledge Query: RAG + DB combined, comprehensive answers
- Text-to-SQL: DB-only natural language queries
- Unified Analysis: All sources combined with cited evidence

### 3.5 MES/WMS Domain Demonstration
- Sample Oracle Docker with 90 days of manufacturing data
- 11 tables: production orders, defects, inventory, equipment, warehouses
- Simulated defect spike scenario for realistic demo
- Proves real-world applicability in manufacturing domain

### 3.6 AI Coding Agent (ai_code.py)
- 200-line coding agent that works with any OpenAI-compatible LLM
- File read/write, command execution, iterative problem-solving loop
- Runs on air-gapped GPU server with open-source models
- Foundation for building internal Claude Code alternative

### 3.7 Multilingual Support (KO/EN)
- UI language toggle (Korean/English) for all menu items
- LLM responds in user's language automatically
- BGE-M3 embedding model supports 100+ languages
- Documentation in both English and Korean

---

## 4. Performance Metrics

| Metric | Before | After |
|--------|--------|-------|
| Chat response (first message) | 10+ sec (embedding load) | 2 sec |
| Chat response (long conversation) | Timeout/fail | 2-3 sec (compressed) |
| Frontend scroll (500 messages) | Laggy/frozen | Smooth (windowed) |
| RAG upload feedback | Silent/hung | Real-time logging |
| Dashboard load | 4 API calls, partial failures | 1 call, graceful fallback |

---

## 5. Offline Deployment Checklist (Validated)

```
[x] Target Python version confirmed (3.12.10)
[x] Target OS/architecture confirmed (Windows AMD64)
[x] All code imports verified against requirements.txt (grep)
[x] Virtual env install → pip freeze → full dependency list (132 packages)
[x] Pip packages downloaded for target platform (--python-version 3.12 --platform win_amd64)
[x] python-jose + sub-dependencies included (ecdsa, pyasn1, rsa)
[x] node_modules packaged from working dev environment
[x] Embedding model (BGE-M3, 4.3GB) packaged separately
[x] .env.airgap configuration included
[x] postcss.config.js + tailwind.config.ts included
[x] vite.config.ts with proxy settings included
[x] VITE_API_URL fallback for direct connection documented
[x] Python/Node.js installers included
[x] VS Code extensions packaged (.vsix)
```

---

## 6. Multi-Agent Orchestration (2026-03-24)

### 6.1 Multi-Agent System — Zero External Dependencies
- **Motivation**: Enable domain-specific agents to collaborate on complex business queries
- **Architecture**: Orchestrator → Agent selection → Sequential execution with context passing
- **Key Decision**: No AutoGen/CrewAI/LangGraph. Built from scratch in 200 lines.
  - Same LLM (OSS-120B or GPT-4o-mini), different system prompts per agent
  - Tools: SQL, RAG (scoped to agent's allowed tables/collections)
- **Default Agents**:
  - 🔍 Quality Analyst: MES tables only (DEFECTS, PRODUCTION_ORDERS, etc.)
  - 📄 Document Searcher: RAG across all collections
  - 📦 Inventory Manager: WMS tables only (INVENTORY, INBOUND, OUTBOUND, etc.)
  - 📝 Report Writer: Synthesizes other agents' results
- **Files**: `app/services/multi_agent_service.py`, `app/routers/multi_agent.py`

### 6.2 Scoped Agent Execution — Table & Collection Restrictions
- **Problem**: Agents searching all 11 tables / all 7 collections → LLM confused, inaccurate
- **Solution**: Each agent has `tables[]` and `collections[]` fields
  - SQL tool: Only sends allowed table schemas to LLM → narrower context → better SQL
  - RAG tool: Only searches allowed collections → more relevant documents
- **Example**:
  ```
  Quality Analyst: tables=["DEFECTS","PRODUCTION_ORDERS","PRODUCTION_LINES"]
                   collections=["confluence_mes"]
  → LLM only sees 3 tables instead of 11 → generates precise SQL
  ```
- **UI**: Agent Manager page with table/collection picker (toggle buttons)

### 6.3 Agent Manager Page (/agents)
- **Features**: Create, edit, delete agents
- **Configurable fields**: name, domain, icon, system prompt, tools, tables, collections
- **UI shows**: Available tables from registered schemas, available collections from ChromaDB

### 6.4 Business Query Page (/ask) — Replaces Unified Analysis
- **Before**: /analyze page did RAG + SQL but no agent orchestration
- **After**: /ask page with multi-agent orchestration
  - Auto mode: AI selects which agents to involve
  - Manual mode: User picks specific agents
  - Execution timeline: Shows each agent's work, elapsed time, scope
  - Final answer: Last agent's synthesized output

---

## 7. UI/UX Improvements (2026-03-24)

### 7.1 Session State Persistence
- **Problem**: Navigating between pages resets all input/results
- **Root Cause**: React component unmount destroys state
- **Solution**: `sessionStorage` save/restore for key state variables
- **Applied**: AskPage (question, result, agent selection), SqlPage (question, SQL, results, history), RagPage (already had it)
- **Pattern**:
  ```typescript
  const [question, setQuestion] = useState(() => loadSession("question", ""));
  useEffect(() => { saveSession("question", question); }, [question]);
  ```

### 7.2 Pure Chat Mode — RAG Removed from /chat
- **Problem**: Chat page froze 10+ seconds on first message (embedding model loading)
- **Root Cause**: `_search_all_collections()` called on every chat message, triggering 4.3GB model load
- **Solution**: Chat is now pure LLM. RAG is only in /ask (multi-agent) and /rag (dedicated)
- **Result**: Chat response: 10+ sec → 2 sec

### 7.3 Conversation Compression
- **Problem**: Long conversations exceed LLM token limit
- **Solution**: Hybrid compression
  - Messages ≤ 16: send all verbatim
  - Messages > 16: summarize old messages + keep last 10 verbatim
  - Summary cached per conversation
- **Config**: `RECENT_MSG_COUNT=10`, `SUMMARY_THRESHOLD=16`

### 7.4 Frontend Message Windowing
- **Problem**: 500+ messages in DOM causes browser lag
- **Solution**: Render last 30 messages only. "Load older" button adds 30 more.
- **No external library**: Pure React state management

### 7.5 Configurable API Base URL
- **Problem**: Vite proxy didn't work on VDI
- **Solution**: `VITE_API_URL` env var. Set `http://localhost:8080/api` for direct connection.
- **Streaming fix**: `chatApi.stream()` now uses configurable base URL + auth token

### 7.6 Dashboard Stats API
- **Problem**: Dashboard made 4 separate API calls, some failed silently
- **Solution**: Single `/api/stats` endpoint with graceful fallback

---

## 8. Structured Logging System (2026-03-24)

### Log Tags
| Tag | Service | Example |
|-----|---------|---------|
| `[CHAT]` | ChatService | `[CHAT] 질문: 'hello' (conv: db1d, 히스토리: 0→0개)` |
| `[CHAT]` | ChatService | `[CHAT] LLM 응답: 34자 (2.0초)` |
| `[SQL]` | Text2SqlService | `[SQL] 질문: 'defect rate' (스키마: mes_oracle)` |
| `[SQL]` | Text2SqlService | `[SQL] 실행 완료: 5행 반환 (0.08초)` |
| `[RAG]` | RagService | `[RAG] 질의 시작: '생산 불량' (컬렉션: all)` |
| `[UPLOAD]` | RagService | `[UPLOAD] 파일 수신: report.pdf (2.3MB)` |
| `[UPLOAD]` | RagService | `[UPLOAD] 임베딩 + 저장 완료 → 총 3.2초` |
| `[AGENT]` | MultiAgentService | `[AGENT] 실행 시작: quality_analyst | 테이블: [DEFECTS...]` |
| `[AGENT-TOOL]` | MultiAgentService | `[AGENT-TOOL] quality_analyst SQL 생성: SELECT...` |
| `[AGENT-TOOL]` | MultiAgentService | `[AGENT-TOOL] quality_analyst SQL 실행 에러: ORA-00942` |
| `[AGENT-MGMT]` | MultiAgentService | `[AGENT-MGMT] 생성: line_monitor (라인 모니터)` |
| `[ORCHESTRATOR]` | MultiAgentService | `[ORCHESTRATOR] 자동 선택: ['quality_analyst', 'report_writer']` |
| `[ORCHESTRATOR]` | MultiAgentService | `[ORCHESTRATOR] 완료: 2개 에이전트, 총 22.7초` |

### Error Logging Principles
- API 200 OK but business error → `logger.error("[TAG] 비즈니스 에러: {msg}")`
- API 200 OK + success → `logger.info("[TAG] 완료: {detail}")`
- Exception caught → `logger.error("[TAG] 예외: {e}")` with full context
- All timing measured: `t0 = time.time()` → `elapsed = time.time() - t0`

---

## 9. RAG Quality Engineering (2026-03-25)

### 9.1 Problem: RAG Search Quality Degrades with More Documents

- **Symptom**: After syncing Confluence space (hundreds of pages), RAG answers became irrelevant
- **Root Cause**: Searching "all" collections at once mixes unrelated documents
  ```
  Query: "A라인 납땜불량 원인"
  Results:
    1. [confluence_mes] 생산 지시 처리 프로세스  ← 관련
    2. [test] Jake's Cover Letter Template       ← 완전 무관
    3. [confluence_dev] 온보딩 가이드             ← 무관
  → LLM gets confused by noise, gives poor answer
  ```
- **Key Learning**: RAG is NOT "throw all documents in and search". Scoping is critical.

### 9.2 Solution: Scoped Search via Multi-Agent Architecture

Instead of one agent searching everything, **each agent searches its own domain**:

```
Before (single agent, all documents):
  "A라인 불량 원인?" → searches 7 collections, 1500+ chunks
  → noisy results, inaccurate answer

After (multi-agent, scoped):
  Quality Analyst → confluence_mes only (3 docs)
  Inventory Manager → confluence_wms only (3 docs)
  Report Writer → synthesizes focused results
  → precise, relevant answers
```

### 9.3 Why This Matters (Interview-Ready Explanation)

```
Interviewer: "How do you maintain RAG accuracy as document count grows?"

Answer: "We use a multi-agent architecture where each agent has a scoped
search space. Instead of one agent searching all 7 collections with 1500+
chunks, the quality analyst only searches confluence_mes (3 relevant docs),
and the inventory manager only searches confluence_wms.

This reduces noise dramatically. The LLM receives only relevant context,
so SQL generation and answers are more accurate.

We also use a three-stage retrieval pipeline:
1. Dense embedding search (BGE-M3, multilingual)
2. BM25 keyword matching (exact terms)
3. Cross-encoder reranking (precision boost)

The combination of scoped search + hybrid retrieval gives us production-grade
accuracy even with thousands of documents."
```

### 9.4 RAG Quality Improvement Techniques (Ordered by Impact)

| Technique | Impact | Implemented |
|-----------|--------|-------------|
| **Agent-scoped collections** | High | ✅ Yes |
| **Hybrid search (Dense + BM25)** | High | ✅ Yes |
| **Cross-encoder reranking** | High | ✅ Yes |
| **Semantic chunking** | Medium | ✅ Yes |
| **Metadata filtering** (date, domain) | Medium | Planned |
| **Query expansion** (rephrase query) | Medium | Planned |
| **User feedback loop** (thumbs up/down) | Low-Medium | Planned |
| **Fine-tuned embedding model** | Low (BGE-M3 already good) | Not needed |

### 9.5 Confluence Integration Learnings

- **Authentication**: Confluence Server uses Basic Auth (ID + password), NOT API tokens
- **API Token location varies**: Cloud = id.atlassian.com, Server = profile settings (may not exist)
- **Space sync blocks backend**: Embedding large spaces (100+ pages) blocks all other requests
  - **Fix needed**: Background worker for sync (async task queue)
- **HTML to Text**: BeautifulSoup `get_text()` strips all HTML. Tables become flat text.
  - **Improvement needed**: HTML table → Markdown table conversion for better LLM understanding

### 9.6 LLM Timeout for Large Models

- **Symptom**: RAG queries hang for 1+ minutes with no response
- **Root Cause**: OpenAI client default timeout (60s) too short for OSS-120B model
- **Fix**: Set explicit timeout `httpx.Timeout(300.0, connect=10.0)` — 5 minute response timeout
- **File**: `app/llm_client.py`
- **Key Learning**: Large open-source models (70B+) can take 30-60 seconds per response. Always set generous timeouts.

### 9.7 GPU vs CPU Embedding — "cannot copy out of meta tensor"

- **Symptom**: `cannot copy out of meta tensor` error when registering Confluence page
- **Root Cause**: PyTorch attempting GPU operations on CPU-only machine, or concurrent embedding requests causing memory pressure
- **Context**: Confluence sync was still running (embedding pages) when user tried URL registration simultaneously
- **Fix**: Wait for sync to complete before additional embedding operations
- **Improvement needed**: Queue-based embedding to prevent concurrent model access

---

## 10. Production Deployment Architecture (2026-03-25)

### 10.1 Unified Server — No Node.js Required

- **Before**: Backend (Python :8080) + Frontend (Vite/Node :3000) = 2 processes, 2 ports
- **After**: `npm run build` → `platform/dist/` → FastAPI serves static files
  ```
  http://localhost:8080/         → React SPA (index.html)
  http://localhost:8080/api/*    → FastAPI backend
  http://localhost:8080/assets/* → CSS/JS static files
  ```
- **Result**: Single process, single port, Python only
- **User experience**: `start.bat` double-click → browser opens → done
- **File**: `app/main.py` — SPA catch-all route serves index.html for all non-API paths

### 10.2 Deployment Options Comparison

| Method | Requirements | Best For |
|--------|-------------|----------|
| **Local PC** | Python only | Individual use, demo |
| **Linux server** | Python + nginx | Team (10-100 users) |
| **Docker** | Docker only | Easy deployment |
| **Air-gapped** | Python + offline packages | Closed networks |

---

*Last updated: 2026-03-25*
*Author: Jason (JasonAIFactory)*
