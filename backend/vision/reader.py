"""Screenshot -> {"speaker", "text"}, reading each image only once.

Every reading engine is a module with read(image_bytes) -> {"speaker", "text"}. v1.1 has one,
ollama_reader. Readings are cached in SQLite by the image's SHA-256, so the same screenshot is
never read twice.
"""
import hashlib
import json

from backend.scraper.cache import connect
from backend.vision import ollama_reader


def read(image):
    digest = hashlib.sha256(image).hexdigest()
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS readings (sha256 TEXT PRIMARY KEY, reading TEXT NOT NULL)")
        row = db.execute("SELECT reading FROM readings WHERE sha256 = ?", (digest,)).fetchone()
    if row:
        return json.loads(row[0])
    reading = ollama_reader.read(image)
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO readings VALUES (?, ?)", (digest, json.dumps(reading)))
    return reading
