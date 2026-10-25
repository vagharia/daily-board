"""Air picture from open ADS-B networks: military aircraft in the region (adsb.fi + adsb.lol, with
airplanes.live as a fallback) and civil traffic levels over Iran, Iraq, Israel and the Persian Gulf
(OpenSky Network, falling back to point queries) compared with the same time of day on recent days."""
import statistics
import time

from . import http
from .util import log, now

MIL_URLS = [("adsb.fi", "https://opendata.adsb.fi/api/v2/mil"), ("adsb.lol", "https://api.adsb.lol/v2/mil"),
            ("airplanes.live", "https://api.airplanes.live/v2/mil")]
OPENSKY = "https://opensky-network.org/api/states/all?lamin=12&lomin=32&lamax=42&lomax=64"
POINT_URL = "https://api.adsb.lol/v2/point/{lat}/{lon}/250"
REGION = (10.0, 42.5, 24.0, 66.0)   # lat_min, lat_max, lon_min, lon_max

CATS = {
    "tanker": {"K35R", "K35E", "K35T", "KC46", "KC10", "KC30", "A332", "A310", "K46", "KC2", "KC39", "C135"},
    "isr": {"E3TF", "E3CF", "E3", "E737", "E7", "R135", "P8", "Q4", "Q9", "U2", "E6", "E8", "EP3", "RC12", "GLEX",
            "E2", "MQ9", "RQ4", "GL5T", "CL60", "P3"},
    "bomber": {"B52", "B1", "B2", "B21"},
    "transport": {"C17", "C5", "C5M", "C130", "C30J", "A400", "C2", "KC390", "IL76", "Y20", "C40", "C32", "C37"},
}
CAT_FA = {"tanker": "سوخت‌رسان", "isr": "شناسایی و هشدار", "bomber": "بمب‌افکن", "transport": "ترابری", "other": "سایر"}
CAT_EN = {"tanker": "Tankers", "isr": "ISR / AWACS", "bomber": "Bombers", "transport": "Transport", "other": "Other"}

# rough polygons (lon, lat)
POLY = {
    "iran": [(44.0, 39.8), (48.0, 38.4), (49.0, 37.6), (53.9, 37.3), (56.9, 38.2), (61.1, 36.6), (60.6, 33.5),
             (61.9, 30.9), (63.3, 26.6), (61.6, 25.2), (57.3, 25.6), (56.3, 27.0), (54.0, 26.4), (51.3, 27.9),
             (48.6, 30.0), (47.5, 31.0), (46.2, 32.9), (45.4, 33.9), (46.0, 35.1), (44.8, 37.3)],
    "iraq": [(38.8, 33.4), (41.0, 34.4), (42.3, 37.1), (44.8, 37.2), (46.0, 35.1), (45.4, 33.9), (46.2, 32.9),
             (47.5, 31.0), (48.6, 30.0), (47.9, 29.9), (47.3, 30.0), (46.5, 29.1), (44.7, 29.2), (42.0, 31.1),
             (39.0, 32.0)],
    "israel": [(34.2, 31.2), (34.25, 31.35), (34.9, 29.5), (35.0, 29.6), (35.5, 31.4), (35.9, 33.3), (35.1, 33.1),
               (34.9, 32.8), (34.5, 31.6)],
    "gulf": [(48.5, 30.0), (50.5, 29.0), (51.3, 27.9), (54.0, 26.4), (56.3, 27.0), (57.3, 25.6), (57.0, 23.5),
             (55.0, 22.5), (51.5, 23.5), (50.0, 24.5), (48.0, 27.5), (47.6, 29.0)],
}
REGION_LABEL = {"iran": ("ایران", "Iran"), "iraq": ("عراق", "Iraq"), "israel": ("اسرائیل", "Israel"),
                "gulf": ("حوزه خلیج فارس", "Persian Gulf")}
POINTS = {
    "iran": [(35.69, 51.39), (32.65, 51.67), (29.59, 52.58), (36.30, 59.60), (38.08, 46.29), (27.18, 56.27)],
    "iraq": [(33.31, 44.36), (30.5, 47.8)],
    "israel": [(31.9, 35.0)],
    "gulf": [(25.25, 55.36), (26.0, 50.6)],
}


def _inside(lon, lat, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def _cat(t):
    t = (t or "").upper()
    for k, s in CATS.items():
        if t in s:
            return k
    return "other"


def _json(url, timeout=15):
    r = http.get(url, timeout=timeout, retries=0, headers={"Accept": "application/json"})
    return r.json()


def _military(snap):
    """Union of the military feeds that answer (they share contributors but not all of them)."""
    got, used = {}, []
    for name, url in MIL_URLS:
        if name == "airplanes.live" and got:
            break                                  # only needed when the other two failed
        try:
            for a in _json(url).get("ac") or []:
                if a.get("hex"):
                    got.setdefault(a["hex"], a)
            used.append(name)
        except Exception as e:  # noqa: BLE001
            snap["errors"].append(f"mil {name}: {str(e)[:60]}")
    return list(got.values()), used


def _civil_opensky(mil_hex):
    d = _json(OPENSKY, timeout=25)
    counts = {reg: 0 for reg in POLY}
    for st in d.get("states") or []:
        try:
            hexid, lon, lat, ground = st[0], st[5], st[6], st[8]
        except (IndexError, TypeError):
            continue
        if lon is None or lat is None or ground or hexid in mil_hex:
            continue
        for reg, poly in POLY.items():
            if _inside(lon, lat, poly):
                counts[reg] += 1
                break
    return counts


def _civil_points(snap, mil_hex):
    counts, fails = {}, 0
    for reg, pts in POINTS.items():
        seen, ok = {}, False
        for lat, lon in pts:
            if fails >= 2:
                break
            time.sleep(1.05)
            try:
                for a in _json(POINT_URL.format(lat=lat, lon=lon)).get("ac") or []:
                    if a.get("lat") is None or a.get("alt_baro") == "ground" or a.get("hex") in mil_hex:
                        continue
                    if (a.get("dbFlags") or 0) & 1:
                        continue
                    if _inside(a["lon"], a["lat"], POLY[reg]):
                        seen[a.get("hex")] = 1
                ok, fails = True, 0
            except Exception as e:  # noqa: BLE001
                fails += 1
                snap["errors"].append(f"point {reg}: {str(e)[:60]}")
        if ok:
            counts[reg] = len(seen)
    return counts


def snapshot():
    snap = {"ts": now(), "mil": None, "civil": {}, "csrc": None, "list": [], "errors": [], "providers": []}
    ac, used = _military(snap)
    snap["providers"] = used
    mil_hex = set()
    if used:
        lat0, lat1, lon0, lon1 = REGION
        sel = [a for a in ac if a.get("lat") is not None and lat0 <= a["lat"] <= lat1 and lon0 <= a["lon"] <= lon1]
        cats = {k: 0 for k in list(CATS) + ["other"]}
        lst = []
        for a in sel:
            c = _cat(a.get("t"))
            cats[c] += 1
            lst.append({"hex": a.get("hex"), "cs": (a.get("flight") or "").strip(), "type": a.get("t") or "",
                        "cat": c, "lat": round(a["lat"], 3), "lon": round(a["lon"], 3),
                        "alt": a.get("alt_baro") if isinstance(a.get("alt_baro"), int) else 0})
        mil_hex = {a.get("hex") for a in ac}
        snap["mil"] = {"total": len(sel), "cats": cats}
        snap["list"] = sorted(lst, key=lambda x: ["tanker", "bomber", "isr", "transport", "other"].index(x["cat"]))[:80]
    try:
        snap["civil"] = _civil_opensky(mil_hex)
        snap["csrc"] = "opensky"
    except Exception as e:  # noqa: BLE001
        snap["errors"].append(f"opensky: {str(e)[:60]}")
        snap["civil"] = _civil_points(snap, mil_hex)
        snap["csrc"] = "points" if snap["civil"] else None
    return snap


def _baseline(hist, getter, ts, window_h=1.0, days=7, exclude_h=3):
    """Mean of the same time of day over the past days (needs >=3 samples), else overall mean."""
    cut_old = ts - days * 86400
    cut_new = ts - exclude_h * 3600
    tod = (ts % 86400) / 3600
    same, allv = [], []
    for h in hist:
        if not (cut_old <= h["ts"] <= cut_new):
            continue
        v = getter(h)
        if v is None:
            continue
        allv.append(v)
        d = abs(((h["ts"] % 86400) / 3600) - tod)
        if min(d, 24 - d) <= window_h:
            same.append(v)
    if len(same) >= 3:
        return statistics.mean(same), len(same)
    if len(allv) >= 6:
        return statistics.mean(allv), len(allv)
    return None, len(allv)


def summarize(snap, hist):
    ts = snap["ts"]
    ok_parts = bool(snap["mil"]) + bool(snap["civil"])
    out = {"updated": ts, "status": "ok" if ok_parts == 2 else ("partial" if ok_parts else "fail"),
           "mil": None, "civil": [], "list": snap["list"], "surge": 0.0, "civil_drop": 0.0,
           "providers": snap.get("providers", []) + ([snap["csrc"]] if snap.get("csrc") else []),
           "errors": snap["errors"][:6]}
    if snap["mil"]:
        b, n = _baseline(hist, lambda h: (h.get("mil") or {}).get("total"), ts, window_h=24, days=7)
        bt, _ = _baseline(hist, lambda h: ((h.get("mil") or {}).get("cats") or {}).get("tanker"), ts, window_h=24, days=7)
        tot = snap["mil"]["total"]
        tank = snap["mil"]["cats"].get("tanker", 0)
        surge = 0.0
        if b and b >= 3:
            surge = max(surge, min(1.0, max(0.0, (tot / b - 1.0) / 1.5)))
        if bt is not None and bt >= 1:
            surge = max(surge, min(1.0, max(0.0, (tank / max(bt, 1.0) - 1.0) / 2.0)))
        if snap["mil"]["cats"].get("bomber"):
            surge = max(surge, 0.6)
        out["mil"] = {"total": tot, "cats": snap["mil"]["cats"], "baseline": round(b, 1) if b else None,
                      "tank_base": round(bt, 1) if bt is not None else None, "samples": n}
        out["surge"] = round(surge, 2)
    drops = []
    for reg in ("iran", "israel", "iraq", "gulf"):
        if reg not in snap["civil"]:
            continue
        cnt = snap["civil"][reg]
        b, n = _baseline(hist, lambda h, r=reg: (h.get("civil") or {}).get(r)
                         if h.get("csrc", "points") == snap.get("csrc") else None, ts)
        pct = round(100 * cnt / b) if b else None
        state = "na"
        if b is not None and b >= 12:
            state = "low" if pct < 35 else ("reduced" if pct < 65 else "normal")
            drop = max(0.0, 1 - cnt / b)
            drops.append(min(1.0, max(0.0, (drop - 0.2) / 0.6)) * (0.6 if reg == "gulf" else 1.0))
        out["civil"].append({"id": reg, "fa": REGION_LABEL[reg][0], "en": REGION_LABEL[reg][1], "count": cnt,
                             "baseline": round(b, 1) if b else None, "pct": pct, "state": state, "samples": n})
    out["civil_drop"] = round(max(drops), 2) if drops else 0.0
    return out


def run(hist):
    try:
        snap = snapshot()
    except Exception as e:  # noqa: BLE001
        log("air snapshot failed:", e)
        return None, hist
    hist = [h for h in hist if h["ts"] >= snap["ts"] - 14 * 86400]
    summary = summarize(snap, hist)
    hist.append({"ts": snap["ts"], "mil": snap["mil"], "civil": snap["civil"], "csrc": snap.get("csrc")})
    log(f"air: mil={summary['mil'] and summary['mil']['total']} via {snap.get('providers')} civil={snap['civil']} "
        f"({snap.get('csrc')}) errors={snap['errors'][:3]}")
    return summary, hist
