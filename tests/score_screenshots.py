"""Score the screenshot -> keywords step on the labeled set in tests/screenshots/. Needs Ollama running.

    python -m tests.score_screenshots

labels.json is a list of {"file", "speaker", "text", "keywords"}: the name box and dialog as written, and
the wiki pages a fan would want as seeds. The number that matters is chip edits per screenshot: keywords
to add (missed, or found but parked under needs-context) plus keywords to remove. Readings come through
the cache, so a rerun with nothing changed is instant.
"""
import difflib
import json
from pathlib import Path

from backend.index import matcher
from backend.vision import reader

FOLDER = Path(__file__).parent / "screenshots"


def plain(text):
    """Straight apostrophes and single spaces, so a reading isn't marked wrong for the game's typography."""
    return " ".join(text.replace("’", "'").split())


def score(label):
    reading = reader.read((FOLDER / label["file"]).read_bytes())
    found = matcher.find(reading["speaker"], reading["text"])
    expected = set(label["keywords"])
    return {
        "speaker": plain(reading["speaker"]).casefold() == plain(label["speaker"]).casefold(),
        "text": difflib.SequenceMatcher(None, plain(reading["text"]), plain(label.get("text", ""))).ratio(),
        "missed": sorted(expected - set(found["keywords"]) - set(found["needs_context"])),
        "parked": sorted(expected & set(found["needs_context"])),
        "extra": sorted(set(found["keywords"]) - expected),
        "reading": reading,
    }


def main():
    labels = json.loads((FOLDER / "labels.json").read_text())
    results = [(label, score(label)) for label in labels]
    for label, r in results:
        line = f"{label['file']:28} speaker={'ok' if r['speaker'] else repr(r['reading']['speaker']):14} text={r['text']:.2f}"
        line += f"  edits={len(r['missed']) + len(r['parked']) + len(r['extra'])}"
        for key in ("missed", "parked", "extra"):
            if r[key]:
                line += f"  {key}={r[key]}"
        print(line)
    n = len(results)
    expected = sum(len(label["keywords"]) for label, _ in results)
    missed, parked, extra = (sum(len(r[key]) for _, r in results) for key in ("missed", "parked", "extra"))
    zero = sum(not (r["missed"] or r["parked"] or r["extra"]) for _, r in results)
    print(f"\n{n} screenshots. Speaker right: {sum(r['speaker'] for _, r in results)}/{n}. Text match: {sum(r['text'] for _, r in results) / n:.3f} mean.")
    print(f"Keywords: {expected - missed - parked}/{expected} found, {parked} parked under needs-context, {extra} extra. Zero edits: {zero}/{n}.")


if __name__ == "__main__":
    main()
