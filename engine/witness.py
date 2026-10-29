"""Citizen reports relayed by a Telegram channel in wartime ("پیام‌های دریافتی:" followed by short messages from
readers: "سلام الان ساعت ۰۰:۲۵ قشم صدای انفجار اومد", "#قشم 00:24 صدای انفجار و لرزش", …).

Such a post is read message by message (messages are separated by blank lines): what was heard (explosion, air
defence fire, jets, drones, sirens), where (a city named in the message or in a hashtag) and when (the clock times
in it). It becomes one news sentence ("گزارش‌های مردمی از صدای انفجار در قشم و بندرعباس، حدود ساعت ۰۰:۲۵") with a
line of counts under it, in Persian and in English, and its severity comes from the counts (score). It stays an
unconfirmed report until a news outlet reports something that happened in the same city (cluster.same_story)."""
import re
from collections import Counter

from .util import fa_norm, to_latin_digits

HEADER = re.compile(r"^\W*(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in (
    "پیام های دریافتی", "پیام‌های دریافتی", "پیام های رسیده", "پیام‌های رسیده", "پیامهای دریافتی", "پیامهای رسیده",
    "گزارش های مردمی", "گزارش‌های مردمی", "گزارش های رسیده", "گزارش‌های رسیده", "پیام های مخاطبان",
    "پیام‌های مخاطبان", "پیام های شما", "پیام‌های شما")) + r")\s*[:：]?")

# Iranian cities: key -> (Persian, English, other Persian spellings, other English spellings)
CITIES = {
    "tehran": ("تهران", "Tehran", [], []), "karaj": ("کرج", "Karaj", [], []),
    "isfahan": ("اصفهان", "Isfahan", [], ["esfahan"]), "shiraz": ("شیراز", "Shiraz", [], []),
    "tabriz": ("تبریز", "Tabriz", [], []), "mashhad": ("مشهد", "Mashhad", [], []), "qom": ("قم", "Qom", [], []),
    "ahvaz": ("اهواز", "Ahvaz", [], ["ahwaz"]), "abadan": ("آبادان", "Abadan", ["ابادان"], []),
    "khorramshahr": ("خرمشهر", "Khorramshahr", [], []), "dezful": ("دزفول", "Dezful", [], []),
    "bandar_abbas": ("بندرعباس", "Bandar Abbas", ["بندر عباس"], []), "qeshm": ("قشم", "Qeshm", [], []),
    "kish": ("کیش", "Kish", [], []), "sirik": ("سیریک", "Sirik", [], []), "jask": ("جاسک", "Jask", [], []),
    "minab": ("میناب", "Minab", [], []), "hormuz_island": ("جزیره هرمز", "Hormuz Island", [], []),
    "lengeh": ("بندر لنگه", "Bandar Lengeh", ["بندرلنگه"], ["lengeh"]), "bushehr": ("بوشهر", "Bushehr", [], []),
    "kharg": ("خارک", "Kharg", ["خارگ"], []), "asaluyeh": ("عسلویه", "Asaluyeh", [], ["assaluyeh"]),
    "chabahar": ("چابهار", "Chabahar", [], []), "zahedan": ("زاهدان", "Zahedan", [], []),
    "kerman": ("کرمان", "Kerman", [], []), "yazd": ("یزد", "Yazd", [], []), "kashan": ("کاشان", "Kashan", [], []),
    "natanz": ("نطنز", "Natanz", [], []), "arak": ("اراک", "Arak", [], []), "hamedan": ("همدان", "Hamedan", [], []),
    "kermanshah": ("کرمانشاه", "Kermanshah", [], []), "sanandaj": ("سنندج", "Sanandaj", [], []),
    "ilam": ("ایلام", "Ilam", [], []), "khorramabad": ("خرم آباد", "Khorramabad", ["خرم‌آباد", "خرماباد"], []),
    "urmia": ("ارومیه", "Urmia", [], ["orumiyeh"]), "ardabil": ("اردبیل", "Ardabil", [], []),
    "zanjan": ("زنجان", "Zanjan", [], []), "qazvin": ("قزوین", "Qazvin", [], []), "rasht": ("رشت", "Rasht", [], []),
    "sari": ("ساری", "Sari", [], []), "gorgan": ("گرگان", "Gorgan", [], []), "semnan": ("سمنان", "Semnan", [], []),
    "birjand": ("بیرجند", "Birjand", [], []), "bojnurd": ("بجنورد", "Bojnurd", [], []),
    "parchin": ("پارچین", "Parchin", [], []), "pardis": ("پردیس", "Pardis", [], []),
    "shahriar": ("شهریار", "Shahriar", [], []), "eslamshahr": ("اسلامشهر", "Eslamshahr", [], []),
    "varamin": ("ورامین", "Varamin", [], []), "damavand": ("دماوند", "Damavand", [], []),
    "khomeini_shahr": ("خمینی شهر", "Khomeini Shahr", ["خمینی‌شهر"], []), "najafabad": ("نجف آباد", "Najafabad", ["نجف‌آباد"], []),
    "dezful_vahdati": ("پایگاه وحدتی", "Vahdati air base", [], []), "bam": ("بم", "Bam", [], []),
    "marivan": ("مریوان", "Marivan", [], []), "piranshahr": ("پیرانشهر", "Piranshahr", [], []),
    "saqqez": ("سقز", "Saqqez", [], []), "mahabad": ("مهاباد", "Mahabad", [], []), "khoy": ("خوی", "Khoy", [], []),
    "maragheh": ("مراغه", "Maragheh", [], []), "shahroud": ("شاهرود", "Shahroud", [], []),
}
_L = r"ؠ-ۿ"
_CITY_FA = [(k, re.compile(rf"(?<![{_L}])(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in [v[0], *v[2]])
                           + rf")(?![{_L}])")) for k, v in CITIES.items()]
_CITY_EN = [(k, re.compile(r"\b(?:" + "|".join(re.escape(x.lower()) for x in [v[1], *v[3]]) + r")\b", re.I))
            for k, v in CITIES.items()]

# what was heard, strongest first
KINDS = [
    ("blast", r"انفجار|منفجر|موج انفجار|لرزید|لرزش|لرزوند|بد\s*زد|صدای\s*(?:مهیب|وحشتناک|شدید|بلند|بم)|بمب|اصابت"),
    ("launch", r"پرتاب\s*موشک|شلیک\s*موشک|موشک"),
    ("airdef", r"پدافند|ضد\s*هوایی|ضدهوایی|تیربار|شلیک|رهگیری|منور"),
    ("jet", r"جنگنده|جت|هواپیما|هواپیمای\s*نظامی|دیوار صوتی"),
    ("drone", r"پهپاد|ریزپرنده|کوادکوپتر|صدای\s*موتور"),
    ("siren", r"آژیر|اژیر"),
]
_KIND_RX = [(k, re.compile(fa_norm(rx))) for k, rx in KINDS]
KIND_FA = {"blast": "صدای انفجار", "launch": "پرتاب موشک", "airdef": "شلیک پدافند", "jet": "صدای جنگنده", "drone": "صدای پهپاد",
           "siren": "صدای آژیر"}
KIND_EN = {"blast": "explosions", "launch": "missile launches", "airdef": "air defence fire", "jet": "jets", "drone": "drones", "siren": "sirens"}
SHAKE = re.compile(fa_norm(r"لرزید|لرزش|لرزوند|شیشه"))
# an explanation in the post itself: an exercise, a test, a gas explosion, ordnance being destroyed
OFFICIAL = re.compile(fa_norm(r"رزمایش|مانور|تست\s*پدافند|آزمایش|انفجار\s*گاز|نشت\s*گاز|کپسول|انهدام\s*مهمات|خنثی\s*سازی"
                              r"|مهمات\s*عمل\s*نکرده|ترقه|آتش\s*بازی|چهارشنبه\s*سوری"))
_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*[:：٫.]\s*([0-5]\d)(?!\d)")


def cities_in(text, lang="fa"):
    """City keys named in a text."""
    if lang == "fa":
        t = fa_norm(text or "")
        return {k for k, rx in _CITY_FA if rx.search(t)}
    return {k for k, rx in _CITY_EN if rx.search(text or "")}


def parse(raw):
    """A post's raw text (blank lines between messages) -> what its messages report, or None if it isn't a post of
    citizen reports of sounds of war."""
    text = (raw or "").replace("\r", "")
    lines = [x for x in text.split("\n") if x.strip()]
    if not lines or not HEADER.search(fa_norm(lines[0])):
        return None
    first = text.strip().split("\n", 1)
    body = (HEADER.sub("", fa_norm(first[0]), count=1) + "\n" + (first[1] if len(first) > 1 else ""))
    # normalised block by block: fa_norm folds line breaks, which separate the messages
    blocks = [fa_norm(b) for b in re.split(r"\n\s*\n", body) if b.strip()]
    kinds, cities, times, n, shake, official = Counter(), Counter(), [], 0, False, False
    ck = {}                                         # what was heard, city by city
    tag_city = set()
    for b in blocks:
        tags = set()
        for h in re.findall(r"#([^\s#]+)", b):
            tags |= cities_in(h.replace("_", " "))
        here = cities_in(re.sub(r"#\S+", " ", b)) | tags
        b_plain = re.sub(r"#\S+", " ", b)
        ks = {k for k, rx in _KIND_RX if rx.search(b_plain)}
        if tags and not ks and len(b_plain.strip()) < 3:
            tag_city = tags                         # a hashtag line on its own: the place of what follows
            continue
        if not ks:
            continue
        n += 1
        kinds.update(ks)
        for c in (here or tag_city):
            cities[c] += 1
            ck.setdefault(c, set()).update(ks)
        for h, m in _TIME.findall(to_latin_digits(b_plain)):
            times.append(f"{int(h):02d}:{m}")
        shake = shake or bool(SHAKE.search(b_plain))
        official = official or bool(OFFICIAL.search(b_plain))
    if not n:
        return None
    if any(x.startswith("00:") for x in times):
        times = ["00" + x[2:] if x.startswith("12:") else x for x in times]     # "12:25" on a 12-hour clock
    return {"n": n, "kinds": dict(kinds), "cities": dict(cities), "times": sorted(times), "shake": shake,
            "official": official, "ck": {c: sorted(v) for c, v in ck.items()}}


def _fa_digits(s):
    return s.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _join(xs, lang):
    if len(xs) <= 1:
        return "".join(xs)
    return ("، ".join(xs[:-1]) + " و " + xs[-1]) if lang == "fa" else (", ".join(xs[:-1]) + " and " + xs[-1])


def _when(times, lang):
    if not times:
        return ""
    lo, hi = times[0], times[-1]
    mins = lambda x: int(x[:2]) * 60 + int(x[3:])  # noqa: E731
    if lo == hi or mins(hi) - mins(lo) <= 10 or mins(hi) - mins(lo) > 90:
        at = Counter(times).most_common(1)[0][0] if mins(hi) - mins(lo) > 90 else times[len(times) // 2]
        return f"، حدود ساعت {_fa_digits(at)}" if lang == "fa" else f", around {at} Tehran time"
    return (f"، بین ساعت {_fa_digits(lo)} تا {_fa_digits(hi)}" if lang == "fa"
            else f", between {lo} and {hi} Tehran time")


def texts(w):
    """(Persian headline, Persian text, English headline, English text) for a parsed post."""
    ks = [k for k, _ in KINDS if w["kinds"].get(k)]
    top = sorted(w["cities"], key=lambda c: -w["cities"][c])
    shown = top[:3]
    fa_c = [CITIES[c][0] for c in shown] + (["چند شهر دیگر"] if len(top) > 3 else [])
    en_c = [CITIES[c][1] for c in shown] + (["other cities"] if len(top) > 3 else [])
    fa_where = f" در {_join(fa_c, 'fa')}" if fa_c else ""
    en_where = f" in {_join(en_c, 'en')}" if en_c else ""
    fa_ti = f"گزارش‌های مردمی از {_join([KIND_FA[k] for k in ks], 'fa')}{fa_where}{_when(w['times'], 'fa')}"
    en_ti = f"Reports from residents of {_join([KIND_EN[k] for k in ks], 'en')}{en_where}{_when(w['times'], 'en')}"
    per_fa = "، ".join(f"{_fa_digits(str(w['cities'][c]))} از {CITIES[c][0]}" for c in top[:4])
    per_en = ", ".join(f"{w['cities'][c]} from {CITIES[c][1]}" for c in top[:4])
    n = w["n"]
    fa_su = f"{_fa_digits(str(n))} پیام مردمی" + (f"؛ {per_fa}" if per_fa else "") + "."
    en_su = f"{n} message{'s' if n != 1 else ''} from the public" + (f": {per_en}" if per_en else "") + "."
    if w.get("shake"):
        fa_su += " لرزش شیشه‌ها یا ساختمان هم گزارش شده."
        en_su += " Windows or buildings shaking reported."
    if w.get("official"):
        fa_su += " در پیام‌ها به رزمایش، آزمایش یا انفجار غیرنظامی هم اشاره شده."
        en_su += " Some messages mention an exercise, a test or a non-military explosion."
    return fa_ti, fa_su, en_ti, en_su


def score(w):
    """(severity, flags) of a post of citizen reports: red when explosions, missile launches or air defence fire are
    reported by three people in one city or from two cities or more, or jets, drones or sirens from two cities or
    more; orange otherwise; yellow when the messages themselves name an exercise, a test or a non-military explosion."""
    if w.get("official"):
        return 35.0, {"witness", "controlled"}
    strong = bool(set(w["kinds"]) & {"blast", "launch", "airdef"})
    most = max(w["cities"].values(), default=0)
    many = len(w["cities"]) >= 2
    if (strong and (most >= 3 or many)) or (not strong and many):
        return 76.0, {"witness", "kinetic"}
    return 55.0, {"witness"}
