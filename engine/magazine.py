"""The weekly Economist tab.

Each week's issue is read and summarised by hand into engine/economist/issue.json: only the articles that bear on
politics and war, gold, oil, money and banking, or AI, each with a one- or two-paragraph summary and its likely
effects, in Persian and English (see engine/economist/README.md). This step adds what has to be looked up online,
the article's preview picture, and publishes economist.json for the app.

The Economist's article pages turn away requests from cloud machines, so the lead picture is read from a public
reader service's copy of the page (r.jina.ai), and a Bing News thumbnail of the same article is kept as a second
choice for when the first cannot be loaded. Pictures are only linked, never copied."""
import hashlib
import json
import os
import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

from . import http
from .http import parallel
from .util import data_path, load_json, log, save_json

ISSUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "economist", "issue.json")
CATS = ("pol", "gold", "oil", "money", "ai")
TIERS = ("red", "orange", "yellow")
RETRY = 3 * 3600            # look for missing pictures again after three hours
TRIES = 4                   # and give up on an article after four rounds
PER_ROUND = 8               # articles looked up per round, so a round never holds up the news
WIDTH = 960                 # picture width asked from The Economist's image service

# the lead picture is the first full-width image of the page, before the "more from this section" links
LEAD = re.compile(r"https://www\.economist\.com/cdn-cgi/image/width=1424[^)\s\"']*?/content-assets/images/"
                  r"([\w.-]+\.(?:jpe?g|png|webp))", re.I)
TAIL = re.compile(r"This article appeared in the |\n#+\s*More from |\nMore from ")
TITLE = re.compile(r"^Title:\s*(.+)$", re.M)


def _norm(u):
    u = unquote(u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    return u.split("?")[0].split("#")[0].rstrip("/")


def _reader(url):
    """Lead picture and web headline from the reader service's copy of the article page."""
    text = http.get("https://r.jina.ai/" + url, timeout=35, retries=0).text
    t = TITLE.search(text)
    title = unescape(t.group(1).strip()) if t else None
    if title and title.lower() in ("just a moment...", "economist.com"):
        return None, None                                   # a challenge page, not the article
    cut = TAIL.search(text)
    m = LEAD.search(text[:cut.start()] if cut else text)
    img = (f"https://www.economist.com/cdn-cgi/image/width={WIDTH},quality=80,format=auto/content-assets/images/"
           f"{m.group(1)}") if m else None
    return img, title


def _section_titles(urls):
    """Web headlines from the section feeds, for articles the reader service could not open."""
    out = {}
    for sec in sorted({urlparse(u).path.strip("/").split("/")[0] for u in urls}):
        try:
            text = http.get(f"https://www.economist.com/{sec}/rss.xml", timeout=20, retries=0).text
        except Exception:  # noqa: BLE001
            continue
        for it in re.findall(r"<item>(.*?)</item>", text, re.S):
            ti = re.search(r"<title>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</title>", it, re.S)
            li = re.search(r"<link>\s*(.*?)\s*</link>", it, re.S)
            if ti and li:
                out[_norm(li.group(1))] = unescape(ti.group(1).strip())
    return out


def _bing(url, title):
    """A Bing News thumbnail of exactly this article, found by its headline."""
    q = (title or urlparse(url).path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")) + " economist"
    text = http.get("https://www.bing.com/news/search", params={"q": q, "format": "rss"}, timeout=20, retries=0).text
    want = _norm(url)
    for it in re.findall(r"<item>(.*?)</item>", text, re.S):
        link = re.search(r"<link>(.*?)</link>", it, re.S)
        img = re.search(r"<News:Image>(.*?)</News:Image>", it, re.S)
        if not (link and img):
            continue
        target = parse_qs(urlparse(unescape(link.group(1).strip())).query).get("url", [""])[0]
        if _norm(target) == want:
            u = unescape(img.group(1).strip()).replace("http://", "https://", 1)
            return u + ("&" if "?" in u else "?") + "w=960&h=540&c=7"
    return None


def _look_up(arts, pics, t):
    for a, res, err in parallel(lambda x: _reader(x["url"]), [a for a in arts if not pics[a["url"]].get("img")],
                                workers=4):
        p = pics[a["url"]]
        if err is None and res:
            img, title = res
            if img:
                p["img"] = img
            if title:
                p["wt"] = title
        elif err is not None:
            p["err"] = str(err)[:80]
    need = [a for a in arts if not pics[a["url"]].get("alt")]
    if need:
        untitled = [a["url"] for a in need if not pics[a["url"]].get("wt")]
        titles = _section_titles(untitled) if untitled else {}
        headline = lambda a: pics[a["url"]].get("wt") or titles.get(_norm(a["url"]))  # noqa: E731
        for a, alt, err in parallel(lambda x: _bing(x["url"], headline(x)), need, workers=4):
            if err is None and alt:
                pics[a["url"]]["alt"] = alt
    for a in arts:
        p = pics[a["url"]]
        p["n"] = p.get("n", 0) + 1
        p["t"] = t


def _check(issue):
    """Problems in a hand-made issue file, logged once when the issue changes."""
    probs, ids = [], set()
    for a in issue.get("articles", []):
        if not a.get("id") or a["id"] in ids:
            probs.append(f"missing or repeated id {a.get('id')}")
        ids.add(a.get("id"))
        for lang in ("fa", "en"):
            if not (a.get(lang) or {}).get("t") or not (a.get(lang) or {}).get("s"):
                probs.append(f"{a.get('id')}: no {lang} title or summary")
        if not str(a.get("url", "")).startswith("https://www.economist.com/"):
            probs.append(f"{a.get('id')}: no Economist link")
    cats = issue.get("cats") or {}
    for k, lst in cats.items():
        if k not in CATS:
            probs.append(f"unknown category {k}")
        probs += [f"{k}: unknown article {i}" for i in lst if i not in ids]
    for i in cats.get("pol", []):
        a = next((x for x in issue.get("articles", []) if x.get("id") == i), {})
        if a and a.get("tier") not in TIERS:
            probs.append(f"{i}: politics article without a red/orange/yellow tier")
    return probs


def update(misc, t):
    issue = load_json(ISSUE, None)
    if not issue or not issue.get("articles"):
        return
    st = misc.get("econ") or {}
    if st.get("issue") != issue.get("issue"):
        st = {"issue": issue.get("issue"), "pics": {}}
        for p in _check(issue):
            log("economist issue:", p)
    pics = st.setdefault("pics", {})
    arts = [a for a in issue["articles"] if a.get("id") and str(a.get("url", "")).startswith("http")]
    for a in arts:
        pics.setdefault(a["url"], {})
    todo = [a for a in arts if not (pics[a["url"]].get("img") and pics[a["url"]].get("alt"))
            and pics[a["url"]].get("n", 0) < TRIES and t - pics[a["url"]].get("t", 0) >= RETRY]
    if todo:
        _look_up(todo[:PER_ROUND], pics, t)
        log(f"economist: pictures for {sum(1 for a in arts if pics[a['url']].get('img'))} of {len(arts)} articles, "
            f"thumbnails for {sum(1 for a in arts if pics[a['url']].get('alt'))}")

    out_arts = []
    for a in issue["articles"]:
        if not a.get("id"):
            continue
        p = pics.get(a.get("url")) or {}
        o = {k: a[k] for k in ("id", "url", "sec", "col", "page", "tier", "fa", "en") if k in a}
        o["img"], o["alt"] = p.get("img"), p.get("alt")
        out_arts.append(o)
    ids = {a["id"] for a in out_arts}
    cats = {k: [i for i in (issue.get("cats") or {}).get(k, []) if i in ids] for k in CATS}
    body = {"issue": issue.get("issue"), "cats": cats, "articles": out_arts}
    h = hashlib.sha1(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    if h != st.get("h") or not os.path.exists(data_path("economist.json")):
        save_json(data_path("economist.json"), {"v": 1, "updated": t, **body})
        st["h"] = h
        log(f"economist: issue {issue.get('issue')} published, {len(out_arts)} articles")
    misc["econ"] = st
