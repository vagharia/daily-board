"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: public channels of Ali Gholhaki and Mohammad Marandi, on Telegram (t.me/s) and on Eitaa (Iranian
messenger with a public web preview), so their posts can be read directly."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

TG = ["aghplt", "aligholhaky", "aligholhaki", "gholhaki", "gholhaky", "ali_gholhaki", "Ali_Gholhaki", "gholhaki_ali",
      "smmarandi", "s_m_marandi", "marandi", "mohammadmarandi", "MohammadMarandi", "seyedmohammadmarandi",
      "marandi_sm", "smarandi"]
EITAA = ["aligholhaky", "aligholhaki", "gholhaki", "aghplt", "smmarandi", "marandi", "s_m_marandi",
         "mohammadmarandi", "seyedmohammadmarandi"]


def clean(s, n=120):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))[:n]


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
            "subs": subs.group(1) if subs else None, "sample": clean(texts[-1]) if texts else None}


def eitaa(handle):
    out = {}
    for url in (f"https://eitaa.com/{handle}", f"https://eitaa.com/s/{handle}"):
        try:
            r = http.get(url, timeout=20, retries=0)
        except Exception as e:  # noqa: BLE001
            out[url] = {"err": str(e)[:100]}
            continue
        t = r.text or ""
        classes = sorted(set(re.findall(r'class="([a-z_]*message[a-z_]*)', t)))[:20]
        title = re.search(r'<meta property="og:title" content="([^"]*)"', t) or re.search(r"<title>(.*?)</title>", t, re.S)
        times = re.findall(r'<time[^>]*datetime="([^"]+)"', t)
        i = t.find("message_text")
        out[url] = {"code": r.status_code, "len": len(t), "title": clean(title.group(1), 60) if title else None,
                    "classes": classes, "times": times[-3:], "n_times": len(times),
                    "snippet": t[max(0, i - 600):i + 900] if i >= 0 else clean(t, 400)}
    return out


res = {"t": int(time.time()), "tg": {}, "eitaa": {}}
for h in TG:
    res["tg"][h] = tg(h)
for h in EITAA:
    res["eitaa"][h] = eitaa(h)
    time.sleep(1)
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
