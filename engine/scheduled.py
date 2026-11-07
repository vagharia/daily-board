"""A notice of something that will happen later, not a report of something happening now.

"عملیات انفجارهای کنترل‌شده … فردا هفدهم آبان اجرا می‌شود", "Controlled detonations will be carried out tomorrow":
an outlet tells people in advance what they will hear. Such a report is no event of the moment: it never goes on the
main front's list and never makes a red story (classify.py adds the flag "scheduled", drops the event flags and keeps it
orange at most).

The rule is strict on purpose, so that real news is never lost to one word. A report is read as a notice only when
all of these hold:
1. it would otherwise be an explosion or a strike on land ("kinetic") and nothing else: an incident at sea, Hormuz
   closed, a nuclear step, a threat, an ultimatum or a retaliation are never read as notices;
2. one sentence of the headline, or the headline with the first sentence of the text, says WHEN in the future
   (فردا, پس‌فردا, روزهای/هفته آینده, شنبه آینده, a date after today such as «هفدهم آبان»; tomorrow, next week, in the
   coming days, a date after today) and HOW it will happen in a future form (اجرا می‌شود/خواهد شد، انجام می‌شود،
   برگزار می‌شود، صورت می‌گیرد، شنیده خواهد شد، … خواهیم داشت; will be carried out, is scheduled to, will take place)
   or as a notice to people (اطلاعیه، به اطلاع می‌رساند، نگران نباشند; residents told not to worry), and that same
   sentence names what will happen (an explosion, a detonation, a drill, a test, an operation);
3. nothing in the headline or the first lines tells of now or the past (هم‌اکنون، دقایقی پیش، امروز، دیشب، شنیده شد، رخ
   داد; now, earlier today, last night, was heard), of an attack, a hit, casualties, an evacuation, an enemy, a ship,
   a threat or a response;
4. no part of the headline outside the future sentence tells of an event with a verb of its own («انفجار در اصفهان رخ
   داد؛ فردا …»).
"""
import datetime as dt
import re

from .util import fa_norm, to_latin_digits

_L = r"ء-غف-ٟٮ-ۓەۮۯۺ-ۿ"
_B = f"(?<![{_L}])"
_E = f"(?![{_L}])"
TEHRAN = dt.timezone(dt.timedelta(hours=3, minutes=30))
AHEAD_DAYS = 60                     # a date further ahead than this is no notice of what people will hear


def _fa(*alts, whole=True):
    """Persian alternatives, normalised like the text; a space matches any run of spaces (or none)."""
    body = "|".join(re.escape(fa_norm(a)).replace(r"\ ", r"\s*") for a in alts)
    return _B + "(?:" + body + ")" + (_E if whole else "")


# ------------------------------------------------------------------ Persian
_SENT_FA = re.compile(r"[.!?؟\n]+")
_CLAUSE_FA = re.compile(r"[.!?؟\n؛;:|/–—]+|\s-\s")

_FUT_TIME_FA = re.compile(
    _fa("پس فردا", "فردا", "فردا صبح", "فردا شب")                       # not «فردای آن روز» (the next day, in a story)
    + "|" + _fa("روز آینده", "روزهای آینده", "روز های آینده", "روزهای آتی", "روز های آتی", "روزهای پیش رو",
                "روز های پیش رو", "هفته آینده", "هفته آتی", "هفته پیش رو", "ماه آینده", "ماه آتی", "ساعات آینده",
                "ساعت های آینده", "ساعتهای آینده")
    + "|" + _B + fa_norm("(?:شنبه|یکشنبه|یک شنبه|دوشنبه|دو شنبه|سه شنبه|سهشنبه|چهارشنبه|چهار شنبه|پنجشنبه|پنج شنبه"
                         "|جمعه)").replace(" ", r"\s*") + r"\s*" + fa_norm("(?:آینده|هفته آینده|آتی)") + _E)

_MONTHS_FA = {fa_norm(m): i + 1 for i, m in enumerate(
    ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"])}
_UNITS = ["یکم", "دوم", "سوم", "چهارم", "پنجم", "ششم", "هفتم", "هشتم", "نهم"]
_ORD = {"اول": 1, "دهم": 10, "یازدهم": 11, "دوازدهم": 12, "سیزدهم": 13, "چهاردهم": 14, "پانزدهم": 15, "پونزدهم": 15,
        "شانزدهم": 16, "هفدهم": 17, "هیفدهم": 17, "هجدهم": 18, "هیجدهم": 18, "نوزدهم": 19, "بیستم": 20, "سی ام": 30,
        "سیام": 30, "سی و یکم": 31}
_ORD.update({u: i + 1 for i, u in enumerate(_UNITS)})
_ORD.update({"بیست و " + u: 21 + i for i, u in enumerate(_UNITS)})
_ORD = {fa_norm(k): v for k, v in _ORD.items()}
_ORD_RX = "|".join(re.escape(k).replace(r"\ ", r"\s*") for k in sorted(_ORD, key=len, reverse=True))
_DATE_FA = re.compile(r"(?<!\d)(?:(\d{1,2})|" + _B + "(" + _ORD_RX + r"))\s*(?:" + fa_norm("ماه") + r"\s*)?("
                      + "|".join(_MONTHS_FA) + ")" + _E + r"(?:\s*(?:" + fa_norm("ماه") + r"\s*)?(?:"
                      + fa_norm("سال") + r"\s*)?(1[34]\d\d))?")

_STEMS_FA = ("(?:اجرا|انجام|برگزار|آغاز|شروع|برپا|منفجر|منهدم|معدوم|امحا|خنثی|شنیده|اعمال|عملیاتی|اجرایی|تخریب"
             "|نابود)")
_FUT_VERB_FA = re.compile(
    _B + fa_norm(_STEMS_FA) + r"\s*(?:" + fa_norm("خواهد|خواهند") + r")\s*(?:" + fa_norm("شد|گردید") + ")" + _E
    + "|" + _B + fa_norm(_STEMS_FA) + r"\s*(?:" + fa_norm("می") + r")?\s*(?:" + fa_norm("شود|شوند|گردد|گردند") + ")" + _E
    + "|" + _fa("صورت می گیرد", "صورت می گیرند", "صورت خواهد گرفت", "صورت می پذیرد", "صورت خواهد پذیرفت",
                "انجام می گیرد", "انجام خواهد گرفت", "به اجرا در می آید", "به اجرا درمی آید", "به اجرا خواهد آمد",
                "به اجرا گذاشته می شود", "به اجرا گذاشته خواهد شد", "خواهیم داشت", "خواهید داشت", "خواهند داشت",
                "خواهد داشت")
    + "|" + _B + fa_norm("قرار") + r"\s*" + fa_norm("است") + r"\s*(?:\S+\s+){0,6}?" + fa_norm(_STEMS_FA) + r"\s*"
    + fa_norm("(?:شود|شوند|گردد|گردند)") + _E)
_NOTICE_FA = re.compile(
    _fa("اطلاعیه", "به اطلاع عموم", "اطلاع رسانی", "نگران نباشند", "نگران نباشید", "موجب نگرانی نشود",
        "باعث نگرانی نشود", "جای نگرانی نیست", "جای نگرانی ندارد", "جای هیچ نگرانی نیست", "دچار نگرانی نشوند")
    + "|" + _B + fa_norm("به") + r"\s*" + fa_norm("اطلاع") + r"\s*(?:\S+\s+){0,4}?" + fa_norm("می") + r"\s*"
    + fa_norm("رساند") + _E
    + "|" + _B + fa_norm("از") + r"\s*" + fa_norm("(?:شهروندان|مردم|ساکنان|اهالی|همشهریان|هم وطنان|هموطنان)")
    + r"\s*(?:\S+\s+){0,3}?" + fa_norm("(?:خواسته|درخواست|تقاضا)"))
# what is scheduled: the sentence must name it
_WHAT_FA = re.compile(_fa("انفجار", "انفجارها", "انفجارهای", "انفجار ها", "انفجار های", "منفجر", "انهدام", "امحا",
                          "امحای", "خنثی سازی", "صدای", "صدا", "شلیک", "رزمایش", "مانور", "تمرین", "آزمایش", "تست",
                          "عملیات", "معدوم سازی", "تخریب", "پدافند", whole=False))
# now or the past, an attack and its toll, an enemy, a threat: never a notice
_VETO_FA = re.compile(
    _fa("هم اکنون", "همین الان", "همینک", "هم اینک", "اکنون", "الان", "لحظاتی پیش", "لحظاتی قبل", "دقایقی پیش",
        "دقایقی قبل", "دقیقه پیش", "ساعاتی پیش", "ساعاتی قبل", "ساعتی پیش", "ساعتی قبل", "ساعت پیش", "امروز", "امشب",
        "بامداد امروز", "دیشب", "شب گذشته", "دیروز", "روز گذشته", "پریروز", "در حال", "ادامه", "دوباره", "مجدد", "مجددا", "باز هم",
        "شنیده شد", "شنیده شده", "رخ داد", "رخ داده", "به وقوع پیوست", "اتفاق افتاد", "منفجر شد", "منفجر شده",
        "گزارش شد", "گزارش شده", "گزارش ها", "شاهدان", "شهروندان گزارش")
    + "|" + _B + fa_norm("بامداد") + r"(?!\s*" + fa_norm("فردا") + ")" + _E
    + "|" + _fa("حمله", "حملات", "تهاجم", "تجاوز", "بمباران", "اصابت", "هدف قرار", "ترور", "کشته", "شهید", "شهادت",
                "زخمی", "مجروح", "مصدوم", "جان باخت", "جانباخت", "تلفات", "قربانی", "تخلیه", "اولتیماتوم", "ضرب الاجل",
                "مهلت", "تهدید", "انتقام", "تلافی", "پاسخ", "دشمن", "صهیونیست", "اسرائیل", "اسراییل", "آمریکا",
                "امریکا", "سنتکام", "پنتاگون", "ناو", "نفتکش", "کشتی", "توقیف", "غرق", "سقوط", "آتش سوزی", "حریق",
                "آژیر", "پهپاد", "جنگنده", "ترامپ", "نتانیاهو", "انتحاری", "تروریست", "پایگاه", "پالایشگاه",
                "نیروگاه", "تاسیسات هسته", "نطنز", "فردو", whole=False))
# a verb telling of an event that happened or is happening ("رخ داد", "شنیده شد", "منفجر شد", "هدف قرار گرفت")
_PAST_VERB_FA = re.compile(
    r"(?<!" + fa_norm("خواهد") + r")(?<!" + fa_norm("خواهند") + r")(?<!" + fa_norm("خواهد") + r"\s)"
    r"(?<!" + fa_norm("خواهند") + r"\s)" + _B + fa_norm("(?:شد|شدند|شده|گردید|گردیدند|کرد|کردند|کرده|زد|زدند|داد"
                                                        "|دادند|گرفت|گرفتند|رسید|پیوست|افتاد|است|اند|بود|بودند)") + _E)


def jalali(d):
    """(year, month, day) in the Iranian calendar of a Gregorian date."""
    gy, gm, gd = d.year, d.month, d.day
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def gregorian(jy, jm, jd):
    """The Gregorian date of an Iranian (year, month, day); ValueError for a day the month doesn't have."""
    if not (1 <= jm <= 12 and 1 <= jd <= (31 if jm <= 6 else 30)):
        raise ValueError("no such day")
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd + (31 * (jm - 1) if jm < 7
                                                                              else (jm - 7) * 30 + 186)
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    return dt.date(gy, 1, 1) + dt.timedelta(days=days)


def _future_date_fa(text, now_ts):
    """True when the text names an Iranian date after today (Tehran) and at most AHEAD_DAYS ahead."""
    if not now_ts:
        return False
    g_today = dt.datetime.fromtimestamp(now_ts, TEHRAN).date()
    today = jalali(g_today)
    for x in _DATE_FA.finditer(text):
        d = int(x.group(1)) if x.group(1) else _ORD.get(re.sub(r"\s+", " ", x.group(2)))
        mon = _MONTHS_FA.get(x.group(3))
        if not d or not mon or not 1 <= d <= 31:
            continue
        years = [int(x.group(4))] if x.group(4) else [today[0], today[0] + 1]
        for y in years:
            try:
                gap = (gregorian(y, mon, d) - g_today).days
            except ValueError:
                continue
            if 1 <= gap <= AHEAD_DAYS:
                return True
    return False


def _future_sentence_fa(sent, now_ts):
    return bool((_FUT_TIME_FA.search(sent) or _future_date_fa(sent, now_ts))
                and (_FUT_VERB_FA.search(sent) or _NOTICE_FA.search(sent)) and _WHAT_FA.search(sent))


def _notice_fa(title, summary, now_ts):
    t = fa_norm(to_latin_digits(title or ""))
    s = fa_norm(to_latin_digits(summary or ""))
    lead = (_SENT_FA.split(s)[0] if s else "")[:300]
    if _VETO_FA.search(t) or (lead and _VETO_FA.search(lead)):
        return False
    return _parts_ok([x for x in _CLAUSE_FA.split(t) if x.strip()], lead, t, now_ts, _future_sentence_fa,
                     lambda x: bool(_FUT_TIME_FA.search(x) or _future_date_fa(x, now_ts) or _FUT_VERB_FA.search(x)
                                    or _NOTICE_FA.search(x)),
                     _PAST_VERB_FA, _WHAT_FA)


def _parts_ok(clauses, lead, t, now_ts, future, hint, past_verb, what):
    """The headline's parts and the text's first sentence read together as a notice (rules 2 and 4 above)."""
    fut = [x for x in clauses if future(x, now_ts)]
    lead_ok = bool(lead) and future(lead, now_ts)
    if not fut and not (lead_ok and hint(t)):
        return False
    for x in clauses:
        if x in fut:
            continue
        if past_verb.search(x):
            return False                      # «انفجار در اصفهان رخ داد؛ فردا …»: an event of its own
        if what.search(x) and not lead_ok:
            return False                      # «صدای انفجار در اصفهان؛ فردا هم …»: only the text could say it is planned
    return True


# ------------------------------------------------------------------ English
_SENT_EN = re.compile(r"(?<=[.!?])\s+|\n+")
_CLAUSE_EN = re.compile(r"[;:|]|\s[-–—]\s")
_FUT_TIME_EN = re.compile(
    r"\b(tomorrow|the day after tomorrow|next (week|month|(mon|tues|wednes|thurs|fri|satur|sun)day)"
    r"|in the (coming|next) (few )?(days|weeks|hours)|later this (week|month)|over the (coming|next) (few )?(days|weeks))\b",
    re.I)
_MONTHS_EN = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                              "august", "september", "october", "november", "december"])}
_DATE_EN = re.compile(r"\b(?:(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(_MONTHS_EN) + r")|(" + "|".join(_MONTHS_EN)
                      + r")\s+(\d{1,2})(?:st|nd|rd|th)?)\b", re.I)
_FUT_VERB_EN = re.compile(
    r"\b(will|would|shall) be (carried out|conducted|held|heard|detonated|staged|performed|undertaken|done|destroyed"
    r"|defused|disposed of)\b|\b(will|shall) take place\b|\b(is|are|was|were) (scheduled|planned|set|due) (to|for)\b"
    r"|\b(scheduled|planned) (to|for)\b|\bset to take place\b|\bto be (carried out|conducted|held|detonated|staged|performed)\b", re.I)
_NOTICE_EN = re.compile(r"\b(notice|advisory|no (cause|need|reason) for (alarm|concern|panic)"
                        r"|(not|no need) to (worry|panic|be alarmed)|(residents|people|citizens|public) (are|were|have been)"
                        r" (told|asked|advised|informed|notified))\b", re.I)
_WHAT_EN = re.compile(r"\b(explosions?|blasts?|detonations?|detonat\w+|drills?|exercises?|tests?|testing|operations?"
                      r"|demolitions?|disposal|sounds?|noises?|booms?|air defen[cs]e)\b", re.I)
_VETO_EN = re.compile(
    r"\b(now|currently|underway|ongoing|earlier|today|tonight|this (morning|afternoon|evening)|last night|yesterday"
    r"|overnight|hours? ago|minutes? ago|moments? ago|was heard|were heard|reported|witness\w*|has begun|began"
    r"|continu\w*|again|more|another|renewed|resum\w*"
    r"|attack\w*|strikes?|struck|bomb(ed|ing|ings|ard\w*)|hit|hits|killed|dead|died|wounded|injured|casualt\w+|victims?"
    r"|evacuat\w+|ultimatum|deadline|threat\w*|warn\w*|retaliat\w*|revenge|respon\w+|enemy|israel\w*|u\.s\.|us"
    r"|america\w*|pentagon|centcom|trump|netanyahu|tankers?|ships?|vessels?|seiz\w+|sank|sunk|crash\w*|fires?"
    r"|sirens?|drones?|jets?|warplanes?|missiles?|rockets?|terror\w*|bases?|refiner\w+|nuclear|natanz|fordow)\b", re.I)
_PAST_VERB_EN = re.compile(r"\b(was|were|has|have|had|is|are) (been )?\w+ed\b|\b\w+ed (in|at|near|on)\b", re.I)


def _future_date_en(text, now_ts):
    if not now_ts:
        return False
    today = dt.datetime.fromtimestamp(now_ts, TEHRAN).date()
    for x in _DATE_EN.finditer(text):
        d = int(x.group(1) or x.group(4))
        mon = _MONTHS_EN[(x.group(2) or x.group(3)).lower()]
        for y in (today.year, today.year + 1):
            try:
                gap = (dt.date(y, mon, d) - today).days
            except ValueError:
                continue
            if 1 <= gap <= AHEAD_DAYS:
                return True
    return False


def _future_sentence_en(sent, now_ts):
    return bool((_FUT_TIME_EN.search(sent) or _future_date_en(sent, now_ts))
                and (_FUT_VERB_EN.search(sent) or _NOTICE_EN.search(sent)) and _WHAT_EN.search(sent))


def _notice_en(title, summary, now_ts):
    t, s = title or "", summary or ""
    lead = (_SENT_EN.split(s.strip())[0] if s.strip() else "")[:300]
    if _VETO_EN.search(t) or (lead and _VETO_EN.search(lead)):
        return False
    return _parts_ok([x for x in _CLAUSE_EN.split(t) if x.strip()], lead, t, now_ts, _future_sentence_en,
                     lambda x: bool(_FUT_TIME_EN.search(x) or _future_date_en(x, now_ts) or _FUT_VERB_EN.search(x)
                                    or _NOTICE_EN.search(x)),
                     _PAST_VERB_EN, _WHAT_EN)


# ------------------------------------------------------------------
NOT_A_NOTICE = {"maritime_incident", "hormuz_closure", "nuclear_red", "ultimatum", "kinetic_threat", "threat",
                "retaliation", "denial", "past"}


def notice(lang, title, summary, flags, now_ts):
    """True when a report that reads as an explosion or a strike is an advance notice of something planned (see above)."""
    flags = set(flags or [])
    if "kinetic" not in flags or flags & NOT_A_NOTICE:
        return False
    if lang == "fa":
        return _notice_fa(title, summary, now_ts)
    return _notice_en(title, summary, now_ts)
