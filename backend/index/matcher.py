"""Find the wiki pages a screenshot's speaker and dialog name, by scanning them against the term index."""
import difflib
import re
from collections import defaultdict
from functools import cache

from backend.graph.builder import resolve
from backend.index import build_index as index

MAX_WORDS = 6  # longest phrase tried; 99% of titles are this short
WORD = re.compile(r"\w+(?:'\w+)*")  # Kal'tsit and Ch'en are one word each
# Capitalized in nearly every line, since it is how characters address the player, so a match says little.
NEEDS_CONTEXT = {"Doctor"}
# A capitalized word of at least MIN_GUESS letters that matched nothing is probably a misread name, and the one title
# at least CUTOFF similar (difflib ratio) is what it meant. Tuned on tests/screenshots: the reader wrote Dublinn as
# Dublinl, Dublininn and Dublin (0.857 to 0.923) and Czcibor as Czibor (0.923); nothing wrong scored 0.85 or more,
# while 0.8 let in sentence openers (There -> Theresa, Hence -> Fence) and 0.9 lost all but three true guesses.
MIN_GUESS = 5  # "Red" -> Reed would be a guess at 3 letters
CUTOFF = 0.85
# Demonyms and plurals: Tarans -> Tara, Victorian -> Victoria, Sargonian -> Sargon, Lungmenite -> Lungmen. Shortest first,
# so "Victorians" reaches Victoria through "ns" before "ians" could reach a page called Victor.
SUFFIXES = ("s", "n", "ns", "ian", "ians", "ans", "ese", "ite")
# Pages people shorten to one word: a first name or surname, the distinctive word of a place or a group. Operators
# are the "N-star" categories on top of these.
NAMED = ("NPCs", "Other characters", "Locations", "Nation-states", "Major factions", "Minor factions", "Enemy factions",
         "Non-Terran factions", "Races", "Race subgroups", "Sarkaz tribes")
# Ordinary words that start or end one of those pages (County Hillock, Palace of Westhaleg, Little Black Sheep, Blue
# Poison): never a name on their own, so never a guess. Listed from the index on 2026-10-03.
# ponytail: hand-kept; a new page starting or ending with another ordinary word slips through until it is added here.
# The upgrade is a lowercase-frequency check over cached page text, which would need the page cache at match time.
GENERIC = set("""
    Abyssal Agency Beauty Black Brown Castle Catch Chimes Church Cluster Commandant Commerce Commission Corps Corrupted
    County Crimson Deathless Deity Delivering Demon Department Destructive Drudge Elite Empresses Father Galería Galleria
    Garden Grain Great Group House Hunters Industries Island Keeper Little Military Museum Nothing Official Other Palace
    Paradise Party Pegasi Poison Priest Prison Propeller Reckoner Recon Record Regulator Sheep Shrine Signora Snake Spring
    Tower Trade Tutor Uncle Union Universität Violet Witch Withered
    """.split())


def scan(text):
    """Yield (canonical title, phrase as written) for each lore page named in the text, in reading order.

    At each word the longest phrase that resolves to a page wins, so "Rhodes Island" beats "Island".
    Case is ignored, and a possessive 's is dropped: "Amiya's" -> Amiya.
    """
    text = text.replace("’", "'")  # game text uses curly apostrophes; titles use straight ones
    words = [(m.start(), m.end() - 2 * m[0].endswith("'s")) for m in WORD.finditer(text)]
    i = 0
    while i < len(words):
        for j in range(min(len(words), i + MAX_WORDS), i, -1):
            phrase = text[words[i][0]:words[j - 1][1]]
            if title := resolve(phrase):
                yield title, phrase
                i = j
                break
        else:
            i += 1


@cache
def qualified():
    """Gameplay title -> the lore pages that qualify it: Guard -> [Guard (NPC)], Nightzmora -> [Nightzmora (country), ...].

    The plain title is noise (a class, a term, a disambiguation), but the same word can name a character or a place.
    """
    pages = defaultdict(list)
    for title in index.titles():
        if title.endswith(")") and "/" not in title and resolve(title) == title:
            plain = index.lookup(title.rsplit(" (", 1)[0])
            if plain and resolve(plain) is None:
                pages[plain].append(title)
    return pages


@cache
def names():
    """First or last word of a NAMED page -> that page, where no other NAMED page starts or ends with it.

    "Reserve Operator - Logistics" and its kin are left out: placeholders, not people. An alter title like
    "Gavial the Invincible" gives only its first word, since the last is an epithet.
    """
    pages = defaultdict(set)
    for title in index.titles():
        if "/" in title or " - " in title or resolve(title) != title:
            continue
        if any(c in NAMED or c.endswith("-star") for c in index.categories(title)):
            words = WORD.findall(title)
            for word in {words[0]} if " the " in title else {words[0], words[-1]}:
                if len(word) >= MIN_GUESS and word[0].isupper() and word not in GENERIC:
                    pages[word].add(title)
    return {word: next(iter(titles)) for word, titles in pages.items() if len(titles) == 1}


def guess(word):
    """The page a leftover name probably means, or None. Tried in order: a demonym or plural ("Tarans" -> Tara), a
    misreading ("Dublinl" -> Dublinn), one word of a person, place or group ("Candela" -> Candela Sanchez,
    "Hillock" -> County Hillock). An ordinary word (GENERIC) is never any of these.

    A misreading counts only when the single closest title is a lore page: a guess that lands on a class or
    disambiguation page is dropped, not retried further away.
    """
    if word in GENERIC:
        return None
    for suffix in SUFFIXES:
        if word.endswith(suffix) and (title := resolve(word[: -len(suffix)])):
            return title
    # ponytail: linear over all ~19k titles, 11 ms a word; bucket titles by first letter if a log view ever drags
    closest = difflib.get_close_matches(word, index.titles(), n=1, cutoff=CUTOFF)
    return (closest and resolve(closest[0])) or names().get(word)


def find(speaker, text):
    """{"keywords": [...], "needs_context": [...], "guesses": {title: word as read}} of canonical titles, each once.

    Whatever the speaker name matches is always a keyword. In the dialog, a match written all in lower
    case ("the silence here") is more likely an ordinary word than the operator Silence, so it goes to
    needs_context with the NEEDS_CONTEXT titles, for the user to decide.

    Capitalized words left over then get a second look. One that is a gameplay title offers the pages that
    qualify it: a disambiguation's targets (Nightzmora (country), Nightzmora (race)) as keywords, since the plain
    word means nothing else; a class or term's namesake (Guard (NPC)) under needs_context, since "Guard" is
    usually the class. Any other goes through guess(); a guess is a keyword too, and `guesses` says what was read.
    """
    keywords, maybe, rest = [], [], f"{speaker}\n{text}".replace("’", "'")
    for title, phrase in scan(speaker):
        keywords.append(title)
        rest = rest.replace(phrase, " ")
    for title, phrase in scan(text):
        (maybe if phrase.islower() or title in NEEDS_CONTEXT else keywords).append(title)
        rest = rest.replace(phrase, " ")
    keywords, guesses = list(dict.fromkeys(keywords)), {}
    for word in WORD.findall(rest):
        word = word.removesuffix("'s")
        if not word[0].isupper():
            continue
        if plain := index.lookup(word):  # left over, so a title the noise filter rejected
            for title in qualified().get(plain, ()):
                (keywords if "Disambiguations" in index.categories(plain) else maybe).append(title)
        elif len(word) >= MIN_GUESS and (title := guess(word)):
            if title not in keywords and title not in maybe and title not in NEEDS_CONTEXT:
                guesses.setdefault(title, word)
    keywords = list(dict.fromkeys(keywords + list(guesses)))
    return {"keywords": keywords, "needs_context": [t for t in dict.fromkeys(maybe) if t not in keywords], "guesses": guesses}
