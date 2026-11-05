"""Incidents at sea: where one happened, as precisely as the reports say it, so reports of one incident can be told
apart from reports of another.

UKMTO and the outlets that relay it place an incident by its distance and bearing from a port or headland:
"25 nautical miles northeast of Khasab", "۹ مایلی شمال خصب". That is the incident's mark (mark()). Reports that
give no such place ("UK says vessel on fire in Strait of Hormuz") are general reports (general()): about one ship,
in a known sea area, not a recap of several ships nor an Iranian claim of mines.

Used by the bulletin's clustering (cluster.py) and by the Telegram alerts (alerts.py)."""
import re

from .util import fa_norm, to_latin_digits

# reference points UKMTO and others measure from: key -> (English forms, Persian forms, sea area). Sea areas:
# "hormuz" (the strait, its islands and the Gulf of Oman), "gulf" (the Persian Gulf inside the strait), "arabian"
# (the Arabian Sea), "redsea" (the Red Sea, Bab al-Mandab and the Gulf of Aden).
REFS = {
    # the Strait of Hormuz and the Gulf of Oman
    "khasab": (["khasab"], ["خصب"], "hormuz"),
    "musandam": (["musandam"], ["مسندم"], "hormuz"),
    "kumzar": (["kumzar"], ["کمزار"], "hormuz"),
    "bandar abbas": (["bandar abbas"], ["بندرعباس", "بندر عباس"], "hormuz"),
    "qeshm": (["qeshm"], ["قشم"], "hormuz"),
    "larak": (["larak"], ["لارک"], "hormuz"),
    "hormuz island": (["hormuz island", "hormoz island"], ["جزیره هرمز"], "hormuz"),
    "hengam": (["hengam"], ["هنگام"], "hormuz"),
    "abu musa": (["abu musa"], ["ابوموسی", "ابو موسی"], "hormuz"),
    "tunb": (["(?:greater |lesser )?tunbs?"], ["تنب بزرگ", "تنب کوچک", "تنب"], "hormuz"),
    "jask": (["jask"], ["جاسک"], "hormuz"),
    "chabahar": (["chabahar"], ["چابهار"], "hormuz"),
    "fujairah": (["fujairah"], ["فجیره"], "hormuz"),
    "khor fakkan": (["khor ?fakkan"], ["خورفکان", "خور فکان"], "hormuz"),
    "kalba": (["kalba"], ["کلبا"], "hormuz"),
    "dibba": (["dibba", "daba"], ["دبا"], "hormuz"),
    "ras al khaimah": (["ras al[- ]?khaimah"], ["راس الخیمه", "رأس الخیمه"], "hormuz"),
    "limah": (["limah"], ["لیمه"], "hormuz"),
    "sohar": (["sohar"], ["صحار"], "hormuz"),
    "muscat": (["muscat"], ["مسقط"], "hormuz"),
    # the Persian Gulf
    "bandar lengeh": (["bandar lengeh", "lengeh"], ["بندر لنگه", "لنگه"], "gulf"),
    "kish": (["kish"], ["کیش"], "gulf"),
    "lavan": (["lavan"], ["لاوان"], "gulf"),
    "sirri": (["sirri", "siri"], ["سیری"], "gulf"),
    "asaluyeh": (["assaluyeh", "asaluyeh", "asaluyah"], ["عسلویه"], "gulf"),
    "kangan": (["kangan"], ["کنگان"], "gulf"),
    "bushehr": (["bushehr"], ["بوشهر"], "gulf"),
    "kharg": (["kharg"], ["خارک"], "gulf"),
    "sharjah": (["sharjah"], ["شارجه"], "gulf"),
    "dubai": (["dubai"], ["دبی", "دوبی"], "gulf"),
    "jebel ali": (["jebel ali"], ["جبل علی"], "gulf"),
    "abu dhabi": (["abu dhabi"], ["ابوظبی", "ابوظبی"], "gulf"),
    "ruwais": (["ruwais"], ["رویس"], "gulf"),
    "das island": (["das island"], ["جزیره داس"], "gulf"),
    "madinat ash shamal": (["madinat (?:a[shl]{1,2}[- ]?)?shamal", "al[- ]?shamal", "ash[- ]?shamal"],
                           ["مدینه الشمال", "مدینه شمال", "مدینة الشمال", "الشمال"], "gulf"),
    "ras laffan": (["ras laffan"], ["راس لفان", "رأس لفان"], "gulf"),
    "doha": (["doha"], ["دوحه"], "gulf"),
    "mesaieed": (["mesaieed", "umm said"], ["مسیعید"], "gulf"),
    "bahrain": (["bahrain", "manama"], ["بحرین", "منامه"], "gulf"),
    "ras tanura": (["ras tanura", "ras tannurah"], ["راس تنوره", "رأس تنوره"], "gulf"),
    "jubail": (["jubail"], ["جبیل", "الجبیل"], "gulf"),
    "dammam": (["dammam"], ["دمام"], "gulf"),
    "khafji": (["khafji"], ["خفجی"], "gulf"),
    "kuwait": (["kuwait"], ["کویت"], "gulf"),
    "umm qasr": (["umm qasr"], ["ام القصر", "ام قصر"], "gulf"),
    "basra": (["basra", "basrah"], ["بصره"], "gulf"),
    "faw": (["faw", "fao"], ["فاو"], "gulf"),
    # the Arabian Sea
    "ras al hadd": (["ras al[- ]?hadd"], ["راس الحد"], "arabian"),
    "masirah": (["masirah"], ["مصیره"], "arabian"),
    "duqm": (["duqm"], ["دقم"], "arabian"),
    "salalah": (["salalah"], ["صلاله"], "arabian"),
    "socotra": (["socotra"], ["سقطری", "سوقطری"], "arabian"),
    # the Red Sea and the Gulf of Aden
    "mukalla": (["mukalla"], ["مکلا", "المکلا"], "redsea"),
    "nishtun": (["nishtun"], ["نشطون"], "redsea"),
    "aden": (["aden"], ["عدن"], "redsea"),
    "djibouti": (["djibouti"], ["جیبوتی"], "redsea"),
    "mokha": (["mokha", "mocha"], ["مخا"], "redsea"),
    "perim": (["perim", "mayun"], ["میون"], "redsea"),
    "assab": (["assab"], ["عصب"], "redsea"),
    "hodeidah": (["hodeidah", "hudaydah", "hodeida"], ["حدیده", "الحدیده"], "redsea"),
    "salif": (["salif"], ["صلیف", "الصلیف"], "redsea"),
    "ras isa": (["ras isa"], ["راس عیسی", "رأس عیسی"], "redsea"),
    "kamaran": (["kamaran"], ["کمران"], "redsea"),
    "port sudan": (["port sudan"], ["بندر سودان", "پورت سودان"], "redsea"),
    "jeddah": (["jeddah", "jiddah"], ["جده"], "redsea"),
    "yanbu": (["yanbu"], ["ینبع"], "redsea"),
    "eilat": (["eilat"], ["ایلات"], "redsea"),
    "aqaba": (["aqaba"], ["عقبه"], "redsea"),
}
# a country named before the reference point ("of Qatar's Ras Laffan", «قطر»)
_COUNTRY_EN = r"(?:(?:qatar|oman|the uae|uae|saudi arabia|yemen|iran|kuwait|bahrain|eritrea|sudan|djibouti)(?:'s|’s)?\s+)?"
_REF_EN = [(k, re.compile(_COUNTRY_EN + r"(?:" + "|".join(v[0]) + r")\b", re.I)) for k, v in REFS.items()]
_REF_FA = [(k, re.compile(r"[«\"“]?\s*(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in v[1])
                          + r")(?![ء-ۿ])")) for k, v in REFS.items()]

# sea areas named without a distance. Checked in this order: a report about the Persian Gulf near the strait is the
# strait's. A country is a sea area only with words placing the ship by it ("off Qatar", «آب‌های قطر»): a country
# named alone may be the one that condemns or reports the attack.
_OFF_EN = r"\b(?:off|near|by|north of|south of|east of|west of|north-?east of|north-?west of|south-?east of|south-?west of)\s+(?:the\s+)?(?:coast\s+of\s+)?"
_OFF_FA = "(?:آب های|آبهای|سواحل|ساحل|نزدیکی|نزدیک|مقابل|شمال|جنوب|شرق|غرب|شمال شرق|شمال غرب|جنوب شرق|جنوب غرب|حوالی)\\s*"
AREAS = {
    "hormuz": (r"\b(hormuz|hormoz|khasab|musandam|gulf of oman|fujairah|khor ?fakkan|jask|bandar abbas|qeshm|larak"
               r"|ras al[- ]?khaimah|sohar|abu musa|tunbs?|chabahar)\b|" + _OFF_EN + r"oman\b|\b(oman'?s coast|omani waters)\b",
               "هرمز|خصب|مسندم|دریای عمان|فجیره|خورفکان|جاسک|بندرعباس|بندر عباس|قشم|لارک|راس الخیمه|صحار|ابوموسی|ابو موسی"
               "|تنب|چابهار|" + _OFF_FA + "عمان"),
    "gulf": (r"\b(persian gulf|arabian gulf|ras laffan|ras tanura|jubail|bushehr|kharg|assaluyeh|asaluyeh|kish island"
             r"|lavan|sirri|jebel ali|ruwais|das island|madinat (?:a[shl]{1,2}[- ]?)?shamal|umm qasr|khafji|bandar lengeh)\b|"
             + _OFF_EN + r"(?:qatar|bahrain|kuwait|saudi arabia|the uae|uae|emirates|abu dhabi|dubai|sharjah|iraq)\b"
             r"|\b(qatari|bahraini|kuwaiti|saudi|emirati|iraqi) (waters|coast)\b|\bwaters (?:off|of) (qatar|bahrain|kuwait)\b",
             "خلیج فارس|راس لفان|رأس لفان|راس تنوره|جبیل|بوشهر|خارک|عسلویه|جزیره کیش|لاوان|جزیره سیری|جبل علی|الشمال"
             "|ام القصر|بندر لنگه|" + _OFF_FA + "(?:قطر|بحرین|کویت|عربستان|امارات|ابوظبی|دبی|دوبی|شارجه|عراق|بوشهر)"),
    "arabian": (r"\b(arabian sea|salalah|duqm|socotra|masirah|ras al[- ]?hadd)\b", "دریای عرب|دریای عربی|صلاله|دقم|سقطری|مصیره|راس الحد"),
    "redsea": (r"\b(red sea|gulf of aden|bab[- ]?(?:al|el)[- ]?mandab|bab[- ]?(?:al|el)[- ]?mandeb|hodeidah|aden|mokha"
               r"|salif|ras isa|kamaran|port sudan|yanbu|eilat|mukalla)\b|" + _OFF_EN + r"(?:yemen|eritrea|djibouti)\b",
               "دریای سرخ|بحر احمر|خلیج عدن|باب المندب|حدیده|عدن|صلیف|راس عیسی|ینبع|ایلات|" + _OFF_FA + "(?:یمن|اریتره|جیبوتی)"),
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
    r"(?:(?:بندر|شهر|جزیره|سواحل|ساحل|منطقه)\s*)?[«\"“]?\s*([ء-ۿ][ء-ۿ ]{1,25})")

SHIP_EN = re.compile(r"\b(vessels?|ships?|tankers?|dhows?|boats?|carriers?|freighters?|bulkers?|bulk carriers?"
                     r"|merchant|supertankers?|lng carriers?)\b", re.I)
SHIP_FA = re.compile(r"(?<![\u0621-\u06FF])(?:" + fa_norm("نفتکش|نفت کش|کشتی|شناور|شناورها|لنج|تانکر|ناو|ناوها|ناوهای"
                     "|ناوشکن|قایق|قایق ها|سوپرتانکر|سوپر نفتکش|ابرنفتکش") + r")(?![\u0621-\u06FF])")
_PLURAL_EN = re.compile(r"\b(vessels|ships|tankers|dhows|boats|carriers|freighters|supertankers)\b"
                        r"|\b(?:vessel|ship|tanker|shipping)\s+(?:attacks|incidents|strikes|seizures)\b"
                        r"|\b(two|three|four|five|six|several|multiple|\d+)\s+(?:\w+\s+)?(vessels|ships|tankers)", re.I)
_PLURAL_FA = re.compile(fa_norm("نفتکش ها|نفت کش ها|کشتی ها|شناورها|شناور ها|لنج ها|تانکرها|تانکر ها")
                        + r"|(?:\d+|" + fa_norm("دو|سه|چهار|پنج|چند") + r")\s*(?:" + fa_norm("فروند") + r"\s*)?"
                        + fa_norm("(?:نفتکش|نفت کش|کشتی|شناور|تانکر)"))
# ------------------------------------------------------------------ what kind of ship, its flag, its name
# Kinds of ship a headline names. Kinds of one family can be one ship told in other words (a "tanker" may be a
# super tanker or an LNG tanker; a "cargo ship" a container ship); kinds of different families never are.
KINDS_EN = [
    ("super", r"\bsuper[- ]?tankers?\b|\bvlccs?\b|\bulccs?\b|\bvery large crude (?:carrier|tanker)s?\b"),
    ("lng", r"\b(?:lng|lpg|gas)\s+(?:carrier|tanker|vessel|ship)s?\b|\bgas carriers?\b"),
    ("tanker", r"(?<!lng )(?<!lpg )(?<!gas )(?<!super )(?<!super-)\btankers?\b|\b(?:oil|crude|product|chemical) (?:carrier|vessel|ship)s?\b"),
    ("container", r"\bcontainer\s*(?:ship|vessel|carrier)s?\b|\bboxships?\b"),
    ("bulk", r"\bbulk(?:\s+carrier)?s?\b|\bbulkers?\b"),
    ("carcarrier", r"\b(?:car|vehicle) carriers?\b|\bro-?ro\b"),
    ("cargo", r"\b(?:cargo|general cargo) (?:ship|vessel)s?\b|\bfreighters?\b"),
    ("tug", r"\btug(?:boat)?s?\b"),
    ("dhow", r"\bdhows?\b"),
    ("fishing", r"\bfishing (?:boat|vessel|ship|trawler)s?\b|\btrawlers?\b"),
    ("usv", r"\b(?:drone|unmanned|uncrewed|explosive|suicide)[- ](?:surface )?(?:boat|vessel|craft)s?\b|\busvs?\b"
            r"|\b(?:sea|naval|maritime|water) drones?\b|\bdrone vessels?\b"),
    ("war", r"\bwarships?\b|\bdestroyers?\b|\bfrigates?\b|\bcorvettes?\b|\bminesweepers?\b|\baircraft carriers?\b"
            r"|\bnaval (?:ship|vessel)s?\b|\buss\s+[a-z]"),
]
KINDS_FA = [
    ("super", "سوپرتانکر|سوپر تانکر|سوپر نفتکش|سوپرنفتکش|ابرنفتکش|ابر نفتکش|نفتکش غول پیکر|vlcc"),
    ("lng", "نفتکش های گاز|نفتکش گاز|تانکر گاز|تانکرهای گاز|کشتی حامل گاز|کشتی گازبر|گازبر|حامل ال ان جی|ال ان جی|lng|lpg|حامل گاز مایع|نفتکش گازی|کشتی گاز"),
    ("tanker", "نفتکش|نفت کش|تانکر|کشتی حامل نفت|کشتی نفتی|کشتی سوخت|سوخت کش"),
    ("container", "کانتینربر|کانتینر بر|کشتی کانتینری|کشتی کانتینر"),
    ("bulk", "فله بر|کشتی فله"),
    ("carcarrier", "خودروبر|کشتی حمل خودرو"),
    ("cargo", "کشتی باری|کشتی کالا|باربری"),
    ("tug", "یدک کش|یدککش"),
    ("dhow", "لنج"),
    ("fishing", "قایق ماهیگیری|کشتی ماهیگیری|صیادی|صیاد"),
    ("usv", "شمپاد|شناور بدون سرنشین|شناورهای بدون سرنشین|قایق بدون سرنشین|قایق انتحاری|پهپاد دریایی|شناور انتحاری"),
    ("war", "ناوشکن|ناوچه|رزمناو|ناو هواپیمابر|کشتی جنگی|ناو جنگی|(?<![ء-ۿ])ناو(?:های)?(?![ء-ۿ])|مین روب"),
]
_KINDS_EN = [(k, re.compile(v, re.I)) for k, v in KINDS_EN]
_KINDS_FA = [(k, re.compile(fa_norm(v), re.I)) for k, v in KINDS_FA]
_FAMILY = {"super": "oil", "lng": "oil", "tanker": "oil", "container": "dry", "bulk": "dry", "carcarrier": "dry",
           "cargo": "dry", "tug": "tug", "dhow": "dhow", "fishing": "fishing", "war": "war", "usv": "usv"}
_GENERAL = {"tanker", "cargo"}          # a kind that also stands for the others of its family


def kinds(m):
    """The kinds of ship a report's headline names: {"tanker", "super", "lng", "container", …}; empty for "vessel",
    "ship", "merchant vessel"."""
    en, fa = _head(m)
    out = set()
    for kl, txt in ((_KINDS_EN, en), (_KINDS_FA, fa)):
        for k, rx in kl:                    # a phrase found is taken out: «سوپر نفتکش» is no plain «نفتکش» too
            if txt and rx.search(txt):
                out.add(k)
                txt = rx.sub(" ", txt)
    return frozenset(out)


def _kind_ok(a, b):
    if a == b:
        return True
    if _FAMILY[a] != _FAMILY[b]:
        return False
    return a in _GENERAL or b in _GENERAL


def kinds_fit(a, b):
    """Two reports' kinds of ship can be one ship: either names none, or some kind of one fits some kind of the other
    (a tanker and a super tanker; not a tanker and a container ship, nor a super tanker and an LNG carrier)."""
    if not a or not b:
        return True
    return any(_kind_ok(x, y) for x in a for y in b)


# the flag a ship flies, in English and Persian: "Liberian-flagged", "flagged in Panama", «با پرچم لیبریا»
FLAGS = {
    "liberia": (["liberia", "liberian"], ["لیبریا"]), "panama": (["panama", "panamanian"], ["پاناما", "پاناما"]),
    "marshall": (["marshall islands?"], ["جزایر مارشال", "مارشال"]), "malta": (["malta", "maltese"], ["مالت"]),
    "greece": (["greek", "greece"], ["یونان"]), "bahamas": (["bahamas", "bahamian"], ["باهاما"]),
    "hongkong": (["hong kong"], ["هنگ کنگ", "هنگکنگ"]), "singapore": (["singapore", "singaporean"], ["سنگاپور"]),
    "comoros": (["comoros"], ["کومور"]), "togo": (["togo", "togolese"], ["توگو"]), "palau": (["palau"], ["پالائو"]),
    "cameroon": (["cameroon"], ["کامرون"]), "sierraleone": (["sierra leone"], ["سیرالئون"]),
    "gabon": (["gabon", "gabonese"], ["گابن"]), "china": (["china", "chinese"], ["چین"]),
    "india": (["india", "indian"], ["هند"]), "iran": (["iran", "iranian"], ["ایران"]),
    "uk": (["british", "uk", "united kingdom"], ["انگلیس", "بریتانیا"]), "us": (["us", "u\\.s\\.", "american"], ["آمریکا"]),
    "saudi": (["saudi", "saudi arabia"], ["عربستان"]), "uae": (["uae", "emirati"], ["امارات"]),
    "qatar": (["qatar", "qatari"], ["قطر"]), "norway": (["norway", "norwegian"], ["نروژ"]),
    "cyprus": (["cyprus", "cypriot"], ["قبرس"]), "portugal": (["portugal", "portuguese"], ["پرتغال"]),
    "antigua": (["antigua"], ["آنتیگوا"]), "barbados": (["barbados"], ["باربادوس"]),
    "vietnam": (["vietnam", "vietnamese"], ["ویتنام"]), "pakistan": (["pakistan", "pakistani"], ["پاکستان"]),
    "turkey": (["turkey", "turkish"], ["ترکیه"]), "russia": (["russia", "russian"], ["روسیه"]),
}
_FLAG_EN = [(k, re.compile(r"\b(?:" + "|".join(v[0]) + r")[- ]flagged\b|\bflagged (?:in|by|to) (?:the )?(?:"
                           + "|".join(v[0]) + r")\b|\b(?:" + "|".join(v[0]) + r") flag\b", re.I)) for k, v in FLAGS.items()]
_FLAG_FA = [(k, re.compile(fa_norm("(?:(?:با|تحت|دارای|حامل) پرچم|پرچم دار|پرچمدار|پرچم)") + r"\s*(?:کشور\s*)?(?:"
                           + "|".join(fa_norm(x) for x in v[1]) + r")(?![ء-ۿ])")) for k, v in FLAGS.items()]


def flag(m):
    """The flag the ship of a report flies, as a country key, if the report says so; else None."""
    en, fa = _texts(m)
    for k, rx in _FLAG_EN:
        if rx.search(en):
            return k
    for k, rx in _FLAG_FA:
        if fa and rx.search(fa):
            return k
    return None


# whose ship it is: "Qatari LNG tanker", "Iranian vessel", "a tanker belonging to Iran", «نفتکش قطری», «متعلق به ایران»
OWNERS = {"iran": (["iranian", "iran's"], ["ایرانی", "ایران"]), "qatar": (["qatari", "qatar's"], ["قطری", "قطر"]),
          "saudi": (["saudi"], ["سعودی", "عربستان"]), "uae": (["emirati", "uae"], ["اماراتی", "امارات"]),
          "kuwait": (["kuwaiti"], ["کویتی", "کویت"]), "india": (["indian"], ["هندی", "هند"]),
          "pakistan": (["pakistani"], ["پاکستانی", "پاکستان"]), "china": (["chinese"], ["چینی", "چین"]),
          "greece": (["greek"], ["یونانی", "یونان"]), "us": (["american", "us", "u\\.s\\."], ["آمریکایی", "آمریکا"]),
          "uk": (["british"], ["انگلیسی", "بریتانیایی", "انگلیس"]), "israel": (["israeli", "israel-linked", "israeli-linked"],
          ["اسرائیلی", "صهیونیستی", "اسرائیل"]), "oman": (["omani"], ["عمانی", "عمان"]), "iraq": (["iraqi"], ["عراقی", "عراق"]),
          "japan": (["japanese"], ["ژاپنی", "ژاپن"]), "korea": (["south korean", "korean"], ["کره ای", "کره"]),
          "turkey": (["turkish"], ["ترکیه ای", "ترکیه"]), "russia": (["russian"], ["روسی", "روسیه"])}
_SHIPW_EN = r"(?:(?:oil|crude|lng|lpg|gas|cargo|container|merchant|commercial|fishing)\s+)?(?:super)?(?:tankers?|vessels?|ships?|carriers?|freighters?|dhows?|boats?)"
_OWNER_EN = [(k, re.compile(r"\b(?:" + "|".join(v[0]) + r")\s+(?:[\w-]+\s+){0,1}" + _SHIPW_EN + r"\b|\b" + _SHIPW_EN
                            + r"\s+(?:owned by|belonging to|operated by)\s+(?:an?\s+)?(?:" + "|".join(v[0]) + r"|"
                            + k + r")\b", re.I)) for k, v in OWNERS.items()]
_SHIPW_FA = fa_norm("(?:نفتکش|نفت کش|تانکر|کشتی|شناور|لنج|کانتینربر|سوپرتانکر)(?: حامل گاز| حامل نفت| تجاری| باری)?")
_OWNER_FA = [(k, re.compile(_SHIPW_FA + r"\s*(?:" + "|".join(fa_norm(x) for x in v[1] if x.endswith("ی")) + r")(?![ء-ۿ])|"
                            + _SHIPW_FA + r"\s*(?:\S+\s*){0,2}?" + fa_norm("(?:متعلق به|مالکیت|از آن)") + r"\s*(?:"
                            + "|".join(fa_norm(x) for x in v[1]) + r")(?![ء-ۿ])|" + fa_norm("(?:کشتی|نفتکش|تانکر|شناور) حامل (?:گاز|نفت|ال ان جی)")
                            + r"\s*(?:\S+\s*)?(?:" + "|".join(fa_norm(x) for x in v[1]) + r")(?![ء-ۿ])")) for k, v in OWNERS.items()]
for _k, _v in OWNERS.items():                  # "a ship carrying Qatari gas"
    _OWNER_EN.append((_k, re.compile(r"\b(?:vessel|ship|tanker|carrier)s?\s+carrying\s+(?:" + "|".join(_v[0]) + r")\s+(?:gas|lng|oil|crude)\b", re.I)))


_NOUN_EN = {"iran": "iran", "qatar": "qatar", "saudi": "saudi arabia|saudis?", "uae": "uae|emirates", "kuwait": "kuwait",
            "india": "india", "pakistan": "pakistan", "china": "china", "greece": "greece", "us": "us|u\\.s\\.|united states",
            "uk": "uk|britain", "israel": "israel", "oman": "oman", "iraq": "iraq", "japan": "japan",
            "korea": "south korea", "turkey": "turkey", "russia": "russia"}
# a country telling of its own ship: "Qatar confirms the attack on its LNG carrier",
# «قطر حمله به کشتی خود را تأیید کرد», «شرکت قطر گاز: یکی از نفتکش‌های گاز ما…», "ship of the Qatar Gas company"
_OWN_SAY_EN = [(k, re.compile(r"\b(?:" + v + r"|" + "|".join(OWNERS[k][0]) + r")s?\b(?:\s+[\w-]+){0,6}?\s+(?:its|their|one of its)\s+"
                              + _SHIPW_EN + r"\b|\b" + _SHIPW_EN + r"\s+(?:of|operated by|owned by)\s+(?:the\s+|a\s+)?(?:"
                              + v + r"|" + "|".join(OWNERS[k][0]) + r")\b", re.I)) for k, v in _NOUN_EN.items()]
_OWN_SAY_FA = [(k, re.compile(r"(?<![ء-ۿ])(?:" + "|".join(fa_norm(x) for x in v[1]) + r")(?![ء-ۿ])[^.؛]{0,30}?"
                              + _SHIPW_FA + r"(?: ها| های)?(?: گاز| نفت)?\s*(?:خود|ما|اش|شان)(?![ء-ۿ])|"
                              + fa_norm("(?:نفتکش|نفت کش|تانکر|کشتی|شناور)") + r"(?: های)?\s*" + fa_norm("شرکت")
                              + r"\s*(?:\S+\s*){0,5}?(?:" + "|".join(fa_norm(x) for x in v[1]) + r")(?![ء-ۿ])"))
               for k, v in OWNERS.items()]


def owner(m):
    """The country whose ship it is (owner or operator), if the report's headline says so; else None."""
    en, fa = _head(m)
    for k, rx in _OWNER_EN:
        if rx.search(en):
            return k
    for k, rx in _OWNER_FA:
        if fa and rx.search(fa):
            return k
    for k, rx in _OWN_SAY_EN:
        if rx.search(en):
            return k
    for k, rx in _OWN_SAY_FA:
        if fa and rx.search(fa):
            return k
    return None


# the ship's name: "MT Front Altair", "M/V Galaxy Leader", tanker "Stena Impero", نفتکش «استنا ایمپرو»
_NAME_EN = re.compile(r"\b(?:MT|MV|M/T|M/V|M\.T\.|M\.V\.)\s+([A-Z][\w-]+(?:\s+[A-Z0-9][\w-]*){0,3})"
                      r"|\b(?:tanker|vessel|ship|carrier|freighter)\s+(?:named\s+|called\s+)?[\"“‘']([A-Z][^\"”’']{2,30})[\"”’']")
_NAME_FA = re.compile(fa_norm("(?:نفتکش|نفت کش|تانکر|کشتی|شناور|سوپرتانکر|کانتینربر)") + r"\s*(?:[\w ]{0,12}?\s)?"
                      + fa_norm("(?:به نام|موسوم به)?") + r"\s*«([^»]{3,30})»")
_NOT_NAME_FA = re.compile(fa_norm("متخلف|ناامن|غیر مجاز|غیرمجاز|ممنوعه|دشمن|آمریکایی|صهیونیستی"))


def name(m):
    """("en"|"fa", the ship's name in lower case) if the report names the ship, else None. Names are compared only
    within one language: a Persian spelling of a foreign name may differ from one outlet to another."""
    en, fa = _texts(m)
    x = _NAME_EN.search(en)
    if x:
        return ("en", re.sub(r"\s+", " ", (x.group(1) or x.group(2)).strip().lower()))
    if fa:
        x = _NAME_FA.search(fa)
        if x and not _NOT_NAME_FA.search(x.group(1)):
            return ("fa", re.sub(r"\s+", " ", x.group(1).strip()))
    return None


def ship_id(m):
    """What sets a report's ship apart from others: {"kd": kinds, "fl": flag, "nm": name, "ow": whose ship}."""
    return {"kd": kinds(m), "fl": flag(m), "nm": name(m), "ow": owner(m)}


def ships_fit(a, b):
    """Two reports (their ship_id()) can be about one ship: kinds that fit, no two flags, owners or names."""
    if not kinds_fit(a.get("kd"), b.get("kd")):
        return False
    if a.get("fl") and b.get("fl") and a["fl"] != b["fl"]:
        return False
    if a.get("ow") and b.get("ow") and a["ow"] != b["ow"]:
        return False
    na, nb = a.get("nm"), b.get("nm")
    if na and nb and na[0] == nb[0] and na[1] != nb[1]:
        return False
    return True


def same_ship(a, b):
    """The same ship for sure: the same name, in one language."""
    na, nb = a.get("nm"), b.get("nm")
    return bool(na and nb and na == nb)


_COUNT_W = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
_COUNT_EN = re.compile(r"\b(\d{1,3}|two|three|four|five|six|seven|eight|nine|ten)\s+(?:[\w\"'“”‘’-]+\s+){0,2}?"
                       r"(?:vessels|ships|tankers|super ?tankers|oil tankers|carriers|freighters|dhows|tug(?:boat)?s)\b", re.I)
_COUNT_FA = re.compile(r"(?<![ء-ۿ\d])(\d{1,3}|" + "|".join(k for k in _COUNT_W if not k.isascii()) + r")\s*"
                       + fa_norm("(?:فروند\\s*)?(?:نفتکش|نفت کش|تانکر|کشتی|شناور|سوپرتانکر|ابرنفتکش|لنج|یدک کش)"))


def counts(m):
    """How many ships the headline says (\"two tankers\", «۴ نفتکش»): numbers that count ships, not a statement's
    number («اطلاعیه شماره ۲۱»), a drone's or a day's. "One" ship is no count."""
    en, fa = _head(m)
    out = set()
    for x in _COUNT_EN.finditer(en):
        w = x.group(1).lower()
        n = int(w) if w.isdigit() else _COUNT_W[w]
        if 2 <= n <= 60:
            out.add(n)
    for x in _COUNT_FA.finditer(fa or ""):
        w = x.group(1)
        n = int(w) if w.isdigit() else _COUNT_W.get(w, 0)
        if 2 <= n <= 60:
            out.add(n)
    return sorted(out)


_ANOTHER_EN = re.compile(r"\b(another|second|third|separate)\b|\b(new|fresh|further)\s+(attack|incident|strike|explosion)", re.I)
_ANOTHER_FA = re.compile(fa_norm("کشتی دیگر|نفتکش دیگر|نفت کش دیگر|شناور دیگر|لنج دیگر|دومین|سومین|حادثه جدید|حمله جدید"
                                 "|حادثه دیگر|حمله دیگر|حادثه تازه|حمله تازه|یک کشتی دیگر"))
_HAPPENED_EN = re.compile(r"\b(fire|ablaze|burning|blaze|attack\w*|struck|hit|hits|explosions?|blasts?|incident"
                          r"|damaged|disabled|sank|sinks|sinking|sunk|targeted|exploded)\b", re.I)
_HAPPENED_FA = re.compile(fa_norm("آتش|حمله|اصابت|انفجار|حادثه|آسیب|غرق|هدف قرار"))
_MINE_EN = re.compile(r"(?<!limpet )(?<!limpet-)\bmines?\b|\bmined\b", re.I)   # a limpet mine is stuck on by hand
_MINE_FA = re.compile(r"(?<![ء-ۿ])" + fa_norm("مین") + r"(?:\s*" + fa_norm("ها") + r")?(?![ء-ۿ])(?!\s*(?:مغناطیسی|چسبان|چسبنده|لیمپت))")
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


_GULF_EN = re.compile(r"\b(?:in|into|the|gulf)\s+(?:waters\s+of\s+the\s+)?gulf\b(?!\s+of\b)|\bgulf waters\b", re.I)
_GULF_STATE_EN = re.compile(r"\b(?:qatar\w*|saudi\w*|kuwait\w*|bahrain\w*|emirat\w*|uae|iraq\w*)\b", re.I)


def area(m, head=False):
    """The sea area a report names: "hormuz", "gulf", "arabian", "redsea", or None. "The Gulf" alone is the Persian
    Gulf only beside a Gulf state's name ("Qatari gas tanker struck in Gulf"); otherwise it may be the strait."""
    en, fa = _head(m) if head else _texts(m)
    for k, rx in _AREA_EN:
        if rx.search(en):
            return k
    for k, rx in _AREA_FA:
        if fa and rx.search(fa):
            return k
    if _GULF_EN.search(en) and _GULF_STATE_EN.search(en):
        return "gulf"
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
            ("explosive", r"\b(explosives?|limpets?)\b"), ("mine", r"(?<!limpet )\bmines?\b"), ("drone", r"\bdrones?\b"),
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


# ------------------------------------------------------------------ when it happened, as the report says
TEHRAN = 12600
H = 3600
_WEEKDAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_WEEKDAYS_FA = ["دوشنبه", "سه شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]   # Monday first
_MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                           "september", "october", "november", "december"])}
_REL_EN = [  # phrase -> (from, to) in hours relative to the report, or "day:k" for a day k days before the report's
    (re.compile(r"\b(past|last) (24|twenty-four) hours\b|\bin the past day\b", re.I), (-24, 0)),
    (re.compile(r"\b(minutes ago|an hour ago|hours? ago|moments ago|just now)\b", re.I), (-4, 0)),
    (re.compile(r"\b(earlier today|this morning|this afternoon|this evening|today)\b", re.I), "day:0"),
    (re.compile(r"\b(late yesterday|last night|overnight|yesterday|late on \w+day)\b", re.I), "day:1"),
]
_REL_FA = [
    (re.compile(fa_norm("شبانه روز گذشته|24 ساعت گذشته|۲۴ ساعت گذشته|بیست و چهار ساعت گذشته")), (-24, 0)),
    (re.compile(fa_norm("دقایقی پیش|ساعتی پیش|ساعاتی پیش|لحظاتی پیش|دقایق پیش|ساعت گذشته")), (-4, 0)),
    (re.compile(fa_norm("بامداد امروز|صبح امروز|ظهر امروز|عصر امروز|امروز")), "day:0"),
    (re.compile(fa_norm("دیشب|شب گذشته|دیروز|روز گذشته|بامداد دیروز")), "day:1"),
]
_CLOCK_UTC = re.compile(r"\b(\d{1,2})[:.]?(\d{2})\s*(?:hrs?\s*)?(utc|gmt|z\b)", re.I)
_CLOCK_FA_UTC = re.compile(r"(\d{1,2})[:.](\d{2})\s*" + fa_norm("به وقت (?:جهانی|گرینویچ)"))
_DATE_EN = re.compile(r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\b|\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})\b", re.I)


def _day0(t):
    """Midnight in Tehran of the day of t."""
    return (t + TEHRAN) // 86400 * 86400 - TEHRAN


# finer times, for reports about ships (fine=True): parts of the day in Tehran's hours, local clock times, "three
# hours ago". (day before the report's day, from hour, to hour); hours past 24 run into the next day.
_PART_EN = [
    (r"\b(?:early|late)? ?yesterday (?:morning|before dawn)\b|\bearly (?:on )?yesterday\b", (1, 0, 13)),
    (r"\byesterday (?:afternoon|evening)\b|\blate yesterday\b|\blate on yesterday\b", (1, 12, 26)),
    (r"\b(?:last night|overnight|during the night|late last night)\b", (1, 17, 32)),
    (r"\b(?:before dawn|pre-?dawn|in the early hours|early hours of|early this morning|early today|early morning)\b", (0, -3, 9)),
    (r"\bthis morning\b|\bon \w+ morning\b", (0, 3, 13)),
    (r"\b(?:at )?(?:midday|noon) today\b|\bthis midday\b", (0, 10, 16)),
    (r"\bthis afternoon\b", (0, 11, 20)),
    (r"\b(?:this evening|tonight|late today)\b", (0, 16, 30)),
    (r"\b(?:day before yesterday|two days ago)\b", (2, -6, 30)),
]
_PART_FA = [
    ("(?:بامداد|صبح|سحرگاه|صبحگاه) دیروز|دیروز (?:صبح|بامداد)", (1, 0, 13)),
    ("(?:ظهر|عصر|بعد از ظهر|بعدازظهر|غروب|شامگاه) دیروز|دیروز (?:ظهر|عصر|بعد از ظهر|بعدازظهر|غروب)", (1, 11, 26)),
    ("دیشب|شب گذشته|نیمه شب گذشته|نیمه شب دیشب|بامداد امروز پس از نیمه شب|در طول شب|شبانه", (1, 17, 32)),
    ("(?:بامداد|سحرگاه|سپیده دم|ساعات اولیه) امروز|امروز (?:بامداد|سحرگاه)|ساعات اولیه بامداد|بامداد", (0, -3, 9)),
    ("صبح امروز|امروز صبح|صبحگاه امروز", (0, 3, 13)),
    ("ظهر امروز|امروز ظهر|نیمروز امروز", (0, 10, 16)),
    ("(?:عصر|بعد از ظهر|بعدازظهر) امروز|امروز (?:عصر|بعد از ظهر|بعدازظهر)", (0, 11, 20)),
    ("امشب|(?:غروب|شامگاه|شب) امروز|امروز (?:غروب|شامگاه)", (0, 16, 30)),
    ("پریروز|دو روز پیش|دو روز قبل|دو روز گذشته", (2, -6, 30)),
]
_PART_EN = [(re.compile(r, re.I), sp) for r, sp in _PART_EN]
_PART_FA = [(re.compile(fa_norm(r)), sp) for r, sp in _PART_FA]
_AGO_EN = re.compile(r"\b(\d{1,2}|an?|one|two|three|four|five|six|several|a few|few)\s+(hours?|minutes?)\s+(?:ago|earlier)\b", re.I)
_AGO_FA = re.compile(r"(\d{1,2}|" + fa_norm("یک|دو|سه|چهار|پنج|شش|چند|ساعاتی|دقایقی|ساعتی|لحظاتی") + r")\s*("
                     + fa_norm("ساعت|دقیقه") + r")?\s*(?:" + fa_norm("پیش|قبل") + r")")
_DAYS_AGO_EN = re.compile(r"\b(\d{1,2}|two|three|four|five|six)\s+days?\s+(?:ago|earlier)\b", re.I)
_DAYS_AGO_FA = re.compile(r"(\d{1,2}|" + fa_norm("دو|سه|چهار|پنج|شش") + r")\s*" + fa_norm("روز") + r"\s*"
                          + fa_norm("(?:پیش|قبل|گذشته)"))
_AGO_W = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "یک": 1, "دو": 2, "سه": 3,
          "چهار": 4, "پنج": 5, "شش": 6}
_CLOCK_FA_LOCAL = re.compile(fa_norm("ساعت") + r"\s*(\d{1,2})(?:[:.](\d{2}))?\s*(?:" + fa_norm("و") + r"\s*\d{1,2}\s*"
                             + fa_norm("دقیقه") + r"\s*)?(" + fa_norm("بامداد|صبح|ظهر|بعد از ظهر|بعدازظهر|عصر|غروب|شب|نیمه شب")
                             + r")?(?!\s*" + fa_norm("گذشته|اخیر|پیش|قبل") + r")")
_CLOCK_EN_LOCAL = re.compile(r"\b(\d{1,2})(?:[:.]?(\d{2}))?\s*(?:hrs?\s*)?(a\.?m\.?|p\.?m\.?)?\s*(?:\(|,)?\s*local time\b"
                             r"|\bat (\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", re.I)
_YDAY = re.compile(r"\byesterday\b|\blast night\b", re.I)
_YDAY_FA = re.compile(fa_norm("دیروز|دیشب|شب گذشته"))
_WD_PART_EN = re.compile(r"\b(early|late)?\s*(?:on\s+)?(" + "|".join(_WEEKDAYS_EN) + r")(?:'s)?\s*(morning|afternoon|evening|night)?\b", re.I)
_WD_PART_FA = re.compile(r"(?<![ء-ۿ])(" + fa_norm("بامداد|سحرگاه|صبح|ظهر|عصر|بعدازظهر|غروب|شامگاه|شب") + r")?\s*(?:"
                         + fa_norm("روز") + r"\s*)?(" + "|".join(fa_norm(w) for w in _WEEKDAYS_FA) + r")(?![ء-ۿ])")
_PART_HOURS = {"early": (-3, 10), "morning": (3, 13), "afternoon": (11, 20), "evening": (16, 26), "night": (17, 30),
               "late": (14, 30), "بامداد": (-3, 9), "سحرگاه": (-3, 8), "صبح": (3, 13), "ظهر": (10, 16), "عصر": (11, 20),
               "بعدازظهر": (11, 20), "غروب": (15, 22), "شامگاه": (15, 24), "شب": (-6, 6)}   # «شب جمعه»: the night before Friday


def _span(lo, hi, t):
    hi = min(t, hi)
    return (min(lo, hi), hi)


def _when_fine(t, en, fa, d0):
    head_en, head_fa = en, fa
    x = _AGO_EN.search(en)
    if x:
        w = x.group(1).lower()
        n = int(w) if w.isdigit() else _AGO_W.get(w, 0)
        if x.group(2).lower().startswith("minute"):
            return (t - 2 * H, t)
        return (t - (n + 1) * H, t - max(0, n - 1) * H) if n else (t - 8 * H, t)
    x = fa and _AGO_FA.search(fa)
    if x:
        w, unit = x.group(1), x.group(2) or ""
        if unit == fa_norm("دقیقه") or w in (fa_norm("دقایقی"), fa_norm("لحظاتی")):
            return (t - 2 * H, t)
        n = int(w) if w.isdigit() else _AGO_W.get(w, 0)
        if w == fa_norm("ساعتی"):
            return (t - 2 * H, t)
        if unit or w == fa_norm("ساعاتی"):
            return (t - (n + 1) * H, t - max(0, n - 1) * H) if n else (t - 8 * H, t)
    x = _DAYS_AGO_EN.search(en) or (fa and _DAYS_AGO_FA.search(fa))
    if x:
        w = x.group(1).lower()
        n = int(w) if w.isdigit() else _AGO_W.get(w, 0)
        if 1 <= n <= 14:
            lo = d0 - n * 86400
            return _span(lo - 6 * H, lo + 30 * H, t)
    # a clock time in local time (Tehran's, or the Gulf's: within an hour of it)
    for rx, txt, lang in ((_CLOCK_FA_LOCAL, fa, "fa"), (_CLOCK_EN_LOCAL, en, "en")):
        x = txt and rx.search(txt)
        if not x:
            continue
        g = x.groups()
        if lang == "en" and g[0] is None:
            g = g[3:]
        hh, mm, part = int(g[0]), int(g[1] or 0), (g[2] or "").lower().replace(".", "")
        if hh > 23 or mm > 59:
            continue
        if part in ("pm", fa_norm("بعد از ظهر"), fa_norm("بعدازظهر"), fa_norm("عصر"), fa_norm("غروب")) and hh < 12:
            hh += 12
        elif part == fa_norm("شب") and 5 <= hh < 12:
            hh += 12
        elif part == fa_norm("ظهر") and hh < 5:
            hh += 12
        elif part in ("am", fa_norm("بامداد"), fa_norm("نیمه شب")) and hh == 12:
            hh = 0
        back = 1 if (_YDAY.search(en) or (fa and _YDAY_FA.search(fa))) else 0
        base = d0 - back * 86400 + hh * H + mm * 60
        if base > t + 600:
            base -= 86400
        if 0 <= t - base <= 3 * 86400:
            return (base - int(1.5 * H), min(t, base + int(1.5 * H)))
    # a weekday with a part of the day ("early Thursday", «بامداد پنجشنبه», «شب جمعه»)
    x = _WD_PART_EN.search(en)
    if x and (x.group(1) or x.group(3)):
        i = _WEEKDAYS_EN.index(x.group(2).lower())
        part = (x.group(3) or x.group(1)).lower()
        return _weekday_part(t, i, _PART_HOURS[part])
    if fa:
        for x in _WD_PART_FA.finditer(fa):
            if not x.group(1):
                continue
            w = x.group(2)
            if w == fa_norm("شنبه") and re.search(fa_norm("(?:یک|دو|سه|چهار|پنج)\\s*") + "$", fa[:x.start(2)]):
                continue
            i = [fa_norm(d) for d in _WEEKDAYS_FA].index(w)
            return _weekday_part(t, i, _PART_HOURS[x.group(1).replace(" ", "")])
    for rx, (k, h0, h1), txt in [(r, sp, en) for r, sp in _PART_EN] + [(r, sp, fa) for r, sp in _PART_FA]:
        if txt and rx.search(txt):
            lo = d0 - k * 86400
            if k == 0 and h0 * H > t - d0:
                continue                    # "this evening" in a report from the morning: not a time of the past
            return _span(lo + h0 * H, lo + h1 * H, t)
    return None


def _weekday_part(t, i, hours):
    import time as _t
    wd = _t.gmtime(t + TEHRAN).tm_wday
    lo = _day0(t) - ((wd - i) % 7) * 86400
    if lo + hours[0] * H > t:
        lo -= 7 * 86400
    return _span(lo + hours[0] * H, lo + hours[1] * H, t)


def when(m, fine=False):
    """(earliest, latest) moment of what the report tells of, from its headline and text: a clock time in UTC, a date,
    a weekday, "an hour ago", "last night", "in the past 24 hours"… None if it says nothing about time.
    fine: also parts of the day ("early Thursday", «بامداد امروز», «عصر دیروز»), local clock times («ساعت ۴ بامداد»)
    and "three hours ago", for reports about ships."""
    t = m["t"]
    en, fa = _texts(m)
    d0 = _day0(t)
    # a clock time in UTC, on the date given or else the last such moment before the report
    x = _CLOCK_UTC.search(en) or (fa and _CLOCK_FA_UTC.search(fa))
    if x:
        hh, mm = int(x.group(1)), int(x.group(2))
        if hh < 24 and mm < 60:
            dt = _DATE_EN.search(en)
            base = None
            if dt:
                day = int(dt.group(1) or dt.group(4))
                mon = _MONTHS[(dt.group(2) or dt.group(3)).lower()]
                import calendar
                import time as _t
                y = _t.gmtime(t).tm_year
                base = calendar.timegm((y, mon, day, hh, mm, 0))
                if base > t + 86400:
                    base = calendar.timegm((y - 1, mon, day, hh, mm, 0))
            if base is None:
                base = (t // 86400) * 86400 + hh * H + mm * 60
                if base > t + 600:
                    base -= 86400
            if 0 <= t - base <= 4 * 86400:
                return (base - H // 2, base + H // 2)
    if fine:
        w = _when_fine(t, en, fa, d0)
        if w:
            return w
    for rx, span, txt in [(r, sp, en) for r, sp in _REL_EN] + [(r, sp, fa) for r, sp in _REL_FA]:
        if txt and rx.search(txt):
            if isinstance(span, tuple):
                return (t + span[0] * H, t + span[1] * H)
            k = int(span.split(":")[1])
            lo = d0 - k * 86400
            return (lo - (6 * H if k else 0), min(t, lo + 86400 + (6 * H if k else 0)))
    # a weekday named: that day (the most recent one), give or take the night around it
    low = en.lower()
    for i, w in enumerate(_WEEKDAYS_EN):
        if re.search(r"\b(on )?" + w + r"\b", low):
            return _weekday(t, i)
    if fa:
        for i, w in enumerate(_WEEKDAYS_FA):
            if re.search(r"(?<![ء-ۿ])" + re.escape(fa_norm(w)) + r"(?![ء-ۿ])", fa):
                if w == "شنبه" and re.search(fa_norm("(?:یک|دو|سه|چهار|پنج)\\s*شنبه"), fa):
                    continue
                return _weekday(t, i)
    return None


def _weekday(t, i):
    import time as _t
    wd = _t.gmtime(t + TEHRAN).tm_wday                    # 0 = Monday, in Tehran
    back = (wd - i) % 7
    lo = _day0(t) - back * 86400
    return (lo - 6 * H, min(t, lo + 86400 + 6 * H))


def overlap(a, b, slack=3 * H):
    return a[0] - slack <= b[1] and b[0] - slack <= a[1]


# ------------------------------------------------------------------ an Iranian body's statement about tankers
_IR_WORDS_FA = re.compile(fa_norm("متخلف|مسیر غیر مجاز|مسیر غیرمجاز|محدوده ممنوعه|منطقه ممنوعه|محدوده ناامن|"
                                  "بی توجهی به هشدار|مسیر غیر قانونی"))
_IR_WORDS_EN = re.compile(r"\b(offending|violating|unauthori[sz]ed route|illegal route|prohibited (?:area|zone|route)"
                          r"|unsafe area|ignor\w+ (?:radio )?warnings?)\b", re.I)
_IR_OUTLETS = {"irna", "fars", "isna", "mehr", "iribnews", "nournews", "defapress", "tasnim", "presstv", "khabaronline",
               "entekhab"}
_RELAYS = re.compile(r"\bukmto\b|\bu\.?k\.? maritime|\bbritish\b|\bunited kingdom\b|\bvanguard\b|\bambrey\b", re.I)
_RELAYS_FA = re.compile(fa_norm("بریتانیا|انگلیس|ukmto|عملیات تجارت دریایی|سنتکام"))


def statement(m):
    """True if the report tells an Iranian body's statement about ships (the IRGC or the army saying tankers hit
    mines, were stopped…), not an incident reported independently: an Iranian claim or a headline about mines,
    the words those statements use ("offending" tankers, the "unauthorised route"), or an Iranian outlet's report
    about a ship that cites no one else (UKMTO, Britain). A report placing the incident by distance is not."""
    if mark(m):
        return False
    en, fa = _head(m)
    ten, tfa = _texts(m)
    if not (SHIP_EN.search(en) or (fa and SHIP_FA.search(fa))):
        return False
    if iran_claim(m) or _IR_WORDS_EN.search(ten) or (fa and _IR_WORDS_FA.search(tfa)):
        return True
    sid = (m.get("s") or "").split(":")[0]
    if sid in _IR_OUTLETS and not (_RELAYS.search(ten) or (tfa and _RELAYS_FA.search(tfa))) \
            and not _FOREIGN_SAYS_EN.search(en) and not (fa and _FOREIGN_SAYS_FA.search(fa)):
        return True
    return False


# another country or company telling of its ship ("Qatar confirmed the attack on its ship", «شرکت قطر گاز: …»): an
# Iranian outlet retelling it is not an Iranian statement
_FOREIGN = ("قطر|قطر گاز|قطرگاز|عربستان|سعودی|امارات|عمان|کویت|بحرین|عراق|هند|پاکستان|آمریکا|سنتکام|پنتاگون|انگلیس"
            "|بریتانیا|یونان|ژاپن|چین|کره|ترکیه|مصر|اردن|آمبری|وانگارد|لویدز|مرسک")
_FOREIGN_SAYS_FA = re.compile(r"^(?:\S+\s*){0,3}?(?:" + fa_norm(_FOREIGN) + r")[^:؛.]{0,25}:|(?:" + fa_norm(_FOREIGN)
                              + r")[^:؛.]{0,40}?" + fa_norm("(?:تایید کرد|تأیید کرد|اعلام کرد|گفت|می گوید|مدعی شد|خبر داد|تایید شد)"))
_FOREIGN_SAYS_EN = re.compile(r"\b(?:qatar\w*|saudi\w*|emirati|uae|oman\w*|kuwait\w*|bahrain\w*|iraq\w*|india\w*|pakistan\w*"
                              r"|us|u\.s\.|american|pentagon|centcom|british|uk|greek|japan\w*|chin\w*|ambrey|vanguard|maersk)"
                              r"\b[^.:;]{0,40}\b(?:confirm\w*|says?|said|announc\w+|reports?)\b", re.I)


_WHO_IRGC = re.compile(r"\b(irgc|revolutionary guards?|guards navy)\b", re.I)
_WHO_IRGC_FA = re.compile(fa_norm("سپاه"))
_WHO_ARMY = re.compile(r"\b(army|artesh)\b|\bnavy of the army\b|\b(?:iranian|iran's|iran’s|islamic republic of iran) navy\b", re.I)
_WHO_ARMY_FA = re.compile(fa_norm("ارتش"))
_SUPER = re.compile(r"\b(super ?tankers?|vlcc|very large crude)\b", re.I)
_SUPER_FA = re.compile(fa_norm("سوپر نفتکش|سوپرنفتکش|ابرنفتکش|ابر نفتکش"))
_STOP = re.compile(r"\b(stopped|halted|intercepted|seized|stoppage)\b", re.I)
_STOP_FA = re.compile(fa_norm("متوقف|توقف|توقیف|رهگیری"))
_ORD = {"second": 2, "third": 3, "fourth": 4, "fifth": 5}
_ORD_FA = {"دومین": 2, "سومین": 3, "چهارمین": 4, "پنجمین": 5}


def signature(m):
    """Who made the statement and what sets it apart: {"who", "nums", "super", "stop", "ord", "kd", "ano", "area"},
    or None if the report is not an Iranian statement about ships. nums: how many ships it counts (not a statement's
    number, «اطلاعیه شماره ۲۱»); kd: the kinds of ship it names; ano: it tells of another ship ("another offending
    tanker", «یک نفتکش متخلف دیگر»); area: the sea area it names."""
    if not statement(m):
        return None
    en, fa = _head(m)
    ten, tfa = _texts(m)
    who = ("irgc" if _WHO_IRGC.search(ten) or (tfa and _WHO_IRGC_FA.search(tfa)) else
           "army" if _WHO_ARMY.search(ten) or (tfa and _WHO_ARMY_FA.search(tfa)) else "iran")
    ord_ = next((v for k, v in _ORD.items() if re.search(r"\b" + k + r"\b", en, re.I)), None) or \
        next((v for k, v in _ORD_FA.items() if fa and fa_norm(k) in fa), None)
    kd = kinds(m)
    return {"who": who, "nums": counts(m), "ord": ord_, "kd": sorted(kd),
            "super": "super" in kd or bool(_SUPER.search(en) or (fa and _SUPER_FA.search(fa))),
            "stop": bool(_STOP.search(en) or (fa and _STOP_FA.search(fa))),
            "ano": another(m) or bool(_MORE_EN.search(en) or (fa and _MORE_FA.search(fa))), "area": area(m, head=True)}


_MORE_EN = re.compile(r"\b(?:more|other|new|additional|further)\s+(?:\w+\s+)?(?:tankers?|ships?|vessels?)\b", re.I)
_MORE_FA = re.compile(fa_norm("(?:نفتکش|نفت کش|تانکر|کشتی|شناور)(?: های| ها)?(?: \\S+)? (?:دیگر|جدید|تازه)|افزایش (?:تعداد|شمار)"))


def _who_fits(a, b):
    return a["who"] == b["who"] or "iran" in (a["who"], b["who"])


def same_statement(a, b):
    """Reports of one statement: the same body (or one of them only says "Iran"), the same sea area if both name one,
    kinds of ship that fit, both or neither telling of "another" ship, and something particular in common: the same
    count of ships, a super tanker, ships stopped."""
    if not a or not b or not _who_fits(a, b):
        return False
    if a.get("area") and b.get("area") and a["area"] != b["area"]:
        return False
    if not kinds_fit(frozenset(a.get("kd") or ()), frozenset(b.get("kd") or ())):
        return False
    if bool(a.get("ano")) != bool(b.get("ano")) and not (a["nums"] and b["nums"] and set(a["nums"]) & set(b["nums"])):
        return False
    if a["nums"] and b["nums"] and set(a["nums"]) & set(b["nums"]):
        return True
    if a.get("ord") and a.get("ord") == b.get("ord"):
        return True
    return (a["super"] and b["super"]) or (a["stop"] and b["stop"])


def other_statement(a, b):
    """Two statements that cannot be one: the same body with other counts, a super tanker and ships stopped, other
    sea areas, kinds of ship that don't fit, or two bodies, one telling of "another" ship (the army's "another
    offending tanker" is not the IRGC's "two tankers and a tug" of the morning)."""
    if not a or not b:
        return False
    if a.get("area") and b.get("area") and a["area"] != b["area"]:
        return True
    if not kinds_fit(frozenset(a.get("kd") or ()), frozenset(b.get("kd") or ())):
        return True
    if a.get("ord") and b.get("ord") and a["ord"] != b["ord"]:
        return True
    if not _who_fits(a, b):
        return bool(a.get("ano") or b.get("ano"))
    if a["nums"] and b["nums"] and not set(a["nums"]) & set(b["nums"]):
        return True
    return (a["super"] and b["stop"] and not b["super"]) or (b["super"] and a["stop"] and not a["super"])
