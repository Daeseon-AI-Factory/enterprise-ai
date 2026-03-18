"""Git 소스 코드 → RAG 색인 라우터."""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from app.connectors.git_connector import GitConnector
from app.core.vector_store import get_vector_store

router = APIRouter()
_connector = GitConnector()
_vector_store = get_vector_store()

# 진행 상황 추적 (간단한 인메모리)
_jobs: dict[str, dict] = {}


class IndexRepoRequest(BaseModel):
    repo_path: str          # 로컬 경로 (예: C:/Sources/MyProject)
    repo_url: str | None = None   # 원격 URL (clone/pull)
    collection: str | None = None  # 기본값: git_{폴더명}
    max_files: int = 500


class IndexStatusResponse(BaseModel):
    job_id: str
    status: str
    files_indexed: int = 0
    chunks_indexed: int = 0
    message: str = ""


def _do_index(job_id: str, req: IndexRepoRequest):
    """백그라운드 색인 작업."""
    _jobs[job_id] = {"status": "running", "files_indexed": 0, "chunks_indexed": 0}
    try:
        # 1. clone/pull (URL 있을 때만)
        path = req.repo_path
        if req.repo_url:
            path = _connector.clone_or_pull(req.repo_url, req.repo_path)

        # 2. 파일 읽기
        files = _connector.read_files(path, max_files=req.max_files)
        if not files:
            _jobs[job_id] = {"status": "done", "files_indexed": 0, "chunks_indexed": 0, "message": "파일 없음"}
            return

        # 3. 컬렉션명 결정
        import os
        stripped = path.rstrip('/\\')
        collection = req.collection or f"git_{os.path.basename(stripped)}"

        # 4. 청크 생성 및 색인
        import uuid
        total_chunks = 0
        for file in files:
            chunks = _connector.chunk_file(file)
            if not chunks:
                continue
            doc_id = str(uuid.uuid4())
            texts = [c["content"] for c in chunks]
            _vector_store.add_documents(
                collection=collection,
                documents=texts,
                doc_id=doc_id,
                filename=file["path"],
            )
            total_chunks += len(chunks)

        _jobs[job_id] = {
            "status": "done",
            "files_indexed": len(files),
            "chunks_indexed": total_chunks,
            "message": f"컬렉션 '{collection}'에 색인 완료",
        }
        logger.info(f"Git index done: {len(files)} files, {total_chunks} chunks → '{collection}'")

    except Exception as e:
        logger.error(f"Git index failed: {e}")
        _jobs[job_id] = {"status": "error", "files_indexed": 0, "chunks_indexed": 0, "message": str(e)}


@router.post("/index")
async def index_repo(req: IndexRepoRequest, background_tasks: BackgroundTasks):
    """소스 저장소를 RAG로 색인 (백그라운드)."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_do_index, job_id, req)
    return {"job_id": job_id, "status": "started", "message": "백그라운드에서 색인 중..."}


@router.get("/index/{job_id}")
async def index_status(job_id: str):
    """색인 작업 진행 상황 조회."""
    job = _jobs.get(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, **job}


@router.get("/collections")
async def list_git_collections():
    """git_ 접두사 컬렉션 목록."""
    all_cols = _vector_store.list_collections()
    return [c for c in all_cols if c["name"].startswith("git_")]
