"""Tests for crawler (mocks / HTML fixtures; no live network in default suite)."""

from unittest.mock import MagicMock

import pytest
import requests

from crawler import (
    POLITENESS_SECONDS,
    CrawlError,
    crawl_quotes_site,
    discover_next_page_url,
    extract_visible_text,
    fetch_page,
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
