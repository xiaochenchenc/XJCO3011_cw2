# Coursework 2: Search Engine Tool

Small Python CLI that crawls [quotes.toscrape.com](https://quotes.toscrape.com/), builds an inverted index with per-page statistics, and supports `print` / `find` queries (case-insensitive). Politeness delay between HTTP requests: **≥ 6 seconds**.

## Setup

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the interactive shell

From the repository root:

```bash
python src/main.py
```

Example session:

```text
> build
> load
> print nonsense
> find good friends
> quit
```

The default index file path is `data/index.json` (created by `build`).

## Tests

```bash
pytest
```

## Behaviour notes

- **Politeness:** at least **6 seconds** between finishing one HTTP request and starting the next.
- **Host safety:** only `https://quotes.toscrape.com` URLs are followed; off-site “Next” links raise a clear error.
- **Tokenisation:** words are letters, digits, and apostrophes (e.g. `don't`); punctuation is stripped at boundaries for `print` / `find`.
- **`find`:** all arguments are tokenised; multiple tokens use **AND** (page must contain every term).

## Layout

- `src/crawler.py` — HTTP crawl and HTML text extraction  
- `src/indexer.py` — tokenise, build/save/load inverted index  
- `src/search.py` — `print` and `find` logic  
- `src/main.py` — interactive CLI loop  
- `tests/` — pytest suite (`pythonpath` is set in `pytest.ini`)

## Dependencies

See `requirements.txt` (`requests`, `beautifulsoup4`, `pytest`).
