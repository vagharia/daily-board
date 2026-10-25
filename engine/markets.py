"""Brent crude and gold prices (Yahoo Finance chart API, Stooq as fallback)."""
import csv
import io

from . import http
from .util import log, now

SYMBOLS = {
    "brent": {"yahoo": "BZ=F", "stooq": "cb.f", "fa": "نفت برنت", "en": "Brent", "unit": "$"},
    "gold": {"yahoo": "GC=F", "stooq": "xauusd", "fa": "اونس طلا", "en": "Gold (oz)", "unit": "$"},
}


def _yahoo(sym):
    last_err = None
    for host in ("query1", "query2"):
        try:
            r = http.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}",
                         params={"range": "5d", "interval": "30m", "includePrePost": "false"},
                         timeout=15, retries=1, headers={"Accept": "application/json"})
            res = r.json()["chart"]["result"][0]
            meta = res["meta"]
            ts = res.get("timestamp") or []
            closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            series = [[t, round(c, 2)] for t, c in zip(ts, closes) if c is not None]
            price = meta.get("regularMarketPrice") or (series[-1][1] if series else None)
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            # previous close of the *last* session: use the last close before today's session start
            if series:
                last_day = series[-1][0] // 86400
                before = [c for t, c in series if t // 86400 < last_day]
                if before:
                    prev = before[-1]
            return {"price": round(price, 2), "prev": round(prev, 2) if prev else None,
                    "t": meta.get("regularMarketTime") or (series[-1][0] if series else now()),
                    "series": series[-160:], "src": "yahoo"}
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise last_err


def _stooq(sym):
    r = http.get("https://stooq.com/q/l/", params={"s": sym, "f": "sd2t2ohlc", "h": "", "e": "csv"}, timeout=15)
    row = next(csv.DictReader(io.StringIO(r.text)))
    price = float(row["Close"])
    op = float(row["Open"]) if row.get("Open") not in (None, "", "N/D") else None
    return {"price": round(price, 2), "prev": round(op, 2) if op else None, "t": now(), "series": [], "src": "stooq"}


def run(prev_state):
    out = {}
    for key, cfg in SYMBOLS.items():
        d = None
        for fn, sym in ((_yahoo, cfg["yahoo"]), (_stooq, cfg["stooq"])):
            try:
                d = fn(sym)
                break
            except Exception as e:  # noqa: BLE001
                log(f"markets {key} via {fn.__name__}: {str(e)[:80]}")
        if d is None:
            old = (prev_state or {}).get(key)
            if old:
                old = dict(old, status="stale")
            out[key] = old or {"status": "fail", "fa": cfg["fa"], "en": cfg["en"]}
            continue
        chg = (d["price"] - d["prev"]) if d.get("prev") else None
        out[key] = {
            "fa": cfg["fa"], "en": cfg["en"], "unit": cfg["unit"], "price": d["price"], "prev": d.get("prev"),
            "chg": round(chg, 2) if chg is not None else None,
            "chgPct": round(100 * chg / d["prev"], 2) if chg is not None and d["prev"] else None,
            "t": d["t"], "series": d["series"], "src": d["src"], "status": "ok",
        }
        # 24h change for the oil-spike light
        s = d["series"]
        if s:
            target = s[-1][0] - 86400
            older = [c for t, c in s if t <= target]
            if older:
                out[key]["chg24Pct"] = round(100 * (s[-1][1] - older[-1]) / older[-1], 2)
    return out
