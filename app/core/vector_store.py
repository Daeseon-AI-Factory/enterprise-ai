import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

from app.config import settings


class VectorStore:
    def __init__(self):
        self._client: chromadb.ClientAPI | None = None
        self._embedding_fn: SentenceTransformerEmbeddingFunction | None = None

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
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            if settings.CHROMA_HOST == "localhost" and settings.CHROMA_PORT == 0:
                # Persistent local mode (no Docker needed)
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

    def add_documents(
        self,
        collection: str,
        documents: list[str],
        doc_id: str,
        filename: str,
    ) -> None:
        col = self._get_collection(collection, create=True)
        ids = [f"{doc_id}_{i}" for i in range(len(documents))]
        metadatas = [{"filename": filename, "chunk_index": i, "doc_id": doc_id} for i in range(len(documents))]
        # Batch insert (ChromaDB has a limit of ~41666 per batch)
        batch_size = 5000
        for start in range(0, len(documents), batch_size):
            end = min(start + batch_size, len(documents))
            col.add(
                documents=documents[start:end],
                ids=ids[start:end],
                metadatas=metadatas[start:end],
            )
        logger.info(f"Added {len(documents)} chunks to collection '{collection}'")

    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        try:
            col = self._get_collection(collection)
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
        result = []
        for name in collections:
            try:
                col = self.client.get_collection(name=name if isinstance(name, str) else name.name)
                result.append({"name": col.name, "count": col.count()})
            except Exception:
                result.append({"name": str(name), "count": 0})
        return result

    def delete_collection(self, collection_id: str) -> None:
        self.client.delete_collection(name=collection_id)
