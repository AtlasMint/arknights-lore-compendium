"""Term index: every wiki page title and redirect -> canonical page, plus each page's categories.

    python -m backend.index.build_index    # refresh it; one pass of ~70 requests, about 2 minutes
"""
import json
import sys
from functools import cache

from backend import config
from backend.parser.terms import normalize
from backend.scraper import wiki_client
from backend.scraper.cache import connect

SCHEMA = "CREATE TABLE IF NOT EXISTS terms (title TEXT PRIMARY KEY, canonical TEXT NOT NULL, categories TEXT)"


def build():
    """Download every title, redirect and category, then swap them in as the new index in one transaction."""
    categories, redirects = {}, {}
    for page in wiki_client.all_pages():
        categories.setdefault(page["title"], set()).update(c["title"].removeprefix("Category:") for c in page.get("categories", []))
        redirects.update((r["title"], page["title"]) for r in page.get("redirects", []))
    with connect() as db:
        db.execute(SCHEMA)
        db.execute("DELETE FROM terms")
        db.executemany("INSERT INTO terms VALUES (?, ?, ?)", [(t, t, json.dumps(sorted(c))) for t, c in categories.items()])
        db.executemany("INSERT OR IGNORE INTO terms VALUES (?, ?, NULL)", redirects.items())
    _load.cache_clear()
    return len(categories), len(redirects)


def _rows():
    with connect() as db:
        db.execute(SCHEMA)
        return db.execute("SELECT title, canonical, categories FROM terms").fetchall()


@cache
def _load():
    """The whole index in memory (~19k rows): exact titles, case-folded titles, categories."""
    rows = _rows()
    if not rows:
        # ponytail: no lock, so two first requests at once would both build; fine for one user
        print("Term index is empty, building it (about 2 minutes)...", file=sys.stderr)
        build()
        rows = _rows()
    exact = {title: canonical for title, canonical, _ in rows}
    # Pages sort after redirects, so a real page wins when two titles differ only by case.
    folded = {title.casefold(): canonical for title, canonical, cats in sorted(rows, key=lambda r: r[2] is not None)}
    categories = {title: json.loads(cats) for title, _, cats in rows if cats is not None}
    return exact, folded, categories


def lookup(term):
    """Canonical page title for a term, matching titles and redirects in any case; None if it isn't on the wiki."""
    exact, folded, _ = _load()
    title = normalize(term)
    return exact.get(title) or folded.get(title.casefold())


def categories(title):
    """Visible wiki categories of a canonical page title."""
    return _load()[2].get(title, [])


if __name__ == "__main__":
    pages, redirects = build()
    print(f"Indexed {pages} pages and {redirects} redirects into {config.DB_PATH}")
