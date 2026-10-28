from __future__ import annotations

import enum
import uuid
from typing import Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.article import Article


class VerificationStatus(str, enum.Enum):
    verified = "verified"
    disputed = "disputed"
    unknown = "unknown"


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        Index("ix_claims_article_id", "article_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.unknown,
    )

    # Store Tavily evidence + LLM notes as JSON for easy frontend rendering
    evidence: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)

    # Optional embeddings for semantic similarity search
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    article: Mapped["Article"] = relationship(back_populates="claims")
