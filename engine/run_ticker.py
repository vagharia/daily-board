"""Ticker run (every 5 minutes): Tehran dollar trades from Telegram + Brent + gold."""
import time

from . import dollar, markets, store
from .util import data_path, load_json, log, now, save_json


def main():
    started = time.time()
    store.prepare()
    state = load_json(data_path("state", "ticker_state.json"), {}) or {}
    prev = load_json(data_path("ticker.json"), {}) or {}
    try:
        usd = dollar.run(state.setdefault("dollar", {}))
    except Exception as e:  # noqa: BLE001
        log("dollar failed:", e)
        usd = prev.get("dollar") or {"status": "fail", "error": str(e)[:100]}
        if usd.get("status") == "ok":
            usd["status"] = "stale"
    mk = markets.run({k: prev.get(k) for k in ("brent", "gold")})
    out = {"v": 1, "updated": now(), "dollar": usd, **mk}
    save_json(data_path("ticker.json"), out)
    save_json(data_path("state", "ticker_state.json"), state)
    store.publish("ticker")
    log(f"ticker done in {time.time() - started:.1f}s: usd={usd.get('price')} brent={mk['brent'].get('price')} "
        f"gold={mk['gold'].get('price')}")


if __name__ == "__main__":
    main()
