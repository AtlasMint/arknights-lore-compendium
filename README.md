# Arknights Lore Compendium

Drop in an Arknights story screenshot and get a map of the characters, factions and places it mentions, with how they connect, drawn from the [Arknights Terra Wiki](https://arknights.wiki.gg). Tick the stories you have read, and the map leaves out anything they haven't reached yet.

## Features

- **Screenshots in, keywords out:** a vision model on your own machine reads the speaker and the text, and you check the wiki terms it found before building the map. No API key. You can also type keywords.
- **A lore map:** the pages around your keywords, ranked by relevance. Shape shows what each is (operator, character, faction, place, event), and colour shows the main factions.
- **Details on click:** a summary that grows with the stories you have read, the wiki link, and labelled connections ("Talulah is the half-sister of Ch'en").
- **Spoiler-safe:** tick the stories you have read on a timeline of every story released on Global. Anything from later stories stays hidden, and an optional fog covers the timeline itself beyond the next story.
- **Several screenshots, one map:** each screenshot adds to the same session.

## Tech stack

Python with Flask, NetworkX and SQLite; React, Vite and D3; [Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-2B) models (Apache-2.0) served locally by [Ollama](https://ollama.com).

## Prerequisites

- Python 3.12 or newer
- [bun](https://bun.sh)
- [Ollama](https://ollama.com), with about 6 GB of disk for two models
- Internet access to arknights.wiki.gg

## Quick start

On macOS (Windows and Linux: see [docs/SETUP.md](docs/SETUP.md)):

```bash
git clone https://github.com/AtlasMint/arknights-lore-compendium.git
cd arknights-lore-compendium
python3 -m venv .venv
source .venv/bin/activate
WITH_EXTENSION=0 pip install -r requirements.txt

brew install ollama && brew services start ollama
ollama pull qwen3.5:2b    # reads screenshots
ollama pull qwen3.5:4b    # labels connections
```

Start both with `./scripts/start-app.sh` (Ctrl+C stops both), or by hand — the API, then the frontend in a second terminal:

```bash
python -m flask --app backend.app run --port 5001
```

```bash
cd frontend
bun install
bun run dev
```

Open http://localhost:5173, then:

1. Under **Stories read**, tick the stories you have finished.
2. Drop a story screenshot, or type a keyword.
3. Check the keyword chips, then **Build graph**.
4. Click a node to read about it.

The first build downloads the wiki's title index, which takes 1–2 minutes.

## Repository structure

```
backend/    Python: wiki client and cache, term index and keyword matcher, graph, labels, stories, Flask API
frontend/   React app: the lore map and the stories timeline
tests/      offline tests, and the labeled screenshot set with its scorer
docs/       guides below, version plans, and archive/ of finished versions with their outcome notes
data/       SQLite cache and progress.json, your ticks; created on first run, not committed
```

## Testing

```bash
python -m tests.test_v3     # likewise test_v0, test_v1, test_v2
cd frontend && bun test
```

See [docs/TESTING.md](docs/TESTING.md) for the screenshot scorer and CI. GitHub Actions runs the tests on Windows, macOS and Linux on every push.

## Documentation

- [Setup](docs/SETUP.md): install on every OS, the command line, settings, keeping data current, troubleshooting
- [How it works](docs/HOW-IT-WORKS.md): reading, keyword matching, the graph, labels, stories and spoiler control
- [API](docs/API.md): the HTTP endpoints
- [Testing](docs/TESTING.md): the tests, the screenshot scorer, CI
- [Roadmap](docs/ROADMAP.md): versions, past and planned
- [Commits](docs/COMMITS.md): commit message conventions

## References

- **Final Fantasy XVI's Active Time Lore**, the inspiration for the spoiler-safe map. Momoka Aono (Square Enix) presented it at GDC 2024 ([slides](https://media.gdcvault.com/gdc2024/Slides/GDC+slide+presentations/Aono_Momoka_DesigningActiveTime.pdf)). This project borrows its progress-based half: entries that grow as the story progresses, written from a narrator's view, with one dictionary feeding every view. The [v3 plan](docs/archive/v3-richer-lore.md#why-a-ticked-list-not-detection) records what was taken and what wasn't.
- **[Arknights Terra Wiki](https://arknights.wiki.gg)** on wiki.gg, the source of every page, link, summary, story teaser and Movement icon the app shows. Its text is under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), and the summaries and labels drawn from it are too.
- **[Arknights](https://www.arknights.global)**, by Hypergryph, published on the Global server by Yostar. The Movement icons are the game's artwork. This is an unofficial fan project, not affiliated with Hypergryph or Yostar.
- **[Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)** and **[Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)** by the Qwen team, under Apache-2.0, run locally through [Ollama](https://ollama.com).