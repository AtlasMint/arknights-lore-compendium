"""Relationship labels for graph links: the wiki sentences that name both ends, put into a few words by the local model.

A label reads from one end to the other, {"from": "Talulah", "relation": "is the half-sister of", "to": "Ch'en"}, from the
side whose page the evidence is on, since "she" on Talulah's page is Talulah. Labels are cached in SQLite by pair, model
and prompt, so each pair is read once and a new model or prompt reads it afresh.
"""
import hashlib
import json
import re
from functools import lru_cache

from backend import config
from backend.graph import lore
from backend.parser import wikitext
from backend.scraper.cache import connect
from backend.vision import ollama_reader

UNSURE = "is related to"  # when the wiki has no sentence naming both, or the model's answer isn't a short phrase
MAX_EVIDENCE = 6          # sentences per pair: enough to say how two pages relate, few enough for a sub-second call
MAX_WORDS = 8
IMAGE = re.compile(r"\.(png|jpe?g|gif)\b", re.I)  # infobox image lines name a faction in a file name, not a relation
# No example phrases: a small model copies them ("Amiya is the sister of Chernobog"). Asking for the sentences' own words
# keeps it to what the wiki says.
PROMPT = (
    "Sentences from the Arknights wiki page about {a}:\n{evidence}\n\nWhat do these sentences say about how {a} relates "
    'to {b}? Answer by filling the blank in "{a} ___ {b}." with 1 to 6 words, using the sentences\' own words where you '
    'can. If they only mention both without saying how they relate, answer "is related to".'
)
SCHEMA = {"type": "object", "properties": {"relation": {"type": "string"}}, "required": ["relation"]}


@lru_cache(maxsize=256)  # keyed by page text, so a page fetched afresh is parsed afresh
def _lines(text):
    """[(field or None, sentence, lore pages it names)]: a page's infobox lines, then its prose sentences."""
    return ([(field, line, lore.named(line, targets)) for field, line, targets in wikitext.infobox_lines(text)]
            + [(None, sentence, lore.named(sentence, targets)) for sentence, targets in wikitext.sentences(text)])


def evidence(a, b):
    """(subject, other, sentences): the sentences on a's pages that name b, or else those on b's pages that name a, with
    the page's owner as the subject. An infobox line gets the owner's name, "Talulah's family: Ch'en Hui-chieh
    (half-sister)", since on a page about Talulah the subject goes unsaid. No sentences on either side: (a, b, [])."""
    texts = lore.page_texts([a, b])
    for subject, other in ((a, b), (b, a)):
        found = [f"{subject}'s {field}: {line}" if field else line
                 for text in texts[subject] for field, line, named in _lines(text)
                 if other in named and not IMAGE.search(line)]
        if found:
            return subject, other, list(dict.fromkeys(found))[:MAX_EVIDENCE]
    return a, b, []


def clean(reply, a, b):
    """The model's phrase, without an echo of either name or end punctuation; UNSURE if it isn't a short phrase."""
    try:
        relation = str(json.loads(reply).get("relation", ""))
    except (ValueError, AttributeError):
        return UNSURE
    relation = relation.strip().removeprefix(a).removesuffix(".").removesuffix(b).strip(" .,:;\"'")
    return relation if relation and "\n" not in relation and len(relation.split()) <= MAX_WORDS else UNSURE


def label(a, b):
    """{"from", "relation", "to"} for the link between a and b. Raises RuntimeError when Ollama is down, as the reader does."""
    key = hashlib.sha256(f"{config.LABEL_MODEL}\n{PROMPT}\n{a}\n{b}".encode()).hexdigest()
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS labels (key TEXT PRIMARY KEY, label TEXT NOT NULL)")
        row = db.execute("SELECT label FROM labels WHERE key = ?", (key,)).fetchone()
    if row:
        return json.loads(row[0])
    subject, other, found = evidence(a, b)
    relation = UNSURE
    if found:
        prompt = PROMPT.format(a=subject, b=other, evidence="\n".join(f"- {sentence}" for sentence in found))
        relation = clean(ollama_reader.chat(prompt, SCHEMA, model=config.LABEL_MODEL), subject, other)
    result = {"from": subject, "relation": relation, "to": other}
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO labels VALUES (?, ?)", (key, json.dumps(result)))
    return result
