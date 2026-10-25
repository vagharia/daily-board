"""Live loop: every 5 minutes refresh the dollar, Brent and gold and the news, and publish both.

GitHub starts scheduled workflows far less often than a 5-minute cron asks for, so one run of the
live workflow keeps going for several rounds, five minutes apart. Google News / Bing fallbacks run in
"full" rounds (every ~15 minutes) so Google doesn't throttle us; air data is refreshed every ~30 minutes
(OpenSky's anonymous daily allowance)."""
import os
import time

from . import config, run_news, run_ticker, store
from .util import data_path, load_json, log, now

ROUNDS = max(1, int(os.environ.get("DB_LIVE_ROUNDS", "5") or 5))
INTERVAL = int(os.environ.get("DB_LIVE_INTERVAL", "300") or 300)
FULL_EVERY = 14 * 60


def one_round(i):
    t0 = time.time()
    store.prepare()
    try:
        run_ticker.update()
    except Exception as e:  # noqa: BLE001 - the news must still go out
        log("ticker part failed:", str(e)[:200])
    misc = load_json(data_path("state", "misc.json"), {}) or {}
    full = now() - (misc.get("last_full") or 0) >= FULL_EVERY or config.OFFLINE and i == 0
    try:
        run_news.news_round(full=full)
    except Exception as e:  # noqa: BLE001
        log("news part failed:", str(e)[:300])
    store.publish("all")
    log(f"round {i + 1}/{ROUNDS} ({'full' if full else 'light'}) finished in {time.time() - t0:.1f}s")


def main():
    start = time.time()
    for i in range(ROUNDS):
        try:
            one_round(i)
        except Exception as e:  # noqa: BLE001
            log("round failed:", str(e)[:300])
        if i < ROUNDS - 1:
            wait = start + (i + 1) * INTERVAL - time.time()
            if wait > 0:
                time.sleep(wait)


if __name__ == "__main__":
    main()
