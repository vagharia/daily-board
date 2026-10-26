"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: where a preview picture for an Economist article can be found from a runner, since the article pages
themselves answer 403 to plain requests (sitemaps, link-preview agents, web archives, link-preview services)."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

ARTS = ["https://www.economist.com/leaders/2026/10/22/saudi-arabia-and-the-uae-are-sowing-chaos",
        "https://www.economist.com/middle-east-and-africa/2026/10/25/politics-not-strategy-could-mean-more-israeli-strikes-on-iran"]
UAS = {
    "facebook": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "twitter": "Twitterbot/1.0",
    "slack": "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "telegram": "TelegramBot (like TwitterBot)",
    "whatsapp": "WhatsApp/2.23.20.0",
    "discord": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "linkedin": "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
    "google": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}
OG = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*content=["\']([^"\']+)', re.I)
OG2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\']', re.I)


def og(html):
    m = OG.search(html) or OG2.search(html)
    return m.group(1) if m else None


def get(url, **kw):
    try:
        r = http.get(url, timeout=20, retries=0, **kw)
        return r.status_code, r.text
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:200]


res = {"t": int(time.time()), "ua": {}, "wayback": {}, "microlink": {}, "jina": {}, "bing": {}, "site": {}, "img": {}}

for name, ua in UAS.items():
    code, txt = get(ARTS[0], headers={"User-Agent": ua, "Accept": "text/html"}, max_bytes=400_000)
    res["ua"][name] = {"code": code, "og": og(txt) if code == 200 else None, "head": txt[:160] if code != 200 else None}
    time.sleep(0.5)

for a in ARTS:
    code, txt = get("https://archive.org/wayback/available", params={"url": a})
    snap = None
    try:
        snap = json.loads(txt)["archived_snapshots"].get("closest", {}).get("url")
    except Exception:  # noqa: BLE001
        pass
    entry = {"code": code, "snap": snap}
    raw = "https://web.archive.org/web/2026id_/" + a
    c2, t2 = get(raw, max_bytes=500_000)
    entry["raw_code"] = c2
    entry["raw_og"] = og(t2) if c2 == 200 else t2[:160]
    res["wayback"][a] = entry

    c3, t3 = get("https://api.microlink.io/", params={"url": a})
    try:
        j = json.loads(t3)
        res["microlink"][a] = {"code": c3, "status": j.get("status"), "img": (j.get("data") or {}).get("image"),
                               "title": (j.get("data") or {}).get("title")}
    except Exception:  # noqa: BLE001
        res["microlink"][a] = {"code": c3, "txt": t3[:200]}

    c4, t4 = get("https://r.jina.ai/" + a, headers={"Accept": "text/plain"})
    res["jina"][a] = {"code": c4, "imgs": re.findall(r"https://[^\s)\"']+\.(?:jpe?g|png|webp)[^\s)\"']*", t4)[:5],
                      "head": t4[:300]}

    title = a.rsplit("/", 1)[1].replace("-", " ")
    c5, t5 = get("https://www.bing.com/news/search", params={"q": title + " economist", "format": "rss"})
    items = re.findall(r"<item>(.*?)</item>", t5, re.S)[:4]
    res["bing"][a] = {"code": c5, "n": len(items), "items": [
        {"link": (re.search(r"<link>(.*?)</link>", it) or [None, None])[1] if re.search(r"<link>(.*?)</link>", it) else None,
         "img": (re.search(r"<News:Image>(.*?)</News:Image>", it).group(1) if re.search(r"<News:Image>(.*?)</News:Image>", it) else None)}
        for it in items]}
    time.sleep(1)

for u in ["https://www.economist.com/robots.txt", "https://www.economist.com/sitemap.xml",
          "https://www.economist.com/googlenews.xml", "https://www.economist.com/sitemap-news.xml",
          "https://www.economist.com/weeklyedition/2026-10-24", "https://www.economist.com/latest/rss.xml"]:
    code, txt = get(u, max_bytes=300_000)
    res["site"][u] = {"code": code, "head": txt[:1500], "imgs": re.findall(r"<image:loc>(.*?)</image:loc>", txt)[:5],
                      "len": len(txt)}

for u in ["https://www.economist.com/content-assets/images/20261024_LDD001.jpg",
          "https://www.economist.com/cdn-cgi/image/width=834,quality=80,format=auto/content-assets/images/20261024_LDD001.jpg",
          "https://www.economist.com/img/b/1280/720/90/media-assets/image/20261024_LDD001.jpg",
          "https://www.economist.com/media-assets/image/20261024_LDD001.jpg"]:
    try:
        r = http.get(u, timeout=20, retries=0, max_bytes=2000)
        res["img"][u] = {"code": r.status_code, "type": r.headers.get("content-type")}
    except Exception as e:  # noqa: BLE001
        res["img"][u] = {"err": str(e)[:160]}

code, txt = get("https://www.economist.com/leaders/rss.xml", max_bytes=60_000)
m = re.search(r"<item>(.*?)</item>", txt, re.S)
res["raw_item"] = m.group(1)[:2500] if m else txt[:800]

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
