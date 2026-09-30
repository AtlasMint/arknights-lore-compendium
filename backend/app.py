"""HTTP API for the frontend.

    flask --app backend.app run --port 5001    # macOS AirPlay already listens on 5000
"""
from flask import Flask, request

from backend import config
from backend.graph.builder import build_graph
from backend.index.build_index import lookup

app = Flask(__name__)


@app.get("/graph")
def graph():
    """GET /graph?seeds=Amiya,Reunion&depth=2 -> {"nodes": [...], "links": [...]}"""
    terms = [t.strip() for t in request.args.get("seeds", "").split(",") if t.strip()]
    depth = request.args.get("depth", config.DEPTH, type=int)
    if not 1 <= len(terms) <= 10 or any(len(t) > 100 for t in terms) or not 1 <= depth <= 3:
        return {"error": "Give 1 to 10 comma-separated seeds (up to 100 characters each) and a depth from 1 to 3."}, 400
    seeds = [lookup(t) for t in terms]
    if None in seeds:
        return {"error": "Not on the wiki: " + ", ".join(t for t, s in zip(terms, seeds) if s is None)}, 400
    return build_graph(seeds, depth)
