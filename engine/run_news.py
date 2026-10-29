"""News run (every 30 minutes): sources -> relevance -> translation -> severity -> stories ->
media & posts on X -> airspace warnings & sea signals -> index & warning lights -> Telegram alerts -> JSON."""
import os
import re
import time

from . import alerts, aviation, collect, config, flash, magazine, media, sea, store, stories, util, xposts
from .classify import classify
from . import citation
from .cluster import Clusterer, prune, recluster, refresh
from .http import parallel
from .index import compute_index, compute_lights, hotspots
from .relevance import is_relevant
from .sources import BY_ID, GROUPS, SOURCES
from .translate import Translator, fix_terms
from .util import data_path, has_fa, fa_norm, first_sentences, load_json, log, now, save_json, speaker_first, truncate

MEMBER_KEYS = ("k", "s", "sn", "sn_fa", "rel", "u", "t", "ti", "su", "en_ti", "en_su", "img", "vid", "lang", "via",
               "sev", "topics", "flags", "ppl", "geo", "ctry", "wit")
PUBLIC_FLAGS = {"kinetic", "denial", "analysis", "opinion", "speculative", "past", "maritime_incident", "airspace",
                "evac", "deploy", "ultimatum", "sanctions", "exercise", "threat"}


_PAGE_ID = re.compile(r"/(\d{5,})(?=[/?#._-]|$)")


def page_id(url):
    """The numeric article id in a URL (entekhab.ir/fa/news/944944/…), leaving out dates such as 20261024."""
    for x in _PAGE_ID.findall(url or ""):
        if not (len(x) == 8 and x.startswith("20")):
            return x
    return None


def _words(s):
    return set(re.findall(r"\w{2,}", util.fa_norm(s or "").lower()))


def _similar_titles(a, b):
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.5


def retime_updates(new, raw, clusters, pages, T):
    """Entekhab's live page keeps the page's own date (00:11) on every update, and some outlets re-headline an
    article with fresh news under its old date. A new item from a page we already had from an earlier round,
    with that same date but a different headline, is timed when it first appeared (now). pages: the registry of
    pages seen in feeds, kept in the state. Returns the number of items retimed."""
    stored = {}
    for c in clusters:
        for m in c["m"]:
            pid = m.get("via") == "direct" and page_id(m.get("u"))
            if pid:
                stored.setdefault(f"{m['s']}:{pid}", []).append(m)
    n = 0
    for it in new:
        pid = it.get("via") == "direct" and page_id(it.get("u"))
        if not pid or T - it["t"] < 3600:
            continue
        key = f"{it['s']}:{pid}"
        p = pages.get(key)
        if not p or p["k"] == it["k"] or p["t"] != it["t"] or p["s"] >= T:
            continue
        if any(m["t"] == it["t"] and _similar_titles(m.get("ti"), it["ti"]) for m in stored.get(key, [])):
            continue                                       # only a reworded headline of a report we have
        it["t"] = T
        n += 1
    for it in raw:
        pid = it.get("via") == "direct" and page_id(it.get("u"))
        if pid:
            pages.setdefault(f"{it['s']}:{pid}", {"k": it["k"], "t": it["t"], "s": T})
    for key in [k for k, p in pages.items() if T - p["s"] > 3 * 86400]:
        del pages[key]
    return n


def fix_live_pages(clusters, seen):
    """One-time repair of stored reports that came from a live page or a re-headlined article (several reports
    from one page, same date, different headlines): time each by when it first appeared."""
    groups = {}
    for c in clusters:
        for m in c["m"]:
            pid = m.get("via") == "direct" and page_id(m.get("u"))
            if pid:
                groups.setdefault((m["s"], pid, m["t"]), []).append(m)
    n = 0
    for ms in groups.values():
        if len(ms) < 2 or all(_similar_titles(ms[0].get("ti"), m.get("ti")) for m in ms[1:]):
            continue
        for m in ms:
            first = seen.get(m["k"])
            if first and first - m["t"] >= 3600:
                m["t"] = first
                n += 1
    return n


def slim(it):
    return {k: it.get(k) for k in MEMBER_KEYS if it.get(k) not in (None, "", [])}


def ensure_texts(clusters, tr):
    """Fill c['en'] / c['fa'] (title + summary) from the best member in each language,
    translating the English representative into Persian when no good Persian original exists."""
    # Persian-only stories whose English translation failed earlier: try again
    redo = []
    for c in clusters:
        byk = {m["k"]: m for m in c["m"]}
        en_m = byk.get(c.get("en_from")) or c["m"][0]
        if en_m.get("lang") == "fa" and not en_m.get("en_ti"):
            redo.append(en_m)
    if redo:
        texts = [m["ti"] for m in redo] + [first_sentences(m["su"], 330) for m in redo if m.get("su")]
        res = tr.translate_many(texts, "fa", "en")
        for m in redo:
            m["en_ti"] = res.get(m["ti"], "")
            if m.get("su"):
                m["en_su"] = res.get(first_sentences(m["su"], 330), "")
    need = []
    for c in clusters:
        byk = {m["k"]: m for m in c["m"]}
        en_m = byk.get(c.get("en_from")) or c["m"][0]
        if en_m.get("lang") == "en":
            c["en"] = {"ti": speaker_first(en_m["ti"]), "su": en_m.get("su", "")}
        elif en_m.get("en_ti"):
            c["en"] = {"ti": en_m["en_ti"], "su": en_m.get("en_su") or "", "mt": 1}
        else:
            c["en"] = {"ti": en_m["ti"], "su": en_m.get("su") or "", "fallback": 1}
        fa_m = byk.get(c.get("fa_from")) if c.get("fa_from") else None
        if fa_m and fa_m.get("lang") == "fa":
            c["fa"] = {"ti": speaker_first(fa_m["ti"]), "su": fa_m.get("su", "")}
        elif c["en"].get("fallback"):
            c["fa"] = {"ti": speaker_first(en_m["ti"]), "su": en_m.get("su") or ""}   # Persian original, untranslated
        else:
            c["_fa_src"] = (c["en"]["ti"], first_sentences(c["en"]["su"], 330))
            need += [x for x in c["_fa_src"] if x]
    res = tr.translate_many(need, "en", "fa") if need else {}
    for c in clusters:
        src = c.pop("_fa_src", None)
        if not src:
            continue
        ti, su = src
        if res.get(ti):
            c["fa"] = {"ti": res[ti], "su": res.get(su, "") if su else "", "mt": 1}
        else:
            c["fa"] = {"ti": ti, "su": su, "fallback": 1}


PERSIAN_GROUPS = {"iran", "fa_intl", "tg"}


def persian_only(c):
    """Every report in the story comes from an Iranian, Persian-language-abroad or Telegram source."""
    return all(BY_ID.get(m["s"], {}).get("group") in PERSIAN_GROUPS for m in c["m"])


def big_claim(c):
    """An unconfirmed report from Telegram channels of something that would be orange or red if confirmed (a
    strike, an explosion, the internet cut): shown, yellow and labelled, though minor Persian-only yellow stories
    aren't."""
    return bool(c.get("unconf")) and c.get("claim", 0) >= config.TIER_ORANGE


def drop_reply_copies(clusters, seen, T):
    """Telegram posts of the last 36 hours that repeat an earlier post of the same channel word for word at the start
    (a reply read as the post it answers) leave their stories and are forgotten, so the next collection reads their
    own text. Returns how many were dropped."""
    first, n = {}, 0
    members = sorted(((m, c) for c in clusters for m in c["m"]), key=lambda x: x[0]["t"])
    for m, c in members:
        if m.get("via") != "tg" or T - m["t"] > 36 * 3600:
            continue
        key = (m["s"], fa_norm(m.get("ti") or "")[:40])
        if key in first and m["t"] - first[key] <= 24 * 3600:
            c["m"].remove(m)
            c.pop("en", None)                 # its headline may have come from the dropped copy
            c.pop("fa", None)
            seen.pop(m["k"], None)
            n += 1
        else:
            first.setdefault(key, m["t"])
    return n


_FOLLOW = re.compile(r"^(?P<reply>.+?) \((?:در ادامهٔ|following): (?P<orig>.+?)\)$")


def fix_follow_ups(clusters, T):
    """Short replies on Telegram stored as "<reply> (در ادامهٔ: <the post it answers>)" that only comment on that
    post ("ممکن هم هست ناشی از عوامل دیگری باشد…") leave their stories, as such comments are left out now
    (collect._tg_parse); follow-ups with news of their own stay. Returns how many were dropped."""
    n = 0
    for c in clusters:
        for m in list(c["m"]):
            g = _FOLLOW.match(m.get("ti") or "") if m.get("via") == "tg" and T - m["t"] <= 3 * 86400 else None
            if g and collect.follow_up_comment(g["reply"]):
                c["m"].remove(m)
                c.pop("en", None)
                c.pop("fa", None)
                n += 1
    return n


def reread_cut_posts(clusters, T):
    """Telegram posts of the last week whose headline was cut mid-sentence while their text lost the rest are
    read again, each from its own page, and get their whole text back. Returns (posts read again, posts found)."""
    by_id = BY_ID
    todo = [(m, c) for c in clusters for m in c["m"] if m.get("via") == "tg" and T - m["t"] <= 8 * 86400
            and (m.get("ti") or "").endswith("…") and m.get("s") in by_id]
    n = 0
    for (m, c), e, err in parallel(lambda mc: collect.tg_post(mc[0]["u"]), todo, workers=8):
        if err is not None or not e:
            continue
        its = collect.make_items(by_id[m["s"]], [e], "tg", T)
        if not its:
            continue
        m["ti"], m["su"] = its[0]["ti"], its[0]["su"]
        for k in ("en_ti", "en_su"):
            m.pop(k, None)                    # translated again from the whole text
        c.pop("en", None)
        c.pop("fa", None)
        n += 1
    return n, len(todo)


def rescore(clusters):
    out = []
    for c in clusters:
        keep = []
        for m in c["m"]:
            if not is_relevant(m)[1]:
                continue
            for tk, sk in (("ti", "su"), ("en_ti", "en_su")):
                lim = collect.TG_WHOLE if m.get("via") == "tg" else 160
                if len(m.get(tk) or "") > lim:          # stored before overlong headlines were split
                    head, rest = collect.split_long_title(m[tk], lim)
                    m[tk], m[sk] = head, (rest + " " + (m.get(sk) or "")).strip()
                    c.pop("en", None)
                    c.pop("fa", None)
            if m.get("lang") == "fa" or m.get("en_ti"):
                classify(m)
            keep.append(m)
        if not keep:
            continue
        if len(keep) < len(c["m"]):
            c.pop("en", None)                 # its headline may have come from a dropped report
            c.pop("fa", None)
        c["m"] = keep
        refresh(c)
        out.append(c)
    dropped = len(clusters) - len(out)
    if dropped:
        log(f"rescore: {dropped} stored stories no longer pass the relevance rules")
    return out


def lite(T, day, idx, lights, lang, front=()):
    """Everything the app's data-saving mode shows, in one small file per language: the three prices, the index,
    the lamps, the last day's headlines (no summaries, links, pictures or tags) and the main front's list."""
    tk = load_json(data_path("ticker.json"), {}) or {}
    pick = lambda d, ks: {k: d.get(k) for k in ks if d.get(k) is not None}  # noqa: E731
    other = "en" if lang == "fa" else "fa"
    return {
        "v": 1, "updated": T,
        "ticker": {"dollar": pick(tk.get("dollar") or {}, ("price", "chgDayPct", "status")),
                   "brent": pick(tk.get("brent") or {}, ("price", "chgPct", "status")),
                   "gold": pick(tk.get("gold") or {}, ("price", "chgPct", "status"))},
        "index": pick(idx, ("value", "zone", "label_fa", "label_en", "delta24")),
        "lights": [pick(l, ("id", "state", "fa", "en")) for l in lights],
        # id, tier, severity, time, number of sources, headline, first source, unconfirmed label, de-escalation tag
        "news": [[c["id"], c["tier"], round(c["sev"]), c["t"], c["ns"],
                  (c[lang] or {}).get("ti") or (c[other] or {}).get("ti", ""),
                  (c["src"][0].get("nf" if lang == "fa" else "n") or c["src"][0].get("n") or "") if c["src"] else "",
                  c.get("unconf") or "", 1 if c.get("green") else 0] for c in day],
        # the main front as it happens (flash.py): time, step, line, confirmed by a news outlet
        "front": [[e["t"], e["s"], e.get(lang) or e.get(other, ""), e.get("conf", 0)]
                  for e in front if T - e["t"] <= 48 * 3600][-80:],
    }


def public_cluster(c, short=False):
    srcs, seen = [], set()
    for m in sorted(c["m"], key=lambda m: (-(m.get("rel") or 0), m["t"])):
        key = m.get("sn") or m["s"]
        if key in seen:
            continue
        seen.add(key)
        srcs.append({"id": m["s"], "n": m.get("sn"), "nf": m.get("sn_fa"), "u": m["u"], "t": m["t"]})
    en, fa = dict(c.get("en") or {}), dict(c.get("fa") or {})
    if short:
        en["su"] = truncate(en.get("su", ""), 260)
        fa["su"] = truncate(fa.get("su", ""), 260)
    lang = next((m.get("lang") for m in c["m"] if m["k"] == c.get("en_from")), "en")
    return {
        "id": c["id"], "t": c["t"], "u": c["u"], "tier": c["tier"], "sev": c["sev"], "en": en, "fa": fa,
        "lang": lang, "img": c.get("img"), "vid": c.get("vid"), "src": srcs[:14], "ns": c.get("ns", len(srcs)),
        "topics": c.get("topics", []), "geo": c.get("geo", [])[:4], "ctry": c.get("ctry", [])[:5],
        "ppl": c.get("ppl", [])[:5], "flags": [f for f in c.get("flags", []) if f in PUBLIC_FLAGS],
        **({"unconf": c["unconf"] if isinstance(c["unconf"], str) else "event"} if c.get("unconf") else {}),
        **({"green": 1} if c.get("green") else {}),
        **({"fl": 1} if c.get("flash") else {}),
    }


def main():
    """One full news run (manual runs of the news workflow). The live loop calls news_round()."""
    store.prepare()
    news_round(full=True)
    store.publish("news")


def news_round(full=True):
    """Collect, score and write all news outputs into DATA_DIR (already prepared). A light round
    (full=False) reads the sources' own feeds and Telegram channels only; Google News / Bing fallbacks
    run in full rounds; airspace warnings are refreshed about once an hour."""
    started = time.time()
    T = now()
    st = lambda name, default: load_json(data_path("state", name), default)  # noqa: E731
    first_run = not os.path.exists(data_path("state", "clusters.json"))
    clusters = st("clusters.json", {"clusters": []})["clusters"]
    seen = st("seen.json", {})
    tcache = st("tcache.json", {})
    av_state = st("aviation_state.json", {}) or {}
    idx_hist = st("index_hist.json", [])
    alerts_state = st("alerts.json", {})
    x_state = st("x_state.json", {})
    sea_state = st("sea_state.json", {})
    misc = st("misc.json", {})
    if misc.get("state_version") != config.STATE_VERSION:
        log(f"state version {misc.get('state_version')} -> {config.STATE_VERSION}: starting stories afresh")
        clusters, seen, x_state, idx_hist = [], {}, {}, []
        alerts_state = {k: v for k, v in alerts_state.items() if k == "chat"}
        misc["state_version"] = config.STATE_VERSION
        first_run = True

    if misc.get("tg_replies") != 1:
        # replies on Telegram pages were once read as the post they answer: such copies are dropped and read again
        log(f"telegram replies to read again: {drop_reply_copies(clusters, seen, T)}")
        misc["tg_replies"] = 1
    if misc.get("tg_follow") != 1:
        log(f"telegram replies that only comment, dropped: {fix_follow_ups(clusters, T)}")
        misc["tg_follow"] = 1
    if misc.get("tg_cut") != 2:
        log("telegram posts cut mid-sentence, read again: %d of %d" % reread_cut_posts(clusters, T))
        misc["tg_cut"] = 2
    # stored stories are re-checked with the current rules, so rule changes apply at once
    clusters = rescore(clusters)
    if misc.get("live_fix") != 1:
        log(f"live-page reports retimed: {fix_live_pages(clusters, seen)}")
        misc["live_fix"] = 1
        misc["recluster"] = 0                 # so their stories are rebuilt just below
    if misc.get("recluster") != 10:
        # once after a clustering change: rebuild the last two days' stories from their reports
        for c in clusters:                    # names translated wrongly: Pezeshkian as "doctors", Hegseth as "Hegst"
            for m in c["m"]:
                if m.get("lang") == "fa" and m.get("en_ti"):
                    m["en_ti"] = fix_terms(m["ti"], m["en_ti"], "en")
                    if m.get("en_su"):
                        m["en_su"] = fix_terms(m.get("su") or "", m["en_su"], "en")
        n0 = len(clusters)
        clusters = recluster(clusters, T)
        misc["recluster"] = 10
        # re-formed stories must not trigger alerts again; new reports in this round still can
        sent = alerts_state.setdefault("sent", [])
        sent.extend(c["id"] for c in clusters if c.get("tier") == "red" and c["id"] not in sent)
        log(f"re-clustered recent stories: {n0} -> {len(clusters)}")
    if misc.get("reeval") != 3:
        # once after a relevance change: items of the last 36 hours that were left out get another look
        kept = {m["k"] for c in clusters for m in c["m"]}
        seen = {k: v for k, v in seen.items() if k in kept or v < T - 36 * 3600}
        misc["reeval"] = 3
        log("re-checking items of the last 36 hours with the current relevance rules")

    # ---------------------------------------------------------------- 1. collect
    raw, health = collect.collect_all(T, full=full)
    if not full:
        # sources only reachable through Google News / Bing keep their status from the last full round
        prev = {h["id"]: h for h in (load_json(data_path("health.json"), {}) or {}).get("sources", [])}
        for sid, h in health.items():
            p = prev.get(sid)
            if not h["ok"] and p and p.get("ok") and p.get("via") in ("gn", "bing"):
                health[sid] = {**h, "ok": True, "via": p["via"], "items": p.get("items", 0), "err": None}
    else:
        misc["last_full"] = T
    new = [it for it in raw if it["k"] not in seen]
    retimed = retime_updates(new, raw, clusters, misc.setdefault("pages", {}), T)
    if retimed:
        log(f"items timed when they appeared (live page or re-headlined article): {retimed}")
    for it in raw:
        seen.setdefault(it["k"], T)
    seen = {k: v for k, v in seen.items() if T - v <= config.WEEK + 3600}   # older items aren't collected anyway
    log(f"items: {len(raw)} fetched, {len(new)} new")

    # ---------------------------------------------------------------- 2. relevance
    rel_items = []
    for it in new:
        _, ok = is_relevant(it)
        if ok:
            rel_items.append(it)
            health[it["s"]]["relevant"] += 1
    log(f"relevant new items: {len(rel_items)}")

    # ---------------------------------------------------------------- 3. Persian items -> English
    tr = Translator(tcache)
    fa_items, deferred, budget = [], [], config.MAX_FA_TRANSLATE
    # citizen reports come with their English text already written (witness.py)
    for it in sorted([it for it in rel_items if it["lang"] == "fa" and not it.get("wit")], key=lambda x: -x["t"]):
        if tr.get(it["ti"], "fa", "en") is not None:
            fa_items.append(it)
        elif budget > 0:
            fa_items.append(it)
            budget -= 1
        else:
            deferred.append(it)
    if deferred:
        # too many Persian items for one run: the oldest wait for the next run
        dk = {it["k"] for it in deferred}
        rel_items = [it for it in rel_items if it["k"] not in dk]
        for k in dk:
            seen.pop(k, None)
        for it in deferred:
            health[it["s"]]["relevant"] -= 1
        log(f"persian items deferred to the next run: {len(deferred)}")
    texts = []
    for it in fa_items:
        texts.append(it["ti"])
        if it.get("su"):
            texts.append(first_sentences(it["su"], 330))
    res = tr.translate_many(texts, "fa", "en") if texts else {}
    for it in rel_items:
        if it.get("wit"):
            pass
        elif it["lang"] == "fa":
            it["en_ti"] = res.get(it["ti"], "")
            it["en_su"] = res.get(first_sentences(it.get("su", ""), 330), "") if it.get("su") else ""
        else:
            it["en_ti"], it["en_su"] = it["ti"], it.get("su", "")
        classify(it)

    # ---------------------------------------------------------------- 4. stories
    cl = Clusterer(clusters)
    changed = {}
    for it in sorted(rel_items, key=lambda x: x["t"]):
        c, _ = cl.add(slim(it))
        changed[c["id"]] = c
    clusters = prune(cl.clusters, T)
    alive = {c["id"] for c in clusters} - cl.merged_away
    changed = {k: v for k, v in changed.items() if k in alive}
    for c in changed.values():
        refresh(c)
    log(f"stories: {len(clusters)} total, {len(changed)} new/updated")
    n = citation.verify(clusters, T)
    if n:
        log(f"channel posts relaying an outlet, checked against it: {n} changed")

    # ---------------------------------------------------------------- 5. pages: images & embedded posts
    candidates = []
    for it in rel_items:
        for h, tid in media.tweets_in(it.get("html", "")):
            c = next((c for c in changed.values() if any(m["k"] == it["k"] for m in c["m"])), None)
            candidates.append((h, tid, c["id"] if c else None))
    targets = []
    for c in sorted(changed.values(), key=lambda c: -c["sev"]):
        want_img = not c.get("img")
        want_posts = "statement" in c.get("topics", []) or c["tier"] != "yellow"
        if not (want_img or want_posts):
            continue
        for m in sorted(c["m"], key=lambda m: -(m.get("rel") or 0)):
            if m.get("via") != "gn" and m["u"].startswith("http"):
                targets.append((c, m["u"]))
                break
        if len(targets) >= config.MAX_PAGE_FETCHES:
            break
    pages_ok = 0
    for (c, url), meta, err in parallel(lambda t: media.page_meta(t[1]), targets, workers=10):
        if err or not meta:
            continue
        pages_ok += 1
        if meta.get("img") and not c.get("img"):
            c["img"] = meta["img"]
        if meta.get("vid") and not c.get("vid"):
            c["vid"] = meta["vid"]
        for h, tid in meta.get("tweets", []):
            candidates.append((h, tid, c["id"]))
    log(f"pages: {pages_ok}/{len(targets)} fetched, {len(candidates)} post candidates")

    # ---------------------------------------------------------------- 6. display texts
    retry = [c for c in clusters if c["id"] not in changed and
             ("en" not in c or "fa" not in c or (c.get("fa") or {}).get("fallback")
              or (c.get("en") or {}).get("fallback"))]
    for c in retry:
        if "en_from" not in c:
            refresh(c)
    retry.sort(key=lambda c: ("en" in c and "fa" in c, -c["u"]))
    if misc.get("speaker_fix") != 2:
        # once: "Quote — Speaker" headlines of the last two days, put the other way round and translated again
        again = [c for c in clusters if T - c["u"] <= 2 * 86400 and c["id"] not in changed]
        retry = [c for c in retry if c not in again] + again
        misc["speaker_fix"] = 2
        ensure_texts(list(changed.values()) + retry, tr)
    else:
        ensure_texts(list(changed.values()) + retry[:150], tr)
    for c in clusters:                      # source-dependent corrections, for earlier translations too
        if (c.get("fa") or {}).get("mt") and c.get("en"):
            for f in ("ti", "su"):
                if c["fa"].get(f):
                    c["fa"][f] = fix_terms(c["en"].get(f, ""), c["fa"][f], "fa")
    for c in clusters:                      # main-front stories told only by Telegram channels (flash.py)
        if T - c["u"] > 2 * 86400 or not any(flash.events(m) for m in c["m"]):
            c.pop("flash", None)
            continue
        c["flash"] = 1                      # a sign of war at the main front: the card shows its latest report too
        fx = flash.story_texts(c)           # told only by channels: a headline made of all their reports
        if fx:
            c["en"], c["fa"] = fx["en"], fx["fa"]
    for c in clusters:                      # a headline or summary set by hand (c["fixed"]) is kept as it is
        for lang, fx in (c.get("fixed") or {}).items():
            if lang in ("en", "fa") and isinstance(fx, dict):
                c.setdefault(lang, {}).update({f: v for f, v in fx.items() if f in ("ti", "su") and v})
    for c in clusters:                      # never publish a story without a headline
        if "en" not in c or "fa" not in c:
            m = c["m"][0]
            c.setdefault("en", {"ti": m.get("en_ti") or m["ti"], "su": m.get("en_su") or m.get("su", ""), "fallback": 1})
            c.setdefault("fa", {"ti": m["ti"] if m.get("lang") == "fa" else c["en"]["ti"], "su": m.get("su", ""),
                                "fallback": 1})

    # ---------------------------------------------------------------- 7. posts on X + Truth Social
    truth = xposts.truth_social(BY_ID["truth"])
    th = health["truth"]
    th.update(ok=bool(truth) or th["ok"], via="direct" if truth else None, items=len(truth),
              relevant=len(truth), err=None if truth else "no relevant posts or feed unreachable")
    if misc.get("posts_fix") != 1:
        # once: forget everything that came in through a channel this project no longer reads
        ps, cand, seen_p = x_state.get("posts", {}), x_state.get("cand", {}), x_state.get("tg_seen", {})
        drop = [k for k, p in ps.items() if p.get("via") == "eitaa"
                or (cand.get(k, {}).get("own") and cand[k].get("h", "").lower() == "aghplt")]
        for k in drop:
            ps.pop(k, None)
        for k in [k for k, e in cand.items() if e.get("own") and e.get("h", "").lower() == "aghplt"]:
            cand.pop(k, None)
        for k in [k for k in seen_p if k.startswith("eitaa:")]:
            seen_p.pop(k, None)
        misc["posts_fix"] = 1
        log(f"posts from a dropped channel removed: {len(drop)}")
    extra = []
    if full:
        try:
            n_off = xposts.prune_off_topic(x_state)
            if n_off:
                log(f"posts no longer kept: {n_off}")
            extra += xposts.telegram_posts(x_state, tr)
        except Exception as e:  # noqa: BLE001
            log("telegram accounts failed:", str(e)[:120])
        try:
            extra += xposts.x_timelines(x_state, tr)[0]
        except Exception as e:  # noqa: BLE001
            log("x timelines failed:", str(e)[:120])
    try:
        extra += xposts.manual_posts()                # posts read off screenshots of X
    except Exception as e:  # noqa: BLE001
        log("posts from screenshots failed:", str(e)[:120])
    xstats = xposts.update(x_state, candidates, truth, extra)
    posts = xposts.newest(x_state.get("posts", {}))
    by_lang = {}
    for p in posts:
        lg = p.get("lang") or "en"
        lg = {"und": "auto", "zxx": "auto", "qme": "auto", "qht": "auto"}.get(lg, lg)
        by_lang.setdefault(lg, []).append(p)
    for lg, group in by_lang.items():
        if lg != "fa":
            todo = [p["text"] for p in group if not p.get("fa") or p.get("fa") == p["text"]]
            res = tr.translate_many(todo, lg, "fa") if todo else {}
            for p in group:
                if res.get(p["text"]):
                    p["fa"] = res[p["text"]]
        if lg != "en":
            todo = [p["text"] for p in group if not p.get("en") or p.get("en") == p["text"]]
            res = tr.translate_many(todo, lg, "en") if todo else {}
            for p in group:
                if res.get(p["text"]):
                    p["en"] = res[p["text"]]
        for p in group:
            p.setdefault("fa", p["text"])
            p.setdefault("en", p["text"])
            p["fa"] = fix_terms(p["text"] + " " + (p.get("en") or ""), p["fa"], "fa")

    # ---------------------------------------------------------------- 8. signals
    try:
        av = aviation.run(av_state, translate=lambda texts: tr.translate_many(texts, "en", "fa"))
    except Exception as e:  # noqa: BLE001
        log("aviation failed:", str(e)[:200])
        av = av_state.get("data") or {"status": "fail", "countries": []}
    sea_out = sea.run(sea_state)
    ticker = load_json(data_path("ticker.json"), {}) or {}
    idx, idx_hist = compute_index(clusters, av, sea_out, idx_hist, ticker)
    lights = compute_lights(clusters, av, sea_out, ticker)
    log(f"index={idx['value']} news={idx['news']} signals={idx['signals']} lights="
        f"{[l['id'] for l in lights if l['state'] == 'on']}")

    # ---------------------------------------------------------------- 9. alerts
    # instant alerts from the main front, step by step (flash.py); their stories don't also get the red-story alert
    fstate = alerts_state.setdefault("flash", {})
    start = {m["k"]: c["t"] for c in clusters for m in c["m"]}
    flash_msgs, _ = flash.process(fstate, rel_items, T, start, quiet=first_run)
    alert_res = alerts.run(alerts_state, clusters, lights, idx, first_run=first_run, flash_msgs=flash_msgs,
                           flash_keys=set(fstate.get("keys", {})))

    # ---------------------------------------------------------------- 10. stories, chosen every two hours
    if T - (misc.get("stories_t") or 0) >= stories.EVERY - 300 or not os.path.exists(data_path("stories.json")):
        chosen = stories.pick(clusters, T, hidden=lambda c: c["tier"] == "yellow" and persian_only(c))
        save_json(data_path("stories.json"), {"v": 1, "updated": T, "next": T + stories.EVERY,
                                              "stories": [public_cluster(c, short=True) for c in chosen]})
        misc["stories_t"] = T
        log(f"stories: {len(chosen)} chosen for the next two hours")

    # ---------------------------------------------------------------- 10b. the weekly Economist tab
    try:
        magazine.update(misc, T)
    except Exception as e:  # noqa: BLE001 - never holds up the news
        log("economist tab failed:", str(e)[:200])

    # ---------------------------------------------------------------- 11. outputs
    clusters.sort(key=lambda c: -c["u"])
    shown = [c for c in clusters if not (c["tier"] == "yellow" and persian_only(c) and not big_claim(c))]
    day = [public_cluster(c) for c in shown if T - c["u"] <= config.H24]
    week = [public_cluster(c, short=True) for c in shown]
    counts = lambda lst: {k: sum(1 for c in lst if c["tier"] == k) for k in ("red", "orange", "yellow")}  # noqa: E731
    save_json(data_path("news_24h.json"), {"v": 1, "updated": T, "range": "24h", "counts": counts(day), "clusters": day})
    save_json(data_path("news_week.json"), {"v": 1, "updated": T, "range": "week", "counts": counts(week),
                                            "clusters": week})
    save_json(data_path("signals.json"), {
        "v": 1, "updated": T, "index": idx, "lights": lights, "aviation": av, "sea": sea_out,
        "hotspots": {"24h": hotspots(shown, T, config.H24), "week": hotspots(shown, T, config.WEEK)},
        "alerts": {"enabled": bool(alert_res.get("enabled")), "linked": bool(alert_res.get("chat"))},
        "schedule": {"news_min": 5, "ticker_min": 5, "full_min": 15},
    })
    save_json(data_path("x.json"), {"v": 1, "updated": T, "posts": posts[:120], "stats": xstats})
    save_json(data_path("flash.json"), {"v": 1, "updated": T, "events": fstate.get("log", [])[-200:]})
    for lang in ("fa", "en"):
        save_json(data_path(f"lite_{lang}.json"), lite(T, day, idx, lights, lang, fstate.get("log", [])))
    src_health = []
    for s in SOURCES:
        h = health[s["id"]]
        src_health.append({**h, "group_fa": GROUPS[s["group"]][0], "group_en": GROUPS[s["group"]][1],
                           "lang": s["lang"]})
    sys_msgs = alerts.system(alerts_state, src_health, ticker, tr.stats, full)
    save_json(data_path("health.json"), {
        "v": 1, "updated": T, "duration": round(time.time() - started, 1), "full": full,
        "last_full": misc.get("last_full"),
        "ok_sources": sum(1 for h in src_health if h["ok"]), "total_sources": len(src_health),
        "new_items": len(new), "relevant": len(rel_items), "stories": len(clusters),
        "deferred": len(deferred), "translate": {**tr.stats, "errors": tr.errors}, "x": xstats,
        "pages": [pages_ok, len(targets)],
        "aviation": {"status": av.get("status"), "errors": av.get("errors")},
        "sea": {"status": sea_out.get("status"), "errors": sea_out.get("errors")},
        "alerts": alert_res, "system_msgs": sys_msgs, "sources": src_health, "log": util.LOGS[-250:],
    }, pretty=True)

    tr.prune()
    save_json(data_path("state", "clusters.json"), {"clusters": clusters})
    save_json(data_path("state", "seen.json"), seen)
    save_json(data_path("state", "tcache.json"), tr.cache)
    save_json(data_path("state", "aviation_state.json"), av_state)
    save_json(data_path("state", "index_hist.json"), idx_hist)
    save_json(data_path("state", "alerts.json"), alerts_state)
    save_json(data_path("state", "x_state.json"), x_state)
    save_json(data_path("state", "sea_state.json"), sea_state)
    store.heartbeat(misc)
    save_json(data_path("state", "misc.json"), misc)
    log(f"news round ({'full' if full else 'light'}) done in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
