"""Decide whether an item is about the Iran / US / Israel / Persian Gulf conflict space."""
import re

from .lexicon import en_rx, fa_rx
from .util import fa_norm

# ------------------------------------------------------------------ English
EN_CORE = en_rx([
    "iran", "tehran", "irgc", "revolutionary guard", "khamenei", "hormuz", "persian gulf", "gulf of oman",
    "israel", "idf$", "netanyahu", "hezbollah", "houthi", "centcom", "natanz", "fordow", "fordo$", "bushehr",
    "kharg", "bandar abbas", "araghchi", "araqchi", "pezeshkian", "larijani", "vahidi", "quds force", "mossad",
    "tel aviv", "ayatollah", "basij", "isfahan",
])
EN_MID = en_rx([
    "middle east", "mideast", "gulf states", "gulf countries", "gulf arab", "saudi", "riyadh", "uae$", "emirat",
    "abu dhabi", "qatar", "doha", "oman$", "omani", "muscat", "bahrain", "kuwait", "iraq", "baghdad", "erbil",
    "syria", "damascus", "lebanon", "lebanese", "beirut", "yemen", "sanaa", "hodeidah", "red sea", "bab el-mandeb",
    "bab al-mandab", "gaza", "hamas", "west bank", "jordan$", "enrichment", "uranium", "iaea", "nuclear deal",
    "jcpoa", "snapback", "e3$", "tanker", "crude", "brent", "opec", "strait$", "jerusalem", "haifa", "dimona", "eilat",
    "ukmto",
])
EN_SEC = en_rx([
    "strike$", "strikes$", "struck$", "airstrike", "air strike", "missile", "drone", "attack", "war$", "wars$",
    "warfare", "ceasefire", "cease-fire", "truce", "sanction", "military", "troops", "navy$", "naval", "warship",
    "aircraft carrier", "carrier strike", "bomber", "retaliat", "escalat", "threat", "warn", "nuclear", "blockade",
    "airspace", "evacuat", "intercept", "explosion", "blast$", "killed", "invasion", "ultimatum", "mobiliz",
    "deploy", "talks$", "negotiat", "envoy", "diplomat", "oil price", "shipping",
])
EN_US = en_rx(["trump", "rubio", "vance$", "bessent", "hegseth", "witkoff", "pentagon", "white house",
               "state department", "treasury"])
EN_NOISE = en_rx([
    "football", "soccer", "world cup", "fifa", "olympic", "wrestling", "volleyball", "futsal", "basketball",
    "tournament", "goalkeeper", "medal", "box office", "film festival", "movie", "concert", "fashion", "recipe",
    "grand prix", "formula 1", "cricket", "tennis", "chess", "oscars", "eurovision", "horoscope",
])

# ------------------------------------------------------------------ Persian
FA_CORE = fa_rx([
    "آمریکا", "امریکا", "ایالات متحده", "اسرائیل", "اسراییل", "رژیم صهیونیستی", "صهیونیست", "تل آویو",
    "هرمز", "خلیج فارس", "دریای عمان", "سنتکام", "ترامپ", "روبیو", "ونس$", "بسنت", "هگست", "هگزث", "ویتکاف",
    "ویتکوف", "نتانیاهو", "حزب الله", "انصارالله", "حوثی", "پنتاگون", "کاخ سفید", "ناو هواپیمابر", "هواپیمابر",
    "بمب افکن", "گروسی", "اسنپ بک", "مکانیسم ماشه", "شورای امنیت سازمان ملل", "آژانس بین المللی انرژی اتمی",
    "موساد", "سیا$", "ناوگان",
])
FA_MID = fa_rx([
    "عربستان", "ریاض", "امارات", "ابوظبی", "قطر", "دوحه", "عمان", "مسقط", "بحرین", "کویت", "عراق", "بغداد",
    "سوریه", "دمشق", "لبنان", "بیروت", "یمن", "صنعا", "دریای سرخ", "باب المندب", "غزه", "حماس", "اروپا",
    "تروئیکا", "روسیه", "چین$", "چینی$", "غنی سازی", "اورانیوم", "هسته ای", "نفتکش", "تحریم", "مذاکره",
    "مذاکرات", "عراقچی", "لاریجانی", "وحیدی", "بقائی", "بقایی", "قالیباف", "شورای عالی امنیت ملی", "سپاه",
    "ارتش", "پدافند", "نیروی دریایی", "موشک", "پهپاد", "حمله", "حملات", "جنگ$", "جنگنده", "آتش بس", "تجاوز",
    "انفجار", "رزمایش", "تهدید", "هشدار", "اولتیماتوم", "ضرب الاجل", "تنگه", "شورای امنیت",
])
FA_NOISE = fa_rx([
    "فوتبال", "والیبال", "فوتسال", "بسکتبال", "جام جهانی", "لیگ برتر", "المپیک", "سینما", "کنسرت",
    "تیم ملی", "پرسپولیس", "استقلال تهران", "سریال", "جشنواره فیلم",
])


def _distinct(rx, text):
    return {m.lower() for m in rx.findall(text)} if text else set()


def relevance_en(title: str, summary: str):
    t, s = title or "", summary or ""
    ct, cs = _distinct(EN_CORE, t), _distinct(EN_CORE, s)
    mt, ms = _distinct(EN_MID, t), _distinct(EN_MID, s)
    st, ss = _distinct(EN_SEC, t), _distinct(EN_SEC, s)
    ut, us = _distinct(EN_US, t), _distinct(EN_US, s)
    score = 1.5 * (4 * len(ct) + 2 * len(mt) + len(st) + len(ut)) + \
        (3 * len(cs - ct) + 1.5 * len(ms - mt) + 0.7 * len(ss - st) + 0.7 * len(us - ut))
    other = len(mt | ms) + len(st | ss) + len(ut | us)
    ok = bool(ct) or (bool(cs) and other >= 1) \
        or (bool(mt) and bool(st | ss | ut | us) and score >= 4.5) \
        or (bool(ut) and bool(mt | ms | cs)) or score >= 9
    if ok and EN_NOISE.search(t) and not ct:
        ok = False
    if ok and EN_NOISE.search(t) and ct and not (st | ss):
        ok = False   # e.g. "Iran beat Japan in the World Cup qualifier"
    return round(score, 1), ok


def relevance_fa(title: str, summary: str):
    t, s = fa_norm(title or ""), fa_norm(summary or "")
    ct, cs = _distinct(FA_CORE, t), _distinct(FA_CORE, s)
    mt, ms = _distinct(FA_MID, t), _distinct(FA_MID, s)
    score = 4 * len(ct) + 2 * len(mt) + 2.5 * len(cs - ct) + 1 * len(ms - mt)
    ok = bool(ct) or score >= 6 or len(mt) >= 2
    if ok and FA_NOISE.search(t) and not (mt & {"حمله", "موشک", "پهپاد", "جنگ"}):
        ok = False
    return round(score, 1), ok


def is_relevant(item):
    if item.get("lang") == "fa":
        return relevance_fa(item.get("ti", ""), item.get("su", ""))
    return relevance_en(item.get("ti", ""), item.get("su", ""))


if __name__ == "__main__":
    tests = [
        ("US strikes Iranian drone sites near Bandar Abbas", ""),
        ("Iran beat Japan in World Cup qualifier", "Tehran fans celebrate"),
        ("Saudi Arabia hosts tourism expo", "Riyadh"),
        ("Trump says talks with Tehran could resume next week", ""),
        ("Oil prices rise as tanker traffic slows in the Strait of Hormuz", ""),
        ("Stocks rally on Wall Street", "Tech shares led gains"),
        ("Qatar mediates between Washington and Tehran", ""),
    ]
    for t, s in tests:
        print(relevance_en(t, s), t)
    for t in ["عراقچی با وزیر خارجه عمان دیدار کرد", "قیمت دلار امروز", "رزمایش پدافند هوایی در اصفهان",
              "پیروزی تیم ملی فوتبال ایران", "ترامپ: ایران باید پای میز مذاکره بیاید"]:
        print(relevance_fa(t, ""), t)
