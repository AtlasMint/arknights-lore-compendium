"""Offline checks for v3: node types and summaries, the stories timeline and its spoiler tags, the in-game years seed,
relationship labels, the new endpoints, the progress file that followed, and v3.1's sourced summaries. No network and no Ollama: the wiki is
fake and the model is stubbed.

    python -m tests.test_v3
"""
import datetime
import tempfile
from pathlib import Path

from backend import config, stories
from backend.app import app
from backend.graph import builder, labels, lore
from backend.index import build_index
from backend.parser import terms, wikitext
from backend.scraper import cache, wiki_client
from backend.vision import ollama_reader

config.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"
config.PROGRESS_PATH = config.DB_PATH.with_name("progress.json")
stories.YEARS = config.DB_PATH.with_name("years.json")
stories.YEARS.write_text('{"Babel (event)": "1094"}')
TODAY = datetime.date(2026, 10, 3)


def cell(**params):
    return "{{Timeline cell" + "".join(f"\n|{k} = {v}" for k, v in params.items()) + "}}"


PAGES = {
    "Story/Movements": "<tabber>Main Theme={{:Story/Movements/Main Theme}}|-|The Ark={{:Story/Movements/The Ark}}</tabber>",
    "Story/Movements/Main Theme": "{{Timeline head|arc = MS|name = For Tomorrow|intro = Heroes.}}"
    + cell(act="I", name="Shatter")
    + cell(name="Episode 01", subtitle="Evil Time", intro="[[Amiya]] escapes.")
    + cell(name="Episode 02", intro="On to [[Lungmen]].", related="Babel")
    + cell(cn="true", name="Episode 03"),
    "Story/Movements/The Ark": "{{Timeline head|arc = RI|name = The Ark|intro = Rhodes Island.}}"
    + cell(name="Babel", link="Babel (event)", intro="Long ago.", related="Episode 02"),
    "Episode 01": "{{Episode infobox|name = Episode 01|next = Episode 02}}",  # no date: in the game at Global launch
    "Episode 02": "{{Episode infobox|name = Episode 02|prev = Episode 01|next = Episode 03|global = 2020/02/26}}",
    "Episode 03": "{{Episode infobox|name = Episode 03|prev = Episode 02}}",  # CN only: no Global date, so left out
    "Babel (event)": "{{Event infobox|name = Babel|type = intermezzo|globalstart = 2024/10/10}}",
    "Crossy": "<tabber>Part 1={{:Crossy/Part 1}}</tabber>",  # a crossover keeping its infobox on a Part subpage
    "Crossy/Part 1": "{{Event infobox|name = Crossy Part 1|globalstart = 2023/01/05}}",
    "Episode 01/Synopsis": "{{Synopsis head|desc = Escape.}}\n==Awake==\nIn 1096, [[Amiya]] meets [[Talulah]].",
    "Babel (event)/Synopsis": "==Past==\nIn the year 1094, [[Theresa]] raises [[Amiya]].",
    "Talulah": "{{Character infobox|appearance = \n*[[Episode 02]]\n*[[Babel (event)]] (flashback)\n*[[Crossy]] (mentioned as the Snake)"
               "|affiliation = [[Reunion]] (leader)|family = \n*[[Ch'en|Ch'en Hui-chieh]]{{Status|deceased}} (half-sister)}}\n"
               "'''Talulah''' is an [[NPC]]. She leads [[Reunion]].<ref name=\"start\">[[1-1]]</ref> [[File:T.png|thumb|A photo]]\n"
               "==Background==\nTalulah grew up in [[Lungmen]] with her half-sister [[Ch'en]]. Later she met Amiya. "
               "She was raised by [[Theresa]].<ref>[[BB-4/Story#After operation|BB-4 After]]</ref> She is tall.<ref>pg. 5, a book</ref>\n"
               "==Story==\n===Babel===\nYoung Talulah meets [[Theresa]].\n===Episode 02===\nShe fights in [[Lungmen]].<ref name=\"start\"/> "
               "Then she leaves.\n===Episode 3===\nShe returns to Ursus.\n===Talulah: A Record===\nAn operator record, not a story.",
    "Ch'en": "{{Operator info|faction = Lungmen Guard Department}}",
    "Ch'en/Story": "'''Ch'en''' is an operator. She is strict with herself.",
    "Ch'en/File": "{{Archive|title = Profile|text = Senior Inspector of the [[Lungmen Guard Department]].<br/>She is strict.}}"
                  "{{Archive|title = Archive File 1|text = Secret things.}}",
    "1-1": "{{Operation info|episode = 01|name = Isolated Island|next = 1-2}}",
    "BB-4": "{{Operation info|code = BB-4|name = Long Voyage|intermezzo = Babel (event)|event title = Babel}}",
    "Arknights Timeline": "==Common Era==\n===11th Century===\n====1090&ndash;1096====\n*'''Founding''': see [[Babel (event)]].\n"
                          "====1097====\n*'''Crisis''' (ca. 1097): See [[Episode 02]].{{Note|Not [[Babel (event)]].}}\n"
                          "==Crossover events==\n===Identified===\n*'''Visit''' (ca. 1098 ~ 1099): [[Crossy]] takes place.",
}
CATEGORIES = {
    "Episode 01": ["Episodes"], "Episode 02": ["Episodes"], "Episode 03": ["Episodes"], "Babel (event)": ["Intermezzi"],
    "Crossy": ["Collaboration events", "Side Stories"], "Amiya": ["5-star", "Rhodes Island"], "Talulah": ["NPCs"],
    "Ch'en": ["6-star", "Lungmen Guard Department"], "Reunion": ["Enemy factions"], "Rhodes Island": ["Major factions"],
    "Lungmen": ["Major factions", "Nation-states"], "Lungmen Guard Department": ["Major factions"], "Theresa": ["NPCs"],
    "Catastrophe": ["Lore"], "1-1": ["Main Theme operations"], "BB-4": ["Babel event"], "Ch'en/Story": [], "Ch'en/File": [],
}
wiki_client.all_pages = lambda: iter(
    [{"title": t, "categories": [{"title": f"Category:{c}"} for c in CATEGORIES.get(t, [])]} for t in {*PAGES, *CATEGORIES}]
)
cache.get_pages = lambda titles: {t: PAGES[t] for t in titles if t in PAGES}
build_index.build()

model_calls = []
ollama_reader.chat = lambda prompt, schema, model: model_calls.append((model, prompt)) or '{"relation": "Talulah is the half-sister of Ch\'en."}'


def test_types():
    assert terms.node_type(["6-star", "Rhodes Island"]) == "Operator"
    assert terms.node_type(["Major factions", "Nation-states"]) == "Faction"  # a nation that is a faction is a Faction
    assert terms.node_type(["NPCs"]) == "Character"
    assert terms.node_type(["Intermezzi"]) == "Event"
    assert terms.node_type(["Lore"]) == terms.node_type([]) == "Other"


def test_wikitext():
    said = wikitext.sentences(PAGES["Talulah"])
    assert said[0] == ("Talulah is an NPC.", ["NPC"])  # infobox, <ref> and file caption gone
    assert said[2] == ("Talulah grew up in Lungmen with her half-sister Ch'en.", ["Lungmen", "Ch'en"])
    assert ("family", "Ch'en Hui-chieh (half-sister)", ["Ch'en"]) in wikitext.infobox_lines(PAGES["Talulah"])
    rows = wikitext.prose(PAGES["Talulah"])
    assert rows[0] == ("", "Talulah is an NPC.", ["NPC"], "1-1")  # covered by the citation that closes its run
    assert rows[2] == ("Background", "Talulah grew up in Lungmen with her half-sister Ch'en.", ["Lungmen", "Ch'en"], "BB-4/Story#After operation")
    assert rows[5][1:] == ("She is tall.", [], None)  # a book: no link, nothing to resolve
    assert rows[7] == ("Episode 02", "She fights in Lungmen.", ["Lungmen"], "1-1")  # <ref name=.../> reuse
    assert wikitext.archive(PAGES["Ch'en/File"])[0] == ("Profile", [("Senior Inspector of the Lungmen Guard Department.", ["Lungmen Guard Department"]), ("She is strict.", [])])
    assert stories.stage_stories({"1-1", "BB-4/Story#After operation", "Terra: A Journey"}) == {"1-1": "Episode 01", "BB-4/Story#After operation": "Babel (event)"}
    assert [stories.story_named(h) for h in ("Episode 3", "Babel", "Talulah: A Record")] == ["Episode 03", "Babel (event)", None]
    # A ref the parser reads as holding the next one, as on the wiki's Arknights Timeline, cites that one's stage.
    nested = "Founded long ago here.<ref>p. 151, a book <ref>[[10-19]]</ref> and more</ref> The rebels won the war.<ref>[[1-1]]</ref>"
    assert [row[3] for row in wikitext.prose(nested)] == ["10-19", "1-1"]


def test_timeline():
    data = stories.timeline(TODAY)
    assert [s["id"] for s in data["stories"]] == ["Episode 01", "Episode 02", "Babel (event)", "Crossy"]
    first, second, babel, crossy = data["stories"]
    assert first["start"] == config.GLOBAL_LAUNCH and second["start"] == "2020-02-26"
    assert (first["band"], babel["band"], crossy["band"]) == ("main", "intermezzo", "crossover")
    assert babel["name"] == "Babel" and babel["year"] == "1094" and crossy["start"] == "2023-01-05"
    assert first["teaser"] == "Amiya escapes." and first["subtitle"] == "Evil Time"
    # Episode 03 isn't out, so its sequel edge goes; the related pair is listed on both cells and drawn once.
    assert [(e["source"], e["target"], e["kind"]) for e in data["edges"]] == [
        ("Episode 01", "Episode 02", "sequel"), ("Babel (event)", "Episode 02", "related")]
    assert data["acts"] == [{"name": "Act I: Shatter", "first": "Episode 01"}]
    assert [m["code"] for m in data["movements"]] == ["MS", "RI"]
    assert "Babel (event)" not in [s["id"] for s in stories.timeline(datetime.date(2024, 10, 9))["stories"]]


def test_tags_and_years():
    assert stories.tags("Talulah") == ["Episode 01"]
    assert stories.tags("Talulah", {"Episode 02", "Episode 03"}) == ["Episode 01", "Episode 02"]  # Episode 03 isn't out
    assert stories.tags("Amiya") == ["Episode 01", "Babel (event)"]  # synopsis and teaser
    assert stories.tags("Lungmen") == ["Episode 02"] and stories.tags("Catastrophe") == []
    # The latest year wins; a note's link doesn't count; a crossover takes its own line's year.
    assert stories.seed_years() == {"Episode 01": "1096", "Episode 02": "ca. 1097", "Babel (event)": "1096", "Crossy": "ca. 1099"}


def test_describe():
    graph = lore.describe(builder.build_graph(["Talulah"]))
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert nodes["Talulah"]["type"] == "Character" and nodes["Talulah"]["faction"] == "Reunion"  # from the infobox
    assert nodes["Ch'en"]["faction"] == "Lungmen Guard Department" and nodes["Reunion"]["faction"] == "Reunion"
    assert nodes["Lungmen"]["type"] == "Faction" and nodes["Lungmen"]["faction"] == "Lungmen"  # a faction is its own
    summary = nodes["Talulah"]["summary"]
    assert summary[1] == {"text": "She leads Reunion.", "terms": ["Reunion"], "story": "Episode 01"}  # cited to stage 1-1
    assert {"text": "Later she met Amiya.", "terms": ["Amiya"], "story": "Babel (event)"} in summary  # named without a link
    # Four lead sentences, then one per story heading in Score order (Babel's Movement comes after the Episodes); the
    # fifth lead sentence and the operator record are left out.
    assert [s["story"] for s in summary] == ["Episode 01", "Episode 01", "Babel (event)", "Babel (event)", "Episode 02", "Episode 03", "Babel (event)"]
    assert [s["text"] for s in summary[4:]] == ["She fights in Lungmen.", "She returns to Ursus.", "Young Talulah meets Theresa."]
    assert nodes["Ch'en"]["summary"][:3] == [{"text": "Senior Inspector of the Lungmen Guard Department.", "terms": ["Lungmen Guard Department"], "story": None},
                                            {"text": "She is strict.", "terms": [], "story": None}, {"text": "Ch'en is an operator.", "terms": ["Ch'en"], "story": None}]
    assert graph["tags"]["Talulah"] == ["Episode 01", "Episode 02", "Babel (event)"]  # not Crossy, under another name
    assert graph["tags"]["Amiya"] == ["Episode 01", "Babel (event)"]  # named in a summary, not a node
    link = next(l for l in graph["links"] if {l["source"], l["target"]} == {"Talulah", "Lungmen"})
    assert link["stories"] == ["Episode 02"]


def test_labels():
    subject, other, found = labels.evidence("Talulah", "Ch'en")
    assert (subject, other) == ("Talulah", "Ch'en") and found[:2] == [
        "Talulah's family: Ch'en Hui-chieh (half-sister)", "Talulah grew up in Lungmen with her half-sister Ch'en."]
    assert labels.evidence("Ch'en", "Talulah")[:2] == ("Talulah", "Ch'en")  # read from the side the evidence is on
    half = {"from": "Talulah", "relation": "is the half-sister of", "to": "Ch'en"}  # the echoed names and full stop trimmed
    assert labels.label("Ch'en", "Talulah") == half and model_calls[0][0] == config.LABEL_MODEL
    assert "page about Talulah" in model_calls[0][1]
    assert labels.label("Ch'en", "Talulah") == half and len(model_calls) == 1  # cached
    assert labels.label("Theresa", "Catastrophe") == {"from": "Theresa", "relation": labels.UNSURE, "to": "Catastrophe"}
    assert len(model_calls) == 1  # no evidence, no call
    assert labels.clean('{"relation": "a\\nb"}', "A", "B") == labels.clean("not json", "A", "B") == labels.UNSURE


def test_endpoints():
    client = app.test_client()
    wiki_client.fetch_file = lambda name: b"\x89PNG " + name.encode()
    assert client.get("/stories").json["movements"][0]["code"] == "MS"
    response = client.get("/icon/MS")
    assert response.status_code == 200 and response.data == b"\x89PNG MS_arc.png" and response.content_type == "image/png"
    assert client.get("/icon/..%2Fsecret").status_code == 404
    assert client.post("/labels", json={"pairs": [["Talulah", "Ch'en"]]}).json["labels"][0]["relation"] == "is the half-sister of"
    assert client.post("/labels", json={"pairs": [["Talulah", "Not a page"]]}).status_code == 400
    assert client.post("/labels", json={"pairs": [["Talulah", "Ch'en"]] * 21}).status_code == 400
    body = client.get("/graph?seeds=Talulah,Ch'en&speaker=Talulah,Nobody").json
    assert "tags" in body and {n["id"] for n in body["nodes"] if n["seed"]} == {"Talulah", "Ch'en"}


def test_progress():
    """The progress file: none yet, then saved whole and read back; bad input and a broken file refused."""
    client = app.test_client()
    assert client.get("/progress").status_code == 404
    good = {"ticked": ["Episode 01", "Babel (event)"], "overrides": {"Talulah": "hide"}, "fog": True}
    assert client.put("/progress", json=good).json == good
    assert client.get("/progress").json == good
    assert "Babel (event)" in config.PROGRESS_PATH.read_text("utf-8") and not list(config.PROGRESS_PATH.parent.glob("*.tmp"))
    for bad in [{"ticked": "Episode 01"}, {"overrides": {"Talulah": "maybe"}}, {"fog": "yes"}, ["Episode 01"]]:
        assert client.put("/progress", json=bad).status_code == 400
    assert client.get("/progress").json == good  # a refused save changes nothing
    config.PROGRESS_PATH.write_text("not json", "utf-8")
    assert client.get("/progress").status_code == 500


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
