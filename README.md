# Enterprise LLM Platform

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Oracle](https://img.shields.io/badge/Oracle-DB-F80000?logo=oracle&logoColor=white)](https://www.oracle.com/database/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Air-gapped enterprise AI platform that connects internal databases, documents, and source code to LLMs — enabling natural language queries, RAG-based search, and unified analytics without exposing data to external services.**

[🇰🇷 한국어 README](docs/README_ko.md)

---

## Why I Built This

Manufacturing companies in Korea operate in air-gapped networks where ChatGPT and cloud AI services are blocked. Factory floor engineers need data insights but can't write SQL. Internal documents are scattered across Confluence, shared drives, and Git repos. I built this platform to solve these real problems from my 5 years of MES/WMS experience.

---

## Demo

> **Try it:** Clone → `pip install` → `start.bat` → Ask "What is the defect rate for Line A this month?" and watch it generate SQL, query Oracle, and respond in natural language.

| Query | Result |
|-------|--------|
| "A라인 이번달 불량률 알려줘" | Generates SQL → queries Oracle → "A라인(SMT) defect rate: 2.47%" |
| "납땜불량 급증 원인 분석해줘" | Multi-agent: Quality Analyst queries DB + Doc Searcher finds SOP → combined report |
| "현재 재고가 가장 많은 품목 5개" | Text-to-SQL → Inventory table → top 5 items with quantities |

[Screenshots placeholder - 6 images in 2x3 grid]

---

## Key Features

| # | Feature | Description |
|---|---------|-------------|
| 🗣️ | **Text-to-SQL** | Ask questions in plain English/Korean, get real-time database results from Oracle/PostgreSQL |
| 📚 | **RAG Document Search** | Upload PDFs, Word, Excel or sync Confluence — AI answers with source citations |
| 🔗 | **Git Code RAG** | Index Git repositories and ask questions about your codebase |
| 🔍 | **Unified Analysis** | Combines DB data + document search for comprehensive insights |
| 🏭 | **MES/WMS Integration** | Production lines, defect rates, inventory — query manufacturing data naturally |
| 🔒 | **Air-gapped Deployment** | Runs fully offline with local LLM (vLLM) and local embeddings |
| 🤖 | **ReAct Agent** | Autonomous tool-calling agent that chains multiple capabilities |
| 🎙️ | **Multi-Modal** | OCR, Speech-to-Text, and Vision analysis endpoints |
| 🔄 | **Confluence Sync** | Auto-sync wiki pages into the vector store for instant RAG |
| 🌐 | **Bilingual UI** | Full Korean/English interface toggle |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Browser (User)                      │
│                 http://localhost:3000                  │
└─────────────────────────┬────────────────────────────┘
                          │
             ┌────────────▼─────────────┐
             │    React Frontend         │
             │    TypeScript + Tailwind  │
             │    Vite (port 3000)       │
             └────────────┬─────────────┘
                          │  /api/* proxy
             ┌────────────▼─────────────┐
             │    FastAPI Backend        │
             │    19 Routers             │
             │    16 Services            │
             │    JWT Authentication     │
             │    Uvicorn (port 8080)    │
             └──┬─────────┬──────────┬──┘
                │         │          │
    ┌───────────▼──┐  ┌───▼───┐  ┌──▼──────────────┐
    │  ChromaDB    │  │Oracle │  │ LLM Server       │
    │  Vector DB   │  │  DB   │  │ OpenAI API       │
    │  + BM25      │  │       │  │ or vLLM (airgap) │
    └──────────────┘  └───────┘  └──────────────────┘
```

---

## Technical Decisions

| Decision | Why | Alternative Considered |
|----------|-----|----------------------|
| ChromaDB over Pinecone | Air-gapped: no external API calls. Embedded mode = no separate server | Pinecone (cloud-only), Milvus (complex setup) |
| BGE-M3 embedding | Multilingual (KR+EN), supports Dense+Sparse+ColBERT in one model | OpenAI embeddings (cloud-only), e5-large (English-only) |
| FastAPI over Django | Async-native, lightweight, auto OpenAPI docs | Django (heavy ORM not needed), Flask (no async) |
| Multi-agent over single RAG | Scoped search per agent → higher accuracy than searching all docs | Single RAG pipeline (noisy with 1000+ docs) |
| SQLAlchemy + raw oracledb | Thin mode (no Oracle Client install), works in air-gapped | cx_Oracle (requires Oracle Client binary) |
| Pre-built frontend (dist/) | Users only need Python, no Node.js install | Vite dev server (requires Node.js on every PC) |

---

## Performance

| Metric | Value |
|--------|-------|
| Chat response (pure LLM) | ~2 seconds |
| Text-to-SQL generation | ~1.8 seconds |
| SQL execution (Oracle) | ~0.08 seconds |
| RAG search (hybrid) | ~0.5 seconds |
| Multi-agent orchestration (2 agents) | ~22 seconds |
| Embedding model load (cold start) | ~10 seconds |
| Frontend build size | ~650KB gzipped |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19, TypeScript, Tailwind CSS | Single-page application |
| **Build** | Vite 6 | Dev server + production bundling |
| **Backend** | Python 3.12, FastAPI | Async REST API |
| **Auth** | JWT (python-jose) + bcrypt | Token-based authentication |
| **Vector DB** | ChromaDB (persistent) | Document embedding storage |
| **Embedding** | SentenceTransformers (BGE-M3) | Text to 1024-dim vectors |
| **Search** | Dense + BM25 + Reranker | Hybrid retrieval pipeline |
| **Database** | Oracle / PostgreSQL | Text-to-SQL target |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **LLM** | OpenAI API / vLLM | Language model inference |
| **Monitoring** | Prometheus | Metrics collection |
| **Deployment** | Docker Compose / Bare metal | Infrastructure |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Oracle DB (optional, for Text-to-SQL)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/JasonAIFactory/Product006_ClosedEnterpriseLLM.git
cd Product006_ClosedEnterpriseLLM

# Backend setup
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd platform
npm install
```

### Environment Setup

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Required: LLM_API_KEY (your OpenAI API key)
# Optional: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD (for Text-to-SQL)
```

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODE` | `local` | `local` (OpenAI) or `airgap` (self-hosted LLM) |
| `LLM_API_BASE` | `https://api.openai.com/v1` | LLM API endpoint |
| `LLM_API_KEY` | — | API key for the LLM provider |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `DB_TYPE` | `oracle` | Database type for Text-to-SQL |
| `CHROMA_PORT` | `0` | `0` = in-process mode (no Docker needed) |

### Run

```bash
# Terminal 1 — Backend (port 8080)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2 — Frontend (port 3000)
cd platform
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Air-gapped Deployment

For environments with no internet access (manufacturing, finance, government):

1. **Prepare** on an online machine:
   - Python wheels: `pip download -r requirements_full.txt -d offline_packages/`
   - Frontend build: `cd platform && npm run build`
   - Embedding model: download BGE-M3 into `models/embedding/`

2. **Transfer** to the air-gapped machine via USB or shared folder

3. **Install** offline:
   ```bash
   pip install --no-index --find-links=offline_packages -r requirements_full.txt
   cp .env.airgap .env
   # Edit LLM_API_BASE to point to your internal vLLM server
   ```

4. **Start** the vLLM server on a GPU node:
   ```bash
   docker compose -f docker-compose.vllm.yml up -d
   ```

See [`docs/project-structure.md`](docs/project-structure.md) for the full air-gapped deployment diagram.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | JWT authentication |
| `GET` | `/api/auth/me` | Current user info |
| `POST` | `/api/chat/` | Chat with LLM |
| `POST` | `/api/chat/stream` | Streaming chat response |
| `POST` | `/api/chat/smart` | Function-calling chat |
| `POST` | `/api/rag/upload` | Upload documents for RAG |
| `POST` | `/api/rag/query` | Query documents with RAG |
| `POST` | `/api/text2sql/generate` | Natural language to SQL |
| `POST` | `/api/analyze` | Unified analysis (RAG + SQL) |
| `POST` | `/api/git/index` | Index a Git repository |
| `POST` | `/api/confluence/sync` | Sync Confluence pages |
| `POST` | `/api/agent/run` | Run ReAct agent |
| `POST` | `/api/codegen/generate` | AI code generation |
| `POST` | `/api/review/code` | AI code review |
| `POST` | `/api/ocr/extract` | OCR text extraction |
| `POST` | `/api/stt/transcribe` | Speech-to-text |
| `POST` | `/api/vision/analyze` | Vision analysis |
| `GET` | `/health` | Health check |

---

## Project Structure

```
Product006_ClosedEnterpriseLLM/
├── app/                          # Backend (Python/FastAPI)
│   ├── main.py                   #   Entry point
│   ├── config.py                 #   Settings from .env
│   ├── llm_client.py             #   OpenAI-compatible wrapper
│   ├── core/                     #   Core modules
│   │   ├── auth.py               #     JWT + bcrypt auth
│   │   ├── prompts.py            #     System prompts
│   │   ├── vector_store.py       #     ChromaDB + BM25 hybrid
│   │   ├── document_loader.py    #     PDF/Word/Excel parser
│   │   └── agent_executor.py     #     ReAct agent loop
│   ├── connectors/               #   External integrations
│   │   ├── confluence.py         #     Confluence REST client
│   │   └── git_connector.py      #     Git repo reader
│   ├── routers/                  #   API endpoints (19 routers)
│   └── services/                 #   Business logic (16 services)
│
├── platform/                     # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── pages/                #   12 pages
│   │   ├── components/           #   Reusable UI components
│   │   └── lib/                  #   API client + utilities
│   ├── vite.config.ts
│   └── package.json
│
├── models/embedding/             # SentenceTransformer model (~500MB)
├── scripts/                      # AI coding agent, model downloader
├── data/                         # Runtime data (schemas, conversations)
├── chroma_data/                  # ChromaDB persistence
├── docker-compose.yml            # Main compose file
├── docker-compose.vllm.yml       # GPU LLM server
├── requirements.txt              # Python dependencies
└── .env.example                  # Configuration template
```

---

## Screenshots

| Dashboard | Text-to-SQL | RAG Document Search |
|-----------|-------------|---------------------|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Text-to-SQL](docs/screenshots/text2sql.png) | ![RAG](docs/screenshots/rag.png) |

| Unified Analysis | Git Code RAG | Settings |
|------------------|--------------|----------|
| ![Analysis](docs/screenshots/analyze.png) | ![Git RAG](docs/screenshots/git-rag.png) | ![Settings](docs/screenshots/settings.png) |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All Python code includes type hints
- New endpoints have corresponding service layer
- Environment variables are documented in `.env.example`

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built by <a href="https://github.com/JasonAIFactory">Jason (Daeseon Yoo)</a> — Backend Developer & AI Platform Engineer
</p>
