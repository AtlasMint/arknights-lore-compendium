# v1: Screenshot MVP

**Theme:** screenshot → graph, end to end
**Outcome:** upload a dialog screenshot and see a relevant lore network.
**Status:** built 2026-09-30. All tasks are done. The "Done when" checks need a Gemini API key and real screenshots, and are still open. See [Outcome notes](#outcome-notes). Rather than get a key, the Gemini reader was replaced by a local open model on 2026-10-01, before any key was used: see [v1.1](v1.1-local-reader.md). The notes below describe the reader as first built.

## Goal

The simplest version of the full idea that works. Accuracy can be rough: a review step lets the user fix keywords by hand before the graph is built.

## Flow

```
Upload → Gemini reads text → match against term index → user reviews chips → v0 graph
```

## Tasks

### Upload
- [x] Frontend: drag-and-drop or file picker, with an image preview
- [x] Flask `POST /analyze`: accept an image, validate type and size

### Reading text
- [x] `vision/reader.py`: a common interface, `read(image) → {speaker, text}`
- [x] `vision/gemini_reader.py`: send the image to a Gemini Flash model
- [x] Prompt asks for JSON only: speaker name and dialog text, no commentary
- [x] Parse the JSON safely (strip code fences, fall back on failure)
- [x] API key in `.env`, never committed

### Finding keywords
- [x] `index/matcher.py`: scan the text for term-index matches
- [x] Longest match wins ("Rhodes Island" beats "Island")
- [x] Case-insensitive matching, with the canonical title returned
- [x] The speaker name is always included as a keyword if it matches

### Review step
- [x] Show the found keywords as chips: remove with a click, add with a text box
- [x] Autocomplete for the add box, powered by the term index
- [x] "Build graph" button sends the confirmed keywords to `/graph`

### Graph
- [x] Reuse v0 as-is
- [x] Highlight the keywords that came from the screenshot

## Why Gemini for v1

Classic OCR tools like Tesseract struggle with stylized game fonts and textured backgrounds. A vision model reads them far better, can return structured JSON directly, and you already know the API. The term index acts as a safety net: anything the model gets wrong or invents simply won't match a real page.

## Done when

- A typical story dialog screenshot produces a relevant graph in one flow
- The review step makes it easy to fix any mistakes
- The whole round trip takes under ~15 seconds on a cold cache

## Out of scope

Fuzzy matching, cropping, keyword ranking, and alternative OCR engines.

## Risks

| Risk | Mitigation |
|---|---|
| Model misreads names | The review step for now; fuzzy matching in v2 |
| Common words match page titles ("Doctor", "Guard") | Add them to a "needs context" list and let the user decide |
| API cost or rate limits | Cache results by image hash so the same screenshot is never read twice |

## Outcome notes

### Where the build departs from the plan

- **Gemini over REST, not the SDK.** `vision/gemini_reader.py` makes one `generateContent` call with `urllib`, as the wiki client does, so Google's SDK and its dependencies aren't needed. The model is `gemini-3.8-flash`, the current stable Flash on 2026-09-30, set in `config.py`. The prompt asks for JSON only and the request sets `responseMimeType: application/json`. `parse()` still strips code fences, and keeps a reply that isn't JSON whole as the text, so the names in it can still match.
- **The key.** Flask loads `.env` itself once `python-dotenv` is installed, so there's no loading code; that package is v1's only new dependency. The key travels in a request header, never the URL, so it can't leak into an error message.
- **`read(image, mime_type)`**, not `read(image)`: Gemini needs the type, and `app.py` has already sniffed it from the file's bytes while validating the upload.
- **Matching reuses the graph's `resolve()`**, so pages the graph treats as noise never become keywords. `Guard` and `Sniper` are class pages and drop out that way.
- **"Needs context" is a rule, not a list.** 501 of the 1,271 single-word lore titles are ordinary English words (Silence, Mountain, Dusk, Frost, Ash), mostly operator names, which is too many to list by hand. So a match written all in lower case in the dialog goes to `needs_context`, and so does `Doctor`, which is capitalized in nearly every line. Whatever the speaker name matches is always a keyword.
- **Possessives and curly apostrophes** are handled: `Amiya’s` matches Amiya.
- **The chips replace v0's seed box.** They start as `Amiya, Reunion`, so typing keywords by hand still works, and the add box takes a comma-separated list. A click toggles a chip rather than deleting it, so a misclick is undone by clicking again. `needs_context` chips start off.
- **Autocomplete** is a native `<datalist>` fed by `GET /terms`.
- **Highlighting** is v0's seed highlight. The seeds are exactly the confirmed keywords, so no second style was added. Chips added by hand are highlighted the same way.
- **The reading is shown** next to the preview, so a misread is visible, not just its effect on the chips.
- **Upload checks:** the type comes from the file's magic bytes (PNG, JPEG, WebP), not its name. The 10 MB limit is Flask's `MAX_CONTENT_LENGTH`, with a JSON 413.
- **The image-hash cache** from the risk table is built: a `readings` table in `data/wiki.db`. Failed reads aren't cached.

### Measured

- Matching takes about 0.1 ms per line against the real 19k-title index.
- On sample lines written for this check (not taken from the game):
  - Amiya: *"Doctor, Kal'tsit says the Reunion Movement has taken Chernobog. We need to get everyone back to Rhodes Island before the Catastrophe hits."* gives Amiya, Kal'tsit, Reunion, Chernobog, Rhodes Island and Catastrophe, with Doctor under needs context.
  - *"the frost on the mountain was thick at dusk, and there was only silence and ash. Hope kept us going."* puts Frost, Mountain, Dusk, Silence and Ash under needs context. `Hope`, a roguelike item page, gets through as a keyword because it starts a sentence.
- Browser check in headless Chrome, with Gemini stubbed: upload, drag-and-drop, chip toggles, autocomplete and add all work. A wrong file type shows the error. Building from five chips gave 150 nodes and 2,045 links in 1.2 s, mostly from cached pages.
- A real call with a fake key comes back as `Gemini API error 400: API key not valid`, so the endpoint and auth header are right. No successful reading has been seen yet.

### Still owed

- All three "Done when" checks. They need a key and real screenshots. The round-trip time is unmeasured. The model's thinking is left at its default, because the docs didn't confirm how to set it for `generateContent`. If reading is slow, lowering it is the first thing to try.
- About 370 gameplay pages get past v0's noise filter and can match as keywords: base skills (87), roguelike items (Foldartals, Tongbaos, `Hope`), furniture and debuffs. Adding their categories to `NOISE_CATEGORIES` would stop that, but it also changes v0's graphs. That's left for v2's test set to justify.
- Common words at the start of a sentence still come through as keywords. For now the review step catches them.
- Titles containing a comma still can't be seeds (from v0). The add box splits on commas too, so `Talulah, the Fighter` becomes two chips.
- Gemini 429 and 503 errors aren't retried. The user uploads again.
