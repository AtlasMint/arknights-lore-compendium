# API

The Flask API the frontend calls, served by `python -m flask --app backend.app run --port 5001`. Every error is a JSON `{"error": "..."}` with the status given below. [How it works](HOW-IT-WORKS.md) explains where the data comes from.

## `GET /graph`

`GET /graph?seeds=Amiya,Reunion&depth=1&speaker=Amiya` returns the lore map around the seeds:

```json
{"nodes": [{"id": "Amiya", "seed": true, "score": 0.144, "categories": ["5-star", "Amiya", "Caster", "Core Caster", "Rhodes Island"],
            "type": "Operator", "faction": "Rhodes Island",
            "summary": [{"text": "The public face of Rhodes Island and its top executive.", "terms": ["Rhodes Island"], "story": null},
                        {"text": "Amiya is a Rim Billitonian Cautus who lost her parents ...", "terms": ["Amiya", "Cautus", "Rim Billiton"], "story": "Babel (event)"}, ...]}, ...],
 "links": [{"source": "Kal'tsit", "target": "Amiya", "weight": 59, "stories": ["Episode 02", "Episode 04", ...]}, ...],
 "tags": {"Amiya": ["Prologue", "Episode 01", ...], "Cautus": [...], ...}}
```

- `seeds`: 1 to 50 comma-separated wiki titles or redirects. One that isn't on the wiki gets a 400, `"Not on the wiki: ..."`.
- `depth`: link hops out from the seeds, 1 to 3 (default 1).
- `speaker`: optional, and may name several speakers, one per screenshot. Each that is one of the seeds gets three times the others' share of the PageRank restart, so the map leans toward whoever was talking.

In the reply:

- `type` is one of Operator, Character, Faction, Location, Event and Other.
- `faction` is set for operators, characters and factions themselves.
- `summary` is an operator's in-game Profile, then the page's first four sentences, then one sentence per story the page has a section for, in Score order. Each carries the lore pages it names and `story`: the story that told it (a citation's stage, or the section's heading), or null.
- `tags` maps every node, and every term a summary names, to the released stories it appears in, in Score order.
- A link's `stories` are the ones both ends share.

The frontend hides whatever has no ticked story, and a summary sentence until its `story` is ticked.

## `POST /analyze`

Takes a multipart form with one `image` field (PNG, JPEG or WebP, up to 10 MB) and returns what the screenshot names:

```json
{"speaker": "Amiya", "text": "Doctor, the Reunion Movement has taken Chernobog.",
 "keywords": ["Amiya", "Reunion", "Chernobog"], "needs_context": ["Doctor"], "guesses": {"Chernobog": "Chernobug"}}
```

- `keywords` are wiki pages the screenshot names.
- `needs_context` are matches that could be ordinary words. The UI shows them unselected.
- `guesses` are keywords found from a misread or partial word, with the word as read. The UI draws those chips dotted.

The frontend scales screenshots to 1280 px on the long side before uploading, since the reader's time grows with pixels: a phone screenshot went from 19 s to 5 s with the text still legible. The file type is checked from its bytes, not its name. A wrong type gets a 415, an oversized file a 413, and a failed read (Ollama not running, model not pulled) a 502.

## `GET /terms`

`GET /terms?prefix=kal` returns up to 10 titles and redirects starting with the prefix, for autocomplete: `["Kal", "Kal'tsit", ...]`.

## `GET /stories`

Returns every story released on Global, for ticking progress:

```json
{"movements": [{"code": "MS", "name": "Main Theme", "intro": "In every story, there are heroes ..."}, ...],
 "acts": [{"name": "Act I: Shatter of a Vision", "first": "Episode 04"}, ...],
 "stories": [{"id": "Babel (event)", "name": "Babel", "subtitle": "", "movement": "RI", "band": "intermezzo",
              "start": "2024-10-10", "order": 21, "year": "1094", "teaser": "..."}, ...],
 "edges": [{"source": "Babel (event)", "target": "Episode 14", "kind": "related"}, ...]}
```

- `band` is one of `main`, `intermezzo`, `side`, `collection` and `crossover`.
- `start` is the Global start date.
- `order` is the game's Score order.
- `year` is the in-game year: "1097", or "ca. 1098" where the wiki estimates, or null.
- An edge's `kind` is `sequel` or `related`.

## `GET /icon/<code>`

`GET /icon/MS` returns a Movement's 90×90 icon (PNG), fetched from the wiki once and then kept. An unknown code gets a 404, and a failed fetch a 502.

## `POST /labels`

Takes 1 to 20 pairs of lore page titles and returns a label for each, in the same order:

```json
{"pairs": [["Ch'en", "Talulah"], ["Theresa", "Catastrophe"]]}
```

```json
{"labels": [{"from": "Talulah", "relation": "is the half-sister of", "to": "Ch'en"},
            {"from": "Theresa", "relation": "is related to", "to": "Catastrophe"}]}
```

A label reads `from relation to`, from whichever end the wiki's evidence is about, so it may run the other way from the pair as sent. "is related to" means the wiki doesn't say. A title that isn't a lore page gets a 400, and a failed call to Ollama a 502.

## `GET /progress` and `PUT /progress`

The stories you have read, the hide/show corrections and the fog toggle, kept in one file by the API (`data/progress.json`, `PROGRESS_PATH` in `config.py`), so progress follows the backend rather than the browser:

```json
{"ticked": ["Prologue", "Episode 01"], "overrides": {"Talulah": "hide"}, "fog": false}
```

`GET` returns it: a 404 when nothing has been saved yet, a 500 when the file can't be read or isn't this shape (the frontend then saves nothing, so the file is never overwritten). `PUT` with the same object saves it, whole or not at all, and echoes it back; anything else gets a 400. Titles are up to 200 characters, `overrides` values are `hide` or `show`, and `fog` is a boolean.
