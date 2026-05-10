"""Tests for crawler (mocks / HTML fixtures; no live network in default suite)."""

from unittest.mock import MagicMock

import pytest
import requests

from crawler import (
    POLITENESS_SECONDS,
    CrawlError,
    canonicalise_crawl_url,
    canonicalise_url,
    crawl_quotes_site,
    discover_next_page_url,
    extract_discovered_urls,
    extract_visible_text,
    fetch_page,
    is_allowed_crawl_path,
)


def test_politeness_between_requests(monkeypatch):
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    class FakeSession:
        def get(self, url, timeout=30):
            r = MagicMock()
            r.raise_for_status = MagicMock()
            if "page/2" not in url:
                r.text = (
                    '<html><body>hi</body>'
                    '<ul class="pager"><li class="next"><a href="/page/2/">Next</a></li></ul></html>'
                )
            else:
                r.text = "<html><body>bye</body></html>"
            return r

    times = iter([100.0, 100.05, 200.0])

    def fake_monotonic() -> float:
        return next(times)

    monkeypatch.setattr("crawler.time.monotonic", fake_monotonic)
    crawl_quotes_site(session=FakeSession(), sleep_fn=fake_sleep)
    assert len(sleeps) == 1
    assert sleeps[0] == pytest.approx(POLITENESS_SECONDS - 0.05)


def test_discover_next_absolute():
    html = '<li class="next"><a href="/page/2/">next</a></li>'
    assert discover_next_page_url(html, "https://quotes.toscrape.com/") == "https://quotes.toscrape.com/page/2/"


def test_extract_visible_prefers_quote_blocks():
    html = """
    <html><body>
      <div class="quote"><span class="text">OnlyQuote</span></div>
      <footer>FooterNoise</footer>
    </body></html>
    """
    text = extract_visible_text(html)
    assert "OnlyQuote" in text
    assert "FooterNoise" not in text


def test_crawl_refuses_off_site_next_link():
    class FakeSession:
        def get(self, url, timeout=30):
            r = MagicMock()
            r.raise_for_status = MagicMock()
            r.text = '<li class="next"><a href="https://evil.example/">bad</a></li>'
            return r

    with pytest.raises(CrawlError, match="off-site"):
        crawl_quotes_site(session=FakeSession(), sleep_fn=lambda s: None)


def test_crawl_request_error_wrapped():
    class BoomSession:
        def get(self, url, timeout=30):
            raise requests.ConnectionError("offline")

    with pytest.raises(CrawlError, match="Request failed"):
        crawl_quotes_site(session=BoomSession(), sleep_fn=lambda s: None)


def test_canonicalise_url_strips_trailing_slash_on_paths():
    assert canonicalise_url("https://quotes.toscrape.com/tag/love/") == "https://quotes.toscrape.com/tag/love"


def test_canonicalise_crawl_url_tag_first_page_uses_page_1():
    assert canonicalise_crawl_url("https://quotes.toscrape.com/tag/books") == (
        "https://quotes.toscrape.com/tag/books/page/1"
    )
    assert canonicalise_crawl_url("https://quotes.toscrape.com/tag/books/page/1") == (
        "https://quotes.toscrape.com/tag/books/page/1"
    )


def test_is_allowed_crawl_path():
    assert is_allowed_crawl_path("/")
    assert is_allowed_crawl_path("/page/2")
    assert is_allowed_crawl_path("/author/Albert-Einstein")
    assert is_allowed_crawl_path("/tag/change/page/1")
    assert is_allowed_crawl_path("/tag/humor/page/2")
    assert not is_allowed_crawl_path("/tag/change")
    assert not is_allowed_crawl_path("/tag/humor/extra")
    assert not is_allowed_crawl_path("/login")
    assert not is_allowed_crawl_path("/author")


def test_extract_discovered_urls_filters_paths():
    html = """
    <a href="/author/Albert-Einstein">a</a>
    <a href="/tag/love/">t</a>
    <a href="/page/2/">n</a>
    <a href="/tag/humor/page/2/">p</a>
    <a href="https://evil.example/x">e</a>
    <a href="/login">l</a>
    """
    u = extract_discovered_urls(html, "https://quotes.toscrape.com/")
    assert canonicalise_url("https://quotes.toscrape.com/author/Albert-Einstein") in u
    assert canonicalise_crawl_url("https://quotes.toscrape.com/tag/love") in u
    assert canonicalise_url("https://quotes.toscrape.com/page/2") in u
    assert canonicalise_url("https://quotes.toscrape.com/tag/humor/page/2") in u
    assert all("evil" not in x for x in u)
    assert all("login" not in x for x in u)


def test_fetch_page_uses_session(monkeypatch):
    captured: dict[str, str] = {}

    class S:
        def get(self, url, timeout=30):
            captured["url"] = url
            r = MagicMock()
            r.raise_for_status = MagicMock()
            r.text = "<html/>"
            return r

    fetch_page("https://quotes.toscrape.com/", S())
    assert captured["url"] == "https://quotes.toscrape.com/"
