from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel

from app.services.rag_service import RagService

router = APIRouter()
service = RagService()


class RagQueryRequest(BaseModel):
    query: str
    collection: str = "all"
    top_k: int = 5


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[dict]


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("default"),
):
    """Upload a document (PDF/Word/Excel/code) for RAG indexing."""
    result = await service.upload_and_index(file=file, collection=collection)
    return result


@router.post("/query", response_model=RagQueryResponse)
async def query(req: RagQueryRequest):
    """Query documents using RAG."""
    result = await service.query(
        query=req.query,
        collection=req.collection,
        top_k=req.top_k,
    )
    return result


@router.get("/collections")
async def list_collections():
    """List all document collections."""
    return await service.list_collections()


@router.get("/collections/{collection_name}/documents")
async def list_documents(collection_name: str):
    """List all documents (files) in a collection."""
    return await service.list_documents(collection_name)


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str):
    """Delete a document collection."""
    await service.delete_collection(collection_id)
    return {"status": "deleted", "collection": collection_id}
