"""Ticker run: Tehran dollar trades from Telegram + Brent + gold.

GitHub's scheduler starts this workflow far less often than its 5-minute cron asks for (roughly every
15-40 minutes), so one run refreshes the ticker several times, five minutes apart (DB_TICKER_ROUNDS)."""
import os
import time

from . import dollar, markets, store
from .util import data_path, load_json, log, now, save_json

ROUNDS = max(1, int(os.environ.get("DB_TICKER_ROUNDS", "1") or 1))
INTERVAL = 300


def update():
    """Refresh ticker.json in DATA_DIR (already prepared)."""
    started = time.time()
    prev = load_json(data_path("ticker.json"), {}) or {}
    state = load_json(data_path("state", "ticker_state.json"), {}) or {}
    try:
        usd = dollar.run(state.setdefault("dollar", {}))
    except Exception as e:  # noqa: BLE001
        log("dollar failed:", e)
        usd = prev.get("dollar") or {"status": "fail", "error": str(e)[:100]}
        if usd.get("status") == "ok":
            usd["status"] = "stale"
    mk = markets.run({k: prev.get(k) for k in ("brent", "gold")}, state.setdefault("markets", {}))
    out = {"v": 1, "updated": now(), "dollar": usd, **mk}
    save_json(data_path("ticker.json"), out)
    save_json(data_path("state", "ticker_state.json"), state)
    log(f"ticker done in {time.time() - started:.1f}s: usd={usd.get('price')} brent={mk['brent'].get('price')} "
        f"gold={mk['gold'].get('price')}")


def once():
    store.prepare()
    prev = load_json(data_path("ticker.json"), {}) or {}
    if ROUNDS > 1 and prev.get("updated") and now() - prev["updated"] < 150:
        log("ticker refreshed moments ago by another run; skipping this round")
        return
    update()
    store.publish("ticker")


def main():
    t0 = time.time()
    for i in range(ROUNDS):
        try:
            once()
        except Exception as e:  # noqa: BLE001 - one bad round shouldn't end the run
            log("ticker round failed:", str(e)[:200])
        if i < ROUNDS - 1:
            wait = t0 + (i + 1) * INTERVAL - time.time()
            if wait > 0:
                time.sleep(wait)


if __name__ == "__main__":
    main()
