"""CodeLens HTTP routes."""
import os
from fastapi import APIRouter, HTTPException, Request
from backend.db import save_feedback, save_review
from backend.review_service import ReviewService
from backend.schemas import FeedbackRequest, ReviewRequest

router = APIRouter(prefix="/api")
service = ReviewService()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "model": os.environ.get("REVIEW_MODEL", "mlx-community/Qwen2.5-1.5B-Instruct-4bit"),
        "languages": ["python", "javascript", "typescript", "java", "cpp", "csharp"],
    }


@router.post("/review")
def review(req: ReviewRequest):
    result = service.run(req)
    result["review_id"] = save_review(
        req.code, result["language"], result["findings"],
        result["ai_review"], result["warnings"],
    )
    return result


@router.post("/feedback", status_code=201)
def feedback(req: FeedbackRequest):
    feedback_id = save_feedback(req.review_id, req.verdict, req.correction)
    if feedback_id is None:
        raise HTTPException(404, "Review not found")
    return {"feedback_id": feedback_id, "saved": True, "used_for_training": False}


@router.post("/review/jobs", status_code=202)
def submit_review(req: ReviewRequest, request: Request):
    job_id = request.app.state.review_jobs.submit(req)
    if job_id is None:
        raise HTTPException(429, "Review queue is full. Try again shortly.")
    return {"job_id": job_id, "status": "queued"}


@router.get("/review/jobs/{job_id}")
def review_status(job_id: str, request: Request):
    job = request.app.state.review_jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Review job not found or expired")
    return job
