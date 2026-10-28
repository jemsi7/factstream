from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.models.event import Event
from app.models.timeline import TimelineItem
from app.services.tavily import tavily_search


async def recheck_event_for_updates(event_id: UUID, db: AsyncSession) -> None:
    """
    Stub: periodically re-check an event for new articles.
    Idea:
      1) Load event + existing articles + last timeline date
      2) Search Tavily for: event.title, key entities, and/or top disputed claims
      3) Compare URLs against stored Article URLs
      4) If new URLs exist:
         - store new Article rows
         - optionally scrape+summarize them
         - run LLM to append timeline items (or re-synthesize timeline)
    """
    q = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.articles), selectinload(Event.timeline_items))
    )
    evt = q.scalar_one_or_none()
    if not evt:
        return

    known_urls = {a.url for a in evt.articles}
    query = f"{evt.title} update OR correction OR statement OR ruling"
    results = await tavily_search(query, max_results=8)

    new_urls = [r.url for r in results if r.url and r.url not in known_urls]
    if not new_urls:
        return

    # Persist new articles (minimal metadata for now)
    for r in results:
        if not r.url or r.url in known_urls:
            continue
        a = Article(
            event_id=evt.id,
            url=r.url,
            title=r.title,
            published_date=r.published_date,
            content_summary=r.snippet,
        )
        db.add(a)

    # Later: create timeline items + associations here
    # For now: just save the discovered articles.
    await db.commit()
