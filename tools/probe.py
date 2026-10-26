"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: feeds of an internet-measurement group's public posts, as a news source on internet disruptions."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402
from engine.feeds import parse_feed  # noqa: E402

FEEDS = ["https://mastodon.social/@netblocks.rss",
         "https://bsky.app/profile/netblocks.org/rss",
         "https://netblocks.org/feed",
         "https://netblocks.org/reports/feed",
         "https://mastodon.social/@ioda_live.rss",
         "https://bsky.app/profile/ioda-live.bsky.social/rss",
         "https://mastodon.social/@CloudflareRadar.rss",
         "https://bsky.app/profile/radar.cloudflare.com/rss"]

res = {"t": int(time.time()), "feeds": {}}
for u in FEEDS:
    try:
        r = http.get(u, timeout=25, retries=0)
        entries = parse_feed(r.content)
        res["feeds"][u] = {"code": r.status_code, "n": len(entries), "items": [
            {"title": (e.get("title") or "")[:160], "date": e.get("date"), "link": e.get("link"),
             "text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", e.get("summary") or e.get("content") or ""))[:400]}
            for e in entries[:12]]}
    except Exception as e:  # noqa: BLE001
        res["feeds"][u] = {"err": str(e)[:200]}
    time.sleep(1)

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
