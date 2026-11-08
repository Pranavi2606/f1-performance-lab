from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.races import router as races_router
from app.api.analytics import router as analytics_router
from app.api.ml import router as ml_router
from app.api.research import router as research_router
from app.api.lab import router as lab_router
from app.api.benchmark import router as benchmark_router

app = FastAPI(title="F1 Race Decision Intelligence API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(races_router)
app.include_router(analytics_router)
app.include_router(ml_router)
app.include_router(research_router)
app.include_router(lab_router)
app.include_router(benchmark_router)
