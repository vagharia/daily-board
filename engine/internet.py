"""Internet disruptions in Iran: the international link cut or throttled, nationwide outages, access restored.

Whoever reports them (measurement groups such as NetBlocks and Cloudflare Radar, or the news), these are orange
stories. A report counts when its headline speaks of the disruption and it is about Iran: an English report must
name Iran; a Persian one must not be about another country, a village's outage, a global cloud failure or the price
of data packages."""
import re

from .classify_fa import _ANY, F, R
from .util import fa_norm

DOWN_SEV = 58.0             # a cut, slowdown or restriction
UP_SEV = 48.0               # access coming back, or a denial

# ------------------------------------------------------------------ English
_NET_EN = (r"(?:internet|connectivity|online access|web access|mobile data|mobile internet|internet traffic"
           r"|network traffic|web traffic|international (?:internet|bandwidth|gateway|access)|bandwidth)")
_DOWN_EN = (r"(?:blackouts?|shut ?downs?|shutting down|shut off|outages?|cuts?|cut off|knocked out|disrupt\w*|restrict\w*"
            r"|throttl\w*|slow\w*|drop\w*|fall\w*|fell|plung\w*|collaps\w*|offline|declin\w*|loss|lost|curb\w*"
            r"|block\w*|down (?:by |over |more than |nearly |about |to )?\d)")
DOWN_EN = re.compile(r"\b" + _NET_EN + r"\b.{0,50}?\b" + _DOWN_EN
                     + r"|\b" + _DOWN_EN + r"\b.{0,30}?\b" + _NET_EN + r"\b"
                     + r"|\bkill switch\b"
                     + r"|\b(?:internet|connectivity)\b.{0,20}\b\d{1,3} ?(?:%|percent) of (?:ordinary|normal|usual)", re.I)
UP_EN = re.compile(r"\b(?:internet|connectivity|online access|mobile data)\b.{0,40}?\b(?:restor\w*|return\w*|back online"
                   r"|resum\w*|reconnect\w*|lift\w*)\b|\b(?:restor\w*|reconnect\w*)\b.{0,25}?\b(?:internet|connectivity)\b",
                   re.I)
IRAN_EN = re.compile(r"\b(?:iran\w*|tehran|islamic republic|persian)\b", re.I)
PRICE_EN = re.compile(r"\b(?:prices?|costs?|tariffs?|subscriptions?|packages?|plans?)\b", re.I)

# ------------------------------------------------------------------ Persian
_NET_FA = ("(?:اینترنت|ترافیک\\s*اینترنت|پهنای\\s*باند|شبکه\\s*ملی\\s*اطلاعات|فیلترشکن|فیلتر\\s*شکن"
           "|وی\\s*پی\\s*ان|اتصال\\s*به\\s*اینترنت|دسترسی\\s*به\\s*اینترنت)")
DOWN_FA = re.compile(R("(?:قطع|قطعی|اختلال|اختلالات|کندی|کند\\s*شدن|کاهش|افت|محدودیت|محدود\\s*سازی|محدود\\s*شدن"
                       "|خاموشی|مسدود|ریزش|سقوط|ناپایداری|قطعی\\s*های)", _ANY % 25, _NET_FA, "|", _NET_FA, _ANY % 25,
                       "(?:قطع|مختل|اختلال|کند|محدود|کاهش|افت|خاموش|مسدود|ریزش|سقوط|از\\s*دسترس\\s*خارج)", "|",
                       # the strong verbs further on ("ترافیک اینترنت ایران به دلایلی اعلام نشده شدیدا در حال سقوط است")
                       _NET_FA, _ANY % 50, "(?:قطع|مختل|خاموش|ریزش|سقوط|از\\s*دسترس\\s*خارج)")
                     + "|" + F("نت بلاکس", "نتبلاکس", "کلادفلر رادار"))
UP_FA = re.compile(R("(?:وصل\\s*شدن|وصل\\s*شد|بازگشت|برقراری|برقرار\\s*شد|اتصال\\s*مجدد|رفع\\s*اختلال|رفع\\s*محدودیت"
                     "|بازگشایی)", _ANY % 20, "اینترنت", "|", "اینترنت", _ANY % 20,
                     "(?:وصل\\s*شد|برقرار\\s*شد|بازگشت|بازگشایی|رفع\\s*شد)"))
DENIAL_FA = re.compile(F("تکذیب", "شایعه", "صحت ندارد", "کذب", "بی اساس"))
PRICE_FA = re.compile(F("قیمت", "تعرفه", "هزینه", "بسته اینترنت", "بسته های اینترنت", "اینترنت رایگان", "حجم",
                        "گران", "ارزان"))
# outages of one village or a dormitory are not the country's internet
LOCAL_FA = re.compile(F("روستا", "روستاهای", "دهستان", "محله", "خوابگاه", "شهرک"))
NATIONAL_FA = re.compile(F("کشور", "سراسری", "بین الملل", "ملی", "ایران", "گسترده", "ترافیک", "نت بلاکس", "همه",
                           "تمام", "استان"))
# a disruption somewhere else, or a cloud company's worldwide failure
ABROAD_FA = re.compile(F("افغانستان", "پاکستان", "عراق", "سوریه", "روسیه", "اوکراین", "کریمه", "کره شمالی", "ترکیه",
                         "ونزوئلا", "میانمار", "سودان", "اتیوپی", "چین", "آمریکا", "اروپا", "جهانی", "کلادفلر",
                         "آمازون", "مایکروسافت", "گوگل کلود"))
IRAN_FA = re.compile(F("ایران", "کشور", "تهران"))


def internet(lang, title, summary=""):
    """'down', 'up' or None for a report's headline (and the start of its text)."""
    if lang == "fa":
        t, s = fa_norm(title or ""), fa_norm(summary or "")[:300]
        if not (DOWN_FA.search(t) or UP_FA.search(t)) or PRICE_FA.search(t):
            return None
        if ABROAD_FA.search(t) and not IRAN_FA.search(t):
            return None
        if LOCAL_FA.search(t) and not NATIONAL_FA.search(t):
            return None
        if UP_FA.search(t) or DENIAL_FA.search(t):
            return "up"
        return "down"
    t, s = title or "", (summary or "")[:300]
    if not (DOWN_EN.search(t) or UP_EN.search(t)) or PRICE_EN.search(t):
        return None
    if not (IRAN_EN.search(t) or IRAN_EN.search(s)):
        return None
    return "up" if UP_EN.search(t) and not DOWN_EN.search(t.split(" after ")[0]) else "down"


def severity(kind):
    return DOWN_SEV if kind == "down" else UP_SEV
