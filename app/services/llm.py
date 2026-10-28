from __future__ import annotations

import json
from datetime import date
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from app.core.config import settings


# -----------------------------
# LLM Output Schemas
# -----------------------------
class ExtractedClaim(BaseModel):
    content: str = Field(..., description="An atomic, verifiable factual claim.")


class ClaimExtractionOutput(BaseModel):
    title: Optional[str] = Field(default=None, description="Best-guess article title.")
    published_date: Optional[str] = Field(default=None, description="Best-guess publish date (YYYY-MM-DD).")
    summary: str = Field(..., description="Neutral 3-6 sentence summary.")
    claims: List[ExtractedClaim] = Field(..., description="5-12 atomic factual claims.")


class EvidenceSource(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    snippet: Optional[str] = None
    published_date: Optional[str] = None


class ClaimVerdict(BaseModel):
    content: str
    verification_status: Literal["verified", "disputed", "unknown"]
    notes: Optional[str] = Field(default=None, description="Short explanation of why.")
    supporting_sources: List[EvidenceSource] = Field(default_factory=list)
    opposing_sources: List[EvidenceSource] = Field(default_factory=list)


class EventClassification(BaseModel):
    title: str
    summary: str
    status: Literal["ongoing", "concluded"]


class TimelineItemLLM(BaseModel):
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD if known; null otherwise.")
    type: Literal[
        "initial_report",
        "correction",
        "rebuttal",
        "official_statement",
        "court_ruling",
        "investigation_update",
        "context",
        "other",
    ]
    summary: str
    related_urls: List[HttpUrl] = Field(default_factory=list)


class TimelineSynthesisOutput(BaseModel):
    event: EventClassification
    claims: List[ClaimVerdict]
    timeline: List[TimelineItemLLM]


# -----------------------------
# Prompts
# -----------------------------
CLAIM_EXTRACTION_SYSTEM = """You extract factual, verifiable claims from news articles.
Rules:
- Output MUST be valid JSON only (no markdown).
- **ALL text content (summary, claims, title) MUST be written in Korean (한국어).**
- Claims must be atomic, self-contained, and verifiable (avoid opinions).
- Prefer concrete entities, dates, numbers. If missing, keep it general but factual.
- De-duplicate overlapping claims.
"""

CLAIM_EXTRACTION_HUMAN = """URL: {url}
Known title: {known_title}
Known published_date: {known_published_date}

ARTICLE TEXT (may be truncated):
{article_text}

Task:
1) Write a neutral summary (3-6 sentences).
2) Extract 5-12 atomic factual claims.

{format_instructions}
"""

TIMELINE_SYSTEM = """You build a fact-check timeline from an original article plus web evidence.
Rules:
- Output MUST be valid JSON only (no markdown).
- **ALL text content (event title, event summary, claim content, claim notes, timeline summaries) MUST be written in Korean (한국어).**
- Timeline items should be chronological when dates are known.
- Each timeline item: short, factual, and should cite related_urls when possible.
- For each claim, assign verification_status:
  - verified: multiple independent sources OR primary source corroboration
  - disputed: credible sources contradict or corrections exist
  - unknown: insufficient or conflicting evidence
- Do not invent facts not present in inputs. If uncertain, mark unknown.
"""

TIMELINE_HUMAN = """ORIGINAL ARTICLE
URL: {url}
Original scrape title: {scrape_title}
Original scrape published_date: {scrape_published_date}

Original summary:
{article_summary}

Extracted claims:
{claims_json}

EVIDENCE (Tavily search results grouped by claim):
{evidence_json}

Task:
- Produce a coherent event classification (title/summary/status).
- Provide claim verdicts with supporting/opposing sources (use the evidence URLs).
- Produce a timeline of key updates (initial report, corrections, official statements, court rulings, etc).

{format_instructions}
"""


def _llm() -> ChatOpenAI:
    model = settings.OPENAI_MODEL
    
    # o-series models (o1, o3, o4-mini, etc.) don't support temperature parameter
    is_o_series = model.startswith("o1") or model.startswith("o3") or model.startswith("o4")
    
    if is_o_series:
        return ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
        )
    else:
        return ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )


def _safe_json_dumps(obj: Any, max_chars: int = 120_000) -> str:
    """
    Prevent sending absurdly large payloads into the model.
    """
    s = json.dumps(obj, ensure_ascii=False, default=str)
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "…(truncated)"


async def extract_claims_llm(
    *,
    url: str,
    article_text: str,
    known_title: str | None,
    known_published_date: date | None,
) -> ClaimExtractionOutput:
    parser = PydanticOutputParser(pydantic_object=ClaimExtractionOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CLAIM_EXTRACTION_SYSTEM),
            ("human", CLAIM_EXTRACTION_HUMAN),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | _llm() | parser

    # Truncate article text to reduce token usage; you can refine chunking later
    trimmed_text = article_text[:20_000]

    return await chain.ainvoke(
        {
            "url": url,
            "known_title": known_title,
            "known_published_date": str(known_published_date) if known_published_date else None,
            "article_text": trimmed_text,
        }
    )


async def synthesize_timeline_llm(
    *,
    url: str,
    scrape_title: str | None,
    scrape_published_date: date | None,
    article_summary: str,
    claims: list[str],
    evidence_by_claim: dict[str, list[dict[str, Any]]],
) -> TimelineSynthesisOutput:
    parser = PydanticOutputParser(pydantic_object=TimelineSynthesisOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TIMELINE_SYSTEM),
            ("human", TIMELINE_HUMAN),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | _llm() | parser

    claims_json = _safe_json_dumps([{"content": c} for c in claims])
    evidence_json = _safe_json_dumps(evidence_by_claim)

    return await chain.ainvoke(
        {
            "url": url,
            "scrape_title": scrape_title,
            "scrape_published_date": str(scrape_published_date) if scrape_published_date else None,
            "article_summary": article_summary,
            "claims_json": claims_json,
            "evidence_json": evidence_json,
        }
    )
