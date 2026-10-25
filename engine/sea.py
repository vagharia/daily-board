"""Shipping picture: daily transits through Hormuz and Bab el-Mandeb (IMF PortWatch, free but
about a week behind) and active navigational warnings for the region (NGA)."""
import re
import statistics
from datetime import date, datetime, timedelta, timezone

from . import config, http
from .util import log, now

PORTWATCH = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
             "Daily_Chokepoints_Data/FeatureServer/0/query")
CHOKEPOINTS = {"hormuz": ("%Hormuz%", "تنگه هرمز", "Strait of Hormuz"),
               "bab": ("%Mandeb%", "باب‌المندب", "Bab el-Mandeb")}


def _day(v):
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc).date()
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def portwatch(key):
    like, fa, en = CHOKEPOINTS[key]
    params = {"where": f"portname LIKE '{like}'", "outFields": "*", "orderByFields": "date DESC",
              "resultRecordCount": "800", "f": "json"}
    r = http.get(PORTWATCH, params=params, timeout=30, retries=1)
    feats = r.json().get("features") or []
    rows = []
    for f in feats:
        a = f.get("attributes") or {}
        d = _day(a.get("date"))
        if not d:
            continue
        tot = a.get("n_total")
        if tot is None:
            continue
        rows.append((d, int(tot), int(a.get("n_tanker") or 0)))
    rows.sort()
    if not rows:
        raise ValueError("no rows")
    crisis = date.fromisoformat(config.CRISIS_START)
    pre = [t for d, t, _ in rows if crisis - timedelta(days=365) <= d < crisis]
    pre_tank = [k for d, _, k in rows if crisis - timedelta(days=365) <= d < crisis]
    last_d = rows[-1][0]
    last7 = [t for d, t, _ in rows if d > last_d - timedelta(days=7)]
    last7k = [k for d, _, k in rows if d > last_d - timedelta(days=7)]
    last30 = [t for d, t, _ in rows if d > last_d - timedelta(days=30)]
    prev7 = [t for d, t, _ in rows if last_d - timedelta(days=14) < d <= last_d - timedelta(days=7)]
    out = {
        "fa": fa, "en": en, "last_date": last_d.isoformat(), "last": rows[-1][1],
        "avg7": round(statistics.mean(last7), 1) if last7 else None,
        "prev7": round(statistics.mean(prev7), 1) if prev7 else None,
        "avg30": round(statistics.mean(last30), 1) if last30 else None,
        "tank7": round(statistics.mean(last7k), 1) if last7k else None,
        "pre": round(statistics.mean(pre), 1) if pre else None,
        "pre_tank": round(statistics.mean(pre_tank), 1) if pre_tank else None,
        "series": [[d.isoformat(), t, k] for d, t, k in rows if d > last_d - timedelta(days=180)],
    }
    if out["pre"] and out["avg7"] is not None:
        out["pct7"] = round(100 * out["avg7"] / out["pre"])
    return out


WARN_RX = re.compile(r"PERSIAN GULF|STRAIT OF HORMUZ|GULF OF OMAN|ARABIAN SEA|RED SEA|GULF OF ADEN|BAB EL MANDEB"
                     r"|BAB AL MANDAB|IRAN|OMAN|UNITED ARAB EMIRATES|QATAR|BAHRAIN|KUWAIT|SAUDI ARABIA|YEMEN", re.I)


def nga_warnings():
    r = http.get("https://msi.nga.mil/api/publications/broadcast-warn",
                 params={"output": "json", "status": "active"}, timeout=30, retries=1,
                 headers={"Accept": "application/json"})
    data = r.json()
    rows = data.get("broadcast-warn") if isinstance(data, dict) else data
    out = []
    for w in rows or []:
        text = (w.get("text") or "").strip()
        area = " ".join(str(w.get(k) or "") for k in ("navArea", "subregion", "area"))
        if not WARN_RX.search(text[:400] + " " + area):
            continue
        out.append({
            "id": f"{w.get('navArea', '')} {w.get('msgNumber', '')}/{w.get('msgYear', '')}".strip(),
            "date": str(w.get("issueDate") or "")[:20],
            "text": re.sub(r"\s+", " ", text)[:600],
        })
    return out[:25]


def run(state):
    """state caches PortWatch for 6h and NGA for 2h (both change slowly)."""
    t = now()
    out = {"updated": t, "status": "ok", "errors": []}
    cache = state.setdefault("cache", {})
    for key in CHOKEPOINTS:
        c = cache.get(key)
        if c and t - c.get("fetched", 0) < 6 * 3600:
            out[key] = c["data"]
            continue
        try:
            d = portwatch(key)
            cache[key] = {"fetched": t, "data": d}
            out[key] = d
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"portwatch {key}: {str(e)[:80]}")
            if c:
                out[key] = c["data"]
    c = cache.get("nga")
    if c and t - c.get("fetched", 0) < 2 * 3600:
        out["warnings"] = c["data"]
    else:
        try:
            w = nga_warnings()
            cache["nga"] = {"fetched": t, "data": w}
            out["warnings"] = w
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"nga: {str(e)[:80]}")
            out["warnings"] = c["data"] if c else []
    if out["errors"]:
        out["status"] = "partial" if ("hormuz" in out) else "fail"
    log(f"sea: hormuz avg7={out.get('hormuz', {}).get('avg7')} warnings={len(out.get('warnings', []))} errors={out['errors']}")
    return out
