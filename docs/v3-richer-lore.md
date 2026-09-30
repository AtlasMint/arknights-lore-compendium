# v3: Richer Lore

**Theme:** graphs that explain connections, not just show them
**Outcome:** a player can screenshot their way through a chapter and end up with a labeled, spoiler-safe lore map.

## Goal

Make the graph genuinely useful for understanding the story: what each node is, how nodes relate, and without spoiling anything the player hasn't reached yet.

## Tasks

### Node types
- [ ] Map wiki categories to types: Operator, Faction, Location, Event, Other
- [ ] Color and shape nodes by type, like unit symbols on a map legend
- [ ] Legend and a filter to show or hide each type

### Node detail panel
- [ ] Click a node to see a short summary, its type, and a link to the wiki page
- [ ] Summaries come from the page intro, cleaned of wikitext

### Relationship labels
- [ ] For each edge in the final graph, pull the wiki sentences where both terms appear
- [ ] An LLM labels the relationship ("member of", "sibling of", "fought at", "leads")
- [ ] Only label edges that survived pruning, which keeps the cost down
- [ ] Cache labels per term pair

### Spoiler control
- [ ] Tag each term with the story chapter where it first appears
- [ ] Source the chapter data from the wiki's story and event pages
- [ ] A "how far have you played" setting hides anything past that point
- [ ] Hidden nodes are removed entirely, not just greyed out

### Session graphs
- [ ] Multiple screenshots add to one growing graph
- [ ] Show which screenshot introduced each keyword
- [ ] Clear or restart the session

## Done when

- Every node has a type and a summary
- Most edges have a sensible relationship label
- Setting an early chapter reliably hides later-chapter terms
- Five screenshots from one chapter build into one coherent map

## Out of scope

Deployment, sharing, and other game servers.

## Risks

| Risk | Mitigation |
|---|---|
| The LLM invents relationships | Only label from real wiki sentences; show "related" when unsure |
| Chapter data is incomplete | Untagged terms default to hidden when spoiler mode is on |
| Session graphs grow too big | Apply the same max-node pruning across the whole session |
