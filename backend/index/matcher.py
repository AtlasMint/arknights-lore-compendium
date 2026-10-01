"""Find the wiki pages a screenshot's speaker and dialog name, by scanning them against the term index."""
import re

from backend.graph.builder import resolve

MAX_WORDS = 6  # longest phrase tried; 99% of titles are this short
WORD = re.compile(r"\w+(?:'\w+)*")  # Kal'tsit and Ch'en are one word each
# Capitalized in nearly every line, since it is how characters address the player, so a match says little.
NEEDS_CONTEXT = {"Doctor"}


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


def find(speaker, text):
    """{"keywords": [...], "needs_context": [...]} of canonical titles, each listed once.

    Whatever the speaker name matches is always a keyword. In the dialog, a match written all in lower
    case ("the silence here") is more likely an ordinary word than the operator Silence, so it goes to
    needs_context with the NEEDS_CONTEXT titles, for the user to decide.
    """
    keywords, maybe = [title for title, _ in scan(speaker)], []
    for title, phrase in scan(text):
        (maybe if phrase.islower() or title in NEEDS_CONTEXT else keywords).append(title)
    keywords = list(dict.fromkeys(keywords))
    return {"keywords": keywords, "needs_context": [t for t in dict.fromkeys(maybe) if t not in keywords]}
