"""Free machine translation through Google's public web endpoints (two independent endpoints,
so one being throttled doesn't stop the run), with caching, size-limited batching and a small
glossary so names and terms come out right in Persian."""
import datetime as dt
import json
import re
import time

from . import config, http
from .scheduled import TEHRAN, gregorian, jalali
from .util import log, now, sha

# ------------------------------------------------------------------ glossary
EN_PRE = [
    (re.compile(r"\bArabian Gulf\b"), "Persian Gulf"),
    (re.compile(r"\bthe Gulf\b(?!\s+of\b)"), "the Persian Gulf"),
    (re.compile(r"\bGulf (states|countries|nations|Arab states|monarchies|allies|neighbou?rs|region|Cooperation Council)\b"),
     r"Persian Gulf \1"),
    (re.compile(r"\bGulf Arab\b"), "Persian Gulf Arab"),
    # "Putin to meet Iran's Pezeshkian, Qatar's emir" came out as "the emir of Qatar of Iran"
    (re.compile(r"\bIran's (?:President )?Pezeshkian\b"), "Iranian President Pezeshkian"),
    (re.compile(r"\bQatar's [Ee]mir\b"), "the Emir of Qatar"),
    # terse headlines Google reads wrongly: the source named last ("Ship attacked near Hormuz: maritime agency" came
    # out as "the maritime agency was attacked"), "Tug Struck" read as active ("the tug struck"), "Hit 72 Nautical
    # Miles Off Saudi Arabia" as "hit Saudi Arabia with 72 miles"
    (re.compile(r"^(?P<what>.{12,}?)\s*(?::|\s[—–-])\s*(?P<who>(?:(?:the\s)?UK\s|British\s)?(?:maritime|navy|naval|security)"
                r"\s(?:agency|monitor|firm|sources?)|UKMTO|Ambrey|Vanguard)\s*$", re.I),
     lambda m: m.group("who")[:1].upper() + m.group("who")[1:] + " says: " + m.group("what")),
    (re.compile(r"\b(Tankers?|Vessels?|Ships?|Tugs?|Tugboats?|Boats?|Ferr(?:y|ies)|Freighters?|Dhows?|Carriers?"
                r"|Cargo [Ss]hips?)\s+(Hit|Struck|Attacked|Seized|Targeted|Damaged)\b"),
     lambda m: m.group(1) + (" were " if m.group(1).endswith(("s", "ies")) else " was ") + m.group(2).lower()),
    (re.compile(r"\b(\d+)\s+[Nn]autical\s+[Mm]iles\s+[Oo]ff\s+(?:the\s+)?(?!coast)"),
     r"\1 nautical miles off the coast of "),
    # "attacks mount" (= grow) came out as a mountain ("حمله نفتکش هرمز به کوه"); only the intransitive verb at the
    # end or before a preposition, so "mount an attack" and Mount Klang (کوه کلنگ) stay as they are
    (MOUNT_VERB := re.compile(r"(?<=[A-Za-z] )(?<![Tt]he )(?<![Aa] )([Mm])ount(s?)\b"
                              r"(?=\s*(?:$|[,.:;!?—–]|\s-\s|\s(?i:as|amid|in|on|at|after|over|across|following|for|with"
                              r"|against|despite|near|off|around|since|while)\b))"),
     lambda m: ("R" if m.group(1) == "M" else "r") + "ise" + m.group(2)),
    # the company, not the alphabet
    (re.compile(r"\bAlphabet(?=\s+(?:Inc|Opens|Sells|Shares|Stock|Bonds?|Plans|Says|Reports|Earnings|Profit|Revenue)"
                r"|'s|\s+and\s+Google)"), "Alphabet Inc."),
]

FA_POST = [
    ("خلیج عربی", "خلیج فارس"), ("خلیج فارس فارس", "خلیج فارس"),
    ("رهبر عالی ایران", "رهبر ایران"), ("رهبر عالی", "رهبر ایران"), ("رهبر معظم ایران ایران", "رهبر ایران"),
    ("هگزث", "هگست"), ("هگسث", "هگست"), ("هگزت", "هگست"), ("ویتکوف", "ویتکاف"),
    ("اراقچی", "عراقچی"), ("ارقچی", "عراقچی"),
    ("حزب الله", "حزب‌الله"), ("حوثی ها", "حوثی‌ها"), ("سپاه پاسداران انقلاب اسلامی", "سپاه پاسداران"),
    ("فرماندهی مرکزی ایالات متحده", "سنتکام"), ("فرماندهی مرکزی آمریکا", "سنتکام"),
    ("آژانس بین المللی انرژی اتمی", "آژانس بین‌المللی انرژی اتمی"),
    ("ایالات متحده آمریکا", "آمریکا"),
]
FA_RX_POST = [
    (re.compile(r"(?<=\S) ها(?=[\s،.؛:!؟]|$)"), "‌ها"),
    (re.compile(r"(?<=\S) های(?=[\s،.؛:!؟]|$)"), "‌های"),
    (re.compile(r"(?<![؀-ۿ])می (?=[؀-ۿ])"), "می‌"),
    (re.compile(r"(?<![؀-ۿ])نمی (?=[؀-ۿ])"), "نمی‌"),
    (re.compile(r"\s+([،.؛:!؟])"), r"\1"),
]
# Google renders a shekel as a mithqal (the old weight) in Persian; put the currency back when the source names it
_SHEKEL = re.compile(r"shekel|\bNIS\b|שקל|ש\"ח|ש״ח", re.I)
# and now and then calls a president "US president" when the English never mentions America
# ("President Pezeshkian to meet Putin" -> "Pezeshkian, the US president")
_US_PRES_FA = re.compile(r"رئیس[\s\u200c]?جمهور (آمریکا|ایالات متحده)")
_US_SRC = re.compile(r"(?<![A-Za-z])(U\.S\.?|US|USA)(?![A-Za-z])|(?i:\b(america\w*|united states|trump|biden|vance"
                     r"|white house|washington)\b)")
_IR_PRES_SRC = re.compile(r"pezeshkian|\biran(ian|'s)? president|president of iran", re.I)
_OTHER_SCRIPT = re.compile(r"[\u0590-\u05FF\u0600-\u06FF\u0400-\u04FF\u4E00-\u9FFF]")
# war vocabulary Google gets wrong in Persian, fixed only when the source shows which sense was meant:
# sea mines come out as mineral mines (معادن), air strikes as labour strikes (اعتصاب), and Iran's Pickaxe Mountain
# site (کوه کلنگ) as a transliteration
_MINES_SRC = re.compile(r"\bmines?\b|\bmine[- ]?(lay\w*|sweep\w*|clear\w*|field\w*|hunt\w*)|\bminelay\w*|\bminesweep\w*",
                        re.I)
_MINING_SRC = re.compile(r"\b(mining|miners?|ores?|quarr\w*|mineral\w*|coal|copper|gold mines?|lithium|iron mines?"
                         r"|bitcoin|crypto\w*)\b", re.I)
_STRIKE_SRC = re.compile(r"\bstrik(e|es|ing)\b|\bstruck\b", re.I)
_LABOUR_SRC = re.compile(r"\b(workers?|unions?|labou?r|wages?|teachers|drivers|truckers|bazaar\w*|merchants|shopkeepers"
                         r"|employees|walkouts?|hunger strike|general strike|on strike|went on strike|strikers)\b", re.I)
_ALPHABET_SRC = re.compile(r"\bAlphabet\b(?!\s+(?:soup|of|letters?)\b)")
_PICKAXE_SRC = re.compile(r"pick-?\s?axe", re.I)
_PICKAXE_FA = re.compile(r"پیک\s*[\u200c]?\s*اکس|پیککس|پیکاکس|پیکس(?=\s|$)")
# Persian names that are fixed regardless of the source (also applied to stored translations)
FA_ALWAYS = [("خلیج عمان", "دریای عمان"), ("امیر قطر ایران", "امیر قطر")]
_LINEBREAKS = re.compile(r"[\r\n  \u0085\v\f]+")


def _pre(text, sl):
    text = _LINEBREAKS.sub(" ", text)
    if sl == "en":
        for rx, rep in EN_PRE:
            text = rx.sub(rep, text)
    return text


_DOCTORS_EN = re.compile(r"\b(the )?[Dd]octors\b")
# a film director comes out as a manager (مدیر); when the source is about cinema, he is a کارگردان
_FILM_SRC = re.compile(r"\b(?:film\w*|movie\w*|cinema\w*|screen\w*|oscar\w*|cannes|berlinale|venice|award-winning"
                       r"|panahi|rasoulof|farhadi|kiarostami|makhmalbaf)\b", re.I)
_DIRECTOR_SRC = re.compile(r"\bdirector\b", re.I)


_HEGSETH_SRC = re.compile("ه[گك]س[تث]|ه[گك]ز[تث]")
_HEGSETH_EN = re.compile(r"\bH[aeoiu]g{1,2}s?[aeiou]?[st]{1,2}t?h?\b")


# ------------------------------------------------------------------ dates between the two calendars
# The machine translation keeps a date's day and swaps the month for the other calendar's nearest one: «۲۲ آبان»
# comes out "November 22" (it is November 13), "November 13" can come out «۱۳ آبان» (it is ۲۲ آبان). A date of the
# source is converted properly (the year nearest today) and put in place of the wrong one in the translation.
SOLAR_FA = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
SOLAR_EN = ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar", "Mehr", "Aban", "Azar", "Dey",
            "Bahman", "Esfand"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]
MONTHS_FA = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_FA_DIG = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_D = r"([0-9۰-۹٠-٩]{1,2})"
_SOLAR_SRC = re.compile(_D + r"\s*(?:ام\s*)?(" + "|".join(SOLAR_FA) + r")(?![؀-ۿ])")
_EN_ABBR = {m[:3].lower(): i for i, m in enumerate(MONTHS_EN)} | {"sept": 8}
_EN_MON = r"(" + "|".join(MONTHS_EN) + r"|(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?)"
_GREG_SRC = re.compile(r"\b" + _EN_MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b|\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?"
                       + _EN_MON + r"\b")
_GREG_SRC_FA = re.compile(_D + r"\s*(" + "|".join(MONTHS_FA) + r")(?![؀-ۿ])")
_ANY_MON_EN = r"(" + "|".join(MONTHS_EN + SOLAR_EN) + r"|(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?)"


def _en_month(name):
    name = name.rstrip(".").lower()
    for i, m in enumerate(MONTHS_EN):
        if m.lower() == name:
            return i + 1
    return _EN_ABBR.get(name[:4] if name.startswith("sept") else name[:3], -1) + 1


def _today():
    return dt.datetime.fromtimestamp(now(), TEHRAN).date()


def _from_solar(jm, jd):
    """The Gregorian date of a day and month of the Iranian calendar, in the year that puts it nearest today."""
    today = _today()
    jy = jalali(today)[0]
    best = None
    for y in (jy - 1, jy, jy + 1):
        try:
            g = gregorian(y, jm, jd)
        except ValueError:
            continue
        if best is None or abs((g - today).days) < abs((best - today).days):
            best = g
    return best


def _from_greg(gm, gd):
    """The Iranian (month, day) of a Gregorian day and month, in the year that puts it nearest today."""
    today = _today()
    best = None
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            g = dt.date(y, gm, gd)
        except ValueError:
            continue
        if best is None or abs((g - today).days) < abs((best - today).days):
            best = g
    return jalali(best)[1:] if best else None


def fix_dates(src, out, tl):
    """The translation's dates put right from the source's (see above)."""
    if not src or not out:
        return out
    if tl == "en":
        right = {}                                   # day → (month, day) as it must read
        for x in _SOLAR_SRC.finditer(src):
            jd, jm = int(x.group(1).translate(_DIG)), SOLAR_FA.index(x.group(2)) + 1
            g = _from_solar(jm, jd)
            if g:
                right.setdefault(jd, set()).add((g.month, g.day))
        if not right:
            return out
        kept = {(gm, gd) for x in _GREG_SRC_FA.finditer(src)
                for gd, gm in [(int(x.group(1).translate(_DIG)), MONTHS_FA.index(x.group(2)) + 1)]}

        def put(day, mon):
            want = right.get(day)
            got = (_en_month(mon) if mon not in SOLAR_EN else 0, day)
            if not want or len(want) > 1 or got in want or got in kept:
                return None
            gm, gd = next(iter(want))
            return gm, gd

        def a(x):                                    # "November 22"
            r = put(int(x.group(2)), x.group(1))
            return f"{MONTHS_EN[r[0] - 1]} {r[1]}" if r else x.group(0)

        def b(x):                                    # "22 November", "22 Aban"
            r = put(int(x.group(1)), x.group(2))
            return f"{MONTHS_EN[r[0] - 1]} {r[1]}" if r else x.group(0)

        out = re.sub(r"\b" + _ANY_MON_EN + r"\s+(\d{1,2})(?!\d)(?:st|nd|rd|th)?\b", a, out)
        return re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + _ANY_MON_EN + r"\b", b, out)
    if tl == "fa":
        right = {}                                   # day → Iranian (month, day)
        for x in _GREG_SRC.finditer(src):
            mon, day = (x.group(1), x.group(2)) if x.group(1) else (x.group(4), x.group(3))
            gm, gd = _en_month(mon), int(day)
            r = _from_greg(gm, gd) if gm else None
            if r:
                right.setdefault(gd, set()).add(r)
        if not right:
            return out
        kept = {(SOLAR_EN.index(m) + 1, int(d)) for m, d in
                re.findall(r"\b(" + "|".join(SOLAR_EN) + r")\s+(\d{1,2})\b", src)}

        def c(x):                                    # «۱۳ آبان» for "November 13"
            day, jm = int(x.group(1).translate(_DIG)), SOLAR_FA.index(x.group(2)) + 1
            want = right.get(day)
            if not want or len(want) > 1 or (jm, day) in want or (jm, day) in kept:
                return x.group(0)
            rm, rd = next(iter(want))
            digits = str(rd).translate(_FA_DIG) if re.search("[۰-۹]", x.group(1)) else str(rd)
            return f"{digits} {SOLAR_FA[rm - 1]}"

        return _SOLAR_SRC.sub(c, out)
    return out


def fix_terms(src, out, tl):
    """Corrections that depend on the source text."""
    out = fix_dates(src, out, tl)
    if tl == "en" and out:
        if "پزشکیان" in (src or "") and "پزشکان" not in src:
            out = _DOCTORS_EN.sub("Pezeshkian", out)   # the president's name read as "doctors"
        if _HEGSETH_SRC.search(src or ""):
            out = _HEGSETH_EN.sub("Hegseth", out)      # "هگست" read as "Hegst", "Hogst", "Hegset"
        return out
    if tl != "fa" or not out:
        return out
    src = src or ""
    if "مثقال" in out and _SHEKEL.search(src):
        out = out.replace("مثقال", "شِکِل")
    if _US_PRES_FA.search(out) and not _OTHER_SCRIPT.search(src) and not _US_SRC.search(src):
        out = _US_PRES_FA.sub("رئیس‌جمهور ایران" if _IR_PRES_SRC.search(src) else "رئیس‌جمهور", out)
    if ("معدن" in out or "معادن" in out) and _MINES_SRC.search(src) and not _MINING_SRC.search(src):
        out = out.replace("معادن دریایی", "مین‌های دریایی").replace("معدن دریایی", "مین دریایی")
        out = out.replace("معادن", "مین‌ها").replace("معدن", "مین")
    if "اعتصاب" in out and _STRIKE_SRC.search(src) and not _LABOUR_SRC.search(src):
        out = out.replace("اعتصابات", "حملات").replace("اعتصاب", "حمله")
    if _DIRECTOR_SRC.search(src) and _FILM_SRC.search(src) and "مدیر" in out:
        out = re.sub(r"مدیر(?=\s|$|،)", "کارگردان", out).replace("مدیران", "کارگردانان")
    if _ALPHABET_SRC.search(src):
        out = re.sub(r"(?<![\u0600-\u06FF])(?:الفبا|الفبای)(?![\u0600-\u06FF])", "آلفابت", out)
        out = out.replace("آلفابت اینک", "آلفابت").replace("آلفابت شرکت", "شرکت آلفابت")
    if _PICKAXE_SRC.search(src):
        out = _PICKAXE_FA.sub("کلنگ", out).replace("کوه تبر", "کوه کلنگ")
    for a, b in FA_ALWAYS:
        out = out.replace(a, b)
    return out


def stale(src, out, sl="en", tl="fa"):
    """A stored translation made before a pre-edit rule that would change it (asked again once)."""
    return sl == "en" and tl == "fa" and bool(out) and "کوه" in out and bool(MOUNT_VERB.search(src or ""))


def _post(text, tl):
    if tl == "fa":
        for a, b in FA_POST:
            text = text.replace(a, b)
        for rx, rep in FA_RX_POST:
            text = rx.sub(rep, text)
    return text.strip()


# ------------------------------------------------------------------ engines
def _single(texts, sl, tl, host="translate.googleapis.com", client="gtx"):
    """Several single-line texts in one request, newline separated."""
    r = http.post(f"https://{host}/translate_a/single", params={"client": client, "sl": sl, "tl": tl, "dt": "t"},
                  data={"q": "\n".join(texts)}, timeout=25, retries=1)
    data = r.json()
    out = "".join(seg[0] for seg in (data[0] or []) if seg and seg[0])
    parts = [p.strip() for p in out.split("\n")]
    if len(parts) != len(texts):
        raise ValueError(f"split mismatch {len(parts)} != {len(texts)}")
    return parts


def _multi(texts, sl, tl, host="translate.googleapis.com", client="gtx"):
    """One request, one q parameter per text (no newline juggling)."""
    r = http.post(f"https://{host}/translate_a/t", params={"client": client, "sl": sl, "tl": tl},
                  data=[("q", t) for t in texts], timeout=25, retries=1)
    d = r.json()
    if len(texts) == 1 and isinstance(d, list) and d and isinstance(d[0], str) and len(d) == 2:
        d = [d]                       # single text with sl=auto comes back as [text, lang]
    out = [x if isinstance(x, str) else x[0] for x in d]
    if len(out) != len(texts):
        raise ValueError(f"multi mismatch {len(out)} != {len(texts)}")
    return out


def _clients5(texts, sl, tl):
    return _multi(texts, sl, tl, host="clients5.google.com", client="dict-chrome-ex")


def _offline(texts, sl, tl):
    """Deterministic stand-in used by the offline test suite."""
    table = {}
    try:
        with open(f"{config.FIXTURES}/translations.json", encoding="utf-8") as f:
            table = json.load(f)
    except FileNotFoundError:
        pass
    return [table.get(t, ("[FA] " if tl == "fa" else "[EN] ") + t) for t in texts]


ENGINES = [("single", _single), ("multi", _multi), ("clients5", _clients5)]
MAX_ITEMS = 10
MAX_BYTES = 2600          # UTF-8 bytes of source text per request (Persian is 2 bytes a letter)


class Translator:
    def __init__(self, cache):
        self.cache = cache if cache is not None else {}
        self.stats = {"cached": 0, "failed": 0, "requests": 0}
        self.errors = []
        self._dead = {}           # engine -> consecutive failures

    def key(self, text, sl, tl):
        return sha(f"{sl}>{tl}:{text}", 20)

    def get(self, text, sl, tl):
        e = self.cache.get(self.key(text, sl, tl))
        return e[0] if e else None

    def translate_many(self, texts, sl, tl):
        """Return dict text -> translation (missing on failure)."""
        result, todo = {}, []
        for t in dict.fromkeys(x for x in texts if x and x.strip()):
            e = self.cache.get(self.key(t, sl, tl))
            if e and stale(t, e[0], sl, tl):
                e = None                   # translated before its glossary rule existed: ask again
            if e:
                result[t] = e[0]
                e[1] = now()
                self.stats["cached"] += 1
            else:
                todo.append(t)
        batch, size = [], 0
        for t in todo:
            n = len(t.encode("utf-8"))
            if batch and (size + n > MAX_BYTES or len(batch) >= MAX_ITEMS):
                self._run(batch, sl, tl, result)
                batch, size = [], 0
            batch.append(t)
            size += n
        if batch:
            self._run(batch, sl, tl, result)
        return {k: fix_terms(k, v, tl) for k, v in result.items()}

    def _err(self, msg):
        log(msg)
        if len(self.errors) < 12:
            self.errors.append(msg[:160])

    def _run(self, batch, sl, tl, result):
        pre = [_pre(t, sl)[:1800] for t in batch]
        out = None
        engines = [("offline", _offline)] if config.OFFLINE else ENGINES
        for name, fn in engines:
            if self._dead.get(name, 0) >= 3:
                continue
            try:
                self.stats["requests"] += 1
                out = fn(pre, sl, tl)
                self.stats[name] = self.stats.get(name, 0) + len(batch)
                self._dead[name] = 0
                break
            except Exception as e:  # noqa: BLE001
                self._dead[name] = self._dead.get(name, 0) + 1
                self._err(f"translate {name} {sl}>{tl} ({len(batch)} items, "
                          f"{sum(len(p.encode()) for p in pre)}B): {str(e)[:100]}")
                time.sleep(0.6)
        if out is None and len(batch) > 1:
            # last resort: one text per request so a single bad text can't sink the batch
            out = []
            for p in pre:
                try:
                    self.stats["requests"] += 1
                    out.append(_multi([p], sl, tl)[0])
                except Exception as e:  # noqa: BLE001
                    self._err(f"translate one-by-one {sl}>{tl}: {str(e)[:100]}")
                    out.append(None)
                time.sleep(0.1)
        if out is None:
            self.stats["failed"] += len(batch)
            return
        if not config.OFFLINE:
            time.sleep(0.12)
        for src, tr in zip(batch, out):
            tr = _post(tr, tl) if tr else ""
            if tr:
                result[src] = tr
                self.cache[self.key(src, sl, tl)] = [tr, now()]
            else:
                self.stats["failed"] += 1

    def prune(self, max_age=7 * 24 * 3600, max_entries=24000):
        cut = now() - max_age
        for k in [k for k, v in self.cache.items() if v[1] < cut]:
            del self.cache[k]
        if len(self.cache) > max_entries:
            for k, _ in sorted(self.cache.items(), key=lambda kv: kv[1][1])[: len(self.cache) - max_entries]:
                del self.cache[k]
