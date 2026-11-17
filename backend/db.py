"""Database access and persistence for CodeLens."""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("REVIEW_DB_PATH", str(ROOT / "data" / "feedback.sqlite3")))
_LOCK = threading.Lock()


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database():
    with _LOCK, connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, code TEXT NOT NULL,
            findings TEXT NOT NULL, ai_review TEXT NOT NULL, warnings TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY, review_id TEXT NOT NULL, created_at TEXT NOT NULL,
            verdict TEXT NOT NULL, correction TEXT NOT NULL,
            FOREIGN KEY(review_id) REFERENCES reviews(id)
        )""")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
        if "language" not in columns:
            conn.execute("ALTER TABLE reviews ADD COLUMN language TEXT NOT NULL DEFAULT 'python'")


def save_review(code, language, findings, ai_review, warnings):
    review_id = str(uuid.uuid4())
    with _LOCK, connect() as conn:
        conn.execute("""INSERT INTO reviews
            (id, created_at, code, findings, ai_review, warnings, language)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                review_id, datetime.now(timezone.utc).isoformat(), code,
                json.dumps(findings), ai_review, json.dumps(warnings), language,
            ))
    return review_id


def save_feedback(review_id, verdict, correction):
    with _LOCK, connect() as conn:
        exists = conn.execute("SELECT 1 FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not exists:
            return None
        feedback_id = str(uuid.uuid4())
        conn.execute("""INSERT INTO feedback
            (id, review_id, created_at, verdict, correction)
            VALUES (?, ?, ?, ?, ?)""", (
                feedback_id, review_id, datetime.now(timezone.utc).isoformat(),
                verdict, correction,
            ))
    return feedback_id
