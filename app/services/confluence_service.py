"""Service that orchestrates Confluence → Vector DB sync pipeline."""

from __future__ import annotations

import uuid

from loguru import logger

from app.connectors.confluence import ConfluenceConnector
from app.core.document_loader import DocumentLoader
from app.core.vector_store import get_vector_store


class ConfluenceService:
    def __init__(self):
        self._vector_store = get_vector_store()
        self._doc_loader = DocumentLoader()

    async def sync_space(
        self,
        base_url: str,
        username: str,
        api_token: str,
        space_key: str,
        collection: str | None = None,
        labels: list[str] | None = None,
        full_sync: bool = False,
    ) -> dict:
        """Fetch pages from a Confluence space and index into vector DB.

        Args:
            base_url: Confluence base URL (e.g. https://company.atlassian.net/wiki)
            username: Confluence username (email for Cloud)
            api_token: API token or password
            space_key: Confluence space key (e.g. "DEV", "HR")
            collection: Vector DB collection name (defaults to confluence_{space_key})
            labels: Optional list of labels to filter pages
            full_sync: If True, re-index all pages. If False, only changed pages.
        """
        connector = ConfluenceConnector(base_url, username, api_token)
        collection = collection or f"confluence_{space_key.lower()}"

        # 1. Fetch all pages from space
        pages = connector.fetch_space_pages(space_key, labels=labels)

        if not pages:
            return {
                "status": "no_pages",
                "space_key": space_key,
                "collection": collection,
                "synced": 0,
                "total": 0,
            }

        # 2. Filter to only changed pages (unless full sync)
        if not full_sync:
            pages = connector.get_changed_pages(space_key, pages)

        if not pages:
            return {
                "status": "up_to_date",
                "space_key": space_key,
                "collection": collection,
                "synced": 0,
                "total": 0,
            }

        # 3. Chunk and index each page
        total_chunks = 0
        for page in pages:
            # Semantic chunking (same pipeline as uploaded files)
            chunks = self._doc_loader._semantic_chunk(page["text"])
            if not chunks:
                continue

            doc_id = f"confluence_{page['id']}"
            ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "filename": page["title"],
                    "chunk_index": i,
                    "doc_id": doc_id,
                    "source": "confluence",
                    "page_id": page["id"],
                    "page_url": page["url"],
                    "space_key": space_key,
                }
                for i in range(len(chunks))
            ]

            col = self._vector_store._get_collection(collection, create=True)

            # Upsert — remove old chunks for this page, then add new
            try:
                existing = col.get(where={"doc_id": doc_id})
                if existing["ids"]:
                    col.delete(ids=existing["ids"])
            except Exception:
                pass  # Collection might be empty or filter unsupported

            col.add(documents=chunks, ids=ids, metadatas=metadatas)
            total_chunks += len(chunks)

        # Rebuild BM25 from ChromaDB to ensure hybrid search is in sync
        self._vector_store.rebuild_bm25(collection)

        logger.info(
            f"Confluence sync complete: {len(pages)} pages, {total_chunks} chunks → '{collection}'"
        )

        return {
            "status": "synced",
            "space_key": space_key,
            "collection": collection,
            "synced": len(pages),
            "total_chunks": total_chunks,
        }

    async def register_page_by_url(
        self,
        page_url: str,
        base_url: str,
        username: str,
        api_token: str,
        collection: str = "confluence_pages",
    ) -> dict:
        """Confluence 페이지 URL을 받아서 API로 콘텐츠를 가져와 RAG에 등록.

        URL 형식 예시:
          - https://company.atlassian.net/wiki/spaces/MES/pages/12345/페이지제목
          - https://company.atlassian.net/wiki/pages/viewpage.action?pageId=12345
        """
        import re

        # URL에서 page_id 추출
        page_id = None
        # 패턴 1: /pages/12345/...
        m = re.search(r"/pages/(\d+)", page_url)
        if m:
            page_id = m.group(1)
        # 패턴 2: ?pageId=12345
        if not page_id:
            m = re.search(r"pageId=(\d+)", page_url)
            if m:
                page_id = m.group(1)

        if not page_id:
            return {"status": "error", "message": "URL에서 page ID를 추출할 수 없습니다."}

        # API 호출로 페이지 콘텐츠 가져오기
        connector = ConfluenceConnector(base_url, username, api_token)
        page = connector.fetch_single_page(page_id)

        if not page:
            return {"status": "error", "message": f"페이지 {page_id}를 찾을 수 없습니다."}

        if not page["text"].strip():
            return {"status": "error", "message": "페이지 콘텐츠가 비어있습니다."}

        # Semantic chunking
        chunks = self._doc_loader._semantic_chunk(page["text"])
        if not chunks:
            return {"status": "error", "message": "청크 생성 실패."}

        doc_id = f"confluence_{page_id}"
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "filename": page["title"],
                "chunk_index": i,
                "doc_id": doc_id,
                "source": "confluence",
                "page_id": page_id,
                "page_url": page["url"],
            }
            for i in range(len(chunks))
        ]

        col = self._vector_store._get_collection(collection, create=True)

        # 기존 청크 제거 후 새로 추가 (upsert)
        try:
            existing = col.get(where={"doc_id": doc_id})
            if existing["ids"]:
                col.delete(ids=existing["ids"])
        except Exception:
            pass

        col.add(documents=chunks, ids=ids, metadatas=metadatas)
        self._vector_store.rebuild_bm25(collection)

        logger.info(f"Confluence page registered: '{page['title']}' ({len(chunks)} chunks) → '{collection}'")

        return {
            "status": "registered",
            "title": page["title"],
            "page_id": page_id,
            "page_url": page["url"],
            "collection": collection,
            "chunks": len(chunks),
        }

    async def list_spaces(
        self,
        base_url: str,
        username: str,
        api_token: str,
    ) -> list[dict]:
        """List available Confluence spaces."""
        import httpx

        from app.config import settings
        resp = httpx.get(
            f"{base_url.rstrip('/')}/rest/api/space",
            params={"limit": 100},
            auth=(username, api_token),
            timeout=30,
            verify=settings.CONFLUENCE_VERIFY_SSL,
        )
        resp.raise_for_status()
        spaces = resp.json().get("results", [])
        return [
            {"key": s["key"], "name": s["name"], "type": s.get("type", "")}
            for s in spaces
        ]
