"""Query operations: print postings for one word; find pages matching multi-token AND queries."""

from __future__ import annotations

from typing import Any

from indexer import Index, normalise_token, tokenise


def _positions_as_ints(stats: dict[str, Any]) -> list[int]:
    raw = stats.get("positions", [])
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    for p in raw:
        try:
            out.append(int(p))
        except (TypeError, ValueError):
            continue
    return out


def _format_positions_display(positions: list[int], *, max_inline: int = 14) -> str:
    """Readable list of 0-based token positions; truncate very long lists."""
    if not positions:
        return "[]"
    if len(positions) <= max_inline:
        return str(positions)
    head = positions[:10]
    return f"{head} … ({len(positions)} positions total; truncated for display)"


def print_word(index: Index, word: str) -> str:
    """
    Pretty-print inverted index for one term with corpus- and document-level metrics.

    Aligns with the brief: statistics such as **frequency** and **position(s)** per page,
    plus aggregated **df** (document frequency) and corpus-wide occurrence counts for demos.
    """
    token = normalise_token(word)
    postings = index.postings.get(token)
    if not postings:
        return (
            f"{'─' * 58}\n"
            f"Inverted index lookup  term={token!r}\n"
            f"{'─' * 58}\n"
            "Corpus-level metrics:\n"
            "  • document frequency (df):     0 page(s)\n"
            "  • total term frequency (Σtf): 0 occurrence(s) in corpus\n"
            "  (no postings for this term)\n"
            f"{'─' * 58}"
        )

    doc_freq = len(postings)
    total_tf = 0
    for stats in postings.values():
        total_tf += int(stats.get("frequency", 0))

    avg_tf = total_tf / doc_freq if doc_freq else 0.0

    lines: list[str] = [
        f"{'=' * 58}",
        f"Inverted index entry  term={token!r}",
        f"{'=' * 58}",
        "",
        "Corpus-level metrics:",
        f"  • document frequency (df):      {doc_freq} page(s) contain this term",
        f"  • total term frequency (Σtf):     {total_tf} occurrence(s) summed over those pages",
        f"  • avg term frequency (among hits): {avg_tf:.3f}",
        "",
        "Per-page postings (structure: term → URL → {frequency, positions}):",
        "",
    ]

    for i, (url, stats) in enumerate(sorted(postings.items()), 1):
        freq = int(stats.get("frequency", 0))
        positions = _positions_as_ints(stats)
        pos_display = _format_positions_display(positions)
        first_p = min(positions) if positions else None
        last_p = max(positions) if positions else None
        span = (last_p - first_p + 1) if first_p is not None and last_p is not None else 0

        lines.append(f"  [{i}] {url}")
        lines.append(f"      tf (frequency on this page):     {freq}")
        lines.append(f"      positions (0-based in-page token index): {pos_display}")
        if first_p is not None:
            lines.append(
                f"      first / last position: {first_p} / {last_p}  |  span = {span} token slot(s)"
            )
        lines.append("")

    lines.append(
        "Note: positions follow the same token stream order produced by the indexer’s tokeniser."
    )
    lines.append(f"{'=' * 58}")
    return "\n".join(lines)


def find_pages(index: Index, query_tokens: list[str]) -> list[str]:
    """
    AND semantics: URLs that contain every query token at least once.

    query_tokens must be normalised tokens (use tokenise on user input first).
    """
    if not query_tokens:
        return []
    url_sets: list[set[str]] = []
    for t in query_tokens:
        urls = index.postings.get(t)
        if not urls:
            return []
        url_sets.append(set(urls.keys()))
    first, *rest = url_sets
    matched = first.intersection(*rest) if rest else first
    return sorted(matched)


def tokens_for_find_arguments(parts: list[str]) -> list[str]:
    """Turn CLI arguments after 'find' into a flat list of index tokens (order preserved)."""
    out: list[str] = []
    for p in parts:
        out.extend(tokenise(p))
    return out


def tokens_for_print_argument(parts: list[str]) -> list[str]:
    """Join remainder of line and tokenise; used so punctuation next to a word still matches."""
    return tokenise(" ".join(parts))
