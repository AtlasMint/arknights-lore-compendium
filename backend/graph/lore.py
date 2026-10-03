"""What a /graph result needs for v3: each node's type, faction and summary, and the stories each term appears in."""
import re

from backend import stories
from backend.graph import builder
from backend.index import build_index as index
from backend.index import matcher
from backend.parser import terms, wikitext
from backend.scraper import cache

SUMMARY_SENTENCES = 4
# An appearance under another name doesn't reveal this one: "Episode 05 (mentioned as Kashchey)" on the Deathless Black
# Snake's page is the Snake before Episode 08 names it. Errs towards hiding: "(as a child)" is skipped too.
DISGUISED = re.compile(r"\((?:[^)]*\s)?as\s")


def named(sentence, targets):
    """Lore pages a sentence names: its links, plus titles written in it with a capital (the matcher's rule: "the
    silence here" is not Silence)."""
    found = {builder.resolve(t) for t in targets}
    found.update(title for title, phrase in matcher.scan(sentence) if not phrase.islower())
    return found - {None}


def page_texts(titles):
    """{title: [wikitext of each lore source page]} for the given lore pages, fetched in one go."""
    pages = cache.get_pages([s for t in titles for s in builder.sources(t)])
    return {t: [pages.get(s, "") for s in builder.sources(t)] for t in titles}


def faction(categories, lines):
    """The faction a character or operator belongs to: the first of its categories that is a faction page (operators
    carry one, Amiya -> Rhodes Island), else the first faction its infobox's affiliation links (NPCs: Talulah -> Reunion)."""
    candidates = list(categories) + [t for field, _, targets in lines if field == "affiliation" for t in targets]
    for candidate in candidates:
        title = builder.resolve(candidate)
        if title and terms.node_type(index.categories(title)) == "Faction":
            return title
    return None


def describe(graph):
    """Adds to each node its type, faction (characters, operators and factions) and summary sentences, to each link
    the stories both ends share, and a top-level `tags`: every node and every term a summary names -> the released
    stories it appears in, in Score order. An unknown story is left out, so a term only in unreleased stories is untagged.
    """
    texts = page_texts([n["id"] for n in graph["nodes"]])
    tags = {}
    for node in graph["nodes"]:
        title = node["id"]
        lines = [line for text in texts[title] for line in wikitext.infobox_lines(text)]
        appearances = {index.lookup(t) for field, line, targets in lines
                       if field == "appearance" and not DISGUISED.search(line) for t in targets}
        tags[title] = stories.tags(title, appearances - {None})
        node["type"] = terms.node_type(node["categories"])
        node["faction"] = title if node["type"] == "Faction" else (
            faction(node["categories"], lines) if node["type"] in ("Operator", "Character") else None)
        found = next((s for s in map(wikitext.sentences, texts[title]) if s), [])[:SUMMARY_SENTENCES]
        node["summary"] = [{"text": text, "terms": sorted(named(text, targets))} for text, targets in found]
        for sentence in node["summary"]:
            for term in sentence["terms"]:
                tags.setdefault(term, stories.tags(term))
    for link in graph["links"]:
        shared = set(tags[link["source"]]) & set(tags[link["target"]])
        link["stories"] = [s for s in tags[link["source"]] if s in shared]
    graph["tags"] = {term: found for term, found in tags.items() if found}
    return graph
