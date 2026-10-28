"""Live results of Israel's Knesset election (27 Oct 2026) for the pinned story.

Source: the Central Elections Committee's own results site (votes26.bechirot.gov.il), the official count. It sits
behind a bot check that only a real browser passes, so the page is read with a headless Chromium. It lists every
list's valid votes; seats are worked out here the way the law does it (Knesset Elections Law, s. 81-82):
lists under 3.25% of the valid votes get none; the 120 seats go by the Bader-Ofer method (largest averages), with
lists that signed a surplus-vote agreement counted as one for the remainder seats and then splitting theirs.

Writes election.json and pushes it to the `election` branch (its own branch, so it never races the news data).
The count is official only when the committee publishes the final results; the story stays up 24 hours after that.

    python -m engine.election            # loop: a round every 5 minutes, ROUNDS rounds
"""
import json
import os
import re
import calendar
import subprocess
import sys
import time

URL = "https://votes26.bechirot.gov.il/nationalresults"
THRESHOLD = 0.0325
SEATS = 120
MAJORITY = 61
# the law's own deadline for publishing the final results in the official gazette (Reshumot): 4 Nov 2026
LEGAL_FINAL = 1793829600          # 2026-11-05 00:00 Israel time
KEEP_AFTER_FINAL = 24 * 3600
BRANCH = "election"

# lists by their ballot letters: Persian and English names, leader, bloc
# blocs: "bibi" (Netanyahu's coalition), "change" (the opposition led by Eisenkot), "arab", None (other)
LISTS = {
    "מחל": ("لیکود", "Likud", "نتانیاهو", "Netanyahu", "bibi"),
    "דרך": ("یاشار!", "Yashar!", "آیزنکوت", "Eisenkot", "change"),
    "ודם": ("فهرست مشترک", "Joint List", "", "", "arab"),
    "רק": ("با هم", "Together", "بنت", "Bennett", "change"),
    "אמת": ("دموکرات‌ها", "The Democrats", "گولان", "Golan", "change"),
    "ג": ("یهدوت هتورا", "United Torah Judaism", "", "", "bibi"),
    "ל": ("اسرائیل بیتنو", "Yisrael Beiteinu", "لیبرمن", "Liberman", "change"),
    "שס": ("شاس", "Shas", "درعی", "Deri", "bibi"),
    "ב": ("عوتصما یهودیت", "Otzma Yehudit", "بن‌گویر", "Ben Gvir", "bibi"),
    "ט": ("صهیونیسم مذهبی", "Religious Zionism", "اسموتریچ", "Smotrich", "bibi"),
    "עם": ("رعام", "Ra'am", "منصور عباس", "Mansour Abbas", "arab"),
    "די": ("ذخیره‌ها و اقتصادی", "Reservists & Economic", "هندل", "Hendel", None),
    "ך": ("عمخا یسرائیل", "Amcha Yisrael", "وینتر", "Winter", None),
    "ני": ("نوعام", "Noam", "", "", "bibi"),
}
# surplus-vote agreements signed by the deadline (ynet, 2026)
SURPLUS = [("רק", "ל"), ("דרך", "אמת"), ("ודם", "עם"), ("מחל", "ט"), ("שס", "ג")]

ROW = re.compile(r"^(?P<name>[^\t\n]{2,160})\t(?P<let>[^\t\n]{1,6})\t(?P<pct>[\d.]+)%\t\s*\n\s*(?P<votes>[\d,]+)\s*$", re.M)
ASOF = re.compile(r"תוצאות נכון ל-\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})")


def _num(label, text):
    m = re.search(re.escape(label) + r"\s*\n\s*([\d,]+)", text)
    return int(m.group(1).replace(",", "")) if m else None


def parse(text):
    """The national results page's text -> counts and lists. None if it isn't the results page."""
    rows = [{"let": m["let"].strip(), "name": m["name"].strip(), "pct": float(m["pct"]),
             "votes": int(m["votes"].replace(",", ""))} for m in ROW.finditer(text)]
    if len(rows) < 5:
        return None
    a = ASOF.search(text)
    asof = None
    if a:
        d, mo, y, h, mi = map(int, a.groups())
        # Israel is UTC+2 in winter (from the last Sunday of October), UTC+3 in summer; the count runs in winter
        asof = calendar.timegm((y, mo, d, h, mi, 0)) - 2 * 3600
    # "final results" as the committee's own heading, not the standing notice that they are due by 4 November
    head = text.split("תוצאות ארציות", 2)[-1][:400] if "תוצאות ארציות" in text else text[:400]
    final = bool(re.search(r"תוצאות\s+סופיות|התוצאות\s+הסופיות", head))
    return {"asof": asof, "final": final, "eligible": _num("מספר בעלי זכות בחירה", text),
            "votes": _num("קולות עד עתה", text), "boxes": _num("קלפיות עד עתה", text),
            "valid": _num("קולות כשרים עד עתה", text), "invalid": _num("קולות פסולים עד עתה", text), "lists": rows}


def _largest_averages(units, seats, total):
    """units: {key: (votes, seats so far)}; hands out `total - assigned` seats one by one to the highest average."""
    s = dict(seats)
    while sum(s.values()) < total:
        k = max(units, key=lambda k: (units[k] / (s[k] + 1), units[k]))
        s[k] += 1
    return s


def allocate(lists):
    """Seats per list letter by the Bader-Ofer method with surplus-vote agreements."""
    valid = sum(x["votes"] for x in lists)
    if not valid:
        return {}
    passing = {x["let"]: x["votes"] for x in lists if x["votes"] >= THRESHOLD * valid}
    if not passing:
        return {}
    quota = sum(passing.values()) / SEATS
    base = {k: int(v // quota) for k, v in passing.items()}
    # agreement pairs (both over the threshold) compete for the remainder as one unit
    unit_of = {k: k for k in passing}
    for a, b in SURPLUS:
        if a in passing and b in passing:
            unit_of[a] = unit_of[b] = a + "+" + b
    uv, us = {}, {}
    for k, v in passing.items():
        u = unit_of[k]
        uv[u] = uv.get(u, 0) + v
        us[u] = us.get(u, 0) + base[k]
    us = _largest_averages(uv, us, SEATS)
    out = {}
    for u, n in us.items():
        members = [k for k in passing if unit_of[k] == u]
        if len(members) == 1:
            out[members[0]] = n
            continue
        q = uv[u] / n
        inner = {k: int(passing[k] // q) for k in members}
        inner = _largest_averages({k: passing[k] for k in members}, inner, n)
        out.update(inner)
    return out


def build(parsed, prev=None, t=None):
    t = t or int(time.time())
    lists = parsed["lists"]
    seats = allocate(lists)
    valid = sum(x["votes"] for x in lists) or 1
    rows = []
    for x in sorted(lists, key=lambda x: -x["votes"]):
        fa, en, lfa, len_, bloc = LISTS.get(x["let"], (None, None, "", "", None))
        rows.append({"let": x["let"], "he": x["name"], "fa": fa, "en": en, "lfa": lfa, "len": len_, "bloc": bloc,
                     "votes": x["votes"], "pct": round(100 * x["votes"] / valid, 2), "seats": seats.get(x["let"], 0)})
    blocs = {b: sum(r["seats"] for r in rows if r["bloc"] == b) for b in ("bibi", "change", "arab")}
    blocs["other"] = SEATS - sum(blocs.values())
    prev = prev or {}
    final_t = prev.get("final_t")
    if not final_t and (parsed["final"] or t >= LEGAL_FINAL):
        final_t = t
    return {"v": 1, "updated": t, "asof": parsed["asof"], "source": URL, "eligible": parsed["eligible"],
            "votes": parsed["votes"], "valid": parsed["valid"], "boxes": parsed["boxes"],
            "turnout": round(100 * parsed["votes"] / parsed["eligible"], 1) if parsed["eligible"] and parsed["votes"] else None,
            "threshold": THRESHOLD * 100, "majority": MAJORITY, "seats_total": SEATS, "blocs": blocs,
            "lists": rows, "final": bool(final_t), "final_t": final_t,
            "until": final_t + KEEP_AFTER_FINAL if final_t else None}


def fetch_text():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(locale="he-IL", viewport={"width": 1280, "height": 900},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                       "Chrome/130.0.0.0 Safari/537.36")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=90000)
        for _ in range(20):                       # the bot check reloads the page once it is solved
            if "קולות כשרים לרשימה" in page.inner_text("body"):
                break
            page.wait_for_timeout(1500)
        text = page.inner_text("body")
        b.close()
    return text


def _git(*args, env=None):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True,
                          env={**os.environ, **(env or {})}).stdout.strip()


def publish(doc):
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=json.dumps(doc, ensure_ascii=False),
                          check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "mktree"], input=f"100644 blob {blob}\telection.json\n", check=True,
                          capture_output=True, text=True).stdout.strip()
    commit = _git("commit-tree", tree, "-m", "election " + time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()))
    _git("push", "-f", "origin", f"{commit}:refs/heads/{BRANCH}")


def previous():
    try:
        _git("fetch", "-q", "origin", BRANCH)
        return json.loads(_git("show", f"origin/{BRANCH}:election.json"))
    except Exception:  # noqa: BLE001 - first run
        return None


def main():
    rounds = int(os.environ.get("ELECTION_ROUNDS", "6"))
    prev = previous()
    for i in range(rounds):
        t0 = time.time()
        if prev and prev.get("until") and t0 > prev["until"]:
            print("results final and their day is over: nothing more to do")
            open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a").write("done=1\n")
            return
        try:
            parsed = parse(fetch_text())
            if parsed:
                doc = build(parsed, prev)
                key = lambda d: (d.get("asof"), d.get("votes"), d.get("final"))  # noqa: E731
                if not prev or key(doc) != key(prev) or t0 - prev.get("updated", 0) > 1800:
                    publish(doc)
                    print(f"round {i + 1}: published asof={doc['asof']} votes={doc['votes']} blocs={doc['blocs']}")
                else:
                    print(f"round {i + 1}: no change")
                prev = doc
            else:
                print(f"round {i + 1}: results page not read")
        except Exception as e:  # noqa: BLE001
            print(f"round {i + 1}: failed: {str(e)[:300]}", file=sys.stderr)
        if i < rounds - 1:
            time.sleep(max(0, 300 - (time.time() - t0)))


if __name__ == "__main__":
    main()
