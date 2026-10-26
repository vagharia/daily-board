"""Sport: matches, clubs, teams, federations and the stadiums they play in.

A sports report is not war news, even when the war is why a match was called off or a team would not travel. It is
kept, as a yellow story, when it speaks of the war or of security, and dropped otherwise, since attacks, wars and
threats are figures of speech in sport. A sports headline counts as war news only when it reports a strike itself: on
a stadium or a team's camp, with people killed, or as the news it opens with ("Missile attack on Riyadh; Al-Nassr
match called off")."""
import re

from .classify_fa import _ANY, _B, _E, F, R
from .lexicon import en_rx, fa_rx
from .util import fa_norm

CAP = 40.0                      # a sports story is yellow at most

# ------------------------------------------------------------------ Persian
# words that also mean something else are left out: «بازی» (playing with fire), «دیدار» (a meeting), «تیم» (the
# negotiating team), «مسابقه» (the arms race), «کشتی» (a ship), «جام» (a cup of poison), «باشگاه» (the Young
# Journalists Club), «هواداران» (supporters), «تراکتور» (a farmer's tractor hit by a drone), and clubs named after a
# city or a hospital (العین، الشارجه، الاهلی، الشباب)
FA_SPORT = re.compile(fa_rx([
    "فوتبال", "فوتسال", "والیبال", "بسکتبال", "هندبال", "تکواندو", "جودو", "وزنه برداری", "تنیس", "کشتی گیر",
    "کشتی آزاد", "کشتی فرنگی", "فرمول یک", "گرندپری", "گرند پری", "سرمربی", "تیم ملی", "دروازه بان", "ورزشکار",
    "لیگ$", "لیگ های", "لیگ برتر", "لیگ قهرمانان", "لیگ نخبگان", "جام جهانی", "جام حذفی", "جام ملت ها",
    "جام باشگاه ها", "جام خلیج فارس", "سوپرجام", "المپیک", "فیفا", "یوفا", "ای اف سی$", "کنفدراسیون فوتبال",
    "فدراسیون فوتبال", "ورزشگاه", "استادیوم", "مسابقات ورزشی", "مسابقه فوتبال", "مسابقات فوتبال", "رویداد ورزشی",
    "رویدادهای ورزشی", "رویداد های ورزشی", "وزیر ورزش", "وزارت ورزش", "دربی$", "لغو بازی", "تعویق بازی",
    "بازی رفت", "بازی برگشت", "بازی های لیگ", "پرسپولیس", "استقلال تهران", "سپاهان", "تراکتورسازی",
    "تراکتور سازی", "پیکان تهران", "النصر$", "الوصل$", "السد$", "الدحیل$", "الغرافه$", "الریان$",
]).pattern + "|" + R(_B, "الهلال", _E, "(?!\\s*الاحمر)")
    + "|" + R(_B, "بازیکن(?:ان|های|\\s*های)?", _E,
              "(?!\\s*(?:اصلی|کلیدی|منطقه|مهم|بزرگ|فعال|موثر|جدید|سیاسی|ژئوپلیتیک))"))
# sports talk that sounds like war: a shot "like a missile", a goal "under bombardment", the crowd "exploding"
FA_FIGURATIVE = re.compile(F("انفجار شادی", "شوت موشکی", "ضربه موشکی", "بمباران دروازه"))
_KIN_FA = ("(?:حمله\\s*(?:موشکی|پهپادی|هوایی)|حملات\\s*(?:موشکی|پهپادی|هوایی)|موشک|راکت|پهپاد|بمباران|انفجار|پدافند"
           "|آژیر|رهگیری)")
FA_KINETIC = re.compile(R(_B, _KIN_FA))
# the strike as the reason for the sports news, or as a threat: "called off after the missile attack"
FA_CAUSE = re.compile(F("به دلیل", "به خاطر", "در پی", "پس از", "بعد از", "به دنبال", "به علت", "از ترس", "ترس از",
                        "با وجود", "در سایه", "در بحبوحه", "بر اثر", "در اثر", "به سبب", "با توجه به", "هنگام", "حین",
                        "در زمان", "در جریان", "تهدید", "خطر", "احتمال", "نگرانی", "هراس", "وحشت") + "[^.؛!؟?]{0,25}$")
_VENUE_FA = ("(?:ورزشگاه|استادیوم|سالن\\s*ورزشی|مجموعه\\s*ورزشی|زمین\\s*فوتبال|زمین\\s*بازی|اردوی\\s*تیم|کمپ\\s*تیم"
             "|محل\\s*اقامت\\s*(?:تیم|بازیکنان))")
FA_VENUE_ATTACK = re.compile(R(_KIN_FA, _ANY % 30, _VENUE_FA, "|", _VENUE_FA, _ANY % 30,
                               "(?:موشک|راکت|پهپاد|بمب|بمباران|انفجار|اصابت|هدف\\s*قرار|حمله\\s*(?:موشکی|پهپادی|هوایی))"))
FA_DEAD = re.compile(F("کشته شد", "کشته شدند", "کشته شدن", "کشته و زخمی", "کشتار", "به شهادت رسید", "شهید شد",
                       "شهید شدند", "شهید شدن", "جان باخت", "جان خود را از دست") + "|" + R(_B, "کشته", _E)
                     + "|" + R("(?<!سالروز )(?<!سالگرد )(?<!یادواره )", _B, "شهادت", _E))
# weapons and the dead in a headline that isn't about sport: a war report that mentions a match in its text
FA_HARD = fa_rx(["موشک", "پهپاد", "راکت", "بمباران", "حمله هوایی", "حمله موشکی", "حمله پهپادی", "حملات هوایی",
                 "حملات موشکی", "حملات پهپادی", "انفجار", "رهگیری", "آژیر", "شهید", "شهادت", "کشته", "ترور", "پدافند",
                 "اسرائیل", "اسراییل", "صهیونیست"])
# what ties a sports report to the war: security, weapons, the airspace, the war itself
FA_TENSION = re.compile(fa_rx([
    "ناامنی", "امنیتی$", "امنیت$", "ترس جان", "از ترس جان", "ترس از جان", "خطر جانی", "جانشان$", "جان بازیکنان",
    "جنگی$", "موشک", "پهپاد", "راکت", "بمباران", "انفجار", "پدافند", "آژیر", "رهگیری", "حمله هوایی", "حملات هوایی",
    "حریم هوایی", "فضای هوایی", "بسته شدن آسمان", "تعطیلی فرودگاه", "بسته شدن فرودگاه", "لغو پرواز", "لغو پروازها",
    "تعلیق پرواز", "توقف پرواز", "تخلیه", "تنش های منطقه", "تنش منطقه", "تنش در منطقه", "تنش ها در منطقه",
    "تنش های سیاسی", "تنش سیاسی", "تنش نظامی", "تنش های نظامی", "تهدید امنیتی", "تهدیدات امنیتی", "تهدید نظامی",
    "نظامی$", "نیروهای مسلح", "نیرو های مسلح", "اسرائیل", "اسراییل", "صهیونیست", "تحریم", "حوثی", "انصارالله",
    "آتش بس", "آواره", "آوارگان", "پناهگاه", "ویزا", "روادید", "ممنوعیت سفر", "کشته", "شهید شد", "شهید شدند",
    "به شهادت", "شهادت", "ترور",
]).pattern + "|" + R("(?:شرایط|وضعیت|منطقه|سایه|بحبوحه|دلیل|خاطر|پی|ادامه|آغاز|شروع|زمان|دوران|تبعات|پیامد|پیامدهای"
                     "|پیامد\\s*های|ترس\\s*از|خطر|وقوع|احتمال|تشدید)\\s*(?:وقوع\\s*)?جنگ", _E, "|", _B,
                     "جنگ\\s*(?:ایران|اسرائیل|اسراییل|آمریکا|امریکا|منطقه|اخیر|12|۱۲|دوازده|تحمیلی|رمضان|غزه|یمن"
                     "|لبنان)", _E, "|", _B,
                     # attacks on a country, not a team's ("حملات اخیر", "با وجود حملات", "حمله به ریاض")
                     "(?:حمله|حملات)\\s*(?:اخیر|ایران|حوثی|اسرائیل|اسراییل|آمریکا|امریکا|تروریستی|به\\s*(?:ریاض|جده"
                     "|عربستان|امارات|ابوظبی|دبی|قطر|دوحه|کویت|بحرین|عمان|عراق|ایران|تهران|اسرائیل|اسراییل|پایگاه))", "|",
                     F("با وجود حملات", "علی رغم حملات", "به رغم حملات", "در پی حملات", "پس از حملات", "به دلیل حملات",
                       "به خاطر حملات")))

# ------------------------------------------------------------------ English
EN_SPORT = en_rx([
    r"re:(?<!political )\bfootball", "soccer", "world cup", "fifa", "uefa", "afc$", "olympic", "futsal",
    "volleyball", "basketball", "handball", "head coach", "national team", "goalkeeper",
    r"re:(?<!hunger )\bstrikers?\b", "midfielder", "footballer", "athlete", "premier league", "pro league",
    "champions league", "asian cup", "gulf cup", "club world cup", "playoff", "stadium", "grand prix", "formula 1",
    "formula one", "f1$", "motogp", "tennis", "cricket", "tournament", r"re:\bwrestl\w*\b(?! with)", "kick-off",
    "kickoff", "football club", "fc$", "al-nassr", "al nassr", "al-nasr", "al-hilal", "al hilal", "al-wasl",
    "al wasl", "al-sadd", "al sadd", "al-duhail", "al-gharafa", "home games", "home matches", "away games",
    "away matches", "neutral venue",
    r"re:\b(?:match|matches|fixtures?)\b.{0,25}\b(?:postponed|called off|cancell?ed|suspended|relocated|moved"
    r"|abandoned|halted|scrapped)\b",
])
# (only the verb goes, so "attacks head coach" still names the coach)
EN_FIGURATIVE = re.compile(r"\bbombshell\b|\brocket(ed|s)?(?= (into|past|home)\b)|\b(attack|blast|slam)(s|ed|ing)?\b"
                           r"(?= (\w+ ){0,2}(critics?|referees?|fans|media|press|journalists?|reporters?|rivals?"
                           r"|coach(es)?|players?|federation|club|board|officials|pundits?|management)\b)", re.I)
_KIN_EN = (r"\b(missiles?|drones?|rockets?|air ?strikes?|bomb(s|ed|ing|ings)?|explosions?|sirens?|intercept\w*"
           r"|shelling|shot down)\b")
EN_KINETIC = re.compile(_KIN_EN, re.I)
EN_CAUSE = re.compile(r"\b(amid|after|over|due to|because of|following|for fear of|fears? of|threats? of|risk of"
                      r"|despite|in the wake of|during)\b[^.;!?]{0,25}$", re.I)
_VENUE_EN = (r"\b(stadiums?|arenas?|sports (complex|hall|centre|center|club)|football (pitch|ground|field)"
             r"|training (camp|ground)|team hotel)\b")
EN_VENUE_ATTACK = re.compile(_KIN_EN + r".{0,40}" + _VENUE_EN + "|" + _VENUE_EN
                             + r".{0,40}\b(hit|struck|targeted|bombed|shelled|destroyed|damaged)\b", re.I)
EN_DEAD = re.compile(r"\b(killed|martyred|dies|died|deaths?)\b", re.I)
EN_HARD = en_rx(["missile", "drone", "airstrike", "air strike", "strike$", "strikes$", "struck$", "bomb", "explosion",
                 "killed", "shot down", "intercept", "rocket", "air defen", "shelling", "siren"])
EN_TENSION = en_rx([
    "security", "insecurity", "safety concern", "safety fear", "safety reason", "safety risk", "missile", "drone",
    "airstrike", "air strike", "rocket", "siren", "airspace", "air space", "evacuat", r"re:\bbomb(?:s|ed|ing|ings)?\b",
    "explosion", "war$", "wartime", "war-time", "war-torn", "conflict", "hostilities", "regional tension",
    "tensions in the region", "geopolitical", "ceasefire", "cease-fire", "military", "troops", "armed forces",
    "shelling", "sanction", "killed", "houthi", "israel", "hezbollah", "irgc", "displaced", "refugee", "shelter",
    "visa", "travel ban", "attack on", "attacks on", "strike on", "strikes on", "attacks$", "attacked$", "under attack",
    "terror",
])


def _text(lang, title, summary):
    if lang == "fa":
        t, s = fa_norm(title or ""), fa_norm(summary or "")[:300]
        return FA_FIGURATIVE.sub(" ", t), FA_FIGURATIVE.sub(" ", s)
    t, s = title or "", (summary or "")[:300]
    return EN_FIGURATIVE.sub(" ", t), EN_FIGURATIVE.sub(" ", s)


def _strike_led(t, sport_at, kinetic, cause):
    """The headline opens with a strike, not with the sport it led to."""
    for m in kinetic.finditer(t):
        if m.start() >= sport_at:
            return False
        if not cause.search(t[:m.start()]):
            return True
    return False


def story(lang, title, summary=""):
    """'sport' for a sports report, 'war' for a sports headline that reports a strike itself, None otherwise."""
    fa = lang == "fa"
    t, s = _text(lang, title, summary)
    sport, kinetic = (FA_SPORT, FA_KINETIC) if fa else (EN_SPORT, EN_KINETIC)
    m = sport.search(t)
    if not m:
        # only the text speaks of sport: a sports report when its opening is about it (two sports terms or more)
        # and the headline names no weapon; a war report or a speech that mentions a match in passing stays news
        if len({x.group(0).lower() for x in sport.finditer(s)}) < 2 or (FA_HARD if fa else EN_HARD).search(t):
            return None
        return "sport"
    if (FA_VENUE_ATTACK if fa else EN_VENUE_ATTACK).search(t) or (FA_DEAD if fa else EN_DEAD).search(t):
        return "war"
    if _strike_led(t, m.start(), kinetic, FA_CAUSE if fa else EN_CAUSE):
        return "war"
    return "sport"


def tension(lang, title, summary=""):
    """The sports report speaks of the war, of security or of weapons."""
    t, s = _text(lang, title, summary)
    rx = FA_TENSION if lang == "fa" else EN_TENSION
    return bool(rx.search(t) or rx.search(s))
