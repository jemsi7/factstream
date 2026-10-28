from __future__ import annotations

import enum
import uuid
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.timeline import TimelineItem


class EventStatus(str, enum.Enum):
    ongoing = "ongoing"
    concluded = "concluded"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(400), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus, name="event_status"), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    articles: Mapped[List["Article"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    timeline_items: Mapped[List["TimelineItem"]] = relationship(back_populates="event", cascade="all, delete-orphan")
