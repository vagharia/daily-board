"""The weekly Economist tab.

Each week's issue is read and summarised by hand into a file of its own under engine/economist/issues/ (named by
its date; the two newest are shown, the newer first): only the articles that bear on
the tab's categories (military, politics, oil and energy, commodities, money and banking, AI, cyber), in the
magazine's own order, each tagged with its categories and given a short summary and its likely effects, in Persian
and English (see engine/economist/README.md). This step adds what has to be looked up online,
the article's preview picture, and publishes economist.json for the app.

The Economist's article pages turn away requests from cloud machines, so the lead picture is read from a public
reader service's copy of the page (r.jina.ai). Only the article's own picture is used (news-search thumbnails were
sometimes about something else); an article without one shows none, unless a picture made for it by hand is given
in the issue file ("pic"), and "nopic" hides an own picture that doesn't fit. Pictures are only linked, never copied."""
import hashlib
import json
import os
import re
from html import unescape
from urllib.parse import unquote

from . import http
from .http import parallel
from .util import data_path, load_json, log, save_json

ISSUES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "economist", "issues")
KEEP = 2                    # issues shown in the tab, newest first
CATS = ("mil", "pol", "oil", "commod", "money", "ai", "cyber")
PER_ROUND = 8               # articles looked up per round, so a round never holds up the news
# each article is looked up once per issue; a picture not found then is left out (the card shows its icon instead)
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
        tags = a.get("tags") or []
        if not tags:
            probs.append(f"{a.get('id')}: no category tag")
        probs += [f"{a.get('id')}: unknown category {k}" for k in tags if k not in CATS]
    return probs


def _issues():
    """The newest KEEP issues, newest first; files are named YYYY-MM-DD.json."""
    out = []
    names = sorted((f for f in os.listdir(ISSUES) if f.endswith(".json")), reverse=True) if os.path.isdir(ISSUES) else []
    for f in names:
        iss = load_json(os.path.join(ISSUES, f), None)
        if iss and iss.get("articles"):
            iss.setdefault("issue", f[:-5])
            out.append(iss)
        if len(out) == KEEP:
            break
    return out


def _out_article(a, pics):
    p = pics.get(a.get("url")) or {}
    o = {k: a[k] for k in ("id", "url", "sec", "col", "page", "fa", "en") if k in a}
    o["tags"] = [k for k in a.get("tags") or [] if k in CATS]
    # only the article's own picture (a news-search thumbnail was sometimes about something else), or one made
    # by hand for it ("pic": a file under docs/econ/), or none ("nopic": its own picture doesn't fit)
    o["img"] = a.get("pic") or (None if a.get("nopic") else p.get("img"))
    return o


def update(misc, t):
    issues = _issues()
    if not issues:
        return
    st = misc.get("econ") or {}
    dates = [i.get("issue") for i in issues]
    if st.get("dates") != dates:
        st["dates"] = dates
        st.pop("issue", None)
        for iss in issues:
            for p in _check(iss):
                log(f"economist issue {iss.get('issue')}:", p)
    arts = [a for iss in issues for a in iss["articles"] if a.get("id") and str(a.get("url", "")).startswith("http")]
    urls = {a["url"] for a in arts}
    # pictures are kept per article link, so an issue that stays on from last week is not looked up again
    pics = {u: p for u, p in (st.get("pics") or {}).items() if u in urls}
    st["pics"] = pics
    for a in arts:
        pics.setdefault(a["url"], {})
    todo = [a for a in arts if not pics[a["url"]].get("n")]
    if todo:
        _look_up(todo[:PER_ROUND], pics, t)
        log(f"economist: pictures for {sum(1 for a in arts if pics[a['url']].get('img'))} of {len(arts)} articles")

    out = [{"issue": iss.get("issue"), "articles": [_out_article(a, pics) for a in iss["articles"] if a.get("id")]}
           for iss in issues]                                         # each in the magazine's order
    # the newest issue also at the top level, for copies of the app from before there were two
    body = {"issue": out[0]["issue"], "articles": out[0]["articles"], "issues": out}
    h = hashlib.sha1(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    if h != st.get("h") or not os.path.exists(data_path("economist.json")):
        save_json(data_path("economist.json"), {"v": 3, "updated": t, **body})
        st["h"] = h
        log(f"economist: issues {', '.join(dates)} published, {sum(len(i['articles']) for i in out)} articles")
    misc["econ"] = st
