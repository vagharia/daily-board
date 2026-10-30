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
