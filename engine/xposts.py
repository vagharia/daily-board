"""Posts from credible accounts: on X (found through reputable media that cite or embed them, plus the public
embedded timelines of some official accounts, read sparingly because X limits them), Trump's Truth Social
posts, and the public Telegram channels that officials and leading journalists run. X's own API is paid-only,
so this is deliberately selective. Only posts about the region and the conflict are kept."""
import hashlib
import json
import math
import os
import re
from datetime import datetime

from bs4 import BeautifulSoup

from . import config, http
from .classify import classify
from .cluster import is_core
from .feeds import parse_feed
from .lexicon import COUNTRIES_RX, match_keys
from .relevance import relevance_en, relevance_fa, ukraine_war
from .util import clean_summary, fa_norm, has_fa, load_json, log, now, parse_date

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
    "presssec": ("geo", "سخنگوی کاخ سفید", "White House Press Secretary"),
    "usadarfarsi": ("geo", "وزارت خارجه آمریکا به فارسی", "US State Dept in Persian"),
    "us5thfleet": ("geo", "ناوگان پنجم آمریکا", "US 5th Fleet"),
    "usafcent": ("geo", "نیروی هوایی سنتکام", "US Air Forces Central"),
    "usun": ("geo", "نمایندگی آمریکا در سازمان ملل", "US Mission to the UN"),
    "statedept_nea": ("geo", "دفتر خاور نزدیک وزارت خارجه آمریکا", "State Dept Near East bureau"),
    "usambisrael": ("geo", "سفیر آمریکا در اسرائیل", "US Ambassador to Israel"),
    "govmikehuckabee": ("geo", "سفیر آمریکا در اسرائیل", "US Ambassador to Israel"),
    # --- Israel
    "netanyahu": ("geo", "نخست‌وزیر اسرائیل", "Israeli PM"),
    "israelipm": ("geo", "نخست‌وزیر اسرائیل", "Israeli PM"),
    "idf": ("geo", "ارتش اسرائیل", "IDF"),
    "israel_katz": ("geo", "وزیر دفاع اسرائیل", "Israeli Defense Minister"),
    "israelmfa": ("geo", "وزارت خارجه اسرائیل", "Israel MFA"),
    "gidonsaar": ("geo", "وزیر خارجه اسرائیل", "Israeli Foreign Minister"),
    "ltc_shoshani": ("geo", "سخنگوی بین‌المللی ارتش اسرائیل", "IDF international spokesperson"),
    "avichayadraee": ("geo", "سخنگوی عربی ارتش اسرائیل", "IDF Arabic spokesperson"),
    "israelpersian": ("geo", "اسرائیل به فارسی", "Israel in Persian"),
    "israel_mod": ("geo", "وزارت دفاع اسرائیل", "Israel Ministry of Defense"),
    "dannydanon": ("geo", "سفیر اسرائیل در سازمان ملل", "Israel's UN ambassador"),
    # --- Iran
    "khamenei_ir": ("geo", "رهبر ایران", "Iran's Supreme Leader"),
    "khamenei_fa": ("geo", "رهبر ایران", "Iran's Supreme Leader"),
    "drpezeshkian": ("geo", "رئیس‌جمهور ایران", "Iran's President"),
    "araghchi": ("geo", "وزیر خارجه ایران", "Iran's Foreign Minister"),
    "irimfa_spox": ("geo", "سخنگوی وزارت خارجه ایران", "Iran MFA spokesperson"),
    "irimfa_en": ("geo", "وزارت خارجه ایران", "Iran MFA"),
    "iran_un": ("geo", "نمایندگی ایران در سازمان ملل", "Iran's UN mission"),
    "irimfa": ("geo", "وزارت خارجه ایران", "Iran MFA"),
    "mb_ghalibaf": ("geo", "رئیس مجلس ایران", "Iran's Parliament Speaker"),
    "jzarif": ("geo", "محمدجواد ظریف", "Javad Zarif"),
    "gharibabadi": ("geo", "معاون وزیر خارجه ایران", "Iran's deputy foreign minister"),
    "takhtravanchi": ("geo", "معاون وزیر خارجه ایران", "Iran's deputy foreign minister"),
    # --- Russia
    "mfa_russia": ("geo", "وزارت خارجه روسیه", "Russian MFA"),
    "mid_rf": ("geo", "وزارت خارجه روسیه", "Russian MFA"),
    "kremlinrussia_e": ("geo", "کرملین", "Kremlin"),
    "kremlinrussia": ("geo", "کرملین", "Kremlin"),
    "medvedevrussiae": ("geo", "مدودف، نایب‌رئیس شورای امنیت روسیه", "Medvedev, Russian Security Council"),
    "russiaun": ("geo", "نمایندگی روسیه در سازمان ملل", "Russia's UN mission"),
    "amb_ulyanov": ("geo", "نماینده روسیه در وین (آژانس)", "Russia's envoy in Vienna (IAEA)"),
    "dpol_un": ("geo", "معاون نماینده روسیه در سازمان ملل", "Russia's deputy UN envoy"),
    # --- China
    "mfa_china": ("geo", "وزارت خارجه چین", "China MFA"),
    "spokespersonchn": ("geo", "سخنگوی وزارت خارجه چین", "China MFA spokesperson"),
    "spoxchn_maoning": ("geo", "مائو نینگ، سخنگوی وزارت خارجه چین", "Mao Ning, China MFA spokesperson"),
    "spoxchn_linjian": ("geo", "لین جیان، سخنگوی وزارت خارجه چین", "Lin Jian, China MFA spokesperson"),
    "chinamission2un": ("geo", "نمایندگی چین در سازمان ملل", "China's UN mission"),
    "globaltimesnews": ("geo", "گلوبال تایمز (رسانه دولتی چین)", "Global Times (Chinese state media)"),
    "huxijin_gt": ("geo", "هو شی‌جین، گلوبال تایمز", "Hu Xijin, Global Times"),
    "xhnews": ("geo", "خبرگزاری شینهوا", "Xinhua"),
    "cgtnofficial": ("geo", "سی‌جی‌تی‌ان (رسانه دولتی چین)", "CGTN (Chinese state media)"),
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
    "lrozen": ("geo", "روزنامه‌نگار", "Journalist"),
    "jengriffinfnc": ("geo", "خبرنگار فاکس نیوز", "Fox News reporter"),
    "natashabertrand": ("geo", "خبرنگار سی‌ان‌ان", "CNN reporter"),
    "idreesali114": ("geo", "خبرنگار رویترز", "Reuters reporter"),
    "phildstewart": ("geo", "خبرنگار رویترز", "Reuters reporter"),
    "amichaistein1": ("geo", "خبرنگار دیپلماتیک کان", "Kan diplomatic correspondent"),
    "ckubenbc": ("geo", "خبرنگار امنیت ملی ان‌بی‌سی", "NBC national security reporter"),
    "jacquiheinrich": ("geo", "خبرنگار کاخ سفید فاکس نیوز", "Fox News White House correspondent"),
    "kylieatwood": ("geo", "خبرنگار سی‌ان‌ان", "CNN correspondent"),
    "jongambrellap": ("geo", "خبرنگار آسوشیتدپرس در خلیج فارس", "AP Gulf & Iran correspondent"),
    "ericschmittnyt": ("geo", "خبرنگار امنیت ملی نیویورک تایمز", "NYT national security correspondent"),
    "helenecooper": ("geo", "خبرنگار پنتاگون نیویورک تایمز", "NYT Pentagon correspondent"),
    "laraseligman": ("geo", "خبرنگار پنتاگون وال‌استریت ژورنال", "WSJ Pentagon reporter"),
    "glubold": ("geo", "خبرنگار امنیت ملی", "National security reporter"),
    "alexwardvox": ("geo", "خبرنگار امنیت ملی وال‌استریت ژورنال", "WSJ national security reporter"),
    "jonathanvswan": ("geo", "خبرنگار کاخ سفید نیویورک تایمز", "NYT White House reporter"),
    "jdiamond1": ("geo", "خبرنگار کاخ سفید سی‌ان‌ان", "CNN White House correspondent"),
    "danlamothe": ("geo", "خبرنگار نظامی واشنگتن پست", "Washington Post military reporter"),
    "apdiplowriter": ("geo", "خبرنگار دیپلماتیک آسوشیتدپرس", "AP diplomatic writer"),
    "humeyra_pamuk": ("geo", "خبرنگار وزارت خارجه رویترز", "Reuters State Dept correspondent"),
    "jmhansler": ("geo", "خبرنگار وزارت خارجه سی‌ان‌ان", "CNN State Dept reporter"),
    "manniefabian": ("geo", "خبرنگار نظامی تایمز اسرائیل", "Times of Israel military correspondent"),
    "amit_segal": ("geo", "تحلیلگر سیاسی شبکه ۱۲ اسرائیل", "Channel 12 political analyst"),
    "talshalev1": ("geo", "خبرنگار سیاسی والا", "Walla political correspondent"),
    "yossi_melman": ("geo", "روزنامه‌نگار امنیتی اسرائیلی", "Israeli intelligence journalist"),
    "yanivkubovich": ("geo", "خبرنگار نظامی هاآرتص", "Haaretz military correspondent"),
    "doron_kadosh": ("geo", "خبرنگار نظامی رادیو ارتش اسرائیل", "Army Radio military correspondent"),
    "orheller": ("geo", "خبرنگار نظامی شبکه ۱۳ اسرائیل", "Channel 13 military correspondent"),
    "nirdvori": ("geo", "خبرنگار نظامی شبکه ۱۲ اسرائیل", "Channel 12 military correspondent"),
    "aviissacharoff": ("geo", "روزنامه‌نگار اسرائیلی", "Israeli journalist"),
    "bencaspit": ("geo", "تحلیلگر سیاسی معاریو", "Maariv political analyst"),
    "arik3000": ("geo", "خبرنگار سیاسی اسرائیل هیوم", "Israel Hayom diplomatic correspondent"),
    "lahavharkov": ("geo", "خبرنگار جوئیش اینسایدر", "Jewish Insider correspondent"),
    "sfrantzman": ("geo", "تحلیلگر جروزالم پست", "Jerusalem Post analyst"),
    "yonahjeremybob": ("geo", "خبرنگار اطلاعاتی جروزالم پست", "Jerusalem Post intelligence correspondent"),
    "itayblumental": ("geo", "خبرنگار نظامی کان", "Kan military correspondent"),
    "jasonrezaian": ("geo", "روزنامه‌نگار واشنگتن پست", "Washington Post journalist"),
    "negarmortazavi": ("geo", "روزنامه‌نگار", "Journalist"),
    "gesfandiari": ("geo", "روزنامه‌نگار رادیو اروپای آزاد", "RFE/RL journalist"),
    "sanamvakil": ("geo", "تحلیلگر چتم هاوس", "Chatham House analyst"),
    "alihashem_tv": ("geo", "خبرنگار الجزیره", "Al Jazeera correspondent"),
    "abasaslani": ("geo", "تحلیلگر ایرانی", "Iranian analyst"),
    "s_m_marandi": ("geo", "استاد دانشگاه تهران", "University of Tehran professor"),
    "aghplt": ("geo", "روزنامه‌نگار", "Iranian journalist"),
    "hoseindalirian": ("geo", "خبرنگار نظامی", "Military journalist"),
    "hdagres": ("geo", "تحلیلگر آتلانتیک کانسیل", "Atlantic Council analyst"),
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
    "behnamben": ("geo", "تحلیلگر FDD", "FDD analyst"),
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
    "lloydslist": ("econ", "لویدز لیست", "Lloyd's List"),
    "reuterscommods": ("econ", "رویترز کامادیتی", "Reuters Commodities"),
}

# accounts no longer followed: their stored posts and pending look-ups are dropped
UNFOLLOWED = {"farnazfassihi"}

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
            if (not rel and not econ) or ukraine_war(text[:200], text[200:900]):
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


def update(state, candidates, truth_posts, extra_posts=()):
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
    todo = [tid for tid, e in cand.items() if tid not in posts and not e.get("failed")
            and e["h"].lower() not in UNFOLLOWED]
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
        if cand[tid].get("own") and not _on_topic(p):
            cand[tid]["failed"] = "off topic"       # linked from the author's own channel, not cited by a story
            continue
        who = WHITELIST.get(p["h"].lower()) or WHITELIST.get(cand[tid]["h"].lower())
        if not who or p["h"].lower() in UNFOLLOWED:
            cand[tid]["failed"] = "not followed"
            continue
        seg, rfa, ren = who
        p.update(seg=seg, role_fa=rfa, role_en=ren)
        posts[tid] = p
        stats["ok"] += 1
    for p in list(truth_posts) + list(extra_posts):
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


# public Telegram channels of officials and journalists (checked to be active): channel -> (role fa, role en, name)
TG_ACCOUNTS = {
    "BarakRavid1": ("خبرنگار اکسیوس", "Axios reporter", "Barak Ravid"),
    "amitsegal": ("تحلیلگر سیاسی شبکه ۱۲ اسرائیل", "Channel 12 political analyst", "Amit Segal"),
    "manniefabian": ("خبرنگار نظامی تایمز اسرائیل", "Times of Israel military correspondent", "Emanuel Fabian"),
    "Doron_Kadosh": ("خبرنگار نظامی رادیو ارتش اسرائیل", "Army Radio military correspondent", "Doron Kadosh"),
    "idfofficial": ("ارتش اسرائیل", "IDF", "Israel Defense Forces"),
    # mostly links to his interviews and tweets; the tweets are looked up on X
    "s_m_marandi": ("استاد دانشگاه تهران", "University of Tehran professor", "Seyed Mohammad Marandi"),
}
_TWEET_LINK = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/(\w{1,15})/status/(\d{8,25})")
# official X accounts whose public embedded timeline is current (government-labelled accounts; for others, Iranian
# officials included, X serves an old snapshot); X refuses this page after a few requests from a shared server
# address, so a few are read per full round, in turn, with a pause after a refusal
X_TIMELINES = ["MFA_China", "mfa_russia", "Chinamission2un", "SpokespersonCHN", "KremlinRussia_E", "Amb_Ulyanov",
               "MedvedevRussiaE", "RussiaUN", "gidonsaar", "CENTCOM", "DeptofWar", "StateDept", "IsraeliPM", "IDF",
               "IsraelMFA"]
X_PER_ROUND = 3
X_COOLDOWN = 3600
POST_MAX_AGE = 3 * 86400
_SCRIPTS = [("iw", re.compile(r"[\u0590-\u05FF]")), ("ru", re.compile(r"[\u0400-\u04FF]")),
            ("zh-CN", re.compile(r"[\u4E00-\u9FFF]")), ("ar", re.compile(r"[\u0600-\u06FF]")),
            ("en", re.compile(r"[A-Za-z]"))]
_FA_ONLY = re.compile(r"[\u067E\u0686\u0698\u06AF\u06A9\u06CC]")      # پ چ ژ گ ک ی


def _lang(text):
    """The script most of the post is written in (Persian told apart from Arabic by its own letters)."""
    counts = {code: len(rx.findall(text or "")) for code, rx in _SCRIPTS}
    code = max(counts, key=counts.get)
    if not counts[code]:
        return "en"
    if code == "ar" and len(_FA_ONLY.findall(text)) >= 2:
        return "fa"
    return code


def _views(s):
    m = re.match(r"([\d.]+)\s*([KM]?)", (s or "").strip())
    if not m:
        return 0
    return int(float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6}[m.group(2)])


# Russian and Chinese official accounts: what they say about the Middle East counts even outside the core theatre
POWER_ACCOUNTS = {"mfa_russia", "mid_rf", "kremlinrussia_e", "kremlinrussia", "medvedevrussiae", "russiaun",
                  "amb_ulyanov", "dpol_un", "mfa_china", "spokespersonchn", "spoxchn_maoning", "spoxchn_linjian",
                  "chinamission2un"}
_REGION = re.compile(r"\b(middle east|west asia|iran\w*|tehran|israel\w*|gaza|lebanon|lebanese|hezbollah|yemen\w*"
                     r"|houthis?|syria\w*|persian gulf|gulf states|hormuz|palestin\w*)\b", re.I)


def on_topic(en, power=False):
    """About the conflict itself: relevant by the news rules and touching the core theatre (Iran, the Persian Gulf
    states, Iraq, Yemen, Lebanon, Hormuz…), so West Bank arrests or a Jordanian church attack stay out. Russia and
    China on the Middle East (their own accounts, or a post quoting Putin, Lavrov, Wang Yi…) are kept too."""
    if not en or not relevance_en(en[:220], en[220:900])[1]:
        return False
    it = {"lang": "en", "en_ti": en[:220], "en_su": en[220:900]}
    classify(it)
    it["ctry"] = sorted(set(it["ctry"]) | set(match_keys(COUNTRIES_RX, en[:900], "")))
    if is_core(it):
        return True
    return (power or "powers" in it["flags"]) and bool(_REGION.search(en[:900]))


_REGION_FA = re.compile(r"خاورمیانه|غرب آسیا|ایران|تهران|اسرائیل|اسراییل|غزه|لبنان|حزب\s*الله|یمن|حوثی|سوریه"
                        r"|خلیج فارس|هرمز|فلسطین")


def on_topic_fa(text, power=False):
    """The same test for a Persian post, by the Persian rules (as Persian news reports are judged)."""
    if not text:
        return False
    t, s = text[:220], text[220:900]
    if not relevance_fa(t, s)[1]:
        return False
    it = {"lang": "fa", "ti": t, "su": s}
    classify(it)
    it["ctry"] = sorted(set(it["ctry"]) | set(match_keys(COUNTRIES_RX, "", text[:900])))
    if is_core(it):
        return True
    return (power or "powers" in it["flags"]) and bool(_REGION_FA.search(fa_norm(text[:900])))


def _on_topic(p):
    power = (p.get("h") or "").lower() in POWER_ACCOUNTS
    if p.get("lang") == "fa":
        return on_topic_fa(p["text"], power)
    return on_topic(p["text"] if p.get("lang") == "en" else p.get("en"), power)


def _ukraine(p):
    if p.get("lang") == "fa":
        return ukraine_war(p["text"][:220], p["text"][220:900], "fa")
    en = p["text"] if p.get("lang") == "en" else p.get("en") or ""
    return ukraine_war(en[:220], en[220:900])


def prune_off_topic(state):
    """Drop stored posts that the current rules no longer keep: channels no longer followed, posts read from
    channels and timelines that are off topic, and anything about the Russia-Ukraine war."""
    posts, cand = state.get("posts", {}), state.get("cand", {})
    gone = []
    for k, p in posts.items():
        if (p.get("platform") == "telegram" and p.get("h") not in TG_ACCOUNTS) or \
                (p.get("h") or "").lower() in UNFOLLOWED:
            gone.append(k)
        elif (p.get("platform") == "telegram" or p.get("via") == "timeline") and not _on_topic(p):
            gone.append(k)
        elif _ukraine(p):
            gone.append(k)
    for k in gone:
        posts.pop(k, None)
        if k in cand:
            cand[k]["failed"] = "off topic"         # not looked up again
    return len(gone)


def _own_tweet(state, handle, tid):
    """A tweet the author links from their own channel: looked up on X like a cited one, kept if on topic."""
    cand = state.setdefault("cand", {})
    if tid not in cand and tid not in state.get("posts", {}):
        cand[tid] = {"h": handle, "cites": [], "t": now(), "own": True}


def _relevant(posts, tr):
    """Keep posts about the region and the conflict: Persian ones by the Persian rules, the rest on their English
    text (translated when needed)."""
    todo = {}
    for p in posts:
        if p["lang"] not in ("en", "fa") and not p.get("en"):
            todo.setdefault(p["lang"], []).append(p["text"])
    for lg, texts in todo.items():
        res = tr.translate_many(texts, lg, "en") if tr else {}
        for p in posts:
            if p["lang"] == lg and res.get(p["text"]):
                p["en"] = res[p["text"]]
    return [p for p in posts if _on_topic(p)]


def telegram_posts(state, tr):
    """Recent posts from TG_ACCOUNTS that are about the region; posts already judged are skipped."""
    seen = state.setdefault("tg_seen", {})
    t0, fresh = now(), []

    def fetch(ch):
        r = http.get(f"https://t.me/s/{ch}", timeout=20, retries=1)
        return BeautifulSoup(r.content, "lxml")

    for ch, soup, err in http.parallel(fetch, list(TG_ACCOUNTS), workers=5):
        if err is not None or soup is None:
            continue
        rfa, ren, name = TG_ACCOUNTS[ch]
        img = soup.select_one('meta[property="og:image"]')
        avatar = img["content"] if img and img.get("content", "").startswith("https://") else None
        for div in soup.select("div.tgme_widget_message[data-post]"):
            pid = "tg:" + div["data-post"]
            tm = div.select_one("time[datetime]")
            node = div.select_one(".tgme_widget_message_text")
            if pid in seen or not tm or not node:
                continue
            seen[pid] = t0
            ts = parse_date(tm["datetime"]) or t0
            if t0 - ts > POST_MAX_AGE:
                continue
            for br in node.find_all("br"):
                br.replace_with("\n")
            text = re.sub(r"[ \t]+", " ", node.get_text("")).strip()
            link = _TWEET_LINK.search(text)
            if link and link.group(1).lower() in WHITELIST and len(_TWEET_LINK.sub("", text).strip()) < 25:
                _own_tweet(state, link.group(1), link.group(2))     # just a link to a tweet: read the tweet itself
                continue
            if len(text) < 25:
                continue
            media = []
            ph = div.select_one(".tgme_widget_message_photo_wrap")
            m = re.search(r"background-image:url\('([^']+)'\)", (ph.get("style") or "") if ph else "")
            if m:
                media.append({"type": "photo", "url": m.group(1)})
            views = div.select_one(".tgme_widget_message_views")
            fresh.append({
                "id": pid, "platform": "telegram", "h": ch, "n": name, "img": avatar, "v": False, "t": ts,
                "text": text[:1500], "lang": _lang(text), "media": media,
                "likes": _views(views.get_text() if views else "") // 20, "replies": 0,
                "url": "https://t.me/" + div["data-post"], "seg": "geo", "role_fa": rfa, "role_en": ren,
            })
    for k in [k for k, v in seen.items() if t0 - v > 8 * 86400]:
        seen.pop(k, None)
    kept = _relevant(fresh, tr)
    log(f"telegram accounts: {len(fresh)} new posts, {len(kept)} about the region")
    return kept


def _tweet(x, t0):
    """A post from an embedded-timeline entry, or None for retweets, replies and old posts."""
    text = x.get("full_text") or x.get("text") or ""
    if not x.get("id_str") or text.startswith("RT @") or x.get("in_reply_to_status_id_str"):
        return None
    try:
        ts = int(datetime.strptime(x.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y").timestamp())
    except ValueError:
        return None
    if t0 - ts > POST_MAX_AGE:
        return None
    ent = x.get("entities") or {}
    for u in ent.get("urls", []):
        if u.get("url") and u.get("display_url"):
            text = text.replace(u["url"], u["display_url"])
    text = re.sub(r"\s*https://t\.co/\w+\s*$", "", text).strip()
    media = []
    for m in (x.get("extended_entities") or ent).get("media", []) or []:
        if m.get("type") == "photo":
            media.append({"type": "photo", "url": m.get("media_url_https")})
    u = x.get("user") or {}
    return {"id": x["id_str"], "platform": "x", "h": u.get("screen_name"), "n": u.get("name"),
            "img": u.get("profile_image_url_https"), "v": bool(u.get("verified") or u.get("is_blue_verified")),
            "t": ts, "text": text, "lang": _lang(text), "media": media[:2],
            "likes": int(x.get("favorite_count") or 0), "replies": int(x.get("reply_count") or 0),
            "url": f"https://x.com/{u.get('screen_name')}/status/{x['id_str']}"}


def x_timelines(state, tr):
    """A few official accounts' recent posts per call, in turn; stops for an hour once X refuses."""
    st = state.setdefault("xt", {"next": 0, "cool": 0})
    t0 = now()
    if t0 < st.get("cool", 0):
        return [], "cooling down"
    got, status = [], "ok"
    for _ in range(X_PER_ROUND):
        h = X_TIMELINES[st["next"] % len(X_TIMELINES)]
        try:
            r = http.get(f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}", timeout=20, retries=0,
                         headers={"Accept": "text/html"})
        except Exception as e:  # noqa: BLE001
            if "429" in str(e):
                st["cool"] = t0 + X_COOLDOWN
                status = "rate limited"
                break
            st["next"] += 1
            continue
        st["next"] += 1
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text or "", re.S)
        if not m:
            continue
        try:
            entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
        except (KeyError, TypeError, ValueError):
            continue
        for e in entries:
            p = _tweet((e.get("content") or {}).get("tweet") or {}, t0) if e.get("type") == "tweet" else None
            if p and p["h"] and p["h"].lower() in WHITELIST:
                seg, rfa, ren = WHITELIST[p["h"].lower()]
                p.update(seg=seg, role_fa=rfa, role_en=ren, via="timeline")
                got.append(p)
    kept = _relevant(got, tr)
    log(f"x timelines: {status}, {len(got)} recent posts, {len(kept)} about the region")
    return kept, status


# posts read off screenshots of X that the owner sends; see engine/xmanual/README.md
MANUAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xmanual", "posts.json")


def manual_posts():
    """The posts in engine/xmanual/posts.json, shaped like any other post in the X tab."""
    data = load_json(MANUAL, None) or {}
    out = []
    for p in data.get("posts", []):
        h = str(p.get("h") or "").lstrip("@")
        ts = parse_date(p["t"]) if isinstance(p.get("t"), str) else p.get("t")
        text = (p.get("text") or "").strip()
        if not h or not text or not ts or now() - ts > POST_MAX_AGE:
            continue
        who = WHITELIST.get(h.lower())
        pid = "m" + hashlib.sha1(f"{h.lower()}|{ts}|{text[:80]}".encode("utf-8")).hexdigest()[:15]
        out.append({
            "id": pid, "platform": "x", "h": h, "n": p.get("n") or h, "img": None, "v": False, "t": ts,
            "text": text, "fa": p.get("fa") or text, "en": p.get("en") or text,
            "lang": "fa" if has_fa(text) else "en", "media": [], "likes": 0, "replies": 0,
            "url": p.get("url") or f"https://x.com/{h}", "seg": p.get("seg") or (who[0] if who else "geo"),
            "role_fa": who[1] if who else p.get("role_fa", ""), "role_en": who[2] if who else p.get("role_en", ""),
        })
    return out


def ranked(posts):
    def score(p):
        age_h = max(0.0, (now() - p["t"]) / 3600)
        return math.log10(p.get("likes", 0) + 1) + 0.9 * p.get("cites", 0) - age_h / 24 + (1.5 if p["platform"] == "truth" else 0)
    return sorted(posts.values(), key=score, reverse=True)
