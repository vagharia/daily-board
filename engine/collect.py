"""Fetch all 94 sources. Order of attempts per source:
1. its own feeds;  2. Google News (grouped, with topic keywords);  3. Google News per domain without
keywords;  4. the source's public Telegram channel;  5. Bing News per domain."""
import re
import time
from collections import defaultdict
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup

from . import config, http, media
from .feeds import parse_feed
from .sources import SOURCES, source_for_domain
from . import witness
from .util import fa_norm, clean_summary, clean_title, first_sentences, has_fa, log, parse_date, sha, norm_url, tg_text

KW_EN = '(Iran OR Iranian OR Israel OR Israeli OR Hormuz OR Tehran OR IRGC OR Hezbollah OR Houthi OR "Persian Gulf" OR Gulf OR CENTCOM)'
KW_FA = "(آمریکا OR اسرائیل OR هرمز OR ترامپ OR سپاه OR حمله OR تحریم OR مذاکره OR موشک)"
GN_EN = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
GN_FA = "https://news.google.com/rss/search?q={q}&hl=fa&gl=IR&ceid=IR:fa"
BING = "https://www.bing.com/news/search?q={q}&format=rss&setlang={lang}&mkt={mkt}"

_TRACK = re.compile(r"^(utm_|fbclid|gclid|cmpid|ito|ref|smid|mod|taid|ftag|guccounter|at_|ns_)", re.I)
_OLD_DATE = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2},? ((?:19|20)\d\d)\b", re.I)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]+")


def _pause(sec):
    if not config.OFFLINE:
        time.sleep(sec)


def canonical(url: str) -> str:
    try:
        p = urlparse(url.strip())
        q = [(k, v) for k, v in parse_qsl(p.query) if not _TRACK.match(k)]
        host = p.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return urlunparse(("https", host, p.path.rstrip("/"), "", urlencode(q), ""))
    except Exception:  # noqa: BLE001
        return url


_SEP = re.compile(r"\s*(?:/|؛|;|\s\|\s|\s[-–—]\s)\s*")


def split_long_title(title, limit=160):
    """Some outlets put a whole lede in the headline ("A / B / C"). Keep the first part as the headline."""
    if len(title) <= limit:
        return title, ""
    for m in _SEP.finditer(title):
        if 35 <= m.start() <= limit:
            return title[:m.start()].strip(), title[m.end():].strip()
    cut = title[:limit]
    sp = cut.rfind(" ")
    head = cut[:sp] if sp > limit * 0.6 else cut
    return head.rstrip(" ,،:") + "…", title[len(head):].strip()


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+")
_POST_TAG = re.compile(r"^(?:confirmed|update|updated|note|breaking|alert|important)\s*:\s*", re.I)
_POST_TAIL = re.compile(r"\s*(?:follow the latest|more (?:details|info\w*)|read more|see more|details)\b[^.]*$", re.I)


def post_text(html):
    """A social post as headline text: no emoji, links, hashtag signs or closing calls to follow."""
    s = clean_summary(html)
    s = re.sub(r"https?://\S+", " ", s)
    s = _EMOJI.sub(" ", s)
    s = re.sub(r"#\s?(?=\w)", "", s)                 # "#Iran", "# Iran"
    s = re.sub(r"\s+", " ", s).strip(" -—–|:")
    s = _POST_TAIL.sub("", s)
    return _POST_TAG.sub("", s).strip(" -—–|:")


def make_items(src, entries, via, T, gn_source=None):
    out = []
    for e in entries:
        title = clean_title(e.get("title", ""))
        post = src.get("kind") == "posts" and not title
        if post:
            title = post_text(e.get("summary") or e.get("content") or "")
        if via in ("gn", "bing") and e.get("source_name"):
            suf = " - " + e["source_name"]
            if title.endswith(suf):
                title = title[: -len(suf)].strip()
        if via == "gn" and " - " in title:
            head, _, tail = title.rpartition(" - ")
            if len(tail) <= 45 and len(head) >= 20:
                title = head.strip()             # Google News appends the outlet ("… - AP")
        link = (e.get("link") or "").strip()
        if via == "bing" and "apiclick" in link:
            real = parse_qs(urlparse(link).query).get("url", [None])[0]
            if real:
                link = real
        if not title or len(title) < 12 or not link.startswith("http"):
            continue
        if src["lang"] != "fa" and has_fa(title):
            continue                     # Arabic-language items from Arab outlets (we read their English output)
        m = _OLD_DATE.search(title)
        if m and int(m.group(1)) < time.gmtime(T).tm_year:
            continue                     # "June 17, 2024 - Israel-Gaza news": an old live page
        ts = parse_date(e.get("date"))
        if ts is None:
            continue                     # undated items are usually stale feed leftovers
        ts += src.get("tz", 0)
        if ts > T + 900:
            ts = T
        if T - ts > config.WEEK:
            continue
        su = "" if via == "gn" or post else clean_summary(e.get("summary") or e.get("content") or "")
        if su and (su == title or su.startswith(title[:50])) and not (via == "tg" and title.endswith("…")):
            su = su[len(title):].strip(" .-—") if su.startswith(title) else ""
        title, rest = split_long_title(title, TG_WHOLE if via == "tg" else 160)
        if rest:
            su = (rest.rstrip(" .") + ". " + su).strip() if su else rest
        su = first_sentences(su, 400)
        img, vid = media.from_entry(e, link)
        name_en, name_fa = src["en"], src["fa"]
        if gn_source:
            name_en = name_fa = gn_source
        out.append({
            "k": sha(canonical(link) if via != "gn" else (title.lower() + src["id"]), 16),
            "s": src["id"], "sn": name_en, "sn_fa": name_fa, "rel": src["rel"], "u": link, "t": ts,
            "ti": title, "su": su, "img": img, "vid": vid, "lang": "fa" if has_fa(title) else "en", "via": via,
            "html": ((e.get("summary") or "") + " " + (e.get("content") or ""))[:40000],
            **({k: e[k] for k in ("wit", "en_ti", "en_su")} if e.get("wit") else {}),
        })
    return out


# ------------------------------------------------------------------ Telegram channels (public web preview)
_BG = re.compile(r"background-image:url\('([^']+)'\)")


_TG_PREFIX = re.compile(r"^(فوری|خبر فوری|مهم|ویدیو|ویدئو|فیلم|عکس|تصاویر|اینفوگرافیک|گزارش|breaking|video)\s*[|:｜/-]\s*",
                        re.I)


def _clean_tg_line(s):
    s = _EMOJI.sub(" ", s)
    s = re.sub(r"(?:^|\s)[#@]\S+", " ", s)
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -–—|•*▪◾🔹")
    s = _TG_PREFIX.sub("", s)
    return s.strip(" -–—|•*")


TG_TITLE = 220
TG_WHOLE = 300
_SENT_END = re.compile(r"[.!؟?](?=\s)")


def tg_head(first, rest):
    """A channel post's first paragraph as its headline. A long one is cut at the end of a sentence; if it is one
    long sentence, the headline is cut at a word and the text keeps the whole sentence, so nothing reads half-said."""
    if len(first) <= TG_TITLE:
        return first, rest
    ends = [m.end() for m in _SENT_END.finditer(first) if 40 <= m.end() <= TG_TITLE]
    if ends:
        return first[: ends[-1]].strip(), (first[ends[-1]:].strip() + " " + rest).strip()
    if len(first) <= TG_WHOLE:
        return first, rest                       # one sentence, a little long: kept whole rather than cut
    cut = first[:TG_TITLE]
    return cut[: cut.rfind(" ")].rstrip(" ,،:(") + "…", (first + " " + rest).strip()


def tg_post(url):
    """One channel post read again on its own (its embed page), as tg_entries reads it; None if not readable."""
    url = url.split("?")[0]
    post = url.split("t.me/", 1)[-1]
    try:
        out = _tg_parse(BeautifulSoup(http.get(url + "?embed=1", timeout=20, retries=1).content, "lxml"))
    except Exception:  # noqa: BLE001 - the channel page around it is tried next
        out = []
    if not out:                                   # the channel page that ends with this post
        handle, _, num = post.partition("/")
        r = http.get(f"https://t.me/s/{handle}?before={int(num) + 1}", timeout=20, retries=1)
        out = _tg_parse(BeautifulSoup(r.content, "lxml"))
    out = [e for e in out if e["link"].endswith("/" + post)]
    return out[0] if out else None


def tg_entries(handle):
    r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=1)
    return _tg_parse(BeautifulSoup(r.content, "lxml"))


def follow_up_comment(text):
    """A short reply that only comments ("ممکن هم هست…", "نگو که…", "البته باید صبر کرد"): no news of its own, no
    denial, no place named, no one quoted."""
    from .classify import score_en
    from .classify_fa import DENIAL, score_fa
    from .lexicon import PLACES_RX, match_keys
    if has_fa(text):
        sev, _, _ = score_fa(text, "")
        if DENIAL.search(fa_norm(text)):
            return False
    else:
        sev, _, fl = score_en(text, "")
        if "denial" in fl:
            return False
    from .classify import aside
    if aside(text):
        return True                         # "فکر کنید ایران … اعلام جنگ بدهد!": an aside, whatever it pictures
    if sev >= 40 or witness.cities_in(text, "fa" if has_fa(text) else "en") or re.match(r"^[^:：]{2,45}[:：]\s", text):
        return False                        # news of its own, a place, or someone quoted ("درخواست لرها: …")
    return not (match_keys(PLACES_RX, "" if has_fa(text) else text, text if has_fa(text) else ""))


def _tg_parse(soup):
    posts = []
    for div in soup.select("div.tgme_widget_message[data-post]"):
        rp = div.select_one("a.tgme_widget_message_reply")
        reply_to = (rp.get("href") or "").split("t.me/", 1)[-1].split("?")[0] if rp is not None else ""
        tnode, quoted = tg_text(div)
        tm = div.select_one("time[datetime]")
        if not tnode or not tm:
            continue
        for br in tnode.find_all("br"):
            br.replace_with("\n")
        raw = tnode.get_text("")
        wit = witness.parse(raw)
        lines = [_clean_tg_line(x) for x in raw.split("\n")]
        lines = [x for x in lines if x and "t.me/" not in x]
        if len(lines) > 1 and len(lines[0]) < 30 and lines[0].endswith(":"):
            lines = [lines[0] + " " + lines[1]] + lines[2:]          # "عراقچی:" + the quote
        lines = [x for x in lines if len(x) >= 8]
        if not lines:
            continue
        img = None
        ph = div.select_one(".tgme_widget_message_photo_wrap")
        if ph and ph.get("style"):
            m = _BG.search(ph["style"])
            if m:
                img = norm_url(m.group(1))
        posts.append({"post": div["data-post"], "lines": lines, "quoted": _clean_tg_line(quoted), "reply_to": reply_to,
                      "wit": wit, "date": tm["datetime"], "img": img})
    out = []
    for p in posts:
        lines, quoted, wit = p["lines"], p["quoted"], p["wit"]
        title, rest = lines[0], " ".join(lines[1:])
        if quoted and len(title) <= 70 and len(rest) < 40 and not wit:
            # a short reply to an earlier post. A comment on it ("ممکن هم هست ناشی از عوامل دیگری باشد…") adds no news:
            # a channel's comment on its own post is left out (the post itself is read on its own), a comment on
            # another channel's post is headed by that post. A follow-up with news of its own ("ترامپ این خبر را
            # تکذیب کرد", "گزارش مشابه از کرمانشاه و اهواز") is read together with the post it answers.
            if follow_up_comment(title + " " + rest):
                if p["reply_to"].split("/")[0].lower() == p["post"].split("/")[0].lower():
                    continue
                fa = has_fa(quoted + title)
                title, rest = quoted, (("در ادامه: " if fa else "Followed by: ") + title + (" " + rest if rest else ""))
            else:
                cut = quoted[:90]
                cut = cut[: cut.rfind(" ")] + "…" if len(quoted) > 90 and " " in cut else cut
                title = f"{title} (در ادامهٔ: {cut})" if has_fa(title + quoted) else f"{title} (following: {cut})"
        title, rest = tg_head(title, rest)
        extra = {}
        if wit:
            # citizen reports ("پیام‌های دریافتی: …"): one news sentence and a line of counts (witness.py)
            title, rest, en_ti, en_su = witness.texts(wit)
            extra = {"wit": wit, "en_ti": en_ti, "en_su": en_su}
        img = p["img"]
        out.append({"title": title, "link": f"https://t.me/{p['post']}", "summary": rest[:900], "content": "",
                    "date": p["date"], "media": [{"url": img, "type": "image/jpeg", "medium": "image", "w": 0}] if img else [],
                    "source_name": "", "source_url": "", **extra})
    return out


def collect_all(T, full=True):
    health = {s["id"]: {"id": s["id"], "en": s["en"], "fa": s["fa"], "group": s["group"], "ok": False, "via": None,
                        "items": 0, "relevant": 0, "err": None} for s in SOURCES}
    per_source = defaultdict(list)

    def note(sid, msg):
        h = health[sid]
        h["err"] = ((h["err"] + " | ") if h["err"] else "") + msg[:90]

    # ---- 1. direct feeds
    tasks = [(s, u) for s in SOURCES if s["kind"] in ("news", "posts") for u in s["feeds"]]
    t0 = time.time()

    def fetch_feed(task):
        r = http.get(task[1], timeout=20, retries=1)
        entries = parse_feed(r.content)
        if not entries:
            raise ValueError("empty or invalid feed")
        return entries

    for (src, url), entries, err in http.parallel(fetch_feed, tasks, workers=16):
        if err is not None:
            note(src["id"], f"feed: {type(err).__name__}: {str(err)[:60]}")
            continue
        its = make_items(src, entries, "direct", T)
        if not its:
            note(src["id"], "feed: no dated items in the last week")
        per_source[src["id"]].extend(its)
    log(f"direct feeds: {len(tasks)} requests in {time.time() - t0:.1f}s, "
        f"{sum(1 for v in per_source.values() if v)} sources with items")

    def empty(s):
        return s["kind"] in ("news", "tg") and not per_source.get(s["id"])

    def gn_fetch(url, group, special=False):
        try:
            r = http.get(url, timeout=20, retries=1)
            entries = parse_feed(r.content)
        except Exception as e:  # noqa: BLE001
            for s in group:
                note(s["id"], f"gn: {str(e)[:50]}")
            return
        ids = {s["id"] for s in group}
        for e in entries:
            host = urlparse(e.get("source_url") or "").netloc
            if special:
                src = group[0]
                gn_name = (e.get("source_name") or src["en"]) if src.get("via_media") else None
                per_source[src["id"]].extend(make_items(src, [e], "gn", T, gn_source=gn_name))
                continue
            cand = [s for s in group if any(host.endswith(d.split("/")[0]) for d in s["domains"])]
            src = cand[0] if cand else source_for_domain(host)
            if src and src["id"] in ids:
                per_source[src["id"]].extend(make_items(src, [e], "gn", T))

    # ---- 2. Google News, grouped with keywords (full rounds only: Google throttles frequent queries)
    need = [s for s in SOURCES if empty(s) and s["gn"]] if full else []
    queries = []
    for s in need:
        if s.get("gnq"):
            queries.append(([s], s["lang"], True, f"{s['gnq']} {KW_FA if s['lang'] == 'fa' else KW_EN} when:2d"))
    for lang in ("en", "fa"):
        pool = [s for s in need if not s.get("gnq") and s["lang"] == lang]
        for i in range(0, len(pool), 5):
            grp = pool[i:i + 5]
            sites = [f"site:{d}" for s in grp for d in s["domains"]]
            base = "(" + " OR ".join(sites) + ")" if len(sites) > 1 else sites[0]
            queries.append((grp, lang, False, f"{base} {KW_FA if lang == 'fa' else KW_EN} when:2d"))
    t0 = time.time()
    for grp, lang, special, q in queries:
        gn_fetch((GN_FA if lang == "fa" else GN_EN).format(q=quote(q)), grp, special)
        _pause(1.1)
    # ---- 3. Google News per domain, no keywords (official agencies rarely use our keywords)
    second = [s for s in SOURCES if empty(s) and s["gn"] and not s.get("gnq")] if full else []
    for s in second[:16]:
        sites = " OR ".join(f"site:{d}" for d in s["domains"])
        gn_fetch((GN_FA if s["lang"] == "fa" else GN_EN).format(q=quote(f"{sites} when:2d")), [s])
        _pause(1.1)
    log(f"google news: {len(queries)} grouped + {len(second[:16])} single queries in {time.time() - t0:.1f}s")

    # ---- 4. Telegram channels
    def tg_source(src):
        errs = []
        for handle in src["tg"]:
            try:
                its = make_items(src, tg_entries(handle), "tg", T)
            except Exception as e:  # noqa: BLE001
                errs.append(f"tg {handle}: {str(e)[:40]}")
                continue
            if its:
                return its, errs
            errs.append(f"tg {handle}: no posts")
        return [], errs

    for src, res, err in http.parallel(tg_source, [s for s in SOURCES if empty(s) and s.get("tg")], workers=4):
        if err is not None:
            note(src["id"], f"tg: {str(err)[:60]}")
            continue
        its, errs = res
        for m in errs:
            note(src["id"], m)
        per_source[src["id"]].extend(its)

    # ---- 5. Bing News per domain
    for s in ([s for s in SOURCES if empty(s) and s["kind"] == "news"][:20] if full else []):
        if s["kind"] != "news":
            continue
        q = quote(" OR ".join(f"site:{d}" for d in s["domains"]))
        try:
            r = http.get(BING.format(q=q, lang="fa" if s["lang"] == "fa" else "en", mkt="en-US"), timeout=20, retries=1)
            its = make_items(s, parse_feed(r.content), "bing", T)
            per_source[s["id"]].extend(its)
            if not its:
                note(s["id"], "bing: no items")
        except Exception as e:  # noqa: BLE001
            note(s["id"], f"bing: {str(e)[:50]}")
        _pause(0.8)

    items, keys = [], set()
    for sid, its in per_source.items():
        uniq, titles = [], set()
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
            vias = {i["via"] for i in uniq}
            h["via"] = "direct" if "direct" in vias else sorted(vias)[0]
        items.extend(uniq)
    return items, health
