"""Wikitext -> section headings, the link candidates in each section, infobox fields, and plain sentences."""
import re

import mwparserfromhell

MARK = re.compile("\ue000(\\d+)\ue001")  # where a <ref> stood, by its index
# A sentence ends at . ! or ? (and any closing quote, bracket or citation mark) before a space and a capital, digit or
# opening quote.
SENTENCE_END = re.compile(r"(?<=[.!?])((?:[\"”’')]|\ue000\d+\ue001)*)\s+(?=[\"“'(]?[A-Z0-9])")
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
        line_break = isinstance(node, mwparserfromhell.nodes.Tag) and str(node.tag).lower() == "br"
        if drop or line_break:
            try:  # a line break is a paragraph break, so the sentences on each side stay apart
                code.replace(node, "\n") if line_break else code.remove(node)
            except ValueError:  # already gone with the node around it
                pass
    links = [((link.text or link.title).strip_code().strip(), str(link.title)) for link in code.filter_wikilinks()]
    return code.strip_code(), links


def _cite(code):
    """Swaps every <ref> in the code for a mark and returns what each mark cites: the ref's first link target
    ("BB-4/Story#After operation"), or None for a citation with no link. <ref name="x"/> reuses the ref defined as x."""
    refs = code.filter_tags(matches=lambda node: node.tag == "ref")
    attr = lambda ref, name: str(ref.get(name).value).strip().strip("\"'") if ref.has(name) else None
    body = lambda ref: ref.contents if ref.contents is not None and str(ref.contents).strip() else None
    defined = {attr(r, "name"): body(r) for r in refs if attr(r, "name") and body(r) is not None}
    cites = []
    for i, ref in enumerate(refs):
        contents = body(ref) if body(ref) is not None else defined.get(attr(ref, "name"))
        links = contents.filter_wikilinks() if contents is not None else []
        cites.append(str(links[0].title).strip() if links else None)
        try:
            code.replace(ref, f"\ue000{i}\ue001")
        except ValueError:  # gone with a ref around it: an unclosed one swallows the next (Arknights Timeline)
            pass
    return cites


def _split(code):
    """[(sentence, [link target, ...], mark or None)] of a fragment's prose: each sentence with its links and the
    citation mark that covers it, one inside it or at its end, else the next one in its paragraph."""
    text, links = plain(code)
    out = []
    for paragraph in text.split("\n"):
        pieces, start = [], 0
        for m in SENTENCE_END.finditer(paragraph.strip()):
            pieces.append(paragraph.strip()[start:m.end(1)])
            start = m.end()
        pieces.append(paragraph.strip()[start:])
        marks = [[int(i) for i in MARK.findall(piece)] for piece in pieces]
        for i, piece in enumerate(pieces):
            sentence = MARK.sub("", piece).strip()
            if len(sentence.split()) >= 3:  # leftovers like "thumb" or a lone name aren't sentences
                mark = next((found[0] for found in marks[i:] if found), None)
                out.append((sentence, [target for shown, target in links if shown and shown in sentence], mark))
    return out


def prose(wikitext):
    """[(heading, sentence, [link target, ...], citation)] of a page's prose in reading order, so the intro comes first,
    under the heading "". The citation is what the <ref> covering the sentence links first ("BB-4/Story#After
    operation"): a ref inside the sentence or at its end, else the next one in its paragraph, the reference following
    the claims it supports; None when nothing does. Templates (infoboxes, quotes), tables, files and headings are
    dropped. A link belongs to every sentence its shown text appears in, so a sentence keeps its links however the page
    wraps them.
    """
    code = mwparserfromhell.parse(wikitext)
    cites = _cite(code)
    out = []
    for section in code.get_sections(flat=True, include_lead=True):
        headings = section.filter_headings(recursive=False)
        heading = headings[0].title.strip_code().strip() if headings else ""
        for sentence, targets, mark in _split(mwparserfromhell.parse(str(section))):
            out.append((heading, sentence, targets, cites[mark] if mark is not None else None))
    return out


def sentences(wikitext):
    """[(sentence, [link target, ...])] of a page's prose in reading order: prose() without the headings and citations."""
    return [(sentence, targets) for _, sentence, targets, _ in prose(wikitext)]


def archive(wikitext):
    """[(title, [(sentence, [link target, ...])])] of an operator's archive files: the {{Archive}} templates of its /File
    page, the game's own text, in the page's order (Profile first)."""
    return [(str(t.get("title").value).strip() if t.has("title") else "",
             [(s, targets) for s, targets, _ in _split(mwparserfromhell.parse(str(t.get("text").value)))])
            for t in mwparserfromhell.parse(wikitext).filter_templates() if str(t.name).strip() == "Archive" and t.has("text")]


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
