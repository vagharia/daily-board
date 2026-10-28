"""Escalation index (0-100), warning lights and map hotspots.

The index measures one thing above all: how close Iran, America and Israel are to war, or how deep in it they are.
Four parts, each 0-100, over the last 24 hours (newer stories weigh more, 6h half-life; each story counts once):

  acts (40%)       military action that happened: strikes, attacks at sea, Hormuz closed. A sum that saturates, so
                   two strikes count for more than one but thirty don't run off the scale.
  threats (20%)    what points towards war: ultimatums, threats, carriers and bombers sent, embassies evacuated,
                   talks breaking down.
  spread (15%)     how many fronts are hot at once (Iran, Israel, the Persian Gulf and Hormuz, Lebanon, Iraq, Yemen
                   and Saudi Arabia, Syria).
  signals (25%)    what can be measured: Hormuz traffic and incidents, airspace risk and fresh official warnings,
                   a jump in Brent.

Who is involved sets the weight: Iran against America or Israel counts in full, Iran and the Persian Gulf states
at 70%, the other fronts (the Houthis and Saudi Arabia, Hezbollah, Iraq's militias) at 35%. Those fronts matter
because they are fought for Iran, but on their own they can take the index to "high tension", never to "critical":
above 75 only Iran, America and Israel count.

Not counted: one Telegram channel's unconfirmed report, denials, analysis and opinion, past events, Putin on trade.
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


W_ACTS, W_THREATS, W_SPREAD, W_SIGNALS = 0.35, 0.25, 0.15, 0.25
HALF = 6 * 3600
ACT_FLAGS = {"kinetic", "maritime_incident", "hormuz_closure", "nuclear_red"}
THREAT_FLAGS = {"ultimatum", "threat", "kinetic_threat", "deploy", "evac", "talks_fail", "retaliation", "alert"}
SKIP_FLAGS = {"denial", "past", "opinion", "analysis", "powers_soft", "sport"}
IR_LAND = {"tehran", "isfahan", "natanz", "fordow", "bushehr", "bandar_abbas", "kharg", "tabriz", "shiraz", "chabahar"}
IR_SEA = {"hormuz", "persian_gulf", "gulf_oman"}
PROXY = {"yemen", "lebanon", "iraq", "syria"}
PROXY_GEO = {"baghdad", "erbil", "ain_asad", "sanaa", "hodeidah", "red_sea", "bab", "lebanon", "riyadh", "east_sa"}
FRONTS = {"ir": "iran", "il": "israel", "gulf": "gulf", "lebanon": "lebanon", "iraq": "iraq", "yemen": "yemen",
          "syria": "syria"}
CRITICAL = 75
K_ACTS, K_THREATS, K_SPREAD = 4.0, 3.0, 3.0
HIGH = 50


def theatre(c):
    """How much a story is about the Iran-America-Israel war: 1 (Iran against America or Israel), 0.7 (Iran alone, Iran
    and the Persian Gulf states, or America and Israel in the region with no other front named), 0.5 (Iran's name
    next to another front: "US strikes Iran-backed militia in Iraq"), 0.35 (another front)."""
    ctry, geo = set(c.get("ctry", [])), set(c.get("geo", []))
    iran = "ir" in ctry or bool(geo & (IR_LAND | IR_SEA))
    us_il = bool(ctry & {"us", "il"})
    proxy = bool(ctry & PROXY or geo & PROXY_GEO) and not geo & IR_LAND
    if iran:
        if proxy:
            return 0.5
        return 1.0 if us_il else 0.7
    if us_il and not proxy:
        return 0.7
    return 0.35


def _counted(c, t):
    age = t - c["u"]
    if age > 24 * 3600 or age < -3600 or c.get("unconf") or not c.get("core", True):
        return None
    fl = set(c.get("flags", []))
    if fl & SKIP_FLAGS:
        return None
    return fl, 0.5 ** (max(0, age) / HALF)


def _saturate(x, k):
    return 100.0 * (1 - math.exp(-x / k))


def pillars(clusters, av, sea, markets, t, direct_only=False):
    """The four parts of the index; direct_only leaves out everything that isn't Iran against America or Israel."""
    acts = threats = 0.0
    fronts = {}
    for c in clusters:
        got = _counted(c, t)
        if not got:
            continue
        fl, decay = got
        w = theatre(c)
        if direct_only and w < 1:
            continue
        s = c["sev"]
        # serious events count far more than borderline ones: ((sev - floor) / 30)^2
        if fl & ACT_FLAGS and s >= 60:
            acts += ((s - 55) / 30) ** 2 * decay * w * w * (0.5 if "secondary" in fl else 1.0)
        elif fl & THREAT_FLAGS and s >= 50:
            threats += ((s - 45) / 30) ** 2 * decay * w * w
        if s >= 60 and fl & (ACT_FLAGS | THREAT_FLAGS):
            for k in set(c.get("ctry", [])) & set(FRONTS):
                if not direct_only or k in ("ir", "il"):
                    fronts[FRONTS[k]] = max(fronts.get(FRONTS[k], 0), decay * (1.0 if s >= 70 else 0.5) * (1.0 if w >= 0.7 else 0.5))
    raw = {"acts": round(acts, 2), "threats": round(threats, 2), "spread": round(sum(fronts.values()), 2)}
    a = _saturate(acts, K_ACTS)
    th = _saturate(threats, K_THREATS)
    sp = _saturate(sum(fronts.values()), K_SPREAD)
    sig, parts = signals_component(av, sea, clusters, t)
    b = (markets or {}).get("brent") or {}
    oil = b.get("chg24Pct")
    if sig is not None and oil is not None and oil > 2:
        sig = min(100.0, sig + min(15.0, (oil - 2) * 3))           # a jump in Brent
    if direct_only:
        sig = None
    return {"acts": round(a, 1), "threats": round(th, 1), "spread": round(sp, 1),
            "signals": None if sig is None else round(sig, 1), "raw": raw}, parts


def combine(p):
    ws = [(W_ACTS, p["acts"]), (W_THREATS, p["threats"]), (W_SPREAD, p["spread"])]
    if p.get("signals") is not None:
        ws.append((W_SIGNALS, p["signals"]))
    return sum(w * v for w, v in ws) / sum(w for w, _ in ws)


def direct_strikes(clusters, t, hours=12):
    """Confirmed military action between Iran and America or Israel (serious, reported by at least two outlets) in
    the last `hours` hours."""
    out = []
    for c in clusters:
        got = _counted(c, t)
        if not got or t - c["u"] > hours * 3600:
            continue
        fl, _ = got
        if fl & ACT_FLAGS and "secondary" not in fl and c["sev"] >= 80 and c.get("ns", 1) >= 2 \
                and not c.get("single") and theatre(c) >= 1:
            out.append(c)
    return out


def proxy_attacks(clusters, t, hours=12):
    """A serious attack on another front of the region (the Houthis on Saudi Arabia, Hezbollah, Iraq's militias),
    confirmed by two outlets, in the last `hours` hours."""
    for c in clusters:
        got = _counted(c, t)
        if got and t - c["u"] <= hours * 3600 and got[0] & ACT_FLAGS and "secondary" not in got[0] \
                and c["sev"] >= 80 and c.get("ns", 1) >= 2 and not c.get("single"):
            return True
    return False


def index_value(clusters, av, sea, markets, t):
    p, parts = pillars(clusters, av, sea, markets, t)
    v = combine(p)
    if v >= CRITICAL:
        # the other fronts can make it "high tension", only Iran, America and Israel "critical"
        d, _ = pillars(clusters, av, sea, markets, t, direct_only=True)
        direct = (W_ACTS * d["acts"] + W_THREATS * d["threats"] + W_SPREAD * d["spread"]
                  + W_SIGNALS * (p["signals"] or 0)) / (W_ACTS + W_THREATS + W_SPREAD + W_SIGNALS)
        v = max(CRITICAL - 1, min(v, direct))
    # anything that is war between Iran and America or Israel lifts the index however quiet the rest is: one confirmed
    # strike to "high tension", two separate ones (or one very large) to "critical"
    ds = direct_strikes(clusters, t)
    if len(ds) >= 2 or any(c["sev"] >= 90 and c.get("ns", 1) >= 3 for c in ds):
        v = max(v, CRITICAL + min(15, 4 * (len(ds) - 1)))
    elif ds:
        v = max(v, 65)
    elif proxy_attacks(clusters, t):
        v = max(v, HIGH)                       # a serious attack on another front: "high tension" at least
    p["direct"] = len(ds)
    return int(max(0, min(100, round(v)))), p, parts


def compute_index(clusters, av, sea, hist, markets=None):
    t = now()
    v, p, parts = index_value(clusters, av, sea, markets, t)
    n = news_component(clusters, t)          # the old measure, kept alongside for comparison
    zi, zfa, zen = zone(v)
    # points of the earlier formula (no version mark) aren't comparable: the history restarts with this one
    hist = [h for h in hist if h[0] >= t - 30 * 86400 and len(h) > 4 and h[4] == 2]
    if hist and int(hist[-1][0] // 600) == int(t // 600):
        hist[-1] = [t, v, n, p["signals"], 2]   # rounds run every 5 minutes; keep one point per 10-minute slot
    else:
        hist.append([t, v, n, p["signals"], 2])
    past = [h for h in hist if h[0] <= t - 23.5 * 3600]
    delta = v - past[-1][1] if past else None
    week = [[h[0], h[1]] for h in hist if h[0] >= t - 7 * 86400]
    # thin the weekly series to <= 1 point per hour for the sparkline
    thin, last = [], 0
    for q in week:
        if q[0] - last >= 3500 or q is week[-1]:
            thin.append(q)
            last = q[0]
    return {"value": v, "zone": zi, "label_fa": zfa, "label_en": zen, "pillars": p, "news": n,
            "signals": p["signals"], "parts": parts, "delta24": delta, "history": thin}, hist


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
            if c.get("unconf"):
                continue                       # one Telegram channel's report doesn't light a lamp
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
