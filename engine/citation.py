"""Telegram channel posts that name the outlet they relay ("نیویورک تایمز: …", "به گزارش رویترز …").

Such a post isn't an unconfirmed report when the outlet really said it: the outlet's own report of the same story is
among the news collected in the last day and a half. When it isn't (the outlet isn't one of the sources, or nothing of
it matches), the post stays an unconfirmed report like any other channel post."""
import re

from .cluster import channel, refresh, tokens
from .sources import SOURCES
from .util import fa_norm

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
           "iranintl": ["ایران اینترنشنال", "اینترنشنال"]}


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
    return out


NAMES = _names()
_ALT = "|".join(sorted((re.escape(n).replace(r"\ ", r"\s*") for n in NAMES), key=len, reverse=True))
# "X:" at the start, "به گزارش X", "به نقل از X", "X گزارش داد / نوشت / مدعی شد", "به X گفتند"
CITE = re.compile(r"^\W*(" + _ALT + r")\s*[:：]"
                  r"|(?:به\s*گزارش|به\s*نقل\s*از|بنا\s*بر\s*گزارش|طبق\s*گزارش|بر\s*اساس\s*گزارش)\s*(?:خبرگزاری\s*|شبکه\s*|روزنامه\s*)?(" + _ALT + r")"
                  r"|^\W*(" + _ALT + r")\s+(?:گزارش\s*داد|گزارش\s*می\s*دهد|نوشت|مدعی\s*شد|اعلام\s*کرد|می\s*گوید|ادعا\s*کرد)"
                  r"|به\s*(" + _ALT + r")\s*(?:گفت|گفتند|گفته)",
                  re.I)


def cited(m):
    """The outlets a channel post says it relays."""
    t = fa_norm(m.get("ti") or "")
    out = set()
    for mt in CITE.finditer(t):
        for g in mt.groups():
            if g:
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
