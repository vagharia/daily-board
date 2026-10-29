"""Instant alerts from the main front: Iran's cities and islands, Hormuz and the waters around it, Israel and the
American bases of the region. Separate from the bulletin's stories and their colours, which these never change.

Every new report is read for signs of war at a place: (1) jets, drones or sirens heard, (2) air defence firing or
something intercepted or shot down, (3) missiles launched, (4) an explosion or an impact. What happens at one place
within half an hour is one incident, timed by the clock times citizen reports give, else by the report itself.
An incident is announced on Telegram at once, and again each time it reaches a higher step; the same step somewhere
else is a new incident and announced as well. A post of citizen reports counts when at least two messages come from
the same city, or messages from two cities. When a report of the incident comes from a news outlet (not a Telegram
channel) within half an hour of its first announcement, that confirmation is announced too, once.

The announcements are also kept as a list (state["log"]) for the bulletin."""
import html
import re

from . import witness
from .cluster import blast, channel
from .util import fa_norm, truncate

INCIDENT = 30 * 60          # one incident: the same place within half an hour
CONFIRM_WITHIN = 30 * 60    # a news outlet's report confirms it only this soon after the first announcement
KEEP = 48 * 3600            # incidents and the list are kept two days
TEHRAN = 12600

STEP_FA = {1: "صدا", 2: "پدافند", 3: "پرتاب موشک", 4: "انفجار"}

# places of the main front besides Iran's cities (witness.CITIES): key -> (Persian, English, Persian forms, English
# forms); the general names (Iran, Israel) only when nothing more precise is named
_FRONT = {
    "hormuz": ("تنگه هرمز", "the Strait of Hormuz", ["تنگه هرمز", "هرمز"], ["strait of hormuz", "hormuz"]),
    "persian_gulf": ("خلیج فارس", "the Persian Gulf", ["خلیج فارس"], ["persian gulf", "arabian gulf"]),
    "gulf_oman": ("دریای عمان", "the Gulf of Oman", ["دریای عمان"], ["gulf of oman"]),
    "tel_aviv": ("تل‌آویو", "Tel Aviv", ["تل آویو", "تلاویو"], ["tel aviv"]),
    "haifa": ("حیفا", "Haifa", ["حیفا"], ["haifa"]),
    "jerusalem": ("قدس", "Jerusalem", ["قدس", "اورشلیم", "بیت المقدس"], ["jerusalem"]),
    "dimona": ("دیمونا", "Dimona", ["دیمونا"], ["dimona"]),
    "eilat": ("ایلات", "Eilat", ["ایلات", "ام الرشراش"], ["eilat"]),
    "beersheba": ("بئرشبع", "Beersheba", ["بئرشبع", "بئر السبع"], ["beersheba", "beer sheva"]),
    "ashdod": ("اشدود", "Ashdod", ["اشدود"], ["ashdod"]),
    "ashkelon": ("عسقلان", "Ashkelon", ["عسقلان", "اشکلون"], ["ashkelon"]),
    "nevatim": ("نواتیم", "Nevatim", ["نواتیم"], ["nevatim"]),
    "north_israel": ("شمال اسرائیل", "northern Israel", ["شمال اسرائیل", "شمال سرزمین های اشغالی", "الجلیل"],
                     ["northern israel", "galilee"]),
    "al_udeid": ("پایگاه العدید", "Al Udeid base", ["العدید"], ["al udeid", "al-udeid"]),
    "al_dhafra": ("پایگاه الظفره", "Al Dhafra base", ["الظفره"], ["al dhafra", "al-dhafra"]),
    "ain_asad": ("پایگاه عین الاسد", "Ain al-Asad base", ["عین الاسد"], ["ain al-asad", "ain al asad"]),
    "fifth_fleet": ("مقر ناوگان پنجم آمریکا", "the US Fifth Fleet base", ["ناوگان پنجم"], ["fifth fleet"]),
}
_GENERAL = {"iran": ("ایران", "Iran", ["ایران"], ["iran"]), "israel": ("اسرائیل", "Israel", ["اسرائیل", "اسراییل",
            "سرزمین های اشغالی"], ["israel"])}
_L = r"ؠ-ۿ"


def _rx_fa(forms):
    return re.compile(rf"(?<![{_L}])(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in forms)
                      + rf")(?![{_L}])")


def _rx_en(forms):
    return re.compile(r"\b(?:" + "|".join(re.escape(x) for x in forms) + r")\b", re.I)


_FRONT_RX = [(k, _rx_fa(v[2]), _rx_en(v[3])) for k, v in _FRONT.items()]
_GENERAL_RX = [(k, _rx_fa(v[2]), _rx_en(v[3])) for k, v in _GENERAL.items()]
# another front named in the headline: not the main one, unless an Iranian city is named too
_OTHER_FA = re.compile(fa_norm("لبنان|بیروت|غزه|سوریه|دمشق|یمن|صنعا|حوثی|عراق|بغداد|اربیل|عربستان|ریاض|اردن|کرانه باختری"
                               "|اوکراین|روسیه|کی یف"))
_OTHER_EN = re.compile(r"\b(leban\w*|beirut|gaza|syria\w*|damascus|yemen\w*|sanaa|houthis?|iraq\w*|baghdad|erbil|saudi"
                       r"|riyadh|jordan\w*|west bank|ukrain\w*|russia\w*|kyiv)\b", re.I)

# the steps, strongest first; each with the words that tell it (Persian and English headlines)
_STEPS = [
    (4, "blast", fa_norm("انفجار|منفجر|اصابت|صدای مهیب|موج انفجار"),
     r"\b(explosions?|blasts?|exploded|impacts?|struck|hit by|detonations?)\b"),
    (4, "strike", fa_norm("حمله هوایی|حملات هوایی|حمله موشکی|حملات موشکی|حمله پهپادی|بمباران|هدف قرار گرفت|هدف حمله"),
     r"\b(air ?strikes?|missile strikes?|drone strikes?|strikes? on|(?<!-)bomb(ed|ing|s)?|attacked|raids? on)\b"
     r"|\b(israel\w*|u\.?s\.?|america\w*|iran\w*|irgc)\b[^.;]{0,12}\bstrikes?\b"),
    (3, "launch", fa_norm("پرتاب موشک|شلیک موشک|موشک ها شلیک|موشک ها پرتاب|موشک پرتاب|موشک شلیک|پرتاب شد|شلیک شد"),
     r"\b(launch(ed|es|ing)?|fires?|fired|firing)\b[^.;]{0,25}\bmissiles?\b|\bmissiles?\b[^.;]{0,20}\b(launch(ed|es)?"
     r"|fired)\b|\bmissile launch(es)?\b"),
    (2, "airdef", fa_norm("پدافند|ضدهوایی|ضد هوایی|رهگیری|رهگیر|منهدم|سرنگون"),
     r"\b(air defen[cs]es?|anti-aircraft|intercept\w*|shot down|shoots? down|downed)\b"),
    (1, "jet", fa_norm("جنگنده|جت|هواپیمای نظامی|دیوار صوتی"), r"\b(fighter jets?|warplanes?|jets?|sonic boom)\b"),
    (1, "drone", fa_norm("پهپاد|ریزپرنده"), r"\b(drones?|uavs?)\b"),
    (1, "siren", fa_norm("آژیر|اژیر"), r"\bsirens?\b"),
]
_STEPS = [(n, k, re.compile(fa), re.compile(en, re.I)) for n, k, fa, en in _STEPS]
_WIT_STEP = {"strike": 4, "blast": 4, "launch": 3, "airdef": 2, "jet": 1, "drone": 1, "siren": 1, "infra": 4}
# a report that is not of something happening now
_NOT_NOW = {"denial", "controlled", "past", "speculative", "threat", "analysis", "opinion", "reaction", "verbal",
            "civil_drill", "exercise", "sport", "local_toll", "earnings", "piracy", "far_off"}
_FROM_FA = re.compile(fa_norm("از"))
# not news of something happening now: a court case, an anniversary, figures for a month, a feature
_NOT_NOW_FA = re.compile(fa_norm("کیفرخواست|دادگاه|محاکمه|سالگرد|رکورد|آمار|تحلیل|گزارش ویژه|مستند|سال گذشته"))
_NOT_NOW_EN = re.compile(r"\b(indictment|trial|court|anniversary|record high|record low|statistics|figures|analyst|analysis"
                         r"|explainer|last year|in october|in september|this month|this year)\b", re.I)
# a statement ("Iran FM: …", "… says"): the general names (Iran, Israel) don't make it news of a place
_SAID_FA = re.compile(r"^[^:：]{2,45}[:：]|" + fa_norm("گفت|اعلام کرد|مدعی شد|ادعا"))
_SAID_EN = re.compile(r"^[^:]{2,45}:|\b(says?|said|claims?|claimed|told)\b", re.I)


# energy and other vital infrastructure in the region that Iran may strike directly: named sites, and kinds of site in
# a country ("تأسیسات نفتی عربستان"); key -> (Persian, English, Persian forms, English forms)
INFRA = {
    "ras_tanura": ("راس تنوره", "Ras Tanura", ["راس تنوره", "رأس تنوره"], ["ras tanura"]),
    "abqaiq": ("ابقیق", "Abqaiq", ["ابقیق", "بقیق"], ["abqaiq"]),
    "jubail": ("جبیل", "Jubail", ["جبیل"], ["jubail"]),
    "yanbu": ("ینبع", "Yanbu", ["ینبع"], ["yanbu"]),
    "ras_al_khair": ("راس الخیر", "Ras al-Khair", ["راس الخیر", "رأس الخیر"], ["ras al-khair", "ras al khair"]),
    "khurais": ("خریص", "Khurais", ["خریص"], ["khurais"]),
    "aramco": ("تأسیسات آرامکو", "Aramco facilities", ["آرامکو"], ["aramco"]),
    "fujairah": ("فجیره", "Fujairah", ["فجیره"], ["fujairah"]),
    "ruwais": ("رویس", "Ruwais", ["رویس"], ["ruwais"]),
    "jebel_ali": ("بندر جبل علی", "Jebel Ali port", ["جبل علی"], ["jebel ali"]),
    "barakah": ("نیروگاه اتمی براکه", "Barakah nuclear plant", ["براکه"], ["barakah"]),
    "habshan": ("حبشان", "Habshan", ["حبشان"], ["habshan"]),
    "ras_laffan": ("راس لفان", "Ras Laffan", ["راس لفان", "رأس لفان"], ["ras laffan"]),
    "mesaieed": ("مسیعید", "Mesaieed", ["مسیعید"], ["mesaieed"]),
    "mina_ahmadi": ("مینا الاحمدی", "Mina al-Ahmadi", ["مینا الاحمدی", "میناء الاحمدی"], ["mina al-ahmadi", "mina al ahmadi"]),
    "al_zour": ("الزور", "Al-Zour", ["الزور"], ["al-zour", "al zour"]),
    "sitra": ("پالایشگاه سیتره", "Sitra refinery", ["سیتره", "بپکو"], ["sitra", "bapco"]),
    "duqm": ("دقم", "Duqm", ["دقم"], ["duqm"]),
    "sohar": ("صحار", "Sohar", ["صحار"], ["sohar"]),
    "haifa_refinery": ("پالایشگاه حیفا", "the Haifa refinery", ["پالایشگاه حیفا", "بازان"], ["haifa refinery", "bazan"]),
    "hadera": ("نیروگاه حدیرا", "the Hadera power station", ["حدیرا", "اوروت رابین"], ["hadera", "orot rabin"]),
    "leviathan": ("میدان گازی لویاتان", "the Leviathan gas field", ["لویاتان"], ["leviathan"]),
    "karish": ("میدان گازی کاریش", "the Karish gas field", ["کاریش"], ["karish"]),
    "tamar": ("میدان گازی تامار", "the Tamar gas field", ["تامار"], ["tamar"]),
}
_INFRA_RX = [(k, _rx_fa(v[2]), _rx_en(v[3])) for k, v in INFRA.items()]
_SITE_KINDS = [  # kind -> (Persian name, English name, Persian forms, English forms)
    ("refinery", "پالایشگاه", "refinery", ["پالایشگاه"], [r"refiner(?:y|ies)"]),
    ("oil", "تأسیسات نفتی", "oil facilities", ["تاسیسات نفتی", "میدان نفتی", "میادین نفتی", "پایانه نفتی",
                                                 "پایانه صادرات نفت", "مخازن نفت"],
     [r"oil (?:facilit(?:y|ies)|installations?|fields?|terminals?|depots?|storage)", r"crude terminals?"]),
    ("gas", "تأسیسات گازی", "gas facilities", ["تاسیسات گازی", "میدان گازی", "تاسیسات ال ان جی", "ال ان جی"],
     [r"gas (?:facilit(?:y|ies)|fields?|plants?|installations?)", r"lng (?:plants?|facilit(?:y|ies)|terminals?)"]),
    ("pipeline", "خط لوله", "pipeline", ["خط لوله"], [r"pipelines?"]),
    ("power", "نیروگاه", "power plant", ["نیروگاه"], [r"power (?:plants?|stations?)"]),
    ("water", "تأسیسات آب‌شیرین‌کن", "desalination plant", ["آب شیرین کن", "آب شیرینکن", "تاسیسات آب"],
     [r"desalination"]),
    ("port", "بندر", "port", ["بندر", "اسکله"], [r"ports?", r"harbou?rs?"]),
    ("airport", "فرودگاه", "airport", ["فرودگاه"], [r"airports?"]),
    ("data", "مرکز داده", "data centre", ["مرکز داده", "مراکز داده", "دیتاسنتر", "دیتا سنتر"], [r"data cent(?:er|re)s?"]),
    ("tech", "زیرساخت فناوری", "technology site", ["شرکت فناوری", "پارک فناوری", "زیرساخت فناوری", "زیرساخت های فناوری",
                                                     "مخابرات", "کابل"],
     [r"tech(?:nology)? (?:hub|compan(?:y|ies)|firms?|parks?|sites?|infrastructure)", r"telecoms?\w*"]),
    ("industry", "تأسیسات صنعتی", "industrial site", ["کارخانه", "منطقه صنعتی", "مجتمع صنعتی", "پتروشیمی"],
     [r"factor(?:y|ies)", r"industrial (?:zone|site|plant)s?", r"petrochemical\w*"]),
    ("company", "شرکت", "company", ["شرکت"], [r"compan(?:y|ies)|firms?"]),
    ("site", "زیرساخت", "infrastructure", ["زیرساخت", "تاسیسات"], [r"infrastructure", r"facilit(?:y|ies)", r"installations?"]),
]
_SITE_KINDS = [(k, fa, en, re.compile("|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in faf)),
                re.compile(r"\b(?:" + "|".join(enf) + r")\b", re.I)) for k, fa, en, faf, enf in _SITE_KINDS]
_GULF = {  # country -> (Persian, English, Persian forms, English forms)
    "sa": ("عربستان", "Saudi Arabia", ["عربستان", "سعودی"], ["saudi"]),
    "ae": ("امارات", "the UAE", ["امارات"], ["uae", "emirati", "emirates", "abu dhabi", "dubai"]),
    "qa": ("قطر", "Qatar", ["قطر"], ["qatar\\w*"]),
    "kw": ("کویت", "Kuwait", ["کویت"], ["kuwait\\w*"]),
    "bh": ("بحرین", "Bahrain", ["بحرین"], ["bahrain\\w*"]),
    "om": ("عمان", "Oman", ["عمان"], ["oman\\w*"]),
    "il": ("اسرائیل", "Israel", ["اسرائیل", "اسراییل", "سرزمین های اشغالی"], ["israel\\w*"]),
    "iq": ("عراق", "Iraq", ["عراق", "اقلیم کردستان", "کردستان عراق"], ["iraq\\w*", "kurdistan region"]),
    "jo": ("اردن", "Jordan", ["اردن"], ["jordan\\w*"]),
    "az": ("جمهوری آذربایجان", "Azerbaijan", ["جمهوری آذربایجان", "باکو"], ["azerbaijan\\w*", "baku"]),
}
# cities in those countries a strike may name
_ABROAD = {
    "riyadh": ("ریاض", "Riyadh", ["ریاض"], ["riyadh"]), "jeddah": ("جده", "Jeddah", ["جده"], ["jeddah"]),
    "dammam": ("دمام", "Dammam", ["دمام"], ["dammam"]), "dhahran": ("ظهران", "Dhahran", ["ظهران"], ["dhahran"]),
    "dubai": ("دبی", "Dubai", ["دبی"], ["dubai"]), "abu_dhabi": ("ابوظبی", "Abu Dhabi", ["ابوظبی", "ابوظبی"], ["abu dhabi"]),
    "doha": ("دوحه", "Doha", ["دوحه"], ["doha"]), "manama": ("منامه", "Manama", ["منامه"], ["manama"]),
    "kuwait_city": ("کویت", "Kuwait City", [], ["kuwait city"]), "muscat": ("مسقط", "Muscat", ["مسقط"], ["muscat"]),
    "erbil": ("اربیل", "Erbil", ["اربیل", "اربیل"], ["erbil", "irbil"]), "baghdad": ("بغداد", "Baghdad", ["بغداد"], ["baghdad"]),
    "sulaymaniyah": ("سلیمانیه", "Sulaymaniyah", ["سلیمانیه"], ["sulaymaniyah", "sulaimaniyah"]),
    "amman": ("امان", "Amman", [], ["amman"]),
}
_ABROAD_RX = [(k, _rx_fa(v[2]) if v[2] else None, _rx_en(v[3])) for k, v in _ABROAD.items()]
# the places of the main front abroad: Israel's cities and America's bases
_FRONT_ABROAD = [k for k in _FRONT if k not in ("hormuz", "persian_gulf", "gulf_oman")]
_GULF_RX = [(k, _rx_fa(v[2]), re.compile(r"\b(?:" + "|".join(v[3]) + r")\b", re.I)) for k, v in _GULF.items()]
# Iran as the one striking; not the Houthis (their attacks on Saudi Arabia are another front)
_IRAN_FA = re.compile(fa_norm("ایران|سپاه|ارتش جمهوری اسلامی|نیروی هوافضا"))
_IRAN_EN = re.compile(r"\b(iran\w*|irgc|revolutionary guards?|tehran)\b", re.I)
_HOUTHI_FA = re.compile(fa_norm("حوثی|یمن|انصارالله|صنعا"))
_HOUTHI_EN = re.compile(r"\b(houthis?|yemen\w*|ansar ?allah|sanaa)\b", re.I)
_HIT_FA = re.compile(fa_norm("حمله|حملات|هدف قرار|اصابت|انفجار|آتش|بمباران|موشک|پهپاد"))
_HIT_EN = re.compile(r"\b(attack\w*|strikes?|struck|hit|hits|targeted|targets?|explosions?|blasts?|fire|ablaze|missiles?"
                     r"|drones?)\b", re.I)
_PROXY_FA = re.compile(fa_norm("متحدان|نیروهای نیابتی|گروه های نیابتی|حامیان"))
_PROXY_EN = re.compile(r"\b(allies|proxies|proxy|backed)\b", re.I)
_SPEAKER_EN = re.compile(r"^\W*[\w' .-]{2,30}?\b(says?|said|claims?|claimed|reports?|reported)\b\s*", re.I)
_TOWARD_FA = re.compile(fa_norm("به سمت|به سوی"))
_TOWARD_EN = re.compile(r"\b(towards?|aimed at|fired at|launched at)\b|\b(fires?|fired|launch\w*)\b[^.;]{0,25}\bat\b", re.I)


def _object_of_strike(p, fa_t, en_t):
    """The place is what was struck: named right after on/in/at/near/hit, or «به/در/حوالی/نزدیک»."""
    v = witness.CITIES.get(p) or _FRONT.get(p)
    if not v:
        return False
    if fa_t:
        forms = "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in [v[0], *v[2]])
        if re.search(fa_norm("(?:به|در|حوالی|نزدیک|اطراف|بر)") + r"\s*(?:\S+\s+){0,2}(?:" + forms + ")", fa_t):
            return True
    if en_t:
        forms = "|".join(re.escape(x) for x in [v[1].lower(), *v[3]])
        if re.search(r"\b(?:on|in|at|near|over|hits?|struck|strikes?|targets?|targeted)\s+(?:\S+\s+){0,2}(?:" + forms + r")\b",
                     en_t, re.I):
            return True
    return False


_OTHER_SIDE_FA = re.compile(fa_norm("اسرائیل|اسراییل|صهیونیست|آمریکا|امریکا"))
_OTHER_SIDE_EN = re.compile(r"\b(israel\w*|idf|u\.?s\.?|america\w*|pentagon|centcom)\b", re.I)
_BY_IRAN_FA = re.compile(fa_norm("(?:حمله|حملات|اصابت|شلیک)\\s*(?:موشکی|پهپادی|هوایی|موشک|پهپاد)?\\s*(?:های)?\\s*(?:ایران|سپاه)"
                                  "|(?:موشک|پهپاد|راکت)\\s*(?:های)?\\s*ایرانی|(?:ایران|سپاه)[^.؛]{0,50}"
                                  "(?:را هدف قرار داد|را هدف قرار دادند|را زد|را زدند|حمله کرد|حمله کردند|موشک شلیک کرد"
                                  "|را بمباران کرد|را مورد حمله قرار داد)"))
# "Iran strikes…", "Iranian missiles hit…", "… by Iran"; not "Iranian tanker attacked…", where Iran's is the one hit
_BY_IRAN_EN = re.compile(r"\b(iran|irgc|revolutionary guards?|tehran)\b(?:'s)?(?:\s+(?!to\b)[\w-]+){0,3}\s+(strikes?|struck"
                         r"|attacks?|attacked|hits?|targets?|targeted|fires?|fired|launch\w*|bombs?|bombed)\b"
                         r"|\biranian\s+(missiles?|drones?|strikes?|attacks?|rockets?|barrage|forces|navy|military)\b"
                         r"|\bby (iran|iranian|the irgc)\b", re.I)


def _iran_strikes(fa_t, en_t):
    """Iran is the one striking: it is named, and before Israel or America if they are named ("Israel strikes Iran's
    Abadan refinery" is not)."""
    for t, ir, other in ((fa_t, _IRAN_FA, _OTHER_SIDE_FA), (en_t, _IRAN_EN, _OTHER_SIDE_EN)):
        if not t:
            continue
        a, b = ir.search(t), other.search(t)
        if a and (not b or a.start() < b.start()):
            return True
    return False


def _infra(fa_t, en_t):
    """What a strike abroad hit, most precise first: a named site, a kind of site in a country ("تأسیسات نفتی
    عربستان"), a city, an American base or Israeli city, or the country: [(key, Persian name, English name)]."""
    hit = lambda rf, re_: bool((fa_t and rf is not None and rf.search(fa_t)) or (en_t and re_.search(en_t)))  # noqa: E731
    out = [(k, INFRA[k][0], INFRA[k][1]) for k, rf, re_ in _INFRA_RX if hit(rf, re_)]
    if out:
        return out
    countries = [k for k, rf, re_ in _GULF_RX if hit(rf, re_)]
    cities = [k for k, rf, re_ in _ABROAD_RX if hit(rf, re_)]
    front = [k for k, rf, re_ in _FRONT_RX if k in _FRONT_ABROAD and hit(rf, re_)]
    for kind, kfa, ken, rf, re_ in _SITE_KINDS:
        if hit(rf, re_):
            where = [(c, _ABROAD[c][0], _ABROAD[c][1]) for c in cities[:1]] or \
                    [(c, _GULF[c][0], _GULF[c][1]) for c in countries[:1]] or \
                    [(c, _FRONT[c][0], _FRONT[c][1]) for c in front[:1]]
            if where:
                c, wfa, wen = where[0]
                return [(f"{kind}_{c}", f"{kfa} {wfa}", f"{wen} {ken}")]
            break
    if front:
        return [(k, _FRONT[k][0], _FRONT[k][1]) for k in front[:2]]
    if cities:
        return [(k, _ABROAD[k][0], _ABROAD[k][1]) for k in cities[:2]]
    return [(k, _GULF[k][0], _GULF[k][1]) for k in countries[:1]]


def _infra_events(m, fa_t, en_t, step, kind):
    """Iran striking anything abroad directly: oil, gas, power and water sites, ports, airports, technology sites,
    companies, cities, American bases, Israel. Iran is the subject ("Iranian missiles hit…", "حمله‌ی موشکی ایران
    به…", "سپاه … را هدف قرار داد"), not the Houthis, and not a threat (flags)."""
    if fa_t:
        en_t = ""                           # a Persian report is read in Persian (its English is a machine translation)
    else:
        en_t = _SPEAKER_EN.sub("", en_t)    # "UAE says Iranian missiles struck…": the UAE is the one speaking
    if not ((fa_t and _BY_IRAN_FA.search(fa_t)) or (en_t and _BY_IRAN_EN.search(en_t))) or not _iran_strikes(fa_t, en_t):
        return []
    if (fa_t and (_HOUTHI_FA.search(fa_t) or _PROXY_FA.search(fa_t))) or \
            (en_t and (_HOUTHI_EN.search(en_t) or _PROXY_EN.search(en_t))):
        return []                           # the Houthis, or Iran's allies: not Iran striking directly
    sites = _infra(fa_t, en_t)
    if not sites and "maritime_incident" in set(m.get("flags") or []):
        # Iran striking ships at sea: "Iranian missiles struck oil tankers in the Strait of Hormuz"
        sea = [k for k, rf, re_ in _FRONT_RX if k in ("hormuz", "persian_gulf", "gulf_oman")
               and ((fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t)))]
        sites = [(k, "کشتی‌ها در " + _FRONT[k][0], "ships in " + _FRONT[k][1]) for k in sea[:1]]
    if not sites:
        return []
    toward = (fa_t and _TOWARD_FA.search(fa_t)) or (en_t and _TOWARD_EN.search(en_t))
    if step == 2:
        st, fa_v, en_v = 2, "رهگیری حمله‌ی ایران به ", "Iranian attack intercepted over "
    elif toward and step != 4:
        st, fa_v, en_v = 3, "پرتاب موشک و پهپاد ایران به سمت ", "Iranian missiles and drones fired at "
    else:
        st, fa_v, en_v = 4, "حمله‌ی ایران به ", "Iranian strike on "
    return [{"place": k, "step": st, "kind": "infra", "t": m["t"], "fa": fa_v + nfa, "en": en_v + nen}
            for k, nfa, nen in sites]


def _name(key, lang):
    v = witness.CITIES.get(key) or _FRONT.get(key) or _GENERAL.get(key) or INFRA.get(key) or _ABROAD.get(key) \
        or _GULF.get(key)
    if v is None:
        return key
    return v[0] if lang == "fa" else v[1]


def _places(fa_t, en_t):
    """Main-front places a headline names: Iranian cities and the front's places; Iran or Israel only if nothing
    more precise is named and it isn't a statement. None if it names another front (Iraq, Lebanon, Yemen…)."""
    if (fa_t and _OTHER_FA.search(fa_t)) or (en_t and _OTHER_EN.search(en_t)):
        return set()                        # "Tehran strikes a Kurdish base in Iraq": another front
    cities = witness.cities_in(fa_t, "fa") | witness.cities_in(en_t, "en")
    front = {k for k, rf, re_ in _FRONT_RX if (fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t))}
    out = cities | front
    if "hormuz" in out and "hormuz_island" in out:
        out.discard("hormuz")
    if not out and not ((fa_t and _SAID_FA.search(fa_t)) or (en_t and _SAID_EN.search(en_t))):
        out = {k for k, rf, re_ in _GENERAL_RX if (fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t))}
    return out


def _step(fa_t, en_t):
    for n, k, rf, re_ in _STEPS:
        if (fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t)):
            return n, k
    return 0, None


def _clock(t):
    import time as _t
    return _t.strftime("%H:%M", _t.gmtime(t + TEHRAN))


def _fa_digits(s):
    return s.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _wit_time(m):
    """The latest clock time a post of citizen reports gives, as a moment at or before the post; else the post's."""
    t = m["t"]
    hm = (m.get("wit") or {}).get("times") or []
    if not hm:
        return t
    day = (t + TEHRAN) // 86400 * 86400 - TEHRAN
    best = None
    for x in hm:
        e = day + int(x[:2]) * 3600 + int(x[3:]) * 60
        if e > t + 600:
            e -= 86400
        if 0 <= t - e <= 6 * 3600:
            best = e if best is None else max(best, e)
    return best or t


def _title(kind, step, place, lang, wit, frm):
    p = _name(place, lang)
    if lang == "fa":
        return {"strike": "حمله به " + p, "blast": ("شنیده شدن صدای انفجار در " if wit else "انفجار در ") + p,
                "launch": ("پرتاب موشک از " if frm else "پرتاب موشک در ") + p,
                "airdef": "شلیک پدافند در " + p, "jet": "صدای جنگنده در " + p, "drone": "صدای پهپاد در " + p,
                "siren": "صدای آژیر در " + p}[kind]
    return {"strike": "Strike on " + p, "blast": ("Explosion heard in " if wit else "Explosion in ") + p,
            "launch": ("Missiles launched from " if frm else "Missile launch in ") + p,
            "airdef": "Air defence fire in " + p, "jet": "Jets heard over " + p, "drone": "Drones heard over " + p,
            "siren": "Sirens in " + p}[kind]


def events(m):
    """Signs of war at main-front places in one report: [{place, step, kind, t, fa, en}]."""
    flags = set(m.get("flags") or [])
    w = m.get("wit")
    out = []
    if w:
        if w.get("official"):
            return []
        cities = w.get("cities") or {}
        if not (max(cities.values(), default=0) >= 2 or len(cities) >= 2):
            return []                       # one message alone waits for a second
        t = _wit_time(m)
        for c, kinds in (w.get("ck") or {c: list(w.get("kinds") or {}) for c in cities}).items():
            best = max(kinds, key=lambda k: _WIT_STEP.get(k, 0), default=None)
            if best:
                out.append({"place": c, "step": _WIT_STEP[best], "kind": best, "t": t,
                            "fa": _title(best, _WIT_STEP[best], c, "fa", True, False),
                            "en": _title(best, _WIT_STEP[best], c, "en", True, False)})
        return out
    if flags & _NOT_NOW or not flags & {"kinetic", "maritime_incident", "airspace"} or blast(m):
        return []
    fa_t = fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else ""
    en_t = m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or ""
    if (fa_t and _NOT_NOW_FA.search(fa_t)) or (en_t and _NOT_NOW_EN.search(en_t)):
        return []
    step, kind = _step(fa_t, en_t)
    infra = _infra_events(m, fa_t, en_t, step, kind)
    if infra:
        return infra                        # Iran striking an oil, gas, power or water site, a port
    if not step:
        return []
    places = _places(fa_t, en_t)
    if places == {"iran", "israel"}:
        # "Iran fires missiles at Israel": one event, from the one named first towards the other
        txt = fa_t or en_t.lower()
        names = {k: txt.find(fa_norm(_GENERAL[k][0]) if fa_t else k) for k in places}
        a, b = sorted(places, key=lambda k: names[k] if names[k] >= 0 else 1e9)
        for k in places:                    # "… launched from Iran": the origin is named after "from"
            if re.search((r"\bfrom\s+" + k) if not fa_t else (fa_norm("از") + r"\s*" + fa_norm(_GENERAL[k][0])), txt):
                a, b = k, ({"iran", "israel"} - {k}).pop()
        fa_k = {"strike": "حمله", "blast": "انفجار", "launch": "پرتاب موشک", "airdef": "رهگیری", "jet": "پرواز جنگنده",
                "drone": "پرتاب پهپاد", "siren": "آژیر"}[kind]
        en_k = {"strike": "Strikes", "blast": "Explosions", "launch": "Missiles launched", "airdef": "Interceptions", "jet": "Jets",
                "drone": "Drones launched", "siren": "Sirens"}[kind]
        return [{"place": a, "step": step, "kind": kind, "t": m["t"],
                 "fa": f"{fa_k} از {_name(a, 'fa')} به سمت {_name(b, 'fa')}",
                 "en": f"{en_k} from {_name(a, 'en')} towards {_name(b, 'en')}"}]
    if places & set(witness.CITIES):
        places &= set(witness.CITIES)       # "missiles from Sirik towards Hormuz": the city is the place
    if kind == "strike":
        # a strike names the place it hit ("airstrikes hit Isfahan", "حمله هوایی به اصفهان"), not a capital speaking for
        # its government ("Tehran says…") nor the country in general ("new Iran strikes")
        places = {p for p in places - set(_GENERAL) if _object_of_strike(p, fa_t, en_t)}
    ship = "maritime_incident" in flags and kind in ("strike", "blast")
    for p in places:
        if ship:
            out.append({"place": p, "step": step, "kind": kind, "t": m["t"],
                        "fa": ("حمله به کشتی در " if kind == "strike" else "انفجار کشتی در ") + _name(p, "fa"),
                        "en": ("Ship attacked in " if kind == "strike" else "Ship explosion in ") + _name(p, "en")})
            continue
        frm = bool(fa_t and re.search(_FROM_FA.pattern + r"\s*(?:جزیره\s*)?" + re.escape(fa_norm(_name(p, "fa"))), fa_t)) \
            or bool(en_t and re.search(r"\bfrom\b[^.;]{0,15}" + re.escape(_name(p, "en")), en_t, re.I))
        out.append({"place": p, "step": step, "kind": kind, "t": m["t"], "fa": _title(kind, step, p, "fa", False, frm),
                    "en": _title(kind, step, p, "en", False, frm)})
    return out


DETAIL = 280                 # the line under the headline: at most this many characters


def _detail(ev, m, fa_story=None):
    """What the report itself says, for the line under the alert's headline: citizen reports, how many messages from
    where; a Persian report (a channel's post, an Iranian outlet), its own words; a foreign outlet, its story's
    Persian headline. Returns (its text, the earlier post it replies to); empty when it would only repeat the headline."""
    if m.get("wit"):
        txt = m.get("su") or ""
    elif m.get("lang") == "fa":
        ti, su = (m.get("ti") or "").strip(), (m.get("su") or "").strip()
        if su and fa_norm(su).startswith(fa_norm(ti)[:40]):
            txt = su                        # the text goes on from the headline
        elif su and len(ti) < 160:
            txt = ti.rstrip(" .") + ". " + su
        else:
            txt = ti
    else:
        txt = fa_story or ""
    txt = re.sub(r"\s+", " ", txt).strip()
    prev = ""
    mm = _FOLLOWS.search(txt)               # a reply to an earlier post: "… (در ادامهٔ: the earlier post)"
    if mm and not m.get("wit"):
        txt, prev = txt[:mm.start()].strip(), mm.group(1).strip()
    if fa_norm(txt).strip(" .،") in (fa_norm(ev["fa"]), ""):
        txt = ""
    if not txt and not prev:
        return "", ""
    return truncate(txt, DETAIL), truncate(prev, DETAIL // 2)


_FOLLOWS = re.compile(r"\s*\((?:در ادامهٔ|following):\s*(.+)\)\s*$")


def _message(ev, m, kind_of_alert, fa_story=None):
    """kind_of_alert: 'new', 'up' (a higher step) or 'ok' (confirmed by a news outlet)."""
    src = html.escape(m.get("sn_fa") or m.get("sn") or "")
    at = _fa_digits(_clock(ev["t"]))
    head = {"new": "🔴" if ev["step"] >= 3 else "🟠", "up": "⬆️", "ok": "✅"}[kind_of_alert]
    title = html.escape(ev["fa"])
    txt, prev = (html.escape(x) for x in _detail(ev, m, fa_story))
    quote = channel(m) and not m.get("wit")
    det = (f"\n«{txt}»" if quote else f"\n{txt}") if txt else ""     # a channel's own words, in quotes
    if prev:
        det += f"\nدر ادامهٔ پیام قبلی: «{prev}»"
    if kind_of_alert == "ok":
        return f"✅ <b>تأیید شد: {title}</b>، {at}{det}\n<i>{src}</i>"
    if m.get("wit"):
        tail = f"گزارش‌های مردمی، {src}"
    elif channel(m):
        tail = f"{src} · ⚠️ تأییدنشده"
    else:
        tail = src
    return f"{head} <b>{title}</b>، {at}{det}\n<i>{tail}</i>"


def process(state, items, now_t, story_start=None, quiet=False, fa_story=None):
    """Read this round's new reports. story_start: report key -> when its story was first reported; a report that
    joins a story more than half an hour old tells of something already known (a later account, a recap) and is
    left out. fa_story: report key -> its story's Persian headline (the line under an alert from a foreign outlet).
    Returns (Telegram messages, keys of the reports that are signs of war at the main front: their stories
    don't also get the usual red-story alert)."""
    story_start = story_start or {}
    fa_story = fa_story or {}
    inc = state.setdefault("inc", {})
    log_ = state.setdefault("log", [])
    for p in list(inc):
        if now_t - inc[p]["t1"] > KEEP:
            inc.pop(p)
    state["log"] = log_ = [x for x in log_ if now_t - x["t"] <= KEEP]
    seen = state.setdefault("keys", {})
    for k in [k for k, t in seen.items() if now_t - t > KEEP]:
        seen.pop(k)
    msgs, keys = [], set()
    for m in sorted(items, key=lambda m: m["t"]):
        if m["t"] - story_start.get(m["k"], m["t"]) > INCIDENT:
            continue
        evs = events(m)
        if not evs:
            continue
        keys.add(m["k"])
        seen[m["k"]] = now_t
        news = not channel(m)
        for ev in evs:
            p, t = ev["place"], ev["t"]
            cur = inc.get(p)
            if cur and -INCIDENT <= t - cur["t1"] <= INCIDENT:
                cur["t1"] = max(cur["t1"], t)
                if ev["step"] > cur["step"]:
                    cur["step"] = ev["step"]
                    msgs.append(_message(ev, m, "up", fa_story.get(m["k"])))
                    log_.append({"t": t, "p": p, "s": ev["step"], "fa": ev["fa"], "en": ev["en"], "src": m["s"],
                                 "conf": int(news or cur["conf"])})
                if news and not cur["conf"]:
                    cur["conf"] = 1
                    if now_t - cur["a"] <= CONFIRM_WITHIN:
                        msgs.append(_message(ev, m, "ok", fa_story.get(m["k"])))
                    for x in log_:
                        if x["p"] == p and x["t"] >= cur["t0"]:
                            x["conf"] = 1
            else:
                inc[p] = {"t0": t, "t1": t, "step": ev["step"], "conf": int(news), "a": now_t}
                msgs.append(_message(ev, m, "new", fa_story.get(m["k"])))
                log_.append({"t": t, "p": p, "s": ev["step"], "fa": ev["fa"], "en": ev["en"], "src": m["s"],
                             "conf": int(news)})
    log_.sort(key=lambda x: x["t"])
    return ([] if quiet else msgs), keys


_KIND_NOUN_FA = {"infra": "حمله به زیرساخت", "strike": "حمله", "blast": "انفجار", "launch": "پرتاب موشک", "airdef": "شلیک پدافند", "jet": "صدای جنگنده",
                 "drone": "صدای پهپاد", "siren": "آژیر"}
_KIND_NOUN_EN = {"infra": "strikes on infrastructure", "strike": "strikes", "blast": "explosions", "launch": "missile launches", "airdef": "air defence fire", "jet": "jets",
                 "drone": "drones", "siren": "sirens"}


def story_texts(c):
    """For a main-front story told only by Telegram channels (citizen reports among them): a headline and a summary
    made of all its reports, strongest first ("گزارش‌های تأییدنشده از پرتاب موشک و انفجار در قشم، ۲۲:۴۸ تا ۲۳:۴۴"),
    or None. Once a news outlet reports it, the story takes that outlet's headline as usual."""
    ms = sorted(c["m"], key=lambda m: m["t"])
    if len(ms) < 2 or not all(channel(m) for m in ms):
        return None
    evs = [(e, m) for m in ms for e in events(m)]
    if not evs:
        return None
    kinds = sorted({e["kind"] for e, _ in evs}, key=lambda k: -max(e["step"] for e, _ in evs if e["kind"] == k))
    places = []
    for e, _ in evs:
        if e["place"] not in places:
            places.append(e["place"])
    lo, hi = min(e["t"] for e, _ in evs), max(e["t"] for e, _ in evs)
    def when(fa):
        a, b = _clock(lo), _clock(hi)
        if a == b:
            return f"، ساعت {_fa_digits(a)}" if fa else f", {a} Tehran time"
        return f"، {_fa_digits(a)} تا {_fa_digits(b)}" if fa else f", {a} to {b} Tehran time"
    def join(xs, fa):
        if len(xs) <= 1:
            return "".join(xs)
        return ("، ".join(xs[:-1]) + " و " + xs[-1]) if fa else (", ".join(xs[:-1]) + " and " + xs[-1])
    fa_places = [_name(p, "fa") for p in places[:3]] + (["چند جای دیگر"] if len(places) > 3 else [])
    en_places = [_name(p, "en") for p in places[:3]] + (["other places"] if len(places) > 3 else [])
    fa_ti = (f"گزارش‌های تأییدنشده از {join([_KIND_NOUN_FA[k] for k in kinds], True)} در {join(fa_places, True)}"
             + when(True))
    en_ti = (f"Unconfirmed reports of {join([_KIND_NOUN_EN[k] for k in kinds], False)} in {join(en_places, False)}"
             + when(False))
    chans = []
    for m in ms:
        n = m.get("sn_fa") or m.get("sn") or m["s"]
        if n not in chans:
            chans.append(n)
    parts_fa, parts_en, done = [], [], set()
    for e, m in sorted(evs, key=lambda x: x[0]["t"]):
        if (e["kind"], e["place"]) in done:
            continue
        done.add((e["kind"], e["place"]))
        src = m.get("sn_fa") or m.get("sn") or m["s"]
        parts_fa.append(f"{e['fa']} ({'گزارش‌های مردمی، ' if m.get('wit') else ''}{src}، {_fa_digits(_clock(e['t']))})")
        parts_en.append(f"{e['en']} ({'reports from residents, ' if m.get('wit') else ''}{m.get('sn') or m['s']}, "
                        f"{_clock(e['t'])})")
    n = len(chans)
    fa_su = (f"{_fa_digits(str(n))} کانال تلگرامی: " + "؛ ".join(parts_fa) + ". هنوز هیچ رسانه‌ای گزارشش نکرده.")
    en_su = (f"{n} Telegram channel{'s' if n != 1 else ''}: " + "; ".join(parts_en)
             + ". No news outlet has reported it yet.")
    return {"fa": {"ti": fa_ti, "su": fa_su}, "en": {"ti": en_ti, "su": en_su}}
