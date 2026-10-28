from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.article import Article
from app.models.event import Event
from app.models.timeline import TimelineItem
from app.schemas.events import EventDetailResponse
from app.schemas.common import ArticleRead, ClaimRead, EventRead, TimelineItemRead

router = APIRouter(tags=["events"])


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event_timeline(event_id: UUID, db: AsyncSession = Depends(get_db)) -> EventDetailResponse:
    q = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.articles),
            selectinload(Event.timeline_items).selectinload(TimelineItem.related_articles),
            selectinload(Event.articles).selectinload(Article.claims),
        )
    )
    evt = q.scalar_one_or_none()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    # flatten claims across articles
    all_claims = []
    for a in evt.articles:
        all_claims.extend(a.claims)

    timeline_items = sorted(evt.timeline_items, key=lambda x: (x.date is None, x.date or date.min))

    return EventDetailResponse(
        event=EventRead.model_validate(evt),
        articles=[ArticleRead.model_validate(a) for a in evt.articles],
        claims=[ClaimRead.model_validate(c) for c in all_claims],
        timeline=[TimelineItemRead.model_validate(ti) for ti in timeline_items],
    )
