# Enterprise LLM Platform — Project Structure

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User (Browser)                        │
│                     http://localhost:3000                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   React Frontend        │
              │   TypeScript + Tailwind │
              │   12 Pages              │
              │   Vite (port 3000)      │
              └────────────┬────────────┘
                           │ /api/* (Vite proxy)
              ┌────────────▼────────────┐
              │   FastAPI Backend       │
              │   19 Routers            │
              │   16 Services           │
              │   JWT Auth              │
              │   Uvicorn (port 8080)   │
              └──┬───────┬──────────┬───┘
                 │       │          │
     ┌───────────▼──┐ ┌──▼────┐ ┌──▼──────────────┐
     │  ChromaDB    │ │Oracle │ │ LLM Server       │
     │  (Vector DB) │ │  DB   │ │ OpenAI API       │
     │  Local file  │ │      │ │ or vLLM (airgap) │
     └──────────────┘ └───────┘ └──────────────────┘
```

## Directory Structure

```
Product006_ClosedEnterpriseLLM/
│
├── app/                          # Backend (Python/FastAPI)
│   ├── main.py                   #   Entry point, router registration
│   ├── config.py                 #   Settings from .env
│   ├── llm_client.py             #   OpenAI-compatible API wrapper
│   │
│   ├── core/                     #   Core modules
│   │   ├── auth.py               #     JWT + bcrypt authentication
│   │   ├── prompts.py            #     System prompts (RAG, SQL, Chat)
│   │   ├── vector_store.py       #     ChromaDB + BM25 hybrid search
│   │   ├── bm25_store.py         #     BM25 keyword index
│   │   ├── document_loader.py    #     PDF/Word/Excel/code parser
│   │   ├── conversation_store.py #     Chat history persistence
│   │   ├── tool_registry.py      #     Agent tool definitions
│   │   └── agent_executor.py     #     ReAct agent loop
│   │
│   ├── connectors/               #   External system connectors
│   │   ├── confluence.py         #     Confluence REST API client
│   │   └── git_connector.py      #     Git repo file reader
│   │
│   ├── routers/                  #   API endpoints (19 routers)
│   │   ├── auth.py               #     POST /api/auth/login, /me
│   │   ├── chat.py               #     POST /api/chat/, /stream
│   │   ├── rag.py                #     POST /api/rag/upload, /query
│   │   ├── text2sql.py           #     POST /api/text2sql/generate
│   │   ├── confluence.py         #     POST /api/confluence/sync
│   │   ├── git_rag.py            #     POST /api/git/index
│   │   ├── analyze.py            #     POST /api/analyze
│   │   ├── codegen.py            #     POST /api/codegen/generate
│   │   ├── review.py             #     POST /api/review/code
│   │   ├── build.py              #     POST /api/build/run
│   │   ├── settings.py           #     GET/PUT /api/settings
│   │   ├── agent.py              #     POST /api/agent/run
│   │   ├── function_chat.py      #     POST /api/chat/smart
│   │   ├── finetune.py           #     POST /api/finetune/generate-data
│   │   ├── webhook.py            #     POST /api/webhook/*
│   │   ├── scheduler.py          #     POST /api/scheduler/create
│   │   ├── ocr.py                #     POST /api/ocr/extract
│   │   ├── stt.py                #     POST /api/stt/transcribe
│   │   └── vision.py             #     POST /api/vision/analyze
│   │
│   └── services/                 #   Business logic (16 services)
│       ├── chat_service.py
│       ├── rag_service.py
│       ├── text2sql_service.py
│       ├── confluence_service.py
│       ├── codegen_service.py
│       ├── review_service.py
│       ├── build_service.py
│       ├── settings_service.py
│       ├── agent_service.py
│       ├── function_chat_service.py
│       ├── finetune_service.py
│       ├── webhook_service.py
│       ├── scheduler_service.py
│       ├── ocr_service.py
│       ├── stt_service.py
│       └── vision_service.py
│
├── platform/                     # Frontend (React/TypeScript)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts            #   Dev server + API proxy
│   ├── tailwind.config.ts        #   Tailwind CSS theme
│   ├── postcss.config.js
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── main.tsx              #   Entry point
│       ├── App.tsx               #   Routes + auth state
│       ├── globals.css           #   Tailwind base styles
│       │
│       ├── lib/
│       │   ├── api.ts            #     Axios client + JWT interceptor
│       │   └── utils.ts          #     Utility functions
│       │
│       ├── layouts/
│       │   └── MainLayout.tsx    #     Sidebar + content layout
│       │
│       ├── components/
│       │   ├── Sidebar.tsx       #     Navigation (KO/EN toggle)
│       │   ├── ChatInput.tsx
│       │   ├── ChatMessage.tsx
│       │   ├── CodeBlock.tsx
│       │   ├── FileUploader.tsx
│       │   ├── SqlResultTable.tsx
│       │   └── ui/              #     Radix UI wrappers
│       │
│       └── pages/
│           ├── LoginPage.tsx
│           ├── DashboardPage.tsx
│           ├── ChatPage.tsx
│           ├── RagPage.tsx
│           ├── SqlPage.tsx
│           ├── AnalyzePage.tsx
│           ├── GitPage.tsx
│           ├── CodegenPage.tsx
│           ├── ConfluencePage.tsx
│           ├── ReviewPage.tsx
│           ├── BuildPage.tsx
│           └── SettingsPage.tsx
│
├── models/
│   └── embedding/                # SentenceTransformer (BGE-M3, ~500MB)
│
├── scripts/
│   ├── ai_code.py                # AI coding agent (Claude Code lite)
│   ├── ai_fix.py                 # AI error fixer
│   ├── download_llm_model.ps1
│   └── download_llm_model.sh
│
├── docs/
│   ├── interview-script.md       # Interview Q&A (this file)
│   ├── project-structure.md      # Project structure (this file)
│   ├── architecture-overview.md
│   ├── data-flow-detail.md
│   └── integration-guide.md
│
├── data/                         # Runtime data
│   ├── schemas.json              #   Registered DB schemas
│   ├── conversations/            #   Chat history
│   ├── settings/                 #   Platform settings
│   └── confluence/               #   Cached Confluence data
│
├── chroma_data/                  # ChromaDB persistence
│   ├── chroma.sqlite3            #   Vector database
│   └── bm25/                     #   BM25 keyword index
│
├── .env                          # Environment config
├── .env.example                  # Config template
├── .env.airgap                   # Air-gapped config
├── requirements.txt              # Python dependencies
├── requirements_full.txt         # Complete dep list (132 packages)
├── install.bat                   # Windows installer
├── docker-compose.yml
├── docker-compose.vllm.yml       # GPU LLM server
├── docker-compose.vllm-cpu.yml   # CPU LLM server
└── CLAUDE.md                     # Project philosophy
```

## Data Flow — Text-to-SQL

```
User: "A라인 이번달 불량률 알려줘"
         │
         ▼
┌─ Backend ──────────────────────────────────────┐
│                                                 │
│  1. Load schema from data/schemas.json          │
│     → PRODUCTION_LINES (LINE_ID, LINE_NAME ...) │
│     → DEFECTS (DEFECT_ID, ORDER_ID ...)         │
│     → 11 tables total                           │
│                                                 │
│  2. Build prompt:                               │
│     System: "You are an Oracle SQL expert"       │
│     + Schema text                               │
│     + FK relationships                          │
│     User: "A라인 이번달 불량률 알려줘"            │
│                                                 │
│  3. Send to LLM → Receive SQL                   │
│     SELECT LINE_NAME,                           │
│       ROUND(SUM(DEFECT_QTY) /                   │
│         NULLIF(SUM(ACTUAL_QTY),0) * 100, 2)     │
│     FROM PRODUCTION_LINES ...                   │
│                                                 │
│  4. Validate: SELECT only ✓                     │
│     Strip semicolons ✓                          │
│                                                 │
│  5. Execute against Oracle → Get rows           │
│     [{"LINE_NAME":"A라인","RATE":2.47}]          │
│                                                 │
│  6. Send result back to LLM                     │
│     → "A라인 이번달 불량률은 2.47%입니다"         │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Data Flow — RAG Query

```
User: "납땜불량 처리 방법 알려줘"
         │
         ▼
┌─ Backend ──────────────────────────────────────┐
│                                                 │
│  1. Embed query with SentenceTransformer        │
│     → [0.12, -0.34, 0.56, ...]  (1024-dim)     │
│                                                 │
│  2. Dense search (ChromaDB)                     │
│     → Top 10 similar chunks                     │
│                                                 │
│  3. BM25 keyword search                        │
│     → Top 10 keyword-matched chunks             │
│                                                 │
│  4. Merge + Rerank                              │
│     → Combined top 5 chunks                     │
│                                                 │
│  5. Build prompt:                               │
│     System: "Answer based on these documents"    │
│     Context: [chunk1] [chunk2] [chunk3] ...     │
│     User: "납땜불량 처리 방법 알려줘"             │
│                                                 │
│  6. LLM generates answer with source citations  │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Data Flow — Unified Analysis

```
User: "A라인 불량 급증 원인 분석해줘"
         │
         ▼
┌─ Backend ─────────────────────────────┐
│                                        │
│  ┌──────────┐    ┌───────────────┐    │
│  │ RAG      │    │ Text-to-SQL   │    │
│  │ 문서검색  │    │ DB 조회       │    │
│  └────┬─────┘    └──────┬────────┘    │
│       │                 │             │
│       ▼                 ▼             │
│  관련 문서 3건      실제 수치 데이터    │
│  (공정 규정,       (불량률 2.47%,     │
│   품질 기준 등)     월별 추이 등)      │
│       │                 │             │
│       └────────┬────────┘             │
│                ▼                      │
│         LLM 종합 분석                  │
│  "A라인 불량률이 2월 이후 2.47%로     │
│   급증했으며, 공정 규정에 따르면..."    │
│                                        │
└────────────────────────────────────────┘
```

## Air-gapped Deployment

```
┌─── Online PC ───────────────────────┐
│                                      │
│  EnterpriseLLM_VDI_Full.zip (260MB)  │
│  ├── app/          (source code)     │
│  ├── platform/src/ (frontend)        │
│  ├── offline_packages/ (132 .whl)    │
│  ├── requirements_full.txt           │
│  └── .env.airgap                     │
│                                      │
│  + models/embedding/ (500MB, separate)│
│                                      │
└──────────────┬───────────────────────┘
               │ USB / Shared folder
               ▼
┌─── Air-gapped VDI ──────────────────┐
│                                      │
│  1. Unzip                            │
│  2. pip install --no-index           │
│     --find-links=offline_packages    │
│     -r requirements_full.txt         │
│  3. Copy .env.airgap → .env         │
│  4. Edit LLM_API_BASE               │
│  5. python -m uvicorn app.main:app   │
│  6. cd platform && npm run dev       │
│                                      │
│  localhost:8080 (API)                │
│  localhost:3000 (UI)                 │
│         │                            │
└─────────┼────────────────────────────┘
          │ Internal network
          ▼
┌─── GPU Server ──────────────────────┐
│                                      │
│  vLLM + OSS-120B (or any model)      │
│  :8000/v1/chat/completions           │
│                                      │
└──────────────────────────────────────┘
```

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19, TypeScript, Tailwind CSS | UI |
| Build | Vite 6 | Dev server + bundling |
| Backend | Python 3.12, FastAPI | REST API |
| Auth | JWT (python-jose) + bcrypt | Authentication |
| Vector DB | ChromaDB (persistent mode) | Document embeddings |
| Embedding | SentenceTransformer (BGE-M3) | Text → Vector |
| Search | Dense + BM25 + Reranker | Hybrid retrieval |
| Database | Oracle (oracledb thin driver) | Text-to-SQL target |
| ORM | SQLAlchemy 2.0 | DB abstraction |
| LLM | OpenAI API / vLLM | Language model |
| Deployment | Docker Compose / Bare metal | Infrastructure |
| CI/CD | Git + manual | Version control |
