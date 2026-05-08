"""Query operations: print postings for one word; find pages matching multi-token AND queries."""

from __future__ import annotations

from indexer import Index, normalise_token, tokenise


def print_word(index: Index, word: str) -> str:
    """Pretty-print inverted postings for one index token (already normalised alphanumerically)."""
    token = normalise_token(word)
    postings = index.postings.get(token)
    if not postings:
        return f"(no occurrences) {token!r}"
    lines = [f"{token!r}:"]
    for url, stats in sorted(postings.items()):
        lines.append(f"  {url}  {stats}")
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
