"""Wikitext -> section headings, the link candidates in each section, and infobox fields."""
import mwparserfromhell


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
