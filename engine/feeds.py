"""Tolerant RSS / RDF / Atom parser built on lxml (no feedparser dependency)."""
import re

from lxml import etree

MEDIA_NS = ("http://search.yahoo.com/mrss/", "http://search.yahoo.com/mrss")
ATOM_NS = "http://www.w3.org/2005/Atom"

_ENTITY_FIX = {
    "&nbsp;": "&#160;", "&ndash;": "&#8211;", "&mdash;": "&#8212;", "&lsquo;": "&#8216;",
    "&rsquo;": "&#8217;", "&ldquo;": "&#8220;", "&rdquo;": "&#8221;", "&hellip;": "&#8230;",
    "&laquo;": "&#171;", "&raquo;": "&#187;", "&copy;": "&#169;", "&zwnj;": "&#8204;",
}


def _ln(el):
    t = el.tag
    if not isinstance(t, str):
        return None
    return t.rsplit("}", 1)[-1].lower()


def _ns(el):
    t = el.tag
    if isinstance(t, str) and t.startswith("{"):
        return t[1:].split("}", 1)[0]
    return ""


def _text(el):
    if el is None:
        return ""
    # include CDATA / nested markup as raw string
    if len(el):
        return (el.text or "") + "".join(etree.tostring(c, encoding="unicode", with_tail=True) for c in el)
    return el.text or ""


def _parse_xml(content: bytes):
    content = content.lstrip()
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]
    parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True,
                             huge_tree=True, remove_comments=True)
    root = None
    try:
        root = etree.fromstring(content, parser)
    except Exception:
        root = None
    if root is None or not len(root):
        txt = content.decode("utf-8", errors="replace")
        for k, v in _ENTITY_FIX.items():
            txt = txt.replace(k, v)
        txt = re.sub(r"&(?!#?\w+;)", "&amp;", txt)
        try:
            root = etree.fromstring(txt.encode("utf-8"), parser)
        except Exception:
            root = None
    return root


def parse_feed(content: bytes):
    """Return a list of raw entry dicts."""
    root = _parse_xml(content)
    if root is None:
        return []
    out = []
    for el in root.iter():
        name = _ln(el)
        if name in ("item", "entry"):
            e = _entry(el)
            if e and (e["title"] or e["link"]):
                out.append(e)
    return out


def _entry(el):
    d = {"title": "", "link": "", "summary": "", "content": "", "date": "", "guid": "",
         "media": [], "source_name": "", "source_url": ""}
    atom_links = []
    for c in el:
        name = _ln(c)
        ns = _ns(c)
        if name is None:
            continue
        if name == "title":
            d["title"] = _text(c)
        elif name == "link":
            href = c.get("href")
            if href:
                atom_links.append((c.get("rel", "alternate"), href, c.get("type", "")))
            elif c.text and c.text.strip():
                d["link"] = c.text.strip()
        elif name == "origlink":
            d["link"] = (c.text or "").strip() or d["link"]
        elif name in ("description", "summary"):
            if not d["summary"]:
                d["summary"] = _text(c)
        elif name == "encoded" or (name == "content" and ns not in MEDIA_NS):
            d["content"] = _text(c)
        elif name in ("pubdate", "published", "issued"):
            d["date"] = (c.text or "").strip() or d["date"]
        elif name in ("updated", "date", "modified"):
            if not d["date"]:
                d["date"] = (c.text or "").strip()
        elif name in ("guid", "id"):
            d["guid"] = (c.text or "").strip()
            if not d["link"] and c.get("isPermaLink", "true").lower() != "false" and d["guid"].startswith("http"):
                d["link"] = d["guid"]
        elif name == "enclosure":
            u = c.get("url") or c.get("href")
            if u:
                d["media"].append({"url": u, "type": c.get("type", ""), "medium": "", "w": 0})
        elif ns in MEDIA_NS and name in ("content", "thumbnail", "group"):
            _media(c, d["media"])
        elif name == "source":
            d["source_name"] = (c.text or "").strip()
            d["source_url"] = c.get("url") or c.get("href") or ""
        elif name == "image" and not ns.startswith("http://www.w3.org"):
            u = c.get("url") or c.get("href") or (c.text or "").strip()
            if u and u.startswith("http"):
                d["media"].append({"url": u, "type": "image/", "medium": "image", "w": 0})
    if atom_links and not d["link"]:
        alt = [h for r, h, t in atom_links if r == "alternate"]
        d["link"] = alt[0] if alt else atom_links[0][1]
    for r, h, t in atom_links:
        if r == "enclosure":
            d["media"].append({"url": h, "type": t, "medium": "", "w": 0})
    return d


def _media(el, acc):
    name = _ln(el)
    if name == "group":
        for c in el:
            if _ln(c) in ("content", "thumbnail"):
                _media(c, acc)
        return
    u = el.get("url")
    if not u:
        return
    try:
        w = int(el.get("width") or 0)
    except ValueError:
        w = 0
    medium = el.get("medium", "")
    typ = el.get("type", "")
    if name == "thumbnail":
        medium = medium or "image"
    acc.append({"url": u, "type": typ, "medium": medium, "w": w})
