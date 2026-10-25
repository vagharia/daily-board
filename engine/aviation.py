"""Airspace warnings for the region from Safe Airspace (safeairspace.net, run by OPSGROUP): each country's
risk level, its current summary and the list of official warnings in force (state NOTAMs, EASA conflict
zone bulletins, FAA advisories) with issue and expiry dates. Refreshed about once an hour.

Raw NOTAM services (FAA NOTAM Search, DINS) refuse requests from GitHub's servers, which is why this
curated source is used: it lists the same official warnings and is updated as they are issued."""
import re
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Comment

from . import http
from .util import log, now

BASE = "https://safeairspace.net/"
COUNTRIES = {   # slug -> (fa, en, core)
    "iran": ("ایران", "Iran", True), "iraq": ("عراق", "Iraq", True), "israel": ("اسرائیل", "Israel", True),
    "lebanon": ("لبنان", "Lebanon", True), "syria": ("سوریه", "Syria", False), "jordan": ("اردن", "Jordan", False),
    "saudi-arabia": ("عربستان", "Saudi Arabia", True), "kuwait": ("کویت", "Kuwait", True),
    "bahrain": ("بحرین", "Bahrain", True), "qatar": ("قطر", "Qatar", True),
    "united-arab-emirates": ("امارات", "UAE", True), "oman": ("عمان", "Oman", True), "yemen": ("یمن", "Yemen", True),
}
LEVELS = {"one": 1, "two": 2, "three": 3, "four": 4}
LEVEL_TXT = {1: ("پرواز نکنید", "Do not fly"), 2: ("خطر وجود دارد", "Danger exists"), 3: ("احتیاط", "Caution"),
             4: ("اطلاع", "Information")}
REFRESH = 55 * 60


def _date(s):
    s = (s or "").strip()
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return int(datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return None


def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_country(html, slug):
    soup = BeautifulSoup(html, "lxml")
    out = {"id": slug, "level": None, "summary": "", "warnings": []}
    h = soup.select_one("h3[class*=page-country-summary-risk-level]")
    if h:
        m = re.search(r"Risk Level:\s*(\w+)", h.get_text(" ", strip=True), re.I)
        if m:
            out["level"] = LEVELS.get(m.group(1).lower()) or (int(m.group(1)) if m.group(1).isdigit() else None)
    body = soup.select_one(".page-country-summary-content")
    if body:
        first = []
        for node in body.children:
            if getattr(node, "name", None) == "br" and first and first[-1] == "\n":
                break                                          # the first paragraph ends at <br><br>
            first.append("\n" if getattr(node, "name", None) == "br" else
                         (node.get_text(" ") if hasattr(node, "get_text") else str(node)))
        out["summary"] = _clean("".join(first))[:600]
    table = None
    head = soup.find(string=re.compile(r"Current warnings list", re.I))
    if head:
        table = head.find_parent().find_next("table")
    if table:
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            a = tds[1].find("a")
            w = {"src": _clean(tds[0].get_text()), "ref": _clean(tds[1].get_text()),
                 "issued": _date(tds[2].get_text()), "until": _clean(tds[3].get_text()),
                 "url": a["href"] if a and a.get("href", "").startswith("http") else ""}
            w["until_t"] = _date(w["until"])
            nxt = tr.next_sibling
            while nxt is not None and not getattr(nxt, "name", None) and not isinstance(nxt, Comment):
                nxt = nxt.next_sibling
            if isinstance(nxt, Comment):                       # the plain-language line sits in a comment
                note = BeautifulSoup(str(nxt), "lxml").get_text(" ", strip=True)
                w["note"] = _clean(note)[:300]
            if w["src"] or w["ref"]:
                out["warnings"].append(w)
    out["warnings"].sort(key=lambda w: -(w["issued"] or 0))
    return out


def parse_feed(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for d in soup.select("div.feed-item[data-feed-item-country]"):
        a = d.select_one("a[href]")
        out.append({"country": d.get("data-feed-item-country"), "level": int(d.get("data-feed-item-warn-level") or 0),
                    "date": _clean((d.select_one(".feed-item-level") or d).get_text()) if d.select_one(".feed-item-level")
                    else "", "text": _clean((d.select_one(".feed-item-summary") or d).get_text())[:300],
                    "url": a["href"] if a else ""})
    return out


def run(state, translate=None):
    """state caches the result; returns the public 'aviation' block for signals.json."""
    t = now()
    if state.get("data") and t - state.get("fetched", 0) < REFRESH:
        return state["data"]
    prev = {c["id"]: c for c in (state.get("data") or {}).get("countries", [])}
    countries, errors = [], []

    def fetch(slug):
        r = http.get(BASE + slug + "/", timeout=25, retries=1)
        return parse_country(r.text, slug)

    for slug, res, err in http.parallel(fetch, list(COUNTRIES), workers=4):
        fa, en, core = COUNTRIES[slug]
        if err is not None or not res or res.get("level") is None:
            errors.append(f"{slug}: {str(err)[:60] if err else 'no level found'}")
            if slug in prev:
                countries.append(prev[slug])
            continue
        p = prev.get(slug) or {}
        res.update(fa=fa, en=en, core=core, url=BASE + slug + "/")
        res["level_fa"], res["level_en"] = LEVEL_TXT.get(res["level"], ("", ""))
        res["changed"] = p.get("changed")
        if p.get("level") and p["level"] != res["level"]:
            res["changed"] = {"t": t, "from": p["level"], "to": res["level"]}
        res["summary_fa"] = p.get("summary_fa") if p.get("summary") == res["summary"] else None
        countries.append(res)
    if translate:
        todo = [c for c in countries if c.get("summary") and not c.get("summary_fa")]
        notes = {w["note"] for c in countries for w in c.get("warnings", [])[:4] if w.get("note")}
        res = translate([c["summary"] for c in todo] + sorted(notes))
        for c in todo:
            c["summary_fa"] = res.get(c["summary"])
        for c in countries:
            for w in c.get("warnings", [])[:4]:
                if w.get("note") and res.get(w["note"]):
                    w["note_fa"] = res[w["note"]]
    countries.sort(key=lambda c: (c.get("level") or 9, -max([w["issued"] or 0 for w in c["warnings"]] or [0])))
    for c in countries:
        c["warnings"] = c["warnings"][:6]
        c["new"] = sum(1 for w in c["warnings"] if w.get("issued") and t - w["issued"] <= 3 * 86400)
    data = {"updated": t, "status": "ok" if countries else "fail", "errors": errors[:6], "countries": countries,
            "source": "Safe Airspace (OPSGROUP)"}
    if countries:
        state.update(fetched=t, data=data)
    log(f"aviation: {len(countries)} countries, levels "
        f"{ {c['id']: c['level'] for c in countries} }, errors={len(errors)}")
    return data


def recent_warnings(av, t, window):
    """Official warnings issued within `window` seconds for core countries (for the airspace light)."""
    out = []
    for c in (av or {}).get("countries", []):
        if not c.get("core"):
            continue
        for w in c.get("warnings", []):
            if w.get("issued") and t - w["issued"] <= window:
                out.append((c, w))
        ch = c.get("changed")
        if ch and t - ch["t"] <= window and ch["to"] < ch["from"]:        # risk level went up (1 is the worst)
            out.append((c, {"src": "Safe Airspace", "ref": f"level {ch['from']}→{ch['to']}", "issued": ch["t"]}))
    return out


if __name__ == "__main__":
    import sys
    print(parse_country(open(sys.argv[1]).read(), "iran"))
    time.sleep(0)
