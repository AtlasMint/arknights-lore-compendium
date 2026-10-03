# v3: Richer Lore

**Theme:** graphs that explain connections, not just show them
**Outcome:** a player can screenshot their way through a chapter and end up with a labeled, spoiler-safe lore map.
**Status:** built 2026-10-03. Every task is done; three were done differently from the plan (a sixth node type, no colour per Movement, the story named beside a label rather than inside it), and labels need a second local model, `qwen3.5:4b`. See [Outcome notes](#outcome-notes).

## Goal

Make the graph genuinely useful for understanding the story: what each node is, how nodes relate, and without spoiling anything the player hasn't reached yet.

## Why a ticked list, not detection

The app can't hook into the game, so it never knows where the player is. Instead the player keeps a list of the stories they have finished, and the map is everything those stories introduced: a record of what was seen, not a readout of what is on screen now. Reading the stage code off screenshots was considered and dropped, since it can't be enforced and a progress list is what a recall tool wants anyway.

The model is Final Fantasy XVI's lore design ([GDC 2024 slides](https://media.gdcvault.com/gdc2024/Slides/GDC+slide+presentations/Aono_Momoka_DesigningActiveTime.pdf)). Its Active Time Lore panel is keyed to the current cutscene, which we can't do. But the Thousand Tomes (the archive you read back) and State of the Realm (the relationship chart) are progress-based, and those are what this version and [v5](../v5-recall.md) borrow: entries that update as the story progresses, text written from a narrator's perspective, and one dictionary feeding every view.

## Tasks

### Node types
- [x] Map wiki categories to types: Operator, Faction, Location, Event, Other — plus Character, for the 406 NPC pages; `terms.node_type`
- [x] Color and shape nodes by type, like unit symbols on a map legend — shape by type; colour is kept for factions
- [x] Operators take their faction's colour instead, since "who belongs to which faction" is what the chart answers — characters too; the three largest factions in a map get a colour, the rest share the neutral
- [x] Legend and a filter to show or hide each type

### Node detail panel
- [x] Click a node to see a short summary, its type, and a link to the wiki page — also its faction, the screenshot that brought it, and its labelled connections
- [x] Summaries come from the page intro, cleaned of wikitext — the first four prose sentences, from an operator's `/Story` subpage

### Relationship labels
- [x] For each edge in the final graph, pull the wiki sentences where both terms appear — and infobox lines, from the pages of one end that name the other
- [x] An LLM labels the relationship ("member of", "sibling of", "fought at", "leads") — `qwen3.5:4b` through Ollama; the 2B was measured and fell short
- [x] ~~Labels are in narrator voice and name the story unit ("introduced in Chapter 3 as Talulah's lieutenant")~~, so every edge carries where it was learned — the label is a sentence ("Talulah is the half-sister of Ch'en"), and the story is shown beside it, not written into it: "learned in" the first ticked story both ends share
- [x] Only label edges that survived pruning, which keeps the cost down — and only those visible under the current ticks, ten at a time, the selected node's first
- [x] Cache labels per term pair — in SQLite, by pair, model and prompt

### Stories timeline
- [x] One canvas, not a checklist: stories are nodes on a left-to-right axis, ticked by clicking (grey to green) — with a ✓, so read isn't colour alone
- [x] Two tabs over the same nodes, edges and ticked set: **Release**, on global release dates, and **In-game**, on in-universe order
- [x] Movements are the grouping. The game's Score menu sorts every Main Theme episode, intermezzo, side story and story collection into 14 Movements (The Ark, Glimpse of the Depths, Summertime Beats, Tales of Terra and so on), and the wiki mirrors them on `Story/Movements` with one subpage each. Every canon story is in exactly one; the only pages outside are the 8 crossovers, which the game and the wiki treat as non-canon
- [x] The infobox's `arc` field is the Movement's code (`AE` is Glimpse of the Depths); the wiki's `Story arc` template holds the code-to-name table, and the wiki hosts a 90×90 icon per Movement as `<code>_arc.png`, cached through the backend like other wiki data — the code comes from each Movement page's `Timeline head` instead, the same two letters; `GET /icon/<code>`
- [x] Each node carries its Movement's icon next to the name, ~~and nodes are coloured by Movement~~ — no colour: fourteen hues can't be told apart, so the icon carries the Movement
- [x] A Movement picker filters the canvas to that Movement's stories. Related stories from other Movements appear faded at the edge so the branch has somewhere to land; the four Act dividers from the Main Theme page label the Episode chain
- [x] Edges are two kinds, both curated on the wiki and nothing inferred: `previous`/`next` sequels from the infobox (52 of 75 stories), and `related` branches from the Movement pages, the stories the game recommends reading first (26 edges, many crossing Movements, such as Path of Life to Episode 14 and Lone Trail) — on Global: 55 sequel edges among 68 stories, and 25 related; the 26th names Episode 17
- [x] Five bands top to bottom on the same axis: Main Theme, Intermezzi, Side Stories, Story Collections, Crossovers. A band with nothing in it under the current filter is hidden
- [x] Release tab: a linear time axis from the Event and Episode infoboxes' global start dates (74 of 75 story pages carry it; Heart of Surging Flame keeps its infobox on its Part subpages instead). Data is complete, so this is the default tab — Prologue to Episode 04 carry no Global date either; they take Global's launch day, 2020-01-16, and Heart of Surging Flame its earliest Part
- [x] In-game tab: the Movement pages list stories in the Score's order, which the wiki says is in-universe chronological for every Movement but The Ark, so inside a Movement the order is known for all stories. Years are known for only about half: the wiki's Timeline page cites about 30 of the 75 under year headings, 19 of 71 synopsis pages open with a year, and the Timeline's crossover section dates 4
- [x] So with one Movement picked, the In-game axis is simply Score order and needs no years. With all shown, columns are ordinal: "to 1096", one per year, then "Undated" at the far right, with Score order breaking ties inside a column. The years live in a checked-in table, seeded once by script from those three sources and corrected by hand, keeping the wiki's own "ca." for estimated dates. When a story is cited under several years the latest wins, since earlier ones are usually flashbacks. Hand-correcting beats the heuristic, which is the FF16 lesson again — `backend/story_years.json`: 61 seeded, 13 corrected, 70 of 88 dated
- [x] Hovering a story shows the teaser blurb from its Movement page, written spoiler-light like the in-game description
- [x] Inside a band, a node sits at its place on the axis and drops to the next row when it would overlap the previous one, on both tabs: greedy row packing, no force simulation, no overlaps by construction. Worst case is about seven side stories in one release year
- [x] All edges drawn faint; hovering or selecting a node lights its sequels and branches and dims the rest
- [x] Clicking an Episode ticks it and everything before it; clicking a ticked one unticks it and everything after. Other bands tick one node at a time
- [x] Only stories already released on Global appear on either tab: a global start date in the past. The rest are left off, since they can't have been played. The Movement pages list unreleased stories too, so the same rule applies there — 88 of 93
- [x] Two Movement entries name a story differently from its page (Babel, Pinus Sylvestris); the cell's `link` parameter resolves them
- [x] Plain SVG drawn by React with d3's time scale for the axis; horizontal scroll when the canvas is wider than the screen

### Spoiler control
- [x] Tag each term with every story unit it appears in (main chapter, intermezzo, side story, event), from the wiki's story pages — the synopsis and the Movement teaser of each story, plus a character's own infobox list of appearances
- [x] Progress is ticked on the stories timeline above, one click per node
- [x] A tick-all for players who don't care about spoilers; it also shows untagged terms
- [x] Progress is the set of ticked stories, stored in the browser
- [x] A term is visible if any story it appears in is ticked; untagged terms stay hidden
- [x] The screenshot's own terms are never hidden, since the player just saw them; progress gates only the wiki expansion around them — every seed, typed or read
- [x] Node summaries drop any sentence that names a hidden term
- [x] Edge labels hide when their story unit is unticked, even if both ends are visible — when no story both ends share is ticked
- [x] Hidden nodes are removed entirely, not just greyed out — and so is a node they leave without links
- [x] Per-term hide-this and show-anyway overrides, stored in the browser, as the correction path for mistagging in either direction

### Session graphs
- [x] Multiple screenshots add to one growing graph
- [x] Show which screenshot introduced each keyword
- [x] Clear or restart the session

## Done when

- [x] Every node has a type and a summary — 125 of 125 on Amiya + Reunion
- [x] Most edges have a sensible relationship label — 30 of 38 sampled links, counting the plan's own fallback: 14 say how the two relate and are right, 16 say "is related to", 8 are wrong. See *Still owed*
- [x] Ticking Chapter 5 and nothing else reliably hides terms, summary sentences and edge labels from later stories — one leak found on the way and closed (below)
- [x] A Chapter 9 screenshot with only Chapter 5 ticked still shows its own keywords
- [x] Every story released on Global is on both tabs, ticks carry across tabs, and no two nodes overlap on either
- [x] Picking a Movement shows only its stories in Score order, with its branches to other Movements faded in
- [x] Five screenshots from one chapter build into one coherent map

## Out of scope

Deployment, sharing, other game servers, and the recall features in [v5](../v5-recall.md).

## Risks

| Risk | Mitigation |
|---|---|
| The LLM invents relationships | Only label from real wiki sentences; show "related" when unsure |
| Chapter data is incomplete | Untagged terms stay hidden unless tick-all is on |
| Automated tagging leaks spoilers or hides too much | Per-term overrides; FF16 hand-curated over 2000 points and still caught leaks in QA, so expect some |
| A summary sentence spoils without naming a hidden term | Accepted for now; the sentence filter catches the common case |
| Stand-alone Movements (Summertime Beats, Tales of Terra) have few sequel or branch edges, and the 8 crossovers are in no Movement | They sit as unlinked nodes, with their Movement's icon or none, and are still tickable |
| Movement icons are the game's artwork | Same footing as the wiki's own use of them; credited with the wiki in v4 |
| In-game years are known for only about half the stories, and some citations are flashbacks | The Undated column is honest about it; the years table is hand-corrected, not re-derived |
| Session graphs grow too big | Apply the same max-node pruning across the whole session |

## Outcome notes

### Where the build departs from the plan

- **Six node types, not five.** 406 lore pages are NPCs (Talulah, Patriot, Theresa) with no category but `NPCs`. Under the five, they would be "Other", beside races and lore concepts. They are **Character**, and like operators they take their faction's colour. Faction comes from a category that is a faction page (Amiya → Rhodes Island), or else the infobox's `affiliation` (Talulah → Reunion). A nation that is also a faction (Lungmen, Victoria) is a Faction.
- **Three faction colours, not one per faction.** In a force graph any two nodes can touch, and only three hues of the reference palette stay apart then, for colour-blind readers and full-colour ones alike (checked with the dataviz validator; a fourth puts orange beside yellow). The three largest factions in a map get blue, orange and aqua, ranked once per graph so ticking never repaints. The rest share the neutral grey. Every node is labelled, and the panel names its faction. Shape carries the type: circle, diamond, square, triangle, star, cross.
- **No colour per Movement on the stories canvas.** Fourteen Movements need fourteen hues, which nothing can tell apart. The Movement's icon is on every node, the picker filters by Movement, and the fill shows read (green, with a ✓) or not. The game's icons are white on transparent, so a light page shows them inverted.
- **The story is beside the label, not in it.** The model writes the relation as a sentence: `{"from": "Talulah", "relation": "is the half-sister of", "to": "Ch'en"}`. The panel then adds "learned in" the first *ticked* story both ends share. If the model wrote the story into the label, the label would name one story forever: an unticked one, or one that doesn't match the progress. This way it never names a story the player hasn't ticked.
- **Labels read from the side the evidence is on.** "she" on Talulah's page is Talulah, so the evidence is one end's own pages, and that end is the subject. The 2B's worst mistakes were backwards ("Reunion was formerly affiliated with Ines", from Ines's infobox), and this fixed them. Infobox lines count as evidence ("Talulah's family: Ch'en Hui-chieh (half-sister)"), image file names don't.
- **A second model for labels.** `qwen3.5:2b` copied the prompt's examples ("Amiya is the sister of Chernobog"). Without examples it still got 24 of 38 sampled links wrong. `qwen3.5:4b` stays local and open (Apache-2.0, 3.4 GB) and is `LABEL_MODEL` in `config.py`. Screenshots keep the 2B that v2 measured.
- **Labels are written lazily.** A 150-link map is about five minutes of the 4B, so labels come ten links at a time after the map draws: visible links only, the selected node's first. Each pair is cached, so a rebuild is instant.
- **Tags have three sources, not one.** Each story's synopsis and its Movement teaser link the pages it is about, and a story tags itself. A character page's own `appearance` list adds more: it tagged 52 of the 182 characters the synopses missed. An appearance "(as …)" doesn't count. The Deathless Black Snake's page lists "Episode 05 (mentioned as Kashchey)", and counting it showed the Snake three Episodes before its reveal.
- **Release dates.** Prologue to Episode 04 have no Global date in their infoboxes; they were in the game at launch, so they take 2020-01-16 from the wiki's Arknights page (`GLOBAL_LAUNCH`). Heart of Surging Flame takes its earliest Part, 2020-04-15.
- **The counts differ from the plan's.** 88 stories are out on Global (82 from the Movements, 6 of the 8 crossovers), not 75. Five are left out: Episode 17, Till the Lands Become an Orange, Bolívar Diagnosed, Sur le lac lune vivante, Thunder in the Azure Dream.
- **Years.** The seed takes stories linked under a year heading of the Timeline page, synopses with a year in their first 300 characters, and the crossover section, and the latest year wins. It dated 61. Thirteen were corrected by hand from the Timeline's own text:
  - Episodes 01 and 03–08 sit inside the Chernobog–Lungmen crisis (Dec 23, 1096 – Jan 8, 1097). Episode 08 had seeded as 1089, from its opening flashback.
  - Episodes 10–14 sit inside the Londinium crisis ("ca. 1098"). Episode 10 had seeded as 1079, from a backstory line, and the Timeline's note puts it no earlier than July 1098.
  - The Black Forest Wills A Dream is "ca. 1101", the end of its span in the undated section.

  70 of the 88 have a year; the 18 others sit in "Undated".
- **Sessions live in the tab.** Screenshots and chips are React state, and a reload starts afresh. Ticks and overrides are in `localStorage`. `/graph` takes up to 50 seeds (`MAX_SEEDS`), and every screenshot's speaker gets the speaker weight.
- **Hidden names are a spoiler too.** The "show anyway" list sits behind a disclosure marked "spoilers". The faction legend names only factions with a visible node.
- **Noise filter, again.** Building "Other" turned up gameplay pages the v2 filter missed: supply and chip stages by type (AP, CA, CE, CH, LS, PR, SK), Tales Within the Sand provisions, OSTs, summons, tournaments and April Fools events. 1,365 lore pages became 1,285. The screenshot set is unchanged (78/87 found, 26/28 with zero edits), and so is the Amiya + Reunion graph (125 nodes).

### Measured

M5, 24 GB, Ollama 0.35, `qwen3.5:4b` (digest `2a654d98e6fb`) for labels, warm cache.

- **Graph cost.** `/graph` on Amiya + Reunion takes 1.3 s longer for types, factions, summaries and tags (2.6 s cold), and returns 175 KB. All 125 nodes have a type and a summary, 122 have story tags, and 140 of the 152 links share a story.
- **Tags.** 997 of 1,285 lore pages are tagged from synopses, teasers and the stories themselves, before appearance lists: 343/457 operators, 340/406 characters, 84/95 factions, 53/56 locations, 98/131 events.
- **Prologue to Episode 05 ticked, on Amiya + Reunion.** 47 of 125 nodes show; Theresa, Civilight Eterna, Londinium and Kristen Wright are hidden, and Talulah, FrostNova, Patriot and W show. 75 of the 188 summary sentences of shown nodes are dropped, and labels can show on 63 of the 152 links.
- **Five screenshots from the labeled set** (Bagpipe ×3, a Victorian officer, Eblana) with only Prologue to Episode 05 ticked:
  - 6 seeds, numbered by screenshot, and one map of 140 nodes and 213 links.
  - 27 nodes show, all 6 seeds among them; the rest is Episode 09 material.
- **Labels.** The sample is every 4th link of Amiya + Reunion, 38 links, judged by hand against the evidence:

| | `qwen3.5:2b` | `qwen3.5:4b` |
|---|---|---|
| Says how they relate, and is right | 8 | 14 |
| "is related to" | 6 | 16 |
| Wrong | 24 | 8 |
| Time a link | 0.8 s | 1.9 s |

  In the UI, Talulah's links were labelled 19 s after she was clicked: "Reunion was founded by Talulah · learned in Prologue".
- **Stories canvas.** 88 stories on both tabs; the Release tab is about 2,300 px wide and scrolls. `bun test` checks that no two nodes overlap on either tab, with and without a Movement picked, on a crowded fake.
- **Tests.** `python -m tests.test_v0` to `test_v3` pass offline, and so do `bun test`, the lint and the build.

### Still owed

- **Label quality.** About one link in five gets a wrong label, mostly where the only evidence mentions both ends in passing ("Amiya is classified as a Chimera by Revenant"). Knobs, in order:
  - Keep the evidence to infobox lines and sentences where one end is the grammatical subject.
  - Try a larger local model.
  - Show "related" for labels drawn from a single incidental sentence.
- **A summary sentence can spoil without naming a hidden term**, as the plan expected. Bagpipe's summary says "everything changed for her during the County Hillock atrocity in 1098", and County Hillock shows because it was a keyword.
- **A label can spoil the same way.** It is drawn from the whole page, so a link learned in an early story can carry a relation from a later one.
- **Untagged terms.** 288 lore pages appear in no synopsis or teaser, mostly operators with no story role. They stay hidden until everything is ticked, unless the panel's override shows them. The two crossovers without a synopsis tag nothing.
- **The session is lost on reload.** Keeping it would mean keeping the screenshots too.
- **New stories need an API restart.** The stories data is cached for the process.
- **The years table is hand-kept.** A new story needs `python -m backend.stories` and a merge.
