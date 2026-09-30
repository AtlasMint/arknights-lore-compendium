"""NetworkX graph -> D3 force-graph JSON."""


def to_d3(G):
    """{"nodes": [{id, seed, categories, score}], "links": [{source, target, weight}]}.

    Links between two pages in both directions become one link with the weights summed.
    """
    weights = {}
    for u, v, w in G.edges(data="weight"):
        pair = (v, u) if (v, u) in weights else (u, v)
        weights[pair] = weights.get(pair, 0) + w
    return {
        "nodes": [{"id": n, **attrs} for n, attrs in G.nodes(data=True)],
        "links": [{"source": u, "target": v, "weight": w} for (u, v), w in weights.items()],
    }
