import os
import uuid

from fastapi import UploadFile
from loguru import logger

from app.llm_client import chat_completion
from app.core.vector_store import get_vector_store
from app.core.document_loader import DocumentLoader
from app.core.prompts import SYSTEM_RAG


QUERY_EXPANSION_PROMPT = """Generate 3 alternative search queries for the given question.
Each query should use different keywords, synonyms, or rephrasings to improve document retrieval.
Include both Korean and English variations if applicable.

Return ONLY the queries, one per line. No numbering, no explanation.

Question: {query}"""


class RagService:
    def __init__(self):
        self._vector_store = get_vector_store()
        self._doc_loader = DocumentLoader()

    async def _expand_query(self, query: str) -> list[str]:
        """Generate alternative queries via LLM for better recall.

        Why: A single query misses relevant documents that use different terminology.
        e.g., "불량률" should also find "품질", "수율", "defect rate".

        Returns the original query + up to 3 expanded queries.
        """
        expanded = [query]  # always include original
        try:
            response = chat_completion(
                messages=[
                    {"role": "user", "content": QUERY_EXPANSION_PROMPT.format(query=query)},
                ],
                temperature=0.7,
                max_tokens=200,
            )
            lines = response.choices[0].message.content.strip().split("\n")
            for line in lines:
                line = line.strip().lstrip("0123456789.-) ")
                if line and line != query:
                    expanded.append(line)
            logger.info(f"[RAG] Query expansion: '{query[:50]}' → {len(expanded)} queries")
        except Exception as e:
            logger.warning(f"[RAG] Query expansion failed, using original only: {e}")
        return expanded[:4]  # cap at original + 3

    async def upload_and_index(
        self,
        file: UploadFile,
        collection: str = "default",
    ) -> dict:
        """Upload document, chunk it, embed, and store in vector DB."""
        import time
        t0 = time.time()
        file_size = f"{len(await file.read()) / 1024:.1f}KB"
        await file.seek(0)  # reset after reading size
        logger.info(f"[UPLOAD] 파일 수신: {file.filename} ({file_size}) → 컬렉션 '{collection}'")

        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"[UPLOAD] 파일 저장 완료: {file_path}")

        # Load and chunk document
        try:
            chunks = self._doc_loader.load_and_chunk(file_path, file.filename)
            avg_len = sum(len(c) for c in chunks) // max(len(chunks), 1)
            logger.info(f"[UPLOAD] 텍스트 추출 + 청킹 완료: {len(chunks)}개 청크 (평균 {avg_len}자)")
        except Exception as e:
            logger.error(f"[UPLOAD] 텍스트 추출 실패: {file.filename} → {e}")
            return {"status": "error", "error": str(e)}

        # Store in vector DB
        doc_id = str(uuid.uuid4())
        try:
            self._vector_store.add_documents(
                collection=collection,
                documents=chunks,
                doc_id=doc_id,
                filename=file.filename,
            )
            elapsed = time.time() - t0
            logger.info(f"[UPLOAD] 임베딩 + 저장 완료 → 컬렉션 '{collection}' | 총 {elapsed:.1f}초")
        except Exception as e:
            logger.error(f"[UPLOAD] 임베딩/저장 실패: {e}")
            return {"status": "error", "error": str(e)}

        return {
            "status": "indexed",
            "filename": file.filename,
            "chunks": len(chunks),
            "collection": collection,
            "doc_id": doc_id,
        }

    def _deduplicate_results(self, results: list[dict], top_k: int) -> list[dict]:
        """Remove duplicate chunks across multi-query results, keeping highest score."""
        seen: dict[str, dict] = {}
        for r in results:
            key = r.get("id", r.get("content", "")[:100])
            existing = seen.get(key)
            if existing is None or r.get("rerank_score", 0) > existing.get("rerank_score", 0):
                seen[key] = r
        deduped = sorted(seen.values(), key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
        return deduped[:top_k]

    async def query(
        self,
        query: str,
        collection: str = "all",
        top_k: int = 5,
    ) -> dict:
        """Query documents using RAG pipeline with query expansion.

        Pipeline:
          1. Expand query into multiple variations (LLM-based)
          2. Run hybrid search (dense + BM25 + RRF + rerank) for each variation
          3. Deduplicate and merge results
          4. Filter by confidence threshold
          5. Generate answer with LLM
        """
        import time
        t0 = time.time()
        logger.info(f"[RAG] 질의 시작: '{query[:80]}' (컬렉션: {collection}, top_k: {top_k})")

        if not self._vector_store.embedding_available:
            return {
                "answer": "임베딩 모델이 설치되지 않았습니다. models/embedding/ 폴더에 모델을 복사해주세요.",
                "sources": [],
            }

        # Step 1: Expand query for better recall
        queries = await self._expand_query(query)

        # Step 2: Search with all query variations
        all_results = []
        collections_to_search = (
            [col["name"] for col in self._vector_store.list_collections()]
            if collection in ("all", "", "*")
            else [collection]
        )

        for q in queries:
            for col_name in collections_to_search:
                try:
                    hits = self._vector_store.hybrid_search(
                        collection=col_name, query=q, top_k=top_k
                    )
                    for h in hits:
                        h["collection"] = col_name
                    all_results.extend(hits)
                except Exception as e:
                    logger.warning(f"Hybrid search failed in '{col_name}': {e}")

        # Step 3: Deduplicate across all query variations
        results = self._deduplicate_results(all_results, top_k)

        # Step 4: Confidence filter — drop low-quality chunks
        MIN_RERANK_SCORE = 0.3
        before_filter = len(results)
        results = [r for r in results if r.get("rerank_score", r.get("score", 0)) >= MIN_RERANK_SCORE]
        if before_filter > len(results):
            logger.info(f"[RAG] Confidence filter: {before_filter} → {len(results)} chunks (threshold={MIN_RERANK_SCORE})")

        logger.info(
            f"[RAG] 검색 완료: {len(queries)} queries × {len(collections_to_search)} collections "
            f"→ {len(results)} chunks from {list(set(r.get('collection','') for r in results))}"
        )

        # Build context from retrieved docs
        context_parts = []
        sources = []
        for doc in results:
            col_label = doc.get("collection", "")
            context_parts.append(f"[{col_label}/{doc.get('filename','?')}]\n{doc['content']}")
            source_entry = {
                "filename": doc.get("filename", "unknown"),
                "collection": col_label,
                "chunk_id": doc.get("id", ""),
                "score": doc.get("score", 0),
            }
            if doc.get("page_url"):
                source_entry["page_url"] = doc["page_url"]
            if doc.get("source"):
                source_entry["source"] = doc["source"]
            sources.append(source_entry)

        context = "\n\n---\n\n".join(context_parts)

        # Generate answer with LLM
        messages = [
            {"role": "system", "content": SYSTEM_RAG},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ]
        try:
            t1 = time.time()
            response = chat_completion(messages=messages)
            answer = response.choices[0].message.content or ""
            logger.info(f"[RAG] LLM 응답 완료: {len(answer)}자 ({time.time()-t1:.1f}초) | 총 {time.time()-t0:.1f}초")
        except Exception as e:
            logger.error(f"[RAG] LLM 호출 실패: {e}")
            answer = f"LLM 호출 실패: {e}"

        return {"answer": answer, "sources": sources}

    async def list_collections(self) -> list[dict]:
        return self._vector_store.list_collections()

    async def list_documents(self, collection: str) -> list[dict]:
        return self._vector_store.list_documents(collection)

    async def get_document_chunks(self, collection: str, doc_id: str) -> list[dict]:
        return self._vector_store.get_document_chunks(collection, doc_id)

    async def delete_document(self, collection: str, doc_id: str) -> dict:
        removed = self._vector_store.delete_document(collection, doc_id)
        logger.info(f"Deleted document {doc_id} from {collection}: {removed} chunks")
        return {"status": "deleted", "doc_id": doc_id, "chunks_removed": removed}

    async def delete_collection(self, collection_id: str) -> None:
        self._vector_store.delete_collection(collection_id)
        logger.info(f"Deleted collection: {collection_id}")
