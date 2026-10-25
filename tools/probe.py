"""Connectivity probe run inside GitHub Actions (the dev sandbox has no internet).
Writes _probe/probe.json, which the workflow pushes to the `probe` branch."""
import json
import os
import re
import sys
import time
from urllib.parse import quote, urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import http  # noqa: E402
from engine.feeds import parse_feed  # noqa: E402

OUT = {"t": int(time.time()), "translate": {}, "air": {}, "feeds": {}, "pages": {}, "tg": {}}


def timed(fn):
    t0 = time.time()
    try:
        v = fn()
        return {"ok": True, "ms": int((time.time() - t0) * 1000), "v": v}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ms": int((time.time() - t0) * 1000), "err": f"{type(e).__name__}: {str(e)[:200]}"}


# ------------------------------------------------------------------ translation size limits
FA_LINE = "سخنگوی وزارت امور خارجه ایران روز یکشنبه در نشست خبری هفتگی درباره مذاکرات و تحولات منطقه توضیح داد"
EN_LINE = "Iran's foreign ministry spokesman on Sunday discussed the negotiations and regional developments at a briefing"


def g_post(texts, sl, tl):
    r = http.post("https://translate.googleapis.com/translate_a/single",
                  params={"client": "gtx", "sl": sl, "tl": tl, "dt": "t"},
                  data={"q": "\n".join(texts)}, timeout=25, retries=0)
    d = r.json()
    return "".join(s[0] for s in d[0] if s and s[0]).split("\n")


def g_t(texts, sl, tl):
    r = http.post("https://translate.googleapis.com/translate_a/t", params={"client": "gtx", "sl": sl, "tl": tl},
                  data=[("q", t) for t in texts], timeout=25, retries=0)
    d = r.json()
    return [x if isinstance(x, str) else x[0] for x in d]


def size_test(fn, line, sl, tl, n_chars):
    lines, total = [], 0
    i = 0
    while total < n_chars:
        s = f"{line} {i}"
        lines.append(s)
        total += len(s) + 1
        i += 1
    out = fn(lines, sl, tl)
    return {"lines": len(lines), "chars": total, "bytes": len("\n".join(lines).encode()), "out": len(out),
            "match": len(out) == len(lines), "sample": out[-1][:60] if out else None}


T = OUT["translate"]
for n in (1000, 2000, 3000, 4000, 5000, 8000):
    T[f"post_fa_{n}"] = timed(lambda n=n: size_test(g_post, FA_LINE, "fa", "en", n))
    T[f"post_en_{n}"] = timed(lambda n=n: size_test(g_post, EN_LINE, "en", "fa", n))
    T[f"t_fa_{n}"] = timed(lambda n=n: size_test(g_t, FA_LINE, "fa", "en", n))
# mixed-language batch with sl=auto (Hebrew + English)
T["auto_mixed"] = timed(lambda: g_post(["תודה לך הנשיא טראמפ על התמיכה", "Thank you for the support"], "auto", "fa"))
T["iw_single"] = timed(lambda: g_post(["תודה לך הנשיא טראמפ על התמיכה האדירה"], "iw", "fa"))
T["t_auto_mixed"] = timed(lambda: g_t(["תודה לך הנשיא טראמפ על התמיכה", "Thank you for the support"], "auto", "fa"))

# ------------------------------------------------------------------ ADS-B / OpenSky
AIR = {
    "opensky_big": "https://opensky-network.org/api/states/all?lamin=12&lomin=32&lamax=42&lomax=64",
    "opensky_iran": "https://opensky-network.org/api/states/all?lamin=25&lomin=44&lamax=40&lomax=63",
    "opensky_gulf": "https://opensky-network.org/api/states/all?lamin=22&lomin=47&lamax=30&lomax=57",
    "adsblol_mil": "https://api.adsb.lol/v2/mil",
    "adsbfi_mil": "https://opendata.adsb.fi/api/v2/mil",
    "adsblol_dubai": "https://api.adsb.lol/v2/point/25.25/55.36/250",
    "adsbfi_dubai": "https://opendata.adsb.fi/api/v3/lat/25.25/lon/55.36/dist/250",
    "adsblol_baghdad": "https://api.adsb.lol/v2/point/33.31/44.36/250",
    "adsblol_telaviv": "https://api.adsb.lol/v2/point/31.9/35.0/150",
}


def air(url):
    r = http.get(url, timeout=25, retries=0, headers={"Accept": "application/json"})
    d = r.json()
    ac = d.get("ac") or d.get("aircraft") or d.get("states") or []
    res = {"n": len(ac), "code": r.status_code, "rl": r.headers.get("x-rate-limit-remaining")}
    if "opensky" in url:
        res["ground"] = sum(1 for s in ac if s[8])
        res["countries"] = {}
        for s in ac:
            res["countries"][s[2]] = res["countries"].get(s[2], 0) + 1
        res["countries"] = dict(sorted(res["countries"].items(), key=lambda x: -x[1])[:8])
    else:
        reg = [a for a in ac if a.get("lat") is not None and 10 <= a["lat"] <= 42.5 and 24 <= a["lon"] <= 66]
        res["region"] = len(reg)
        res["types"] = sorted({a.get("t") or "?" for a in reg})[:30]
    return res


for k, u in AIR.items():
    OUT["air"][k] = timed(lambda u=u: air(u))
    time.sleep(1.2)

# ------------------------------------------------------------------ feeds
FEEDS = [
    "https://www.radiofarda.com/api/zrttpol-vomx-tpeoogpi", "https://www.radiofarda.com/api/zv_rmtl-vomx-tpeubomq",
    "https://www.radiofarda.com/api/zptimql-vomx-tpe_o_mi", "https://www.radiofarda.com/api/zpoqil-vomx-tpe_kip",
    "https://www.radiofarda.com/api/z-oqml-vomx-tpergim", "https://www.radiofarda.com/api/zboq_l-vomx-tpeqgi_",
    "https://www.radiofarda.com/api/zotqpvl-vomx-tpepoppr", "https://www.radiofarda.com/api/zgygmpl-vomx-tpe-rbm_",
    "https://www.radiofarda.com/api/zrqpml-vomx-tpeou_p", "https://www.radiofarda.com/api/zriqyl-vomx-tpeogiy",
    "https://www.radiofarda.com/api/zqqp_l-vomx-tpeiu_m", "https://www.radiofarda.com/api/zmoqpl-vomx-tpeykim",
    "https://www.radiofarda.com/api/zbbvmol-vomx-tpeqtkmp", "https://www.radiofarda.com/api/",
    "https://qna.org.qa/en/Pages/RSS-Feeds/General", "https://qna.org.qa/en/Pages/RSS-Feeds/Qatar",
    "https://www.independentpersian.com/rss.xml",
    "https://nournews.ir/fa/rss/allnews", "https://nournews.ir/en/rss/allnews",
    "https://www.wam.ae/en/rss/feed/g20ajfd0bv", "https://www.spa.gov.sa/en/rss",
    "https://www.iranintl.com/en/feed", "https://www.timesofisrael.com/feed/",
]


def feed(url):
    r = http.get(url, timeout=20, retries=0)
    es = parse_feed(r.content)
    dates = sorted([e.get("date") or "" for e in es])
    from engine.util import parse_date
    ts = sorted([parse_date(e.get("date")) or 0 for e in es])
    return {"code": r.status_code, "n": len(es), "newest": ts[-1] if ts else None,
            "age_h": round((time.time() - ts[-1]) / 3600, 1) if ts and ts[-1] else None,
            "title": r.text[:400].split("<title>")[1].split("</title>")[0][:80] if "<title>" in r.text[:400] else None,
            "first": (es[0].get("title") or "")[:80] if es else None, "dates": dates[-1:]}


for (u,), v, e in http.parallel(lambda t: timed(lambda: feed(t[0])), [(u,) for u in FEEDS], workers=8):
    OUT["feeds"][u] = v

ALT = re.compile(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', re.I)
FEEDLINK = re.compile(r'href="([^"]*(?:rss|feed)[^"]*)"', re.I)


def page(url):
    r = http.get(url, timeout=20, retries=0)
    txt = r.text
    return {"code": r.status_code, "len": len(txt),
            "feedlinks": [urljoin(r.url, m.group(1)) for m in FEEDLINK.finditer(txt)][:40]}


for u in ["https://nournews.ir/fa/feeds/", "https://www.radiofarda.com/rssfeeds"]:
    OUT["pages"][u] = timed(lambda u=u: page(u))

# ------------------------------------------------------------------ telegram
TG = ["bbcpersian", "iranintltv", "iranintl", "radiofarda", "indypersian", "tasnimnews", "farsna", "irna_1313",
      "irnanews", "isna94", "mehrnews", "iribnews_ir", "iribnews", "nournews_ir", "defapress_ir", "khabaronline_ir",
      "entekhab_ir", "entekhabnews", "dollar_tehran3bze"]


def tg(handle):
    r = http.get(f"https://t.me/s/{handle}", timeout=20, retries=0)
    t = r.text
    n = t.count('class="tgme_widget_message_text')
    dates = re.findall(r'<time datetime="([^"]+)"', t)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    first = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', t, re.S)
    return {"code": r.status_code, "posts": n, "last": dates[-1] if dates else None,
            "title": title.group(1)[:60] if title else None,
            "sample": re.sub(r"<[^>]+>", " ", first[-1])[:160] if first else None}


for (h,), v, e in http.parallel(lambda t: timed(lambda: tg(t[0])), [(h,) for h in TG], workers=6):
    OUT["tg"][h] = v

os.makedirs("_probe", exist_ok=True)
with open("_probe/probe.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("probe done", int(time.time()) - OUT["t"], "s")
