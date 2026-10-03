"""Find the wiki pages a screenshot's speaker and dialog name, by scanning them against the term index."""
import difflib
import re

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


def guess(word):
    """The page a misread name probably meant ("Dublinl" -> Dublinn), or None.

    Only the single closest title counts, and only if it is a lore page: a guess that lands on a class or
    disambiguation page is dropped, not retried further away.
    """
    # ponytail: linear over all ~19k titles, 11 ms a word; bucket titles by first letter if a log view ever drags
    closest = difflib.get_close_matches(word, index.titles(), n=1, cutoff=CUTOFF)
    return resolve(closest[0]) if closest else None


def find(speaker, text):
    """{"keywords": [...], "needs_context": [...], "guesses": {title: word as read}} of canonical titles, each once.

    Whatever the speaker name matches is always a keyword. In the dialog, a match written all in lower
    case ("the silence here") is more likely an ordinary word than the operator Silence, so it goes to
    needs_context with the NEEDS_CONTEXT titles, for the user to decide. Capitalized words that matched
    nothing are checked for misreadings; a guess is a keyword too, and `guesses` says what was read.
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
        if word[0].isupper() and len(word) >= MIN_GUESS and (title := guess(word)):
            if title not in keywords and title not in maybe and title not in NEEDS_CONTEXT:
                guesses.setdefault(title, word)
    return {"keywords": keywords + list(guesses), "needs_context": [t for t in dict.fromkeys(maybe) if t not in keywords],
            "guesses": guesses}
