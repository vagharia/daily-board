"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402
from engine.feeds import parse_feed  # noqa: E402

OUT = {"t": int(time.time()), "notam": {}, "prices": {}}


def timed(fn):
    t0 = time.time()
    try:
        v = fn()
        return {"ok": True, "ms": int((time.time() - t0) * 1000), "v": v}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ms": int((time.time() - t0) * 1000), "err": f"{type(e).__name__}: {str(e)[:240]}"}


def strip(s, n=300):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:n]


N = OUT["notam"]


def easa_json():
    r = http.get("https://www.easa.europa.eu/en/domains/air-operations/czibs/export-json?page&_format=json",
                 timeout=30, retries=0, headers={"Accept": "application/json"})
    d = r.json()
    rows = d if isinstance(d, list) else d.get("data") or d.get("rows") or d
    return {"type": type(d).__name__, "n": len(rows) if hasattr(rows, "__len__") else None,
            "first": rows[:4] if isinstance(rows, list) else str(rows)[:1500]}


N["easa_json"] = timed(easa_json)


def easa_feed():
    r = http.get("https://www.easa.europa.eu/en/domains/air-operations/czibs/feed.xml", timeout=30, retries=0)
    es = parse_feed(r.content)
    return {"n": len(es), "items": [{k: (e.get(k) or "")[:300] for k in ("title", "link", "date", "summary")}
                                    for e in es[:8]], "head": r.text[:300] if not es else None}


N["easa_feed"] = timed(easa_feed)


def kicz():
    r = http.get("https://www.faa.gov/air_traffic/publications/us_restrictions", timeout=30, retries=0)
    t = r.text
    links = re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', t, re.S | re.I)
    out = [(u[-90:], strip(x, 220)) for u, x in links if re.search(r"KICZ|SFAR|NOTAM", x + u, re.I)]
    i = t.find("Iran")
    return {"n": len(out), "links": out[:40], "around_iran": strip(t[max(0, i - 1500):i + 1500], 1800)}


N["faa_kicz"] = timed(kicz)


def faa_session(fir):
    import requests
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/130.0.0.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"})
    a = s.get("https://notams.aim.faa.gov/notamSearch/nsapp.html", timeout=20)
    r = s.post("https://notams.aim.faa.gov/notamSearch/search",
               data={"searchType": "0", "designatorsForLocation": fir, "offset": "0", "notamsOnly": "false",
                     "sortColumns": "5 false", "sortDirection": "true", "radius": "10"},
               headers={"Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest",
                        "Origin": "https://notams.aim.faa.gov",
                        "Referer": "https://notams.aim.faa.gov/notamSearch/nsapp.html"}, timeout=30)
    return {"page": a.status_code, "code": r.status_code, "head": r.text[:400]}


N["faa_session"] = timed(lambda: faa_session("OIIX"))


def sa():
    r = http.get("https://safeairspace.net/", timeout=30, retries=0)
    t = r.text
    items = re.findall(r'data-feed-item-country="([^"]+)"[^>]*data-feed-item-warn-level="(\d)"(.*?)</a>', t, re.S)
    if not items:
        items = re.findall(r'data-feed-item-warn-level="(\d)"(.{0,600})', t, re.S)
    return {"n": len(items), "items": [strip(" ".join(x) if isinstance(x, tuple) else x, 300) for x in items[:15]]}


N["safeairspace"] = timed(sa)

P = OUT["prices"]


def tv(screener, tickers):
    body = {"symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": ["close", "change", "description", "update_mode", "close|1D", "prev_close_price"]}
    r = http.post(f"https://scanner.tradingview.com/{screener}/scan", json_body=body, timeout=20, retries=0,
                  headers={"Accept": "application/json", "Origin": "https://www.tradingview.com",
                           "Referer": "https://www.tradingview.com/"})
    return r.json()


BRENT = ["TVC:UKOIL", "FX:UKOIL", "OANDA:BCOUSD", "PEPPERSTONE:XBRUSD", "FXOPEN:XBRUSD", "CAPITALCOM:OIL_BRENT",
         "BLACKBULL:BRENT", "EIGHTCAP:XBRUSD", "TVC:USOIL", "ICEEUR:BRN1!", "ICEEUR:BRN2!", "NYMEX:BZ1!"]
for scr in ("cfd", "global", "futures", "america"):
    P["tv_" + scr] = timed(lambda scr=scr: tv(scr, BRENT + ["TVC:GOLD", "OANDA:XAUUSD"]))

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("probe done", int(time.time()) - OUT["t"], "s")
