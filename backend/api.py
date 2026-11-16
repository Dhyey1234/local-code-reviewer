"""Local review API. Start with: uvicorn backend.api:app --reload"""
from __future__ import annotations
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.static_analyzer import analyze_code
from backend.local_reviewer import generate_review

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("REVIEW_DB_PATH", str(ROOT / "data" / "feedback.sqlite3")))
MAX_CODE = 30000
_lock = threading.Lock()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, code TEXT NOT NULL,
      findings TEXT NOT NULL, ai_review TEXT NOT NULL, warnings TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
      id TEXT PRIMARY KEY, review_id TEXT NOT NULL, created_at TEXT NOT NULL,
      verdict TEXT NOT NULL, correction TEXT NOT NULL,
      FOREIGN KEY(review_id) REFERENCES reviews(id)
    )""")
    return conn

@asynccontextmanager
async def lifespan(app):
    with connect():
        pass
    yield

app = FastAPI(title="Local Code Reviewer", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])

class ReviewRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE)
    use_ai: bool = True

class FeedbackRequest(BaseModel):
    review_id: str
    verdict: str
    correction: str = Field(default="", max_length=10000)

@app.get("/api/health")
def health():
    return {"status": "ok", "model": os.environ.get("REVIEW_MODEL", "mlx-community/Qwen2.5-1.5B-Instruct-4bit")}

@app.post("/api/review")
def review(req: ReviewRequest):
    import json
    findings = analyze_code(req.code)
    ai_review = "AI disabled; showing static analysis only."
    warnings = []
    if req.use_ai:
        try:
            ai_review, warnings = generate_review(req.code, findings)
        except Exception as exc:
            warnings.append(f"AI generation unavailable: {type(exc).__name__}: {exc}")
            ai_review = "AI review unavailable. Static findings are still shown."
    review_id = str(uuid.uuid4())
    with _lock, connect() as conn:
        conn.execute("INSERT INTO reviews VALUES (?,?,?,?,?,?)", (review_id, datetime.now(timezone.utc).isoformat(), req.code, json.dumps(findings), ai_review, json.dumps(warnings)))
    return {"review_id": review_id, "findings": findings, "ai_review": ai_review, "warnings": warnings}

@app.post("/api/feedback", status_code=201)
def feedback(req: FeedbackRequest):
    if req.verdict not in ("correct", "incorrect"):
        raise HTTPException(422, "verdict must be correct or incorrect")
    with _lock, connect() as conn:
        if not conn.execute("SELECT 1 FROM reviews WHERE id=?", (req.review_id,)).fetchone():
            raise HTTPException(404, "Review not found")
        feedback_id = str(uuid.uuid4())
        conn.execute("INSERT INTO feedback VALUES (?,?,?,?,?)", (feedback_id, req.review_id, datetime.now(timezone.utc).isoformat(), req.verdict, req.correction))
    return {"feedback_id": feedback_id, "saved": True, "used_for_training": False}
