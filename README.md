# Coursework 2: Search Engine Tool

**Module:** XJCO3011 — Web Services and Web Data  
**Assessment:** Individual practical project
**Name:** Cao Yuchen
**Leeds ID:** 201690931
**SWJTU ID:** 2022115980

## Submission checklist

1. **Video link**: 
2. **GitHub repository URL**: https://github.com/xiaochenchenc/XJCO3011_cw2 

This repository implements a **Python command-line search tool** for the target site **[quotes.toscrape.com](https://quotes.toscrape.com/)**. It crawls allowed pages on that host, builds an **inverted index** with per-page statistics (**term frequency** and **token positions**, as required by the brief), saves the index to a **single JSON file**, and supports **case-insensitive** `print` and `find` operations. Successive HTTP requests respect a **politeness window of at least 6 seconds**.

---

## 1. Project overview and purpose

| Goal | Description |
|------|-------------|
| **Crawl** | Breadth-first crawl of `quotes.toscrape.com`: quote **listings** (`/` and `/page/N`), **author** pages (`/author/...`), and **tag** listings (`/tag/name/page/N`). Bare `/tag/name` links are normalised to `/tag/name/page/1` to avoid duplicate documents. Only the target host is followed; off-site pagination raises an error. |
| **Index** | While processing each page, the tool builds an inverted index: *token → URL →* `{ frequency, positions }`, where `positions` are 0-based indices in that page’s token stream. |
| **Search** | Interactive shell commands **`build`**, **`load`**, **`print`**, and **`find`** (see §4). |
| **Output** | Default compiled index path: **`data/index.json`**. |

**Suggested libraries (per assessment brief):** [Requests](https://docs.python-requests.org/) for HTTP, [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) for HTML parsing.

---

## 2. Requirements

- **Python 3.10+**
- Network access to `https://quotes.toscrape.com` when running **`build`**.
- **`build` runtime:** the crawler waits **≥ 6 seconds** between requests, so a full crawl may take **many minutes** (many pages after including authors and tags).

---

## 3. Installation and setup

### 3.1 Clone and enter the project root

You must run commands from the directory that contains `src/`, `tests/`, `data/`, and `requirements.txt`.

```bash
cd path/to/cw2
```

*(On Windows, if the path contains spaces, use quotes or `Set-Location -LiteralPath "..."` in PowerShell.)*

### 3.2 Virtual environment (recommended, not mandatory)

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd):**

```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

You may instead use your **Anaconda base** or another interpreter; ensure you install dependencies into **that** same environment (see §5).

---

## 4. Dependencies and how to install them

| Package | Role |
|---------|------|
| **requests** | HTTP client for crawling |
| **beautifulsoup4** | HTML parsing |
| **pytest** | Test runner |

Install pinned minimum versions from **`requirements.txt`**:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
requests>=2.31.0
beautifulsoup4>=4.12.0
pytest>=8.0.0
```

---

## 5. How to run the tool

From the **repository root**:

```bash
python src/main.py
```

You will see a short usage line and a **`>`** prompt. Type one command per line.

**Exit:** `quit` or `exit`, or press **Ctrl+C** / **Ctrl+Z** (EOF) depending on your OS.

---

## 6. Usage examples for all four commands

Below, lines starting with **`>`** are what you type; other lines are illustrative program output.

### 6.1 `build`

**Purpose:** Crawl the site, build the inverted index in memory, and save it to **`data/index.json`**.

```text
> build
```

Expected behaviour:

- A **crawl log** (each fetched URL and length of extracted text).
- A **summary** of every indexed URL with **token counts** after tokenisation.
- Message confirming the number of pages and the path to the saved index.

*First-time setup:* ensure the `data/` folder exists or can be created; the program writes `data/index.json`.

---

### 6.2 `load`

**Purpose:** Load a previously saved index from disk into memory. Use this after restarting the program, or to demonstrate loading without re-crawling.

**Prerequisite:** `data/index.json` must exist (run **`build`** once first).

```text
> load
```

Expected behaviour: confirmation that the index was loaded from `data/index.json` (or an error if the file is missing or invalid JSON).

---

### 6.3 `print`

**Purpose:** Print the **inverted index entry** for one word: corpus-level metrics (**df**, **Σtf**, average among hit pages) and **per-URL** **tf**, **positions**, and span information, as required by the brief’s statistics (e.g. frequency, position).

**Prerequisite:** run **`build`** or **`load`** first so an index is in memory.

```text
> print nonsense
```

Example aligned with the assessment brief (`> print nonsense`):

```text
> print nonsense
```

If the word does not occur, the tool reports zero document frequency and no postings.

**Note:** `print` is defined for **one search term** at a time. If you type several tokens, the tool uses the **first** indexable token and may show a short notice.

---

### 6.4 `find`

**Purpose:** List **all page URLs** that contain the query terms. **Multiple words use AND semantics:** every term must appear on the page (order does not matter). Matching is **case-insensitive**.

**Prerequisite:** run **`build`** or **`load`** first.

**Single word (as in the brief):**

```text
> find indifference
```

**Multi-word AND (as in the brief):**

```text
> find good friends
```

The tool tokenises arguments (punctuation around words is stripped consistently with indexing). Example with punctuation on one argument:

```text
> find good, friends
```

*(Equivalent to finding pages that contain both `good` and `friends`.)*

If no page matches, the tool prints `(no pages)` and may summarise the query.

---

## 7. Full example session (copy-paste style)

```text
> build
   … crawl log and summary …
> load
Loaded index from …\data\index.json
> print change
   … inverted index report …
> find world life
Matched N page(s) (AND over 2 term(s): ['world', 'life']):
  https://quotes.toscrape.com/…
> quit
```

---

## 8. Testing instructions

Tests live under **`tests/`** and follow the brief’s naming: `test_crawler.py`, `test_indexer.py`, `test_search.py`. **`pytest.ini`** sets `pythonpath = src` so imports match the project layout.

From the **repository root**, with dependencies installed:

```bash
python -m pytest
```

Quiet summary:

```bash
python -m pytest -q
```

Run a single file:

```bash
python -m pytest tests/test_crawler.py
```

All tests should pass before submission.

---

## 9. Repository layout (per assessment brief)

```text
repository-root/
  src/
    crawler.py
    indexer.py
    search.py
    main.py
  tests/
    test_crawler.py
    test_indexer.py
    test_search.py
  data/
    index.json          ← produced by `build` (submit for coursework)
  requirements.txt
  README.md
  pytest.ini
```

---

## 10. Troubleshooting

### 10.1 `build` fails with `ProxyError`

`requests` may pick up **`HTTP_PROXY` / `HTTPS_PROXY`** or a broken system proxy. By default this project uses a `requests.Session` with **`trust_env=False`** so **environment proxy variables are ignored** and the client connects **directly** to `quotes.toscrape.com`.

- To **force use of environment proxies** (e.g. corporate network): set **`QUOTES_CRAWL_USE_PROXY=1`** before running.
- To clear proxies for one **PowerShell** session:

```powershell
Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy -ErrorAction SilentlyContinue
```

### 10.2 `python` not found

Try **`py -3`** (Windows launcher) or ensure Python is on your `PATH`.

---