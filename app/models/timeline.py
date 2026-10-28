from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.article import Article


class TimelineItemType(str, enum.Enum):
    initial_report = "initial_report"
    correction = "correction"
    rebuttal = "rebuttal"
    official_statement = "official_statement"
    court_ruling = "court_ruling"
    investigation_update = "investigation_update"
    context = "context"
    other = "other"


timeline_item_articles = Table(
    "timeline_item_articles",
    Base.metadata,
    Column("timeline_item_id", UUID(as_uuid=True), ForeignKey("timeline_items.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
)


class TimelineItem(Base):
    __tablename__ = "timeline_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), index=True)

    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    type: Mapped[TimelineItemType] = mapped_column(Enum(TimelineItemType, name="timeline_item_type"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="timeline_items")

    related_articles: Mapped[List["Article"]] = relationship(
        secondary="timeline_item_articles",
        back_populates="timeline_items",
    )
