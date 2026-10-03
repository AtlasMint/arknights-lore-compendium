"""HTTP API for the frontend.

    flask --app backend.app run --port 5001    # macOS AirPlay already listens on 5000
"""
from flask import Flask, request

from backend import config, stories
from backend.graph import lore
from backend.graph.builder import build_graph
from backend.index import matcher
from backend.index.build_index import lookup, suggest
from backend.scraper import cache
from backend.vision import reader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024  # bigger uploads get too_large's 413


def image_type(data):
    """"image/png", "image/jpeg" or "image/webp" from the file's own bytes, never the name or type the client sent."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@app.get("/graph")
def graph():
    """GET /graph?seeds=Amiya,Reunion&depth=1&speaker=Amiya -> {"nodes": [...], "links": [...], "tags": {...}}

    `speaker` is optional: if it resolves to one of the seeds, that seed weighs more in the ranking.
    """
    terms = [t.strip() for t in request.args.get("seeds", "").split(",") if t.strip()]
    depth = request.args.get("depth", config.DEPTH, type=int)
    if not 1 <= len(terms) <= 10 or any(len(t) > 100 for t in terms) or not 1 <= depth <= 3:
        return {"error": "Give 1 to 10 comma-separated seeds (up to 100 characters each) and a depth from 1 to 3."}, 400
    seeds = [lookup(t) for t in terms]
    if None in seeds:
        return {"error": "Not on the wiki: " + ", ".join(t for t, s in zip(terms, seeds) if s is None)}, 400
    speaker = lookup(request.args.get("speaker", "")[:100])
    return lore.describe(build_graph(seeds, depth, speaker=speaker if speaker in seeds else None))


@app.post("/analyze")
def analyze():
    """POST /analyze with an "image" file -> {"speaker", "text", "keywords": [...], "needs_context": [...]}"""
    upload = request.files.get("image")
    image = upload.read() if upload else b""
    if not image_type(image):
        return {"error": "Upload a PNG, JPEG or WebP screenshot."}, 415
    try:
        reading = reader.read(image)
    except (OSError, RuntimeError, ValueError) as e:  # Ollama down or refusing, a timeout, or a reply that isn't JSON
        return {"error": f"Couldn't read the screenshot: {e}"}, 502
    return {**reading, **matcher.find(reading["speaker"], reading["text"])}


@app.errorhandler(413)
def too_large(_):
    return {"error": f"Screenshots can be up to {config.MAX_UPLOAD_MB} MB."}, 413


@app.get("/terms")
def terms():
    """GET /terms?prefix=ami -> ["Amiya", ...], for the keyword box's autocomplete."""
    return suggest(request.args.get("prefix", "")[:100])


@app.get("/stories")
def timeline():
    """GET /stories -> {"movements", "acts", "stories", "edges"}: every story released on Global, for ticking progress."""
    return stories.timeline()


@app.get("/icon/<code>")
def icon(code):
    """GET /icon/AE -> a Movement's 90x90 icon, fetched from the wiki once."""
    if code not in {m["code"] for m in stories.timeline()["movements"]}:
        return {"error": "No such Movement."}, 404
    try:
        data = cache.get_file(f"{code}_arc.png")
    except OSError as e:
        return {"error": f"Couldn't fetch the icon: {e}"}, 502
    return data, {"Content-Type": "image/png", "Cache-Control": "max-age=604800"}
