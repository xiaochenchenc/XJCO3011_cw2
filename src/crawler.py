"""HTTP crawl of https://quotes.toscrape.com/ with politeness delay."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
POLITENESS_SECONDS = 6.0
MAX_PAGES = 200


class CrawlError(Exception):
    """Raised when crawling cannot complete (network, HTTP, or unexpected structure)."""


@dataclass(frozen=True)
class CrawledPage:
    """One page: URL and plain text extracted for indexing."""

    url: str
    text: str


def _sleep_polite(last_request: float | None, sleep_fn: Callable[[float], None] = time.sleep) -> None:
    if last_request is None:
        return
    elapsed = time.monotonic() - last_request
    wait = POLITENESS_SECONDS - elapsed
    if wait > 0:
        sleep_fn(wait)


def _is_target_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and parsed.netloc == "quotes.toscrape.com"


def fetch_page(url: str, session: requests.Session) -> str:
    """GET url and return response text (HTML). Raise on HTTP errors."""
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_visible_text(html: str) -> str:
    """
    Prefer quote blocks on quotes.toscrape.com; fall back to whole-page text.

    Keeps author names and tags in the indexed stream so they remain searchable.
    """
    soup = BeautifulSoup(html, "html.parser")
    quotes = soup.select("div.quote")
    if quotes:
        chunks: list[str] = []
        for q in quotes:
            chunks.append(q.get_text(separator=" ", strip=True))
        return "\n".join(chunks)
    return soup.get_text(separator=" ", strip=True)


def discover_next_page_url(html: str, current_url: str) -> str | None:
    """Return absolute URL of 'Next' page if present."""
    soup = BeautifulSoup(html, "html.parser")
    li = soup.find("li", class_="next")
    if not li:
        return None
    a = li.find("a", href=True)
    if not a:
        return None
    return urljoin(current_url, a["href"])


def crawl_quotes_site(
    session: requests.Session | None = None,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
    max_pages: int = MAX_PAGES,
) -> list[CrawledPage]:
    """
    Crawl all pages under quotes.toscrape.com, waiting >= POLITENESS_SECONDS between requests.

    Only URLs on quotes.toscrape.com are followed. Network/HTTP failures raise CrawlError.
    """
    session = session or requests.Session()
    hdrs = getattr(session, "headers", None)
    if hdrs is not None:
        hdrs.setdefault(
            "User-Agent",
            "XJCO3011-Coursework2-SearchTool/1.0 (+educational crawler; polite delay)",
        )

    pages: list[CrawledPage] = []
    url: str | None = f"{BASE_URL}/"
    last_request_end: float | None = None

    if not _is_target_url(url):
        raise CrawlError(f"Start URL must be on quotes.toscrape.com: {url!r}")

    while url:
        if len(pages) >= max_pages:
            raise CrawlError(f"Stopped after {max_pages} pages (safety limit).")

        _sleep_polite(last_request_end, sleep_fn=sleep_fn)
        try:
            html = fetch_page(url, session)
        except requests.RequestException as exc:
            raise CrawlError(f"Request failed for {url!r}: {exc}") from exc

        last_request_end = time.monotonic()
        text = extract_visible_text(html)
        pages.append(CrawledPage(url=url, text=text))

        next_url = discover_next_page_url(html, url)
        if next_url is None:
            url = None
        elif not _is_target_url(next_url):
            raise CrawlError(f"Refusing to follow off-site URL: {next_url!r}")
        else:
            url = next_url

    return pages
