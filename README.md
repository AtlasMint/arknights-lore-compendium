# arknights-lore-compendium
Gets the Arknights wiki and builds a network graph of characters, factions, and lore terms connected to a set of keywords.

## Features

- Type seed terms (e.g. `Amiya, Reunion`) and get the lore pages around them: links followed 2 hops out, weighted, and pruned to the 150 most relevant with PageRank that restarts at the seeds.
- A term index of every wiki page title and redirect, so any name or alternate name resolves to its page (`Reunion Movement` → `Reunion`).
- Operator pages are gameplay stats, so their lore comes from the `/Story` and `/File` subpages. Stages, mechanics, items, staff and media pages are filtered out by wiki category.
- Fetched pages are cached in SQLite for 7 days. A cold build takes about 8 seconds, a repeat under 1 second.
- A CLI, a Flask JSON API, and a React + D3 force graph (drag, zoom, seeds highlighted).

## Tech stack

- **Data:** MediaWiki API of the [Arknights Terra Wiki](https://arknights.wiki.gg) (wiki.gg)
- **Backend:** Python, Flask, `mwparserfromhell`, NetworkX (+ SciPy for PageRank), SQLite
- **Frontend:** React 19, Vite 8, D3 7, with bun as the package manager

## Prerequisites

- Windows, macOS or Linux
- Python 3.12 or newer
- [bun](https://bun.sh) for the frontend
- Internet access to arknights.wiki.gg

## Quick start

Install on macOS or Linux:

```bash
git clone https://github.com/AtlasMint/arknights-lore-compendium.git
cd arknights-lore-compendium
python3 -m venv .venv
source .venv/bin/activate
WITH_EXTENSION=0 pip install -r requirements.txt
```

Install on Windows (PowerShell):

```powershell
git clone https://github.com/AtlasMint/arknights-lore-compendium.git
cd arknights-lore-compendium
py -m venv .venv
.venv\Scripts\Activate.ps1
$env:WITH_EXTENSION = "0"; pip install -r requirements.txt
```

`WITH_EXTENSION=0` lets pip install `mwparserfromhell` without a C compiler where it has no prebuilt wheel (Python 3.14, Windows on ARM). It then uses its pure-Python parser, which is about 1.5× slower and still under a second per graph. Where a wheel exists, the setting does nothing.

Then, on any OS, with the venv active:

```bash
# Term index: every title and redirect, about 1-2 minutes. The first graph build runs this if you skip it.
python -m backend.index.build_index

# Command line
python -m backend.cli --seeds "Amiya,Reunion" --depth 2
python -m backend.cli --lookup "Reunion Movement"

# Web UI: the API in one terminal...
python -m flask --app backend.app run --port 5001
# ...and the frontend in another, then open http://localhost:5173
cd frontend
bun install
bun run dev
```

Settings (wiki URL, depth, max nodes, request delay, cache expiry, edge weights) live in `backend/config.py`. Rerun `build_index` now and then to pick up new wiki pages.

Platform notes:

- **Windows:** if PowerShell won't run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- **Debian and Ubuntu:** if creating the venv fails, run `sudo apt install python3-venv`.
- **macOS with the python.org installer:** if wiki requests fail with `CERTIFICATE_VERIFY_FAILED`, run `Install Certificates.command` from the Python folder in Applications.
- **Port 5001** is used because macOS AirPlay holds 5000. To use another port, change it in the `flask` command and in `frontend/vite.config.js`.

## API endpoints

`GET /graph?seeds=Amiya,Reunion&depth=2` returns:

```json
{"nodes": [{"id": "Amiya", "seed": true, "score": 0.144, "categories": ["5-star", "Amiya", "Caster", "Core Caster", "Rhodes Island"]}, ...],
 "links": [{"source": "Kal'tsit", "target": "Amiya", "weight": 59}, ...]}
```

It takes 1–10 comma-separated seeds and a depth from 1 to 3. Seeds that aren't wiki pages or redirects get a 400 with `{"error": "Not on the wiki: ..."}`.

## Repository structure

```
backend/    engine: scraper/ (wiki API + cache), parser/, index/ (term index), graph/, cli.py, app.py (Flask), config.py
frontend/   React + Vite + D3 force graph
tests/      offline test of the engine
docs/       per-version plans
data/       SQLite page cache and term index (created on first run, not committed)
```

## Testing

```bash
python -m tests.test_v0
```

The test runs against a small fake wiki, so it needs no network.

## CI

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every push and pull request. It runs the test on Windows, macOS and Linux with Python 3.12 and 3.14, and lints and builds the frontend on all three. CI never calls the wiki.

# Roadmap

Arknights Lore Compendium turns a game screenshot into a map of connected lore.

## The pipeline

Think of it like a military intelligence chain: a recon photo comes in, an analyst reads it, the findings get checked against a known order of battle, and a situation map gets drawn.

```
Screenshot
   │
   ▼
[1] Read text      → vision model / OCR pulls dialog + speaker name
   │
   ▼
[2] Find keywords  → match text against a list of all wiki page titles
   │
   ▼
[3] Build network  → follow wiki links outward, build a weighted graph
   │
   ▼
[4] Show it        → React + D3 force graph, found keywords highlighted
```

## The key idea: a term index

Before touching screenshots, we download every wiki page title plus its redirects (alternate names that point to the same page). That list is the answer key. The system never guesses whether a word "sounds important"; it only asks whether the word is a real wiki page. This filters out OCR mistakes and made-up terms, and redirects cover nicknames and alternate spellings.

## Versions

| Version | Theme | Outcome |
|---|---|---|
| [v0](docs/v0-foundation.md) | Foundation | Type keywords, get a graph |
| [v1](docs/v1-screenshot-mvp.md) | Screenshot MVP | Upload a screenshot, get a graph |
| [v2](docs/v2-accuracy.md) | Accuracy | Keywords are right without manual fixes |
| [v3](docs/v3-richer-lore.md) | Richer lore | Labeled, spoiler-safe lore maps |
| [v4](docs/v4-polish-and-reach.md) | Polish and reach | Deployed, shareable, multi-server |

## Planned stack

| Layer | Choice |
|---|---|
| Data source | MediaWiki API ([Arknights Terra Wiki](https://arknights.wiki.gg) on wiki.gg, chosen in v0) |
| Wikitext parsing | `mwparserfromhell` |
| Text from images | Gemini Flash (v1), PaddleOCR as an alternative (v2) |
| Term matching | Exact match (v1), `rapidfuzz` fuzzy match (v2) |
| Graph | NetworkX |
| Cache / index | SQLite |
| Backend | Flask |
| Frontend | React + Vite + D3.js |

## Order of work

v0 and the term index come first, since everything else depends on them. v1 is mostly wiring existing parts together. v2 is where the real tuning happens, and the labeled screenshot test set is what tells you whether each change actually helped.