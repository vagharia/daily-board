"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: (1) which official X accounts get a fresh embedded timeline (syndication), asked slowly to stay
under the rate limit; (2) can Bing's web search (RSS) find an account's recent posts; (3) more Telegram channels
of officials and journalists."""
import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}"
X_OFFICIAL = ["CENTCOM", "StateDept", "SecRubio", "WhiteHouse", "DeptofWar", "IDF", "IsraeliPM", "netanyahu",
              "Israel_katz", "IsraelMFA", "KremlinRussia_E", "RussiaUN", "Amb_Ulyanov", "SpoxCHN_MaoNing",
              "SpokespersonCHN", "USUN", "araghchi", "IRIMFA_SPOX", "Iran_UN", "khamenei_ir", "US5thFleet",
              "StateDeptSpox", "BarakRavid"]
BING = ["BarakRavid", "araghchi", "AmichaiStein1"]
TG = ["OrHeller", "Doron_Kadosh", "yanivkubovich", "itayblumental", "kann_news", "kannews", "N12News", "N12il",
      "amitsegal", "yossimelman", "talshalev", "arik3000", "dalirian_ir", "hosseindalirian", "dalirian",
      "smmarandi", "marandi_ir", "abasaslani", "aslani_abas", "farnazfassihi", "negarmortazavi", "jasonrezaian",
      "IranIntl", "iranintl", "bbcpersian", "radiofarda", "iranwire", "mfa_china", "zlj517", "globaltimes",
      "chinadaily", "MFAChina", "RusEmbIran", "rusembiran", "embassy_of_russia_in_iran", "UlyanovMikhail",
      "Ulyanov_Mikhail", "Amb_Ulyanov", "SolovievLive", "rybar", "Rybar", "intelslava", "idfspokesperson",
      "IDFSpokesperson", "israelpm", "IsraeliPM", "netanyahu", "CENTCOM", "khamenei", "leader_ir", "Khamenei_ir",
      "farsna", "tasnimnews", "mehrnews", "irna_1313", "sepahnews"]


def ts(s):
    try:
        return int(datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y").timestamp())
    except Exception:  # noqa: BLE001
        return 0


def xprobe(h):
    r = http.get(URL.format(h=h), timeout=25, retries=0, headers={"Accept": "text/html"})
    t = r.text or ""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    if not m:
        return {"code": r.status_code, "no_data": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:120]}
    d = json.loads(m.group(1))
    entries = (((d.get("props") or {}).get("pageProps") or {}).get("timeline") or {}).get("entries") or []
    tw = [e.get("content", {}).get("tweet") or {} for e in entries if e.get("type") == "tweet"]
    times = sorted((ts(x.get("created_at", "")) for x in tw), reverse=True)
    now = time.time()
    newest = max(tw, key=lambda x: ts(x.get("created_at", "")), default={})
    u = newest.get("user") or {}
    return {"n": len(tw), "newest": newest.get("created_at"), "last24h": sum(1 for x in times if now - x < 86400),
            "last3d": sum(1 for x in times if now - x < 3 * 86400), "name": u.get("name"),
            "verified_type": u.get("verified_type"), "blue": u.get("is_blue_verified"),
            "sample": re.sub(r"\s+", " ", newest.get("full_text") or newest.get("text") or "")[:120]}


def bing(h):
    out = {}
    for q in (f"site:x.com/{h}/status", f"x.com/{h}/status"):
        try:
            r = http.get("https://www.bing.com/search", params={"q": q, "format": "rss", "count": "30"}, timeout=20,
                         retries=0)
        except Exception as e:  # noqa: BLE001
            out[q] = {"err": str(e)[:100]}
            continue
        items = re.findall(r"<item>(.*?)</item>", r.text, re.S)
        links = [re.search(r"<link>(.*?)</link>", i).group(1) for i in items if re.search(r"<link>", i)]
        dates = [re.search(r"<pubDate>(.*?)</pubDate>", i).group(1) for i in items if re.search(r"<pubDate>", i)]
        out[q] = {"code": r.status_code, "items": len(items), "links": links[:6], "dates": dates[:6]}
    return out


def tg(handle):
    try:
        r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=0)
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:100]}
    t = r.text
    dates = re.findall(r'<time datetime="([^"]+)"', t)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    subs = re.search(r'counter_value">([^<]*)</span>\s*<span class="counter_type">subscribers', t)
    texts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', t, re.S)
    return {"posts": len(texts), "last": dates[-1] if dates else None, "title": title.group(1)[:50] if title else None,
            "subs": subs.group(1) if subs else None,
            "sample": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texts[-1]))[:100] if texts else None}


out = {"t": int(time.time()), "x": {}, "bing": {}, "tg": {}, "log": []}
for h in TG:
    out["tg"][h] = tg(h)
for h in BING:
    out["bing"][h] = bing(h)
for i, h in enumerate(X_OFFICIAL):
    t0 = time.time()
    try:
        out["x"][h] = xprobe(h)
    except Exception as e:  # noqa: BLE001
        out["x"][h] = {"err": str(e)[:100]}
    out["log"].append([i, h, int(time.time())])
    time.sleep(12)
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("probe done")
