"""Temporary: find the JSON feeds behind election results pages (removed after use)."""
import sys
from playwright.sync_api import sync_playwright

PAGES = sys.argv[1:]
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36")
    for url in PAGES:
        print("=== PAGE", url, flush=True)
        page = ctx.new_page()
        seen = []
        def on_resp(r):
            ct = r.headers.get("content-type", "")
            if "json" in ct or r.url.split("?")[0].endswith(".json"):
                try:
                    body = r.text()[:240].replace("\n", " ")
                except Exception as e:
                    body = f"<{e}>"
                print("JSON", r.status, len(r.body()) if r.ok else 0, r.url[:300], "|", body, flush=True)
        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)
            print("TITLE", page.title(), flush=True)
            for f in page.frames:
                if f.url and f.url != url:
                    print("FRAME", f.url[:300], flush=True)
        except Exception as e:
            print("ERR", e, flush=True)
        page.close()
    b.close()
