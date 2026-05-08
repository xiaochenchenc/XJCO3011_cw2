"""Build, serialise, and deserialise inverted index (word -> per-page statistics)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crawler import CrawledPage

WORD_PATTERN = re.compile(r"[A-Za-z0-9']+")


def normalise_token(word: str) -> str:
    """Lowercase normalisation for case-insensitive search."""
    return word.lower()


def tokenise(text: str) -> list[str]:
    """
    Extract word-like tokens (letters, digits, apostrophe) for indexing and queries.

    Punctuation attached to words is stripped at token boundaries (e.g. 'hello,' -> hello).
    """
    return [normalise_token(m.group(0)) for m in WORD_PATTERN.finditer(text)]


@dataclass
class Index:
    """
    Inverted index: token -> { page_url: stats }.

    stats holds at least frequency and token positions within that page's token stream.
    """

    postings: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def add_page(self, page: CrawledPage) -> None:
        tokens = tokenise(page.text)
        for position, token in enumerate(tokens):
            by_url = self.postings.setdefault(token, {})
            stats = by_url.setdefault(page.url, {"frequency": 0, "positions": []})
            stats["frequency"] = int(stats["frequency"]) + 1
            stats["positions"].append(position)

    def to_json_dict(self) -> dict[str, Any]:
        return {"version": 1, "postings": self.postings}

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "Index":
        return cls(postings=data.get("postings", {}))


def build_index(pages: list[CrawledPage]) -> Index:
    index = Index()
    for p in pages:
        index.add_page(p)
    return index


def save_index(index: Index, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index.to_json_dict(), indent=2), encoding="utf-8")


def load_index(path: Path) -> Index:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read index file: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid index JSON: {exc}") from exc
    if not isinstance(data, dict) or "postings" not in data:
        raise ValueError("Index file is missing a 'postings' object.")
    postings = data.get("postings")
    if not isinstance(postings, dict):
        raise ValueError("Index 'postings' must be a JSON object.")
    return Index.from_json_dict(data)
