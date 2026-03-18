"""
BM25 keyword index store — persists per collection alongside ChromaDB.

Why BM25 alongside dense vectors?
  Dense (embedding) search → good at semantic/paraphrase matching
  BM25 keyword search      → good at exact term / proper noun / code matching
  Hybrid (RRF)             → best of both worlds
"""
import os
import re
import pickle

from loguru import logger

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed — BM25 search disabled. Run: pip install rank-bm25")


class BM25Store:
    def __init__(self, persist_dir: str = "./chroma_data/bm25"):
        self._dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._cache: dict[str, dict] = {}

    def available(self) -> bool:
        return BM25_AVAILABLE

    # ── Tokenizer ────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize for BM25. Works for Korean + English:
        - Lowercase
        - Split on whitespace and punctuation
        - Keep Korean syllables (가-힣) and alphanumerics
        - Add character n-grams for Korean compound nouns
        """
        text = text.lower()
        # Extract words (Korean + English + numbers)
        words = re.findall(r'[가-힣]+|[a-z0-9]+', text)

        # Add bigrams for Korean (improves compound noun matching)
        bigrams = []
        for w in words:
            if re.fullmatch(r'[가-힣]+', w) and len(w) >= 2:
                bigrams.extend(w[i:i+2] for i in range(len(w) - 1))

        tokens = words + bigrams
        return tokens if tokens else [""]

    # ── Persistence ──────────────────────────────────────────

    def _path(self, collection: str) -> str:
        # Sanitize collection name for filesystem
        safe = re.sub(r'[^\w\-]', '_', collection)
        return os.path.join(self._dir, f"{safe}.pkl")

    def _load(self, collection: str) -> dict | None:
        if collection in self._cache:
            return self._cache[collection]
        path = self._path(collection)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                self._cache[collection] = data
                return data
            except Exception as e:
                logger.warning(f"BM25 load failed for '{collection}': {e}")
        return None

    def _save(self, collection: str, data: dict):
        self._cache[collection] = data
        try:
            with open(self._path(collection), "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.warning(f"BM25 save failed for '{collection}': {e}")

    # ── Public API ───────────────────────────────────────────

    def add_documents(
        self,
        collection: str,
        docs: list[str],
        ids: list[str],
        metadatas: list[dict],
    ) -> None:
        if not BM25_AVAILABLE:
            return

        existing = self._load(collection)
        if existing:
            all_docs = existing["docs"] + docs
            all_ids = existing["ids"] + ids
            all_meta = existing["metadatas"] + metadatas
        else:
            all_docs, all_ids, all_meta = docs, ids, metadatas

        tokenized = [self._tokenize(d) for d in all_docs]
        bm25 = BM25Okapi(tokenized)

        self._save(collection, {
            "bm25": bm25,
            "docs": all_docs,
            "ids": all_ids,
            "metadatas": all_meta,
        })
        logger.debug(f"BM25 index updated: '{collection}' now has {len(all_docs)} docs")

    def search(self, collection: str, query: str, top_k: int = 10) -> list[dict]:
        if not BM25_AVAILABLE:
            return []

        data = self._load(collection)
        if not data:
            return []

        tokens = self._tokenize(query)
        scores = data["bm25"].get_scores(tokens)

        # Get top_k by score (only positive scores)
        indexed = [(i, float(s)) for i, s in enumerate(scores) if s > 0]
        indexed.sort(key=lambda x: x[1], reverse=True)
        top = indexed[:top_k]

        results = []
        for rank, (idx, score) in enumerate(top):
            meta = data["metadatas"][idx]
            results.append({
                "id": data["ids"][idx],
                "content": data["docs"][idx],
                "score": score,
                "bm25_rank": rank,
                "filename": meta.get("filename", "unknown"),
                "doc_id": meta.get("doc_id", ""),
                "chunk_index": meta.get("chunk_index", 0),
            })
        return results

    def delete_collection(self, collection: str) -> None:
        self._cache.pop(collection, None)
        path = self._path(collection)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"BM25 index deleted: '{collection}'")

    def list_collections(self) -> list[str]:
        return [
            f[:-4] for f in os.listdir(self._dir)
            if f.endswith(".pkl")
        ]
