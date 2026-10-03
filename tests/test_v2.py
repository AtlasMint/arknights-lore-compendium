"""Offline checks for v2: the speaker's extra weight in the graph. The fake wiki comes from test_v0.

    python -m tests.test_v2
"""
import tests.test_v0  # noqa: F401  builds the fake index and stubs the wiki on import

from backend.graph import builder, scoring


def test_speaker_weight():
    G = builder.build(["Alpha", "Delta"], depth=2)
    plain = dict(scoring.prune(G, ["Alpha", "Delta"], max_nodes=3).nodes(data="score"))
    tilted = dict(scoring.prune(G, ["Alpha", "Delta"], max_nodes=3, weights={"Alpha": 1, "Delta": 3}).nodes(data="score"))
    assert tilted["Delta"] > plain["Delta"] and tilted["Alpha"] < plain["Alpha"]
    graph = builder.build_graph(["Alpha", "Delta"], speakers={"Delta"})
    assert {n["id"]: n["seed"] for n in graph["nodes"]}["Delta"]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
