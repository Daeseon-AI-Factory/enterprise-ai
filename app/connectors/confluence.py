"""Confluence connector — fetches pages from Confluence REST API and indexes them into Vector DB."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from loguru import logger


# Persisted sync state so we only re-index pages that changed.
_SYNC_STATE_DIR = "./data/confluence"


class ConfluenceConnector:
    """Pull pages from Confluence Cloud/Server and return plain-text chunks."""

    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, api_token)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch_space_pages(
        self,
        space_key: str,
        limit: int = 50,
        *,
        labels: list[str] | None = None,
    ) -> list[dict]:
        """Return list of page dicts with title, id, body text, url, modified date."""
        pages: list[dict] = []
        start = 0

        while True:
            params: dict = {
                "spaceKey": space_key,
                "expand": "body.storage,version,metadata.labels",
                "limit": limit,
                "start": start,
            }
            resp = httpx.get(
                f"{self.base_url}/rest/api/content",
                params=params,
                auth=self.auth,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            for page in results:
                # Optional label filter
                if labels:
                    page_labels = [
                        lb["name"]
                        for lb in page.get("metadata", {}).get("labels", {}).get("results", [])
                    ]
                    if not any(lb in labels for lb in page_labels):
                        continue

                html = page["body"]["storage"]["value"]
                text = self._html_to_text(html)
                if not text.strip():
                    continue

                pages.append({
                    "id": page["id"],
                    "title": page["title"],
                    "text": text,
                    "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
                    "modified": page["version"]["when"],
                    "version": page["version"]["number"],
                })

            # Pagination
            if data.get("_links", {}).get("next"):
                start += limit
            else:
                break

        logger.info(f"Fetched {len(pages)} pages from Confluence space '{space_key}'")
        return pages

    def fetch_single_page(self, page_id: str) -> dict | None:
        """Fetch a single page by ID."""
        resp = httpx.get(
            f"{self.base_url}/rest/api/content/{page_id}",
            params={"expand": "body.storage,version"},
            auth=self.auth,
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        page = resp.json()
        html = page["body"]["storage"]["value"]
        return {
            "id": page["id"],
            "title": page["title"],
            "text": self._html_to_text(html),
            "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
            "modified": page["version"]["when"],
            "version": page["version"]["number"],
        }

    # ------------------------------------------------------------------
    # Change detection
    # ------------------------------------------------------------------

    def get_changed_pages(self, space_key: str, pages: list[dict]) -> list[dict]:
        """Filter pages to only those whose content changed since last sync."""
        state = self._load_sync_state(space_key)
        changed = []
        for page in pages:
            content_hash = hashlib.md5(page["text"].encode()).hexdigest()
            if state.get(page["id"]) != content_hash:
                changed.append(page)
                state[page["id"]] = content_hash
        self._save_sync_state(space_key, state)
        logger.info(f"Change detection: {len(changed)}/{len(pages)} pages changed")
        return changed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _html_to_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        # Remove script/style
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _load_sync_state(space_key: str) -> dict:
        os.makedirs(_SYNC_STATE_DIR, exist_ok=True)
        path = os.path.join(_SYNC_STATE_DIR, f"{space_key}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    @staticmethod
    def _save_sync_state(space_key: str, state: dict) -> None:
        os.makedirs(_SYNC_STATE_DIR, exist_ok=True)
        path = os.path.join(_SYNC_STATE_DIR, f"{space_key}.json")
        with open(path, "w") as f:
            json.dump(state, f)
