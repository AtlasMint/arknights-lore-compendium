"""SQLite cache of fetched wikitext with fetch timestamps. A page is fetched again after config.CACHE_TTL."""
import sqlite3
import time

from backend import config
from backend.scraper import wiki_client


def connect():
    config.DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def get_pages(titles):
    """{title: wikitext} from the cache, fetching whatever is missing or stale. Pages that don't exist are left out."""
    titles = list(dict.fromkeys(titles))
    fresh_after = time.time() - config.CACHE_TTL
    out = {}
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS pages (title TEXT PRIMARY KEY, wikitext TEXT NOT NULL, fetched_at REAL NOT NULL)")
        for title in titles:
            row = db.execute("SELECT wikitext FROM pages WHERE title = ? AND fetched_at > ?", (title, fresh_after)).fetchone()
            if row:
                out[title] = row[0]
        missing = [t for t in titles if t not in out]
        for i in range(0, len(missing), wiki_client.BATCH):
            fetched = wiki_client.fetch_wikitext(missing[i:i + wiki_client.BATCH])
            db.executemany("INSERT OR REPLACE INTO pages VALUES (?, ?, ?)", [(t, text, time.time()) for t, text in fetched.items()])
            db.commit()  # keep each batch even if a later one fails
            out.update(fetched)
    return out
