"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: The Economist's section RSS feeds (titles, links, descriptions, any picture) and whether an article
page gives its preview picture (og:image), for the weekly Economist tab."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http, media  # noqa: E402

SECTIONS = ["leaders", "briefing", "middle-east-and-africa", "finance-and-economics", "business", "china", "asia",
            "europe", "international", "science-and-technology", "united-states", "the-americas", "britain",
            "culture", "the-world-this-week"]


def clean(s, n=200):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:n]


res = {"t": int(time.time()), "rss": {}, "pages": {}}
first_links = []
for sec in SECTIONS:
    url = f"https://www.economist.com/{sec}/rss.xml"
    try:
        r = http.get(url, timeout=20, retries=1)
        t = r.text
        items = re.findall(r"<item>(.*?)</item>", t, re.S)
        out = []
        for it in items[:40]:
            title = re.search(r"<title>(.*?)</title>", it, re.S)
            link = re.search(r"<link>(.*?)</link>", it, re.S)
            desc = re.search(r"<description>(.*?)</description>", it, re.S)
            date = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
            img = re.search(r'<media:(?:content|thumbnail)[^>]*url="([^"]+)"', it) or re.search(r'<enclosure[^>]*url="([^"]+)"', it)
            out.append({"title": clean(title.group(1) if title else "", 160).replace("<![CDATA[", "").replace("]]>", ""),
                        "link": clean(link.group(1) if link else "", 300),
                        "desc": clean((desc.group(1) if desc else "").replace("<![CDATA[", "").replace("]]>", ""), 220),
                        "date": clean(date.group(1) if date else "", 40), "img": img.group(1) if img else None})
        res["rss"][sec] = {"code": r.status_code, "n": len(items), "items": out}
        if out and out[0]["link"]:
            first_links.append(out[0]["link"])
    except Exception as e:  # noqa: BLE001
        res["rss"][sec] = {"err": str(e)[:160]}
    time.sleep(1)
for link in first_links[:4]:
    try:
        res["pages"][link] = media.page_meta(link)
    except Exception as e:  # noqa: BLE001
        res["pages"][link] = {"err": str(e)[:160]}
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
