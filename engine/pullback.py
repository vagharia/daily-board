"""Forces taken out of a place, or a place emptied, for fear of an attack: "U.S. aircraft evacuated from second U.K.
base due to Iran threat", «فرار هواپیماهای نظامی آمریکا از دومین پایگاه انگلیس», "US moves refueling tankers from UK
base over Iran threat". Read from the headline only, in the report's own language.

Where it happens decides how much it matters (classify.py): out of a Middle East country it is an evacuation (red,
the evacuation lamp); anywhere else (Europe, Diego Garcia, Asia) it is not, orange, or red without the lamp when the
headline gives a threat from Iran as the reason. A report naming a place only as the source of the threat ("Iran
threat") does not place the evacuation there.

mark() labels the event for the bulletin's clustering and the Telegram alerts: whose forces, the country they left,
the base when named, and which round ("second UK base"). Reports with fitting labels tell of one event, whatever
verb they use ("evacuated", "pulls", "moves … from", «فرار», «خارج کرد»)."""
import re

from .util import fa_norm

# --- what is taken out: aircraft of any kind, a base itself, troops (never a ship: "crew evacuated from tanker")
_ASSET_EN = re.compile(r"\b(?:aircraft|air ?planes?|planes?|jets?|warplanes?|fighters?|fighter jets?|bombers?|drones?"
                       r"|refuell?ing (?:planes?|aircraft|tankers?|jets?)|(?:air ?force |aerial |air )?tankers?"
                       r"|airlifters?|[fbc]-\d+[a-z]?s?|kc-\d+[a-z]?s?"
                       r"|troops|forces|personnel|service ?members|soldiers)\b", re.I)
_ASSET_FA = re.compile(fa_norm(r"هواپیما|هواگرد|جنگنده|بمب\s*افکن|سوخت\s*رسان|تانکر\s*سوخت|پهپاد|نیروها|نیروهای"
                               r"|سربازان|نظامیان|اف\s*\d+|بی\s*\d+"))
# a base emptied: only as the place left ("from … base", "evacuated its second base", «از … پایگاه», «پایگاه … را
# تخلیه کرد»), never as where someone was taken ("moved to a military base", «به پایگاه»)
_BASE_OUT_EN = re.compile(r"\b(?:from|out of|left|leaves?|leaving|evacuat\w*|abandon\w*|empt\w*)\s+(?:[\w'.-]+\s+){0,4}?"
                          r"(?:air ?bases?|bases?|airbases?|airfields?)\b|\b(?:air ?bases?|bases?|airbases?|airfields?)\s+"
                          r"(?:is |was |were |are |being |been )*(?:evacuated|emptied|abandoned)\b", re.I)
_BASE_OUT_FA = re.compile(fa_norm(r"(?<!\S)از\s+(?:\S+\s+){0,3}?پایگاه|پایگاه(?:\s+\S+){0,5}?\s+را\s+(?:«?ترک»?|تخلیه|رها)"
                                  r"|تخلیه\s+(?:\S+\s+){0,2}?پایگاه"))
_SHIP_EN = re.compile(r"\b(?:oil tankers?|vessels?|ships?|crews?|strait|hormuz|sea|gulf of|port|lng|crude|supertankers?)\b",
                      re.I)
_SHIP_FA = re.compile(fa_norm(r"(?<!\S)(?:نفتکش|کشتی|خدمه|تنگه|دریای|دریا(?!\S)|بندر)"))     # not «دریافت»
# people taken out (staff, diplomats, citizens): an evacuation too, but never labelled as a pullback of forces
_PEOPLE_EN = re.compile(r"\b(?:embass\w+|consulat\w+|diplomat\w*|staff|citizens|nationals|employees|families|americans"
                        r"|britons|expats|dependents)\b", re.I)
_PEOPLE_FA = re.compile(fa_norm(r"سفارت|کنسولگری|دیپلمات|کارکنان|کارمندان|اتباع|شهروندان|خانواده"))

# --- the verbs: taken out (any of these), or moved "from" a place (only with "from" / "out of")
_OUT_EN = re.compile(r"\b(?:evacuat\w*|withdr[ae]w\w*|withdrawn|pull(?:s|ed|ing)?\b(?:\s+\w+){0,4}?\s+(?:out|from)"
                     r"|flee\w*|fled|escap\w*|abandon\w*|left|leav(?:e|es|ing))\b", re.I)
_MOVE_EN = re.compile(r"\b(?:mov(?:e|es|ed|ing)|remov(?:e|es|ed|ing)|relocat\w*|reposition\w*|shift\w*|redeploy\w*|pull(?:s|ed|ing)?"
                      r"|takes?|took|fl(?:y|ies|ew|own))\b(?:\s+[\w'-]+){0,5}?\s+(?:from|out of)\b", re.I)
_RUN_EN = re.compile(r"\b(?:evacuat\w*|flee\w*|fled|escap\w*|abandon\w*)\b", re.I)   # gone in haste
_OUT_FA = re.compile(fa_norm(r"تخلیه|فرار|خروج|خارج\s*(?:کرد|کردند|شد|شدند|می\s*کند|می\s*کنند|کرده|شده)|بیرون\s*(?:برد|بردند|کشید)"
                             r"|«?ترک»?\s*(?:کرد|کردند|کرده|می\s*کنند)|عقب\s*نشینی|جابجایی|جابه\s*جایی|جا\s*به\s*جایی|انتقال|منتقل"))
_RUN_FA = re.compile(fa_norm(r"تخلیه|فرار"))
_FROM_FA = re.compile(fa_norm(r"(?:^|\s)از\s"))

# --- why: a threat or fear of Iran (the place it names is the threat's source, not where forces were taken from)
_IRAN_W = r"(?:iran\w*|tehran|irgc|the islamic republic)"
_CAUSE_EN = re.compile(r"(?:\b(?:alleged |reported |possible |potential |an? |the )*" + _IRAN_W + r"(?:'s|’s)?(?:\s+[\w-]+)?\s+"
                       r"(?:threat\w*|attacks?|retaliat\w*|strikes?|missiles?|drones?|plots?)\b"
                       r"|\b(?:threat\w*|attacks?|retaliat\w*|fears?|risk|danger)\s+(?:from|by|of)\s+(?:an?\s+|the\s+)?"
                       + _IRAN_W + r"\b|\bfear(?:s|ing)?\s+(?:of\s+)?" + _IRAN_W + r"\b)", re.I)
_CAUSE_FA = re.compile(fa_norm(r"(?:تهدید\S*|بیم|ترس|نگرانی\S*|هراس|حمل\S*|انتقام)(?:\s+\S+){0,3}?\s+(?:ایران|تهران|سپاه|جمهوری اسلامی)"))
# any danger given as the reason (for a pullback inside the Middle East; a routine drawdown has none)
_RISK_EN = re.compile(r"\b(?:threat\w*|attacks?|fears?|feared|safety|security|tensions?|retaliat\w*|strikes?|danger\w*"
                      r"|precaution\w*|escalat\w*|war)\b", re.I)
_RISK_FA = re.compile(fa_norm(r"تهدید|حمله|حملات|ترس|بیم|نگرانی|امنیت|تنش|احتیاط|خطر|انتقام|جنگ"))

# --- whose forces
_WHO = {"us": (r"u\.?s\.?a?|united states|america\w*|pentagon|centcom|washington|usaf|us air force",
               "آمریکا|امریکا|آمریکایی|امریکایی|ایالات متحده|پنتاگون|سنتکام|واشنگتن"),
        "uk": (r"uk|u\.k\.|britain|british|royal air force", "بریتانیا|انگلیس|انگلیسی|بریتانیایی"),
        "il": (r"israel\w*|idf", "اسرائیل|اسراییل"), "fr": (r"france|french", "فرانسه"),
        "de": (r"germany|german", "آلمان")}
_HOME = {"uk": "uk", "il": "israel", "de": "germany"}           # a country whose forces they are, as a place

# --- where: (English, Persian, Middle East?)
_PLACE = {
    "iraq": (r"iraq\w*|baghdad|erbil|ain al-?asad", "عراق|بغداد|اربیل|عین الاسد", True),
    "syria": (r"syria\w*|damascus", "سوریه|دمشق", True),
    "kuwait": (r"kuwait\w*|ali al-?salem|arifjan", "کویت|علی السالم", True),
    "qatar": (r"qatar\w*|doha|al-?udeid|udeid", "قطر|دوحه|العدید", True),
    "bahrain": (r"bahrain\w*|manama", "بحرین|منامه", True),
    "uae": (r"uae|u\.a\.e\.|emirat\w*|dubai|abu dhabi|al-?dhafra", "امارات|دبی|ابوظبی|الظفره", True),
    "saudi": (r"saudi\w*|riyadh|jeddah|prince sultan", "عربستان|سعودی|ریاض|جده|شاهزاده سلطان", True),
    "oman": (r"oman\w*|muscat|duqm", "عمان|مسقط|دقم", True),
    "jordan": (r"jordan\w*|amman|muwaffaq", "اردن|امان|موفق السلطی", True),
    "israel": (r"israel\w*|tel aviv|jerusalem|nevatim", "اسرائیل|اسراییل|تل آویو|سرزمین های اشغالی|فلسطین اشغالی|نواتیم", True),
    "lebanon": (r"leban\w+|beirut", "لبنان|بیروت", True),
    "yemen": (r"yemen\w*|sanaa|aden", "یمن|صنعا|عدن", True),
    "egypt": (r"egypt\w*|cairo", "مصر|قاهره", True),
    "turkey": (r"turk(?:ey|iye|ish)|t[uü]rkiye|incirlik|ankara", "ترکیه|اینجرلیک|آنکارا", True),
    "cyprus": (r"cyprus|cypriot|akrotiri", "قبرس|آکروتیری", True),       # the bases the war is flown from
    "iran": (r"iran\w*|tehran", "ایران|تهران", True),
    "gulf": (r"the gulf|persian gulf|gulf states|middle east|the region", "خلیج فارس|کشورهای خلیج|خاورمیانه|منطقه", True),
    "uk": (r"uk|u\.k\.|britain|british|england|english|scotland|london|raf \w+|mildenhall|lakenheath|fairford",
           "بریتانیا|انگلیس|انگلستان|لندن|میلدنهال|لیکنهیث|لکنهیث|فیرفورد", False),
    "germany": (r"german\w*|berlin|ramstein|spangdahlem", "آلمان|برلین|رامشتاین", False),
    "italy": (r"ital\w+|aviano|sigonella", "ایتالیا|آویانو|سیگونلا", False),
    "spain": (r"spain|spanish|rota|moron", "اسپانیا|روتا", False),
    "greece": (r"greece|greek|souda|crete", "یونان|سودا|کرت", False),
    "europe": (r"europe\w*|nato|paris|france|brussels|belgium|netherlands|poland|romania",
               "اروپا|ناتو|پاریس|فرانسه|بروکسل|بلژیک|هلند|لهستان|رومانی", False),
    "diego": (r"diego garcia", "دیگو گارسیا", False),
    "asia": (r"japan\w*|okinawa|korea\w*|guam|philippine\w*", "ژاپن|اوکیناوا|کره|گوام|فیلیپین", False),
}
# named bases: (English, Persian) -> base id
_BASES = {"mildenhall": ("mildenhall", "میلدنهال"), "lakenheath": ("lakenheath", "لیکنهیث|لکنهیث"),
          "fairford": ("fairford", "فیرفورد"), "ramstein": ("ramstein", "رامشتاین"), "aviano": ("aviano", "آویانو"),
          "udeid": ("al-?udeid|udeid", "العدید"), "dhafra": ("al-?dhafra", "الظفره"), "incirlik": ("incirlik", "اینجرلیک"),
          "akrotiri": ("akrotiri", "آکروتیری"), "sultan": ("prince sultan", "شاهزاده سلطان"),
          "asad": ("ain al-?asad", "عین الاسد"), "diego": ("diego garcia", "دیگو گارسیا")}
# which round: "second UK base", «دومین پایگاه», "another base", «بار دیگر»
_NTH_EN = [(2, re.compile(r"\b(?:second|2nd|another|once again|again)\b", re.I)),
           (3, re.compile(r"\b(?:third|3rd)\b", re.I)), (1, re.compile(r"\bfirst\b", re.I))]
_NTH_FA = [(2, re.compile(fa_norm(r"دومین|پایگاه دوم|پایگاه دیگر|بار دیگر|دوباره|مجددا"))),
           (3, re.compile(fa_norm(r"سومین|پایگاه سوم"))), (1, re.compile(fa_norm(r"نخستین|اولین")))]

_BASE_EN = r"(?:air ?bases?|bases?|airfields?|military bases?|air stations?|stations?)"
_PL_EN = {k: re.compile(r"\b(?:" + e + r")\b", re.I) for k, (e, _, _) in _PLACE.items()}
_PL_FA = {k: re.compile(r"(?<!\S)(?:" + fa_norm(f) + r")") for k, (_, f, _) in _PLACE.items()}
# a place the evacuation is from or in: "from/in/out of (…) Qatar", "British base", "Britain says its bases"
_AT_EN = {k: re.compile(r"\b(?:from|in|out of|at|leave|leaves|leaving|left|across)\s+(?:the\s+|its\s+|a\s+|an\s+)?"
                        r"(?:[\w'.-]+\s+){0,3}?(?:" + e + r")\b|\b(?:" + e + r")(?:'s|’s)?\s+(?:[\w-]+\s+){0,2}?"
                        + _BASE_EN + r"\b", re.I) for k, (e, _, _) in _PLACE.items()}
_AT_FA = {k: re.compile(fa_norm(r"(?:(?<!\S)(?:از|در)|پایگاه\S*|خاک)\s+(?:\S+\s+){0,3}?(?:" + f + r")"))
          for k, (_, f, _) in _PLACE.items()}
# forces going to the Middle East, or on a mission: a deployment, never a pullback ("B-52s leave Fairford for the Middle
# East", "tankers fly from UK bases to support strikes", «انتقال بمب‌افکن‌ها از انگلیس به خاورمیانه»). Moved on to
# somewhere else (Europe…) it is still a pullback: «سوخت‌رسان‌ها را از انگلیس به چند کشور اروپایی منتقل کرد». Iran is
# never the destination ("due to Iran threat", «به بهانه تهدید ایران»).
_ME_EN = "|".join(e for k, (e, _, me) in _PLACE.items() if me and k != "iran")
_ME_FA = "|".join(f for k, (_, f, me) in _PLACE.items() if me and k != "iran")
_DEST_EN = re.compile(r"\b(?:to|for|toward|towards|into|bound for|head(?:s|ed|ing)? (?:to|for|toward)|en route to)\s+"
                      r"(?:the\s+)?(?:eastern\s+|western\s+)?(?:[\w'.-]+\s+){0,2}?(?:" + _ME_EN + r")\b"
                      r"|\b(?:deploy\w*|dispatch\w*|send(?:s|ing)?|sent|arriv\w*|land(?:s|ed|ing)? (?:in|at)|to support|to join"
                      r"|reinforce\w*|for (?:strikes|operations|missions|attacks)|sorties?|missions?"
                      r"|after (?:strikes|bombing|raids|attacks)|(?:strikes?|raids?|bombing) on)\b", re.I)
_DEST_FA = re.compile(fa_norm(r"(?<!\S)به\s+(?:\S+\s+){0,2}?(?:" + _ME_FA + r")"
                              r"|عازم|راهی|اعزام|ارسال|ورود|فرود|استقرار|پشتیبانی از|ماموریت|برای حمله"))
_WHO_EN = {k: re.compile(r"\b(?:" + e + r")\b", re.I) for k, (e, _) in _WHO.items()}
_WHO_FA = {k: re.compile(r"(?<!\S)(?:" + fa_norm(f) + r")") for k, (_, f) in _WHO.items()}
_BASE_RX = {k: (re.compile(r"\b(?:" + e + r")\b", re.I), re.compile(fa_norm(f))) for k, (e, f) in _BASES.items()}


def _heads(m):
    """(English headline, Persian headline) of a report, each in its own language only."""
    if m.get("lang") == "fa":
        return "", fa_norm(m.get("ti") or "")
    return m.get("en_ti") or m.get("ti") or "", ""


def _strip(rx, t):
    return rx.sub(" ", t) if t else t


def place(lang, head):
    """Where a headline puts an evacuation: ("me" / "far" / None, the countries, a threat from Iran given as the
    reason). A country after "from / in / out of", or before "base"; else one named anywhere that is not the forces'
    own; never Iran when it is named only as the source of the threat."""
    fa = lang == "fa"
    t = fa_norm(head or "") if fa else (head or "")
    cause = (_CAUSE_FA if fa else _CAUSE_EN).search(t)
    rest = _strip(_CAUSE_FA if fa else _CAUSE_EN, t)
    at = {k for k, rx in (_AT_FA if fa else _AT_EN).items() if rx.search(rest)}
    loose = {k for k, rx in (_PL_FA if fa else _PL_EN).items() if rx.search(rest)}
    who = {k for k, rx in (_WHO_FA if fa else _WHO_EN).items() if rx.search(rest)}
    places = at or (loose - {_HOME.get(k) for k in who}) or set()
    if cause:
        places.discard("iran")
    me = {p for p in places if _PLACE[p][2]}
    far = places - me
    return ("me" if me else ("far" if far else None)), sorted(me or far), bool(cause)


def read(lang, head):
    """What a headline tells of forces, people or a place taken out: {"run": evacuated or fled (not merely moved),
    "where": "me" / "far" / None, "places": the countries it was in, "iran": a threat from Iran given as the reason,
    "risk": any danger given as the reason, "mil": forces or a base (not only staff or citizens)}, or None when it
    tells of no such thing."""
    if not head:
        return None
    fa = lang == "fa"
    t = fa_norm(head) if fa else head
    if fa:
        mil = bool(_ASSET_FA.search(t) or _BASE_OUT_FA.search(t))
        if not ((mil or _PEOPLE_FA.search(t)) and _OUT_FA.search(t)) or _SHIP_FA.search(t):
            return None
        if mil and _DEST_FA.search(t):
            return None                              # forces sent somewhere: a deployment
        run = bool(_RUN_FA.search(t))
        if not run and not _FROM_FA.search(t) and not re.search(fa_norm(r"«?ترک»?\s*کرد|خارج"), t):
            return None                              # «انتقال هواپیماها به …»: a move to a place, not out of one
        risk = bool(_CAUSE_FA.search(t) or _RISK_FA.search(t))
    else:
        mil = bool(_ASSET_EN.search(t) or _BASE_OUT_EN.search(t))
        if not (mil or _PEOPLE_EN.search(t)) \
                or (_SHIP_EN.search(t) and not re.search(r"\brefuel|\bair ?force\b|\bair ?base", t, re.I)):
            return None
        if not (_OUT_EN.search(t) or _MOVE_EN.search(t)):
            return None
        if mil and _DEST_EN.search(t):
            return None                              # forces sent somewhere: a deployment
        run = bool(_RUN_EN.search(t))
        risk = bool(_CAUSE_EN.search(t) or _RISK_EN.search(t))
    where, places, iran = place(lang, head)
    return {"run": run, "where": where, "places": places, "iran": iran, "risk": risk, "mil": mil}


def mark(m):
    """(whose forces, the country they left, the base or None, the round or None) of a pullback a report's headline
    tells of. None if the headline tells of no pullback, names no one whose forces they are, or names no one country
    they left ("New details of the escape of American planes from the fear of Iran")."""
    en, fa = _heads(m)
    lang = "fa" if fa else "en"
    head = fa or en
    r = read(lang, head)
    if not r or not r["mil"] or "gulf" in r["places"] or (r["where"] != "far" and not (r["run"] or r["risk"])):
        return None                                  # a drawdown in the region, or "the region" as a whole: no one event
    rest = _strip(_CAUSE_FA if fa else _CAUSE_EN, head)
    who = [k for k, rx in (_WHO_FA if fa else _WHO_EN).items() if rx.search(rest)]
    who = [k for k in who if _HOME.get(k) not in r["places"]]             # "British base": a place, not the forces' owner
    if len(who) != 1:
        return None
    if len(r["places"]) != 1 or r["places"][0] == "iran":
        return None                                  # no one country left ("from Qatar to Saudi Arabia", none named)
    place = r["places"][0]
    base = [k for k, (e, f) in _BASE_RX.items() if (e.search(head) if not fa else f.search(head))]
    nth = next((n for n, rx in (_NTH_FA if fa else _NTH_EN) if rx.search(head)), None)
    return (who[0], place, base[0] if len(base) == 1 else None, nth)


def fits(a, b):
    """Two pullback marks may tell of one event: the same forces, the same country (or one gives none), and no named
    base or round that differs."""
    if a[0] != b[0]:
        return False
    if a[1] and b[1] and a[1] != b[1]:
        return False
    if a[2] and b[2] and a[2] != b[2]:
        return False
    return not (a[3] and b[3] and a[3] != b[3])
