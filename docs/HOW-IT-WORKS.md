# How it works

From a screenshot to a spoiler-safe lore map. [API](API.md) has the exact requests and replies; the plans in [archive/](archive/) have the measurements behind each choice.

## The pipeline

```
Screenshot
   │
   ▼
[1] Read text      → a local vision model pulls the speaker and the story text
   │
   ▼
[2] Find keywords  → match the text against a list of all wiki page titles
   │
   ▼
[3] Build network  → follow wiki links outward, build a weighted graph
   │
   ▼
[4] Show it        → a React + D3 map, filtered by the stories you have read
```

## The term index

Before touching screenshots, the app downloads every wiki page title and its redirects (alternate names that point to the same page). That list is the answer key. The app never guesses whether a word "sounds important"; it only asks whether the word is a real wiki page. That filters out reading mistakes and made-up terms, and redirects cover nicknames and alternate spellings (`Reunion Movement` → `Reunion`).

Gameplay pages are filtered out by wiki category: stages, mechanics, items, furniture, base skills, music and the like. That leaves about 1,300 lore pages: characters, places, factions, races and stories.

## Reading a screenshot

`qwen3.5:2b`, through Ollama, is asked for the speaker and all the story text on screen. The lines of a story log, the options of a choice and the cards of a chapter menu count too. Each screenshot is read once: readings are cached by the image's SHA-256.

## Finding keywords

The text is scanned against the term index, the longest phrase first, so "Rhodes Island" beats "Island".

- **Speaker:** whatever the speaker's name matches is a keyword.
- **Lower case and Doctor:** a match written in lower case ("the silence here") could be an ordinary word, and so could `Doctor`. Both go under *needs context*, shown unselected.

Capitalized words that matched nothing get a second look:

- **A gameplay title** (a class, a term, a disambiguation) offers the lore pages that qualify it:
  - a disambiguation's targets as keywords (`Nightzmora` → Nightzmora (country) and Nightzmora (race));
  - a class's namesake under needs-context (`Guard` → Guard (NPC), since "Guard" is usually the class).
- **Any other word of five or more letters** is tried three ways, in order:
  1. As a demonym or plural (`Tarans` → Tara).
  2. As a misreading, compared with every title using `difflib` and accepted at 0.85 similarity or better (`Dublinl` → Dublinn).
  3. As one word of a character, place or group that only one such page starts or ends with (`Candela` → Candela Sanchez, `Hillock` → County Hillock).

  Ordinary words that happen to start or end such a page (County, Palace, Island) are listed in the matcher and never count.

Keywords found by this second look show as dotted chips, with the word as read in the tooltip.

## Building the graph

From the seeds, the builder follows wiki links 1 hop out by default (up to 3). Operator main pages are gameplay stats, so an operator's links come from its `/Story` and `/File` subpages.

An edge's weight is:

- 1 for each link;
- plus a bonus when two pages link each other;
- plus a bonus for each section that links both ends.

Personalized PageRank, restarting at the seeds, keeps the 150 most relevant pages. A screenshot's speaker gets three times the restart share of the other seeds. Fetched pages are cached in SQLite for 7 days, so a cold build takes about 8 seconds and a repeat under 1.

## What each node is

The shape says what a page is, from its categories, like unit symbols on a map legend:

| Shape | Type |
|---|---|
| circle | Operator |
| diamond | Character, for NPCs |
| square | Faction, including nations that are factions |
| triangle | Location |
| star | Event, including every story |
| cross | Other: races, lore concepts |

Colour says which faction an operator or character belongs to. It comes from a category that is a faction page, or else the infobox's `affiliation`. Only three hues stay distinguishable when any two nodes can sit side by side, so the three largest factions in a map get one each and the rest share the neutral grey. Every node keeps its name label, and the layout keeps nodes at least 16 px apart.

A node's summary is its page's first four sentences, cleaned of wikitext; an operator's comes from its `/Story` subpage.

## Relationship labels

For each link, the evidence is the sentences and infobox lines on one end's pages that name the other end. "Talulah's family: Ch'en Hui-chieh (half-sister)" is one. The end whose page it is becomes the subject, since "she" on Talulah's page is Talulah.

`qwen3.5:4b` turns the evidence into a few words: "Talulah *is the half-sister of* Ch'en". With no evidence, or no clear answer, the label is "is related to".

Labels are written after the map draws, ten links at a time, the selected node's first. Each pair is cached, so a rebuild is instant.

## The stories timeline

Every story released on Global sits on one canvas, from the wiki's `Story/Movements` pages: Main Theme episodes, intermezzi, side stories and story collections. The 14 Movements group them, in the game's Score order, and the crossovers come after them.

- **Bands:** five, top to bottom: Main Theme, Intermezzi, Side Stories, Story Collections and Crossovers.
- **Edges:** only what the wiki curates. Sequels come from the infoboxes' previous and next fields, and "read first" branches from the Movement pages.
- **Release tab:** a time axis of Global start dates. Prologue to Episode 04 have no date on the wiki, so they take Global's launch day.
- **In-game tab:** columns by in-universe year, from a hand-corrected table (`backend/story_years.json`), with an "Undated" column for the rest. With one Movement picked, the stories run in Score order, and stories of other Movements linked to them sit faded at the edge.

Nodes in a band are packed into rows, so no two overlap. The canvas scrolls, and dragging its background pans it. Clicking an Episode ticks it and every Episode before it; any other story ticks on its own.

## Spoiler control

You tick the stories you have read; the app never guesses where you are. A term shows only once a story it appears in is ticked. Its stories come from three places:

- each story's synopsis;
- the story's teaser on its Movement page;
- a character page's own list of appearances, except an appearance under another name ("mentioned as Kashchey"), which would give away who someone is.

What follows from the rule:

- **Hidden terms** leave the map, and so does a node they leave without links.
- **Summaries** drop any sentence that names a hidden term.
- **Labels** show only once you have read a story both ends appear in, as "learned in" that story.
- **Your own keywords always show**, since you just saw them.
- **Tick all** shows everything, untagged terms included.
- **Corrections:** a term's **Hide this** and **Show anyway** fix a wrong tag.

**Fog of the Future** is an optional toggle on the stories canvas, for the titles themselves. With it on, only the stories you have read, the ones where a storyline starts (nothing to read before them) and the one step after either are drawn. The rest are covered, an edge into the fog fades out, and a covered story can't be ticked, so the way forward is one story at a time.

Ticks, corrections and the fog toggle are saved by the API in one file, `data/progress.json`, the moment they change, so they follow the backend: any browser pointed at it sees the same progress, and copying the file is the backup. There are no accounts; one backend has one progress file.

## Sessions

Each screenshot adds its keywords to the session's. A keyword shows the number of the screenshot that brought it, and **New session** clears the list. The session lasts as long as the tab.
