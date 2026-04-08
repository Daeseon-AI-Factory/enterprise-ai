# Enterprise LLM Platform

[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen?style=for-the-badge)](https://enterprise-llm.onrender.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Full-stack AI platform for air-gapped enterprise environments.** Ask questions in natural language, get answers from your databases (Text-to-SQL), documents (RAG), and source code — without any data leaving your network.

Built from 5 years of manufacturing (MES/WMS) experience where cloud AI is blocked and engineers need data insights but can't write SQL.

---

## What It Does (30-second version)

```
"What is the defect rate for Line A this month?"
        │
        ▼
   ┌─────────┐    ┌──────────┐    ┌───────────┐
   │ Text-to- │    │   RAG    │    │  ReAct    │
   │   SQL    │    │  Search  │    │  Agent    │
   │          │    │          │    │           │
   │ NL → SQL │    │ Query    │    │ Chains    │
   │ → Oracle │    │ Expand   │    │ tools     │
   │ → Answer │    │ → Hybrid │    │ auto-     │
   │          │    │ → Rerank │    │ matically │
   └─────────┘    └──────────┘    └───────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
              Unified Answer with Sources
```

| Input | What Happens | Output |
|-------|-------------|--------|
| "A라인 이번달 불량률" | Generates SQL, queries Oracle | "Line A (SMT) defect rate: 2.47%" |
| "납땜불량 원인 분석" | Multi-agent: DB query + SOP search | Combined analysis report |
| "재고 TOP 5" | Text-to-SQL on inventory table | Table with item codes + quantities |
| Upload PDF + ask question | Semantic chunk, embed, hybrid search | Answer with page citations |

---

## RAG Pipeline

Not a tutorial wrapper around LangChain. This is a **6-stage retrieval pipeline** built on information retrieval research:

```
Query ──► Query Expansion (LLM generates 3 synonym variations)
             │
             ▼
          Hybrid Search (Dense embeddings + BM25 keywords)
             │
             ▼
          RRF Merge (Reciprocal Rank Fusion, k=60)
             │
             ▼
          Bi-Encoder Rerank (cosine similarity re-scoring)
             │
             ▼
          Confidence Filter (drop chunks below threshold)
             │
             ▼
          Deduplicate + LLM Answer with citations
```

**Key design choices and why:**

| What | Why | Alternative I rejected |
|------|-----|----------------------|
| **Semantic chunking** (embedding similarity breakpoints) | Fixed-size splits cut mid-sentence and mix topics | RecursiveCharacterSplitter (no topic awareness) |
| **Adaptive threshold** (percentile-based, not fixed) | Technical manuals have high baseline similarity; fixed threshold = false positives | Hardcoded cosine cutoff |
| **Query expansion** (LLM-generated synonyms) | "불량률" should also find "defect rate", "quality", "yield" | Single-query search (low recall) |
| **RRF** over linear combination | No score calibration needed between dense and BM25 | Weighted sum (requires per-dataset tuning) |
| **AST-based SQL validation** (sqlparse) | Regex is bypassed by `-- comment\nDELETE`. AST checks actual statement type | `startswith("DELETE")` (trivially exploitable) |

---

## Architecture

```
Browser ─── React 19 + TypeScript + Tailwind (port 3000)
                │
                │  /api/*
                ▼
         FastAPI Backend (port 8080)
         ├── 19 API routers
         ├── 16 service modules
         ├── JWT authentication
         └── OpenAI-compatible LLM client
                │
      ┌─────────┼──────────┐
      ▼         ▼          ▼
  ChromaDB    Oracle    LLM Server
  + BM25      / Pg     (OpenAI API │ vLLM │ Ollama)
  + Reranker
```

**Swap LLM backends with one env var** — same codebase runs on OpenAI, Azure OpenAI, vLLM (GPU), or Ollama (local CPU). No code changes.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | **FastAPI** + Python 3.12 | Async-native, auto OpenAPI docs |
| Frontend | **React 19** + TypeScript + Tailwind | Type-safe SPA, 12 pages |
| Vector DB | **ChromaDB** (embedded) | Runs offline, no separate server |
| Embeddings | **BGE-M3** (SentenceTransformers) | Multilingual KR+EN in one model |
| Search | **Dense + BM25 + RRF + Reranker** | Research-grade hybrid retrieval |
| SQL Safety | **sqlparse** AST validation | Blocks injection at parse level |
| Database | **Oracle / PostgreSQL / SQLite** | SQLAlchemy, swappable |
| Auth | **JWT + bcrypt** | Stateless, standard |
| Agent | **ReAct** (Thought-Action-Observation) | Text-parsed, works with any LLM |
| Deploy | **Docker Compose** / bare metal | Air-gapped or cloud |

---

## Quick Start

```bash
git clone https://github.com/JasonAIFactory/Enterprise-LLM-Platform.git
cd Enterprise-LLM-Platform

python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # Edit: add your LLM_API_KEY

python -m uvicorn app.main:app --port 8080
# Open http://localhost:8080
```

For frontend development: `cd platform && npm install && npm run dev` (port 3000).

### Air-gapped deployment

```bash
# On internet machine: download everything
pip download -r requirements.txt -d offline_packages/
# Transfer via USB, then:
pip install --no-index --find-links=offline_packages -r requirements.txt
cp .env.airgap .env
```

See [Air-gapped Install Guide](docs/OFFLINE_INSTALL_GUIDE.md) for full instructions.

---

## API Overview

19 REST endpoints. Full docs at `/docs` (auto-generated Swagger).

| Endpoint | Description |
|----------|-------------|
| `POST /api/chat` | Chat with LLM (streaming available) |
| `POST /api/rag/upload` | Upload + index documents |
| `POST /api/rag/query` | RAG search with query expansion |
| `POST /api/text2sql/generate` | Natural language to SQL |
| `POST /api/text2sql/execute` | Execute validated SELECT query |
| `POST /api/analyze` | Unified RAG + DB analysis |
| `POST /api/agent/run` | ReAct agent with tool chaining |
| `POST /api/review/code` | AI code review |
| `POST /api/git/index` | Index Git repository for RAG |
| `POST /api/confluence/sync` | Sync Confluence wiki pages |

---

## Project Structure

```
app/
├── main.py                    # FastAPI entry point
├── config.py                  # Pydantic settings from .env
├── llm_client.py              # OpenAI-compatible LLM wrapper
├── core/
│   ├── vector_store.py        # ChromaDB + BM25 + RRF hybrid search
│   ├── document_loader.py     # Semantic chunking (embedding-based)
│   ├── bm25_store.py          # BM25 with Korean bigram tokenizer
│   └── agent_executor.py      # ReAct agent loop with streaming
├── services/                  # 16 business logic modules
└── routers/                   # 19 API endpoint routers

platform/                      # React 19 + TypeScript frontend
├── src/pages/                 # 12 pages (Chat, RAG, SQL, Agent, ...)
└── src/components/            # Reusable UI components
```

---

## About

Built by **Jason (Daeseon Yoo)** — Backend engineer with 5 years at SK, building MES and WMS systems that handle millions of production records. This platform solves real problems I saw on factory floors: engineers who need data insights but can't use SQL, documents scattered across systems, and strict air-gapped networks that block all cloud AI.

- [Portfolio](docs/PORTFOLIO.md) | [Architecture Deep Dive](docs/architecture-deep-dive.md) | [Interview Script](docs/interview-script.md)

---

<p align="center">MIT License</p>
