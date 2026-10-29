"""Telegram channel posts that name the outlet they relay ("نیویورک تایمز: …", "به گزارش رویترز …").

Such a post isn't an unconfirmed report when the outlet really said it: the outlet's own report of the same story is
among the news collected in the last day and a half. When it isn't (the outlet isn't one of the sources, or nothing of
it matches), the post stays an unconfirmed report like any other channel post."""
import re

from .cluster import channel, refresh, tokens
from .sources import SOURCES
from .util import fa_norm, speaker_first

WINDOW = 36 * 3600
# other names the channels use for some outlets
ALIASES = {"nyt": ["نیویورک‌تایمز", "نیویورک تایمز"], "wsj": ["وال استریت ژورنال", "والاستریت ژورنال"],
           "axios": ["آکسیوس", "اکسیوس"], "cnn": ["سی ان ان", "CNN"], "bbc": ["بی بی سی", "BBC"],
           "fox": ["فاکس‌نیوز", "فاکس نیوز", "فاکس"], "aljazeera": ["الجزیره", "الجزيرة"],
           "alarabiya": ["العربیه", "العربية"], "reuters": ["رویترز", "رويترز", "Reuters"],
           "ap": ["آسوشیتدپرس", "آسوشیتد پرس", "AP"], "afp": ["خبرگزاری فرانسه", "AFP"],
           "ch12": ["شبکه ۱۲", "شبکه 12", "کانال ۱۲", "کانال 12"], "iribnews": ["صداوسیما", "صدا و سیما"],
           "toi": ["تایمز اسرائیل", "تایمز اسراییل"], "irna": ["ایرنا"], "isna": ["ایسنا"],
           "mehr": ["خبرگزاری مهر"], "fars": ["خبرگزاری فارس", "فارس"], "bloomberg": ["بلومبرگ"],
           "wapo": ["واشنگتن پست"], "guardian": ["گاردین"], "ft": ["فایننشال تایمز"],
           "iranintl": ["ایران اینترنشنال", "اینترنشنال"],
           "ukmto": ["مرکز عملیات تجارت دریایی بریتانیا", "مرکز عملیات تجاری دریایی بریتانیا",
                     "سازمان عملیات تجارت دریایی بریتانیا", "مرکز عملیات تجارت دریایی انگلیس",
                     "عملیات تجارت دریایی بریتانیا", "آژانس دریایی بریتانیا", "UKMTO"],
           "cnbc": ["سی ان بی سی"], "abc": ["ای بی سی نیوز"], "nbc": ["ان بی سی"], "cbs": ["سی بی اس"],
           "politico": ["پولیتیکو"], "economist": ["اکونومیست"], "haaretz": ["هاآرتص", "هاآرتز"],
           "ynet": ["یدیعوت آحارونوت", "وای نت"], "almonitor": ["المانیتور"], "mee": ["میدل ایست آی"],
           "tass": ["تاس"], "anadolu": ["آناتولی"], "centcom": ["سنتکام", "فرماندهی مرکزی آمریکا"],
           "pentagon": ["پنتاگون"], "iaea": ["آژانس بین المللی انرژی اتمی"]}
# outlets the channels relay that aren't among the sources: such a post is labelled as relaying an outlet, though
# there is nothing here to check it against
OTHER = {"x:semafor": ["سمافور", "Semafor"], "x:hadath": ["الحدث", "شبکه الحدث"],
         "x:ch12": ["شبکه ۱۲", "شبکه 12", "کانال ۱۲", "کانال 12"], "x:ch13": ["شبکه ۱۳", "کانال ۱۳", "شبکه 13"],
         "x:kan": ["شبکه کان", "رادیو ارتش اسرائیل"], "x:mayadeen": ["المیادین"], "x:tasnim": ["تسنیم"],
         "x:jamaran": ["جماران"], "x:nyp": ["نیویورک پست"], "x:newsweek": ["نیوزویک"],
         "x:atlantic": ["آتلانتیک"], "x:washex": ["واشنگتن اگزمینر"], "x:times": ["تایمز لندن"]}


def _names():
    out = {}
    for s in SOURCES:
        if s.get("kind") == "tg":
            continue
        names = {s["fa"], s["en"]} | set(ALIASES.get(s["id"], []))
        for n in names:
            n = fa_norm(n)
            if len(n) >= 3:
                out[n] = s["id"]
    for sid, names in OTHER.items():
        for n in names:
            out.setdefault(fa_norm(n), sid)
    return out


NAMES = _names()
_ALT = "|".join(sorted((re.escape(n).replace(r"\ ", r"\s*") for n in NAMES), key=len, reverse=True))
_PRE = r"(?:خبرگزاری\s*|شبکه\s*|روزنامه\s*|نشریه\s*|پایگاه\s*خبری\s*|وبسایت\s*|رادیو\s*)?"
_SAID = (r"(?:گزارش\s*(?:داد|داده|کرد|کرده|می\s*دهد)|نوشت|نوشته|مدعی\s*شد|اعلام\s*(?:کرد|کرده)|می\s*گوید"
         r"|ادعا\s*کرد|خبر\s*(?:داد|داده)|فاش\s*کرد|نشان\s*می\s*دهد|افشا\s*کرد|به\s*دست\s*آورده)")
# "X:" or "X |" at the start, "به گزارش X", "به نقل از X", "X (…) … گزارش داد / نوشت / خبر داد", "به X گفتند",
# "تحقیقات رویترز نشان می‌دهد", "در گفت‌وگو با شبکه X"
_LAND = r"(?:\s*(?:اسرائیل|اسراییل|آمریکا|قطر|عربستان|ترکیه|انگلیس|بریتانیا|روسیه|چین|عربی|فارسی|انگلیسی))?"
CITE = re.compile(r"^\W*" + _PRE + r"(" + _ALT + r")" + _LAND + r"\s*(?:[:：|]|$)"
                  r"|خبرنگار\s*(?:ارشد\s*)?" + _PRE + r"(" + _ALT + r")"
                  r"|(?:به\s*گزارش|به\s*نقل\s*از|بنا\s*بر\s*گزارش|طبق\s*گزارش|بر\s*اساس\s*گزارش|ادعای)\s*" + _PRE
                  + r"(" + _ALT + r")"
                  r"|^\W*" + _PRE + r"(" + _ALT + r")(?:\s*\([^)]{0,30}\))?[^.!؟?:\n]{0,70}?" + _SAID +
                  # "AFP, citing two judicial sources, has reported that ..."
                  r"|^\W*" + _PRE + r"(" + _ALT + r")\s+(?:به\s*نقل\s*از|با\s*استناد\s*به)[^.!?\n]{0,80}?(?:گزارش\s*(?:کرده|کرد|داده|داد)|نوشته|نوشت|اعلام\s*کرده)"
                  r"|(?:تحقیقات|تحقیق|بررسی|افشاگری|گزارش)\s*(?:جدید\s*|اختصاصی\s*|تازه\s*)?" + _PRE + r"(" + _ALT
                  + r")\s*(?:نشان|حاکی|فاش|می\s*گوید|نیز)"
                  r"|(?:گفت\s*و?\s*گو|مصاحبه)\s*(?:ای\s*)?(?:اختصاصی\s*)?با\s*" + _PRE + r"(" + _ALT + r")"
                  r"|به\s*" + _PRE + r"(" + _ALT + r")\s*(?:گفت|گفتند|گفته)",
                  re.I)
_GULF = re.compile(r"خلیج\s*$")


def cited(m):
    """The outlets a channel post says it relays."""
    t = fa_norm(speaker_first(m.get("ti") or ""))   # "… - فارس" names the outlet last
    # the start of the text too: "به گزارش X", "در گفت‌وگو با شبکه X"
    s = fa_norm((m.get("su") or "")[:300])
    out = set()
    for mt in list(CITE.finditer(t)) + list(CITE.finditer(s)):
        for i, g in enumerate(mt.groups(), 1):
            if g and not _GULF.search((t if mt.string is t else s)[: mt.start(i)]):
                sid = NAMES.get(fa_norm(re.sub(r"\s+", " ", g)))
                if sid is None:
                    sid = next((v for k, v in NAMES.items() if re.sub(r"\s", "", k) == re.sub(r"\s", "", g)), None)
                if sid:
                    out.add(sid)
    return out


def _same(a, b):
    """Two English headlines about the same story: enough words shared."""
    inter = a & b
    return len(inter) >= 3 and len(inter) / max(1, min(len(a), len(b))) >= 0.3


def verify(clusters, T):
    """Mark channel-only stories whose cited outlet really reported them (c["verified"]); returns how many changed."""
    by_src = {}
    for c in clusters:
        for m in c["m"]:
            if not channel(m) and T - m["t"] <= WINDOW + 6 * 3600:
                by_src.setdefault(m["s"], []).append((m["t"], tokens(m.get("en_ti") or m.get("ti") or "")))
    changed = 0
    for c in clusters:
        if not c["m"] or not all(channel(m) for m in c["m"]):
            if c.pop("verified", None):
                refresh(c)
                changed += 1
            continue
        ok = False
        for m in c["m"]:
            srcs = cited(m)
            if not srcs:
                continue
            mine = tokens(m.get("en_ti") or "")
            for sid in srcs:
                if any(abs(t - m["t"]) <= WINDOW and _same(mine, toks) for t, toks in by_src.get(sid, [])):
                    ok = True
        if ok != bool(c.get("verified")):
            if ok:
                c["verified"] = True
            else:
                c.pop("verified", None)
            refresh(c)
            changed += 1
    return changed
