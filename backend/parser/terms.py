"""Title normalization and the noise blocklist."""

# Linked from nearly everything, so they only add clutter.
NOISE_TITLES = {"Terra"}

# Categories of gameplay, media and meta pages: stages, mechanics, items, furniture, staff, and media about the
# world rather than things in it. The first rows were tuned by reading the Amiya + Reunion graph; the furniture,
# base and item rows came from the v2 screenshot set, where 3,900 of the 5,691 pages passing the filter were
# furniture, base skills and gameplay items, and "Castle" matched a ceiling lamp.
NOISE_CATEGORIES = {
    "Mechanics", "Terminology", "Operation mechanics", "RIIC mechanics", "Negative Statuses",
    "Classes", "Class branches", "Operator rarities", "Facilities", "Game modes", "Integrated Strategies themes",
    "Games", "Spin-off games", "Operation", "Operation lists", "Interludes", "Secret interludes", "Enemy",
    "Upgrade materials", "Consumables", "Event items", "Collectibles", "Thoughts", "Summons",
    "Artists", "Developers", "Music artists", "Voice actors", "Music",
    "Publications", "Comics", "Media", "Animations", "Terra Historicus lore posts", "Disambiguations",
    # Furniture, by type; every furniture page carries one of these beside its theme.
    "Decorations", "Seatings", "Wall Decorations", "Tables", "Ceiling Lamps", "Wall Lamps", "Ceilings", "Floors",
    "Wallpapers", "Carpets", "Cabinets", "Beddings", "Plaques", "Functionals", "Interactables", "Furniture themes",
    # The base, game modes and their items.
    "Base skills", "Tongbaos", "Foldartals", "Sanity restoration", "Provisions", "EC Units", "Constructs", "Terrain",
    "Support Items", "Support Devices", "Tokens", "Traps", "Currencies", "Other items", "Battle Records",
    "Buffs", "Debuffs", "Elemental Injuries", "Skill Summaries", "Limited-time game modes", "Reclamation Algorithm",
    "Contingency Contract Pennants", "Annihilation",
    # Promotions, music and the real world. "Celebration", "Festival" and "Carnival events" are story events too
    # (Lone Trail, Invitation to Wine, Dossoles Holiday), so they stay.
    "Other events", "Main Theme episode release events", "Operator EPs", "EPs", "Original soundtracks", "Prelude Suite",
    "Real-world", "Companies", "Guides", "User interface",
    # Supply and chip stages by type, summons and enemy traits, tournaments and joke events: found as v3's "Other" nodes.
    "Tough Siege", "Aerial Threat", "Cargo Escort", "Training Ground", "Tactical Drill", "Resource Search",
    "Solid Defense", "Fierce Attack", "Unstoppable Charge", "Fearless Protection", "Reinforcements", "Enemy properties",
    "Features", "Tournaments", "April Fools", "Browse",
}
NOISE_CATEGORY_SUFFIXES = (" operations", " enemies", " devices", " Collectibles", " Provisions", " OSTs",
                           " seasons", " tokens", " items", " materials", " resources", " mechanics", " currencies", " themes", " music")


# Node types, first match wins, so a nation that is also a faction (Lungmen, Victoria) is a Faction. Character is a
# sixth type beside the plan's five: 388 lore pages are NPCs (Talulah, Patriot, Theresa), who are neither operators nor
# "Other". Races, lore concepts and plays are Other.
TYPES = (
    ("Operator", lambda c: c.endswith("-star")),
    ("Event", {"Episodes", "Intermezzi", "Side Stories", "Story Collections", "Story events", "Collaboration events",
               "Celebration events", "Festival events", "Carnival events", "Login events", "Anniversary events"}.__contains__),
    ("Faction", {"Major factions", "Minor factions", "Enemy factions", "Non-Terran factions", "Nation-states",
                 "Sarkaz tribes"}.__contains__),
    ("Location", {"Locations"}.__contains__),
    ("Character", {"NPCs", "Other characters", "Characters"}.__contains__),
)


def node_type(categories):
    """Operator, Event, Faction, Location, Character or Other, from a page's categories."""
    return next((name for name, match in TYPES if any(map(match, categories))), "Other")


def normalize(title):
    """MediaWiki-style title: no leading colon or #anchor, spaces for underscores, first letter upper-case."""
    t = " ".join(title.split("#")[0].replace("_", " ").lstrip(": ").split())
    return t[:1].upper() + t[1:]


def is_noise(title, categories):
    return title in NOISE_TITLES or any(c in NOISE_CATEGORIES or c.endswith(NOISE_CATEGORY_SUFFIXES) for c in categories)
