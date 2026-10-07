"""HTTP API for the frontend.

    flask --app backend.app run --port 5001    # macOS AirPlay already listens on 5000
"""
import json
import os

from flask import Flask, request

from backend import config, stories
from backend.graph import labels, lore
from backend.graph.builder import build_graph, resolve
from backend.index import matcher
from backend.index.build_index import lookup, suggest
from backend.scraper import cache
from backend.vision import reader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024  # bigger uploads get too_large's 413
MAX_PAIRS = 20  # links one /labels call may name: about 40 seconds of the label model's time when none is cached


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

    `speaker` is optional and may list several names, one per screenshot: those that resolve to seeds weigh more in
    the ranking.
    """
    terms = [t.strip() for t in request.args.get("seeds", "").split(",") if t.strip()]
    depth = request.args.get("depth", config.DEPTH, type=int)
    if not 1 <= len(terms) <= config.MAX_SEEDS or any(len(t) > 100 for t in terms) or not 1 <= depth <= 3:
        return {"error": f"Give 1 to {config.MAX_SEEDS} comma-separated seeds (up to 100 characters each) and a depth from 1 to 3."}, 400
    seeds = [lookup(t) for t in terms]
    if None in seeds:
        return {"error": "Not on the wiki: " + ", ".join(t for t, s in zip(terms, seeds) if s is None)}, 400
    speakers = {lookup(s[:100]) for s in request.args.get("speaker", "").split(",")[:config.MAX_SEEDS]}
    return lore.describe(build_graph(seeds, depth, speakers=speakers & set(seeds)))


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


@app.post("/labels")
def relationships():
    """POST /labels {"pairs": [["Talulah", "Ch'en"], ...]} -> {"labels": [{"from", "relation", "to"}, ...]}, in order."""
    pairs = (request.get_json(silent=True) or {}).get("pairs")
    if (not isinstance(pairs, list) or not 1 <= len(pairs) <= MAX_PAIRS
            or not all(isinstance(p, list) and len(p) == 2 and all(isinstance(t, str) and resolve(t[:100]) == t for t in p)
                       for p in pairs)):
        return {"error": f"Give 1 to {MAX_PAIRS} pairs of lore page titles."}, 400
    try:
        return {"labels": [labels.label(a, b) for a, b in pairs]}
    except (OSError, RuntimeError) as e:
        return {"error": f"Couldn't label the links: {e}"}, 502


def valid_progress(body):
    """The progress a client sent, if it is what the file holds: ticked story titles, hide-or-show overrides by term,
    and the fog toggle. None for anything else, so the file only ever holds that shape."""
    if not isinstance(body, dict):
        return None
    ticked, overrides, fog = body.get("ticked", []), body.get("overrides", {}), body.get("fog", False)
    titles = lambda xs: all(isinstance(x, str) and len(x) <= 200 for x in xs)
    if not (isinstance(ticked, list) and len(ticked) <= 1000 and titles(ticked)
            and isinstance(overrides, dict) and len(overrides) <= 10000 and titles(overrides)
            and all(v in ("hide", "show") for v in overrides.values()) and isinstance(fog, bool)):
        return None
    return {"ticked": ticked, "overrides": overrides, "fog": fog}


@app.get("/progress")
def progress():
    """GET /progress -> {"ticked": [...], "overrides": {...}, "fog": false} from the progress file; 404 if there is none yet."""
    try:
        saved = valid_progress(json.loads(config.PROGRESS_PATH.read_text("utf-8")))
    except FileNotFoundError:
        return {"error": "No progress saved yet."}, 404
    except (OSError, ValueError) as e:
        return {"error": f"Couldn't read {config.PROGRESS_PATH}: {e}"}, 500
    if saved is None:
        return {"error": f"{config.PROGRESS_PATH} isn't a progress file. Fix it or move it away."}, 500
    return saved


@app.put("/progress")
def save_progress():
    """PUT /progress with the same object -> saved to the progress file, whole or not at all, and echoed back."""
    body = valid_progress(request.get_json(silent=True))
    if body is None:
        return {"error": 'Send {"ticked": [titles], "overrides": {term: "hide" or "show"}, "fog": true or false}.'}, 400
    config.PROGRESS_PATH.parent.mkdir(exist_ok=True)
    draft = config.PROGRESS_PATH.with_suffix(".tmp")
    draft.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", "utf-8")
    os.replace(draft, config.PROGRESS_PATH)  # the old file stays whole until the new one is complete
    return body
