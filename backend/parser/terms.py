"""Title normalization and the noise blocklist."""

# Linked from nearly everything, so they only add clutter.
NOISE_TITLES = {"Terra"}

# Categories of gameplay, media and meta pages: stages, mechanics, items, staff, and media about the
# world rather than things in it. Tuned by reading the Amiya + Reunion graph.
NOISE_CATEGORIES = {
    "Mechanics", "Terminology", "Operation mechanics", "RIIC mechanics", "Negative Statuses",
    "Classes", "Class branches", "Operator rarities", "Facilities", "Game modes", "Integrated Strategies themes",
    "Games", "Spin-off games", "Operation", "Operation lists", "Interludes", "Secret interludes", "Enemy",
    "Upgrade materials", "Consumables", "Event items", "Collectibles", "Thoughts", "Summons",
    "Artists", "Developers", "Music artists", "Voice actors", "Music",
    "Publications", "Comics", "Media", "Animations", "Terra Historicus lore posts", "Disambiguations",
}
NOISE_CATEGORY_SUFFIXES = (" operations", " enemies", " devices", " Collectibles")


def normalize(title):
    """MediaWiki-style title: no leading colon or #anchor, spaces for underscores, first letter upper-case."""
    t = " ".join(title.split("#")[0].replace("_", " ").lstrip(": ").split())
    return t[:1].upper() + t[1:]


def is_noise(title, categories):
    return title in NOISE_TITLES or any(c in NOISE_CATEGORIES or c.endswith(NOISE_CATEGORY_SUFFIXES) for c in categories)
