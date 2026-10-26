"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: preview pictures for a few Economist articles through a reader service, the web archive and a news
search, since the article pages themselves answer 403 to plain requests."""
import json
import os
import re
import sys
import time
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

ARTS = ["https://www.economist.com/middle-east-and-africa/2026/10/19/everything-is-going-wrong-for-muhammad-bin-salman",
        "https://www.economist.com/briefing/2026/10/22/emirati-saudi-rivalry-is-spurring-bloodshed-on-a-horrific-scale",
        "https://www.economist.com/business/2026/10/18/the-ai-industrys-gigantic-debts-are-making-investors-nervous",
        "https://www.economist.com/the-world-this-week/2026/10/22/politics",
        "https://www.economist.com/finance-and-economics/2026/10/20/the-late-perry-mehrling-explained-the-hierarchy-of-money"]
OG = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*content=["\']([^"\']+)', re.I)
OG2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\']', re.I)
ASSET = re.compile(r"https://www\.economist\.com/[^\s\"')]*content-assets/images/[^\s\"')]+")


def og(html):
    m = OG.search(html) or OG2.search(html)
    return m.group(1) if m else None


def get(url, **kw):
    try:
        r = http.get(url, timeout=40, retries=0, **kw)
        return r.status_code, r.text
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:200]


res = {"t": int(time.time()), "jina_html": {}, "jina_md": {}, "wayback": {}, "bing": {}, "bing_img": {}}
for a in ARTS:
    c, t = get("https://r.jina.ai/" + a, headers={"X-Return-Format": "html"})
    res["jina_html"][a] = {"code": c, "og": og(t) if c == 200 else None, "len": len(t),
                           "assets": ASSET.findall(t)[:12], "title": (re.search(r"<title>(.*?)</title>", t, re.S) or [None, None])[1] if c == 200 and re.search(r"<title>(.*?)</title>", t, re.S) else t[:200]}
    time.sleep(3)
    c, t = get("https://r.jina.ai/" + a)
    res["jina_md"][a] = {"code": c, "len": len(t), "assets": ASSET.findall(t)[:12], "head": t[:600]}
    time.sleep(3)

for a in ARTS[:3]:
    time.sleep(6)
    c, t = get("https://web.archive.org/web/2026id_/" + a, max_bytes=600_000)
    res["wayback"][a] = {"code": c, "og": og(t) if c == 200 else None, "err": None if c == 200 else t[:160]}

for a in ARTS:
    title = a.rsplit("/", 1)[1].replace("-", " ")
    c, t = get("https://www.bing.com/news/search", params={"q": title + " economist", "format": "rss"})
    out = []
    for it in re.findall(r"<item>(.*?)</item>", t, re.S)[:6]:
        link = re.search(r"<link>(.*?)</link>", it)
        img = re.search(r"<News:Image>(.*?)</News:Image>", it)
        out.append({"link": link.group(1) if link else None, "img": img.group(1).replace("&amp;", "&") if img else None})
    hit = [o for o in out if o["link"] and quote(a.split("economist.com")[1], safe="").lower() in o["link"].lower()]
    res["bing"][a] = {"code": c, "n": len(out), "hit": hit[:1], "first": out[:2]}
    if hit and hit[0]["img"]:
        u = hit[0]["img"].replace("http://", "https://") + "&w=1200&h=675&c=7"
        try:
            r = http.get(u, timeout=20, retries=0)
            res["bing_img"][a] = {"url": u, "code": r.status_code, "type": r.headers.get("content-type"),
                                  "bytes": len(r.content)}
        except Exception as e:  # noqa: BLE001
            res["bing_img"][a] = {"url": u, "err": str(e)[:160]}
    time.sleep(1)

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
