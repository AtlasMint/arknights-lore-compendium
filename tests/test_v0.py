"""Offline checks for the v0 engine: fake wiki in, exact index lookups and edge weights out.

    python -m tests.test_v0
"""
import tempfile
from pathlib import Path

from backend import config
from backend.graph import builder, export, scoring
from backend.index import build_index
from backend.parser import terms, wikitext
from backend.scraper import cache, wiki_client

config.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"

# A tiny wiki. Alpha is an operator: gameplay main page, lore on Alpha/Story and Alpha/File.
PAGES = {
    "Alpha": "[[Gameplay]] [[Zeta]]",
    "Alpha/Story": "{{Character infobox|affiliation = [[Beta Corp]]|family = [[Gamma]] (sister)}}\n"
                   "==Plot==\n[[Gamma]] and [[beta corp|the corp]] meet at [[Delta]].<ref>[[1-1]]</ref> [[Gameplay]]",
    "Alpha/File": "[[Gamma]]",
    "Gamma": "[[Alpha]] {{Main|Delta}}",
    "Beta Corp": "[[Alpha/File|Alpha's file]]",
    "Delta": "",
}
wiki_client.all_pages = lambda: iter([
    {"title": "Alpha", "categories": [{"title": "Category:5-star"}]},
    {"title": "Alpha", "redirects": [{"title": "Alfa"}]},  # same page again, as when continuation splits it
    {"title": "Alpha/Story"}, {"title": "Alpha/File"}, {"title": "Gamma"}, {"title": "Delta"}, {"title": "Zeta"},
    {"title": "Beta Corp", "redirects": [{"title": "The Corp"}]},
    {"title": "Gameplay", "categories": [{"title": "Category:Mechanics"}]},
    {"title": "1-1", "categories": [{"title": "Category:Main Theme operations"}]},
])
cache.get_pages = lambda titles: {t: PAGES[t] for t in titles if t in PAGES}
build_index.build()


def test_normalize():
    assert terms.normalize(" rhodes_island#History") == "Rhodes island"
    assert terms.normalize(":Category:Lore") == "Category:Lore"
    assert terms.normalize("#Talent") == ""


def test_lookup():
    assert build_index.lookup("Alpha") == "Alpha"
    assert build_index.lookup("alfa") == "Alpha"  # redirect, any case
    assert build_index.lookup("The_Corp#Members") == "Beta Corp"
    assert build_index.lookup("Nope") is None
    assert build_index.categories("Alpha") == ["5-star"]  # merged across chunks


def test_parse():
    parsed = wikitext.parse(PAGES["Alpha/Story"])
    assert [h for h, _ in parsed["sections"]] == ["", "Plot"]
    assert "1-1" not in parsed["sections"][1][1]  # <ref> citations dropped
    assert parsed["infobox"] == {"affiliation": "Beta Corp", "family": "Gamma (sister)"}


def test_graph_weights():
    G = builder.build(["Alpha"], depth=2)
    weights = {(u, v): w for u, v, w in G.edges(data="weight")}
    # Alpha's links come from its lore subpages; noise, red links and the gameplay page are gone.
    # Alpha->Gamma: 3 links + reciprocal 2. Alpha->Delta: 1 link + 1 section shared with Delta on Gamma's page.
    # Gamma->Delta: 1 link + 1 section on Alpha/Story. Beta Corp links Alpha/File, which folds into Alpha.
    assert weights == {("Alpha", "Gamma"): 5, ("Gamma", "Alpha"): 3, ("Alpha", "Beta Corp"): 4,
                       ("Beta Corp", "Alpha"): 3, ("Alpha", "Delta"): 2, ("Gamma", "Delta"): 2}
    assert G.nodes["Alpha"]["seed"] and not G.nodes["Gamma"]["seed"]

    kept = scoring.prune(G, ["Alpha"], max_nodes=3)
    assert set(kept) == {"Alpha", "Gamma", "Beta Corp"}
    assert set(scoring.prune(G, ["Delta"], max_nodes=1)) == {"Delta"}  # seeds survive, even alone

    links = {frozenset((l["source"], l["target"])): l["weight"] for l in export.to_d3(G)["links"]}
    assert links[frozenset(("Alpha", "Gamma"))] == 8  # both directions merged into one link


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
