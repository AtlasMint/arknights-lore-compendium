# v1: Screenshot MVP

**Theme:** screenshot → graph, end to end
**Outcome:** upload a dialog screenshot and see a relevant lore network.

## Goal

The simplest version of the full idea that works. Accuracy can be rough: a review step lets the user fix keywords by hand before the graph is built.

## Flow

```
Upload → Gemini reads text → match against term index → user reviews chips → v0 graph
```

## Tasks

### Upload
- [ ] Frontend: drag-and-drop or file picker, with an image preview
- [ ] Flask `POST /analyze`: accept an image, validate type and size

### Reading text
- [ ] `vision/reader.py`: a common interface, `read(image) → {speaker, text}`
- [ ] `vision/gemini_reader.py`: send the image to a Gemini Flash model
- [ ] Prompt asks for JSON only: speaker name and dialog text, no commentary
- [ ] Parse the JSON safely (strip code fences, fall back on failure)
- [ ] API key in `.env`, never committed

### Finding keywords
- [ ] `index/matcher.py`: scan the text for term-index matches
- [ ] Longest match wins ("Rhodes Island" beats "Island")
- [ ] Case-insensitive matching, with the canonical title returned
- [ ] The speaker name is always included as a keyword if it matches

### Review step
- [ ] Show the found keywords as chips: remove with a click, add with a text box
- [ ] Autocomplete for the add box, powered by the term index
- [ ] "Build graph" button sends the confirmed keywords to `/graph`

### Graph
- [ ] Reuse v0 as-is
- [ ] Highlight the keywords that came from the screenshot

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
