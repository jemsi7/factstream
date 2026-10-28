# Pydantic v2 requires proper type evaluation, so we don't use "from __future__ import annotations"
# IMPORTANT: Use `import datetime` instead of `from datetime import date` to avoid type resolution issues

import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EventStatus(str, Enum):
    ongoing = "ongoing"
    concluded = "concluded"


class SourceType(str, Enum):
    major_media = "major_media"
    official = "official"
    blog = "blog"
    other = "other"


class VerificationStatus(str, Enum):
    verified = "verified"
    disputed = "disputed"
    unknown = "unknown"


class TimelineItemType(str, Enum):
    initial_report = "initial_report"
    correction = "correction"
    rebuttal = "rebuttal"
    official_statement = "official_statement"
    court_ruling = "court_ruling"
    investigation_update = "investigation_update"
    context = "context"
    other = "other"


class EvidenceSource(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    snippet: Optional[str] = None
    published_date: Union[datetime.date, None] = None
    source: Optional[str] = Field(default=None, description="Domain or publisher name if available")


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    url: str
    title: Optional[str] = None
    content_summary: Optional[str] = None
    published_date: Union[datetime.date, None] = None
    source_type: SourceType
    created_at: datetime.datetime


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_id: UUID
    content: str
    verification_status: VerificationStatus
    evidence: Optional[dict[str, Any]] = None
    created_at: datetime.datetime


class TimelineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    date: Union[datetime.date, None] = None
    type: TimelineItemType
    summary: str
    related_articles: list[ArticleRead] = []
    created_at: datetime.datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str
    status: EventStatus
    created_at: datetime.datetime
