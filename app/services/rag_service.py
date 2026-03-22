import os
import uuid

from fastapi import UploadFile
from loguru import logger

from app.llm_client import chat_completion
from app.core.vector_store import get_vector_store
from app.core.document_loader import DocumentLoader
from app.core.prompts import SYSTEM_RAG


class RagService:
    def __init__(self):
        self._vector_store = get_vector_store()
        self._doc_loader = DocumentLoader()

    async def upload_and_index(
        self,
        file: UploadFile,
        collection: str = "default",
    ) -> dict:
        """Upload document, chunk it, embed, and store in vector DB."""
        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Load and chunk document
        chunks = self._doc_loader.load_and_chunk(file_path, file.filename)
        logger.info(f"Loaded {len(chunks)} chunks from {file.filename}")

        # Store in vector DB
        doc_id = str(uuid.uuid4())
        self._vector_store.add_documents(
            collection=collection,
            documents=chunks,
            doc_id=doc_id,
            filename=file.filename,
        )

        return {
            "status": "indexed",
            "filename": file.filename,
            "chunks": len(chunks),
            "collection": collection,
            "doc_id": doc_id,
        }

    async def query(
        self,
        query: str,
        collection: str = "all",
        top_k: int = 5,
    ) -> dict:
        """Query documents using RAG pipeline. collection='all' searches every collection."""
        if not self._vector_store.embedding_available:
            return {
                "answer": "임베딩 모델이 설치되지 않았습니다. models/embedding/ 폴더에 모델을 복사해주세요.",
                "sources": [],
            }
        # Search all collections or a specific one (hybrid: dense + BM25 + rerank)
        if collection in ("all", "", "*"):
            all_results = []
            for col in self._vector_store.list_collections():
                col_name = col["name"]
                try:
                    hits = self._vector_store.hybrid_search(
                        collection=col_name, query=query, top_k=top_k
                    )
                    for h in hits:
                        h["collection"] = col_name
                    all_results.extend(hits)
                except Exception as e:
                    logger.warning(f"Hybrid search failed in '{col_name}': {e}")
            # Final cross-collection rerank by rerank_score
            all_results.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
            results = all_results[:top_k]
            logger.info(
                f"RAG hybrid (all collections): '{query[:50]}' → {len(results)} chunks "
                f"from {list(set(r.get('collection','') for r in results))}"
            )
        else:
            results = self._vector_store.hybrid_search(
                collection=collection, query=query, top_k=top_k
            )
            for r in results:
                r["collection"] = collection
            logger.info(f"RAG hybrid ('{collection}'): '{query[:50]}' → {len(results)} chunks")

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
            response = chat_completion(messages=messages)
            answer = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"RAG LLM call failed: {e}")
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
