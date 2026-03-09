#!/usr/bin/env python3
"""
verify_installation.py
Checks that all components are properly installed and accessible.
Run after offline installation to validate the setup.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator to register a check function."""
    def decorator(fn):
        try:
            fn()
            CHECKS.append((name, True, "OK"))
        except Exception as e:
            CHECKS.append((name, False, str(e)))
        return fn
    return decorator


# === Python Import Checks ===

@check("FastAPI")
def _():
    import fastapi  # noqa: F401

@check("Uvicorn")
def _():
    import uvicorn  # noqa: F401

@check("Pydantic Settings")
def _():
    import pydantic_settings  # noqa: F401

@check("LangChain")
def _():
    import langchain  # noqa: F401

@check("ChromaDB")
def _():
    import chromadb  # noqa: F401

@check("OpenAI Client")
def _():
    import openai  # noqa: F401

@check("Sentence Transformers")
def _():
    import sentence_transformers  # noqa: F401

@check("PyPDF")
def _():
    import pypdf  # noqa: F401

@check("python-docx")
def _():
    import docx  # noqa: F401

@check("openpyxl")
def _():
    import openpyxl  # noqa: F401

@check("BeautifulSoup4")
def _():
    import bs4  # noqa: F401

@check("SQLAlchemy")
def _():
    import sqlalchemy  # noqa: F401

@check("Loguru")
def _():
    import loguru  # noqa: F401

@check("HTTPX")
def _():
    import httpx  # noqa: F401


# === Config Check ===

@check("App Config loads")
def _():
    from app.config import settings
    assert settings.MODE in ("local", "airgap"), f"Invalid MODE: {settings.MODE}"


# === Embedding Model Check ===

@check("Embedding model directory exists")
def _():
    from app.config import settings
    model_path = settings.EMBEDDING_MODEL_PATH
    if not os.path.isdir(model_path):
        raise FileNotFoundError(
            f"Embedding model not found at {model_path}. "
            "Download it or set EMBEDDING_MODEL_PATH in .env"
        )


# === Data Directories Check ===

@check("Data directories writable")
def _():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for subdir in ["data/conversations", "data/builds", "data/settings", "data/confluence", "uploads"]:
        path = os.path.join(base, subdir)
        os.makedirs(path, exist_ok=True)
        assert os.path.isdir(path), f"Cannot create {path}"


# === App Module Import Check ===

@check("Backend modules import")
def _():
    from app.main import app  # noqa: F401
    from app.services.review_service import ReviewService  # noqa: F401
    from app.services.build_service import BuildService  # noqa: F401
    from app.services.settings_service import SettingsService  # noqa: F401
    from app.connectors.confluence import ConfluenceConnector  # noqa: F401


# === LLM Endpoint Check ===

@check("LLM endpoint reachable")
def _():
    import httpx
    from app.config import settings
    # Try health/models endpoint
    try:
        r = httpx.get(f"{settings.LLM_API_BASE}/models", timeout=5.0,
                      headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"})
        assert r.status_code in (200, 401, 403), f"Unexpected status: {r.status_code}"
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to LLM at {settings.LLM_API_BASE}")


# === ChromaDB Check ===

@check("ChromaDB reachable")
def _():
    import httpx
    from app.config import settings
    try:
        r = httpx.get(f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v1/heartbeat", timeout=5.0)
        assert r.status_code == 200
    except httpx.ConnectError:
        raise ConnectionError(
            f"Cannot connect to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}. "
            "Start it with: docker compose up -d chromadb"
        )


# === Print Results ===

def main():
    print("=" * 60)
    print("Enterprise LLM — Installation Verification")
    print("=" * 60)
    print()

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = sum(1 for _, ok, _ in CHECKS if not ok)

    for name, ok, msg in CHECKS:
        status = "✓" if ok else "✗"
        if ok:
            print(f"  {status} {name}")
        else:
            print(f"  {status} {name}: {msg}")

    print()
    print(f"Results: {passed} passed, {failed} failed, {len(CHECKS)} total")
    print()

    if failed > 0:
        print("Some checks failed. Review the errors above.")
        print("Import failures → install missing packages")
        print("Connection failures → start required services")
        sys.exit(1)
    else:
        print("All checks passed! System is ready.")
        sys.exit(0)


if __name__ == "__main__":
    main()
