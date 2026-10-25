"""News run (every 30 minutes): sources -> relevance -> translation -> severity -> stories ->
media & posts on X -> air & sea signals -> index & warning lights -> Telegram alerts -> JSON."""
import os
import time

from . import air, alerts, collect, config, media, sea, store, util, xposts
from .classify import classify
from .cluster import Clusterer, prune, refresh
from .http import parallel
from .index import compute_index, compute_lights, hotspots
from .relevance import is_relevant
from .sources import BY_ID, GROUPS, SOURCES
from .translate import Translator
from .util import data_path, first_sentences, load_json, log, now, save_json, truncate

MEMBER_KEYS = ("k", "s", "sn", "sn_fa", "rel", "u", "t", "ti", "su", "en_ti", "en_su", "img", "vid", "lang", "via",
               "sev", "topics", "flags", "ppl", "geo", "ctry")
PUBLIC_FLAGS = {"kinetic", "denial", "analysis", "opinion", "speculative", "past", "maritime_incident", "airspace",
                "evac", "deploy", "ultimatum", "sanctions", "exercise", "threat"}


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
            c["en"] = {"ti": en_m["ti"], "su": en_m.get("su", "")}
        elif en_m.get("en_ti"):
            c["en"] = {"ti": en_m["en_ti"], "su": en_m.get("en_su") or "", "mt": 1}
        else:
            c["en"] = {"ti": en_m["ti"], "su": en_m.get("su") or "", "fallback": 1}
        fa_m = byk.get(c.get("fa_from")) if c.get("fa_from") else None
        if fa_m and fa_m.get("lang") == "fa":
            c["fa"] = {"ti": fa_m["ti"], "su": fa_m.get("su", "")}
        elif c["en"].get("fallback"):
            c["fa"] = {"ti": en_m["ti"], "su": en_m.get("su") or ""}          # Persian original, untranslated
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


def rescore(clusters):
    out = []
    for c in clusters:
        keep = []
        for m in c["m"]:
            if not is_relevant(m)[1]:
                continue
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
    }


def main():
    started = time.time()
    T = now()
    store.prepare()
    st = lambda name, default: load_json(data_path("state", name), default)  # noqa: E731
    first_run = not os.path.exists(data_path("state", "clusters.json"))
    clusters = st("clusters.json", {"clusters": []})["clusters"]
    seen = st("seen.json", {})
    tcache = st("tcache.json", {})
    air_hist = st("air_hist.json", [])
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

    # stored stories are re-checked with the current rules, so rule changes apply at once
    clusters = rescore(clusters)

    # ---------------------------------------------------------------- 1. collect
    raw, health = collect.collect_all(T)
    new = [it for it in raw if it["k"] not in seen]
    for it in raw:
        seen.setdefault(it["k"], T)
    seen = {k: v for k, v in seen.items() if T - v <= 9 * 86400}
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
    for it in sorted([it for it in rel_items if it["lang"] == "fa"], key=lambda x: -x["t"]):
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
        if it["lang"] == "fa":
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
    alive = {c["id"] for c in clusters}
    changed = {k: v for k, v in changed.items() if k in alive}
    for c in changed.values():
        refresh(c)
    log(f"stories: {len(clusters)} total, {len(changed)} new/updated")

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
    ensure_texts(list(changed.values()) + retry[:150], tr)
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
    xstats = xposts.update(x_state, candidates, truth)
    posts = xposts.ranked(x_state.get("posts", {}))
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

    # ---------------------------------------------------------------- 8. signals
    air_sum, air_hist = air.run(air_hist)
    sea_out = sea.run(sea_state)
    ticker = load_json(data_path("ticker.json"), {}) or {}
    idx, idx_hist = compute_index(clusters, air_sum, sea_out, idx_hist)
    lights = compute_lights(clusters, air_sum, sea_out, ticker)
    log(f"index={idx['value']} news={idx['news']} signals={idx['signals']} lights="
        f"{[l['id'] for l in lights if l['state'] == 'on']}")

    # ---------------------------------------------------------------- 9. alerts
    alert_res = alerts.run(alerts_state, clusters, lights, idx, first_run=first_run)

    # ---------------------------------------------------------------- 10. outputs
    clusters.sort(key=lambda c: -c["u"])
    day = [public_cluster(c) for c in clusters if T - c["u"] <= config.H24]
    week = [public_cluster(c, short=True) for c in clusters]
    counts = lambda lst: {k: sum(1 for c in lst if c["tier"] == k) for k in ("red", "orange", "yellow")}  # noqa: E731
    save_json(data_path("news_24h.json"), {"v": 1, "updated": T, "range": "24h", "counts": counts(day), "clusters": day})
    save_json(data_path("news_week.json"), {"v": 1, "updated": T, "range": "week", "counts": counts(week),
                                            "clusters": week})
    save_json(data_path("signals.json"), {
        "v": 1, "updated": T, "index": idx, "lights": lights, "air": air_sum, "sea": sea_out,
        "hotspots": {"24h": hotspots(clusters, T, config.H24), "week": hotspots(clusters, T, config.WEEK)},
        "alerts": {"enabled": bool(alert_res.get("enabled")), "linked": bool(alert_res.get("chat"))},
        "schedule": {"news_min": 30, "ticker_min": 5},
    })
    save_json(data_path("x.json"), {"v": 1, "updated": T, "posts": posts[:120], "stats": xstats})
    src_health = []
    for s in SOURCES:
        h = health[s["id"]]
        src_health.append({**h, "group_fa": GROUPS[s["group"]][0], "group_en": GROUPS[s["group"]][1],
                           "lang": s["lang"]})
    save_json(data_path("health.json"), {
        "v": 1, "updated": T, "duration": round(time.time() - started, 1),
        "ok_sources": sum(1 for h in src_health if h["ok"]), "total_sources": len(src_health),
        "new_items": len(new), "relevant": len(rel_items), "stories": len(clusters),
        "deferred": len(deferred), "translate": {**tr.stats, "errors": tr.errors}, "x": xstats,
        "pages": [pages_ok, len(targets)],
        "air": {"status": (air_sum or {}).get("status", "fail"), "providers": (air_sum or {}).get("providers"),
                "errors": (air_sum or {}).get("errors")},
        "sea": {"status": sea_out.get("status"), "errors": sea_out.get("errors")},
        "alerts": alert_res, "sources": src_health, "log": util.LOGS[-250:],
    }, pretty=True)

    tr.prune()
    save_json(data_path("state", "clusters.json"), {"clusters": clusters})
    save_json(data_path("state", "seen.json"), seen)
    save_json(data_path("state", "tcache.json"), tr.cache)
    save_json(data_path("state", "air_hist.json"), air_hist)
    save_json(data_path("state", "index_hist.json"), idx_hist)
    save_json(data_path("state", "alerts.json"), alerts_state)
    save_json(data_path("state", "x_state.json"), x_state)
    save_json(data_path("state", "sea_state.json"), sea_state)
    store.heartbeat(misc)
    save_json(data_path("state", "misc.json"), misc)
    store.publish("news")
    log(f"done in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
