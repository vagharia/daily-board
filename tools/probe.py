"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch.

This round: the Central Elections Committee's live results site (votes26) in a real browser: whether its bot
check lets a headless Chromium through, the JSON it loads, and the page's text."""
import json
import os
import time

from playwright.sync_api import sync_playwright

res = {"t": int(time.time()), "json": [], "pages": {}}
URLS = ["https://votes26.bechirot.gov.il/", "https://votes26.bechirot.gov.il/nationalresults"]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(locale="he-IL", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36", viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    seen = []

    def on_resp(r):
        ct = r.headers.get("content-type", "")
        u = r.url
        seen.append([r.status, ct[:40], u[:200]])
        if "json" in ct or u.endswith(".json"):
            try:
                body = r.text()
            except Exception as e:  # noqa: BLE001
                body = "ERR " + str(e)[:100]
            res["json"].append({"url": u, "status": r.status, "len": len(body), "body": body[:6000]})

    page.on("response", on_resp)
    for u in URLS:
        try:
            page.goto(u, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(12000)
            res["pages"][u] = {"final": page.url, "title": page.title(), "text": page.inner_text("body")[:8000],
                               "html": page.content()[:3000]}
        except Exception as e:  # noqa: BLE001
            res["pages"][u] = {"err": str(e)[:300]}
    res["requests"] = seen[-150:]
    b.close()

os.makedirs("_probe", exist_ok=True)
json.dump(res, open("_probe/probe.json", "w"), ensure_ascii=False, indent=1)
print(len(res["json"]), "json responses")
