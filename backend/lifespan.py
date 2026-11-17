"""FastAPI application lifecycle."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.db import initialize_database
from backend.review_jobs import ReviewJobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    app.state.review_jobs = ReviewJobs()
    try:
        yield
    finally:
        app.state.review_jobs.shutdown()
