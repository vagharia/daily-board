"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Tests translation endpoints, ADS-B providers and fallbacks for failing sources and writes
_probe/probe.json, which the workflow pushes to the `probe` branch."""
import json
import os
import re
import sys
import time
from urllib.parse import quote, urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402
from engine.feeds import parse_feed  # noqa: E402

OUT = {"t": int(time.time()), "translate": {}, "air": {}, "sources": {}, "tg": {}, "bing": {}, "gn": {}}
EN = ["Iran warns of retaliation after strike near the Strait of Hormuz",
      "US envoy says talks with Tehran could resume next week",
      "Oil prices jump as tanker traffic through the Persian Gulf slows"]
FA = ["ایران درباره حمله در نزدیکی تنگه هرمز هشدار داد", "قیمت نفت پس از کاهش تردد نفتکش‌ها افزایش یافت"]


def timed(fn):
    t0 = time.time()
    try:
        v = fn()
        return {"ok": True, "ms": int((time.time() - t0) * 1000), "v": v}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ms": int((time.time() - t0) * 1000), "err": f"{type(e).__name__}: {str(e)[:200]}"}


# ------------------------------------------------------------------ translation
def g_single_post(texts, sl="en", tl="fa", host="translate.googleapis.com", client="gtx"):
    r = http.post(f"https://{host}/translate_a/single", params={"client": client, "sl": sl, "tl": tl, "dt": "t"},
                  data={"q": "\n".join(texts)}, timeout=20, retries=0)
    d = r.json()
    out = "".join(s[0] for s in d[0] if s and s[0])
    return out.split("\n")


def g_single_get(texts, sl="en", tl="fa"):
    r = http.get("https://translate.googleapis.com/translate_a/single",
                 params={"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": "\n".join(texts)}, timeout=20, retries=0)
    d = r.json()
    return "".join(s[0] for s in d[0] if s and s[0]).split("\n")


def g_t(texts, sl="en", tl="fa", host="translate.googleapis.com", client="gtx"):
    q = "&".join("q=" + quote(t) for t in texts)
    r = http.get(f"https://{host}/translate_a/t?client={client}&sl={sl}&tl={tl}&{q}", timeout=20, retries=0)
    d = r.json()
    return [x if isinstance(x, str) else x[0] for x in d] if isinstance(d, list) else d


def g_mobile(text, sl="en", tl="fa"):
    r = http.get("https://translate.google.com/m", params={"sl": sl, "tl": tl, "q": text, "hl": "en"},
                 timeout=20, retries=0)
    m = re.search(r'class="result-container">(.*?)</div>', r.text, re.S)
    return m.group(1) if m else ("no result-container; " + r.text[:200])


def ms_edge(texts, sl="en", tl="fa"):
    tok = http.get("https://edge.microsoft.com/translate/auth", timeout=15, retries=0).text.strip()
    r = http.post("https://api-edge.cognitive.microsofttranslator.com/translate",
                  params={"from": sl, "to": tl, "api-version": "3.0"},
                  headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "Accept": "*/*"},
                  json_body=[{"Text": t} for t in texts], timeout=20, retries=0)
    return {"tok": tok[:12] + "…", "out": [x["translations"][0]["text"] for x in r.json()]}


def mymemory(text, sl="en", tl="fa"):
    r = http.get("https://api.mymemory.translated.net/get", params={"q": text, "langpair": f"{sl}|{tl}"},
                 timeout=20, retries=0)
    d = r.json()
    return {"t": d.get("responseData", {}).get("translatedText"), "status": d.get("responseStatus"),
            "quota": d.get("quotaFinished")}


def lingva(text, sl="en", tl="fa"):
    r = http.get(f"https://lingva.ml/api/v1/{sl}/{tl}/{quote(text)}", timeout=20, retries=0)
    return r.json().get("translation")


def burst():
    """How many sequential 12-line requests before Google throttles?"""
    lines = [f"{EN[i % 3]} ({i})" for i in range(12)]
    codes = []
    for i in range(30):
        t0 = time.time()
        try:
            out = g_single_post(lines)
            codes.append(f"ok{len(out)}:{int((time.time() - t0) * 1000)}")
        except Exception as e:  # noqa: BLE001
            codes.append(str(e)[:40])
    return codes


T = OUT["translate"]
T["single_post_en_fa"] = timed(lambda: g_single_post(EN))
T["single_post_fa_en"] = timed(lambda: g_single_post(FA, "fa", "en"))
T["single_get"] = timed(lambda: g_single_get(EN))
T["t_gtx"] = timed(lambda: g_t(EN))
T["t_clients5"] = timed(lambda: g_t(EN, host="clients5.google.com", client="dict-chrome-ex"))
T["single_clients5"] = timed(lambda: g_single_post(EN, host="clients5.google.com", client="dict-chrome-ex"))
T["mobile"] = timed(lambda: g_mobile(EN[0]))
T["ms_edge"] = timed(lambda: ms_edge(EN))
T["ms_edge_fa_en"] = timed(lambda: ms_edge(FA, "fa", "en"))
T["mymemory"] = timed(lambda: mymemory(EN[0]))
T["lingva"] = timed(lambda: lingva(EN[0]))
T["burst"] = timed(burst)
T["after_burst"] = timed(lambda: g_single_post(EN))
T["after_burst_t"] = timed(lambda: g_t(EN))

# ------------------------------------------------------------------ ADS-B providers
AIR = {
    "airplanes_mil": "https://api.airplanes.live/v2/mil",
    "airplanes_point": "https://api.airplanes.live/v2/point/35.69/51.39/250",
    "adsblol_mil": "https://api.adsb.lol/v2/mil",
    "adsblol_point": "https://api.adsb.lol/v2/point/35.69/51.39/250",
    "adsblol_latlon": "https://api.adsb.lol/v2/lat/35.69/lon/51.39/dist/250",
    "adsbfi_mil": "https://opendata.adsb.fi/api/v2/mil",
    "adsbfi_v3": "https://opendata.adsb.fi/api/v3/lat/35.69/lon/51.39/dist/250",
    "adsbfi_v2": "https://opendata.adsb.fi/api/v2/lat/35.69/lon/51.39/dist/250",
    "adsbone_mil": "https://api.adsb.one/v2/mil",
    "adsbone_point": "https://api.adsb.one/v2/point/35.69/51.39/250",
    "opensky_bbox": "https://opensky-network.org/api/states/all?lamin=24&lomin=44&lamax=40&lomax=63",
}


def air(url):
    r = http.get(url, timeout=25, retries=0, headers={"Accept": "application/json"})
    d = r.json()
    ac = d.get("ac") or d.get("aircraft") or d.get("states") or []
    return {"n": len(ac), "keys": list(d.keys())[:8], "sample": (ac[0] if ac else None) if "opensky" not in url else
            (ac[0][:8] if ac else None)}


for k, u in AIR.items():
    OUT["air"][k] = timed(lambda u=u: air(u))
    time.sleep(1.1)

# ------------------------------------------------------------------ sources
FAILING = {
    "lorient": ["https://today.lorientlejour.com/", "https://today.lorientlejour.com/rss",
                "https://www.lorientlejour.com/rss"],
    "spa": ["https://www.spa.gov.sa/en", "https://www.spa.gov.sa/rss"],
    "wam": ["https://www.wam.ae/en", "https://www.wam.ae/en/rss"],
    "qna": ["https://www.qna.org.qa/en", "https://www.qna.org.qa/en/RSS-Feeds"],
    "ona": ["https://omannews.gov.om/", "https://omannews.gov.om/rss"],
    "kuna": ["https://www.kuna.net.kw/Default.aspx?language=en", "https://www.kuna.net.kw/rss"],
    "bna": ["https://www.bna.bh/en/", "https://www.bna.bh/en/rss"],
    "centcom": ["https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=808&max=15",
                "https://www.centcom.mil/MEDIA/PRESS-RELEASES/"],
    "radiofarda": ["https://www.radiofarda.com/", "https://www.radiofarda.com/rssfeeds"],
    "indypersian": ["https://www.independentpersian.com/", "https://www.independentpersian.com/rss.xml"],
    "tasnim": ["https://www.tasnimnews.com/fa/rss/feed/0/7/0/", "https://www.tasnimnews.com/en/rss/feed/0/7/0/"],
    "iribnews": ["https://www.iribnews.ir/fa/rss/allnews"],
    "nournews": ["https://nournews.ir/fa/rss", "https://nournews.ir/", "https://nournews.ir/fa"],
    "cnn": ["http://rss.cnn.com/rss/edition_meast.rss"],
}
ALT = re.compile(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', re.I)
HREF = re.compile(r'href="([^"]+)"')
FEEDLINK = re.compile(r'href="([^"]*(?:rss|feed|/api/z)[^"]*)"', re.I)


def src(url):
    r = http.get(url, timeout=20, retries=0)
    body = r.content
    entries = []
    try:
        entries = parse_feed(body)
    except Exception:  # noqa: BLE001
        pass
    res = {"code": r.status_code, "ctype": r.headers.get("content-type", "")[:40], "len": len(body),
           "final": r.url[:120], "entries": len(entries)}
    if entries:
        res["first"] = {k: (entries[0].get(k) or "")[:90] for k in ("title", "link", "date")}
    else:
        txt = r.text
        alts = [HREF.search(m.group(0)).group(1) for m in ALT.finditer(txt) if HREF.search(m.group(0))]
        links = list(dict.fromkeys(m.group(1) for m in FEEDLINK.finditer(txt)))[:15]
        res["alts"] = [urljoin(r.url, a) for a in alts][:8]
        res["feedlinks"] = [urljoin(r.url, a) for a in links]
        res["head"] = re.sub(r"\s+", " ", txt[:300])
    return res


def run_sources():
    tasks = [(sid, u) for sid, us in FAILING.items() for u in us]
    for (sid, u), v, e in http.parallel(lambda t: timed(lambda: src(t[1])), tasks, workers=10):
        OUT["sources"].setdefault(sid, {})[u] = v


run_sources()

# telegram channels
from engine.sources import SOURCES  # noqa: E402

TG = sorted({h for s in SOURCES for h in s.get("tg", [])})


def tg(handle):
    r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=0)
    t = r.text
    n = t.count('class="tgme_widget_message_text')
    dates = re.findall(r'<time datetime="([^"]+)"', t)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    return {"code": r.status_code, "posts": n, "last": dates[-1] if dates else None,
            "title": title.group(1)[:60] if title else None}


for (h,), v, e in http.parallel(lambda t: timed(lambda: tg(t[0])), [(h,) for h in TG], workers=6):
    OUT["tg"][h] = v

# Bing news + google news for failing domains
DOMS = ["spa.gov.sa", "wam.ae", "qna.org.qa", "omannews.gov.om", "kuna.net.kw", "bna.bh", "centcom.mil",
        "lorientlejour.com", "radiofarda.com", "independentpersian.com", "nournews.ir", "iribnews.ir",
        "tasnimnews.com"]


def feedcount(url):
    r = http.get(url, timeout=20, retries=0)
    es = parse_feed(r.content)
    return {"code": r.status_code, "n": len(es), "first": {k: (es[0].get(k) or "")[:100] for k in
                                                         ("title", "link", "date", "source_url")} if es else None}


for d in DOMS:
    OUT["bing"][d] = timed(lambda d=d: feedcount(f"https://www.bing.com/news/search?q={quote('site:' + d)}&format=rss"))
    time.sleep(0.6)
    OUT["gn"][d] = timed(lambda d=d: feedcount(
        f"https://news.google.com/rss/search?q={quote('site:' + d + ' when:2d')}&hl=en-US&gl=US&ceid=US:en"))
    time.sleep(1.0)

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("probe done", int(time.time()) - OUT["t"], "s")
