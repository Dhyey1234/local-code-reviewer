
"""Local CodeLens review API."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.multilang_analyzer import analyze_code, detect_language
from backend.local_reviewer import generate_review


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = Path(
    os.environ.get(
        "REVIEW_DB_PATH",
        str(ROOT / "data" / "feedback.sqlite3")
    )
)

MAX_CODE = 30000
_lock = threading.Lock()

Language = Literal[
    "python",
    "javascript",
    "typescript",
    "java",
    "cpp",
    "csharp",
]

LANGUAGE_NAMES = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "cpp": "C++",
    "csharp": "C#",
}


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            code TEXT NOT NULL,
            findings TEXT NOT NULL,
            ai_review TEXT NOT NULL,
            warnings TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            review_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            verdict TEXT NOT NULL,
            correction TEXT NOT NULL,
            FOREIGN KEY(review_id) REFERENCES reviews(id)
        )
    """)

    # Preserve existing reviews while adding language metadata.
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(reviews)")
    }

    if "language" not in columns:
        conn.execute(
            "ALTER TABLE reviews "
            "ADD COLUMN language TEXT NOT NULL DEFAULT 'python'"
        )

    return conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    with connect():
        pass
    yield


app = FastAPI(
    title="CodeLens",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE)
    language: Literal["auto", "python", "javascript", "typescript", "java", "cpp", "csharp"] = "auto"
    use_ai: bool = True


class FeedbackRequest(BaseModel):
    review_id: str
    verdict: Literal["correct", "incorrect"]
    correction: str = Field(default="", max_length=10000)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": os.environ.get(
            "REVIEW_MODEL",
            "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        ),
        "languages": list(LANGUAGE_NAMES),
    }


@app.post("/api/review")
def review(req: ReviewRequest):
    language = req.language
    if language == "auto":
        language = detect_language(req.code)
        if language is None:
            raise HTTPException(422, "Language is ambiguous. Please select it manually.")
    findings = analyze_code(req.code, language)

    ai_review = ""
    warnings = []

    if req.use_ai:
        try:
            ai_review, warnings = generate_review(req.code, findings, language=language)

        except Exception as exc:
            warnings.append(
                f"AI generation unavailable: "
                f"{type(exc).__name__}: {exc}"
            )
            ai_review = (
                "AI review unavailable. "
                "Try again after checking the local model."
            )


    review_id = str(uuid.uuid4())

    with _lock, connect() as conn:
        conn.execute(
            """
            INSERT INTO reviews (
                id, created_at, code, findings,
                ai_review, warnings, language
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                datetime.now(timezone.utc).isoformat(),
                req.code,
                json.dumps(findings),
                ai_review,
                json.dumps(warnings),
                language,
            ),
        )

    return {
        "review_id": review_id,
        "language": language,
        "findings": findings,
        "ai_review": ai_review,
        "warnings": warnings,
    }


@app.post("/api/feedback", status_code=201)
def feedback(req: FeedbackRequest):
    with _lock, connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM reviews WHERE id=?",
            (req.review_id,),
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Review not found",
            )

        feedback_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO feedback
            (id, review_id, created_at, verdict, correction)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                req.review_id,
                datetime.now(timezone.utc).isoformat(),
                req.verdict,
                req.correction,
            ),
        )

    return {
        "feedback_id": feedback_id,
        "saved": True,
        "used_for_training": False,
    }
