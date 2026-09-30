# v2: Accuracy

**Theme:** fewer wrong or missing keywords
**Outcome:** most screenshots need no manual edits to the keyword list.

## Goal

Make the screenshot-to-keywords step reliable, and measure it instead of eyeballing it.

## Tasks

### Test set (build this first)
- [ ] Collect 20–30 screenshots across different chapters, speakers, and backgrounds
- [ ] Label the correct keywords for each in `tests/screenshots/labels.json`
- [ ] Script that scores the pipeline: how many correct keywords were found, and how many wrong ones were added
- [ ] Record a baseline score from v1 before changing anything

### Fuzzy matching
- [ ] Use `rapidfuzz` to catch near-misses ("Amlya" → "Amiya")
- [ ] Give each match a confidence score
- [ ] Minimum-confidence cutoff, tuned against the test set
- [ ] Show low-confidence chips differently in the review UI

### Speaker priority
- [ ] Detect the speaker from the name box (the vision prompt already returns it)
- [ ] Speaker gets the top seed weight in the graph

### Region cropping
- [ ] `vision/cropper.py`: crop to the dialog band and name box before reading
- [ ] Handle the common aspect ratios (phones, tablets, emulators)
- [ ] Compare scores with and without cropping on the test set

### Swappable reading engines
- [ ] `vision/paddle_reader.py`: PaddleOCR as a free, local option
- [ ] Choose the engine in `config.py`
- [ ] Compare Gemini and PaddleOCR on accuracy, speed, and cost

### Ranking
- [ ] Score each keyword: match confidence × importance (PageRank from the global graph)
- [ ] Only the top N become seeds; the rest are shown as optional

## Done when

- The test set score clearly beats the v1 baseline
- Most test screenshots need zero manual chip edits
- There's a clear, measured answer for which reading engine is the default

## Out of scope

Relationship labels, spoiler control, and multiple screenshots.

## Risks

| Risk | Mitigation |
|---|---|
| Fuzzy matching adds false matches | Tune the cutoff against the test set, not by feel |
| Cropping breaks on unusual layouts | Fall back to the full image when the crop finds no text |
| Test set too small to trust | Grow it any time a real screenshot fails |
