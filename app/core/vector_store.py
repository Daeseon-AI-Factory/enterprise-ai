"""
VectorStore — ChromaDB (dense) + BM25 (keyword) hybrid retrieval.

Retrieval pipeline:
  1. Dense search  (semantic similarity via bge-m3 embeddings)
  2. BM25 search   (keyword matching)
  3. RRF merge     (Reciprocal Rank Fusion — unifies scores from both)
  4. Reranker      (re-score merged candidates with bi-encoder)
"""
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

from app.config import settings
from app.core.bm25_store import BM25Store


class VectorStore:
    def __init__(self):
        self._client: chromadb.ClientAPI | None = None
        self._embedding_fn: SentenceTransformerEmbeddingFunction | None = None
        self._bm25 = BM25Store(persist_dir="./chroma_data/bm25")
        self._st_model = None  # raw SentenceTransformer for reranking

    # ── Lazy init ────────────────────────────────────────────

    @property
    def embedding_fn(self) -> SentenceTransformerEmbeddingFunction:
        if self._embedding_fn is None:
            model_path = settings.EMBEDDING_MODEL_PATH
            logger.info(f"Loading embedding model from {model_path}...")
            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=model_path,
            )
            logger.info("Embedding model loaded")
        return self._embedding_fn

    @property
    def st_model(self):
        """Raw SentenceTransformer model for reranking."""
        if self._st_model is None:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH)
        return self._st_model

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            if settings.CHROMA_HOST == "localhost" and settings.CHROMA_PORT == 0:
                self._client = chromadb.PersistentClient(path="./chroma_data")
                logger.info("Using local persistent ChromaDB at ./chroma_data")
            else:
                self._client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                )
                logger.info(f"Connected to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        return self._client

    def _get_collection(self, name: str, create: bool = False):
        if create:
            return self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_fn,
            )
        return self.client.get_collection(
            name=name,
            embedding_function=self.embedding_fn,
        )

    # ── Write ────────────────────────────────────────────────

    def add_documents(
        self,
        collection: str,
        documents: list[str],
        doc_id: str,
        filename: str,
    ) -> None:
        col = self._get_collection(collection, create=True)
        ids = [f"{doc_id}_{i}" for i in range(len(documents))]
        metadatas = [
            {"filename": filename, "chunk_index": i, "doc_id": doc_id}
            for i in range(len(documents))
        ]

        # Batch insert into ChromaDB
        batch_size = 5000
        for start in range(0, len(documents), batch_size):
            end = min(start + batch_size, len(documents))
            col.add(
                documents=documents[start:end],
                ids=ids[start:end],
                metadatas=metadatas[start:end],
            )

        # Also index into BM25
        self._bm25.add_documents(
            collection=collection,
            docs=documents,
            ids=ids,
            metadatas=metadatas,
        )

        logger.info(f"Indexed {len(documents)} chunks → '{collection}' (dense + BM25)")

    # ── Dense search ─────────────────────────────────────────

    def search(self, collection: str, query: str, top_k: int = 5) -> list[dict]:
        """Pure dense (embedding) search."""
        try:
            col = self._get_collection(collection)
        except Exception:
            logger.warning(f"Collection '{collection}' not found")
            return []

        n = min(top_k, col.count())
        if n == 0:
            return []

        results = col.query(query_texts=[query], n_results=n)
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "filename": results["metadatas"][0][i].get("filename", "unknown"),
                "doc_id": results["metadatas"][0][i].get("doc_id", ""),
                "score": results["distances"][0][i] if results.get("distances") else 0,
            })
        return docs

    # ── Hybrid search (Dense + BM25 + RRF + Reranker) ───────

    def hybrid_search(self, collection: str, query: str, top_k: int = 5) -> list[dict]:
        """
        Hybrid retrieval pipeline:
          dense(top_k*3) + BM25(top_k*3) → RRF merge → rerank → top_k
        """
        candidates = top_k * 3

        dense_hits = self.search(collection, query, top_k=candidates)
        bm25_hits = self._bm25.search(collection, query, top_k=candidates)

        if not dense_hits and not bm25_hits:
            return []

        # If BM25 unavailable, fall back to dense only
        if not bm25_hits:
            logger.debug(f"BM25 unavailable for '{collection}', using dense only")
            return dense_hits[:top_k]

        merged = self._rrf(dense_hits, bm25_hits, top_k=candidates)

        # Rerank: re-score merged candidates with bi-encoder
        reranked = self._rerank(query, merged, top_k=top_k)

        logger.debug(
            f"Hybrid '{collection}': dense={len(dense_hits)} "
            f"bm25={len(bm25_hits)} → rrf={len(merged)} → rerank={len(reranked)}"
        )
        return reranked

    # ── Reciprocal Rank Fusion ───────────────────────────────

    @staticmethod
    def _rrf(
        dense_hits: list[dict],
        bm25_hits: list[dict],
        top_k: int,
        k: int = 60,
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion.
        RRF score = Σ 1/(k + rank)  across retrievers.
        k=60 is the standard constant from the original paper.
        """
        scores: dict[str, float] = {}
        docs_by_id: dict[str, dict] = {}

        for rank, doc in enumerate(dense_hits):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            docs_by_id[doc_id] = doc

        for rank, doc in enumerate(bm25_hits):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            if doc_id not in docs_by_id:
                docs_by_id[doc_id] = doc

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {**docs_by_id[doc_id], "rrf_score": rrf_score, "score": rrf_score}
            for doc_id, rrf_score in ranked
            if doc_id in docs_by_id
        ]

    # ── Bi-encoder Reranker ──────────────────────────────────

    def _rerank(self, query: str, docs: list[dict], top_k: int) -> list[dict]:
        """
        Rerank RRF results using the bi-encoder model.

        How it works:
          - Encode the query and each candidate chunk with bge-m3
          - Compute cosine similarity (query, chunk)
          - Sort by similarity → precise relevance ordering

        Why this helps after RRF:
          RRF only knows *rank position* from each retriever.
          The reranker computes an actual *relevance score* for each
          query–chunk pair, catching cases where RRF merged results
          that aren't actually relevant.
        """
        if not docs:
            return []

        try:
            import torch
            from sentence_transformers import util

            model = self.st_model
            query_emb = model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
            doc_texts = [d["content"] for d in docs]
            doc_embs = model.encode(doc_texts, convert_to_tensor=True, normalize_embeddings=True)

            cos_scores = util.cos_sim(query_emb, doc_embs)[0]

            scored = sorted(
                zip(cos_scores.tolist(), docs),
                key=lambda x: x[0],
                reverse=True,
            )
            result = []
            for score, doc in scored[:top_k]:
                doc = dict(doc)
                doc["rerank_score"] = round(score, 4)
                doc["score"] = round(score, 4)
                result.append(doc)

            logger.debug(f"Reranker top score: {result[0]['score']:.4f} | bottom: {result[-1]['score']:.4f}")
            return result

        except Exception as e:
            logger.warning(f"Reranker failed ({e}), using RRF order")
            return docs[:top_k]

    # ── Metadata queries ─────────────────────────────────────

    def list_collections(self) -> list[dict]:
        # No embedding_fn needed — metadata only, avoids model cold-start
        collections = self.client.list_collections()
        result = []
        for name in collections:
            try:
                col_name = name if isinstance(name, str) else name.name
                col = self.client.get_collection(name=col_name)
                result.append({"name": col.name, "count": col.count()})
            except Exception:
                result.append({"name": str(name), "count": 0})
        return result

    def list_documents(self, collection: str) -> list[dict]:
        """Return unique documents (filename + chunk count) — no embedding model needed."""
        try:
            col = self.client.get_collection(name=collection)  # no embedding_fn
        except Exception:
            return []
        result = col.get(include=["metadatas"])
        file_counts: dict[str, dict] = {}
        for meta in result.get("metadatas") or []:
            fname = meta.get("filename", "unknown")
            doc_id = meta.get("doc_id", "")
            if fname not in file_counts:
                file_counts[fname] = {"filename": fname, "doc_id": doc_id, "chunks": 0}
            file_counts[fname]["chunks"] += 1
        return list(file_counts.values())

    def delete_collection(self, collection_id: str) -> None:
        self.client.delete_collection(name=collection_id)
        self._bm25.delete_collection(collection_id)
