"""Interactive CLI: build, load, print <word>, find <words...>."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python src/main.py` from repo root without PYTHONPATH.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from crawler import CrawlError, crawl_quotes_site  # noqa: E402
from indexer import build_index, load_index, save_index, tokenise  # noqa: E402
from search import find_pages, print_word, tokens_for_find_arguments, tokens_for_print_argument  # noqa: E402

DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[1] / "data" / "index.json"


def _usage_hint() -> str:
    return "Commands: build | load | print <word> | find <word> [<word> ...] | quit"


def run_shell(index_path: Path = DEFAULT_INDEX_PATH) -> None:
    index = None
    print(_usage_hint())
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        if cmd in ("quit", "exit"):
            break
        if cmd == "build":
            print("Crawl log (politeness ≥6s between requests):")
            try:

                def _progress(n: int, url: str, n_chars: int) -> None:
                    print(f"  [{n:>3}] {url}")
                    print(f"        extracted text: {n_chars} character(s)")

                pages = crawl_quotes_site(progress_hook=_progress)
            except CrawlError as exc:
                print(f"Crawl failed: {exc}")
                continue
            print()
            print("Indexed page list (same order as crawl):")
            for i, p in enumerate(pages, 1):
                n_tokens = len(tokenise(p.text))
                print(f"  {i:>3}. {p.url}")
                print(f"        token count (after tokenisation): {n_tokens}")
            print()
            index = build_index(pages)
            try:
                save_index(index, index_path)
            except OSError as exc:
                print(f"Could not save index: {exc}")
                continue
            print(f"Indexed {len(pages)} page(s); wrote {index_path}")
        elif cmd == "load":
            if not index_path.is_file():
                print(f"No index file at {index_path}; run build first.")
                continue
            try:
                index = load_index(index_path)
            except ValueError as exc:
                print(f"Failed to load index: {exc}")
                continue
            print(f"Loaded index from {index_path}")
        elif cmd == "print":
            if index is None:
                print("No index in memory; run load or build first.")
                continue
            if len(parts) < 2:
                print("Usage: print <word>")
                continue
            q_tokens = tokens_for_print_argument(parts[1:])
            if not q_tokens:
                print("(no indexable word in input; use letters, digits, or apostrophe inside words)")
                continue
            if len(q_tokens) > 1:
                print(f"(print shows one term; using {q_tokens[0]!r})")
            print(print_word(index, q_tokens[0]))
        elif cmd == "find":
            if index is None:
                print("No index in memory; run load or build first.")
                continue
            if len(parts) < 2:
                print("Usage: find <word> [<word> ...]")
                continue
            q_tokens = tokens_for_find_arguments(parts[1:])
            if not q_tokens:
                print("(empty query after removing punctuation; add at least one word)")
                continue
            urls = find_pages(index, q_tokens)
            if not urls:
                print("(no pages)")
            else:
                print(f"Matched {len(urls)} page(s) (AND over {len(q_tokens)} term(s): {q_tokens}):")
                for u in urls:
                    print(f"  {u}")
        else:
            print(f"Unknown command: {cmd!r}. {_usage_hint()}")


def main() -> None:
    run_shell()


if __name__ == "__main__":
    main()
