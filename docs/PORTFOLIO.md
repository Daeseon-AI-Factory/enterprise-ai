# Enterprise LLM Platform -- Portfolio

A production-grade AI platform for air-gapped enterprise environments, built solo with AI-assisted development.

---

## About Me

- **Name:** Jason (Daeseon Yoo)
- **Experience:** 5 years backend development at SK AX (Korea), specializing in Manufacturing Execution Systems (MES) and Warehouse Management Systems (WMS)
- **Key Achievement:** Optimized legacy Oracle queries from 45 seconds to 0.8 seconds (57% improvement), automated manual workflows equivalent to 2 full-time positions
- **Production Scale:** Managed millions of production records in Oracle, built cost management systems in C# and Java, debugged real factory floor problems
- **This Project:** Designed, architected, and built the entire platform solo using AI-assisted development (Claude Code), demonstrating both system design capability and modern AI-native development practices

---

## Project Overview

The Enterprise LLM Platform enables non-technical users in manufacturing environments to query databases using natural language, search internal documents with AI, and analyze operations -- all within air-gapped (closed network) environments where no data can leave the company network. A factory engineer can type "What's the defect rate on Line A this month?" and receive a natural language answer backed by real Oracle database queries and internal documentation, without writing a single line of SQL.

**Problem Statement:** Manufacturing, finance, and government organizations operate on closed networks with strict data sovereignty requirements. They cannot use cloud-based AI services (ChatGPT, Copilot) but desperately need AI capabilities to analyze production data, search internal documentation, and generate reports. Existing solutions either require internet connectivity or demand deep technical expertise to operate.

**Target Users:**
- Factory engineers querying production/defect data without SQL knowledge
- Analysts combining database results with internal documentation for reports
- Management needing real-time operational insights in natural language
- IT teams deploying AI tools on air-gapped infrastructure

---

## Architecture Deep Dive

### System Architecture

```
User (Browser)
      |
      v
+----------------------------------------------------------+
|  React + TypeScript + Tailwind CSS (SPA)                 |
|  - ChatPage, SqlPage, AskPage, RagPage, AgentManager     |
|  - JWT auth, session persistence, message windowing       |
+----------------------------------------------------------+
      |  REST API (axios + JWT Bearer token)
      v
+----------------------------------------------------------+
|  FastAPI Backend (Python, 19 routers, 16 services)       |
|                                                          |
|  +-------------+  +-------------+  +-----------------+   |
|  | Chat        |  | Text-to-SQL |  | Multi-Agent     |   |
|  | Service     |  | Service     |  | Orchestrator    |   |
|  +-------------+  +-------------+  +-----------------+   |
|  +-------------+  +-------------+  +-----------------+   |
|  | RAG         |  | Confluence  |  | Git Source      |   |
|  | Service     |  | Connector   |  | Indexer         |   |
|  +-------------+  +-------------+  +-----------------+   |
|                                                          |
|  +---------------------------------------------------+   |
|  | LLM Client (OpenAI-compatible API)                |   |
|  | base_url = OpenAI API  OR  local vLLM server      |   |
|  +---------------------------------------------------+   |
+----------------------------------------------------------+
      |                    |                    |
      v                    v                    v
+------------+    +----------------+    +----------------+
| ChromaDB   |    | Oracle / PG /  |    | LLM Server     |
| (vectors + |    | MySQL          |    | (OpenAI API    |
|  BM25)     |    | (customer DB)  |    |  or vLLM)      |
+------------+    +----------------+    +----------------+
```

**Component Breakdown:**

- **Frontend (React SPA):** 12 pages with session persistence, message windowing (renders only last 30 messages to prevent DOM lag), and configurable API base URL for proxy-free deployments. Built with Vite, served directly by FastAPI in production (single process, single port).
- **Backend (FastAPI):** 19 API routers delegating to 16 service classes. Async-first design for LLM calls that can take seconds. Auto-generated OpenAPI documentation. Pydantic request/response validation.
- **LLM Client:** A thin wrapper around the OpenAI Python client. Because both OpenAI and vLLM expose the same `/v1/chat/completions` endpoint, switching between cloud and local LLM requires only changing one environment variable (`LLM_API_BASE`).
- **Data Layer:** ChromaDB for vector storage (persistent SQLite-backed), customer's own database for Text-to-SQL, JSON files for conversations and settings.

### Text-to-SQL Pipeline

The core feature that transforms natural language questions into SQL queries against enterprise databases.

**Step-by-step flow:**

1. **Schema Registration (one-time):** User connects a database. The system runs metadata queries (`SELECT TABLE_NAME FROM USER_TABLES`, `SELECT COLUMN_NAME, DATA_TYPE FROM USER_TAB_COLUMNS`) to discover all tables, columns, data types, and foreign key relationships. The schema is saved as a JSON file.

2. **Prompt Construction:** When a user asks a question, the backend loads the saved schema, converts it to CREATE TABLE statements as text, and builds a prompt:
   ```
   [System] You are an expert Oracle SQL developer.
            Schema: CREATE TABLE MESADMIN.PRODUCTION_LINES (...);
                    CREATE TABLE MESADMIN.DEFECTS (...);
            FK: DEFECTS.ORDER_ID -> PRODUCTION_ORDERS.ORDER_ID
            Rules: Only SELECT, use Oracle syntax, prefix with schema owner...

   [User]   "What's the defect rate on Line A this month?"
   ```

3. **SQL Generation:** The LLM generates SQL. The system extracts it from the markdown code block in the response using regex.

4. **Validation:** Only SELECT queries are allowed. The SQL is checked against a blocklist (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE). Trailing semicolons are stripped (Oracle compatibility -- ORA-00911).

5. **Execution:** The validated SQL is executed against the customer's database via SQLAlchemy. Results are returned as structured JSON (columns + rows).

6. **Natural Language Response:** The raw data is sent back to the LLM with the original question to generate a human-readable answer.

**Why this works:** LLMs are trained on millions of SQL examples. They already understand SQL syntax perfectly. The only missing piece is the specific database schema -- which tables exist, what columns they have, and how they relate. By injecting the schema as text in the prompt, we give the LLM exactly the context it needs to generate accurate, database-specific SQL.

**Code snippet -- the generate function:**
```python
async def generate(self, question: str, schema_id: str = None):
    schema = self._load_schema(schema_id)       # Load from data/schemas.json
    schema_text = self._format_schema(schema)    # Convert to CREATE TABLE text

    messages = [
        {"role": "system", "content": SYSTEM_TEXT2SQL},
        {"role": "user", "content": f"Schema:\n{schema_text}\n\nQuestion: {question}"}
    ]

    response = chat_completion(messages=messages)
    sql = re.search(r"```sql\s*(.*?)\s*```", response, re.DOTALL).group(1)
    return {"sql": sql, "explanation": explanation}
```

### RAG Pipeline

Retrieval-Augmented Generation allows the LLM to answer questions based on uploaded internal documents.

**Step-by-step flow:**

1. **Document Upload:** User uploads PDF, Word, Excel, or code files. Each file is processed by a document loader that extracts text.

2. **Chunking:** Text is split into semantically meaningful segments (not fixed-size) using LangChain's text splitters. Average chunk size is ~376 characters.

3. **Embedding:** Each chunk is converted to a 1024-dimensional vector using the BGE-M3 embedding model (SentenceTransformer). The vectors capture semantic meaning -- similar texts produce similar vectors.

4. **Vector Storage:** Vectors and original text are stored in ChromaDB (persistent, SQLite-backed). A parallel BM25 index is maintained for keyword search.

5. **Hybrid Search:** When a user asks a question, the system runs two searches in parallel:
   - **Dense search (BGE-M3):** Finds semantically similar chunks via cosine similarity
   - **BM25 keyword search:** Finds chunks containing exact query terms
   Results from both are merged and scored.

6. **Reranking:** Combined results are reranked by relevance. Documents found by both methods get boosted scores.

7. **LLM Answer:** Top-k results are injected as context into the LLM prompt. The LLM generates an answer citing source documents.

**Why BGE-M3:** BAAI's BGE-M3 is a multilingual embedding model supporting 100+ languages with three retrieval modes (Dense, Sparse, ColBERT). This is critical for a Korean/English bilingual manufacturing environment where documents mix both languages.

**Why hybrid search matters:**
- **Dense search** catches semantic similarity: "acceptable defect rate" matches "must maintain defect rate below 3.0%" even though the exact words differ
- **BM25** catches exact terms: "ORA-01017 error" is matched precisely by keyword, which embedding search might miss
- **Reranking** boosts precision by promoting documents that appear in both result sets

### Multi-Agent Orchestration

Complex business queries require expertise across multiple domains. A single agent searching all tables and all documents produces noisy, inaccurate results. The multi-agent system solves this.

**How agents collaborate:**

1. **Orchestrator receives question** (e.g., "Why did defects increase on Line A?")
2. **Agent selection:** The orchestrator LLM analyzes the question and selects which specialist agents to involve (auto mode), or the user picks agents manually
3. **Sequential execution with context passing:** Each agent runs in sequence. Results from previous agents are accumulated and passed as context to the next agent.
4. **Scoped execution:** Each agent only sees its allowed tables and collections, reducing noise
5. **Result synthesis:** The final agent (Report Writer) synthesizes all previous results into a comprehensive answer

**Why scoping matters:** With 11 database tables and 7+ document collections, a single agent's context window gets flooded with irrelevant information. By restricting each agent to its domain:
- Quality Analyst sees only 3 tables (DEFECTS, PRODUCTION_ORDERS, PRODUCTION_LINES) instead of 11
- The LLM generates more precise SQL because it has a narrower, more relevant schema
- RAG results are more relevant because only domain-specific collections are searched

**Code snippet -- the orchestrator loop:**
```python
async def orchestrate(self, question: str, agent_ids: list[str] | None = None):
    # Step 1: Select agents (auto via LLM or manual)
    if agent_ids:
        selected_ids = agent_ids
    else:
        selected_ids = await self._auto_select_agents(question)

    # Step 2: Execute agents in sequence with context accumulation
    results = []
    accumulated_context = ""
    for aid in selected_ids:
        agent = self.get_agent(aid)
        result = await self._run_agent(agent, question, accumulated_context)
        results.append(result)
        accumulated_context += f"\n\n[{result['agent_name']}]\n{result['answer']}"

    return {
        "agents_used": selected_ids,
        "results": results,
        "final_answer": results[-1]["answer"] if results else "No agents available.",
    }
```

**Real example:**

```
User: "A Line defect cause analysis"

Orchestrator selects: [quality_analyst, doc_searcher, report_writer]

1. Quality Analyst (tables: DEFECTS, PRODUCTION_ORDERS, PRODUCTION_LINES)
   -> SQL: SELECT defect_type, COUNT(*) FROM DEFECTS WHERE line_id = 'A' ...
   -> Result: "Solder defects increased 300% since Feb 15"

2. Doc Searcher (collections: confluence_mes)
   -> RAG: Searches quality standards docs
   -> Result: "SMT paste must be replaced every 4 hours per SOP-QC-001"

3. Report Writer (synthesizes)
   -> "Line A defect rate spiked from 1.2% to 4.8% on Feb 15.
       Solder defects account for 72% of all defects.
       Per SOP-QC-001, SMT paste replacement every 4 hours is required.
       Recommendation: Audit paste replacement schedule for Line A."
```

### Air-gapped Deployment

The platform operates in two modes controlled by a single environment variable:

```bash
# Online mode (development, cloud)
MODE=local
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Air-gapped mode (production, closed network)
MODE=airgap
LLM_API_BASE=http://10.0.1.50:8000/v1    # Internal GPU server running vLLM
LLM_MODEL=openai/gpt-oss-120b
```

**Dual-mode architecture:** Because both OpenAI and vLLM implement the same API format (`POST /v1/chat/completions`), the application code is identical. Only the URL changes. The embedding model (BGE-M3, 4.3GB) runs on CPU locally -- no GPU required for embeddings.

**Offline package management:**
- 132 Python packages pre-downloaded as platform-specific wheels (`--python-version 3.12 --platform win_amd64 --only-binary=:all:`)
- Node modules packaged from working dev environment
- BGE-M3 embedding model bundled separately (500MB)
- Single `install.bat` for one-click setup
- Total package size: ~260MB (excluding embedding model and PyTorch)

---

## Troubleshooting Highlights

### 1. Oracle CDB vs PDB -- SID vs Service Name

**Problem:** `ORA-01017: invalid username/password` followed by `DPY-6003: SID "XEPDB1" is not registered with the listener` when connecting to Oracle XE Docker container.

**Root Cause:** Two separate issues compounded. First, Oracle 21c uses a Container Database (CDB) architecture. The Docker image creates the application user in the Pluggable Database (XEPDB1), not the CDB root (XE). Connecting to XE with XEPDB1 credentials fails. Second, SQLAlchemy treats `oracle+oracledb://user:pass@host:port/XEPDB1` as a SID connection, but XEPDB1 is a service name (PDB).

**Solution:** Changed the connection URL format from `/XEPDB1` (SID) to `/?service_name=XEPDB1` (Service Name). This correctly routes through the listener to the PDB where the user exists.

**Key Learning:** Oracle's CDB/PDB architecture means users, tablespaces, and data are isolated per PDB. Always confirm whether you need SID or Service Name format -- they look almost identical in the URL but behave completely differently at the listener level.

### 2. VectorStore OOM -- Singleton Pattern Fix

**Problem:** Backend crashes with out-of-memory after multiple API requests.

**Root Cause:** 9 different service classes each instantiated their own `VectorStore` object. Each instance loaded the BGE-M3 embedding model (4.3GB) independently. Result: 9 x 4.3GB = 38.7GB of memory consumed.

**Solution:** Implemented a singleton pattern (`get_vector_store()`) so all services share a single VectorStore instance with a single embedding model in memory.

**Key Learning:** When working with large ML models, always ensure exactly one instance exists in memory. The singleton pattern is the standard solution. This also informed the decision to add background warmup on server startup -- preloading the model once at boot rather than on first request.

### 3. RAG Quality Degradation -- Scoped Multi-Agent Solution

**Problem:** After syncing a Confluence space (hundreds of pages), RAG answers became irrelevant. A query about "Line A solder defects" returned results from HR onboarding guides and cover letter templates.

**Root Cause:** Searching all collections simultaneously mixes unrelated documents. With 7+ collections and 1500+ chunks, the top-k results contain noise from irrelevant domains. The LLM gets confused by contradictory or irrelevant context.

**Solution:** Implemented multi-agent architecture where each agent has scoped access to specific collections and tables. The Quality Analyst only searches `confluence_mes`. The Inventory Manager only searches `confluence_wms`. Noise is eliminated at the search level, not at the LLM level.

**Key Learning:** RAG quality is not just about embedding model quality or chunk size. The most impactful technique is controlling what gets searched. Scoping is more effective than any reranking algorithm when the fundamental problem is domain mixing.

### 4. Offline Deployment Python Version Mismatch

**Problem:** `Could not find a version that satisfies the requirement tiktoken==0.8.0` when installing on the target VDI machine.

**Root Cause:** Pip packages were downloaded on the development machine (Python 3.11) but the target VDI runs Python 3.12. Binary wheels (`.whl`) are version-specific -- a wheel built for `cp311` will not install on `cp312`.

**Solution:** Re-downloaded all packages with explicit target specification: `pip download --python-version 3.12 --platform win_amd64 --only-binary=:all:`. Also added a pre-deployment verification step: grep all source code imports against requirements.txt to catch missing dependencies.

**Key Learning:** Always confirm the target environment (Python version, OS, architecture) before building offline packages. This is now the first item on the air-gapped deployment checklist.

### 5. Chat Performance 10s to 2s -- RAG Removal from Pure Chat

**Problem:** The AI Chat page froze for 10+ seconds on the very first message, even for simple greetings like "hello".

**Root Cause:** The chat service called `_search_all_collections()` on every message, which triggered the 4.3GB embedding model to load into memory on first invocation (~10 seconds). This happened even for messages that had zero relevance to any documents.

**Solution:** Separated pure chat (LLM-only conversation) from knowledge-based queries. The `/chat` endpoint now uses only the LLM with no RAG overhead. Document search is handled exclusively by the dedicated `/ask` (multi-agent) and `/rag` endpoints. Response time dropped from 10+ seconds to 2 seconds.

**Key Learning:** Not every feature needs every capability. Coupling RAG into chat "just in case" created a 5x performance penalty for the most common use case. Keep pipelines lean -- add capabilities only to endpoints that need them.

---

## Technical Decisions Table

| Decision | Why | Trade-off |
|----------|-----|-----------|
| FastAPI over Django/Express | Async-first for LLM calls, auto OpenAPI docs, Pydantic validation | Smaller ecosystem than Django, but right fit for AI backend |
| ChromaDB over Pinecone/Weaviate | Runs locally as a file (chroma.sqlite3), no server needed, air-gapped compatible | Limited scalability vs. managed vector DBs, sufficient for 100-user target |
| Direct OpenAI API over LangChain | Fewer abstraction layers, easier debugging, fewer dependencies | More boilerplate, but full control over prompts and error handling |
| BGE-M3 over OpenAI embeddings | Multilingual (KO/EN), runs offline on CPU, Dense+Sparse+ColBERT modes | 4.3GB model size, 10s cold start (mitigated by warmup) |
| Hybrid search over pure vector | BM25 catches exact terms embedding misses (error codes, IDs) | Dual index maintenance, slightly more complex codebase |
| Multi-agent over single pipeline | Scoped search eliminates noise, domain-specific accuracy | Higher latency (sequential agent execution), more complex orchestration |
| Singleton VectorStore | Prevents OOM from duplicate 4.3GB model loads | Global state (acceptable trade-off for resource-constrained environments) |
| Unified server (FastAPI serves SPA) | Single process, single port, no Node.js in production | Must rebuild frontend for every UI change (acceptable for air-gapped deploy) |
| JSON file storage over PostgreSQL | Zero additional infrastructure, simple backup (copy files) | No concurrent write safety, will need DB for multi-user production |
| Custom agent framework over AutoGen/CrewAI | Zero external dependencies, 200 lines of code, full control | No community ecosystem, but exactly fits our requirements |

---

## Skills Demonstrated

**Backend:**
- Python, FastAPI, SQLAlchemy, Pydantic
- Oracle (CDB/PDB architecture, oracledb thin driver, ORA error debugging)
- PostgreSQL, MySQL (multi-database support)
- Async programming (asyncio, background tasks)
- REST API design (19 routers, JWT auth, OpenAPI)

**Frontend:**
- React, TypeScript, Tailwind CSS, Vite
- Session persistence (sessionStorage), message windowing
- Axios interceptors, streaming API integration
- Responsive SPA with configurable API base URL

**AI/ML:**
- RAG pipeline (document ingestion, chunking, embedding, hybrid retrieval, reranking)
- Text-to-SQL (schema injection, prompt engineering, SQL validation)
- Multi-agent orchestration (agent selection, scoped execution, context accumulation)
- Embedding models (BGE-M3, SentenceTransformers)
- LLM integration (OpenAI API, vLLM, prompt design)
- Conversation memory compression (hybrid recent + summary)

**Infrastructure:**
- Docker (Oracle XE, multi-service compose)
- vLLM (self-hosted LLM inference server)
- Air-gapped deployment (offline packages, environment isolation)
- Dual-mode architecture (cloud/on-premise via env variable)

**DevOps:**
- Offline package management (pip download with platform targeting)
- Automated verification (grep imports vs requirements.txt)
- Structured logging with tagged services
- Single-process production deployment (FastAPI serves SPA static files)

---

## Interview Q&A (Top 10)

### 1. How does Text-to-SQL work?

The system discovers the database schema by running metadata queries (USER_TABLES, USER_TAB_COLUMNS) and stores the structure as JSON. When a user asks a question, the backend converts the schema into CREATE TABLE text, injects it into the LLM prompt along with FK relationships and Oracle-specific rules, and the LLM generates SQL. The SQL is validated (SELECT only), executed via SQLAlchemy, and the results are formatted into a natural language answer. The key insight is that LLMs already know SQL syntax -- we only need to provide the specific table structure as context.

### 2. How do you maintain RAG accuracy at scale?

We use a multi-agent architecture where each agent has a scoped search space. Instead of one agent searching all 7 collections with 1500+ chunks, the Quality Analyst only searches `confluence_mes` (3 relevant docs), and the Inventory Manager only searches `confluence_wms`. This reduces noise dramatically. Combined with our three-stage retrieval pipeline (Dense embedding + BM25 keyword + reranking), we maintain production-grade accuracy even with thousands of documents. Scoping had the highest impact on accuracy -- more than any embedding model upgrade or chunk size optimization.

### 3. Why multi-agent over single pipeline?

A single pipeline searching 11 tables and all document collections floods the LLM context with irrelevant information. When the Quality Analyst only sees 3 tables instead of 11, the generated SQL is significantly more precise. Each agent is a specialist with scoped access -- narrower context means better results. The trade-off is higher latency (sequential execution), but accuracy is far more important than speed for enterprise analytical queries. We also built the framework from scratch in 200 lines -- no AutoGen, no CrewAI, zero external dependencies.

### 4. How do you handle air-gapped deployment?

The platform has a dual-mode architecture controlled by a single `MODE` environment variable. In `local` mode, it calls OpenAI's API. In `airgap` mode, it points to a local vLLM server on the internal network. Both OpenAI and vLLM implement the same API format, so the application code is identical -- only the URL changes. All Python packages (132 total) are pre-downloaded as platform-specific wheels. The embedding model runs on CPU locally. Zero data leaves the company network.

### 5. What happens when the LLM generates wrong SQL?

Multiple safeguards. First, only SELECT queries are allowed -- INSERT/UPDATE/DELETE/DROP are rejected before execution. Second, the SQL requires explicit user confirmation before running. Third, Oracle-specific quirks are handled automatically (trailing semicolons stripped to prevent ORA-00911). Fourth, if the SQL fails at execution, the error is returned to the user with the generated SQL visible for debugging. Fifth, using scoped agents that only see relevant tables significantly reduces the chance of wrong SQL in the first place. The system is designed for safety and transparency -- users always see the generated SQL before it runs.

### 6. Why did you choose FastAPI?

Three reasons. Async support out of the box, which is critical for LLM API calls that can take 2-60 seconds. Automatic OpenAPI documentation, so every endpoint is self-documenting. And Pydantic integration for request/response validation with type hints. It is the right balance of speed and structure for an AI backend. Django would be overkill, Express would lose Python's ML ecosystem.

### 7. How do you handle the 4.3GB embedding model in a resource-constrained environment?

Singleton pattern -- all 16 services share one VectorStore instance with one model in memory. We discovered this the hard way: 9 services each loading the model independently consumed 38.7GB. Background warmup on server startup preloads the model so the first request is not penalized with a 10-second cold start. Chat endpoints do not load the embedding model at all -- pure LLM, no RAG overhead.

### 8. Explain the hybrid search approach.

Pure vector search captures semantic similarity but misses exact terms. When a user searches for "ORA-01017 error," the embedding might match "authentication failure" but miss the exact error code. BM25 keyword search catches these exact matches. We run both searches in parallel, merge the results, and boost scores for documents found by both methods. This dual-index approach gives us the best of both worlds -- semantic understanding plus exact term matching.

### 9. How do you handle long conversations exceeding the LLM token limit?

Hybrid compression. When a conversation has 16 or fewer messages, all are sent verbatim. Beyond 16 messages, older messages are summarized by the LLM into 2-3 sentences, and only the most recent 10 messages are sent in full. The summary is cached per conversation to avoid regeneration. This keeps response times at 2-3 seconds even for conversations with hundreds of messages, while preserving the most important context.

### 10. What would you build differently if starting over?

Three things. First, I would use a proper database (PostgreSQL) instead of JSON files for conversation storage from day one -- the JSON approach works for single-user but breaks with concurrent access. Second, I would implement a background task queue (Celery or similar) for Confluence sync and large document embedding, which currently blocks the main server. Third, I would add query audit logging earlier -- every SQL execution should be tracked with user, timestamp, and query for compliance. The core architecture decisions (dual-mode LLM, hybrid RAG, scoped multi-agent) were correct and I would make the same choices again.

---

## Quick Reference -- Key Numbers

```
Backend:     19 API routers, 16 services, Python/FastAPI
Frontend:    12 pages, React/TypeScript/Tailwind CSS
Database:    Oracle 11 tables, 90 days MES/WMS simulated data
RAG:         Hybrid retrieval (Dense + BM25 + Reranker), BGE-M3 embedding
Packages:    132 Python packages, 15,000+ npm modules
Deployment:  Complete offline package (~260MB), single .env switch
Auth:        JWT + bcrypt, 24-hour token expiry
LLM:         OpenAI API / vLLM dual mode
Performance: Chat 10s -> 2s, SQL execution < 0.1s, Dashboard 4 calls -> 1
Agents:      4 default specialists, custom agent creation via UI
```

---

*Built by Jason (JasonAIFactory) -- 2026*
*AI-assisted development with Claude Code*
