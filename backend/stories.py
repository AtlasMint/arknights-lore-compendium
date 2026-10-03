"""The stories timeline and spoiler tags: every story released on Global, grouped into the game's Movements as the wiki's
Story/Movements pages list them, plus the crossovers; and the stories each lore page appears in.

    python -m backend.stories    # print in-game years seeded from the wiki, to merge by hand into story_years.json
"""
import datetime
import functools
import json
import re
from collections import defaultdict
from html import unescape
from pathlib import Path

import mwparserfromhell

from backend import config
from backend.graph.builder import resolve
from backend.index import build_index as index
from backend.parser import wikitext
from backend.scraper import cache

MOVEMENTS = "Story/Movements"
# Bands top to bottom, by wiki category. A crossover is a collaboration event with a story: the game and the wiki
# treat all eight as non-canon, and none is in a Movement.
BANDS = {"Episodes": "main", "Intermezzi": "intermezzo", "Side Stories": "side", "Story Collections": "collection"}
CROSSOVER = "Collaboration events"
# In-game years, hand-corrected from what main() seeds: "1097", or "ca. 1098" where the wiki estimates.
YEARS = Path(__file__).with_name("story_years.json")
YEAR = re.compile(r"\b(1[01]\d\d)\b")


def _param(template, name):
    return template.get(name).value if template.has(name) else mwparserfromhell.parse("")


def _infobox(text):
    return next((t for t in mwparserfromhell.parse(text).filter_templates() if str(t.name).strip().lower().endswith("infobox")), None)


def _date(template, *names):
    """"2024-10-10" from the first of the infobox fields that holds a yyyy/mm/dd date, else None."""
    for name in names:
        if template is not None and (m := re.search(r"(\d{4})/(\d\d)/(\d\d)", str(_param(template, name)))):
            return "-".join(m.groups())
    return None


@functools.cache
def _load():
    """Every story the Movement pages list and every crossover, released or not, with its synopsis links.

    ponytail: cached for the process, so a dev server running across a week keeps last week's data; restart to refresh.
    """
    names = re.findall(r"\{\{:" + MOVEMENTS + r"/([^}|]+)\}\}", cache.get_pages([MOVEMENTS])[MOVEMENTS])
    pages = cache.get_pages([f"{MOVEMENTS}/{name}" for name in names])
    movements, acts, stories, links = [], [], [], defaultdict(set)
    for name in names:
        act = None
        for t in mwparserfromhell.parse(pages[f"{MOVEMENTS}/{name}"]).filter_templates():
            kind = str(t.name).strip()
            if kind == "Timeline head":
                code = _param(t, "arc").strip_code().strip()
                movements.append({"code": code, "name": name, "intro": _param(t, "intro").strip_code().strip()})
            elif kind == "Timeline cell" and t.has("act"):
                act = f"Act {_param(t, 'act').strip_code().strip()}: {_param(t, 'name').strip_code().strip()}"
            elif kind == "Timeline cell":
                shown = _param(t, "name").strip_code().strip()
                story = index.lookup(_param(t, "link").strip_code().strip() or shown)  # Babel -> Babel (event)
                if story is None:
                    continue
                if act:
                    acts.append({"name": act, "first": story})
                    act = None
                teaser = _param(t, "intro")
                links[story].update(str(link.title) for link in teaser.filter_wikilinks())
                stories.append({"id": story, "name": shown, "subtitle": _param(t, "subtitle").strip_code().strip(),
                                "movement": code, "teaser": teaser.strip_code().strip(),
                                # ponytail: comma-separated, so a related story with a comma in its name (So Long, Adele)
                                # would split; none is listed as related yet
                                "related": [r.strip() for r in _param(t, "related").strip_code().split(",") if r.strip()]})
    crossovers = sorted(t for t in index.titles() if CROSSOVER in index.categories(t)
                        and {"Side Stories", "Story Collections"} & set(index.categories(t)))
    stories += [{"id": t, "name": t, "subtitle": "", "movement": None, "teaser": "", "related": []} for t in crossovers]

    ids = [s["id"] for s in stories]
    texts = cache.get_pages(ids + [f"{i}/Synopsis" for i in ids])
    named = {s["name"]: s["id"] for s in stories}  # infoboxes call a story by its Movement name: Pinus Sylvestris
    find = lambda name: named.get(name) or index.lookup(name)
    for s in stories:
        infobox = _infobox(texts.get(s["id"], ""))
        if infobox is None:  # Heart of Surging Flame keeps an infobox on each Part subpage
            parts = re.findall(r"\{\{:(" + re.escape(s["id"]) + r"/[^}|]+)\}\}", texts.get(s["id"], ""))
            starts = [_date(_infobox(text), "globalstart") for text in cache.get_pages(parts).values()]
            s["start"] = min(filter(None, starts), default=None)
        else:
            s["start"] = _date(infobox, "global", "globalstart")
        s["band"] = "crossover" if s["movement"] is None else next(
            (BANDS[c] for c in index.categories(s["id"]) if c in BANDS), "side")
        named_in = lambda *fields: [find(_param(infobox, f).strip_code().strip()) for f in fields] if infobox is not None else []
        s["next"], s["previous"] = named_in("next"), named_in("previous", "prev")  # Episodes say prev, events previous
        s["related"] = [find(r) for r in s["related"]]
        for _heading, targets in wikitext.parse(texts.get(f"{s['id']}/Synopsis", ""))["sections"]:
            links[s["id"]].update(targets)
    # Episodes without a Global date that come before a dated one were in the game at launch.
    episodes = [s for s in stories if s["band"] == "main"]
    for i, s in enumerate(episodes):
        if not s["start"] and any(e["start"] for e in episodes[i + 1:]):
            s["start"] = config.GLOBAL_LAUNCH
    crossovers = sorted((s for s in stories if s["band"] == "crossover"), key=lambda s: s["start"] or "9")
    stories = [s for s in stories if s["band"] != "crossover"] + crossovers
    for order, s in enumerate(stories):
        s["order"] = order  # the Score's order: Movement by Movement, then the crossovers by release
    return {"movements": movements, "acts": acts, "stories": stories, "links": links}


def released(today=None):
    """Stories out on Global by `today`: a Global start date on or before it."""
    today = (today or datetime.date.today()).isoformat()
    return [s for s in _load()["stories"] if s["start"] and s["start"] <= today]


def timeline(today=None):
    """{"movements", "acts", "stories", "edges"} for the stories timeline: released stories only, in Score order.

    Edges are curated on the wiki, never inferred: "sequel" from the infoboxes' previous and next, "related" from the
    Movement pages, the stories the game recommends reading first.
    """
    stories = released(today)
    ids = {s["id"] for s in stories}
    years = json.loads(YEARS.read_text(encoding="utf-8"))
    edges = {}
    for s in stories:
        for a, b, kind in ([(p, s["id"], "sequel") for p in s["previous"]] + [(s["id"], n, "sequel") for n in s["next"]]
                           + [(r, s["id"], "related") for r in s["related"]]):
            if a in ids and b in ids and a != b:
                edges.setdefault(frozenset((a, b)), {"source": a, "target": b, "kind": kind})
    keep = ("id", "name", "subtitle", "movement", "band", "start", "order", "teaser")
    return {
        "movements": _load()["movements"],
        "acts": [a for a in _load()["acts"] if a["first"] in ids],
        "stories": [{**{k: s[k] for k in keep}, "year": years.get(s["id"])} for s in stories],
        "edges": list(edges.values()),
    }


@functools.cache
def _tags():
    """Lore page -> the stories it appears in: the pages its synopsis and its Movement teaser link, and the story itself."""
    tags = defaultdict(set)
    for story, targets in _load()["links"].items():
        tags[story].add(story)
        for target in targets:
            if title := resolve(target):
                tags[title].add(story)
    return tags


def tags(title, appearances=()):
    """Released stories that `title` appears in, in Score order. `appearances` adds the stories a character page's
    infobox lists, already resolved to titles."""
    known = {s["id"]: s["order"] for s in released()}
    return sorted((_tags().get(title, set()) | set(appearances)) & known.keys(), key=known.get)


def seed_years():
    """{story: "1097" or "ca. 1098"} from three wiki sources, the latest year winning, since an earlier one is usually a
    flashback: stories linked under a year heading of the Arknights Timeline page, synopses that open with a year,
    and the Timeline's crossover section. Decade and range headings ("1080s", "1090–1096") give their last year."""
    ids = {s["id"] for s in _load()["stories"]}
    found = defaultdict(list)  # story -> [(year, estimated)]
    year, crossover = None, False
    for line in cache.get_pages(["Arknights Timeline"])["Arknights Timeline"].splitlines():
        if heading := re.fullmatch(r"(=+)\s*(.*?)\s*=+\s*", line):
            years = re.findall(r"\d{3,4}", unescape(heading[2]))
            year = int(years[-1]) + (9 if heading[2].endswith("0s") else 0) if years else None
            crossover = "Crossover" in heading[2] or (crossover if len(heading[1]) > 2 else False)
            continue
        plain, links = wikitext.plain(mwparserfromhell.parse(line))  # without the notes and citations, which name
        estimated = "ca." in plain                                     # other stories in passing
        when = int(max(YEAR.findall(plain))) if crossover and YEAR.search(plain) else year
        for _shown, target in links:
            story = index.lookup(target.split("/")[0].split("#")[0])
            if when and story in ids:
                found[story].append((when, estimated))
    synopses = cache.get_pages([f"{i}/Synopsis" for i in ids])
    for story in ids:
        text = " ".join(sentence for sentence, _ in wikitext.sentences(synopses.get(f"{story}/Synopsis", "")))
        if m := YEAR.search(text[:300]):
            found[story].append((int(m[1]), False))
    order = {s["id"]: s["order"] for s in _load()["stories"]}
    best = {story: max(years, key=lambda y: (y[0], not y[1])) for story, years in found.items()}  # exact beats "ca."
    return {story: ("ca. " if est else "") + str(y) for story, (y, est) in sorted(best.items(), key=lambda kv: order[kv[0]])}


if __name__ == "__main__":
    print(json.dumps(seed_years(), indent=1, ensure_ascii=False))
