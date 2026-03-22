# Enterprise LLM Platform — Interview Script

## 1. Project Overview (프로젝트 개요)

**Q: Can you describe your project?**

> "I built an Enterprise LLM Platform designed for air-gapped (closed network) environments. It allows non-technical users to query databases using natural language, search internal documents with AI, and analyze source code — all without any data leaving the company network.
>
> The platform connects to existing enterprise systems like Oracle databases and Confluence, so there's no manual document upload needed. Once connected, users can ask questions like 'What's the defect rate on Line A this month?' and the system automatically generates SQL, executes it against Oracle, and returns a natural language answer."

**한국어 핵심:** 폐쇄망에서 자연어로 DB 조회 + 문서 검색 + 코드 분석이 가능한 AI 플랫폼을 만들었습니다.

---

## 2. Text-to-SQL (자연어 → SQL)

**Q: How does your Text-to-SQL feature work?**

> "It's a three-step process.
>
> First, when we register a database, the system runs metadata queries like `SELECT TABLE_NAME FROM USER_TABLES` to extract the schema — table names, column names, data types, and foreign key relationships. This is stored as a JSON file.
>
> Second, when a user asks a question, the backend constructs a prompt that includes the schema as text plus the user's question, and sends it to the LLM. The LLM generates SQL because it was trained on millions of SQL examples.
>
> Third, we validate the SQL — only SELECT queries are allowed — strip trailing semicolons for Oracle compatibility, execute it, and return the results. The LLM then formats the raw data into a natural language answer."

**Q: What databases do you support?**

> "Oracle, PostgreSQL, and MySQL. The connection URL format is dynamically built based on the `db_type` parameter. For Oracle specifically, we use the `oracledb` thin driver with service name connection format: `oracle+oracledb://user:pass@host:port/?service_name=XE`."

**Q: How do you prevent SQL injection or dangerous queries?**

> "We only allow SELECT statements. Before execution, we check if the SQL starts with INSERT, UPDATE, DELETE, DROP, or ALTER — if so, it's rejected. The SQL also requires explicit user confirmation before execution. This is a whitelist approach rather than a blacklist."

---

## 3. RAG (Retrieval-Augmented Generation)

**Q: Explain your RAG pipeline.**

> "We use a hybrid retrieval approach with three stages.
>
> Stage one is **dense retrieval** — documents are chunked using semantic chunking, embedded with a SentenceTransformer model (BGE-M3), and stored in ChromaDB.
>
> Stage two is **BM25 keyword search** — we maintain a parallel BM25 index for traditional keyword matching. This catches exact terms that embedding-based search might miss.
>
> Stage three is **reranking** — results from both dense and BM25 are merged and reranked by relevance score. The top-k results are then injected into the LLM prompt as context.
>
> This hybrid approach significantly outperforms pure vector search, especially for technical documents with specific terminology."

**Q: Why hybrid instead of just vector search?**

> "Pure vector search is good at semantic similarity but bad at exact keyword matching. If a user asks about 'ORA-01017 error', vector search might miss it because the embedding doesn't capture the exact error code well. BM25 catches these exact matches. Combining both gives us the best of both worlds."

**Q: How do you handle document ingestion?**

> "We support PDF, Word, Excel, and code files. Each file goes through a document loader that extracts text, then a semantic chunker that splits it into meaningful segments rather than fixed-size chunks. Each chunk is embedded and stored in ChromaDB with metadata like filename, collection name, and chunk ID. For Confluence, we use the REST API to pull pages, strip HTML tags with BeautifulSoup, and index the clean text."

---

## 4. Architecture (아키텍처)

**Q: Describe the system architecture.**

> "The platform has four layers.
>
> **Frontend** — React with TypeScript, Tailwind CSS, and Vite. It communicates with the backend through a REST API with JWT authentication.
>
> **Backend** — FastAPI with 19 routers covering chat, RAG, Text-to-SQL, code generation, Confluence sync, Git indexing, and more. Each router delegates to a service layer that contains the business logic.
>
> **Data layer** — ChromaDB for vector storage, SQLite for ChromaDB persistence, JSON files for conversations and settings, and the customer's own database (Oracle/PostgreSQL) for Text-to-SQL.
>
> **LLM layer** — configurable. In online mode, it calls OpenAI API. In air-gapped mode, it calls a local vLLM server running an open-source model. The switch is a single environment variable — `LLM_API_BASE`."

**Q: How does the air-gapped mode work?**

> "The platform has a dual-mode design controlled by the `MODE` environment variable. In `local` mode, it uses OpenAI's API. In `airgap` mode, it points `LLM_API_BASE` to a local vLLM server running on a GPU server within the internal network.
>
> The embedding model is bundled with the deployment package, so it runs on CPU without any internet connection. ChromaDB runs as a local persistent database. The only network dependency is the LLM inference server, which is on the internal network.
>
> This means zero data leaves the company network — which is a hard requirement for manufacturing, finance, and government clients."

---

## 5. MES/WMS Domain (제조 도메인)

**Q: Tell me about your manufacturing domain experience.**

> "I spent 5 years building MES and WMS systems at SK AX. MES is Manufacturing Execution System — it tracks production orders, work results, defect rates, and equipment status on the factory floor. WMS is Warehouse Management System — it handles inventory, inbound/outbound logistics, and warehouse locations.
>
> For this project, I created a sample MES/WMS database with Oracle Docker — 11 tables including production lines, production orders, work results, defects, equipment, warehouses, inventory, and inbound/outbound records. It has 90 days of simulated data with realistic patterns, including a defect spike on Line A starting in February to demonstrate anomaly detection.
>
> When a user asks 'Why did defects increase on Line A?', the platform queries the actual Oracle data, retrieves related documentation from RAG, and gives a combined analysis."

---

## 6. Technical Decisions (기술 결정)

**Q: Why FastAPI instead of Django or Express?**

> "Three reasons. First, async support out of the box — important for LLM API calls that can take seconds. Second, automatic OpenAPI documentation — every endpoint is self-documenting. Third, Pydantic integration for request/response validation with type hints. It's the right balance of speed and structure for an AI backend."

**Q: Why ChromaDB instead of Pinecone or Weaviate?**

> "ChromaDB can run as a local persistent database without a server. For air-gapped deployment, we can't rely on cloud services like Pinecone, and running a Weaviate cluster is overkill for our scale. ChromaDB gives us vector search in a single file — `chroma.sqlite3` — which is perfect for on-premise deployment."

**Q: Why not use LangChain more extensively?**

> "We use LangChain minimally — mainly for text splitting. For the core RAG pipeline and Text-to-SQL, we call the OpenAI-compatible API directly. LangChain adds abstraction layers that make debugging harder and create unnecessary dependencies. For a production system, direct API calls give us more control and fewer failure points."

---

## 7. Challenges & Solutions (어려웠던 점)

**Q: What was the most challenging part?**

> "The Oracle connection in air-gapped environments. Oracle uses two connection formats — SID and Service Name — and they look almost identical in the connection URL but behave differently. We initially used SID format, which caused a DPY-6003 error because the PDB (XEPDB1) is a service name, not a SID.
>
> The fix was changing the SQLAlchemy URL from `oracle+oracledb://user:pass@host:port/XEPDB1` to `oracle+oracledb://user:pass@host:port/?service_name=XEPDB1`. Small change, but it took significant debugging to identify.
>
> Another challenge was the embedding model loading. It takes about 10 seconds to load into memory. If a user sends a query during startup, the request would fail. We solved this by adding async background warmup on server start."

**Q: How did you handle the offline package deployment?**

> "Air-gapped deployment means no pip install from PyPI. We created a virtual environment, installed all dependencies, ran `pip freeze` to get the complete list of 132 packages including transitive dependencies, then used `pip download` with `--python-version 3.12 --platform win_amd64 --only-binary=:all:` to download platform-specific wheels. The entire offline package is about 260MB and installs with a single command."

---

## 8. Scalability & Future (확장성)

**Q: How would you scale this for 100+ users?**

> "The current architecture supports 100 users with minimal changes. The LLM inference is the bottleneck — vLLM handles batching automatically, so concurrent requests are queued efficiently. ChromaDB reads are fast for our data size. For larger scale, I'd add Redis for caching frequent queries, connection pooling for database access, and potentially separate the embedding service into its own process."

**Q: What would you add next?**

> "Three things. First, a proper RBAC system — role-based access control so different users can access different databases and collections. Second, query audit logging — every SQL execution should be logged with user, timestamp, and query. Third, response accuracy measurement — comparing LLM-generated SQL results against expected answers to continuously improve the system prompt."

---

## 9. AI-Assisted Development (AI 활용)

**Q: Did you use AI tools to build this?**

> "Yes, extensively. I used Claude Code as my primary development tool. I designed the architecture, defined the requirements, and made all technical decisions. Claude Code helped with implementation — writing the code, debugging issues, and handling boilerplate.
>
> This is how modern software development works. The value isn't in typing code — it's in knowing what to build, how components should connect, and making the right trade-offs. I could explain every component of this system because I designed it, even though I didn't type every line manually.
>
> In fact, this project itself demonstrates AI-assisted development — which is exactly what the platform enables for other developers and business users."

---

## 10. Why Should We Hire You? (왜 채용해야 하나?)

**Q: What makes you different from other candidates?**

> "Three things make me unique.
>
> First, I have real manufacturing domain expertise — 5 years of MES/WMS development. I understand production lines, defect tracking, inventory management, and supply chain logistics. Most AI engineers don't have this domain knowledge.
>
> Second, I can go from concept to working product fast. This entire platform — backend, frontend, database integration, air-gapped deployment — was built in days, not months. I know how to leverage AI tools to multiply my output.
>
> Third, I understand both sides — the enterprise IT constraints like closed networks and legacy databases, and the modern AI stack like RAG, LLM integration, and vector databases. I can bridge the gap between traditional enterprise systems and AI capabilities."

---

## Quick Reference — Key Numbers

```
Backend:   19 API routers, 16 services, Python/FastAPI
Frontend:  12 pages, React/TypeScript/Tailwind
Database:  Oracle 11 tables, 90 days MES/WMS data
RAG:       Hybrid retrieval (Dense + BM25 + Reranker)
Packages:  132 Python, 15,000+ npm modules
Airgap:    Complete offline deployment (260MB)
Auth:      JWT + bcrypt
LLM:       OpenAI API / vLLM (dual mode)
```
