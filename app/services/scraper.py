from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


@dataclass
class ScrapedArticle:
    url: str
    title: Optional[str]
    text: str
    html: Optional[str] = None
    published_date: Optional[date] = None


_META_DATE_KEYS = (
    "article:published_time",
    "og:published_time",
    "pubdate",
    "publishdate",
    "timestamp",
    "dc.date",
    "date",
)


def _extract_date_from_html(html: str) -> Optional[date]:
    soup = BeautifulSoup(html, "lxml")

    # 1) meta tags
    for key in _META_DATE_KEYS:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            d = _parse_date(tag["content"])
            if d:
                return d

    # 2) <time datetime="...">
    time_tag = soup.find("time")
    if time_tag:
        dt = time_tag.get("datetime") or time_tag.get_text(strip=True)
        d = _parse_date(dt)
        if d:
            return d

    return None


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    value = value.strip()

    # Try ISO-ish first
    try:
        # Handles '2024-01-31', '2024-01-31T12:34:56Z', etc.
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.date()
    except Exception:
        pass

    # Common fallback: YYYY/MM/DD or YYYY.MM.DD
    m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", value)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            return date(y, mo, d)
        except Exception:
            return None

    return None


async def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_S)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


def _html_to_text(html: str) -> tuple[Optional[str], str]:
    soup = BeautifulSoup(html, "lxml")

    # Remove scripts/styles
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    
    # Also try og:title
    if not title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()

    # Heuristic: prefer content containers in priority order
    content_selectors = [
        ("article", {}),
        ("div", {"class": re.compile(r"article[-_]?body|article[-_]?content|news[-_]?body|news[-_]?content|post[-_]?content|entry[-_]?content", re.I)}),
        ("div", {"id": re.compile(r"article[-_]?body|article[-_]?content|news[-_]?body|news[-_]?content|content", re.I)}),
        ("div", {"class": re.compile(r"story[-_]?body|story[-_]?content|main[-_]?content", re.I)}),
        ("section", {"class": re.compile(r"article|content|body", re.I)}),
    ]
    
    text = ""
    for tag_name, attrs in content_selectors:
        container = soup.find(tag_name, attrs=attrs) if attrs else soup.find(tag_name)
        if container:
            text = container.get_text("\n", strip=True)
            if len(text) > 100:  # Found substantial content
                break
    
    # Last resort: get all body text
    if len(text) < 100:
        body = soup.find("body")
        if body:
            text = body.get_text("\n", strip=True)
        else:
            text = soup.get_text("\n", strip=True)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text


async def scrape_url(url: str) -> ScrapedArticle:
    """
    Scrape article content.
    1) Try Firecrawl (if FIRECRAWL_API_KEY and firecrawl lib available).
    2) Fallback to raw HTML fetch + BeautifulSoup extraction.
    3) Fallback to Jina Reader API (free, no API key needed).
    """
    # 1) Firecrawl path (optional)
    if settings.FIRECRAWL_API_KEY:
        try:
            from firecrawl import FirecrawlApp  # type: ignore

            app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
            # Firecrawl output shape depends on versions; keep it defensive.
            result = app.scrape_url(url, params={"formats": ["markdown", "html"]})
            data = result.get("data") if isinstance(result, dict) else result

            html = None
            md = None
            title = None
            if isinstance(data, dict):
                html = data.get("html")
                md = data.get("markdown") or data.get("md")
                title = data.get("title")

            text = (md or "").strip()
            if not text and html:
                title2, text2 = _html_to_text(html)
                title = title or title2
                text = text2

            if text and len(text) > 100:
                published = _extract_date_from_html(html) if html else None
                return ScrapedArticle(url=url, title=title, text=text, html=html, published_date=published)
        except Exception:
            # Fall back to BeautifulSoup route
            pass

    # 2) Direct HTTP fallback
    try:
        html = await _fetch_html(url)
        title, text = _html_to_text(html)
        if text and len(text) > 100:
            published = _extract_date_from_html(html)
            return ScrapedArticle(url=url, title=title, text=text, html=html, published_date=published)
    except Exception:
        pass

    # 3) Jina Reader API fallback (free, no API key needed)
    try:
        jina_result = await _jina_reader_extract(url)
        if jina_result and len(jina_result) > 100:
            return ScrapedArticle(url=url, title=None, text=jina_result, html=None, published_date=None)
    except Exception:
        pass

    # Return whatever we have (may be empty)
    return ScrapedArticle(url=url, title=None, text="", html=None, published_date=None)


async def _jina_reader_extract(url: str) -> Optional[str]:
    """
    Uses Jina Reader API to extract content from URL.
    This is free and doesn't require an API key.
    Format: https://r.jina.ai/{url}
    """
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "text/plain",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_S)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(jina_url, headers=headers)
        r.raise_for_status()
        text = r.text.strip()
        # Jina returns markdown content
        if text and len(text) > 50:
            return text
    return None
