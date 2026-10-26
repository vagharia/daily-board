"""Escalation index (0-100), warning lights and map hotspots.

News component: a severity-weighted average over the last 24h in which serious events weigh
exponentially more (so one missile strike is not drowned out by thirty routine statements),
recent events weigh more (6h half-life), and each story counts once however many outlets
report it. Signals component: Hormuz traffic and maritime incidents, and the airspace risk picture
(Safe Airspace risk levels and fresh official warnings for the core countries).
Index = 70% news + 30% signals.
"""
import math

from .aviation import recent_warnings
from .lexicon import PLACES
from .util import now

ZONES = [(25, "آرام نسبی", "Relative calm"), (50, "تنش متوسط", "Moderate tension"),
         (75, "تنش بالا", "High tension"), (101, "بحرانی", "Critical")]

LIGHTS = [
    ("strike", "حمله نظامی مستقیم", "Direct military strike"),
    ("hormuz", "حادثه دریایی / هرمز", "Hormuz / shipping incident"),
    ("airspace", "هشدار یا بسته شدن حریم هوایی", "Airspace warning / closure"),
    ("deploy", "اعزام ناو و هواپیماهای نظامی", "Carrier / military aircraft deployment"),
    ("evac", "تخلیه سفارت / هشدار سفر", "Embassy evacuation / travel alert"),
    ("ultimatum", "اولتیماتوم / ضرب‌الاجل", "Ultimatum / deadline"),
    ("oil", "جهش قیمت نفت", "Oil price spike"),
]
STATE_ACTORS = {"us", "il", "ir", "gulf"}


def zone(v):
    for i, (hi, fa, en) in enumerate(ZONES):
        if v < hi:
            return i, fa, en
    return 3, ZONES[-1][1], ZONES[-1][2]


def news_component(clusters, t):
    beta, half = 6.0, 6 * 3600
    num = den = 0.0
    # neutral prior so a quiet day sits low but not at zero
    w0 = 6 * math.exp(beta * 0.15)
    num += 15 * w0
    den += w0
    for c in clusters:
        age = t - c["u"]
        if age > 24 * 3600 or age < -3600:
            continue
        decay = 0.5 ** (max(0, age) / half)
        rel = max(m.get("rel", 0.6) for m in c["m"])
        s = c["sev"]
        w = math.exp(beta * s / 100) * decay * (0.6 + 0.4 * rel) * (1.0 if c.get("core", True) else 0.4)
        num += s * w
        den += w
    return round(num / den, 1) if den else 15.0


LEVEL_SCORE = {1: 85, 2: 60, 3: 35, 4: 15}


def aviation_score(av, t):
    """Mean risk level of the core countries' airspace, nudged up by official warnings of the last 3 days."""
    core = [c for c in (av or {}).get("countries", []) if c.get("core") and c.get("level")]
    if not core:
        return None
    base = sum(LEVEL_SCORE.get(c["level"], 15) for c in core) / len(core)
    fresh = len(recent_warnings(av, t, 3 * 86400))
    return min(100.0, base + min(20.0, 4.0 * fresh))


def signals_component(av, sea, clusters, t):
    parts = []
    a = aviation_score(av, t)
    if a is not None:
        parts.append(("airspace", 0.35, a))
    sea_score = None
    h = (sea or {}).get("hormuz")
    if h and h.get("pct7") is not None:
        # level: how far traffic is below the pre-crisis normal
        disruption = max(0.0, 1 - h["pct7"] / 100)
        level = 100 * min(1.0, max(0.0, (disruption - 0.15) / 0.7))
        # trend: change vs the previous week, scaled by normal traffic (a drop pushes up, a recovery pulls down)
        trend = 50.0
        if h.get("prev7") is not None and h.get("pre"):
            trend = 50 + max(-50.0, min(50.0, (h["prev7"] - h["avg7"]) / h["pre"] * 300))
        sea_score = 0.4 * level + 0.6 * trend
    incidents = [c for c in clusters if t - c["u"] <= 24 * 3600 and "maritime_incident" in c.get("flags", [])
                 and c["tier"] in ("red", "orange")]
    if incidents:
        sea_score = max(sea_score or 0, 60 if any(c["tier"] == "red" for c in incidents) else 35)
    if sea_score is not None:
        parts.append(("sea", 0.65, sea_score))
    if not parts:
        return None, {}
    tw = sum(w for _, w, _ in parts)
    val = sum(w * v for _, w, v in parts) / tw
    return round(val, 1), {k: round(v, 1) for k, _, v in parts}


def compute_index(clusters, av, sea, hist):
    t = now()
    n = news_component(clusters, t)
    s, parts = signals_component(av, sea, clusters, t)
    v = round(0.7 * n + 0.3 * s) if s is not None else round(n)
    v = int(max(0, min(100, v)))
    zi, zfa, zen = zone(v)
    hist = [h for h in hist if h[0] >= t - 30 * 86400]
    if hist and t - hist[-1][0] < 9 * 60:
        hist[-1] = [t, v, n, s]          # rounds run every 5 minutes; keep one point per ~10 minutes
    else:
        hist.append([t, v, n, s])
    past = [h for h in hist if h[0] <= t - 23.5 * 3600]
    delta = v - past[-1][1] if past else None
    week = [[h[0], h[1]] for h in hist if h[0] >= t - 7 * 86400]
    # thin the weekly series to <= 1 point per hour for the sparkline
    thin, last = [], 0
    for p in week:
        if p[0] - last >= 3500 or p is week[-1]:
            thin.append(p)
            last = p[0]
    return {"value": v, "zone": zi, "label_fa": zfa, "label_en": zen, "news": n, "signals": s,
            "parts": parts, "delta24": delta, "history": thin}, hist


def _ev_cluster(c):
    return {"type": "cluster", "id": c["id"], "fa": c.get("fa", {}).get("ti", ""), "en": c.get("en", {}).get("ti", ""),
            "tier": c["tier"], "t": c["u"]}


def compute_lights(clusters, av, sea, markets, t=None):
    t = t or now()
    recent = [c for c in clusters if t - c["u"] <= 72 * 3600]

    def by_flag(flags, min_sev=60, need_state_actor=False, exclude=()):
        on, watch = [], []
        for c in recent:
            if not (set(c.get("flags", [])) & flags) or c["sev"] < min_sev or not c.get("core", True):
                continue
            if set(c.get("flags", [])) & set(exclude):
                continue
            if "denial" in c.get("flags", []) or "past" in c.get("flags", []):
                continue
            if need_state_actor and not (set(c.get("ctry", [])) & STATE_ACTORS):
                continue
            (on if t - c["u"] <= 24 * 3600 else watch).append(c)
        return on, watch

    res = {}
    on, watch = by_flag({"kinetic"}, 72, need_state_actor=True, exclude=("maritime_incident",))
    res["strike"] = (on, watch, [])
    on, watch = by_flag({"maritime_incident", "hormuz_closure"}, 60)
    res["hormuz"] = (on, watch, [])
    on, watch = by_flag({"airspace"}, 66)
    data, watch_data = [], []
    for c, w in recent_warnings(av, t, 3 * 86400):
        line = {"type": "data", "fa": f"{c['fa']}: {w.get('src', '')} {w.get('ref', '')}".strip(),
                "en": f"{c['en']}: {w.get('src', '')} {w.get('ref', '')}".strip()}
        (data if t - (w.get("issued") or 0) <= 86400 else watch_data).append(line)
    res["airspace"] = (on, watch + ([{"_data": d} for d in watch_data] if not on and not data else []), data[:3])
    # an attack story is evidence for the strike light, not for a build-up, even when it names a carrier or a base
    on, watch = by_flag({"deploy"}, 62, exclude=("kinetic",))
    res["deploy"] = (on, watch, [])
    on, watch = by_flag({"evac"}, 66)
    res["evac"] = (on, watch, [])
    on, watch = by_flag({"ultimatum"}, 66)
    res["ultimatum"] = (on, watch, [])
    data = []
    b = (markets or {}).get("brent") or {}
    if b.get("chg24Pct") is not None and b["chg24Pct"] >= 5:
        data.append({"type": "data", "fa": f"نفت برنت {b['chg24Pct']}+٪ در ۲۴ ساعت", "en": f"Brent +{b['chg24Pct']}% in 24h"})
    on_c, watch_c = by_flag({"oil_spike"}, 50)
    res["oil"] = (on_c if data else [], watch_c + (on_c if not data else []), data)

    out = []
    for key, fa, en in LIGHTS:
        on, watch, data = res[key]
        state = "on" if (on or data) else ("watch" if watch else "off")
        ev = [{"type": "data", **d} if "type" not in d else d for d in data]
        ev += [_ev_cluster(c) for c in sorted(on, key=lambda c: -c["sev"])[:4]]
        if state != "on":
            ev += [c["_data"] if "_data" in c else _ev_cluster(c)
                   for c in sorted(watch, key=lambda c: -c.get("sev", 0))[:3]]
        out.append({"id": key, "fa": fa, "en": en, "state": state, "evidence": ev})
    return out


def hotspots(clusters, t, window):
    acc = {}
    rank = {"yellow": 0, "orange": 1, "red": 2}
    for c in clusters:
        if t - c["u"] > window:
            continue
        for g in c.get("geo", [])[:3]:
            if g not in PLACES:
                continue
            fa, en, lat, lon = PLACES[g][:4]
            h = acc.setdefault(g, {"id": g, "fa": fa, "en": en, "lat": lat, "lon": lon, "n": 0, "tier": "yellow",
                                   "ids": []})
            h["n"] += 1
            if rank[c["tier"]] > rank[h["tier"]]:
                h["tier"] = c["tier"]
            if len(h["ids"]) < 30:
                h["ids"].append(c["id"])
    return sorted(acc.values(), key=lambda h: (-rank[h["tier"]], -h["n"]))
