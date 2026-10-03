"""Wikitext -> section headings, the link candidates in each section, infobox fields, and plain sentences."""
import re

import mwparserfromhell

# A sentence ends at . ! or ? (and any closing quote or bracket) before a space and a capital, digit or opening quote.
SENTENCE_END = re.compile(r"(?<=[.!?])[\"”’')]*\s+(?=[\"“'(]?[A-Z0-9])")
NOT_PROSE = ("file:", "image:", "category:")  # link prefixes whose text is a caption or nothing


def parse(wikitext):
    """{"sections": [(heading, [link target, ...]), ...], "infobox": {field: plain-text value}}.

    The lead section has the heading "". Targets are raw and may repeat. Besides [[links]], a template
    parameter whose whole value could be a title is a candidate, because templates hide real links:
    {{Character list cell|name=Talulah}}, {{Main|Chernobog Crisis}}, |faction = Rhodes Island.
    The caller keeps only candidates that are real pages. <ref> citations are dropped: they link
    sources (stages, artbooks), not related lore.
    """
    code = mwparserfromhell.parse(wikitext)
    for ref in code.filter_tags(matches=lambda node: node.tag == "ref"):
        code.remove(ref)
    sections = []
    for section in code.get_sections(flat=True, include_lead=True):
        headings = section.filter_headings(recursive=False)
        targets = [str(link.title) for link in section.filter_wikilinks()]
        targets += [str(p.value).strip() for t in section.filter_templates() for p in t.params]
        sections.append((headings[0].title.strip_code().strip() if headings else "", targets))
    infobox = next((t for t in code.filter_templates() if str(t.name).strip().lower().endswith("infobox")), None)
    fields = {str(p.name).strip(): p.value.strip_code().strip() for p in infobox.params} if infobox else {}
    return {"sections": sections, "infobox": fields}


def plain(code):
    """Plain text of a wikicode fragment and the (shown text, target) of each link left in it."""
    for node in code.filter(recursive=True, forcetype=(mwparserfromhell.nodes.Template, mwparserfromhell.nodes.Comment,
                                                        mwparserfromhell.nodes.Heading, mwparserfromhell.nodes.Tag,
                                                        mwparserfromhell.nodes.Wikilink)):
        drop = not isinstance(node, (mwparserfromhell.nodes.Tag, mwparserfromhell.nodes.Wikilink))
        drop |= isinstance(node, mwparserfromhell.nodes.Tag) and str(node.tag).lower() in ("ref", "table", "gallery", "tabber")
        drop |= isinstance(node, mwparserfromhell.nodes.Wikilink) and str(node.title).strip().lower().startswith(NOT_PROSE)
        if drop:
            try:
                code.remove(node)
            except ValueError:  # already gone with the node around it
                pass
    links = [((link.text or link.title).strip_code().strip(), str(link.title)) for link in code.filter_wikilinks()]
    return code.strip_code(), links


def sentences(wikitext):
    """[(sentence, [link target, ...])] of a page's prose in reading order, so the intro comes first. Templates
    (infoboxes, quotes), tables, files, <ref>s and headings are dropped. A link belongs to every sentence its shown
    text appears in, so a sentence keeps its links however the page wraps them.
    """
    text, links = plain(mwparserfromhell.parse(wikitext))
    out = []
    for paragraph in text.split("\n"):
        for sentence in SENTENCE_END.split(paragraph.strip()):
            if len(sentence.split()) >= 3:  # leftovers like "thumb" or a lone name aren't sentences
                out.append((sentence, [target for shown, target in links if shown and shown in sentence]))
    return out


def infobox_lines(wikitext):
    """[(field, plain line, [link target, ...])] for each line of each field of the page's infobox:
    ("family", "Ch'en Hui-chieh (half-sister)", ["Ch'en"]). A list field gives one line per item."""
    code = mwparserfromhell.parse(wikitext)
    infobox = next((t for t in code.filter_templates() if str(t.name).strip().lower().endswith("infobox")), None)
    out = []
    for param in infobox.params if infobox else []:
        for line in str(param.value).split("\n"):
            text, links = plain(mwparserfromhell.parse(line))
            text = text.replace("}}", "").strip(" *")  # the ends of a template wrapped around a list, like Collapsible
            if text and "{{" not in text:
                out.append((str(param.name).strip(), text, [target for _, target in links]))
    return out
