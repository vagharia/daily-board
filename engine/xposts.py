"""Posts on X from credible accounts (found through reputable media that cite or embed them)
and Trump's Truth Social posts. X's own API is paid-only, so this is deliberately selective."""
import math
import re

from . import config, http
from .feeds import parse_feed
from .relevance import relevance_en
from .util import clean_summary, has_fa, log, now, parse_date

# handle (lowercase) -> (segment, role fa, role en)
WHITELIST = {
    # --- US officials
    "realdonaldtrump": ("geo", "رئیس‌جمهور آمریکا", "US President"),
    "potus": ("geo", "رئیس‌جمهور آمریکا", "US President"),
    "whitehouse": ("geo", "کاخ سفید", "White House"),
    "secrubio": ("geo", "وزیر خارجه آمریکا", "US Secretary of State"),
    "marcorubio": ("geo", "وزیر خارجه آمریکا", "US Secretary of State"),
    "jdvance": ("geo", "معاون رئیس‌جمهور آمریکا", "US Vice President"),
    "vp": ("geo", "معاون رئیس‌جمهور آمریکا", "US Vice President"),
    "secscottbessent": ("econ", "وزیر خزانه‌داری آمریکا", "US Treasury Secretary"),
    "ustreasury": ("econ", "خزانه‌داری آمریکا", "US Treasury"),
    "petehegseth": ("geo", "وزیر جنگ آمریکا", "US Secretary of War"),
    "secwar": ("geo", "وزیر جنگ آمریکا", "US Secretary of War"),
    "deptofwar": ("geo", "وزارت جنگ آمریکا", "US Department of War"),
    "centcom": ("geo", "سنتکام", "US Central Command"),
    "statedept": ("geo", "وزارت خارجه آمریکا", "US State Department"),
    "statedeptspox": ("geo", "سخنگوی وزارت خارجه آمریکا", "State Dept spokesperson"),
    "stevewitkoff": ("geo", "فرستاده ویژه آمریکا", "US special envoy"),
    "sepeacemissions": ("geo", "فرستاده ویژه آمریکا", "US special envoy"),
    # --- Israel
    "netanyahu": ("geo", "نخست‌وزیر اسرائیل", "Israeli PM"),
    "israelipm": ("geo", "نخست‌وزیر اسرائیل", "Israeli PM"),
    "idf": ("geo", "ارتش اسرائیل", "IDF"),
    "israel_katz": ("geo", "وزیر جنگ اسرائیل", "Israeli Defense Minister"),
    "israelmfa": ("geo", "وزارت خارجه اسرائیل", "Israel MFA"),
    # --- Iran
    "khamenei_ir": ("geo", "رهبر ایران", "Iran's Supreme Leader"),
    "khamenei_fa": ("geo", "رهبر ایران", "Iran's Supreme Leader"),
    "drpezeshkian": ("geo", "رئیس‌جمهور ایران", "Iran's President"),
    "araghchi": ("geo", "وزیر خارجه ایران", "Iran's Foreign Minister"),
    "irimfa_spox": ("geo", "سخنگوی وزارت خارجه ایران", "Iran MFA spokesperson"),
    "irimfa_en": ("geo", "وزارت خارجه ایران", "Iran MFA"),
    "iran_un": ("geo", "نمایندگی ایران در سازمان ملل", "Iran's UN mission"),
    # --- Persian Gulf & international
    "ksamofaen": ("geo", "وزارت خارجه عربستان", "Saudi MFA"),
    "mofaqatar_en": ("geo", "وزارت خارجه قطر", "Qatar MFA"),
    "mofauae": ("geo", "وزارت خارجه امارات", "UAE MFA"),
    "badralbusaidi": ("geo", "وزیر خارجه عمان", "Omani Foreign Minister"),
    "iaeaorg": ("geo", "آژانس انرژی اتمی", "IAEA"),
    "rafaelmgrossi": ("geo", "مدیرکل آژانس", "IAEA Director General"),
    "antonioguterres": ("geo", "دبیرکل سازمان ملل", "UN Secretary-General"),
    "emmanuelmacron": ("geo", "رئیس‌جمهور فرانسه", "French President"),
    "keir_starmer": ("geo", "نخست‌وزیر بریتانیا", "UK Prime Minister"),
    "kajakallas": ("geo", "مسئول سیاست خارجی اروپا", "EU foreign policy chief"),
    # --- journalists & outlets
    "barakravid": ("geo", "خبرنگار اکسیوس", "Axios reporter"),
    "laurnorman": ("geo", "خبرنگار وال‌استریت ژورنال", "WSJ reporter"),
    "farnazfassihi": ("geo", "خبرنگار نیویورک تایمز", "NYT reporter"),
    "lrozen": ("geo", "روزنامه‌نگار", "Journalist"),
    "jengriffinfnc": ("geo", "خبرنگار فاکس نیوز", "Fox News reporter"),
    "natashabertrand": ("geo", "خبرنگار سی‌ان‌ان", "CNN reporter"),
    "idreesali114": ("geo", "خبرنگار رویترز", "Reuters reporter"),
    "phildstewart": ("geo", "خبرنگار رویترز", "Reuters reporter"),
    "amichaistein1": ("geo", "خبرنگار اسرائیلی", "Israeli reporter"),
    "bnonews": ("geo", "خبر فوری", "Breaking news"),
    "reuters": ("geo", "رویترز", "Reuters"),
    "ap": ("geo", "آسوشیتدپرس", "AP"),
    "afp": ("geo", "خبرگزاری فرانسه", "AFP"),
    "bbcbreaking": ("geo", "بی‌بی‌سی", "BBC"),
    "ajenglish": ("geo", "الجزیره", "Al Jazeera"),
    "timesofisrael": ("geo", "تایمز اسرائیل", "Times of Israel"),
    # --- analysts
    "alivaez": ("geo", "تحلیلگر گروه بحران", "Crisis Group analyst"),
    "ellie_geranmayeh": ("geo", "تحلیلگر شورای روابط خارجی اروپا", "ECFR analyst"),
    "ksadjadpour": ("geo", "تحلیلگر کارنگی", "Carnegie analyst"),
    "tparsi": ("geo", "تحلیلگر موسسه کوئینسی", "Quincy Institute"),
    "mdubowitz": ("geo", "مدیر FDD", "FDD chief executive"),
    "behnambentaleblu": ("geo", "تحلیلگر FDD", "FDD analyst"),
    "jasonmbrodsky": ("geo", "تحلیلگر UANI", "UANI analyst"),
    "alexvatanka": ("geo", "تحلیلگر موسسه خاورمیانه", "MEI analyst"),
    "thestudyofwar": ("geo", "اندیشکده مطالعات جنگ", "ISW"),
    "criticalthreats": ("geo", "کریتیکال تِرِتس", "Critical Threats"),
    # --- oil & gold
    "tankertrackers": ("econ", "ردیاب نفتکش‌ها", "TankerTrackers"),
    "samir_madani": ("econ", "ردیاب نفتکش‌ها", "TankerTrackers co-founder"),
    "javierblas": ("econ", "ستون‌نویس انرژی بلومبرگ", "Bloomberg energy columnist"),
    "amenabakr": ("econ", "تحلیلگر نفت", "Oil analyst"),
    "rory_johnston": ("econ", "تحلیلگر نفت", "Oil market analyst"),
    "staunovo": ("econ", "تحلیلگر کالا UBS", "UBS commodity analyst"),
    "ole_s_hansen": ("econ", "تحلیلگر کالا ساکسو", "Saxo commodity strategist"),
    "kitconewsnow": ("econ", "کیتکو", "Kitco News"),
    "goldcouncil": ("econ", "شورای جهانی طلا", "World Gold Council"),
    "jkempenergy": ("econ", "تحلیلگر انرژی", "Energy analyst"),
    "clyderussell": ("econ", "ستون‌نویس رویترز", "Reuters columnist"),
    "anasalhajji": ("econ", "تحلیلگر انرژی", "Energy analyst"),
    "iea": ("econ", "آژانس بین‌المللی انرژی", "IEA"),
    "opecsecretariat": ("econ", "اوپک", "OPEC"),
    "eiagov": ("econ", "اداره اطلاعات انرژی آمریکا", "US EIA"),
    "federalreserve": ("econ", "فدرال رزرو", "Federal Reserve"),
    "kpler": ("econ", "کپلر", "Kpler"),
    "vortexa": ("econ", "ورتکسا", "Vortexa"),
    "lloyds_list": ("econ", "لویدز لیست", "Lloyd's List"),
    "reuterscommods": ("econ", "رویترز کامادیتی", "Reuters Commodities"),
}

ECON = re.compile(r"\b(oil|crude|brent|wti|opec|barrels?|gold|bullion|fed$|federal reserve|inflation|tariffs?|gasoline"
                  r"|lng|refiner\w*|tanker rates|freight|insurance|commodit\w+|dollar)\b", re.I)
# Trump talks about prices at every rally; only energy, gold and rates count as market news from him
ECON_TRUTH = re.compile(r"\b(oil|crude|opec|energy|gasoline|gas prices?|drill\w*|gold|federal reserve|the fed"
                        r"|interest rates?|rate cuts?|tariffs? on (china|oil))\b", re.I)


def _js_radix36(value: float) -> str:
    """Port of V8's DoubleToRadixCString(value, 36)."""
    import math as _m
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    radix = 36
    integer = _m.floor(value)
    fraction = value - integer
    delta = max(0.5 * (_m.nextafter(value, _m.inf) - value), _m.nextafter(0.0, 1.0))
    frac_digits = []
    if fraction >= delta:
        while True:
            fraction *= radix
            delta *= radix
            digit = int(fraction)
            frac_digits.append(digit)
            fraction -= digit
            if fraction > 0.5 or (fraction == 0.5 and (digit & 1)):
                if fraction + delta > 1:
                    # round up with carry
                    i = len(frac_digits) - 1
                    while True:
                        if i < 0:
                            integer += 1
                            frac_digits = []
                            break
                        if frac_digits[i] + 1 < radix:
                            frac_digits[i] += 1
                            frac_digits = frac_digits[: i + 1]
                            break
                        i -= 1
                    break
            if not fraction >= delta:
                break
    ip = int(integer)
    int_digits = ""
    while True:
        ip, rem = divmod(ip, radix)
        int_digits = chars[rem] + int_digits
        if ip == 0:
            break
    s = int_digits
    if frac_digits:
        s += "." + "".join(chars[d] for d in frac_digits)
    return s


def syndication_token(tweet_id: str) -> str:
    v = (int(tweet_id) / 1e15) * math.pi
    return re.sub(r"(0+|\.)", "", _js_radix36(v))


def fetch_post(tweet_id: str):
    r = http.get("https://cdn.syndication.twimg.com/tweet-result",
                 params={"id": tweet_id, "lang": "en", "token": syndication_token(tweet_id)},
                 timeout=15, retries=1, headers={"Accept": "application/json"})
    d = r.json()
    if not d or d.get("__typename") == "TweetTombstone" or "user" not in d:
        return None
    text = d.get("text", "")
    for u in (d.get("entities") or {}).get("urls", []):
        if u.get("url") and u.get("display_url"):
            text = text.replace(u["url"], u["display_url"])
    for m in (d.get("entities") or {}).get("media", []) or []:
        if m.get("url"):
            text = text.replace(m["url"], "")
    text = re.sub(r"\s*https://t\.co/\w+\s*$", "", text).strip()
    media = []
    for m in d.get("mediaDetails") or []:
        if m.get("type") == "photo":
            media.append({"type": "photo", "url": m.get("media_url_https")})
        elif m.get("type") in ("video", "animated_gif"):
            vs = [v for v in (m.get("video_info") or {}).get("variants", []) if v.get("content_type") == "video/mp4"]
            vs.sort(key=lambda v: v.get("bitrate", 0))
            if vs:
                pick = vs[min(1, len(vs) - 1)]
                media.append({"type": "video", "url": pick["url"], "poster": m.get("media_url_https")})
    u = d["user"]
    return {
        "id": tweet_id,
        "platform": "x",
        "h": u.get("screen_name"),
        "n": u.get("name"),
        "img": u.get("profile_image_url_https"),
        "v": bool(u.get("is_blue_verified") or u.get("verified")),
        "t": parse_date(d.get("created_at")) or now(),
        "text": text,
        "lang": "fa" if has_fa(text) else (d.get("lang") or "en"),
        "media": media[:2],
        "likes": int(d.get("favorite_count") or 0),
        "replies": int(d.get("conversation_count") or 0),
        "url": f"https://x.com/{u.get('screen_name')}/status/{tweet_id}",
    }


def truth_social(source):
    """Trump's posts via a public archive feed."""
    out = []
    for url in source["feeds"]:
        try:
            r = http.get(url, timeout=20, retries=1)
        except Exception as e:  # noqa: BLE001
            log("truth social:", str(e)[:80])
            continue
        for e in parse_feed(r.content):
            text = clean_summary(e.get("content") or e.get("summary") or e.get("title"))
            if not text or len(text) < 12 or re.match(r"^\s*(RT:|RT @)", text):
                continue
            if len(re.sub(r"https?://\S+", "", text).strip()) < 12:
                continue                            # a bare link or a reposted video
            ts = parse_date(e.get("date")) or now()
            sc, rel = relevance_en(text[:200], text[200:900])
            econ = bool(ECON_TRUTH.search(text))
            if not rel and not econ:
                continue
            pid = "t" + re.sub(r"\D", "", e.get("link") or "")[-18:] if re.search(r"\d", e.get("link") or "") \
                else "t" + str(abs(hash(text)) % 10**12)
            out.append({
                "id": pid, "platform": "truth", "h": "realDonaldTrump", "n": "Donald J. Trump",
                "img": None, "v": True, "t": ts, "text": text[:1200], "lang": "en", "media": [],
                "likes": 0, "replies": 0, "url": e.get("link") or "https://truthsocial.com/@realDonaldTrump",
                "seg": "geo" if rel else "econ", "role_fa": "رئیس‌جمهور آمریکا", "role_en": "US President",
            })
        if out:
            break
    return out


def update(state, candidates, truth_posts):
    """state: {'posts': {id: post}, 'cand': {id: {'h':.., 'cites': [cluster ids]}}}"""
    posts = state.setdefault("posts", {})
    cand = state.setdefault("cand", {})
    for handle, tid, cid in candidates:
        h = handle.lower()
        if h not in WHITELIST:
            continue
        e = cand.setdefault(tid, {"h": handle, "cites": [], "t": now()})
        if cid and cid not in e["cites"]:
            e["cites"].append(cid)
    todo = [tid for tid, e in cand.items() if tid not in posts and not e.get("failed")]
    todo.sort(key=lambda t: -len(cand[t]["cites"]))
    stats = {"looked_up": 0, "ok": 0, "failed": 0}
    for tid in todo[: config.MAX_TWEET_LOOKUPS]:
        stats["looked_up"] += 1
        try:
            p = fetch_post(tid)
        except Exception as e:  # noqa: BLE001
            cand[tid]["failed"] = str(e)[:60]
            stats["failed"] += 1
            continue
        if not p:
            cand[tid]["failed"] = "unavailable"
            continue
        seg, rfa, ren = WHITELIST.get(p["h"].lower(), WHITELIST.get(cand[tid]["h"].lower()))
        p.update(seg=seg, role_fa=rfa, role_en=ren)
        posts[tid] = p
        stats["ok"] += 1
    for p in truth_posts:
        if p["id"] not in posts:
            posts[p["id"]] = p
    for tid, p in posts.items():
        p["cites"] = len(cand.get(tid, {}).get("cites", []))
    # prune
    cut = now() - config.WEEK
    for tid in [k for k, p in posts.items() if p["t"] < cut]:
        posts.pop(tid, None)
    for tid in [k for k, e in cand.items() if e.get("t", 0) < cut - 86400]:
        cand.pop(tid, None)
    return stats


def ranked(posts):
    def score(p):
        age_h = max(0.0, (now() - p["t"]) / 3600)
        return math.log10(p.get("likes", 0) + 1) + 0.9 * p.get("cites", 0) - age_h / 24 + (1.5 if p["platform"] == "truth" else 0)
    return sorted(posts.values(), key=score, reverse=True)
