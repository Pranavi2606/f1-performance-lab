"""Vercel FastAPI entrypoint for the backend-root project.

Vercel discovers a module-level `app` in index.py; the local Uvicorn command
continues to use `app.main:app`. No training models or image datasets are bundled.
"""
from app.main import app
