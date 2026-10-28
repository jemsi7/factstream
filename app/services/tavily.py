from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import httpx

from app.core.config import settings


@dataclass
class TavilyResult:
    url: str
    title: Optional[str]
    snippet: Optional[str]
    published_date: Optional[date]
    raw: dict[str, Any]


def _try_parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, str):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.date()
        except Exception:
            return None
    return None


async def tavily_search(query: str, max_results: int | None = None) -> list[TavilyResult]:
    """
    Uses Tavily API to search the web for evidence.
    Tries tavily-python client if installed; otherwise uses direct HTTP.
    """
    max_results = max_results or settings.TAVILY_MAX_RESULTS

    # 1) Try tavily-python client if available
    try:
        from tavily import TavilyClient  # type: ignore

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        resp = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
            include_raw_content=False,
        )
        results = resp.get("results", []) if isinstance(resp, dict) else []
        out: list[TavilyResult] = []
        for r in results:
            out.append(
                TavilyResult(
                    url=r.get("url"),
                    title=r.get("title"),
                    snippet=r.get("content") or r.get("snippet"),
                    published_date=_try_parse_date(r.get("published_date") or r.get("published_time")),
                    raw=r,
                )
            )
        return out
    except Exception:
        pass

    # 2) Direct HTTP fallback
    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_S)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": False,
                "include_raw_content": False,
            },
        )
        r.raise_for_status()
        data = r.json()

    results = data.get("results", []) if isinstance(data, dict) else []
    out: list[TavilyResult] = []
    for r in results:
        out.append(
            TavilyResult(
                url=r.get("url"),
                title=r.get("title"),
                snippet=r.get("content") or r.get("snippet"),
                published_date=_try_parse_date(r.get("published_date") or r.get("published_time")),
                raw=r,
            )
        )
    return out


async def tavily_search_many(claims: list[str], max_results: int | None = None) -> dict[str, list[TavilyResult]]:
    """
    Returns a mapping claim_text -> list[TavilyResult]
    """
    import asyncio

    max_results = max_results or settings.TAVILY_MAX_RESULTS

    async def _one(c: str) -> tuple[str, list[TavilyResult]]:
        res = await tavily_search(c, max_results=max_results)
        return c, res

    tasks = [_one(c) for c in claims]
    pairs = await asyncio.gather(*tasks, return_exceptions=False)
    return {k: v for (k, v) in pairs}


@dataclass
class TavilyExtractResult:
    url: str
    raw_content: Optional[str]
    title: Optional[str]


async def tavily_extract(url: str) -> Optional[TavilyExtractResult]:
    """
    Uses Tavily Extract API to get content from a URL.
    This is useful when direct scraping fails.
    """
    # Try tavily-python client if available
    try:
        from tavily import TavilyClient  # type: ignore

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        resp = client.extract(urls=[url])
        results = resp.get("results", []) if isinstance(resp, dict) else []
        if results and len(results) > 0:
            r = results[0]
            return TavilyExtractResult(
                url=r.get("url", url),
                raw_content=r.get("raw_content"),
                title=None,
            )
    except Exception:
        pass

    # Direct HTTP fallback
    try:
        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_S)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                "https://api.tavily.com/extract",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "urls": [url],
                },
            )
            r.raise_for_status()
            data = r.json()

        results = data.get("results", []) if isinstance(data, dict) else []
        if results and len(results) > 0:
            r = results[0]
            return TavilyExtractResult(
                url=r.get("url", url),
                raw_content=r.get("raw_content"),
                title=None,
            )
    except Exception:
        pass

    return None
