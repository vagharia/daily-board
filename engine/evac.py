"""Orders to leave a country (embassy staff, citizens): who orders, which country, how far ("non-emergency staff"
or everyone, the embassy closed). Reports with the same mark tell of the same order, for a week: outlets retell an
order days after it was given ("effective October 23"). Used by the bulletin's clustering, its warning light and the
Telegram alerts."""
import re
import time

from .util import fa_norm, to_latin_digits

_WHO = {
    "us": (r"u\.?s\.?|united states|america\w*|washington|state department|pentagon", "آمریکا|امریکا|واشنگتن|وزارت خارجه آمریکا"),
    "uk": (r"uk|u\.k\.|britain|british|london|foreign office", "بریتانیا|انگلیس|لندن"),
    "fr": (r"france|french|paris", "فرانسه|پاریس"), "de": (r"germany|german|berlin", "آلمان|برلین"),
    "ca": (r"canada|canadian", "کانادا"), "au": (r"australia\w*", "استرالیا"), "cn": (r"china|chinese|beijing", "چین|پکن"),
    "ru": (r"russia\w*|moscow", "روسیه|مسکو"), "in": (r"india\w*|new delhi", "هند"), "it": (r"ital\w+|rome", "ایتالیا"),
}
_WHERE = {
    "saudi": (r"saudi\w*|riyadh|jeddah|dhahran|the kingdom", "عربستان|سعودی|ریاض|جده|ظهران"),
    "israel": (r"israel\w*|tel aviv|jerusalem", "اسرائیل|اسراییل|تل آویو|قدس|سرزمین های اشغالی"),
    "qatar": (r"qatar\w*|doha", "قطر|دوحه"), "iraq": (r"iraq\w*|baghdad|erbil", "عراق|بغداد|اربیل"),
    "kuwait": (r"kuwait\w*", "کویت"), "bahrain": (r"bahrain\w*|manama", "بحرین|منامه"),
    "uae": (r"uae|emirat\w*|dubai|abu dhabi", "امارات|دبی|ابوظبی"), "lebanon": (r"leban\w+|beirut", "لبنان|بیروت"),
    "iran": (r"iran\w*|tehran", "ایران|تهران"), "jordan": (r"jordan\w*|amman", "اردن|امان"),
    "oman": (r"oman\w*|muscat", "عمان|مسقط"), "yemen": (r"yemen\w*|sanaa|aden", "یمن|صنعا|عدن"),
    "cyprus": (r"cyprus", "قبرس"), "egypt": (r"egypt\w*|cairo", "مصر|قاهره"), "turkey": (r"turk\w+|ankara", "ترکیه|آنکارا"),
    "syria": (r"syria\w*|damascus", "سوریه|دمشق"),
}
_ALL_EN = re.compile(r"\b(all (?:us |american |embassy )?(?:staff|personnel|employees|diplomats|citizens)|clos\w+ (?:the |its )?"
                     r"(?:embassy|consulate)|(?:embassy|consulate) (?:clos\w+|shut\w*)|suspend\w* (?:embassy )?operations"
                     r"|full evacuation)\b", re.I)
_ALL_FA = re.compile(fa_norm("همه کارکنان|تمام کارکنان|همه دیپلمات|تمام دیپلمات|تعطیلی سفارت|سفارت را تعطیل|بسته شدن سفارت"
                             "|سفارت را بست|تعلیق فعالیت سفارت|تخلیه کامل"))
_RX = {k: (re.compile(r"\b(?:" + e + r")\b", re.I), re.compile(fa_norm(f))) for k, (e, f) in {**_WHO, **_WHERE}.items()}

_MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november "
                                         "december".split())}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})
_MONTHS_FA = {"ژانویه": 1, "فوریه": 2, "مارس": 3, "آوریل": 4, "مه": 5, "می": 5, "ژوئن": 6, "ژوئیه": 7, "جولای": 7,
              "اوت": 8, "آگوست": 8, "سپتامبر": 9, "اکتبر": 10, "نوامبر": 11, "دسامبر": 12}
_EFF_EN = re.compile(r"\b(?:effective|as of|since|starting|beginning) (?:on )?(?:\w+day,? )?(" + "|".join(_MONTHS) +
                     r")\.? (\d{1,2})\b|\b(?:effective|as of|since) (\d{1,2}) (" + "|".join(_MONTHS) + r")\b", re.I)
_EFF_FA = re.compile(r"(?:از|از تاریخ|از روز)\s*(\d{1,2})\s*(" + "|".join(_MONTHS_FA) + ")")


def _text(m):
    en = " ".join(x for x in (m.get("en_ti"), m.get("en_su")) if x) if m.get("lang") == "fa" else \
        " ".join(x for x in (m.get("ti"), m.get("su"), m.get("en_ti"), m.get("en_su")) if x)
    fa = fa_norm(" ".join(x for x in (m.get("ti"), m.get("su")) if x)) if m.get("lang") == "fa" else ""
    return en, fa


def _keys(table, head_en, head_fa):
    return [k for k in table if (head_en and _RX[k][0].search(head_en)) or (head_fa and _RX[k][1].search(head_fa))]


def mark(m):
    """(who orders, which country, "all" or "part") of an order to leave a country, from the headline; or None."""
    if "evac" not in (m.get("flags") or []):
        return None
    head_en = m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or ""
    head_fa = fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else ""
    who = _keys(_WHO, head_en, head_fa)
    where = [k for k in _keys(_WHERE, head_en, head_fa) if k not in who]
    if len(who) != 1 or len(where) != 1:
        return None
    level = "all" if (head_en and _ALL_EN.search(head_en)) or (head_fa and _ALL_FA.search(head_fa)) else "part"
    return (who[0], where[0], level)


def stale(m, slack=36 * 3600):
    """True if the report says the order took effect well before the report itself ("effective October 23")."""
    if "evac" not in (m.get("flags") or []):
        return False
    en, fa = _text(m)
    year = time.gmtime(m["t"]).tm_year
    dates = []
    for x in _EFF_EN.finditer(en):
        mon, day = (x.group(1), x.group(2)) if x.group(1) else (x.group(4), x.group(3))
        dates.append((_MONTHS[mon.lower()], int(day)))
    for x in _EFF_FA.finditer(to_latin_digits(fa)):
        dates.append((_MONTHS_FA[x.group(2)], int(x.group(1))))
    for mon, day in dates:
        try:
            t = time.mktime((year, mon, day, 0, 0, 0, 0, 0, 0)) - time.timezone
        except (OverflowError, ValueError):
            continue
        if t > m["t"] + 86400:
            t = time.mktime((year - 1, mon, day, 0, 0, 0, 0, 0, 0)) - time.timezone
        if m["t"] - t > slack:
            return True
    return False
