"""HTTP crawl of https://quotes.toscrape.com/ with politeness delay."""

from __future__ import annotations

import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
POLITENESS_SECONDS = 6.0
# Listing (~10) + many unique authors + tags; upper bound for safety.
MAX_PAGES = 500

# (1-based page count, page URL, extracted text length in characters)
CrawlProgressHook = Callable[[int, str, int], None]


class CrawlError(Exception):
    """Raised when crawling cannot complete (network, HTTP, or unexpected structure)."""


@dataclass(frozen=True)
class CrawledPage:
    """One page: URL and plain text extracted for indexing."""

    url: str
    text: str


def canonicalise_url(url: str) -> str:
    """Normalise scheme/host/path (no query/fragment) for de-duplication."""
    p = urlparse(url.strip())
    scheme = p.scheme if p.scheme in ("http", "https") else "https"
    netloc = (p.netloc or urlparse(BASE_URL).netloc).lower()
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def canonicalise_crawl_url(url: str) -> str:
    """
    URL identity for crawling and de-duplication.

    Tag first pages exist as both ``/tag/name`` and ``/tag/name/page/1`` (same content).
    We always use the ``/tag/name/page/1`` form so they are not indexed twice.
    """
    u = canonicalise_url(url)
    p = urlparse(u)
    path = p.path or "/"
    if re.fullmatch(r"/tag/[^/]+", path):
        new_path = f"{path}/page/1"
        u = urlunparse((p.scheme, p.netloc, new_path, "", "", ""))
        return canonicalise_url(u)
    return u


def is_allowed_crawl_path(path: str) -> bool:
    """
    Paths we index on quotes.toscrape.com:

    - ``/`` — quote listing home
    - ``/page/N`` — paginated listings
    - ``/author/Slug`` — author bios
    - ``/tag/name/page/N`` only for tags (``N>=1``); first page is always ``.../page/1``, never bare ``/tag/name``
    """
    p = path or "/"
    if p != "/" and p.endswith("/"):
        p = p.rstrip("/")
    if p == "/":
        return True
    if re.fullmatch(r"/page/\d+", p):
        return True
    if re.match(r"^/author/[^/]+$", p):
        return len(p) > len("/author/")
    if re.fullmatch(r"/tag/[^/]+/page/\d+", p):
        return True
    return False


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


def assert_pagination_next_on_site(html: str, current_url: str) -> None:
    """If the theme's ``Next`` pager points off-site, fail loudly (broken/malicious markup)."""
    soup = BeautifulSoup(html, "html.parser")
    li = soup.find("li", class_="next")
    if not li:
        return
    a = li.find("a", href=True)
    if not a:
        return
    nxt = urljoin(current_url, a["href"])
    if not _is_target_url(nxt):
        raise CrawlError(f"Refusing to follow off-site pagination: {nxt!r}")


def extract_discovered_urls(html: str, current_url: str) -> list[str]:
    """
    Collect same-host URLs linked from this page that we are allowed to crawl.

    Covers ``Next``, author links, tag links, and listing links discovered via ``<a href>``.
    """
    soup = BeautifulSoup(html, "html.parser")
    found: set[str] = set()
    for a in soup.find_all("a", href=True):
        raw = str(a.get("href", "")).strip()
        if not raw or raw.startswith("#") or raw.lower().startswith("javascript:"):
            continue
        abs_u = urljoin(current_url, raw)
        parsed = urlparse(abs_u)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _is_target_url(abs_u):
            continue
        canon = canonicalise_crawl_url(abs_u)
        path = urlparse(canon).path
        if is_allowed_crawl_path(path):
            found.add(canon)
    return sorted(found)


def fetch_page(url: str, session: requests.Session) -> str:
    """GET url and return response text (HTML). Raise on HTTP errors."""
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_visible_text(html: str) -> str:
    """
    Prefer main content regions on quotes.toscrape.com; fall back to whole-page text.

    - Listing pages: ``div.quote`` blocks
    - Author pages: ``div.author-description`` when present
    """
    soup = BeautifulSoup(html, "html.parser")
    quotes = soup.select("div.quote")
    if quotes:
        chunks = [q.get_text(separator=" ", strip=True) for q in quotes]
        return "\n".join(chunks)
    desc = soup.select_one("div.author-description")
    if desc:
        return desc.get_text(separator=" ", strip=True)
    return soup.get_text(separator=" ", strip=True)


def discover_next_page_url(html: str, current_url: str) -> str | None:
    """Return absolute URL of 'Next' page if present (same helper as theme pagination)."""
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
    progress_hook: CrawlProgressHook | None = None,
) -> list[CrawledPage]:
    """
    Breadth-first crawl of quotes.toscrape.com: listing pages, author pages, and tag pages.

    Discovers URLs from ``<a href>`` on each fetched page (same host, allow-listed paths only),
    with ``>= POLITENESS_SECONDS`` between successive HTTP requests.

    If ``progress_hook`` is set, it is called after each page is fetched and parsed as
    ``(page_number_1based, url, len(extracted_text))``.
    """
    if session is None:
        session = requests.Session()
        if os.environ.get("QUOTES_CRAWL_USE_PROXY", "").lower() not in ("1", "true", "yes"):
            session.trust_env = False
    hdrs = getattr(session, "headers", None)
    if hdrs is not None:
        hdrs.setdefault(
            "User-Agent",
            "XJCO3011-Coursework2-SearchTool/1.0 (+educational crawler; polite delay)",
        )

    start = canonicalise_url(f"{BASE_URL}/")
    if not _is_target_url(start):
        raise CrawlError(f"Start URL must be on quotes.toscrape.com: {start!r}")

    queue: deque[str] = deque([start])
    visited: set[str] = set()
    pages: list[CrawledPage] = []
    last_request_end: float | None = None

    while queue:
        if len(pages) >= max_pages:
            raise CrawlError(f"Stopped after {max_pages} pages (safety limit).")

        url = canonicalise_crawl_url(queue.popleft())
        if url in visited:
            continue
        visited.add(url)

        _sleep_polite(last_request_end, sleep_fn=sleep_fn)
        try:
            html = fetch_page(url, session)
        except requests.RequestException as exc:
            raise CrawlError(f"Request failed for {url!r}: {exc}") from exc

        assert_pagination_next_on_site(html, url)

        last_request_end = time.monotonic()
        text = extract_visible_text(html)
        page = CrawledPage(url=url, text=text)
        pages.append(page)
        if progress_hook is not None:
            progress_hook(len(pages), page.url, len(text))

        for nxt in extract_discovered_urls(html, url):
            c = canonicalise_crawl_url(nxt)
            if c not in visited:
                queue.append(c)

    return pages
