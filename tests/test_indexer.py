"""Tests for indexer."""

import json
from pathlib import Path

import pytest

from crawler import CrawledPage
from indexer import Index, build_index, load_index, normalise_token, save_index, tokenise


def test_normalise_case_insensitive():
    assert normalise_token("Good") == "good"


def test_tokenise_splits_and_strips_punctuation():
    assert tokenise("a B c") == ["a", "b", "c"]
    assert tokenise("Hello, world!") == ["hello", "world"]
    assert tokenise("don't") == ["don't"]


def test_build_and_roundtrip(tmp_path: Path):
    pages = [
        CrawledPage(url="https://example.com/a", text="hello world"),
        CrawledPage(url="https://example.com/b", text="world cup"),
    ]
    idx = build_index(pages)
    path = tmp_path / "idx.json"
    save_index(idx, path)
    loaded = load_index(path)
    assert "hello" in loaded.postings
    assert loaded.postings["world"]["https://example.com/a"]["frequency"] == 1


def test_positions_recorded():
    idx = build_index([CrawledPage(url="https://x.example", text="spam eggs spam")])
    spam = idx.postings["spam"]["https://x.example"]
    assert spam["frequency"] == 2
    assert spam["positions"] == [0, 2]


def test_load_index_rejects_bad_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid index JSON"):
        load_index(bad)


def test_load_index_rejects_missing_postings(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        load_index(p)
