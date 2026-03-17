import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# === Level 1-5: Core Features ===
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(text2sql.router, prefix="/api/text2sql", tags=["Text2SQL"])
app.include_router(codegen.router, prefix="/api/codegen", tags=["Codegen"])
app.include_router(confluence.router, prefix="/api/confluence", tags=["Confluence"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(build.router, prefix="/api/build", tags=["Build"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])

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
async def health():
    return {
        "status": "ok",
        "mode": settings.MODE,
        "model": settings.LLM_MODEL,
    }


@app.on_event("startup")
async def startup():
    logger.info(f"Starting Enterprise LLM Platform in {settings.MODE} mode")
    logger.info(f"LLM endpoint: {settings.LLM_API_BASE}")
    logger.info(f"Model: {settings.LLM_MODEL}")

    # Start scheduler with default handlers
    from app.services.webhook_service import WebhookService
    _webhook = WebhookService()
    scheduler.service.register_handler("confluence_sync", _webhook.handle_confluence_sync)
    scheduler.service.register_handler("rag_query", _webhook.handle_rag_query)
    await scheduler.service.start()
    logger.info("Scheduler started")


@app.on_event("shutdown")
async def shutdown():
    await scheduler.service.stop()
    logger.info("Scheduler stopped")
