"""Build a lore graph, or look up a term, from the command line.

    python -m backend.cli --seeds "Amiya,Reunion" --depth 2
    python -m backend.cli --lookup "Reunion Movement"
"""
import argparse
import json
import sys

from backend import config
from backend.graph.builder import build_graph
from backend.index.build_index import lookup

parser = argparse.ArgumentParser(description="Seed keywords -> Arknights lore graph")
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--seeds", help='comma-separated wiki terms, e.g. "Amiya,Reunion"')
mode.add_argument("--lookup", metavar="TERM", help="print the canonical wiki page for a term or redirect")
parser.add_argument("--depth", type=int, default=config.DEPTH)
parser.add_argument("--max-nodes", type=int, default=config.MAX_NODES)
parser.add_argument("--json", action="store_true", help="print the D3 JSON instead of a ranked node list")
args = parser.parse_args()
sys.stdout.reconfigure(encoding="utf-8")  # redirected output on Windows defaults to cp1252, which has no "ł" for Młynar

if args.lookup:
    found = lookup(args.lookup)
    print(found or f"Not on the wiki: {args.lookup}")
    sys.exit(0 if found else 1)

# ponytail: commas split seeds, so a title with a comma in it can't be a seed; take a list if one is needed
terms = [t.strip() for t in args.seeds.split(",") if t.strip()]
seeds = [lookup(t) for t in terms]
if None in seeds:
    sys.exit("Not on the wiki: " + ", ".join(t for t, s in zip(terms, seeds) if s is None))

graph = build_graph(seeds, args.depth, args.max_nodes)
if args.json:
    print(json.dumps(graph))  # ASCII escapes survive any shell's re-encoding
else:
    for node in sorted(graph["nodes"], key=lambda n: -n["score"]):
        print(f"{node['score']:.4f} {'*' if node['seed'] else ' '} {node['id']}  ({', '.join(node['categories'][:4])})")
    print(f"{len(graph['nodes'])} nodes, {len(graph['links'])} links")
