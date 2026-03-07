import chromadb
from loguru import logger

from app.config import settings


class VectorStore:
    def __init__(self):
        self._client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
            logger.info(f"Connected to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        return self._client

    def add_documents(
        self,
        collection: str,
        documents: list[str],
        doc_id: str,
        filename: str,
    ) -> None:
        col = self.client.get_or_create_collection(name=collection)
        ids = [f"{doc_id}_{i}" for i in range(len(documents))]
        metadatas = [{"filename": filename, "chunk_index": i} for i in range(len(documents))]
        col.add(documents=documents, ids=ids, metadatas=metadatas)
        logger.info(f"Added {len(documents)} chunks to collection '{collection}'")

    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        try:
            col = self.client.get_collection(name=collection)
        except Exception:
            logger.warning(f"Collection '{collection}' not found")
            return []

        results = col.query(query_texts=[query], n_results=top_k)

        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "filename": results["metadatas"][0][i].get("filename", "unknown"),
                "score": results["distances"][0][i] if results.get("distances") else 0,
            })
        return docs

    def list_collections(self) -> list[dict]:
        collections = self.client.list_collections()
        return [{"name": c.name, "count": c.count()} for c in collections]

    def delete_collection(self, collection_id: str) -> None:
        self.client.delete_collection(name=collection_id)
