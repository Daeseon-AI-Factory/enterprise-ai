from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.routers import chat, rag, text2sql, codegen, confluence, review, build, settings as settings_router

app = FastAPI(
    title="Enterprise LLM Platform",
    description="Closed-network AI platform for enterprise",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(text2sql.router, prefix="/api/text2sql", tags=["Text2SQL"])
app.include_router(codegen.router, prefix="/api/codegen", tags=["Codegen"])
app.include_router(confluence.router, prefix="/api/confluence", tags=["Confluence"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(build.router, prefix="/api/build", tags=["Build"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])


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
