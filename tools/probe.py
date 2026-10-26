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

# every message of one channel as the page shows it, text, quoted reply and media included
from bs4 import BeautifulSoup  # noqa: E402
from engine import http  # noqa: E402

raw = []
try:
    for before in (None, 66560):
        r = http.get("https://t.me/s/fundamental_View", params={"before": str(before)} if before else None, timeout=20,
                     retries=1)
        for div in BeautifulSoup(r.content, "lxml").select("div.tgme_widget_message[data-post]"):
            tx = div.select_one(".tgme_widget_message_text")
            rp = div.select_one(".tgme_widget_message_reply")
            tm = div.select_one("time[datetime]")
            raw.append({"post": div["data-post"], "time": tm["datetime"] if tm else None,
                        "text": tx.get_text(" ", strip=True)[:400] if tx else None,
                        "reply": rp.get_text(" ", strip=True)[:200] if rp else None,
                        "media": bool(div.select_one(".tgme_widget_message_photo_wrap, .tgme_widget_message_video_player,"
                                                     " .tgme_widget_message_document"))})
except Exception as e:  # noqa: BLE001
    raw.append({"err": str(e)[:300]})
res["fundamental_raw"] = raw

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
