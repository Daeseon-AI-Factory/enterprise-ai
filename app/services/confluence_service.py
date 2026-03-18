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
