"""Forces sent somewhere: how many, of what, to where, as a headline gives it ("10 US military transport planes land
in Israel", "US sends 10 military planes to Israel", "Ten US military aircraft arrive in Israel"). Reports with the
same count, kind and destination tell of the same deployment. Used by the bulletin's clustering and its warning
lights."""
import re

from .util import fa_norm, to_latin_digits

_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "dozen": 12, "dozens": None}
_WORDS_FA = {"دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10, "دوازده": 12,
             "پانزده": 15, "بیست": 20}

# kinds of forces: key -> English forms, Persian forms
KINDS = {
    "air": (r"(?:military |cargo |transport |refuell?ing |tanker )*(?:planes?|aircraft|airplanes?|airlifters?|c-17s?|c-5s?"
            r"|kc-\d+s?)", "(?:هواپیما|هواپیمای|هواپیماهای|هواپیمای ترابری|هواپیمای نظامی)"),
    "fighter": (r"(?:fighter jets?|fighters?|jets|f-\d+s?|warplanes?|stealth fighters?)", r"(?:جنگنده|جنگنده های|اف \d+)"),
    "bomber": (r"(?:bombers?|b-2s?|b-52s?|b-1s?)", r"(?:بمب افکن|بمب افکن های|بی \d+)"),
    "carrier": (r"(?:aircraft carriers?|carriers?|carrier strike groups?)", "(?:ناو هواپیمابر|ناوهای هواپیمابر|ناو)"),
    "warship": (r"(?:destroyers?|warships?|frigates?|cruisers?|submarines?)", "(?:ناوشکن|ناوشکن ها|زیردریایی|کشتی جنگی)"),
    "troops": (r"(?:troops|soldiers|marines|service ?members|personnel|paratroopers)", "(?:سرباز|نیرو|تفنگدار)"),
}
_PLACES = {
    "israel": ("israel", "اسرائیل|اسراییل|سرزمین های اشغالی"), "qatar": ("qatar", "قطر"),
    "uae": ("uae|united arab emirates|emirates", "امارات"), "saudi": ("saudi(?: arabia)?", "عربستان"),
    "bahrain": ("bahrain", "بحرین"), "kuwait": ("kuwait", "کویت"), "jordan": ("jordan", "اردن"),
    "oman": ("oman", "عمان"), "iraq": ("iraq", "عراق"), "cyprus": ("cyprus", "قبرس"), "greece": ("greece|crete", "یونان|کرت"),
    "turkey": ("turkey|t[uü]rkiye|incirlik", "ترکیه"), "diego": ("diego garcia", "دیگو گارسیا"),
    "gulf": ("the gulf|persian gulf|gulf region", "خلیج فارس|منطقه خلیج"), "mideast": ("(?:the )?middle east|the region",
                                                                                  "خاورمیانه|منطقه"),
    "redsea": ("red sea", "دریای سرخ"), "medit": ("mediterranean", "مدیترانه"),
}
_NUM_EN = r"(\d+|" + "|".join(_WORDS) + r")"
_EN = [(k, re.compile(r"\b" + _NUM_EN + r"\s+(?:more\s+|additional\s+|extra\s+)?(?:u\.?s\.?\s+|us\s+|american\s+|israeli\s+|british\s+)?"
                      + v[0] + r"\b", re.I)) for k, v in KINDS.items()]
_FA = [(k, re.compile(r"(\d+|" + "|".join(_WORDS_FA) + r")\s*(?:فروند\s*)?" + fa_norm(v[1]))) for k, v in KINDS.items()]
_TO_EN = [(k, re.compile(r"\b(?:to|in|into|at|over|land(?:s|ed)? in|arriv\w* (?:in|at))\s+(?:the\s+)?(?:" + v[0] + r")\b", re.I))
          for k, v in _PLACES.items()]
_TO_FA = [(k, re.compile(r"(?:به|در|وارد)\s*(?:" + fa_norm(v[1]) + ")")) for k, v in _PLACES.items()]


def _num(x, fa=False):
    x = x.lower()
    if x.isdigit():
        return int(x)
    return (_WORDS_FA if fa else _WORDS).get(x)


def mark(m):
    """(count, kind, destination) of a deployment the headline tells of, or None. Only for a report the classifier
    tagged as a deployment."""
    if "deploy" not in (m.get("flags") or []):
        return None
    en = m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or ""
    fa = to_latin_digits(fa_norm(m.get("ti") or "")) if m.get("lang") == "fa" else ""
    for txt, kinds, places, is_fa in ((en, _EN, _TO_EN, False), (fa, _FA, _TO_FA, True)):
        if not txt:
            continue
        for k, rx in kinds:
            x = rx.search(txt)
            if not x:
                continue
            n = _num(x.group(1), is_fa)
            if not n or n < 2 or n > 400:
                continue
            dest = [p for p, prx in places if prx.search(txt)]
            if len(dest) == 1:
                return (n, k, dest[0])
    return None


# ---- the deployment lamp (index.compute_lights → "deploy")
# The classifier's "deploy" flag is broad (a carrier named at all, «انتقال فناوری» read as «ناو», F-35 spare parts,
# Syria's troops for Yemen denied). The lamp is narrower: a headline telling that forces of the war's sides are being
# sent, are on their way or have arrived, toward the Middle East or Iran. In one clause of the headline itself: what
# (warships, carriers, bombers, fighters, military planes, air defence, troops), a movement told as it happens (not a
# plan, a denial, a rumour, a purchase, a test, forces leaving), where to (the Middle East, the Gulf, a country of the
# region); and no owner other than the war's sides (a Russian plane in Israel, a Chinese carrier, Syria's troops for
# Saudi Arabia, the Gulf states' joint force).
_CARRIERS = r"ford|lincoln|vinson|nimitz|truman|eisenhower|ike|roosevelt|reagan|washington|stennis|bush"
_ASSET_EN = re.compile(
    r"\b(aircraft carriers?|carrier strike groups?|strike groups?|carrier groups?|uss \w+|(?:" + _CARRIERS + r") carrier"
    r"|amphibious (?:assault )?(?:ships?|ready groups?)|destroyers?|warships?|frigates?|cruisers?|submarines?"
    r"|naval (?:forces|assets|group|flotilla)|bombers?|b-?(?:1b?|2|52)s?|fighter jets?|fighters|warplanes?|stealth jets?"
    r"|f-?(?:15|16|18|22|35)\w*|a-?10s?|military (?:planes?|aircraft|jets|cargo planes?|transport planes?)"
    r"|(?:cargo|transport|tanker|refuell?ing) (?:planes?|aircraft|jets)|c-?(?:17|5)s?|kc-?\d+\w*|awacs|e-?3s?"
    r"|thaad|patriot\w*|air defen[cs]e (?:systems?|batter\w+)|troops|soldiers|marines|paratroopers|reinforcements"
    r"|forces|military (?:assets|hardware|equipment|personnel)|airlift|air bridge|(?:military )?build-?up)\b", re.I)
_MOVE_EN = re.compile(
    r"\b(deploy\w*|redeploy\w*|dispatch\w*|send(?:s|ing)?|sent|head(?:s|ed|ing)? (?:to|for|toward|towards|into|back to)"
    r"|sail\w*|steam\w*|arriv\w*|land(?:s|ed|ing)? (?:in|at)|en route|on (?:its|their) way|bound for|rush\w*|surg\w+"
    r"|bolster\w*|reinforc\w*|beef\w* up|pour\w* into|flood\w* into|mov(?:e|es|ed|ing) (?:\w+ ){0,4}(?:to|into|toward)"
    r"|reposition\w*|enter\w* (?:the )?(?:gulf|persian gulf|red sea|arabian sea|mediterranean|strait)|transit\w*"
    r"|build-?up|mass(?:es|ed|ing)|order(?:s|ed)? (?:\w+ ){0,5}to (?:the )?(?:middle east|region|gulf))\b", re.I)
_DEST_EN = re.compile(
    r"\b(middle east|mideast|the region|persian gulf|the gulf|gulf of oman|arabian sea|red sea|eastern mediterranean"
    r"|diego garcia|strait of hormuz|hormuz|centcom|iran|israel|qatar|al udeid|uae|emirates|saudi(?: arabia)?|bahrain"
    r"|kuwait|jordan|iraq|oman|cyprus|akrotiri)\b", re.I)
_ME_EN = r"(?:the )?(?:middle east|mideast|region|gulf|persian gulf|red sea|arabian sea|mediterranean|iraq|syria|qatar)"
_NOT_EN = re.compile(
    r"\b(den(?:y|ies|ied)|reject\w*|refut\w*|not|no|never|without|rumou?rs?|reports? of|consider\w*|weigh\w*|mull\w*"
    r"|could|might|would|should|plans? to|planning|propos\w*|ask\w* for|request\w*|tries|trying|seeks?|struggl\w*"
    r"|spare parts|parts|contract\w*|sale|sells?|sold|buy\w*|purchas\w*|upgrade\w*|moderni[sz]\w*|engines?|retire\w*"
    r"|crash\w*|test\w*|drills?|exercises?|scrambl\w*|intercept\w*|shot down|downed|if|unless|whether"
    r"|(?:leav\w+|left|withdraw\w*|pull\w* (?:out|back)(?: of| from)?|exit\w*|depart\w*) " + _ME_EN +
    r"|return\w* home|heads? home|homeward)\b|n't\b", re.I)
# the war's sides as owners: never a country that is only a destination ("landing in Israel")
_SIDE_EN = re.compile(r"\b(u\.?s\.?(?!-sanction)|us(?!-sanction)|united states|american|pentagon|washington|centcom"
                      r"|trump|hegseth|israeli|idf|british|britain|uk|royal navy|raf|french|france|nato|iranian|irgc)\b"
                      r"|\buss \w+", re.I)
_OTHER_EN = re.compile(r"\b(russia\w*|china|chinese|pla|syria\w*|damascus|turk\w+|ankara|pakistan\w*|egypt\w*"
                       r"|india\w*|north korea\w*|houthi\w*|yemen\w*|sudan\w*|libya\w*|gcc|gulf states|arab states"
                       r"|saudi-led)\b", re.I)
_OWNER_EN = re.compile(r"\b(russian|chinese|syrian|turkish|pakistani|egyptian|indian|north korean|houthi|yemeni"
                       r"|saudi|emirati|qatari|gulf)\s+(?:\w+\s+){0,2}(?:" + _ASSET_EN.pattern[3:-3] + r")\b", re.I)

_FA_L = "؀-ۿ"
_B_FA = "(?<![" + _FA_L + r"\w])"                 # a word start: «ناو» is never the middle of «فناوری»
_E_FA = "(?:ها|های|هایی|ی|ای)?(?![" + _FA_L + r"\w])"   # a word end, with the plural and the ezafe


def _fa_alt(*ws):
    return "(?:" + "|".join(fa_norm(w).replace(" ", r"\s*") for w in ws) + ")"


def _fa_words(*ws):
    return _B_FA + _fa_alt(*ws) + _E_FA


_ASSET_FA_W = (
    "ناو هواپیمابر", "ناوهواپیمابر", "ناوگروه", "ناو", "ناو جنگی", "ناوشکن", "ناوچه", "رزمناو", "زیردریایی",
    "کشتی جنگی", "شناور جنگی", "گروه ضربت", "گروه رزمی", "بمب افکن", "جنگنده", "هواپیمای نظامی", "هواپیمای ترابری",
    "هواپیمای سوخت رسان", "سوخت رسان", "هواپیما", "ترابری", "آواکس", "تاد", "پاتریوت", "سامانه پدافند",
    "سامانه پدافندی", "پدافند هوایی", "نیرو", "نیروهای نظامی", "نیروی کمکی", "نیروهای کمکی", "تفنگدار", "تفنگداران",
    "سرباز", "سربازان", "تجهیزات نظامی", "پل هوایی", "اف ?15", "اف ?16", "اف ?18", "اف ?22", "اف ?35", "بی ?2",
    "بی ?52", "بی ?1", "سی ?17", "کی سی ?135", "یو اس اس")
_ASSET_FA = re.compile(_fa_words(*_ASSET_FA_W) + r"|\b(?:f-?(?:15|16|18|22|35)|b-?(?:1|2|52)|c-?17|kc-?\d+|uss|cvn)\b",
                       re.I)
# on the way: «اعزام»، «راهی … شد»، «حرکت/مسیر … به سمت»; a bare «به سمت» is no movement («آماده شلیک به سمت ایران»)
_MOVE_FA = re.compile(_fa_words(
    "اعزام", "ارسال", "استقرار", "مستقر", "عازم", "رسید", "رسیدند", "رسیدن", "ورود", "وارد", "به مقصد", "راهی",
    "گسیل", "تقویت حضور", "افزایش حضور", "تقویت نیرو", "تقویت نیروها", "انباشت", "پل هوایی", "می فرستد", "فرستاد",
    "فرستاده", "فرستادن", "روانه", "جابجایی", "جابه جایی") + "|" + _fa_words("حرکت", "مسیر", "در راه", "بازگشت")
    + r".{0,40}" + _fa_words("به سمت", "به سوی"))
_DEST_FA = re.compile(_fa_words(
    "خاورمیانه", "منطقه", "خلیج فارس", "دریای عمان", "دریای عرب", "دریای سرخ", "مدیترانه", "دیگو گارسیا", "ایران",
    "اسرائیل", "اسراییل", "سرزمین های اشغالی", "فلسطین اشغالی", "قطر", "العدید", "امارات", "عربستان", "بحرین", "کویت",
    "اردن", "عراق", "عمان", "هرمز", "تنگه هرمز", "سنتکام", "قبرس"))
_ME_FA = _fa_alt("خاورمیانه", "منطقه", "خلیج فارس", "دریای سرخ", "عراق", "سوریه")
_NOT_FA = re.compile(_fa_words(
    "تکذیب", "رد کرد", "رد شد", "صحت ندارد", "نداریم", "ندارد", "نیست", "نخواهد", "نمی", "شایعه", "ادعای", "احتمال",
    "احتمالا", "ممکن", "بررسی", "قصد", "برنامه", "تلاش", "درخواست", "پیشنهاد", "قطعات", "قطعه", "خرید", "فروش",
    "قرارداد", "نوسازی", "ارتقا", "موتور", "آزمایش", "رزمایش", "مانور", "سقوط", "بازنشسته", "رهگیری", "سرنگون", "اگر",
    "چنانچه", "واکنش", "تهدید", "منتفی")
    + "|" + _fa_words("خروج", "ترک", "عقب نشینی", "خارج") + r"\s*(?:\S+\s+){0,2}?(?:از\s*)?" + _ME_FA
    + "|" + _ME_FA + r"\s*(?:را\s*)?(?:ترک|تخلیه)")
_SIDE_FA = re.compile(_fa_words(
    "آمریکا", "امریکا", "آمریکایی", "امریکایی", "ایالات متحده", "پنتاگون", "واشنگتن", "سنتکام", "ترامپ", "هگست",
    "اسرائیلی", "اسراییلی", "ارتش اسرائیل", "انگلیسی", "بریتانیایی", "انگلیس", "بریتانیا", "فرانسوی", "ناتو",
    "ایرانی", "سپاه", "یو اس اس") + r"|\b(?:uss|cvn)\b", re.I)
_OTHER_FA = re.compile(_fa_words(
    "روسیه", "روسی", "چین", "چینی", "سوریه", "سوری", "دمشق", "جولانی", "ترکیه", "آنکارا", "پاکستان", "پاکستانی", "مصر",
    "مصری", "هند", "هندی", "کره شمالی", "حوثی", "یمن", "یمنی", "سودان", "لیبی", "شورای همکاری", "کشورهای عربی",
    "کشورهای حاشیه خلیج فارس", "سعودی", "اماراتی", "قطری"))
# owner named right after the forces: «ناو هواپیمابر فوجیان چین»، «نیروهای سوری»، «جنگنده های سعودی»
_OWNER_FA = re.compile(_fa_words(*_ASSET_FA_W) + r"\s*(?:\S+\s+){0,2}?" + _fa_words(
    "روسیه", "روسی", "چین", "چینی", "سوریه", "سوری", "ترکیه", "پاکستان", "پاکستانی", "مصر", "مصری", "سعودی",
    "عربستان", "اماراتی", "امارات", "قطری", "یمنی", "حوثی", "هندی"))

# clauses: a source before a colon, two items after a slash, a side clause ("… as American military build-up continues")
_CLAUSE = re.compile(r"\s*(?:[:؛;|/]|\s[-–—]\s|\.\s|,?\s(?:as|amid|while|despite)\s)\s*", re.I)


def _lamp_text(txt, fa):
    asset, move, dest, no, side, other, owner = (
        (_ASSET_FA, _MOVE_FA, _DEST_FA, _NOT_FA, _SIDE_FA, _OTHER_FA, _OWNER_FA) if fa else
        (_ASSET_EN, _MOVE_EN, _DEST_EN, _NOT_EN, _SIDE_EN, _OTHER_EN, _OWNER_EN))
    if owner.search(txt) and not side.search(txt):
        return False                   # another country's forces: a Russian plane in Israel, Syria's troops for Saudi
    if other.search(txt) and not side.search(txt):
        return False
    for part in _CLAUSE.split(txt):
        if asset.search(part) and move.search(part) and dest.search(part) and not no.search(part):
            return True
    return False


LAMP_NOT = {"denial", "past", "speculative", "opinion", "digest", "scheduled", "feature", "aside", "tribute",
            "pullback", "pullback_me", "far_off", "side_minor", "kinetic"}


def lamp(m):
    """Whether a report's headline tells of a deployment that lights the lamp (see above). Only for a report the
    classifier tagged as a deployment; the headline in its own language decides."""
    fl = set(m.get("flags") or [])
    if "deploy" not in fl or fl & LAMP_NOT:
        return False
    if m.get("lang") == "fa":
        return _lamp_text(to_latin_digits(fa_norm(m.get("ti") or "")), True)
    return _lamp_text(m.get("en_ti") or m.get("ti") or "", False)
