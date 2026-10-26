"""Tehran free-market dollar from the public Telegram channel: only executed trades
("معامله شد ✅") are read; buy (🔵) and sell (🔴) quotes are ignored. Trades are kept for one week, which is also
what the chart shows; older ones are deleted every round."""
import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from . import config, http
from .util import fa_norm, log, now, parse_date, tg_text, to_latin_digits

TEHRAN = timezone(timedelta(hours=3, minutes=30))
PRICE = re.compile(r"(\d{1,3}(?:[,٬،]\d{3})+|\d{5,7})")
CHECK = "✅"


def _page(before=None):
    url = f"https://t.me/s/{config.TG_CHANNEL}"
    params = {"before": str(before)} if before else None
    r = http.get(url, params=params, timeout=20, retries=1)
    soup = BeautifulSoup(r.content, "lxml")
    msgs = []
    for div in soup.select("div.tgme_widget_message[data-post]"):
        try:
            mid = int(div["data-post"].rsplit("/", 1)[1])
        except (ValueError, IndexError):
            continue
        tnode, _ = tg_text(div)                     # not the quoted post a reply shows above its own text
        text = tnode.get_text(" ", strip=True) if tnode else ""
        tm = div.select_one("time[datetime]")
        ts = parse_date(tm["datetime"]) if tm else None
        msgs.append({"id": mid, "text": text, "ts": ts})
    return msgs


def parse_trade(msg):
    text = msg["text"] or ""
    if CHECK not in text:
        return None
    norm = fa_norm(text)
    if "معامله شد" not in norm or "دلار" not in norm:
        return None
    latin = to_latin_digits(text)
    m = PRICE.search(latin)
    if not m:
        return None
    price = int(re.sub(r"[,٬،]", "", m.group(1)))
    if not 30_000 <= price <= 5_000_000:
        return None
    label = text[: text.find("⏳")] if "⏳" in text else latin[: m.start()]
    label = re.sub(r"[^؀-ۿ‌ ]", "", label).strip() or "دلار تهران"
    return {"id": msg["id"], "ts": msg["ts"] or now(), "price": price, "label": label}


def run(state):
    trades = state.setdefault("trades", [])
    last_id = state.get("last_id", 0)
    known = {t[2] for t in trades}
    found, pages, before, newest = [], 0, None, None
    err = None
    while pages < 8:
        try:
            msgs = _page(before)
        except Exception as e:  # noqa: BLE001
            err = str(e)[:100]
            break
        pages += 1
        if not msgs:
            break
        ids = [m["id"] for m in msgs]
        newest = max(newest or 0, max(ids))
        for m in msgs:
            tr = parse_trade(m)
            if tr and tr["id"] not in known:
                found.append(tr)
                known.add(tr["id"])
        oldest = min(ids)
        # keep paging back until we reach what we saw last time (or find at least one trade on first run)
        if last_id and oldest <= last_id:
            break
        if not last_id and (found or trades) and pages >= 3:
            break
        before = oldest
    for tr in found:
        trades.append([tr["ts"], tr["price"], tr["id"], tr["label"]])
    trades.sort(key=lambda x: x[2])
    cut = now() - config.WEEK
    trades[:] = [t for t in trades if t[0] >= cut]
    if newest:
        state["last_id"] = max(last_id, newest)
    log(f"dollar: pages={pages} new_trades={len(found)} total={len(trades)} err={err}")
    return summarize(trades, err)


def summarize(trades, err=None):
    if not trades:
        return {"status": "fail" if err else "empty", "error": err}
    ts, price, mid, label = trades[-1]
    prev = trades[-2][1] if len(trades) > 1 else None
    day = datetime.fromtimestamp(ts, TEHRAN).date()
    today = [t for t in trades if datetime.fromtimestamp(t[0], TEHRAN).date() == day]
    before_today = [t for t in trades if datetime.fromtimestamp(t[0], TEHRAN).date() < day]
    day_ref = before_today[-1][1] if before_today else (today[0][1] if today else None)
    out = {
        "status": "ok" if now() - ts < 18 * 3600 else "stale",
        "label": label, "price": price, "t": ts, "id": mid,
        "prev": prev, "chg": (price - prev) if prev else None,
        "dayRef": day_ref, "chgDay": (price - day_ref) if day_ref else None,
        "chgDayPct": round(100 * (price - day_ref) / day_ref, 2) if day_ref else None,
        "dayHigh": max(t[1] for t in today) if today else price,
        "dayLow": min(t[1] for t in today) if today else price,
        "trades": len(today),
        "series": [[t[0], t[1]] for t in trades if t[0] >= now() - config.WEEK],
        "error": err,
    }
    return out
