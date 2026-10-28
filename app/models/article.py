from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.claim import Claim
    from app.models.timeline import TimelineItem


class SourceType(str, enum.Enum):
    major_media = "major_media"
    official = "official"
    blog = "blog"
    other = "other"


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("event_id", "url", name="uq_articles_event_url"),
        Index("ix_articles_event_published_date", "event_id", "published_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), index=True)

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(600), nullable=True)
    content_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"), nullable=False, default=SourceType.other)

    # Optional: store extracted content (original article) for audit/debug
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional: vector embeddings for semantic search / clustering
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="articles")
    claims: Mapped[List["Claim"]] = relationship(back_populates="article", cascade="all, delete-orphan")

    timeline_items: Mapped[List["TimelineItem"]] = relationship(
        secondary="timeline_item_articles",
        back_populates="related_articles",
        viewonly=True,
    )
