# v3: Richer Lore

**Theme:** graphs that explain connections, not just show them
**Outcome:** a player can screenshot their way through a chapter and end up with a labeled, spoiler-safe lore map.

## Goal

Make the graph genuinely useful for understanding the story: what each node is, how nodes relate, and without spoiling anything the player hasn't reached yet.

## Why a ticked list, not detection

The app can't hook into the game, so it never knows where the player is. Instead the player keeps a list of the stories they have finished, and the map is everything those stories introduced: a record of what was seen, not a readout of what is on screen now. Reading the stage code off screenshots was considered and dropped, since it can't be enforced and a progress list is what a recall tool wants anyway.

The model is Final Fantasy XVI's lore design ([GDC 2024 slides](https://media.gdcvault.com/gdc2024/Slides/GDC+slide+presentations/Aono_Momoka_DesigningActiveTime.pdf)). Its Active Time Lore panel is keyed to the current cutscene, which we can't do. But the Thousand Tomes (the archive you read back) and State of the Realm (the relationship chart) are progress-based, and those are what this version and [v5](v5-recall.md) borrow: entries that update as the story progresses, text written from a narrator's perspective, and one dictionary feeding every view.

## Tasks

### Node types
- [ ] Map wiki categories to types: Operator, Faction, Location, Event, Other
- [ ] Color and shape nodes by type, like unit symbols on a map legend
- [ ] Operators take their faction's colour instead, since "who belongs to which faction" is what the chart answers
- [ ] Legend and a filter to show or hide each type

### Node detail panel
- [ ] Click a node to see a short summary, its type, and a link to the wiki page
- [ ] Summaries come from the page intro, cleaned of wikitext

### Relationship labels
- [ ] For each edge in the final graph, pull the wiki sentences where both terms appear
- [ ] An LLM labels the relationship ("member of", "sibling of", "fought at", "leads")
- [ ] Labels are in narrator voice and name the story unit ("introduced in Chapter 3 as Talulah's lieutenant"), so every edge carries where it was learned
- [ ] Only label edges that survived pruning, which keeps the cost down
- [ ] Cache labels per term pair

### Stories timeline
- [ ] One canvas, not a checklist: stories are nodes on a left-to-right year axis, ticked by clicking (grey to green)
- [ ] Two tabs over the same nodes, edges and ticked set: **Release**, on global release dates, and **In-game**, on in-universe years
- [ ] Five bands top to bottom on the same axis: Main Theme, Intermezzi, Side Stories, Story Collections, Crossovers
- [ ] Release tab: a linear time axis from the Event and Episode infoboxes' global start dates (74 of 75 story pages carry it; Heart of Surging Flame keeps its infobox on its Part subpages instead). Data is complete, so this is the default tab
- [ ] In-game tab: in-universe years are known for only about half the stories. The wiki's Timeline page cites about 30 of the 75 under year headings, 19 of 71 synopsis pages open with a year, and the Timeline's crossover section dates 4, with 1090–1096 lumped into one block and Episodes 0–8 inside one fortnight
- [ ] So the in-game years live in a checked-in table, seeded once by script from those three sources and corrected by hand, with the wiki's own "ca." kept for estimated dates. When a story is cited under several years the latest wins, since the earlier ones are usually flashbacks. Hand-correcting beats the heuristic, which is the FF16 lesson again
- [ ] In-game tab columns are ordinal, not linear: "to 1096", then one per year, then "Undated" at the far right for the other half. Each column is as wide as it needs to be for its stories, so 1097 with nine Episodes gets the room and empty years take none. Inside a column, order by month where known, else by release order
- [ ] Inside a band, a node sits at its place on the axis and drops to the next row when it would overlap the previous one, on both tabs: greedy row packing, no force simulation, no overlaps by construction. Worst case is about seven side stories in one release year
- [ ] Edges are the infobox's `previous`/`next` chain, coloured by `arc` (66 of 75 stories have an arc, 52 a chain link). Chains are paths, so there are about as many edges as nodes and no hairball
- [ ] All edges drawn faint; hovering or selecting a node lights its whole arc and dims the rest
- [ ] Clicking an Episode ticks it and everything before it; clicking a ticked one unticks it and everything after. Other bands tick one node at a time
- [ ] Only stories already released on Global appear on either tab: a global start date in the past. The rest are left off, since they can't have been played
- [ ] Plain SVG drawn by React with d3's time scale for the axis; horizontal scroll when the canvas is wider than the screen

### Spoiler control
- [ ] Tag each term with every story unit it appears in (main chapter, intermezzo, side story, event), from the wiki's story pages
- [ ] Progress is ticked on the stories timeline above, one click per node
- [ ] A tick-all for players who don't care about spoilers; it also shows untagged terms
- [ ] Progress is the set of ticked stories, stored in the browser
- [ ] A term is visible if any story it appears in is ticked; untagged terms stay hidden
- [ ] The screenshot's own terms are never hidden, since the player just saw them; progress gates only the wiki expansion around them
- [ ] Node summaries drop any sentence that names a hidden term
- [ ] Edge labels hide when their story unit is unticked, even if both ends are visible
- [ ] Hidden nodes are removed entirely, not just greyed out
- [ ] Per-term hide-this and show-anyway overrides, stored in the browser, as the correction path for mistagging in either direction

### Session graphs
- [ ] Multiple screenshots add to one growing graph
- [ ] Show which screenshot introduced each keyword
- [ ] Clear or restart the session

## Done when

- Every node has a type and a summary
- Most edges have a sensible relationship label
- Ticking Chapter 5 and nothing else reliably hides terms, summary sentences and edge labels from later stories
- A Chapter 9 screenshot with only Chapter 5 ticked still shows its own keywords
- Every story released on Global is on both tabs, ticks carry across tabs, and no two nodes overlap on either
- Five screenshots from one chapter build into one coherent map

## Out of scope

Deployment, sharing, other game servers, and the recall features in [v5](v5-recall.md).

## Risks

| Risk | Mitigation |
|---|---|
| The LLM invents relationships | Only label from real wiki sentences; show "related" when unsure |
| Chapter data is incomplete | Untagged terms stay hidden unless tick-all is on |
| Automated tagging leaks spoilers or hides too much | Per-term overrides; FF16 hand-curated over 2000 points and still caught leaks in QA, so expect some |
| A summary sentence spoils without naming a hidden term | Accepted for now; the sentence filter catches the common case |
| Chain data has gaps (23 stories without a chain link; the 8 crossovers have no arc by design) | They sit as unlinked nodes and are still tickable |
| In-game years are known for only about half the stories, and some citations are flashbacks | The Undated column is honest about it; the years table is hand-corrected, not re-derived |
| Session graphs grow too big | Apply the same max-node pruning across the whole session |
