# arknights-lore-compendium
Gets the Arknights wiki and builds a network graph of characters, factions, and lore terms connected to a set of keywords, typed in or read from a game screenshot.

## Features

- Upload a story screenshot (dialog, story log, a choice, or a chapter menu): an open vision model running on your machine reads the speaker and the text on screen, the term index picks out the wiki pages they name, and you review those keywords as chips before building the graph.
- Or type seed terms (e.g. `Amiya, Reunion`) and get the lore pages around them: links followed 1 hop out by default (up to 3), weighted, and pruned to the 150 most relevant with PageRank that restarts at the seeds.
- A term index of every wiki page title and redirect, so any name or alternate name resolves to its page (`Reunion Movement` → `Reunion`).
- Operator pages are gameplay stats, so their lore comes from the `/Story` and `/File` subpages. Stages, mechanics, items, staff and media pages are filtered out by wiki category.
- Fetched pages are cached in SQLite for 7 days. A cold build takes about 8 seconds, a repeat under 1 second.
- A CLI, a Flask JSON API, and a React + D3 force graph (drag, zoom, seeds highlighted).
- Each screenshot is read once: readings are cached by the image's SHA-256, so uploading it again is instant.

## Tech stack

- **Data:** MediaWiki API of the [Arknights Terra Wiki](https://arknights.wiki.gg) (wiki.gg)
- **Backend:** Python, Flask, `mwparserfromhell`, NetworkX (+ SciPy for PageRank), SQLite
- **Screenshots:** [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) (Apache-2.0), served on your machine by [Ollama](https://ollama.com) and called over REST with the standard library
- **Frontend:** React 19, Vite 8, D3 7, with bun as the package manager

## Prerequisites

- Windows, macOS or Linux
- Python 3.12 or newer
- [bun](https://bun.sh) for the frontend
- Internet access to arknights.wiki.gg
- [Ollama](https://ollama.com), for screenshots only, with about 3 GB of disk for the model

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

For screenshots, install Ollama and pull the model (2.7 GB). On macOS:

```bash
brew install ollama && brew services start ollama
ollama pull qwen3.5:2b
```

On Windows, `winget install Ollama.Ollama`; on Linux, `curl -fsSL https://ollama.com/install.sh | sh`. Then `ollama pull qwen3.5:2b` on either. Ollama keeps running in the background, and the model loads on the first screenshot.

Then, on any OS, with the venv active:

```bash
# Term index: every title and redirect, about 1-2 minutes. The first graph build runs this if you skip it.
python -m backend.index.build_index

# Command line
python -m backend.cli --seeds "Amiya,Reunion" --depth 1
python -m backend.cli --lookup "Reunion Movement"

# Web UI: the API in one terminal...
python -m flask --app backend.app run --port 5001
# ...and the frontend in another, then open http://localhost:5173
cd frontend
bun install
bun run dev
```

Settings (wiki URL, depth, max nodes, request delay, cache expiry, edge weights, reader model, upload size limit) live in `backend/config.py`. Rerun `build_index` now and then to pick up new wiki pages.

Platform notes:

- **Windows:** if PowerShell won't run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- **Debian and Ubuntu:** if creating the venv fails, run `sudo apt install python3-venv`.
- **macOS with the python.org installer:** if wiki requests fail with `CERTIFICATE_VERIFY_FAILED`, run `Install Certificates.command` from the Python folder in Applications.
- **Port 5001** is used because macOS AirPlay holds 5000. To use another port, change it in the `flask` command and in `frontend/vite.config.js`.

## API endpoints

`GET /graph?seeds=Amiya,Reunion&depth=1&speaker=Amiya` returns:

```json
{"nodes": [{"id": "Amiya", "seed": true, "score": 0.144, "categories": ["5-star", "Amiya", "Caster", "Core Caster", "Rhodes Island"]}, ...],
 "links": [{"source": "Kal'tsit", "target": "Amiya", "weight": 59}, ...]}
```

It takes 1–10 comma-separated seeds and a depth from 1 to 3 (default 1). `speaker` is optional: when it is one of the seeds, that seed gets three times the others' share of the PageRank restart, so the map leans toward whoever was talking. Seeds that aren't wiki pages or redirects get a 400 with `{"error": "Not on the wiki: ..."}`.

`POST /analyze` takes a multipart form with one `image` field (PNG, JPEG or WebP, up to 10 MB). The frontend scales screenshots to 1280 px on the long side before uploading, since the reader's time grows with pixels: a phone screenshot went from 19 s to 5 s with the text still legible. It returns:

```json
{"speaker": "Amiya", "text": "Doctor, the Reunion Movement has taken Chernobog.",
 "keywords": ["Amiya", "Reunion", "Chernobog"], "needs_context": ["Doctor"], "guesses": {"Chernobog": "Chernobug"}}
```

The reader is asked for all the story text on screen, so the lines of a story log, the options of a choice and the cards of a chapter menu count too. `keywords` are wiki pages named by the speaker or written capitalized in the text. `needs_context` holds matches written in lower case (`the silence here`) and `Doctor`, which could be ordinary words; the UI shows them unselected. Capitalized words that matched nothing get a second look. A word that is a gameplay title (a class, a term, a disambiguation) offers the lore pages that qualify it: a disambiguation's targets as keywords (`Nightzmora` → Nightzmora (country) and Nightzmora (race)), a class's namesake under `needs_context` (`Guard` → Guard (NPC), since Guard is usually the class). Any other word of five or more letters is tried as a demonym or plural (`Tarans` → Tara), then as a misreading, compared with every title using `difflib` and accepted at 0.85 similarity or better (`Dublinl` → Dublinn), then as one word of a character, place or group that only one such page starts or ends with (`Candela` → Candela Sanchez, `Hillock` → County Hillock). Ordinary words that happen to start or end such a page (County, Palace, Island) are listed in the matcher and never count. `guesses` lists the keywords found that way, with the word as read, and the UI draws those chips dotted, with the word in the tooltip. The file type is checked from its bytes, not its name. A wrong type gets a 415, an oversized file a 413, and a failed read (Ollama not running, model not pulled) a 502, each with an `error` message.

`GET /terms?prefix=kal` returns up to 10 titles and redirects starting with the prefix, for autocomplete: `["Kal", "Kal'tsit", ...]`.

## Repository structure

```
backend/    engine: scraper/ (wiki API + cache), parser/, index/ (term index, keyword matcher), graph/, vision/ (screenshot reading), cli.py, app.py (Flask), config.py
frontend/   React + Vite + D3 force graph
tests/      offline tests, one per version, plus the labeled screenshot set and its scorer
docs/       plans for versions still to build; archive/ holds the finished ones with their outcome notes
data/       SQLite page cache, term index and screenshot readings (created on first run, not committed)
```

## Testing

```bash
python -m tests.test_v0
python -m tests.test_v1
python -m tests.test_v2
```

All three run against a small fake wiki, and `test_v1` stubs the reader, so they need no network and no Ollama.

```bash
python -m tests.score_screenshots
```

This one needs Ollama. It runs the 28 labeled screenshots in `tests/screenshots/` through the reader and matcher and prints, per screenshot, whether the speaker was read right, how close the text came, and the chip edits a user would still have to make (keywords missed, parked under needs-context, or extra), then the totals. `labels.json` holds each screenshot's speaker, text and expected keywords. Readings go through the cache, so a rerun with nothing changed is instant. The committed images are 1280 px copies, the size the frontend uploads; full-size originals can sit in `tests/screenshots/originals/`, which git ignores.

## CI

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every push and pull request. It runs the tests on Windows, macOS and Linux with Python 3.12 and 3.14, and lints and builds the frontend on all three. CI never calls the wiki or Ollama.

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

Before touching screenshots, we download every wiki page title plus its redirects (alternate names that point to the same page). That list is the answer key. The system never guesses whether a word "sounds important"; it only asks whether the word is a real wiki page. This filters out OCR mistakes and made-up terms, and redirects cover nicknames and alternate spellings. Gameplay pages (stages, mechanics, items, furniture, base skills, music) are filtered out by category, so the index holds about 1,400 lore pages: characters, places, factions, races and stories.

## Versions

| Version | Theme | Outcome |
|---|---|---|
| [v0](docs/archive/v0-foundation.md) | Foundation | Type keywords, get a graph |
| [v1](docs/archive/v1-screenshot-mvp.md) | Screenshot MVP | Upload a screenshot, get a graph |
| [v1.1](docs/archive/v1.1-local-reader.md) | Local reader | Screenshots read by an open model on your machine, no API key |
| [v2](docs/archive/v2-accuracy.md) | Accuracy | 26 of 28 real screenshots need no chip edits, from 12 |
| [v3](docs/v3-richer-lore.md) | Richer lore | Labeled, spoiler-safe lore maps |
| [v4](docs/v4-polish-and-reach.md) | Polish and reach | Deployed, shareable, multi-server |
| [v5](docs/v5-recall.md) | Recall | What changed when, searchable, replayable by chapter |

## Planned stack

| Layer | Choice |
|---|---|
| Data source | MediaWiki API ([Arknights Terra Wiki](https://arknights.wiki.gg) on wiki.gg, chosen in v0) |
| Wikitext parsing | `mwparserfromhell` |
| Text from images | Qwen3.5-2B through Ollama (v1.1) |
| Term matching | Exact match (v1); demonyms, `difflib` fuzzy match and partial names (v2) |
| Graph | NetworkX |
| Cache / index | SQLite |
| Backend | Flask |
| Frontend | React + Vite + D3.js |

## Order of work

v0 and the term index come first, since everything else depends on them. v1 is mostly wiring existing parts together. v2 is where the real tuning happens, and the labeled screenshot test set is what tells you whether each change actually helped.