"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: the full reader-service text of two Economist articles (to see where the lead picture sits) and a
news search by headline for an article the slug search missed."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

ARTS = ["https://www.economist.com/business/2026/10/18/the-ai-industrys-gigantic-debts-are-making-investors-nervous",
        "https://www.economist.com/the-world-this-week/2026/10/22/politics"]


def get(url, **kw):
    try:
        r = http.get(url, timeout=40, retries=0, **kw)
        return r.status_code, r.text
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:200]


res = {"t": int(time.time()), "jina": {}, "bing": {}}
for a in ARTS:
    c, t = get("https://r.jina.ai/" + a)
    res["jina"][a] = {"code": c, "text": t[:30000]}
    time.sleep(4)

for q in ["The AI industry’s gigantic debts are making investors nervous",
          "site:economist.com AI industry gigantic debts investors nervous",
          "The world this week politics economist October 22nd 2026"]:
    c, t = get("https://www.bing.com/news/search", params={"q": q, "format": "rss"})
    out = []
    for it in re.findall(r"<item>(.*?)</item>", t, re.S)[:6]:
        link = re.search(r"<link>(.*?)</link>", it)
        img = re.search(r"<News:Image>(.*?)</News:Image>", it)
        out.append({"link": link.group(1)[-160:] if link else None, "img": img.group(1) if img else None})
    res["bing"][q] = {"code": c, "items": out}
    time.sleep(1)

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
