"""Tests for search helpers."""

from crawler import CrawledPage
from indexer import Index, build_index
from search import find_pages, print_word, tokens_for_find_arguments


def _tiny_index() -> Index:
    return build_index(
        [
            CrawledPage(url="https://a.example", text="good friends"),
            CrawledPage(url="https://b.example", text="good enemies"),
        ]
    )


def test_find_and_semantics():
    idx = _tiny_index()
    assert find_pages(idx, ["good", "friends"]) == ["https://a.example"]
    assert find_pages(idx, ["good", "missing"]) == []


def test_find_empty_query():
    idx = _tiny_index()
    assert find_pages(idx, []) == []


def test_print_word_contains_urls():
    idx = _tiny_index()
    out = print_word(idx, "good")
    assert "https://a.example" in out
    assert "https://b.example" in out


def test_print_word_unknown():
    idx = _tiny_index()
    assert "no occurrences" in print_word(idx, "nope")


def test_tokens_for_find_arguments_joins_commas():
    assert tokens_for_find_arguments(["good,friends"]) == ["good", "friends"]
    assert tokens_for_find_arguments(["good", "friends"]) == ["good", "friends"]
