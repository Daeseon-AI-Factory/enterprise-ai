from fastapi import APIRouter
from pydantic import BaseModel

from app.services.review_service import ReviewService

router = APIRouter()
service = ReviewService()


class ReviewRequest(BaseModel):
    code: str
    language: str = ""
    context: str = ""  # optional description of what the code does


class CodeReviewResponse(BaseModel):
    review: str
    language: str


class EdgeCaseResponse(BaseModel):
    analysis: str
    language: str


@router.post("/code", response_model=CodeReviewResponse)
async def code_review(req: ReviewRequest):
    """AI-powered code review — identifies bugs, security issues, and improvements."""
    return await service.code_review(
        code=req.code,
        language=req.language,
        context=req.context,
    )


@router.post("/edge-cases", response_model=EdgeCaseResponse)
async def edge_case_review(req: ReviewRequest):
    """AI-powered edge case analysis — finds boundary conditions and failure scenarios."""
    return await service.edge_case_review(
        code=req.code,
        language=req.language,
        context=req.context,
    )
