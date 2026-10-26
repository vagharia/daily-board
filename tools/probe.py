"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: a search of the Telegram channel sources' public pages for one post, and two single posts."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup  # noqa: E402

from engine import http  # noqa: E402

CHANNELS = ["fundamental_View", "SBoxxx", "VahidOnline", "tsepress", "mazene"]
res = {"t": int(time.time()), "search": {}, "single": {}}


def messages(html):
    out = []
    for div in BeautifulSoup(html, "lxml").select("div.tgme_widget_message[data-post]"):
        tx = div.select_one(".tgme_widget_message_text")
        tm = div.select_one("time[datetime]")
        rp = div.select_one(".tgme_widget_message_reply")
        out.append({"post": div["data-post"], "time": tm["datetime"] if tm else None,
                    "text": tx.get_text(" ", strip=True)[:500] if tx else None,
                    "reply": rp.get_text(" ", strip=True)[:200] if rp else None,
                    "classes": " ".join(div.get("class", []))[:120],
                    "media": bool(div.select_one(".tgme_widget_message_photo_wrap, .tgme_widget_message_video_player,"
                                                 " .tgme_widget_message_document, .message_media_not_supported"))})
    return out


for ch in CHANNELS:
    for q in ("کرمانشاه", "اهواز"):
        try:
            r = http.get(f"https://t.me/s/{ch}", params={"q": q}, timeout=20, retries=1)
            res["search"][f"{ch}:{q}"] = messages(r.content)[-8:]
        except Exception as e:  # noqa: BLE001
            res["search"][f"{ch}:{q}"] = {"err": str(e)[:200]}
        time.sleep(1)
for post in ("fundamental_View/66578", "fundamental_View/66560", "fundamental_View/66582", "fundamental_View/66583"):
    try:
        r = http.get(f"https://t.me/{post}", params={"embed": "1", "mode": "tme"}, timeout=20, retries=1)
        soup = BeautifulSoup(r.content, "lxml")
        tx = soup.select_one(".tgme_widget_message_text")
        err = soup.select_one(".tgme_widget_message_error")
        res["single"][post] = {"text": tx.get_text(" ", strip=True)[:500] if tx else None,
                               "error": err.get_text(" ", strip=True)[:200] if err else None,
                               "media": bool(soup.select_one(".tgme_widget_message_photo_wrap, .tgme_widget_message_video_player,"
                                                             " .message_media_not_supported"))}
    except Exception as e:  # noqa: BLE001
        res["single"][post] = {"err": str(e)[:200]}
    time.sleep(1)
try:
    r = http.get("https://t.me/s/fundamental_View", timeout=20, retries=1)
    res["latest"] = messages(r.content)[-25:]
except Exception as e:  # noqa: BLE001
    res["latest"] = {"err": str(e)[:200]}

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("probe done")
