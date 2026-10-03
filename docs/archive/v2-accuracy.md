# v2: Accuracy

**Theme:** fewer wrong or missing keywords
**Outcome:** most screenshots need no manual edits to the keyword list.
**Status:** built 2026-10-03. Test set, scorer, fuzzy matching and speaker priority are done; cropping, a second reading engine and keyword ranking were measured as not needed. See [Outcome notes](#outcome-notes) and the [addendum](#addendum-partial-names-demonyms-collisions-and-a-tighter-noise-filter) on the alias gaps, closed the same day.

## Goal

Make the screenshot-to-keywords step reliable, and measure it instead of eyeballing it.

## Tasks

### Test set (build this first)
- [x] Collect 20–30 screenshots across different chapters, speakers, and backgrounds — 28, from phone and desktop, in five UIs: dialog, story log, narration, choice and chapter menu
- [x] Label the correct keywords for each in `tests/screenshots/labels.json`
- [x] Script that scores the pipeline: how many correct keywords were found, and how many wrong ones were added — `tests/score_screenshots.py`
- [x] Record a baseline score from v1 before changing anything — see the outcome below

### Fuzzy matching
- [x] Use `rapidfuzz` to catch near-misses ("Amlya" → "Amiya") — stdlib `difflib` instead: 11 ms a word over all 19k titles, so no dependency
- [x] Give each match a confidence score — the difflib ratio; `guesses` in the response says what was read
- [x] Minimum-confidence cutoff, tuned against the test set — 0.85, and five letters or more
- [x] Show low-confidence chips differently in the review UI — dotted, with the misread word as the tooltip

### Speaker priority
- [x] Detect the speaker from the name box (the vision prompt already returns it)
- [x] Speaker gets the top seed weight in the graph — `SPEAKER_WEIGHT = 3` in the PageRank personalization

### Region cropping
- [ ] ~~`vision/cropper.py`: crop to the dialog band and name box before reading~~ not needed: every dialog-UI screenshot read at text match 1.00 without it
- [ ] ~~Handle the common aspect ratios (phones, tablets, emulators)~~ not needed, same reason
- [ ] ~~Compare scores with and without cropping on the test set~~ not needed, same reason

### Swappable reading engines
- [ ] ~~`vision/paddle_reader.py`: PaddleOCR as a free, local option~~ not needed: the misses were scope and spelling, not reading; also no `paddlepaddle` wheel for Python 3.14 (RapidOCR would be the route)
- [ ] ~~Choose the engine in `config.py`~~ not needed, one engine
- [ ] ~~Compare the Qwen3.5 reader and PaddleOCR on accuracy, speed, and memory~~ not needed

### Ranking
- [ ] ~~Score each keyword: match confidence × importance (PageRank from the global graph)~~ not needed: the baseline had zero extra keywords, so there is nothing to rank down
- [ ] ~~Only the top N become seeds; the rest are shown as optional~~ not needed, same reason

## Done when

- [x] The test set score clearly beats the v1 baseline — 70 of 84 keywords against 48
- [x] Most test screenshots need zero manual chip edits — 20 of 28, against 12
- [x] There's a clear, measured answer for which reading engine is the default — Qwen3.5-2B stays; see the notes for why no second engine was built

## Out of scope

Relationship labels, spoiler control, and multiple screenshots.

## Risks

| Risk | Mitigation |
|---|---|
| Fuzzy matching adds false matches | Tune the cutoff against the test set, not by feel |
| Cropping breaks on unusual layouts | Fall back to the full image when the crop finds no text |
| Test set too small to trust | Grow it any time a real screenshot fails |

## Outcome notes

### Where the build departs from the plan

- **`difflib`, not `rapidfuzz`.** `difflib.get_close_matches` over all 19,083 titles takes 11 ms a word, and the fuzzy pass over the whole set is 0.5 s, so no dependency. Only capitalized words of five or more letters that the exact scan left over are tried, only the single closest title counts, and it has to resolve to a lore page (a class or disambiguation page drops the guess). The cutoff came from a sweep on the set: 0.8 gave 10 right and 6 wrong guesses (There → Theresa, Hence → Fence, Hardly → Harley, Amongst → Angst, Logistics → Linguistics), 0.85 gave 9 right and 0 wrong, 0.9 gave 3 right. `CUTOFF = 0.85` and `MIN_GUESS = 5` in `matcher.py`.
- **Confidence is a flag, not a number per chip.** With one cutoff a chip either came from a guess or it didn't, so `/analyze` returns `guesses` (title → the word as read) and the UI draws those chips dotted with the misread word as the tooltip. A score on every chip would have been shown to no purpose.
- **The reader prompt changed, which the plan didn't foresee.** Most misses were scope, not reading: asked for "the dialog text", the model returned one line of a story log, one card of a chapter menu, and ignored the choice boxes. It now asks for all the story text on screen, including the names beside log lines. That took the set from 57 to 69 keywords on its own. One log view got worse (it now returns one line of eight where it returned most of them before); the net is +12.
- **A doubled line break is unescaped in `parse()`.** On one log view the model wrote a literal backslash-n between lines, which glued the next name into `nBlaze`. One `replace`, one more keyword.
- **No cropping.** All 17 dialog-UI screenshots read at text match 1.00 at 1280 px (one at 0.98, a misspelled Dublinn that fuzzy catches), so there was no reading problem for a crop to fix.
- **No PaddleOCR, no engine switch.** The misses were scope and the spelling of invented names (Dublinl, Dublininn, Czibor), both fixed more cheaply above. `paddlepaddle` also has no Python 3.14 wheel; RapidOCR (Paddle's models on ONNX: `rapidocr` 3.9.2 with `onnxruntime` 1.30) installs and is the route if an OCR engine is ever wanted.
- **No ranking.** The baseline had zero extra keywords, so there was nothing to rank down; the whole problem was recall.
- **Stage codes are not expected keywords.** FC-7, CW-7, CW-8 and CW-10 are real pages, but the noise filter excludes operations, so they can never be seeds and were dropped from the labels.
- **The test set is 1280 px JPEG copies** (4.3 MB for 28), the size the frontend uploads, under short descriptive names. The full-size originals (68 MB) sit in `tests/screenshots/originals/`, which git ignores.
- **Speaker priority was checked on one graph, not the set.** `SPEAKER_WEIGHT = 3` on `Amiya, Reunion` with Amiya speaking: Amiya's score 0.274 → 0.404, Reunion 0.274 → 0.143; Theresa, Kal'tsit and Doctor move up, Talulah down. The scorer stops at the chips, so this is direction, not a measured gain.

### Measured

M5, 24 GB, Ollama 0.35.0, `qwen3.5:2b` (digest `324d162be6ca`), temperature 0, 1280 px. 28 real screenshots: 13 from a phone (2556×1179), 15 from a desktop (emulator captures at 2842×1326, two YouTube frames with the macOS menu bar still in shot, and three odd sizes). By UI: 17 dialog, 1 dialog with a choice, 7 story log, 1 narration-only, 2 chapter menu. 84 expected keywords, all canonical titles the graph can hold.

| | v1.1 baseline | + fuzzy | + whole-screen prompt | + parse fix (final) |
|---|---|---|---|---|
| Keywords found | 48/84 | 57/84 | 69/84 | 70/84 |
| Extra keywords | 0 | 0 | 1 | 1 |
| Zero chip edits | 12/28 | 18/28 | 20/28 | 20/28 |
| Speaker right | 21/28 | 21/28 | 22/28 | 22/28 |
| Text match, mean | 0.860 | 0.860 | 0.869 | 0.869 |

- Dialog UI alone (17): 14 need zero edits, and the 3 that don't are alias gaps (below), not reading errors. The speaker was right on all 17.
- The 14 remaining misses by cause: 9 are reader scope on two story-log views (one came back as a single line of eight, the other as the last three, with the dimmed upper lines skipped); 4 are names the index has no redirect for (Candela → Candela Sanchez, Warwick → Earl of Warwick, Schnitz → Schnitz & Yolanta Nearl, and Nightzmora, whose page is a disambiguation); 1 is the plural "Tarans" at 0.80 to Tara, under the cutoff ("Taran" at 0.89 is caught).
- The 1 extra: "Castle" from the episode name *Castle in the Sky* guessed as Castle-3 at 0.857. It shows dotted.
- The 6 wrong speakers are all screens with no name box (log, narration, menu), where the model names someone on screen or writes "I"; the labels there are soft anyway.
- Fuzzy guesses that landed: Dublinl, Dublininn and Dublin → Dublinn; Czibor → Czcibor; Victorians and Victorian → Victoria; Taran → Tara (three times).
- A full pass of 28 with the model loaded: 1 min 32 s, 3.3 s a screenshot; the two earlier passes took 2 min 49 s and 3 min 14 s with loads in between. Readings are deterministic: the cache was cleared and all 28 re-read to the same text, differing only by the parse fix.
- `python -m tests.test_v0`, `test_v1` (with a fuzzy case and the parse case) and `test_v2` pass; the frontend lints and builds.

### Still owed

- **Story-log views.** The 2B returns between one and five of the eight visible lines and skips dimmed ones; two of the seven logs hold 9 of the 14 remaining misses. Knobs, in order: `qwen3.5:4b`, then reading a log in horizontal strips.
- **Alias gaps.** A first name, a surname or an adjective (Candela, Warwick, Schnitz, Tarans) only matches when the wiki has a redirect or fuzzy reaches it. A small alias table or stemming would cover them; wait until more screenshots repeat the same gap.
- **Disambiguation pages resolve to nothing** (Nightzmora). Picking the lore target would need the page text.
- **Speaker priority** has a direction, not a measurement against a fan's judgment.
- From v1.1: `qwen3.5:2b-mlx`, `keep_alive`, and pinning the model digest.

## Addendum: partial names, demonyms, collisions, and a tighter noise filter

Same day, after the fan check: the "alias gaps" under *Still owed* were not acceptable. The requirement is that every noun with a wiki page is matched and shown (shown off by default counts), and that furniture, base skills and mechanics are not lore. Three matcher rules and a filter change, each measured on the set before being kept.

### What changed

- **Collisions.** A leftover capitalized word that is itself a title the noise filter rejects is no longer dropped; the lore pages that qualify it are offered. If the plain page is a disambiguation, its targets are keywords (Nightzmora → Nightzmora (country) and Nightzmora (race)), since the plain word means nothing else. If it is a class or term, the namesake goes under needs-context (Guard → Guard (NPC), Medic → Medic (NPC)), the same treatment as Doctor: in both screenshots here, "Redsteel Guard" is a Victorian unit and the "Medic Operator" in the Tkaronto chapter is not the Act I Medic, so on by default would have been wrong twice. The index holds 31 such pairs; after the filter change only these three matter, the rest were furniture and base skills.
- **Demonyms and plurals.** Strip one of `s, n, ns, ian, ians, ans, ese, ite` (shortest first, so "Victorians" reaches Victoria through "ns" before "ians" could reach a Victor) and accept only an exact page: Tarans → Tara, Victorian → Victoria. Tried before fuzzy, since exact beats approximate. Zero wrong hits on the set.
- **Partial names.** A leftover word that is the first or last word of exactly one named page is that page: Candela → Candela Sanchez, Warwick → Earl of Warwick, Schnitz → Schnitz & Yolanta Nearl, and two names the labels had missed, Ferdinand → Ferdinand Clooney and Parvis → Ahrens Parvis. Named pages are NPCs, other characters, operators, locations, nation-states, factions, races and tribes (1,055 pages), minus the fifteen "Reserve Operator - X" placeholders. Three guards make it safe, each measured. Over all lore pages the raw rule hit *Let There Be Light*, *Bunny Present Pile* and *Plain Hanging Tube Light*, so the pool is those categories only. Adding places and groups brought in ordinary head words: "County" is the first word of County Hillock and nothing else, so it fired on "County Trent" and "County Oak Grove", and the factions add Island, House, Church, Group, Tower. A presence-in-gameplay-titles test was tried as a data-driven detector and failed (it flagged Hillock and Billiton, missed Palace and Church), so the 69 ordinary words among the 310 candidates are listed by hand in `GENERIC` and never count, for partial names or fuzzy guesses; that also removed the Castle-3 extra. Alter titles ("Gavial the Invincible") contribute only their first word, since the last is an epithet. A sentence-opener filter was tried and dropped: it removed "Ms. Candela" and every log-line speaker name. 5 right, 0 wrong on the set; `names()` holds 827 words and builds in 0.05 s.
- **Noise filter.** Of the 5,691 pages passing `is_noise`, 3,900 were furniture (by type: Decorations 824, Seatings 279, Wall Decorations 227, Tables 199, Ceiling Lamps 194, ...), 669 base skills, 103 Tongbaos, plus Reclamation Algorithm items, terrain tiles, sanity food, music and promotions. All of those categories are noise now, by name and by suffix (` seasons`, ` tokens`, ` items`, ` materials`, ` resources`, ` mechanics`, ` currencies`, ` themes`, ` music`). The lore set is 1,361 pages, and no page carries a furniture-theme category any more. Two rows were tried and reverted: "Celebration", "Festival" and "Carnival events" tag real story events (Lone Trail, Invitation to Wine, Dossoles Holiday), and "Text errors" is a maintenance tag on operator pages. The Amiya + Reunion graph is unchanged at 125 nodes: character graphs never reached furniture, which is why v0's tuning never saw it.

### Measured

Same readings as the final column above, from the cache, with the labels extended by Ferdinand Clooney, Ahrens Parvis and Nightzmora (race) (87 expected keywords).

| | Before the addendum | After |
|---|---|---|
| Keywords found | 70/84 | 78/87 |
| Extra keywords | 1 | 0 |
| Zero chip edits | 20/28 | 26/28 |
| Speaker right | 22/28 | 22/28 |

- All 18 dialog-UI screenshots (17 plain, 1 with a choice) and both chapter menus need zero edits.
- The two that don't are the story-log views where the reader skipped lines (accepted). The earlier extra, "Castle" from the episode name *Castle in the Sky* guessed as Castle-3 at 0.857, is gone: Castle is on the GENERIC list.
- Guesses that fired: Tarans and Taran → Tara (three screenshots), Dublininn, Dublinl → Dublinn, Czibor → Czcibor, Victorians and Victorian → Victoria, Candela, Warwick, Schnitz, Ferdinand, Parvis → their pages. Under needs-context: Guard (NPC), Medic (NPC).
- `test_v1` gained the collision, demonym and first-name cases on the fake index; `test_v0`, `test_v1`, `test_v2` pass, the frontend lints.

### Still owed

- Story-log views, as before (the reader's choice of lines, accepted for now).
- The `GENERIC` list is hand-kept. A new page that starts or ends with another ordinary word gets a wrong partial match until the word is added; the data-driven replacement is a lowercase-frequency check over cached page text.
- The named pool keys on categories (`NPCs`, `Other characters`, `Locations`, the faction and race categories, `N-star`). A character or place in none of them is not covered until it shows up in a screenshot.
- No screenshot in the set names a place by one word, so the place half of the rule is verified on the fake index and by inspection (Hillock, Billiton, Grypherburg, Westhaleg, Rhine, Penguin resolve), not by the set.
