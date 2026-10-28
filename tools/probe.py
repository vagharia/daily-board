"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: the Central Elections Committee's live results site for the 2026 Knesset election (votes26), its
scripts, and any JSON data paths they reference."""
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

res = {"t": int(time.time()), "pages": {}, "scripts": {}, "paths": [], "tries": {}}
BASES = ["https://votes26.bechirot.gov.il/", "https://bechirot.gov.il/", "https://www.bechirot.gov.il/"]


def get(url, n=4000):
    try:
        r = http.get(url, timeout=25, retries=1)
        return {"status": r.status_code, "type": r.headers.get("content-type"), "len": len(r.content),
                "final": r.url, "head": r.text[:n]}, r.text
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:300]}, ""


scripts = set()
for b in BASES:
    info, txt = get(b, 6000)
    res["pages"][b] = info
    for src in re.findall(r"""<script[^>]+src=["']([^"']+)""", txt):
        scripts.add(urljoin(info.get("final") or b, src))
    for href in re.findall(r"""href=["']([^"']*(?:results|votes|tozaot|nationalresults)[^"']*)""", txt, re.I)[:20]:
        res["paths"].append(urljoin(info.get("final") or b, href))
    time.sleep(1)

found = set()
for s in list(scripts)[:12]:
    info, txt = get(s, 300)
    res["scripts"][s] = {k: info.get(k) for k in ("status", "len", "err")}
    for m in re.findall(r"""["'`]((?:https?://[^"'`\s]+)?/?[A-Za-z0-9_\-/{}.]*(?:api|json|results|Results|ballot|Ballot)"""
                        r"""[A-Za-z0-9_\-/{}.?=&]*)["'`]""", txt):
        if 4 < len(m) < 160:
            found.add(m)
    time.sleep(0.5)
res["paths"] += sorted(found)[:200]

for path in ["nationalresults", "api/nationalresults", "api/national", "api/results", "results.json",
             "data/results.json", "api/Results/GetNationalResults", "NationalResults", "assets/data/results.json"]:
    for b in BASES[:1]:
        info, _ = get(urljoin(b, path), 1500)
        res["tries"][urljoin(b, path)] = info
        time.sleep(0.5)

os.makedirs("_probe", exist_ok=True)
json.dump(res, open("_probe/probe.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: (v if k != "pages" else {u: {x: p.get(x) for x in ("status", "len", "final", "err")} for u, p in v.items()})
                  for k, v in res.items() if k in ("pages", "tries")}, ensure_ascii=False, indent=1)[:6000])
