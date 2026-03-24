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

*Last updated: 2026-03-24*
*Author: Jason (JasonAIFactory)*
