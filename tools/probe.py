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

OUT = {"t": int(time.time()), "notam": {}, "prices": {}, "tg": {}}


def timed(fn):
    t0 = time.time()
    try:
        v = fn()
        return {"ok": True, "ms": int((time.time() - t0) * 1000), "v": v}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ms": int((time.time() - t0) * 1000), "err": f"{type(e).__name__}: {str(e)[:240]}"}


def strip(s, n=300):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:n]


# ------------------------------------------------------------------ NOTAMs / airspace warnings
def faa_search(fir):
    data = {"searchType": "0", "designatorsForLocation": fir, "designatorForAccountable": "", "latDegrees": "",
            "latMinutes": "0", "latSeconds": "0", "longDegrees": "", "longMinutes": "0", "longSeconds": "0",
            "radius": "10", "sortColumns": "5 false", "sortDirection": "true", "designatorForNotamNumberSearch": "",
            "notamNumber": "", "radiusSearchOnDesignator": "false", "radiusSearchDesignator": "",
            "latitudeDirection": "N", "longitudeDirection": "W", "freeFormText": "", "flightPathText": "",
            "flightPathDivertAirfields": "", "flightPathBuffer": "4", "flightPathIncludeNavaids": "true",
            "flightPathIncludeArtcc": "false", "flightPathIncludeTfr": "true", "flightPathIncludeRegulatory": "false",
            "flightPathResultsType": "All NOTAMs", "archiveDate": "", "archiveDesignator": "", "offset": "0",
            "notamsOnly": "false", "filters": "", "minRunwayLength": "", "minRunwayWidth": "", "runwaySurfaceTypes": "",
            "predefinedAbbreviationsFilters": "", "predefinedFilters": "", "minDate": "", "maxDate": ""}
    r = http.post("https://notams.aim.faa.gov/notamSearch/search", data=data, timeout=30, retries=0,
                  headers={"Accept": "application/json, text/javascript, */*; q=0.01",
                           "X-Requested-With": "XMLHttpRequest",
                           "Referer": "https://notams.aim.faa.gov/notamSearch/nsapp.html"})
    try:
        d = r.json()
    except Exception:  # noqa: BLE001
        return {"code": r.status_code, "head": r.text[:300]}
    lst = d.get("notamList") or []
    return {"code": r.status_code, "keys": list(d.keys())[:12], "total": d.get("totalNotamCount"), "n": len(lst),
            "sample": [{k: (str(x.get(k))[:260]) for k in ("facilityDesignator", "notamNumber", "issueDate",
                                                           "startDate", "endDate", "icaoMessage", "traditionalMessage")}
                       for x in lst[:3]]}


for fir in ("OIIX", "ORBB", "OBBB", "OMAE", "LLLL", "OEJD"):
    OUT["notam"][f"faa_{fir}"] = timed(lambda fir=fir: faa_search(fir))
    time.sleep(1)


def dins(ids):
    url = ("https://www.notams.faa.gov/dinsQueryWeb/queryRetrievalMapAction.do?reportType=Raw&retrieveLocId="
           + "%20".join(ids) + "&actionType=notamRetrievalByICAOs&submit=View+NOTAMs")
    r = http.get(url, timeout=30, retries=0)
    pres = re.findall(r"<PRE>(.*?)</PRE>", r.text, re.S | re.I)
    return {"code": r.status_code, "len": len(r.text), "n": len(pres), "sample": [strip(p, 260) for p in pres[:3]],
            "head": strip(r.text, 200) if not pres else None}


OUT["notam"]["dins"] = timed(lambda: dins(["OIIX", "ORBB", "OBBB"]))


def page(url, rx=None):
    r = http.get(url, timeout=30, retries=0)
    txt = r.text
    out = {"code": r.status_code, "len": len(txt), "title": strip((re.search(r"<title>(.*?)</title>", txt, re.S) or
                                                                  [None, ""])[1], 120)}
    if rx:
        out["hits"] = [strip(m, 200) for m in re.findall(rx, txt, re.S | re.I)[:12]]
    return out


OUT["notam"]["easa_czib"] = timed(lambda: page("https://www.easa.europa.eu/en/domains/air-operations/czibs",
                                               r"(CZIB[^<]{0,160})"))
OUT["notam"]["faa_kicz"] = timed(lambda: page("https://www.faa.gov/air_traffic/publications/us_restrictions",
                                              r"(KICZ[^<]{0,160}|Iran[^<]{0,120}|Iraq[^<]{0,120})"))


def feed(url):
    r = http.get(url, timeout=25, retries=0)
    es = parse_feed(r.content)
    return {"code": r.status_code, "n": len(es), "items": [(e.get("date"), (e.get("title") or "")[:110]) for e in es[:6]]}


OUT["notam"]["opsgroup_feed"] = timed(lambda: feed("https://ops.group/blog/feed/"))
OUT["notam"]["safeairspace_feed"] = timed(lambda: feed("https://safeairspace.net/feed/"))
OUT["notam"]["safeairspace"] = timed(lambda: page("https://safeairspace.net/", r"(Iran[^<]{0,160}|Iraq[^<]{0,120})"))

# ------------------------------------------------------------------ prices (reference closes: gold 3996, Brent 117.4)
P = OUT["prices"]


def stooq(sym):
    r = http.get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&h&e=csv", timeout=20, retries=0)
    return r.text.strip()[:200]


for s in ("xauusd", "gc.f", "cb.f", "sc.f", "brent"):
    P["stooq_" + s] = timed(lambda s=s: stooq(s))


def yahoo(sym):
    r = http.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params={"range": "5d", "interval": "1d"},
                 timeout=20, retries=0, headers={"Accept": "application/json"})
    m = r.json()["chart"]["result"][0]["meta"]
    return {k: m.get(k) for k in ("symbol", "regularMarketPrice", "chartPreviousClose", "regularMarketTime",
                                  "exchangeName", "longName", "shortName")}


for s in ("BZ=F", "GC=F", "BZZ26.NYM", "BZF27.NYM", "XAUUSD=X", "GCZ26.CMX"):
    P["yahoo_" + s] = timed(lambda s=s: yahoo(s))
    time.sleep(0.5)

P["goldprice_org"] = timed(lambda: http.get("https://data-asg.goldprice.org/dbXRates/USD", timeout=20, retries=0,
                                            headers={"Accept": "application/json"}).json())


def tv(screener, tickers):
    body = {"symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": ["close", "change", "description", "update_mode"]}
    r = http.post(f"https://scanner.tradingview.com/{screener}/scan", json_body=body, timeout=20, retries=0,
                  headers={"Accept": "application/json", "Origin": "https://www.tradingview.com",
                           "Referer": "https://www.tradingview.com/"})
    return r.json()


P["tv_cfd"] = timed(lambda: tv("cfd", ["TVC:UKOIL", "TVC:GOLD", "OANDA:XAUUSD", "FX_IDC:XAUUSD", "OANDA:BCOUSD"]))
P["tv_futures"] = timed(lambda: tv("futures", ["ICEEUR:BRN1!", "ICEEUR:BRNZ2026", "NYMEX:BZ1!", "COMEX:GC1!"]))
P["tv_forex"] = timed(lambda: tv("forex", ["OANDA:XAUUSD", "FX_IDC:XAUUSD"]))

# ------------------------------------------------------------------ requested Telegram channels


def tg(handle):
    r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=0)
    t = r.text
    n = t.count('class="tgme_widget_message_text')
    dates = re.findall(r'<time datetime="([^"]+)"', t)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    desc = re.search(r'<meta property="og:description" content="([^"]*)"', t)
    texts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', t, re.S)
    return {"code": r.status_code, "posts": n, "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
            "title": title.group(1)[:80] if title else None, "desc": desc.group(1)[:200] if desc else None,
            "samples": [strip(x, 220) for x in texts[-8:]]}


for h in ("fundamental_View", "SBoxxx", "VahidOnline", "tsepress"):
    OUT["tg"][h] = timed(lambda h=h: tg(h))

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("probe done", int(time.time()) - OUT["t"], "s")
