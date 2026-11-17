"""CodeLens FastAPI entry point: uvicorn backend.api:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.lifespan import lifespan
from backend.routes import router

app = FastAPI(title="CodeLens", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
