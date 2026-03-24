import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.config import settings

# === Logging Setup ===
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Remove default stderr handler, re-add with format
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {name}:{function}:{line} | {message}")
logger.add(
    LOG_DIR / "server_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {name}:{function}:{line} | {message}",
    encoding="utf-8",
)
from app.routers import (
    auth, analyze, git_rag, multi_agent,
    chat, rag, text2sql, codegen, confluence, review, build,
    settings as settings_router,
    agent, function_chat, finetune, webhook, scheduler, ocr, stt, vision,
)

app = FastAPI(
    title="Enterprise LLM Platform",
    description="Closed-network AI platform for enterprise",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Auth ===
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# === Unified Analysis (RAG + DB) ===
app.include_router(analyze.router, prefix="/api", tags=["Analyze"])

# === Git Source RAG ===
app.include_router(git_rag.router, prefix="/api/git", tags=["Git RAG"])

# === Level 1-5: Core Features ===
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(text2sql.router, prefix="/api/text2sql", tags=["Text2SQL"])
app.include_router(codegen.router, prefix="/api/codegen", tags=["Codegen"])
app.include_router(confluence.router, prefix="/api/confluence", tags=["Confluence"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(build.router, prefix="/api/build", tags=["Build"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])

# === Multi-Agent Orchestration ===
app.include_router(multi_agent.router, prefix="/api", tags=["Multi-Agent"])

# === Level 6: AI Agent ===
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])

# === Level 7: Function Calling (Smart Chat) ===
app.include_router(function_chat.router, prefix="/api/chat/smart", tags=["Smart Chat"])

# === Level 8: Fine-tuning Pipeline ===
app.include_router(finetune.router, prefix="/api/finetune", tags=["Fine-tuning"])

# === Level 9: Workflow Automation ===
app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])

# === Level 10: Multi-Modal ===
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])
app.include_router(stt.router, prefix="/api/stt", tags=["Speech-to-Text"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"])


@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mode": settings.MODE,
        "model": settings.LLM_MODEL,
    }


@app.get("/api/stats")
async def stats():
    """Dashboard stats — aggregates data from all services."""
    from app.core.vector_store import get_vector_store

    collections = []
    try:
        vs = get_vector_store()
        collections = vs.list_collections()
    except Exception:
        pass

    conversations = 0
    try:
        from app.routers.chat import service as chat_svc
        convs = await chat_svc.list_conversations()
        conversations = len(convs)
    except Exception:
        pass

    schemas = 0
    try:
        from app.routers.text2sql import service as sql_svc
        schema_list = await sql_svc.list_schemas()
        schemas = len(schema_list)
    except Exception:
        pass

    return {
        "status": "ok",
        "mode": settings.MODE,
        "model": settings.LLM_MODEL,
        "collections": collections,
        "conversations": conversations,
        "schemas": schemas,
    }


@app.on_event("startup")
async def startup():
    logger.info(f"Starting Enterprise LLM Platform in {settings.MODE} mode")
    logger.info(f"LLM endpoint: {settings.LLM_API_BASE}")
    logger.info(f"Model: {settings.LLM_MODEL}")

    # Start scheduler with default handlers
    from app.services.webhook_service import WebhookService
    from app.services.confluence_service import ConfluenceService

    _webhook = WebhookService()
    _confluence_svc = ConfluenceService()

    scheduler.service.register_handler("confluence_sync", _webhook.handle_confluence_sync)
    scheduler.service.register_handler("rag_query", _webhook.handle_rag_query)

    # Confluence auto-sync: reads saved settings and syncs all configured spaces
    async def _auto_confluence_sync(**kwargs):
        from app.routers.settings import service as settings_svc
        try:
            conf = await settings_svc.get("confluence")
            cfg = conf.get("data") if conf else None
            if not cfg:
                logger.info("Confluence auto-sync: no config saved, skipping")
                return
            base_url = cfg.get("base_url", "")
            username = cfg.get("username", "")
            api_token = cfg.get("api_token", "")
            spaces = cfg.get("spaces", [])
            if not base_url or not spaces:
                logger.info("Confluence auto-sync: missing URL or spaces, skipping")
                return
            for space_key in spaces:
                result = await _confluence_svc.sync_space(
                    base_url=base_url, username=username, api_token=api_token,
                    space_key=space_key, full_sync=False,
                )
                logger.info(f"Confluence auto-sync [{space_key}]: {result}")
        except Exception as e:
            logger.error(f"Confluence auto-sync error: {e}")

    scheduler.service.register_handler("confluence_auto_sync", _auto_confluence_sync)
    await scheduler.service.start()
    logger.info("Scheduler started")

    # 임베딩 모델 워밍업 — 백그라운드에서 비동기 로드
    import asyncio
    async def _warmup():
        try:
            from app.core.vector_store import get_vector_store
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                def _load():
                    vs = get_vector_store()
                    _ = vs.embedding_fn
                await loop.run_in_executor(pool, _load)
            logger.info("Embedding model warmed up")
        except Exception as e:
            logger.warning(f"Embedding warmup failed (non-critical): {e}")
    asyncio.create_task(_warmup())


# === Serve frontend static files (production mode) ===
DIST_DIR = Path(__file__).resolve().parent.parent / "platform" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))

    logger.info(f"Serving frontend from {DIST_DIR}")


@app.on_event("shutdown")
async def shutdown():
    await scheduler.service.stop()
    logger.info("Scheduler stopped")
