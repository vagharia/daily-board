"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/ files, which the workflow pushes to the `probe` branch."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402

os.makedirs("_probe", exist_ok=True)
out = {"t": int(time.time())}
for c in ("iran", "israel", "iraq", "saudi-arabia", "united-arab-emirates"):
    try:
        t = http.get(f"https://safeairspace.net/{c}/", timeout=30, retries=0).text
        i = t.find("Risk Level")
        j = t.find("Current warnings list")
        out[c] = {"len": len(t), "risk_at": i, "warn_at": j, "chunk": t[max(0, i - 3000):(j + 12000) if j > 0 else i + 8000]}
    except Exception as e:  # noqa: BLE001
        out[c] = {"err": str(e)[:200]}
    time.sleep(1)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("probe done")
