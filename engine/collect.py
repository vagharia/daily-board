"""Fetch all 94 sources: direct feeds first, then Google News for whatever failed."""
import re
import time
from collections import defaultdict
from urllib.parse import quote, urlparse, urlunparse, parse_qsl, urlencode

from . import config, http, media
from .feeds import parse_feed
from .sources import SOURCES, BY_ID, source_for_domain
from .util import clean_summary, clean_title, first_sentences, has_fa, log, parse_date, sha

KW_EN = '(Iran OR Iranian OR Israel OR Israeli OR Hormuz OR Tehran OR IRGC OR Hezbollah OR Houthi OR "Persian Gulf" OR Gulf OR CENTCOM)'
KW_FA = "(آمریکا OR اسرائیل OR هرمز OR ترامپ OR سپاه OR حمله OR تحریم OR مذاکره OR موشک)"
GN_EN = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
GN_FA = "https://news.google.com/rss/search?q={q}&hl=fa&gl=IR&ceid=IR:fa"

_TRACK = re.compile(r"^(utm_|fbclid|gclid|cmpid|ito|ref|smid|mod|taid|ftag|guccounter|at_|ns_)", re.I)


def canonical(url: str) -> str:
    try:
        p = urlparse(url.strip())
        q = [(k, v) for k, v in parse_qsl(p.query) if not _TRACK.match(k)]
        host = p.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/")
        return urlunparse(("https", host, path, "", urlencode(q), ""))
    except Exception:  # noqa: BLE001
        return url


def make_items(src, entries, via, T, gn_source=None):
    out = []
    for e in entries:
        title = clean_title(e.get("title", ""))
        if via == "gn" and e.get("source_name"):
            suf = " - " + e["source_name"]
            if title.endswith(suf):
                title = title[: -len(suf)].strip()
        link = (e.get("link") or "").strip()
        if not title or len(title) < 12 or not link.startswith("http"):
            continue
        ts = parse_date(e.get("date")) or T
        if ts > T + 900:
            ts = T
        if T - ts > config.WEEK:
            continue
        su = "" if via == "gn" else clean_summary(e.get("summary") or e.get("content") or "")
        if su and (su == title or su.startswith(title[:50])):
            su = su[len(title):].strip(" .-—") if su.startswith(title) else ""
        su = first_sentences(su, 400)
        img, vid = media.from_entry(e, link)
        lang = "fa" if has_fa(title) else "en"
        name_en, name_fa = src["en"], src["fa"]
        if gn_source:
            name_en = name_fa = gn_source
        out.append({
            "k": sha(canonical(link) if via != "gn" else (title.lower() + src["id"]), 16),
            "s": src["id"], "sn": name_en, "sn_fa": name_fa, "rel": src["rel"], "u": link, "t": ts,
            "ti": title, "su": su, "img": img, "vid": vid, "lang": lang, "via": via,
            "html": ((e.get("summary") or "") + " " + (e.get("content") or ""))[:40000],
        })
    return out


def _fetch_feed(task):
    src, url = task
    r = http.get(url, timeout=20, retries=1)
    entries = parse_feed(r.content)
    if not entries:
        raise ValueError("empty or invalid feed")
    return entries


def _gn_query(sources, lang):
    if len(sources) == 1 and sources[0].get("gnq"):
        base = sources[0]["gnq"]
    else:
        sites = []
        for s in sources:
            sites += [f"site:{d}" for d in s["domains"]]
        base = "(" + " OR ".join(sites) + ")" if len(sites) > 1 else sites[0]
    kw = KW_FA if lang == "fa" else KW_EN
    q = f"{base} {kw} when:2d"
    return (GN_FA if lang == "fa" else GN_EN).format(q=quote(q))


def collect_all(T):
    health = {s["id"]: {"id": s["id"], "en": s["en"], "fa": s["fa"], "group": s["group"], "ok": False, "via": None,
                        "items": 0, "relevant": 0, "err": None} for s in SOURCES}
    per_source = defaultdict(list)
    tasks = [(s, u) for s in SOURCES if s["kind"] == "news" for u in s["feeds"]]
    t0 = time.time()
    for (src, url), entries, err in http.parallel(_fetch_feed, tasks, workers=16):
        if err is not None:
            if not per_source.get(src["id"]):
                health[src["id"]]["err"] = f"{type(err).__name__}: {str(err)[:70]}"
            continue
        its = make_items(src, entries, "direct", T)
        per_source[src["id"]].extend(its)
        health[src["id"]]["err"] = None
    log(f"direct feeds: {len(tasks)} requests in {time.time() - t0:.1f}s, "
        f"{sum(1 for v in per_source.values() if v)} sources ok")

    # ---- Google News fallback
    need = [s for s in SOURCES if s["kind"] == "news" and s["gn"] and not per_source.get(s["id"])]
    special = [s for s in need if s.get("gnq")]
    normal = [s for s in need if not s.get("gnq")]
    queries = [([s], s["lang"]) for s in special]
    for lang in ("en", "fa"):
        pool = [s for s in normal if s["lang"] == lang]
        for i in range(0, len(pool), 5):
            queries.append((pool[i:i + 5], lang))
    t0 = time.time()
    for group, lang in queries:
        url = _gn_query(group, lang)
        try:
            r = http.get(url, timeout=20, retries=1)
            entries = parse_feed(r.content)
        except Exception as e:  # noqa: BLE001
            for s in group:
                health[s["id"]]["err"] = (health[s["id"]]["err"] or "") + f" | gn: {str(e)[:50]}"
            time.sleep(1.5)
            continue
        ids = {s["id"] for s in group}
        for e in entries:
            host = urlparse(e.get("source_url") or "").netloc
            if len(group) == 1 and group[0].get("gnq"):
                src = group[0]
                gn_name = e.get("source_name") or src["en"] if src["id"] == "ukmto" else None
                its = make_items(src, [e], "gn", T, gn_source=gn_name)
            else:
                src = source_for_domain(host)
                cand = [s for s in group if any(host.endswith(d.split("/")[0]) for d in s["domains"])]
                if cand:
                    src = cand[0]
                if not src or src["id"] not in ids:
                    continue
                its = make_items(src, [e], "gn", T)
            per_source[src["id"]].extend(its)
        time.sleep(1.2)
    log(f"google news: {len(queries)} queries in {time.time() - t0:.1f}s")

    items, keys = [], set()
    for sid, its in per_source.items():
        uniq = []
        titles = set()
        for it in sorted(its, key=lambda x: -x["t"]):
            tkey = it["ti"].lower()[:90]
            if it["k"] in keys or tkey in titles:
                continue
            keys.add(it["k"])
            titles.add(tkey)
            uniq.append(it)
        if uniq:
            h = health[sid]
            h["ok"] = True
            h["items"] = len(uniq)
            h["via"] = "gn" if all(i["via"] == "gn" for i in uniq) else "direct"
            h["err"] = None if h["via"] == "direct" else h["err"]
        items.extend(uniq)
    return items, health
