from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.routers import analyze_router, events_router

app = FastAPI(title="News Fact-Check Timeline", version="0.1.0")

# Adjust as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router, prefix=settings.API_V1_PREFIX)
app.include_router(events_router, prefix=settings.API_V1_PREFIX)

# Static files
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "home.html")


@app.get("/loading")
async def loading_page():
    return FileResponse(STATIC_DIR / "loading.html")


@app.get("/timeline")
async def timeline_page():
    return FileResponse(STATIC_DIR / "timeline.html")


@app.get("/health")
async def health():
    return {"ok": True}
