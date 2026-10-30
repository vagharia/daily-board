"""Incidents at sea: where one happened, as precisely as the reports say it, so reports of one incident can be told
apart from reports of another.

UKMTO and the outlets that relay it place an incident by its distance and bearing from a port or headland:
"25 nautical miles northeast of Khasab", "۹ مایلی شمال خصب". That is the incident's mark (mark()). Reports that
give no such place ("UK says vessel on fire in Strait of Hormuz") are general reports (general()): about one ship,
in a known sea area, not a recap of several ships nor an Iranian claim of mines.

Used by the bulletin's clustering (cluster.py) and by the Telegram alerts (alerts.py)."""
import re

from .util import fa_norm, to_latin_digits

# reference points UKMTO and others measure from: key -> (English forms, Persian forms, sea area)
REFS = {
    "khasab": (["khasab"], ["خصب"], "hormuz"),
    "musandam": (["musandam"], ["مسندم"], "hormuz"),
    "kumzar": (["kumzar"], ["کمزار"], "hormuz"),
    "bandar abbas": (["bandar abbas"], ["بندرعباس", "بندر عباس"], "hormuz"),
    "qeshm": (["qeshm"], ["قشم"], "hormuz"),
    "larak": (["larak"], ["لارک"], "hormuz"),
    "jask": (["jask"], ["جاسک"], "hormuz"),
    "fujairah": (["fujairah"], ["فجیره"], "hormuz"),
    "khor fakkan": (["khor ?fakkan"], ["خورفکان", "خور فکان"], "hormuz"),
    "kalba": (["kalba"], ["کلبا"], "hormuz"),
    "dibba": (["dibba", "daba"], ["دبا"], "hormuz"),
    "ras al khaimah": (["ras al[- ]?khaimah"], ["راس الخیمه", "رأس الخیمه"], "hormuz"),
    "limah": (["limah"], ["لیمه"], "hormuz"),
    "sohar": (["sohar"], ["صحار"], "hormuz"),
    "muscat": (["muscat"], ["مسقط"], "hormuz"),
    "duqm": (["duqm"], ["دقم"], "arabian"),
    "aden": (["aden"], ["عدن"], "redsea"),
    "hodeidah": (["hodeidah", "hudaydah", "hodeida"], ["حدیده", "الحدیده"], "redsea"),
    "mokha": (["mokha", "mocha"], ["مخا"], "redsea"),
    "djibouti": (["djibouti"], ["جیبوتی"], "redsea"),
    "nishtun": (["nishtun"], ["نشطون"], "redsea"),
}
_REF_EN = [(k, re.compile(r"\b(?:" + "|".join(v[0]) + r")\b", re.I)) for k, v in REFS.items()]
_REF_FA = [(k, re.compile("|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in v[1]))) for k, v in REFS.items()]

# sea areas named without a distance
AREAS = {
    "hormuz": (r"\b(hormuz|khasab|musandam|gulf of oman|fujairah|khor ?fakkan|jask|bandar abbas|qeshm|larak"
               r"|ras al[- ]?khaimah|sohar)\b|\b(off|near) (the )?(coast of )?oman\b|\boman'?s coast\b",
               "هرمز|خصب|مسندم|دریای عمان|فجیره|خورفکان|جاسک|بندرعباس|بندر عباس|قشم|لارک|راس الخیمه|صحار"),
    "redsea": (r"\b(red sea|gulf of aden|bab[- ]?(?:al|el)[- ]?mandab|bab[- ]?(?:al|el)[- ]?mandeb|hodeidah|aden|mokha)\b",
               "دریای سرخ|خلیج عدن|باب المندب|حدیده|عدن"),
}
_AREA_EN = [(k, re.compile(v[0], re.I)) for k, v in AREAS.items()]
_AREA_FA = [(k, re.compile(fa_norm(v[1]))) for k, v in AREAS.items()]

_DIR = {"north": "n", "south": "s", "east": "e", "west": "w", "northeast": "ne", "northwest": "nw",
        "southeast": "se", "southwest": "sw", "n": "n", "s": "s", "e": "e", "w": "w", "ne": "ne", "nw": "nw",
        "se": "se", "sw": "sw", "nne": "ne", "ene": "ne", "ese": "se", "sse": "se", "ssw": "sw", "wsw": "sw",
        "wnw": "nw", "nnw": "nw"}
_DIR_FA = {"شمال شرق": "ne", "شمال غرب": "nw", "جنوب شرق": "se", "جنوب غرب": "sw", "شمال": "n", "جنوب": "s",
           "شرق": "e", "غرب": "w"}

_MARK_EN = re.compile(
    r"(\d+(?:\.\d+)?)\s*-?\s*(nm|n\.\s?m\.?|nautical[- ]miles?|miles?|km|kilomet(?:er|re)s?)\b[\s,]*"
    r"(?:\([^)]{0,30}\)\s*)?"
    r"(?:(north[- ]?east|north[- ]?west|south[- ]?east|south[- ]?west|north|south|east|west"
    r"|nne|ene|ese|sse|ssw|wsw|wnw|nnw|ne|nw|se|sw|n|s|e|w)(?:ern)?\s+)?"
    r"(?:of|from|off)\s+(?:the\s+)?(?:(?:port|town|city|coast|island)\s+of\s+)?([A-Za-z][A-Za-z' -]{2,30})", re.I)
_MARK_FA = re.compile(
    r"(\d+(?:\.\d+)?)\s*(مایل|کیلومتر|کیلو متر)(?:ی)?\s*(?:دریایی\s*)?(?:در\s*)?"
    r"(شمال\s*شرق|شمال\s*غرب|جنوب\s*شرق|جنوب\s*غرب|شمال|جنوب|شرق|غرب)?(?:ی)?\s*"
    r"(?:(?:بندر|شهر|جزیره|سواحل|ساحل)\s*)?([ء-ۿ][ء-ۿ ]{1,25})")

SHIP_EN = re.compile(r"\b(vessels?|ships?|tankers?|dhows?|boats?|carriers?|freighters?|bulkers?|bulk carriers?"
                     r"|merchant|supertankers?|lng carriers?)\b", re.I)
SHIP_FA = re.compile(fa_norm("نفتکش|نفت کش|کشتی|شناور|لنج|تانکر|ناو|قایق|سوپرتانکر|ابرنفتکش"))
_PLURAL_EN = re.compile(r"\b(vessels|ships|tankers|dhows|boats|carriers|freighters|supertankers)\b"
                        r"|\b(?:vessel|ship|tanker|shipping)\s+(?:attacks|incidents|strikes|seizures)\b"
                        r"|\b(two|three|four|five|six|several|multiple|\d+)\s+(?:\w+\s+)?(vessels|ships|tankers)", re.I)
_PLURAL_FA = re.compile(fa_norm("نفتکش ها|نفت کش ها|کشتی ها|شناورها|شناور ها|لنج ها|تانکرها|تانکر ها")
                        + r"|(?:\d+|" + fa_norm("دو|سه|چهار|پنج|چند") + r")\s*(?:" + fa_norm("فروند") + r"\s*)?"
                        + fa_norm("(?:نفتکش|نفت کش|کشتی|شناور|تانکر)"))
_ANOTHER_EN = re.compile(r"\b(another|second|third|separate)\b|\b(new|fresh|further)\s+(attack|incident|strike|explosion)", re.I)
_ANOTHER_FA = re.compile(fa_norm("کشتی دیگر|نفتکش دیگر|نفت کش دیگر|شناور دیگر|لنج دیگر|دومین|سومین|حادثه جدید|حمله جدید"
                                 "|حادثه دیگر|حمله دیگر|حادثه تازه|حمله تازه|یک کشتی دیگر"))
_HAPPENED_EN = re.compile(r"\b(fire|ablaze|burning|blaze|attack\w*|struck|hit|hits|explosions?|blasts?|incident"
                          r"|damaged|disabled|sank|sinks|sinking|sunk|targeted|exploded)\b", re.I)
_HAPPENED_FA = re.compile(fa_norm("آتش|حمله|اصابت|انفجار|حادثه|آسیب|غرق|هدف قرار"))
_MINE_EN = re.compile(r"\bmines?\b|\bmined\b", re.I)
_MINE_FA = re.compile(r"(?<![ء-ۿ])" + fa_norm("مین") + r"(?:\s*" + fa_norm("ها") + r")?(?![ء-ۿ])")
_IRAN_SAYS_EN = re.compile(r"\b(iran\w*|irgc|revolutionary guards?|tehran)\b[^.;:]{0,40}\b(says?|said|claims?|claimed"
                           r"|reports?|announc\w+)\b|^\W*(iran|irgc)\w*\s*:", re.I)
_IRAN_SAYS_FA = re.compile(fa_norm("(?:سپاه|ارتش|ایران|نیروی دریایی)") + r"[^.:؛]{0,40}"
                           + fa_norm("(?:می گوید|گفت|مدعی|ادعا|اعلام|خبر داد)"))


def _texts(m):
    """(English text, Persian text) of a report: its headline and the start of its body."""
    en = ((m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or "") + " . "
          + (m.get("en_su") or (m.get("su") if m.get("lang") != "fa" else "") or "")[:600])
    fa = (to_latin_digits(fa_norm((m.get("ti") or "") + " . " + (m.get("su") or "")[:600]))
          if m.get("lang") == "fa" else "")
    return en, fa


def _ref_en(words):
    for k, rx in _REF_EN:
        if rx.match(words.strip()):
            return k
    return None


def _ref_fa(words):
    for k, rx in _REF_FA:
        if rx.match(words.strip()):
            return k
    return None


def _nm(d, unit):
    """Possible distances in nautical miles: kilometres are often a converted or mistranslated figure, so a
    kilometre figure stands for itself as well as for its conversion."""
    if unit.startswith("k") or unit.startswith(fa_norm("کیلو")):
        return frozenset({round(d), round(d / 1.852)})
    return frozenset({round(d)})


def mark(m):
    """The incident's place as reports give it: {"ref", "nm", "dir", "area"}, or None. Only for a report about a ship
    or a vessel."""
    hen, hfa = _head(m)
    if not (SHIP_EN.search(hen) or (hfa and SHIP_FA.search(hfa))):
        return None                         # the headline must be about a ship (a digest post's text names many things)
    en, fa = _texts(m)
    for txt, rx, lang in ((en, _MARK_EN, "en"), (fa, _MARK_FA, "fa")):
        if not txt:
            continue
        for x in rx.finditer(txt):
            ref = _ref_en(x.group(4)) if lang == "en" else _ref_fa(x.group(4))
            if not ref:
                continue
            d = float(x.group(1))
            if not 0 < d <= 400:
                continue
            dr = x.group(3)
            if dr:
                dr = _DIR.get(re.sub(r"[- ]", "", dr.lower())) if lang == "en" else _DIR_FA.get(re.sub(r"\s+", " ", dr))
            return {"ref": ref, "nm": _nm(d, x.group(2).lower()), "dir": dr or None, "area": REFS[ref][2]}
    return None


def same(a, b):
    """The same place: the same reference point, the same distance (give or take a mile) and, when both give one,
    the same bearing."""
    if not a or not b or a["ref"] != b["ref"]:
        return False
    if a["dir"] and b["dir"] and a["dir"] != b["dir"]:
        return False
    return any(abs(x - y) <= 1 for x in a["nm"] for y in b["nm"])


def differ(a, b):
    """Two places that cannot be the same incident: the same reference point at another distance or bearing."""
    return bool(a and b and a["ref"] == b["ref"] and not same(a, b))


def area(m, head=False):
    en, fa = _head(m) if head else _texts(m)
    for k, rx in _AREA_EN:
        if rx.search(en):
            return k
    for k, rx in _AREA_FA:
        if fa and rx.search(fa):
            return k
    return None


def _head(m):
    """(English headline, Persian headline) of a report."""
    en = m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or ""
    fa = to_latin_digits(fa_norm(m.get("ti") or "")) if m.get("lang") == "fa" else ""
    return en, fa


def plural(m):
    en, fa = _head(m)
    return bool(_PLURAL_EN.search(en) or (fa and _PLURAL_FA.search(fa)))


def another(m):
    """The headline tells of another, a second or a new incident."""
    en, fa = _head(m)
    return bool(_ANOTHER_EN.search(en) or (fa and _ANOTHER_FA.search(fa)))


def iran_claim(m):
    """An Iranian body's own account (the IRGC or the army saying tankers hit mines), or a headline about mines."""
    en, fa = _head(m)
    if _MINE_EN.search(en) or (fa and _MINE_FA.search(fa)):
        return True
    return bool(_IRAN_SAYS_EN.search(en) or (fa and _IRAN_SAYS_FA.search(fa)))


def general(m):
    """The sea area of a report about something that happened to one ship that gives no precise place, or None:
    not several ships, not another incident, not an Iranian claim or a report about mines."""
    en, fa = _head(m)
    if not (SHIP_EN.search(en) or (fa and SHIP_FA.search(fa))):
        return None
    if not (_HAPPENED_EN.search(en) or (fa and _HAPPENED_FA.search(fa))):
        return None
    if plural(m) or another(m) or iran_claim(m) or mark(m):
        return None
    return area(m, head=True)


# what a report adds to an incident already told: a sinking, people hurt, who did it, how
FACTS_EN = [("sank", r"\b(sank|sinks|sinking|sunk|capsiz\w+|submerged)\b"),
            ("hurt", r"\b(killed|dead|deaths?|died|injur\w+|wounded|missing|casualt\w+)\b"),
            ("who", r"\b(claims? responsibility|claimed responsibility|blam\w+|attribut\w+|behind the attack)\b"),
            ("explosive", r"\b(explosives?|limpets?)\b"), ("mine", r"\bmines?\b"), ("drone", r"\bdrones?\b"),
            ("missile", r"\bmissiles?\b"), ("projectile", r"\bprojectiles?\b"),
            ("boat", r"\b(small boat|skiff|speedboat|fast boat|boarded|boarding)\b"), ("seized", r"\bseiz\w+\b")]
FACTS_FA = [("sank", "غرق"), ("hurt", "کشته|جان باخت|زخمی|مجروح|مفقود|تلفات"),
            ("who", "مسئولیت|بر عهده گرفت|عامل حمله"), ("explosive", "مواد منفجره|وسیله انفجاری|وسایل انفجاری"),
            ("mine", "مین"), ("drone", "پهپاد"), ("missile", "موشک"), ("projectile", "پرتابه"),
            ("boat", "قایق"), ("seized", "توقیف")]
_FACTS_EN = [(k, re.compile(v, re.I)) for k, v in FACTS_EN]
_FACTS_FA = [(k, re.compile(fa_norm(v))) for k, v in FACTS_FA]


_NO_HURT_EN = re.compile(r"\b(no|without|zero)\s+(?:\w+\s+){0,2}(injur\w+|casualt\w+|deaths?|fatalit\w+)"
                         r"|\b(not|no one|nobody)\s+(?:\w+\s+){0,2}(injured|hurt|killed|harmed)\b|\bunharmed\b", re.I)
_NO_HURT_FA = re.compile(fa_norm("(?:بدون|هیچ|اطلاعاتی درباره|اطلاعاتی در مورد|گزارشی از)") + r"\s*"
                         + fa_norm("(?:تلفات|کشته|زخمی|مصدوم|آسیب)") + r"\S*|" + fa_norm("(?:تلفات|آسیبی)") + r"\S*\s*"
                         + r"(?:" + fa_norm("جانی") + r"\s*)?(?:" + fa_norm("به خدمه") + r"\s*)?"
                         + fa_norm("(?:گزارش نشده|نداشته|نرسید|وارد نشد)"))
_FIRST = re.compile(r"(?<=[.!?؟])\s")


def facts(m):
    """What a report tells beyond "a ship was hit or caught fire", from its headline and first sentence."""
    en_h, fa_h = _head(m)
    en_s = m.get("en_su") or (m.get("su") if m.get("lang") != "fa" else "") or ""
    en = _NO_HURT_EN.sub(" ", en_h + " . " + _FIRST.split(en_s.strip(), 1)[0])
    out = {k for k, rx in _FACTS_EN if rx.search(en)}
    if m.get("lang") == "fa":
        fa_s = to_latin_digits(fa_norm(m.get("su") or ""))
        fa = _NO_HURT_FA.sub(" ", fa_h + " . " + _FIRST.split(fa_s.strip(), 1)[0])
        out |= {k for k, rx in _FACTS_FA if rx.search(fa)}
    return out
