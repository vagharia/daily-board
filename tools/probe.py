"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

OUT = {"t": int(time.time())}


def timed(fn):
    t0 = time.time()
    try:
        return {"ok": True, "ms": int((time.time() - t0) * 1000), "v": fn()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": f"{type(e).__name__}: {str(e)[:240]}"}


def sa_home():
    t = http.get("https://safeairspace.net/", timeout=30, retries=0).text
    i = t.find("data-feed-item-warn-level")
    blocks = [t[m.start() - 700:m.start() + 900] for m in list(re.finditer("data-feed-item-warn-level", t))[:3]]
    js = re.findall(r'window\["(\w+)Warning"\]\s*=\s*\'([^\']*)\'', t)[:40]
    lv = re.findall(r'(\w[\w ]{1,30})Level\W{0,6}(\d)', t)[:20]
    return {"len": len(t), "first_at": i, "blocks": blocks, "js": js, "lv": lv,
            "map": [t[m.start() - 200:m.start() + 300] for m in list(re.finditer(r"level-?[123]|warn-level-[123]", t))[:3]]}


def sa_country(c):
    t = http.get(f"https://safeairspace.net/{c}/", timeout=30, retries=0).text
    m = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    lvl = re.findall(r"(Level\s*\d[^<]{0,80})", t)[:5]
    upd = re.findall(r"((?:Updated|Last updated|Published)[^<]{0,80})", t, re.I)[:5]
    i = t.find("Level")
    return {"h1": re.sub(r"<[^>]+>", " ", m.group(1)).strip()[:120] if m else None, "level": lvl, "updated": upd,
            "around": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[max(0, i - 400):i + 2500]))[:2200]}


OUT["sa_home"] = timed(sa_home)
OUT["sa_iran"] = timed(lambda: sa_country("iran"))
OUT["sa_israel"] = timed(lambda: sa_country("israel"))
os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("probe done")
