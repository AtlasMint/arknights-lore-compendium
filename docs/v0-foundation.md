# v0: Foundation

**Theme:** keyword → graph
**Outcome:** type a few keywords, get back a sensible lore network.
**Status:** built 2026-09-29. All tasks are done; the fan check under "Done when" is still open. See [Outcome notes](#outcome-notes).

## Goal

Build the core engine that every later version feeds into. No screenshots yet: seed keywords are typed in by hand. Also build the term index, which v1 onward uses to recognize real lore terms.

## Why this comes first

The screenshot features are just a new way to produce seed keywords. If the graph engine is solid, everything after it is mostly plumbing. If it isn't, better OCR won't save it.

## Tasks

### Setup
- [x] Repo skeleton (`backend/`, `frontend/`, `data/`, `tests/`, `notebooks/`)
- [x] Python venv + `requirements.txt`
- [x] `config.py` for wiki URL, depth, max nodes, request delay
- [x] Pick a wiki: compare the Fandom and wiki.gg Arknights wikis for completeness and API access

### Fetching and caching
- [x] `scraper/wiki_client.py`: fetch a page's wikitext, links, and categories through the MediaWiki API
- [x] Set a descriptive `User-Agent` and a delay between requests (about 1 per second)
- [x] `scraper/cache.py`: store fetched pages in SQLite with a fetch timestamp
- [x] Follow redirects so "alternate name" pages resolve to the real page

### Parsing
- [x] `parser/wikitext.py`: pull internal links, section headings, and infobox fields
- [x] `parser/terms.py`: normalize titles (case, underscores, anchors like `Page#Section`)
- [x] Blocklist for noise pages: game mechanics, meta pages, "Arknights" itself, etc.
- [x] Hand-check the output for 3–5 well-known Operators

### Graph
- [x] `graph/builder.py`: BFS outward from the seeds, with depth and max-node limits
- [x] Edge weights: +1 per link, bonus if the link goes both ways, bonus if both terms share a section
- [x] `graph/scoring.py`: PageRank, then prune low-scoring nodes (seeds are always kept)
- [x] Store each node's wiki categories for later coloring
- [x] `graph/export.py`: NetworkX → D3 JSON (`nodes`, `links`)

### Term index
- [x] `index/build_index.py`: download all page titles and all redirects
- [x] Store as `title → canonical page` in SQLite
- [x] Simple lookup function: `lookup("Amiya") → "Amiya"`, `lookup("Doctor") → canonical page`

### Interface
- [x] CLI: `python -m backend.cli --seeds "Amiya,Reunion" --depth 2`
- [x] Flask route `GET /graph?seeds=...&depth=...`
- [x] Basic React + D3 force graph: drag, zoom, seed nodes highlighted

## Starting config values

| Setting | Value | Why |
|---|---|---|
| Depth | 2 | Depth 3 pulls in most of the wiki |
| Max nodes | 150 | Keeps the graph readable |
| Request delay | 1s | Polite to the wiki |
| Cache expiry | 7 days | Lore pages rarely change |

## Done when

- `Amiya, Reunion` produces a graph a fan would call "yeah, that makes sense"
- A second run with the same seeds is near-instant (served from the cache)
- Any term can be looked up in the index, including redirect names

## Out of scope

Screenshots, OCR, fuzzy matching, and styling beyond the basics.

## Risks

| Risk | Mitigation |
|---|---|
| Hub pages ("Terra", "Rhodes Island") connect to everything | Blocklist or cap their weight, and rely on PageRank pruning |
| Wiki blocks or throttles requests | Delay, User-Agent, cache everything |
| Wikitext templates hide links | Check a few pages. If templates hide a lot, switch to `action=parse` for rendered links |

## Outcome notes

### Wiki: wiki.gg

The [Arknights Terra Wiki](https://arknights.wiki.gg), compared with the Fandom wiki on 2026-09-29:

| | Fandom | wiki.gg |
|---|---|---|
| Articles | 10,550 | 17,274 |
| Active editors | 6 | 87 |
| Edits | 296k | 764k |
| `Reunion` page | 7 KB | 28 KB |
| `Terra` page | 3 KB | 32 KB |

Both run MediaWiki 1.43 with an open API, so API access doesn't separate them. Content does.

### Where the build departs from the plan

- **Operator lore lives on subpages.** wiki.gg operator pages are gameplay (stats, skills, stage links). The lore is on `<Name>/Story` (plot summary and character infobox) and `<Name>/File` (archives). A node that has those subpages is read from them instead of its main page, and a link to any subpage folds into its parent (`Amiya/File` → `Amiya`).
- **Links come from the wikitext, not the API's `prop=links`.** On faction and location pages the API's list is about twice as long, mostly navbox and enemy-list entries (158 extra on `Reunion`), and it takes many continuation requests. Templates did hide real links, in a narrower way: `{{Character list cell|name=Talulah}}`, `{{Main|Chernobog Crisis}}` and plain infobox fields. So a template parameter whose whole value is a page title counts as a link. `action=parse` wasn't needed. `<ref>` citations are dropped; on `Amiya/Story` they were 46 stage and artbook links.
- **Categories come from the term-index pass, not from each page fetch.** One `generator=allpages` pass collects every page's categories and redirects (about 70 requests, 1–2 minutes). The blocklist can then judge pages that were never fetched, and every exported node has categories with no extra requests.
- **The blocklist works by category** (stages, mechanics, items, staff, media; see `backend/parser/terms.py`), plus the title `Terra`. `Rhodes Island` is kept, since it matters for Amiya.
- **Section bonus**, read as: +1 for each section, on any fetched page, that links both ends of an existing edge.
- **PageRank is personalized**: the walk restarts at the seeds. On the same graph as plain PageRank, it ranks seed-specific pages higher: for `SilverAsh`, Karlan Trade, Cliffheart, Pramanix and Matterhorn rise while Originium and Oripathy drop.
- **The BFS max-node limit** caps how many pages each level expands: the 150 most linked from the level before. The final graph is then pruned to 150.
- **`notebooks/` was not created**, since nothing needs it yet. `data/` is created on first run and is not committed.
- **Cross-platform install.** `mwparserfromhell` 0.7.2 has no wheel for Python 3.14 or Windows on ARM, and without one pip needs a C compiler. Installs set `WITH_EXTENSION=0` to use its pure-Python parser instead: parsing is about 1.5× slower and the output is identical. Verified on macOS arm64 and in compiler-free Linux containers (Python 3.12 and 3.14). Windows is covered by the CI matrix.

### Measured

`Amiya, Reunion` at depth 2, with the index already built:

- Cold build: 7.7 s. Repeat: 0.7 s from the CLI, 0.5 s through Flask.
- Size: 800 nodes before pruning; 150 nodes and 1,983 links after.
- Top non-seed nodes: Rhodes Island, Oripathy, Infected, Victoria, Ursus, Originium, Sarkaz, Kazdel, Lungmen, Chernobog, Talulah, Doctor, Kal'tsit, Theresa. Patriot, FrostNova, Mephisto, Skullshatterer, Crownslayer, W, Nine and Faust are all in the top 60.

Operators hand-checked: Amiya, Kal'tsit, Ch'en, SilverAsh, Exusiai. Infobox fields (affiliation, family, race, birthplace) parse cleanly, and the top links hold up, e.g. SilverAsh → Cliffheart, Degenbrecher, Karlan Trade, Kjerag, Pramanix.

### Still owed

- The fan check under "Done when".
- Seeds are split on commas, so a title containing one (`Talulah, the Fighter`) can't be a seed.
- The term index refreshes only when `build_index` is rerun.
- Near-miss names don't match (`Frost Nova` vs the page `FrostNova`). That's v2's fuzzy matching.
- At 150 nodes and about 2,000 links the drawing is dense. Fading weak links or lowering `MAX_NODES` would help; that's styling, out of scope here.
