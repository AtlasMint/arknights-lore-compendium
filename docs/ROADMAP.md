# Roadmap

Arknights Lore Compendium turns a game screenshot into a map of connected lore. Each version starts as a plan in `docs/`. A finished one moves to [archive/](archive/) with notes on what was actually built and measured.

## Versions

| Version | Theme | Outcome |
|---|---|---|
| [v0](archive/v0-foundation.md) | Foundation | Type keywords, get a graph |
| [v1](archive/v1-screenshot-mvp.md) | Screenshot MVP | Upload a screenshot, get a graph |
| [v1.1](archive/v1.1-local-reader.md) | Local reader | Screenshots read by an open model on your machine, no API key |
| [v2](archive/v2-accuracy.md) | Accuracy | 26 of 28 real screenshots need no chip edits, from 12 |
| [v3](archive/v3-richer-lore.md) | Richer lore | Labeled, spoiler-safe lore maps from a list of stories read |
| [v3.1](archive/v3.1-sourced-summaries.md) | Sourced summaries | Every summary sentence gated on the story that told it |
| [v4](v4-polish-and-reach.md) | Polish and reach | Deployed, shareable, multi-server |
| [v5](v5-recall.md) | Recall | What changed when, searchable, replayable by chapter |

## Stack, by version

| Layer | Choice |
|---|---|
| Data source | MediaWiki API ([Arknights Terra Wiki](https://arknights.wiki.gg) on wiki.gg, chosen in v0) |
| Wikitext parsing | `mwparserfromhell` |
| Text from images | Qwen3.5-2B through Ollama (v1.1) |
| Relationship labels | Qwen3.5-4B through Ollama (v3) |
| Term matching | Exact match (v1); demonyms, `difflib` fuzzy match and partial names (v2) |
| Graph | NetworkX |
| Cache / index | SQLite |
| Backend | Flask |
| Frontend | React + Vite + D3.js |

## Order of work

v0 and the term index came first, since everything else depends on them. v1 was mostly wiring existing parts together. v2 is where the real tuning happened, and the labeled screenshot set is what says whether a change actually helped.
