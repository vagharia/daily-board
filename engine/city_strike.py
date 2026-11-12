"""One attack on one city of Iran, one story: the main front's counterpart of the Gulf rule (cluster.py, GULF_WINDOW).

The news tells one attack in many words ("Explosions heard in Hormozgan province", "Southern Iran's Sirik attacked,
IRNA says", «حمله آمریکا به پایگاه دریایی سپاه در سیریک»): their headlines share almost no words, so the rule reads
the place instead. Reports of an attack or an explosion in the same city of Iran (witness.CITIES; Tehran is left out:
many strikes a night in its districts) are one story when they come close together (cluster.py: IR_WINDOW and the
rules after it). A report naming only the province (Hormozgan) is read with the city in its text, or else joins the
one story of that province's cities then being told, never one of two.

Two blasts close together stay two stories when (mark, apart):
  - a report says it is a new one ("another", "again", «دوباره», «انفجار دوم»): it joins by no rule here, and one
    told as it happens ("another explosion heard in Jask") joins no story of that city told without such words,
    however close the headlines (cluster.Clusterer._iran_conflict);
  - the two name different kinds of target in the city (a port and an air base) or different streets or districts;
  - a report told as it happens comes after the story has gone quiet (IR_QUIET): it joins by no rule if it is a
    Telegram channel's post or says it is happening now ("moments ago", «لحظاتی پیش»); a news outlet's "explosions
    heard" an hour later is often the same blast retold late, so it only gets no join by this rule;
  - the times the reports give don't meet (the time label, cluster.EV_ON), or more time has passed (the windows).
A report naming three cities or more is a roundup and gets no mark. A Telegram channel's post joins a news story by
this rule, never another channel's; citizen reports (witness.py) have their own rule. Reports at sea have theirs."""
import re

from . import witness
from .util import fa_norm

LEFT_OUT = {"tehran"}
# big cities: separate strikes in one night are common, so only reports close to the story's first one join
BIG = {"isfahan", "shiraz", "tabriz", "mashhad", "karaj", "qom", "ahvaz", "kermanshah", "urmia", "bandar_abbas"}
MAX_CITIES = 2

# provinces a report may name instead of the city: key -> (English, Persian, its cities in witness.CITIES).
# Names shared with a city (Bushehr, Kerman, Isfahan…) only with the word province / «استان».
PROVINCES = {
    "hormozgan": (r"hormozgan|hormuzgan", "هرمزگان",
                  {"bandar_abbas", "qeshm", "kish", "sirik", "jask", "minab", "hormuz_island", "lengeh"}),
    "khuzestan": (r"khuzestan", "خوزستان", {"ahvaz", "abadan", "khorramshahr", "dezful", "dezful_vahdati"}),
    "sistan": (r"sistan(?:[- ]and[- ]|[- ])baluchestan|sistan", "سیستان و بلوچستان|سیستان", {"chabahar", "zahedan"}),
    "bushehr_p": (r"bushehr province", "استان بوشهر", {"bushehr", "kharg", "asaluyeh"}),
    "kurdistan": (r"kurdistan province|iran's kurdistan", "استان کردستان", {"sanandaj", "marivan", "saqqez"}),
    "w_azerbaijan": (r"west azerbaijan", "آذربایجان غربی", {"urmia", "khoy", "mahabad", "piranshahr"}),
    "e_azerbaijan": (r"east azerbaijan", "آذربایجان شرقی", {"tabriz", "maragheh"}),
    "lorestan": (r"lorestan", "لرستان", {"khorramabad"}),
    "kermanshah_p": (r"kermanshah province", "استان کرمانشاه", {"kermanshah"}),
}
_PROV_EN = {k: re.compile(r"\b(?:" + v[0] + r")\b", re.I) for k, v in PROVINCES.items()}
_PROV_FA = {k: re.compile(fa_norm(v[1])) for k, v in PROVINCES.items()}
PROVINCE_OF = {c: k for k, v in PROVINCES.items() for c in v[2]}

# kinds of target named in the city: two reports naming different kinds are two strikes
_KIND_EN = {"port": r"ports?|harbou?rs?|docks?|jett(?:y|ies)|piers?|wharf",
            "base": r"bases?|garrisons?|barracks|headquarters|hq",
            "airport": r"airports?|airfields?|air ?strips?",
            "oil": r"refiner(?:y|ies)|oil|fuel|depots?|terminals?|petrochemical\w*|gas (?:field|plant|facilit\w+)",
            "airdef": r"air defen[cs]es?|radars?|missile (?:sites?|launchers?|batter(?:y|ies))|sam sites?|launchers?",
            "power": r"power (?:plant|station)s?|electricity|substations?",
            "home": r"homes?|houses?|residential|buildings?|apartments?"}
_KIND_FA = {"port": r"بندرگاه|اسکله|لنگرگاه",
            "base": r"پایگاه(?!\s*(?:هوایی|شکاری))|پادگان|قرارگاه|ستاد",
            "airport": r"فرودگاه|پایگاه\s*(?:هوایی|شکاری)",
            "oil": r"پالایشگاه|انبار\s*نفت|مخزن|مخازن|پایانه\s*نفتی|پتروشیمی|سوخت",
            "airdef": r"پدافند|رادار|سکوی\s*پرتاب|لانچر",
            "power": r"نیروگاه|پست\s*برق",
            "home": r"منزل|منازل|مسکونی|ساختمان|آپارتمان|خانه"}
# "airport" in English: an air base is an airfield, not a base on the ground
_AIRBASE_EN = re.compile(r"\bair ?bases?\b", re.I)
_KIND_EN_RX = {k: re.compile(r"\b(?:" + v + r")\b", re.I) for k, v in _KIND_EN.items()}
_KIND_FA_RX = {k: re.compile(fa_norm(v)) for k, v in _KIND_FA.items()}

# told as it happens: explosions or air defence heard, sirens, interceptions
_FRESH_EN = re.compile(r"\b(heard|sounds? of|sirens?|alarms?|air defen[cs]es? (?:activ\w+|fir\w+|engag\w+)"
                       r"|intercept\w*|now|ongoing|under way|underway|moments ago|minutes ago)\b", re.I)
_FRESH_FA = re.compile(fa_norm("شنیده شد|شنیده می|شنیده‌اند|شنیده اند|صدای|آژیر|پدافند|رهگیری|هم اکنون|هم‌اکنون"
                               "|لحظاتی پیش|دقایقی پیش|در حال"))
_NOW_EN = re.compile(r"\b(now|moments ago|minutes ago|just now|right now)\b", re.I)
_NOW_FA = re.compile(fa_norm("هم اکنون|هم‌اکنون|هماکنون|لحظاتی پیش|لحظاتی قبل|دقایقی پیش|دقایقی قبل|همین الان|الان"))
# a new one: "another explosion", "second blast", «انفجار دوم», «دوباره»
_NEW_EN = re.compile(r"\b(?:new|another|fresh|second|third|again|renewed|wave|round|more explosions|further explosions)\b",
                     re.I)
_NEW_FA = re.compile(fa_norm("دوباره|مجدد|مجددا|جدید|تازه|دومین|سومین|انفجار دوم|انفجار سوم|بار دیگر|باز هم|موج"))
_NOT = {"denial", "past", "controlled", "scheduled", "speculative", "analysis", "opinion", "digest", "reaction",
        "quote"}


class Mark(tuple):
    """(cities, province, kinds) of a report; fresh: told as it happens; now: it says so ("moments ago"); new: it
    says it is a new one."""
    fresh = False
    now = False
    new = False


def _kinds(en, fat):
    out = {k for k, rx in _KIND_EN_RX.items() if rx.search(en)}
    if _AIRBASE_EN.search(en):
        out.add("airport")
        if not re.search(r"\bbases?\b", _AIRBASE_EN.sub(" ", en), re.I):
            out.discard("base")
    out |= {k for k, rx in _KIND_FA_RX.items() if fat and rx.search(fat)}
    return frozenset(out)


def _provinces(en, fat):
    return {k for k, rx in _PROV_EN.items() if rx.search(en)} | {k for k, rx in _PROV_FA.items() if fat and rx.search(fat)}


def mark(m):
    """The Mark of a report of an attack or an explosion in a city (or a province) of Iran, or None. The caller
    checks that it is a report of an attack (cluster.event_class "K"), not at sea, and not a citizens' post."""
    if set(m.get("flags") or []) & _NOT or "kinetic" not in (m.get("flags") or []):
        return None
    fa = m.get("lang") == "fa"
    en = m.get("en_ti") or ("" if fa else m.get("ti")) or ""
    fat = fa_norm(m.get("ti") or "") if fa else ""
    cities = witness.cities_in(en, "en") | (witness.cities_in(fat, "fa") if fa else set())
    provs = _provinces(en, fat)
    if not cities:                                  # the province, or no place, in the headline: the city in the text
        su_en = (m.get("en_su") or ("" if fa else m.get("su")) or "")[:250]
        su_fa = fa_norm(m.get("su") or "")[:250] if fa else ""
        cities = witness.cities_in(su_en, "en") | (witness.cities_in(su_fa, "fa") if fa else set())
        if provs:                                   # only that province's cities
            cities = {c for c in cities if PROVINCE_OF.get(c) in provs}
        elif len(cities) > 1:
            cities = set()
    cities -= LEFT_OUT
    if len(cities) > MAX_CITIES:
        return None                                 # a roundup of many places
    if not cities:
        if len(provs) != 1:
            return None
        prov = next(iter(provs))
    else:
        ps = {PROVINCE_OF.get(c) for c in cities}
        prov = ps.pop() if len(ps) == 1 else None
    if not cities and not prov:
        return None
    g = Mark((frozenset(cities), prov, _kinds(en, fat)))
    g.fresh = bool(_FRESH_EN.search(en) or (fa and _FRESH_FA.search(fat)))
    g.now = bool(_NOW_EN.search(en) or (fa and _NOW_FA.search(fat)))
    g.new = bool(_NEW_EN.search(en) or (fa and _NEW_FA.search(fat)))
    return g


def same(a, b):
    """2 = the same city, 1 = one of them names only the province of the other's city, 0 = not the same attack
    (another city, both naming only the province, or kinds of target that don't meet)."""
    if not a or not b:
        return 0
    if a[2] and b[2] and not a[2] & b[2]:
        return 0                                    # a port and an air base: two strikes
    if a[0] and b[0]:
        return 2 if a[0] & b[0] else 0
    return 1 if (a[0] or b[0]) and a[1] and a[1] == b[1] else 0


def big(a):
    return bool(a[0] & BIG)
