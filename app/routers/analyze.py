from __future__ import annotations

import json
import asyncio
import traceback
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import HttpUrl

from app.core.database import get_db
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.analyze_service import analyze_and_persist_streaming

router = APIRouter(tags=["analyze"])
logger = logging.getLogger(__name__)


def sse_message(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/analyze/stream")
async def analyze_stream(url: str, db: AsyncSession = Depends(get_db)):
    """
    SSE endpoint for streaming analysis progress.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in analyze_and_persist_streaming(url, db):
                yield sse_message(event)
                await asyncio.sleep(0.1)  # Small delay for smooth UI updates
        except Exception as e:
            logger.error(f"Streaming analyze failed: {e}")
            logger.error(traceback.format_exc())
            yield sse_message({"type": "error", "message": str(e)})
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_article(payload: AnalyzeRequest, db: AsyncSession = Depends(get_db)) -> AnalyzeResponse:
    """Non-streaming analyze endpoint (legacy)."""
    from app.services.analyze_service import analyze_and_persist
    try:
        result = await analyze_and_persist(str(payload.url), db)
        return AnalyzeResponse(**result.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze failed for URL {payload.url}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=422, detail=f"Analyze failed: {type(e).__name__}: {str(e)}")
