"""BFS outward from the seeds over wiki links, into a weighted, directed lore graph."""
from collections import Counter
from itertools import combinations

import networkx as nx

from backend import config
from backend.graph import export, scoring
from backend.index import build_index as index
from backend.parser import terms, wikitext
from backend.scraper import cache

LORE_SUBPAGES = ("Story", "File")  # operator main pages are gameplay; their lore lives on these subpages


def resolve(target):
    """Link target -> the page it names, or None for red links, other namespaces and noise.

    Subpages fold into their parent page: Amiya/File -> Amiya.
    """
    title = index.lookup(target)
    if title and "/" in title:
        title = index.lookup(title.split("/")[0]) or title
    if title and not terms.is_noise(title, index.categories(title)):
        return title
    return None


def sources(title):
    """Pages whose text describes a node: its lore subpages if it has any, else the page itself."""
    subpages = [f"{title}/{s}" for s in LORE_SUBPAGES if index.lookup(f"{title}/{s}") == f"{title}/{s}"]
    return subpages or [title]


def build(seeds, depth=config.DEPTH, max_nodes=config.MAX_NODES):
    """Directed graph of the pages linked from the seeds, `depth` hops out.

    Each level expands at most `max_nodes` pages: the ones most linked from the level before.
    Edge weight: +1 per link, RECIPROCAL_BONUS when two pages link each other, and SECTION_BONUS
    for every section (on any fetched page) that links both ends.
    """
    G = nx.DiGraph()
    G.add_nodes_from(seeds)
    frontier, seen, sections = list(seeds), set(seeds), []
    for _ in range(depth):
        pages = cache.get_pages([s for node in frontier for s in sources(node)])
        for node in frontier:
            for source in sources(node):
                for _heading, targets in wikitext.parse(pages.get(source, ""))["sections"]:
                    found = [t for t in map(resolve, targets) if t and t != node]
                    for target, n in Counter(found).items():
                        G.add_edge(node, target, weight=G.get_edge_data(node, target, {"weight": 0})["weight"] + n)
                    sections.append(set(found))
        new = [n for n in G if n not in seen]
        seen.update(new)
        frontier = sorted(new, key=lambda n: G.in_degree(n, weight="weight"), reverse=True)[:max_nodes]

    for u, v, data in G.edges(data=True):
        if G.has_edge(v, u):
            data["weight"] += config.RECIPROCAL_BONUS
    for linked in sections:
        for a, b in combinations(linked, 2):
            for u, v in ((a, b), (b, a)):
                if G.has_edge(u, v):
                    G[u][v]["weight"] += config.SECTION_BONUS
    for n in G:
        G.nodes[n].update(seed=n in seeds, categories=index.categories(n))
    return G


def build_graph(seeds, depth=config.DEPTH, max_nodes=config.MAX_NODES):
    """Canonical seed titles -> D3 JSON of the pruned lore graph."""
    seeds = list(dict.fromkeys(seeds))
    return export.to_d3(scoring.prune(build(seeds, depth, max_nodes), seeds, max_nodes))
