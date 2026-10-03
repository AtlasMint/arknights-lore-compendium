# v5: Recall

**Theme:** remembering what you've seen
**Outcome:** the session graph reads back like a lore archive: what changed when, searchable, and replayable chapter by chapter.

## Goal

[v3](archive/v3-richer-lore.md) keys everything to the stories the player has ticked. This version uses that same data to answer "what did I learn, and when". It is the Thousand Tomes and State of the Realm half of Final Fantasy XVI's lore design, where entries update as the story progresses and the relationship chart can be stepped through history.

## Tasks

### What's new after a tick
- [ ] When a story is ticked, show the nodes and edges that just became visible and the summaries that gained sentences
- [ ] One diff of the visible set before and after; no extra data
- [ ] Keep the last few "what's new" lists so the player can reread them

### Timeline scrubber
- [ ] A cursor dragged along the v3 stories timeline's Release tab, whose dates are complete: the session graph becomes "the map as of that date", using only stories ticked and released before it
- [ ] One filter over the same visibility rule as v3

### Search
- [ ] A search box over visible nodes, by name and the aliases the crawl already collects as redirects
- [ ] Results open the node's detail panel

## Done when

- Ticking a new chapter shows a short, correct list of what it added
- Scrubbing back to an early chapter shows the same map the player had then
- Search finds any visible node by any of its wiki redirects

## Out of scope

Points or EXP for collecting entries, a geographic situation map, and placeholder entries for unnamed "???" speakers (the wiki has no reveal data to drive them).

## Risks

| Risk | Mitigation |
|---|---|
| "What's new" is noisy for a big chapter | Cap it and sort by importance, reusing the graph's ranking |
| Scrubber is slow on a large session | It is the v3 filter over cached data; measure before optimising |
