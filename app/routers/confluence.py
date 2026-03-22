from fastapi import APIRouter
from pydantic import BaseModel

from app.services.confluence_service import ConfluenceService

router = APIRouter()
service = ConfluenceService()


class ConfluenceConnection(BaseModel):
    base_url: str  # e.g. "https://company.atlassian.net/wiki"
    username: str  # email for Cloud
    api_token: str


class SyncRequest(ConfluenceConnection):
    space_key: str
    collection: str | None = None
    labels: list[str] | None = None
    full_sync: bool = False


class SyncResponse(BaseModel):
    status: str
    space_key: str
    collection: str
    synced: int
    total_chunks: int = 0


@router.post("/sync", response_model=SyncResponse)
async def sync_space(req: SyncRequest):
    """Sync a Confluence space into the vector DB."""
    result = await service.sync_space(
        base_url=req.base_url,
        username=req.username,
        api_token=req.api_token,
        space_key=req.space_key,
        collection=req.collection,
        labels=req.labels,
        full_sync=req.full_sync,
    )
    return result


@router.post("/spaces")
async def list_spaces(conn: ConfluenceConnection):
    """List available Confluence spaces (requires connection info)."""
    spaces = await service.list_spaces(
        base_url=conn.base_url,
        username=conn.username,
        api_token=conn.api_token,
    )
    return spaces


class RegisterPageRequest(ConfluenceConnection):
    page_url: str  # Confluence 페이지 URL
    collection: str = "confluence_pages"


@router.post("/register-page")
async def register_page(req: RegisterPageRequest):
    """Confluence 페이지 URL을 입력하면 API로 콘텐츠를 가져와 RAG에 등록."""
    return await service.register_page_by_url(
        page_url=req.page_url,
        base_url=req.base_url,
        username=req.username,
        api_token=req.api_token,
        collection=req.collection,
    )
