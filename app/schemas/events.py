# Pydantic v2 compatibility - do not use "from __future__ import annotations"

from pydantic import BaseModel

from app.schemas.common import ArticleRead, ClaimRead, EventRead, TimelineItemRead


class EventDetailResponse(BaseModel):
    event: EventRead
    articles: list[ArticleRead]
    claims: list[ClaimRead]
    timeline: list[TimelineItemRead]
