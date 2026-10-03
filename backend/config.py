"""Settings for the wiki client, cache and graph. Starting values from docs/archive/v0-foundation.md."""
from pathlib import Path

WIKI_API = "https://arknights.wiki.gg/api.php"
WIKI_FILES = "https://arknights.wiki.gg/wiki/Special:FilePath/"  # redirects to an uploaded file's bytes
# MediaWiki API etiquette: say who is asking. Add a contact URL or email here before sharing the tool.
USER_AGENT = "ArknightsLoreCompendium/0.1 (personal fan project)"
REQUEST_DELAY = 1.0          # seconds between wiki requests
CACHE_TTL = 7 * 24 * 3600    # seconds before a cached page is fetched again
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wiki.db"

DEPTH = 1                    # link hops out from the seeds; 2 is a fuller map, 3 pulls in most of the wiki
MAX_NODES = 150              # final graph size, and the most pages expanded per BFS level

RECIPROCAL_BONUS = 2         # added to both directions when two pages link each other
SECTION_BONUS = 1            # added per section in which both ends of an edge are linked
SPEAKER_WEIGHT = 3           # the speaker's share of the PageRank restart, against 1 for each other seed
MAX_SEEDS = 50               # most seeds one graph takes: a session of several screenshots adds up

GLOBAL_LAUNCH = "2020-01-16" # Global's first day, from the wiki's Arknights page; Prologue to Episode 04 date from it

READER_URL = "http://127.0.0.1:11434"  # Ollama, which serves the model that reads screenshots
READER_MODEL = "qwen3.5:2b"  # ollama pull qwen3.5:2b; qwen3.5:4b reads a little better and takes longer
# ollama pull qwen3.5:4b. On 38 links of the Amiya + Reunion graph it was right or said "is related to" on 30, the 2B on
# 14; 1.9 s a link against 0.8, and each pair is labelled once.
LABEL_MODEL = "qwen3.5:4b"
MAX_UPLOAD_MB = 10           # largest screenshot /analyze takes
