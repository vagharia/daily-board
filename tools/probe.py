"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: the latest posts of the Telegram channels among the sources, and how the rules read each one."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import collect  # noqa: E402
from engine.classify import classify  # noqa: E402
from engine.relevance import is_relevant  # noqa: E402
from engine.sources import SOURCES  # noqa: E402

T = int(time.time())
res = {"t": T, "channels": {}}
for src in [s for s in SOURCES if s.get("kind") == "tg"]:
    out = []
    try:
        entries = collect.tg_entries(src["tg"][0])
        for it in collect.make_items(src, entries, "tg", T):
            ok = is_relevant(it)[1]
            if ok:
                classify(it)
            out.append({"t": it["t"], "u": it["u"], "ti": it["ti"], "su": (it.get("su") or "")[:300], "rel": ok,
                        "sev": it.get("sev"), "flags": it.get("flags")})
        res["channels"][src["id"]] = out[-25:]
    except Exception as e:  # noqa: BLE001
        res["channels"][src["id"]] = {"err": str(e)[:300]}
    time.sleep(1)

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
