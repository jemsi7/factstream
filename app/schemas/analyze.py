# Pydantic v2 compatibility - do not use "from __future__ import annotations"

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl

from app.schemas.common import ClaimRead, EventRead, TimelineItemRead, ArticleRead


class AnalyzeRequest(BaseModel):
    url: HttpUrl


class AnalyzeResponse(BaseModel):
    event: EventRead
    articles: list[ArticleRead]
    claims: list[ClaimRead]
    timeline: list[TimelineItemRead]
