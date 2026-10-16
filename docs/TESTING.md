# Testing

## Offline tests

```bash
python -m tests.test_v0
python -m tests.test_v1
python -m tests.test_v2
python -m tests.test_v3
cd frontend && bun test
```

The Python tests run against a small fake wiki, and `test_v1` and `test_v3` stub the model, so they need no network and no Ollama. There is one per version:

| Test | Checks |
|---|---|
| `test_v0` | Term lookups, wikitext parsing, edge weights and pruning |
| `test_v1` | Keyword matching, the reader's request and reply, the reading cache, `POST /analyze` |
| `test_v2` | The speaker's extra weight in the ranking |
| `test_v3` | Node types, summaries and the story each sentence came from, the stories timeline and its tags, the years seed, labels, the new endpoints, the progress file |

`bun test` (`frontend/src/lore.test.js`) checks the spoiler rule and the summary rule, the Episode tick chain, the fog, the map's box collision, and that no two story nodes sit closer than the gap on either tab.

## The screenshot set

```bash
python -m tests.score_screenshots
```

This one needs Ollama. It runs the 28 labeled screenshots in `tests/screenshots/` through the reader and matcher, and prints the totals after a line per screenshot:

- whether the speaker was read right;
- how close the text came;
- the chip edits a user would still have to make: keywords missed, parked under needs-context, or extra.

`labels.json` holds each screenshot's speaker, text and expected keywords. Readings go through the cache, so a rerun with nothing changed is instant. Run it before and after any change to the matcher or the noise filter.

The committed images are 1280 px copies, the size the frontend uploads. Full-size originals can sit in `tests/screenshots/originals/`, which git ignores.

## CI

GitHub Actions ([.github/workflows/ci.yml](../.github/workflows/ci.yml)) runs on every push and pull request:

- the Python tests on Windows, macOS and Linux, with Python 3.12 and 3.14;
- the frontend's lint, `bun test` and build on all three.

CI never calls the wiki or Ollama.
