"""MediaWiki API client: descriptive User-Agent, about one request per second, continuation followed."""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from backend import config

BATCH = 50  # most titles one query may name without a bot account
_lock = threading.Lock()
_last = 0.0


def _get(params):
    global _last
    url = config.WIKI_API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    request = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    for attempt in range(4):
        with _lock:  # ponytail: one process-wide lock, so every thread shares the same 1 req/s budget
            time.sleep(max(0.0, _last + config.REQUEST_DELAY - time.monotonic()))
            _last = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)
            break
        except OSError as e:  # URLError, HTTPError, timeouts: retry throttling, server and network errors
            code = getattr(e, "code", None)
            if attempt == 3 or (code is not None and code != 429 and code < 500):
                raise
            retry_after = e.headers.get("Retry-After", "") if code else ""
            time.sleep(int(retry_after) if retry_after.isdigit() else 5 * (attempt + 1))
    if "error" in data:
        raise RuntimeError(f"wiki API error {data['error']['code']}: {data['error']['info']}")
    return data


def query(**params):
    """Yield every response of an action=query, following continuation."""
    cont = {}
    while True:
        data = _get({"action": "query", **params, **cont})
        yield data
        if "continue" not in data:
            return
        cont = data["continue"]


def fetch_wikitext(titles):
    """{title: wikitext} for up to BATCH titles; pages that don't exist are left out.

    Redirects are followed, and the text is filed under every name that led to it.
    """
    out, aliases = {}, []
    for data in query(titles="|".join(titles), prop="revisions", rvprop="content", rvslots="main", redirects=1):
        q = data.get("query", {})
        aliases += q.get("normalized", []) + q.get("redirects", [])
        out.update((p["title"], p["revisions"][0]["slots"]["main"]["content"]) for p in q.get("pages", []) if "revisions" in p)
    for alias in reversed(aliases):  # redirect hops are listed after normalization, so unwind them first
        if alias["to"] in out:
            out.setdefault(alias["from"], out[alias["to"]])
    return out


def all_pages():
    """Yield every main-namespace article with its visible categories and the redirects pointing to it.

    The same page can come back in several chunks while its categories and redirects are continued.
    """
    for data in query(generator="allpages", gapnamespace=0, gapfilterredir="nonredirects", gaplimit="max",
                      prop="categories|redirects", cllimit="max", clshow="!hidden",
                      rdlimit="max", rdnamespace=0, rdprop="title"):
        yield from data["query"]["pages"]
