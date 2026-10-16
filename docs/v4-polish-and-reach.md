# v4: Polish and Reach

**Theme:** make it usable by other people
**Outcome:** a deployed, mobile-friendly app players can share.

## Goal

Take it from a personal tool to something other Arknights players can open on their phone and use.

## Tasks

### Mobile-friendly UI
- [ ] Responsive layout; the screenshots come from phones anyway
- [ ] Touch-friendly graph: pinch to zoom, tap for details
- [ ] Upload straight from the phone's photo library

### Linked highlighting between the panel and the map
- [ ] Hovering a connection in the detail panel's **Connections** list lights that link and its two nodes on the map and dims everything else, the same look the map already gives a selected node's neighbourhood; moving off restores it
- [ ] The same on keyboard focus of the connection's name button, so it isn't mouse-only
- [ ] Clicking the name keeps doing what it does: it selects that node
- [ ] One piece of state, "the hovered link", read by the map's existing lit/dim classes; no second highlight style

### Sharing
- [ ] Save a graph and get a shareable link
- [ ] Read-only view for shared graphs
- [ ] Export as PNG or JSON

### Other game servers
- [ ] Support the CN, JP, and KR servers
- [ ] Pair the matching OCR language with a matching wiki (for example, PRTS for CN)
- [ ] A separate term index per language
- [ ] Optional: link the same character across languages
- [ ] Story-unit tags from v3 carry over per server; a term first appears at different points on each server, so the tag is the story unit, never a release date

### Deployment
- [ ] Frontend on GitHub Pages or Vercel
- [ ] Backend on Google Cloud Run
- [ ] Pre-built cache and term index shipped with the backend, so there's no cold start against the wiki
- [ ] Basic rate limiting on `/analyze` to protect the API budget

### Project hygiene
- [ ] README with a demo GIF, setup, and usage
- [ ] Credit the wiki and follow its content license
- [ ] Note that this is an unofficial fan project

## Done when

- A friend can open a link on their phone, upload a screenshot, and get a graph with no help
- Shared links work for people without an account
- At least one non-English server works end to end

## Risks

| Risk | Mitigation |
|---|---|
| Hosting and API costs grow with users | Rate limits, image-hash caching, and a free local OCR option |
| Wiki license requirements | Attribute the wiki clearly and keep summaries short |
| Non-English OCR is weaker | Measure it with a per-language test set before launching each server |
