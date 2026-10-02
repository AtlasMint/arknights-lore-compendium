"""PageRank from the seeds, then keep the top-scoring nodes."""
import networkx as nx


def prune(G, seeds, max_nodes, weights=None):
    """Keep the `max_nodes` best nodes by personalized PageRank. Seeds are always kept.

    The random walk restarts at the seeds, so closeness to them counts, not just how often the
    whole wiki links a page. `weights` ({seed: restart share}, 1 each by default) tilts it towards
    one seed: the speaker of a screenshot. Nodes left without edges after pruning are dropped.
    """
    score = nx.pagerank(G, personalization=weights or dict.fromkeys(seeds, 1), weight="weight")
    others = sorted((n for n in G if n not in seeds), key=score.get, reverse=True)
    H = G.subgraph([*seeds, *others[:max(0, max_nodes - len(seeds))]]).copy()
    H.remove_nodes_from([n for n in list(nx.isolates(H)) if n not in seeds])
    nx.set_node_attributes(H, score, "score")
    return H
