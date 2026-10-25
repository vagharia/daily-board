"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: can we read recent posts of chosen X accounts without X's paid API (syndication timeline,
Nitter mirrors, RSSHub), and which officials and journalists publish on public Telegram channels?"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

HANDLES = ["barakravid", "araghchi", "MFA_China", "mfa_russia"]
X_ENDPOINTS = [
    "https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}",
    "https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}?showReplies=false",
    "https://cdn.syndication.twimg.com/timeline/profile?screen_name={h}",
    "https://xcancel.com/{h}/rss",
    "https://nitter.net/{h}/rss",
    "https://nitter.poast.org/{h}/rss",
    "https://nitter.privacydev.net/{h}/rss",
    "https://nitter.space/{h}/rss",
    "https://lightbrd.com/{h}/rss",
    "https://nitter.tiekoetter.com/{h}/rss",
    "https://nitter.kuuro.net/{h}/rss",
    "https://nuku.trabun.org/{h}/rss",
    "https://nitter.catsarch.com/{h}/rss",
    "https://rsshub.app/twitter/user/{h}",
]
TG = ["MID_Russia", "MFARussia", "MariaVladimirovnaZakharova", "medvedev_telegram", "news_kremlin", "tass_agency",
      "khamenei_ir", "Khamenei_fa", "araghchi", "araghchi_ir", "IRIMFA", "irimfa_spox", "baghaei_ir", "dolat_ir",
      "president_ir", "pezeshkian_ir", "mb_ghalibaf", "ghalibaf_ir", "idfofficial", "IDFofficial", "avichayadraee",
      "LTC_Shoshani", "IsraelMFA", "IsraelPersian", "israelinpersian", "amitsegal", "barakravid", "BarakRavid1",
      "AmichaiStein1", "amichaistein", "manniefabian", "abualiexpress", "SepahNews", "sepah_news", "PressTV",
      "Tasnimnews_EN", "chinaembassy", "globaltimesnews", "XHNews", "CGTNOfficial", "rtnews", "RT_com"]


def strip(s, n=200):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:n]


def x_probe(url):
    try:
        r = http.get(url, timeout=20, retries=0, headers={"Accept": "text/html,application/xml,application/json"})
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:160]}
    t = r.text or ""
    out = {"code": r.status_code, "len": len(t), "ctype": r.headers.get("content-type", "")[:40]}
    if "__NEXT_DATA__" in t:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
        try:
            d = json.loads(m.group(1)) if m else {}
            entries = (((d.get("props") or {}).get("pageProps") or {}).get("timeline") or {}).get("entries") or []
            tw = [e.get("content", {}).get("tweet") for e in entries if e.get("type") == "tweet"]
            out["entries"] = len(entries)
            out["tweets"] = [{"id": x.get("id_str"), "t": x.get("created_at"), "text": strip(x.get("full_text") or x.get("text"), 140)}
                             for x in tw[:4] if x]
        except Exception as e:  # noqa: BLE001
            out["parse_err"] = str(e)[:100]
    items = re.findall(r"<item>(.*?)</item>", t, re.S)
    if items:
        out["items"] = len(items)
        out["first"] = [strip(re.search(r"<title>(.*?)</title>", i, re.S).group(1) if re.search(r"<title>", i) else "", 120)
                        + " | " + (re.search(r"<pubDate>(.*?)</pubDate>", i).group(1) if re.search(r"<pubDate>", i) else "")
                        for i in items[:3]]
    if not items and "__NEXT_DATA__" not in t:
        out["head"] = strip(t, 220)
    return out


def tg(handle):
    try:
        r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=0)
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:120]}
    t = r.text
    dates = re.findall(r'<time datetime="([^"]+)"', t)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    subs = re.search(r'counter_value">([^<]*)</span>\s*<span class="counter_type">subscribers', t)
    texts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', t, re.S)
    return {"code": r.status_code, "posts": len(texts), "last": dates[-1] if dates else None,
            "title": title.group(1)[:60] if title else None, "subs": subs.group(1) if subs else None,
            "sample": strip(texts[-1], 160) if texts else None}


out = {"t": int(time.time()), "x": {}, "tg": {}}
for h in HANDLES:
    for tpl in X_ENDPOINTS:
        if h != HANDLES[0] and not any(k in tpl for k in ("syndication.twitter.com", "xcancel", "nitter.net")):
            continue                          # the other handles only on the most promising endpoints
        url = tpl.format(h=h)
        out["x"][url] = x_probe(url)
for h in TG:
    out["tg"][h] = tg(h)
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("probe done")
