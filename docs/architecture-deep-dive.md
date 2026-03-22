# Enterprise LLM Platform — Architecture Deep Dive

A detailed, code-level explanation of how every component works.
Written so that anyone — even with no prior context — can fully understand the system.

---

## Table of Contents

1. [How the Server Starts](#1-how-the-server-starts)
2. [How Authentication Works](#2-how-authentication-works)
3. [How Text-to-SQL Works (Step by Step)](#3-how-text-to-sql-works)
4. [How RAG Works (Step by Step)](#4-how-rag-works)
5. [How Unified Analysis Works](#5-how-unified-analysis-works)
6. [How the Frontend Connects to Backend](#6-how-the-frontend-connects-to-backend)
7. [How Air-gapped Mode Works](#7-how-air-gapped-mode-works)
8. [How the AI Coding Agent Works](#8-how-the-ai-coding-agent-works)
9. [How Git Source Indexing Works](#9-how-git-source-indexing-works)
10. [How Confluence Integration Works](#10-how-confluence-integration-works)

---

## 1. How the Server Starts

When you run `python -m uvicorn app.main:app --port 8080`, here's exactly what happens:

### Step 1: Python loads `app/main.py`

```python
# app/main.py — This is the entry point

from fastapi import FastAPI
from app.config import settings         # Load .env settings
from app.routers import (              # Import all API routers
    auth, chat, rag, text2sql,
    confluence, git_rag, analyze, ...
)

app = FastAPI(title="Enterprise LLM Platform")

# Register every router with its URL prefix
app.include_router(auth.router,     prefix="/api/auth")      # /api/auth/login
app.include_router(chat.router,     prefix="/api/chat")      # /api/chat/
app.include_router(rag.router,      prefix="/api/rag")       # /api/rag/query
app.include_router(text2sql.router, prefix="/api/text2sql")  # /api/text2sql/generate
app.include_router(analyze.router,  prefix="/api")           # /api/analyze
app.include_router(git_rag.router,  prefix="/api/git")       # /api/git/index
# ... 19 routers total
```

**What this means:** Each router is a Python file that defines API endpoints. When a request comes in to `/api/text2sql/generate`, FastAPI routes it to the `text2sql.router`.

### Step 2: Settings are loaded from `.env`

```python
# app/config.py — Reads environment variables

class Settings:
    MODE        = os.getenv("MODE", "local")           # "local" or "airgap"
    LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    LLM_MODEL    = os.getenv("LLM_MODEL", "gpt-4o-mini")
    DB_TYPE      = os.getenv("DB_TYPE", "oracle")
    DB_HOST      = os.getenv("DB_HOST", "localhost")
    DB_PORT      = int(os.getenv("DB_PORT", "1521"))
    # ...

settings = Settings()
```

**What this means:** All configuration comes from `.env` file. To switch from OpenAI to a local model, you only change `LLM_API_BASE` — zero code changes.

### Step 3: The health check endpoint

```python
# app/main.py

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": settings.MODE,       # "local" or "airgap"
        "model": settings.LLM_MODEL  # "gpt-4o-mini" or "openai/gpt-oss-120b"
    }
```

**Test it:** `curl http://localhost:8080/health`
**Response:** `{"status":"ok","mode":"local","model":"gpt-4o-mini"}`

---

## 2. How Authentication Works

### Step 1: User submits login form

The frontend sends a POST request:

```
POST /api/auth/login
Body: {"username": "admin", "password": "changeme123!"}
```

### Step 2: Backend verifies password

```python
# app/routers/auth.py

@router.post("/login")
async def login(req: LoginRequest):
    # Check username matches
    if req.username != settings.ADMIN_USERNAME:
        raise HTTPException(401, "Invalid credentials")

    # Verify password with bcrypt
    if not verify_password(req.password, hashed_admin_password):
        raise HTTPException(401, "Invalid credentials")

    # Create JWT token (expires in 24 hours)
    token = create_access_token({"sub": req.username})

    return {"access_token": token, "token_type": "bearer", "username": req.username}
```

### Step 3: How bcrypt password verification works

```python
# app/core/auth.py

import bcrypt

def verify_password(plain: str, hashed: str) -> bool:
    # bcrypt.checkpw compares plain text against the hashed version
    # It extracts the salt from the hash and re-hashes the plain text
    # If they match, the password is correct
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def hash_password(password: str) -> str:
    # Generate a random salt and hash the password
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

**Why bcrypt?** It's intentionally slow (takes ~100ms per hash), making brute-force attacks impractical. Even if the database is stolen, passwords can't be reversed.

### Step 4: How JWT tokens work

```python
# app/core/auth.py

from jose import jwt

SECRET_KEY = "your-secret-key"

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=24)

    # jwt.encode creates a signed token
    # The token contains: {"sub": "admin", "exp": 1234567890}
    # It's signed with SECRET_KEY so it can't be tampered with
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

**Result token:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc3...`

This token is stored in the browser's localStorage and sent with every subsequent request as `Authorization: Bearer <token>`.

### Step 5: Frontend stores and sends token

```typescript
// platform/src/lib/api.ts

const api = axios.create({ baseURL: "/api" });

// Interceptor: automatically attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
```

**What this means:** After login, every API call automatically includes the JWT token. The user never has to log in again until the token expires (24 hours).

---

## 3. How Text-to-SQL Works

This is the core feature. A user types a natural language question, and the system queries an Oracle database.

### Real Example

```
User types: "What's the defect rate on Line A this month?"

System returns: "Line A (SMT) has a defect rate of 2.47% this month,
                 with 207 defects out of 8,381 units produced."
```

Here's exactly how each step works:

### Step 1: Schema Registration (one-time setup)

Before the system can generate SQL, it needs to know the database structure.

```python
# app/services/text2sql_service.py — discover_schema()

async def discover_schema(self, db_type, host, port, name, user, password, schema_id):
    # Build connection URL
    # For Oracle: oracle+oracledb://MESADMIN:mesadmin123@localhost:1521/?service_name=XEPDB1
    url = _build_db_url(db_type, host, port, name, user, password)

    engine = create_engine(url)
    inspector = inspect(engine)

    tables = []
    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],      # e.g., "ORDER_ID"
                "type": str(col["type"])   # e.g., "NUMBER"
            })
        tables.append({"name": table_name, "columns": columns})

    # Save to data/schemas.json
    schema = {"tables": tables, "description": f"Auto-discovered from {db_type}@{host}/{name}"}
    self._save_schema(schema_id, schema)

    return {"schema_id": schema_id, "tables": len(tables), "status": "discovered"}
```

**What happens internally:**
```sql
-- The system runs these queries against Oracle:
SELECT TABLE_NAME FROM USER_TABLES;
-- Returns: PRODUCTION_LINES, PRODUCTION_ORDERS, DEFECTS, EQUIPMENT, ...

SELECT COLUMN_NAME, DATA_TYPE FROM USER_TAB_COLUMNS WHERE TABLE_NAME = 'PRODUCTION_ORDERS';
-- Returns: ORDER_ID NUMBER, LINE_ID VARCHAR2, PLAN_QTY NUMBER, ACTUAL_QTY NUMBER, ...
```

**Result saved in `data/schemas.json`:**
```json
{
    "mes_oracle": {
        "tables": [
            {
                "name": "PRODUCTION_LINES",
                "columns": [
                    {"name": "LINE_ID", "type": "VARCHAR2(10)"},
                    {"name": "LINE_NAME", "type": "VARCHAR2(50)"},
                    {"name": "STATUS", "type": "VARCHAR2(20)"}
                ]
            },
            {
                "name": "DEFECTS",
                "columns": [
                    {"name": "DEFECT_ID", "type": "NUMBER"},
                    {"name": "ORDER_ID", "type": "NUMBER"},
                    {"name": "DEFECT_QTY", "type": "NUMBER"},
                    {"name": "SEVERITY", "type": "VARCHAR2(20)"}
                ]
            }
            // ... 11 tables total
        ]
    }
}
```

### Step 2: User asks a question

The frontend sends:
```
POST /api/text2sql/generate
Body: {"question": "show defect rate by line", "schema_id": "mes_oracle"}
```

### Step 3: Backend builds the LLM prompt

```python
# app/services/text2sql_service.py — generate()

async def generate(self, question: str, schema_id: str = None):
    # 1. Load the saved schema
    schema = self._load_schema(schema_id)  # From data/schemas.json

    # 2. Convert schema to text format
    schema_text = self._format_schema(schema)
    # Result:
    # CREATE TABLE MESADMIN.PRODUCTION_LINES (LINE_ID VARCHAR2(10), LINE_NAME VARCHAR2(50), ...);
    # CREATE TABLE MESADMIN.DEFECTS (DEFECT_ID NUMBER, ORDER_ID NUMBER, DEFECT_QTY NUMBER, ...);
    # ... (all 11 tables)

    # 3. Build messages for LLM
    messages = [
        {"role": "system", "content": SYSTEM_TEXT2SQL},  # "You are an Oracle SQL expert..."
        {"role": "user", "content": f"Schema:\n{schema_text}\n\nQuestion: {question}"}
    ]

    # 4. Call LLM (OpenAI API or local vLLM)
    response = chat_completion(messages=messages)

    # 5. Extract SQL from response
    content = response.choices[0].message.content
    sql_match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL)
    sql = sql_match.group(1) if sql_match else content

    return {"sql": sql, "explanation": explanation}
```

### Step 4: The system prompt that makes it work

```python
# app/core/prompts.py

SYSTEM_TEXT2SQL = """You are an expert Oracle SQL developer.
Given a database schema and a natural language question, generate ONLY a SQL query.

Rules:
- Use Oracle SQL syntax
- Only generate SELECT queries (never INSERT, UPDATE, DELETE, DROP)
- Always prefix table names with the schema owner (e.g., MESADMIN.TABLE_NAME)
- Return the SQL inside a ```sql code block
- Handle NULL values with NVL() or NULLIF()
- Use TRUNC(date, 'MM') for monthly aggregation
- Use ROUND() for decimal formatting

Foreign Key Relationships:
- PRODUCTION_ORDERS.LINE_ID → PRODUCTION_LINES.LINE_ID
- DEFECTS.ORDER_ID → PRODUCTION_ORDERS.ORDER_ID
- WORK_RESULTS.ORDER_ID → PRODUCTION_ORDERS.ORDER_ID
"""
```

**Why this prompt matters:** Without FK relationships, the LLM wouldn't know how to JOIN tables. Without the Oracle-specific rules, it might generate PostgreSQL or MySQL syntax.

### Step 5: LLM generates SQL

The LLM receives this complete message:
```
[System] You are an expert Oracle SQL developer...
         Schema: CREATE TABLE MESADMIN.PRODUCTION_LINES (...);
                 CREATE TABLE MESADMIN.DEFECTS (...);
                 ...

[User]   show defect rate by line
```

LLM responds:
```sql
SELECT
    pl.line_id,
    pl.line_name,
    SUM(d.defect_qty) AS total_defects,
    SUM(po.actual_qty) AS total_produced,
    ROUND(SUM(d.defect_qty) / NULLIF(SUM(po.actual_qty), 0) * 100, 2) AS defect_rate
FROM MESADMIN.PRODUCTION_LINES pl
LEFT JOIN MESADMIN.PRODUCTION_ORDERS po ON pl.line_id = po.line_id
LEFT JOIN MESADMIN.DEFECTS d ON po.order_id = d.order_id
GROUP BY pl.line_id, pl.line_name
ORDER BY defect_rate DESC
```

### Step 6: SQL Validation and Execution

```python
# app/services/text2sql_service.py — _run_query()

def _run_query(self, sql: str, db_type=None, host=None, ...):
    # Security check: only SELECT allowed
    stripped = sql.strip().upper()
    for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]:
        if stripped.startswith(kw):
            return {"error": f"Only SELECT queries allowed. Got: {kw}"}

    # Oracle quirk: remove trailing semicolons (ORA-00911 error)
    sql = sql.rstrip().rstrip(";")

    # Build connection and execute
    url = _build_db_url(db_type, host, port, name, user, password)
    engine = create_engine(url)

    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())          # ["line_name", "total_defects", "defect_rate"]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        # rows = [
        #     {"line_name": "A라인(SMT)", "total_defects": 2007, "defect_rate": 2.47},
        #     {"line_name": "B라인(DIP)", "total_defects": 1053, "defect_rate": 2.18},
        #     {"line_name": "E라인(포장)", "total_defects": 1154, "defect_rate": 1.19},
        # ]

    return {"sql": sql, "columns": columns, "rows": rows, "row_count": len(rows)}
```

### Step 7: How the LLM is actually called

```python
# app/llm_client.py — This is the bridge to any LLM

from openai import OpenAI

def _get_client():
    return OpenAI(
        base_url=settings.LLM_API_BASE,  # "https://api.openai.com/v1" or "http://gpu-server:8000/v1"
        api_key=settings.LLM_API_KEY,     # API key or "not-needed" for local
    )

def chat_completion(messages, model=None, temperature=0, max_tokens=2048):
    client = _get_client()
    return client.chat.completions.create(
        model=model or settings.LLM_MODEL,  # "gpt-4o-mini" or "openai/gpt-oss-120b"
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
```

**Key insight:** Because we use the OpenAI client library, ANY server that implements the OpenAI API format works. vLLM, Ollama, LiteLLM — they all expose `/v1/chat/completions`. We just change the URL.

---

## 4. How RAG Works

RAG = Retrieval-Augmented Generation. The LLM answers questions using your documents.

### Real Example

```
User uploads: "quality_standards.pdf"
User asks: "What's the acceptable defect rate for Line A?"

System:
1. Searches the PDF for relevant paragraphs
2. Finds: "SMT lines must maintain defect rate below 3.0%..."
3. Sends this context + question to LLM
4. LLM answers: "According to the quality standards document,
                  the acceptable defect rate for SMT lines (including Line A)
                  is below 3.0%."
```

### Step 1: Document Upload

```python
# app/routers/rag.py

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("default"),
):
    return await service.upload(file, collection)
```

### Step 2: Document Processing Pipeline

```python
# app/services/rag_service.py — upload()

async def upload(self, file: UploadFile, collection: str):
    # 1. Save file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # 2. Extract text based on file type
    #    PDF → pypdf extracts text from each page
    #    Word → python-docx reads paragraphs
    #    Excel → openpyxl reads cells
    #    Code → reads as plain text
    loader = DocumentLoader()
    chunks = loader.load_and_split(temp_path)

    # 3. Each chunk looks like this:
    # chunks = [
    #     {"content": "SMT lines must maintain defect rate below 3.0%...",
    #      "metadata": {"filename": "quality_standards.pdf", "page": 3}},
    #     {"content": "DIP lines follow a different standard...",
    #      "metadata": {"filename": "quality_standards.pdf", "page": 4}},
    # ]

    # 4. Store in vector database (ChromaDB + BM25)
    self._vector_store.add_documents(collection, chunks)

    return {"filename": file.filename, "chunks": len(chunks), "collection": collection}
```

### Step 3: How Documents Are Stored (Vector Embedding)

```python
# app/core/vector_store.py — add_documents()

def add_documents(self, collection: str, chunks: list[dict]):
    col = self._client.get_or_create_collection(
        name=collection,
        embedding_function=self.embedding_fn  # SentenceTransformer BGE-M3
    )

    # ChromaDB automatically:
    # 1. Takes each chunk's text
    # 2. Runs it through the embedding model
    # 3. Converts text to a 1024-dimensional vector
    #    "SMT lines must maintain..." → [0.12, -0.34, 0.56, 0.01, ..., -0.23]
    # 4. Stores the vector + original text + metadata

    col.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
    )

    # Also add to BM25 index for keyword search
    self._bm25_store.add(collection, chunks)
```

**What the embedding model does:**
```
Input:  "SMT lines must maintain defect rate below 3.0%"
Output: [0.12, -0.34, 0.56, 0.01, ..., -0.23]  (1024 numbers)

Input:  "What is the maximum defect rate for SMT?"
Output: [0.11, -0.32, 0.55, 0.02, ..., -0.22]  (1024 numbers)

These two vectors are SIMILAR because the texts are semantically similar.
Cosine similarity ≈ 0.95 (very close to 1.0)
```

### Step 4: User Asks a Question

```
POST /api/rag/query
Body: {"query": "what is acceptable defect rate", "collection": "default", "top_k": 5}
```

### Step 5: Hybrid Search (Dense + BM25 + Rerank)

```python
# app/core/vector_store.py — hybrid_search()

def hybrid_search(self, collection: str, query: str, top_k: int = 5):
    # === DENSE SEARCH (Semantic) ===
    # Convert query to vector, find similar vectors in ChromaDB
    col = self._client.get_collection(collection, embedding_function=self.embedding_fn)
    dense_results = col.query(query_texts=[query], n_results=top_k * 2)
    # Finds documents that are SEMANTICALLY similar
    # "acceptable defect rate" matches "must maintain defect rate below 3.0%"
    # even though the exact words are different

    # === BM25 SEARCH (Keyword) ===
    # Traditional keyword matching — exact word frequency scoring
    bm25_results = self._bm25_store.search(collection, query, top_k=top_k * 2)
    # Finds documents containing exact keywords: "defect", "rate", "acceptable"

    # === MERGE + RERANK ===
    # Combine results from both methods
    all_results = {}
    for doc in dense_results + bm25_results:
        doc_id = doc["id"]
        if doc_id not in all_results:
            all_results[doc_id] = doc
            all_results[doc_id]["rerank_score"] = 0
        # Boost score if found by BOTH methods
        all_results[doc_id]["rerank_score"] += doc.get("score", 0)

    # Sort by combined score and return top_k
    ranked = sorted(all_results.values(), key=lambda x: x["rerank_score"], reverse=True)
    return ranked[:top_k]
```

**Why hybrid?**
```
Query: "ORA-01017 error"

Dense search finds: "Authentication failure when connecting to database..."
  → Semantically similar ✓, but doesn't mention the exact error code

BM25 search finds: "ORA-01017: invalid username/password; logon denied"
  → Exact keyword match ✓

Combined: Both results are returned, giving better coverage
```

### Step 6: Generate Answer with Context

```python
# app/services/rag_service.py — query()

async def query(self, query: str, collection: str, top_k: int):
    # 1. Search for relevant document chunks
    results = self._vector_store.hybrid_search(collection, query, top_k)

    # 2. Build context from retrieved chunks
    context_parts = []
    for doc in results:
        context_parts.append(f"[{doc['filename']}]\n{doc['content']}")
    context = "\n\n---\n\n".join(context_parts)

    # 3. The actual prompt sent to LLM:
    messages = [
        {"role": "system", "content": "Answer the question based ONLY on the provided documents. "
                                       "If the answer is not in the documents, say so. "
                                       "Cite the source document name."},
        {"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {query}"}
    ]

    # 4. Call LLM
    response = chat_completion(messages=messages)
    answer = response.choices[0].message.content

    return {"answer": answer, "sources": sources}
```

**The actual prompt LLM receives:**
```
[System] Answer the question based ONLY on the provided documents...

[User] Documents:
       [quality_standards.pdf]
       SMT lines must maintain defect rate below 3.0%. Any line exceeding
       this threshold for 3 consecutive days must be shut down for inspection.

       ---

       [quality_standards.pdf]
       DIP lines have a different standard of 2.5% maximum defect rate...

       Question: what is acceptable defect rate
```

**LLM responds:** "According to quality_standards.pdf, the acceptable defect rate for SMT lines is below 3.0%, and for DIP lines it's below 2.5%. Lines exceeding these thresholds for 3 consecutive days must be shut down for inspection."

---

## 5. How Unified Analysis Works

The `/api/analyze` endpoint combines RAG + Text-to-SQL for comprehensive answers.

```python
# app/routers/analyze.py

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    # Run BOTH RAG search AND SQL query in parallel

    # 1. RAG: Search documents for related information
    rag_results = await rag_service.query(req.question, collection="all", top_k=3)

    # 2. Text-to-SQL: Generate and execute SQL
    sql_result = await text2sql_service.generate(req.question, schema_id=req.schema_id)
    if sql_result.get("sql"):
        db_result = text2sql_service._run_query(sql_result["sql"], ...)

    # 3. Combine everything and send to LLM for final answer
    messages = [
        {"role": "system", "content": "You are an analyst. Use both the documents and database results."},
        {"role": "user", "content": f"""
            Question: {req.question}

            Related Documents:
            {rag_context}

            Database Query Result:
            SQL: {sql_result['sql']}
            Data: {db_result['rows']}

            Provide a comprehensive analysis combining both sources.
        """}
    ]

    answer = chat_completion(messages).choices[0].message.content

    return {
        "answer": answer,
        "rag_sources": rag_results["sources"],
        "db_sql": sql_result["sql"],
        "db_rows": db_result["rows"],
    }
```

**Real example:**
```
User: "Why did defects increase on Line A?"

RAG finds: Quality standards document saying "SMT paste must be replaced every 4 hours"
SQL finds: Defect data showing spike from 1.2% to 4.8% starting February 15

LLM combines: "Line A's defect rate spiked from 1.2% to 4.8% on February 15th.
               According to the quality standards, SMT paste must be replaced every 4 hours.
               The timing correlates with a reported paste replacement delay.
               Recommendation: Audit the paste replacement schedule for Line A."
```

---

## 6. How the Frontend Connects to Backend

### The API Client

```typescript
// platform/src/lib/api.ts

import axios from "axios";

// Create axios instance with base URL
const api = axios.create({ baseURL: "/api" });

// Automatically attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// API functions organized by feature
export const sqlApi = {
    generate: (question: string, schemaId?: string) =>
        api.post("/text2sql/generate", { question, schema_id: schemaId }),

    execute: (sql: string, confirmed: boolean = false) =>
        api.post("/text2sql/execute", { sql, confirmed }),

    testConnection: (params: DbConnection) =>
        api.post("/text2sql/connection/test", params),

    discoverSchema: (params: DiscoverRequest) =>
        api.post("/text2sql/schema/discover", params),
};

export const ragApi = {
    upload: (file: File, collection: string) => {
        const form = new FormData();
        form.append("file", file);
        form.append("collection", collection);
        return api.post("/rag/upload", form, {
            headers: { "Content-Type": "multipart/form-data" },
        });
    },

    query: (query: string, collection: string, topK: number = 5) =>
        api.post("/rag/query", { query, collection, top_k: topK }),
};
```

### How Vite Proxy Routes Requests

```typescript
// platform/vite.config.ts

export default defineConfig({
    server: {
        port: 3000,           // Frontend runs on port 3000
        proxy: {
            "/api": {
                target: "http://localhost:8080",  // Forward /api/* to backend
                changeOrigin: true,
            },
        },
    },
});
```

**What happens when user clicks "Query":**
```
1. Browser (localhost:3000) → POST /api/rag/query
2. Vite proxy intercepts "/api" prefix
3. Forwards to → http://localhost:8080/api/rag/query
4. FastAPI handles the request
5. Response flows back through proxy to browser
```

### How a Page Component Works (SqlPage example)

```typescript
// platform/src/pages/SqlPage.tsx (simplified)

export function SqlPage() {
    const [question, setQuestion] = useState("");
    const [result, setResult] = useState(null);

    const handleQuery = async () => {
        // 1. Call Text-to-SQL API
        const genRes = await sqlApi.generate(question, "mes_oracle");
        const sql = genRes.data.sql;

        // 2. Execute the generated SQL
        const execRes = await sqlApi.execute(sql, true);
        setResult(execRes.data);

        // 3. result.rows is now displayed in a table
        // result = {
        //     columns: ["line_name", "defect_rate"],
        //     rows: [
        //         {"line_name": "A라인", "defect_rate": 2.47},
        //         {"line_name": "B라인", "defect_rate": 2.18},
        //     ]
        // }
    };

    return (
        <div>
            <input value={question} onChange={e => setQuestion(e.target.value)} />
            <button onClick={handleQuery}>Query</button>

            {result && (
                <table>
                    <thead>
                        <tr>{result.columns.map(col => <th>{col}</th>)}</tr>
                    </thead>
                    <tbody>
                        {result.rows.map(row => (
                            <tr>{result.columns.map(col => <td>{row[col]}</td>)}</tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}
```

---

## 7. How Air-gapped Mode Works

### The Switch

```bash
# .env (Online mode — uses OpenAI)
MODE=local
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-proj-...
LLM_MODEL=gpt-4o-mini

# .env.airgap (Offline mode — uses local GPU server)
MODE=airgap
LLM_API_BASE=http://10.0.1.50:8000/v1
LLM_API_KEY=not-needed
LLM_MODEL=openai/gpt-oss-120b
```

### Why This Works

```python
# app/llm_client.py

def _get_client():
    return OpenAI(
        base_url=settings.LLM_API_BASE,  # This is the ONLY thing that changes
        api_key=settings.LLM_API_KEY,
    )
```

Both OpenAI and vLLM expose the same API format:
```
POST /v1/chat/completions
Body: {"model": "...", "messages": [...]}
Response: {"choices": [{"message": {"content": "..."}}]}
```

So the code is identical. Only the URL changes.

### What's in the Air-gapped Package

```
EnterpriseLLM_VDI_Full.zip (260MB)
│
├── app/                    → Backend source code
├── platform/src/           → Frontend source code
├── offline_packages/       → 132 Python packages (.whl files)
│   ├── fastapi-0.115.0-py3-none-any.whl
│   ├── torch-2.10.0-cp312-cp312-win_amd64.whl  (109MB)
│   ├── chromadb-1.5.5-cp39-abi3-win_amd64.whl
│   ├── ... (132 total)
│
├── requirements_full.txt   → Complete dependency list
├── .env.airgap             → Pre-configured for airgap
└── install.bat             → One-click installer
```

### Installation on Air-gapped Machine

```bash
# 1. Install Python packages (no internet needed)
pip install --no-index --find-links=offline_packages -r requirements_full.txt

# 2. Copy embedding model (separate transfer — 500MB)
# models/embedding/ → Contains SentenceTransformer BGE-M3

# 3. Configure
copy .env.airgap .env
# Edit .env: set LLM_API_BASE to GPU server address

# 4. Run
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
cd platform && npm run dev
```

---

## 8. How the AI Coding Agent Works

`scripts/ai_code.py` is a lightweight version of Claude Code.

### The Core Loop

```python
# This is the entire architecture of ANY AI coding agent

while True:
    user_input = input(">>> ")                    # 1. Get user instruction
    conversation.append(user_msg(user_input))

    while True:                                    # 2. Agent loop
        response = call_llm(conversation)          # 3. Ask LLM what to do
        tool = parse_tool(response)                # 4. Did LLM request a tool?

        if tool is None:                           #    No tool → just text response
            print(response)
            break

        if tool.name == "DONE":                    #    Done → exit loop
            break

        result = execute_tool(tool)                # 5. Execute the tool
        conversation.append(tool_result(result))   # 6. Send result back to LLM
        # Go back to step 3                        # 7. LLM decides next action
```

### Available Tools

```python
# READ_FILE — Read any file with line numbers
def read_file(path):
    with open(path) as f:
        lines = f.readlines()
        return [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]

# WRITE_FILE — Create or overwrite a file
def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)

# EDIT_FILE — Replace specific text in a file
def edit_file(path, old, new):
    content = open(path).read()
    content = content.replace(old, new, 1)  # Replace first occurrence only
    open(path, "w").write(content)

# RUN_CMD — Execute a shell command
def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr
```

### Safety Features

```python
# 1. Dangerous commands are blocked
dangerous = ["rm -rf", "del /s", "format", "drop table"]
for d in dangerous:
    if d in cmd.lower():
        return "[BLOCKED: dangerous command]"

# 2. File writes require user confirmation
if tool_name == "WRITE_FILE":
    confirm = input(f"Write to {path}? (y/n): ")
    if confirm != "y":
        return "[User rejected]"

# 3. Command execution requires user confirmation
if tool_name == "RUN_CMD":
    confirm = input(f"Run: {cmd}? (y/n): ")
    if confirm != "y":
        return "[User rejected]"
```

### Example Session

```
>>> Fix the vite proxy error — /api requests return 404

[Step 1] LLM responds:
[TOOL: READ_FILE]
path: platform/vite.config.ts
[/TOOL]

[Tool: READ_FILE] → platform/vite.config.ts (25 lines read)

[Step 2] LLM responds:
"The proxy configuration looks correct. Let me check if the file exists
in the right location."

[TOOL: RUN_CMD]
cmd: dir platform\vite.config.ts
[/TOOL]

Run: dir platform\vite.config.ts? (y/n): y
[Tool: RUN_CMD] → File exists, 1,234 bytes

[Step 3] LLM responds:
"The file exists. The issue might be that vite isn't reading it.
Let me restart the dev server."

[TOOL: RUN_CMD]
cmd: cd platform && npx vite --host
[/TOOL]

Run: cd platform && npx vite --host? (y/n): y

[TOOL: DONE]
summary: Vite dev server restarted with proxy configuration.
         /api requests should now proxy to localhost:8080.
[/TOOL]

Done: Vite dev server restarted with proxy configuration.
```

---

## 9. How Git Source Indexing Works

```python
# app/connectors/git_connector.py

class GitConnector:
    def read_files(self, repo_path: str) -> list[dict]:
        """Walk through a git repository and read all source files."""
        files = []

        for root, dirs, filenames in os.walk(repo_path):
            # Skip hidden directories and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']

            for fname in filenames:
                # Only index code files
                if not fname.endswith(('.py', '.ts', '.tsx', '.js', '.java', '.sql', '.md')):
                    continue

                filepath = os.path.join(root, fname)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                files.append({
                    "content": content,
                    "metadata": {
                        "filename": fname,
                        "filepath": filepath,
                        "language": fname.split('.')[-1],
                    }
                })

        return files
```

After reading all files, they're chunked and stored in ChromaDB — the same pipeline as document upload. Then users can ask questions like:

```
"Where is authentication handled in the codebase?"
→ Searches git-indexed chunks
→ Finds app/core/auth.py and app/routers/auth.py
→ LLM explains: "Authentication is handled in two files..."
```

---

## 10. How Confluence Integration Works

### Fetching Pages via REST API

```python
# app/connectors/confluence.py

class ConfluenceConnector:
    def __init__(self, base_url, username, api_token):
        self.base_url = base_url  # "https://company.atlassian.net/wiki"
        self.auth = (username, api_token)

    def get_space_pages(self, space_key: str) -> list[dict]:
        """Fetch all pages from a Confluence space."""
        url = f"{self.base_url}/rest/api/content"
        params = {
            "spaceKey": space_key,
            "expand": "body.storage",  # Get HTML body
            "limit": 50,
        }

        response = requests.get(url, params=params, auth=self.auth)
        pages = []

        for page in response.json()["results"]:
            html = page["body"]["storage"]["value"]
            text = self._html_to_text(html)  # Strip HTML tags

            pages.append({
                "title": page["title"],
                "text": text,
                "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
            })

        return pages

    def _html_to_text(self, html: str) -> str:
        """Convert Confluence HTML to plain text."""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)
```

### The Sync Flow

```
1. User enters Confluence URL + credentials in UI
2. Backend calls Confluence REST API
3. Gets HTML content of each page
4. BeautifulSoup strips HTML → plain text
5. Text is chunked and embedded into ChromaDB
6. Now searchable via RAG query
```

---

## Summary: The Complete Request Flow

```
User types question in browser
         │
         ▼
React (localhost:3000) sends POST /api/...
         │
         ▼ (Vite proxy)
FastAPI (localhost:8080) receives request
         │
         ▼
JWT token verified → user authenticated
         │
         ▼
Router dispatches to Service
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
 ChromaDB              Oracle DB
 (vector search)       (SQL execution)
    │                     │
    └────┬────────────────┘
         │
         ▼
LLM API (OpenAI or vLLM)
    receives: schema + context + question
    returns: SQL or natural language answer
         │
         ▼
FastAPI sends JSON response
         │
         ▼ (Vite proxy)
React renders result in browser
```

**Every feature follows this same pattern.** The only differences are:
- Which data source is queried (ChromaDB, Oracle, Git, Confluence)
- What prompt template is used
- How the response is formatted
