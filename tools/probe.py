"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402


def strip(s, n=300):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:n]


def tg(handle):
    r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=0)
    t = r.text
    dates = re.findall(r'<time datetime="([^"]+)"', t)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    desc = re.search(r'<meta property="og:description" content="([^"]*)"', t)
    subs = re.search(r'tgme_page_extra">([^<]*)<', t) or re.search(r'counter_value">([^<]*)<', t)
    texts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', t, re.S)
    return {"code": r.status_code, "posts": len(texts), "first": dates[0] if dates else None,
            "last": dates[-1] if dates else None, "title": title.group(1)[:80] if title else None,
            "desc": desc.group(1)[:300] if desc else None, "subs": subs.group(1) if subs else None,
            "samples": [strip(x, 260) for x in texts[-20:]]}


out = {"t": int(time.time())}
for h in ("mazene",):
    try:
        out[h] = tg(h)
    except Exception as e:  # noqa: BLE001
        out[h] = {"err": str(e)[:200]}
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("probe done")
