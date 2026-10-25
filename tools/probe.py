"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: the raw page of Ali Gholhaki's Eitaa channel (to write its parser offline) and the recent posts of
Mohammad Marandi's Telegram channel (to see what he posts there)."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402


def clean(s, n=400):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))[:n]


res = {"t": int(time.time())}
try:
    r = http.get("https://eitaa.com/aligholhaky", timeout=25, retries=1)
    res["eitaa_code"] = r.status_code
    res["eitaa_html"] = r.text
except Exception as e:  # noqa: BLE001
    res["eitaa_err"] = str(e)[:200]
try:
    r = http.get("https://t.me/s/s_m_marandi", timeout=25, retries=1)
    t = r.text
    posts = re.findall(r'data-post="([^"]+)"(.*?)(?=data-post="|$)', t, re.S)
    res["marandi"] = []
    for pid, body in posts:
        tm = re.search(r'<time datetime="([^"]+)"', body)
        tx = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', body, re.S)
        res["marandi"].append({"id": pid, "t": tm.group(1) if tm else None, "text": clean(tx.group(1)) if tx else None,
                               "photo": "message_photo" in body, "video": "message_video" in body})
except Exception as e:  # noqa: BLE001
    res["marandi_err"] = str(e)[:200]
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
