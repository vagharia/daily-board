"""Brent crude and spot gold.

Quotes come from TradingView's public quote scanner: Brent from FXCM's UKOIL (front-month Brent,
real-time; ICE front month as a fallback) and gold from OANDA's XAU/USD spot (TVC:GOLD as a fallback),
so the numbers match what traders see. Yahoo's continuous Brent symbol had already rolled to a later
contract and its gold quote is the December future, which is why they are no longer used for quotes.
Charts are built from our own samples every round and cover one week; older samples are deleted every round.
Brent's is seeded once with Yahoo's 30-minute bars for the same front-month contract."""
import time

from . import config, http
from .util import log, now

TV = "https://scanner.tradingview.com/global/scan"
SYMBOLS = {
    "brent": {"tv": ["FX:UKOIL", "ICEEUR:BRN1!"], "fa": "نفت برنت", "en": "Brent", "unit": "$"},
    "gold": {"tv": ["OANDA:XAUUSD", "TVC:GOLD"], "fa": "اونس طلا", "en": "Gold (oz)", "unit": "$"},
}
SRC_NAME = {"FX:UKOIL": "FXCM UKOIL", "ICEEUR:BRN1!": "ICE Brent", "OANDA:XAUUSD": "OANDA XAU/USD",
            "TVC:GOLD": "TVC Gold"}
MONTHS = "FGHJKMNQUVXZ"
KEEP = config.WEEK


def _tv(tickers):
    body = {"symbols": {"tickers": tickers, "query": {"types": []}}, "columns": ["close", "change", "description"]}
    r = http.post(TV, json_body=body, timeout=15, retries=1,
                  headers={"Accept": "application/json", "Origin": "https://www.tradingview.com",
                           "Referer": "https://www.tradingview.com/"})
    return {row["s"]: row["d"] for row in r.json().get("data", []) if row.get("d") and row["d"][0]}


def brent_contract(t):
    """Yahoo symbol of the ICE Brent front month: in month m the front contract is month m+2."""
    g = time.gmtime(t)
    m, y = g.tm_mon + 2, g.tm_year
    if m > 12:
        m, y = m - 12, y + 1
    return f"BZ{MONTHS[m - 1]}{y % 100:02d}.NYM"


def _yahoo_bars(sym):
    r = http.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                 params={"range": "5d", "interval": "30m", "includePrePost": "false"},
                 timeout=15, retries=1, headers={"Accept": "application/json"})
    res = r.json()["chart"]["result"][0]
    ts = res.get("timestamp") or []
    closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    return [[t, round(c, 2)] for t, c in zip(ts, closes) if c is not None], res["meta"]


def _yahoo_quote(key, t):
    sym = brent_contract(t) if key == "brent" else "GC=F"
    bars, meta = _yahoo_bars(sym)
    price = meta.get("regularMarketPrice") or (bars[-1][1] if bars else None)
    prev = meta.get("chartPreviousClose")
    return price, prev, f"Yahoo {sym}"


def _thin(series, t):
    """Every sample for the last 24 hours, one every 30 minutes before that, a week in all (the chart spans the
    week, so older samples don't need more detail, and the file the app reloads every minute stays small)."""
    out, last = [], 0
    for p in series:
        if p[0] < t - KEEP:
            continue
        if p[0] < t - 86400 and p[0] - last < 1800:
            continue
        out.append(p)
        last = p[0]
    return out


def run(prev_state, state):
    t = now()
    series_state = state.setdefault("series", {})
    try:
        quotes = _tv([s for c in SYMBOLS.values() for s in c["tv"]])
    except Exception as e:  # noqa: BLE001
        log("markets: tradingview failed:", str(e)[:100])
        quotes = {}
    out = {}
    for key, cfg in SYMBOLS.items():
        sym = next((s for s in cfg["tv"] if s in quotes), None)
        price = prev = src = None
        if sym:
            close, chg_pct = quotes[sym][0], quotes[sym][1]
            price = round(close, 2)
            prev = round(close / (1 + chg_pct / 100), 2) if chg_pct not in (None, -100) else None
            src = SRC_NAME.get(sym, sym)
        else:
            try:
                price, prev, src = _yahoo_quote(key, t)
            except Exception as e:  # noqa: BLE001
                log(f"markets {key}: yahoo fallback failed: {str(e)[:80]}")
        if price is None:
            old = (prev_state or {}).get(key)
            out[key] = dict(old, status="stale") if old else {"status": "fail", "fa": cfg["fa"], "en": cfg["en"]}
            continue
        ser = series_state.setdefault(key, [])
        if not ser and key == "brent":
            try:                                   # give the chart some history on the first run
                bars, _ = _yahoo_bars(brent_contract(t))
                ser.extend(p for p in bars if p[0] < t - 600)
            except Exception as e:  # noqa: BLE001
                log("markets: brent seed failed:", str(e)[:80])
        if not ser or ser[-1][1] != price or t - ser[-1][0] >= 900:
            ser.append([t, price])
        ser[:] = _thin(ser, t)
        chg = round(price - prev, 2) if prev else None
        item = {"fa": cfg["fa"], "en": cfg["en"], "unit": cfg["unit"], "price": price, "prev": prev, "chg": chg,
                "chgPct": round(100 * chg / prev, 2) if chg is not None and prev else None, "t": t,
                "series": list(ser), "src": src, "status": "ok"}
        older = [p for p in ser if p[0] <= t - 86400]
        if older:
            item["chg24Pct"] = round(100 * (price - older[-1][1]) / older[-1][1], 2)
        out[key] = item
    return out
