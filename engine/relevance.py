"""Decide whether an item is about the Iran / US / Israel / Persian Gulf conflict space."""
import re

from .internet import internet
from .lexicon import en_rx, fa_rx
from .util import fa_norm

# ------------------------------------------------------------------ English
EN_CORE = en_rx([
    "iran", "tehran", "irgc", "revolutionary guard", "khamenei", "hormuz", "persian gulf", "gulf of oman",
    "hezbollah", "houthi", "centcom", "natanz", "fordow", "fordo$", "bushehr", "kharg", "bandar abbas",
    "araghchi", "araqchi", "pezeshkian", "larijani", "vahidi", "quds force", "ayatollah", "basij", "isfahan",
])
EN_MID = en_rx([
    "israel", "idf$", "netanyahu", "tel aviv", "mossad", "katz$",
    "middle east", "mideast", "gulf states", "gulf countries", "gulf arab", "saudi", "riyadh", "uae$", "emirat",
    "abu dhabi", "qatar", "doha", "oman$", "omani", "muscat", "bahrain", "kuwait", "iraq", "baghdad", "erbil",
    "syria", "damascus", "lebanon", "lebanese", "beirut", "yemen", "sanaa", "hodeidah", "red sea", "bab el-mandeb",
    "bab al-mandab", "gaza", "hamas", "west bank", "jordan$", "enrichment", "uranium", "iaea", "nuclear deal",
    "jcpoa", "snapback", "e3$", "tanker", "crude", "brent", "opec", "strait$", "jerusalem", "haifa", "dimona", "eilat",
    "ukmto", "diego garcia", "al udeid", "incirlik", "akrotiri", "prince sultan air base", "al dhafra",
    "ain al-asad", "muwaffaq", "nevatim", "ramon air base",
])
EN_SEC = en_rx([
    "strike$", "strikes$", "struck$", "airstrike", "air strike", "missile", "drone", "attack", "war$", "wars$",
    "warfare", "ceasefire", "cease-fire", "truce", "sanction", "military", "troops", "navy$", "naval", "warship",
    "aircraft carrier", "carrier strike", "bomber", "retaliat", "escalat", "threat", "nuclear", "blockade",
    "airspace", "evacuat", "intercept", "explosion", "blast$", "killed", "invasion", "ultimatum", "mobiliz",
    "deploy", "shrapnel", "air defen", "airport",
])
# military aircraft movements reported by the media (deployments, tankers, airlift)
EN_AIR = en_rx([
    "refuel", "tanker aircraft", "tanker planes", "tanker jets", "airlift", "warplane", "fighter jet",
    "fighter squadron", "squadron", "cargo flights", "cargo planes", "military flights", "military aircraft",
    "transport planes", "awacs", "stealth bomber", "bomber",
    r"re:\b(?:kc|c|f|b|e|p|mq|rq)-?(?:135|46|10|17|5|15|16|22|35|52|2|1b?|3|8|9|4)s?\b",
])
# Russian and Chinese leaders and diplomats: what they say about the region is news
EN_POWERS = en_rx(["putin", "lavrov", "peskov", "zakharova", "kremlin", "medvedev", "shoigu", "ryabkov", "nebenzia",
                   "ulyanov", "russian foreign ministry", "russia's foreign ministry", "xi jinping", "president xi",
                   "wang yi", "mao ning", "lin jian", "guo jiakun", "fu cong", "chinese foreign ministry",
                   "china's foreign ministry", "beijing", "moscow"])
# the Russia-Ukraine war is not covered at all, even when it moves oil prices or Trump speaks about it; a report that
# mentions it counts only when it also names something from the Middle East
EN_UKRAINE = en_rx(["ukrain", "kyiv", "kiev", "zelensk", "donbas", "donetsk", "luhansk", "crimea", "kursk$",
                    "zaporizh", "kharkiv", "odesa", "odessa", "kherson", "mariupol", "bakhmut", "pokrovsk"])
EN_ME = en_rx(["middle east", "mideast", "west asia"])
# the parts of EN_MID that say nothing about where (the nuclear file, oil, shipping, far-away bases)
EN_MID_GENERIC = en_rx(["enrichment", "uranium", "iaea", "nuclear deal", "jcpoa", "snapback", "e3$", "tanker", "crude",
                        "brent", "opec", "strait$", "ukmto", "diego garcia", "incirlik", "akrotiri"])
# weak signals: enough together with a core term, not enough to make a Middle East item relevant on their own
EN_WEAK = en_rx(["talks$", "negotiat", "envoy", "diplomat", "oil price", "shipping", "warn", "summit", "minister"])
ECON_A = re.compile(r"\b(oil|crude|brent|wti|opec\+?|lng|tankers?|gasoline|diesel|jet fuel)\b", re.I)
ECON_B = re.compile(r"\b(prices?|surg\w*|jump\w*|soar\w*|spik\w*|rall\w*|climb\w*|fall\w*|drop\w*|slump\w*|plung\w*"
                    r"|tumbl\w*|suppl\w*|output|exports?|imports?|market\w*|barrels?|futures|rates?|insurance)\b", re.I)
GOLD = re.compile(r"\bgold\b.{0,60}\b(war|tension\w*|geopolitic\w*|safe[- ]haven|middle east|iran\w*|conflict|record)\b"
                  r"|\b(war|tension\w*|geopolitic\w*|safe[- ]haven|middle east|iran\w*|conflict)\b.{0,60}\bgold\b", re.I)
EN_US = en_rx(["trump", "rubio", "vance$", "bessent", "hegseth", "witkoff", "pentagon", "white house",
               "state department", "treasury"])
EN_NOISE = en_rx([
    "football", "soccer", "world cup", "fifa", "olympic", "wrestling", "volleyball", "futsal", "basketball",
    "tournament", "goalkeeper", "medal", "box office", "film festival", "movie", "concert", "fashion", "recipe",
    "grand prix", "formula 1", "cricket", "tennis", "chess", "oscars", "eurovision", "horoscope",
])

# weather reports (a storm warning for Hormozgan, wind and waves in the Gulf): read in the headline and the start of
# the text, and dropped unless the headline names a weapon or a strike
EN_WEATHER = re.compile(r"\b(weather (forecast|warning|alert|service|office)|meteorolog\w*|thunderstorms?|rainfall"
                        r"|heavy rains?|flash floods?|sandstorms?|dust storms?|heat ?waves?|wind speeds?|wave heights?"
                        r"|high waves|gale)\b", re.I)
EN_SPORT = en_rx(["football", "soccer", "world cup", "fifa", "olympic", "futsal", "volleyball", "basketball",
                  "head coach", "national team", "goalkeeper", "striker$", "midfielder", "premier league", "playoff"])
EN_HARD = en_rx(["missile", "drone", "airstrike", "air strike", "strike$", "strikes$", "bomb", "explosion",
                 "killed", "shot down", "intercept", "rocket", "air defen"])

# ------------------------------------------------------------------ Persian
FA_CORE = fa_rx([
    "آمریکا", "امریکا", "ایالات متحده", "اسرائیل", "اسراییل", "رژیم صهیونیستی", "صهیونیست", "تل آویو",
    "هرمز$", "خلیج فارس", "دریای عمان", "سنتکام", "ترامپ", "روبیو", "ونس$", "بسنت", "هگست", "هگزث", "ویتکاف",
    "ویتکوف", "نتانیاهو", "حزب الله", "انصارالله", "حوثی", "پنتاگون", "کاخ سفید", "ناو هواپیمابر", "هواپیمابر",
    "بمب افکن", "گروسی", "اسنپ بک", "مکانیسم ماشه", "شورای امنیت سازمان ملل", "آژانس بین المللی انرژی اتمی",
    "موساد", "سیا$", "ناوگان پنجم", "ناوگان دریایی آمریکا",
])
FA_MID = fa_rx([
    "عربستان", "ریاض$", "امارات", "ابوظبی", "قطر$", "قطری", "دوحه", "عمان", "مسقط", "بحرین", "کویت", "عراق$",
    "عراقی", "بغداد",
    "سوریه", "دمشق", "لبنان", "بیروت", "یمن", "صنعا", "دریای سرخ", "باب المندب", "غزه", "حماس",
    "تروئیکا", "غنی سازی", "اورانیوم", "هسته ای", "نفتکش", "تحریم", "مذاکره",
    "مذاکرات", "عراقچی", "لاریجانی", "وحیدی", "بقائی", "بقایی", "قالیباف", "شورای عالی امنیت ملی", "سپاه$",
    "ارتش", "پدافند", "نیروی دریایی", "موشک", "پهپاد", "جنگنده", "آتش بس", "رزمایش", "اولتیماتوم", "شورای امنیت",
    "ترور",
    "سوخت رسان", "ترابری", "هواپیماهای نظامی", "هواپیمای نظامی", "پروازهای نظامی", "پایگاه نظامی", "پایگاه هوایی",
    "پایگاه دریایی", "پایگاه موشکی", "پایگاه های نظامی", "پایگاه های آمریکا", "پایگاه آمریکا", "العدید",
    "دیه گو گارسیا", "هواپیمای نظارتی", "هواپیمای جاسوسی", "نیروی هوایی", "حریم هوایی", "دبی$", "نطنز", "فردو$",
    "خارگ", "خارک", "خاورمیانه",
])
# the generic part of FA_MID (military, nuclear, sanctions, talks): it says nothing about where
FA_MID_GENERIC = fa_rx([
    "غنی سازی", "اورانیوم", "هسته ای", "نفتکش", "تحریم", "مذاکره", "مذاکرات", "ارتش", "پدافند", "نیروی دریایی",
    "موشک", "پهپاد", "جنگنده", "آتش بس", "رزمایش", "اولتیماتوم", "شورای امنیت", "ترور", "سوخت رسان", "ترابری",
    "هواپیماهای نظامی", "هواپیمای نظامی", "پروازهای نظامی", "پایگاه نظامی", "پایگاه هوایی", "پایگاه دریایی",
    "پایگاه موشکی", "پایگاه های نظامی", "هواپیمای نظارتی", "هواپیمای جاسوسی", "نیروی هوایی", "حریم هوایی",
])
# Russia, China and Europe, their leaders and diplomats: news here only next to something from the Middle East
# (Lavrov on Iran, Xi on Gaza), not a Putin-Xi summit or Europe's own tensions
FA_POWERS = fa_rx([
    "روسیه", "روس$", "چین$", "چینی$", "اروپا", "پوتین", "لاوروف", "پسکوف", "زاخارووا", "کرملین", "مدودف", "شویگو",
    "ریابکوف", "نبنزیا", "اولیانوف", "شی جین پینگ", "وانگ یی", "مائو نینگ", "لین جیان", "مسکو", "پکن",
])
# Iran's top officials: with a foreign power or a regional term (a trip to Moscow, talks in Beijing) it is news;
# with an Iranian city alone it is domestic politics
FA_IR_TOP = fa_rx(["پزشکیان", "خامنه ای", "رهبر انقلاب", "عراقچی", "لاریجانی", "قالیباف", "ظریف", "ولایتی",
                   "شمخانی", "عارف", "وزیر امور خارجه", "وزیر خارجه ایران", "وزیر دفاع", "هیئت ایرانی", "هیات ایرانی",
                   "ستاد کل نیروهای مسلح", "ستاد کل نیرو های مسلح", "فرمانده کل سپاه", "فرمانده کل ارتش",
                   "دبیر شورای عالی امنیت ملی"])
# words that are everywhere in the news: they count only next to an actor, a region or a military term
FA_GEN = fa_rx(["حمله", "حملات", "جنگ$", "تجاوز", "انفجار", "تهدید", "هشدار", "ضرب الاجل", "تنگه"])
FA_WAR = fa_rx(["حمله", "حملات", "جنگ$", "تجاوز", "انفجار"])
# Iranian places: an explosion or air defence activity in Tabriz is news even without a foreign actor, but two
# city names ("Tehran - Mashhad flight") or a city and a warning ("bear on the Shiraz road; a warning") are not
FA_CITY = fa_rx([
    "تهران", "تبریز", "اصفهان", "شیراز", "مشهد", "کرج", "قم$", "اهواز", "بندرعباس", "بوشهر", "کرمانشاه",
    "ارومیه", "خرمشهر", "آبادان", "چابهار", "کیش", "قشم", "هرمزگان", "خوزستان", "سیستان", "بلوچستان",
    "کردستان", "آذربایجان",
])
FA_KIN = fa_rx(["انفجار", "حمله", "حملات", "پدافند", "موشک", "پهپاد", "شلیک", "آژیر", "بمباران", "رهگیری",
                "جنگنده", "پرتابه", "سقوط"])
# far-away conflicts and politics: not relevant unless the headline also names one of the core actors or Iran
FA_FOREIGN = fa_rx([
    "اوکراین", "کی یف", "کییف", "بلغارستان", "دریای سیاه", "ونزوئلا", "تایوان", "کره شمالی", "میانمار", "سودان",
    "لیبی", "نیجر", "کلمبیا", "مکزیک", "آرژانتین", "برزیل", "فرانسه", "آلمان", "انگلیس", "بریتانیا", "ایتالیا",
    "اسپانیا", "لهستان", "رومانی", "صربستان", "ژاپن", "استرالیا", "کانادا", "کشمیر", "بنگلادش", "سومالی", "اتیوپی",
])
FA_IRAN = fa_rx(["ایران", "ایرانی", "تهران", "جمهوری اسلامی"])
FA_UKRAINE = fa_rx(["اوکراین", "کی یف", "کییف", "زلنسکی", "دونباس", "دونتسک", "لوهانسک", "کریمه", "کورسک",
                    "زاپوریژیا", "خارکیف", "اودسا", "خرسون"])
FA_ME = fa_rx(["خاورمیانه", "غرب آسیا"])
# Iran itself and its own theatre: what a headline about Ukraine must also name to stay (besides the Middle East)
FA_IRAN_CORE = fa_rx(["هرمز$", "خلیج فارس", "دریای عمان", "حزب الله", "انصارالله", "حوثی", "سنتکام", "اسنپ بک",
                      "مکانیسم ماشه", "سپاه$", "نطنز", "فردو$", "خارگ", "خارک", "شورای عالی امنیت ملی"])
# the American and international part of FA_CORE: Trump, the Pentagon or the IAEA on Ukraine is still the Ukraine war
FA_CORE_US = fa_rx(["آمریکا", "امریکا", "ایالات متحده", "ترامپ", "روبیو", "ونس$", "بسنت", "هگست", "هگزث", "ویتکاف",
                    "ویتکوف", "پنتاگون", "کاخ سفید", "سیا$", "بمب افکن", "ناو هواپیمابر", "هواپیمابر",
                    "ناوگان دریایی آمریکا", "شورای امنیت سازمان ملل", "آژانس بین المللی انرژی اتمی", "گروسی"])
# economy and markets: dropped for Telegram channels whose economic posts the owner doesn't want
FA_ECON = fa_rx([
    "بورس", "فرابورس", "شاخص کل", "سهام", "سهامداران", "نماد", "صندوق", "معاملات", "عرضه اولیه", "تالار",
    "سکه", "طلا", "قیمت دلار", "نرخ ارز", "ارز", "تتر", "رمزارز", "بیت کوین", "تورم", "نقدینگی", "بانک مرکزی",
    "سود", "مالیات", "صورت مالی", "صورتهای مالی", "حقیقی", "حقوقی", "بازار سرمایه", "اوراق", "تومان", "ریال",
    "قیمت", "گرانی", "بنزین", "خودرو", "مسکن", "اجاره", "یارانه",
])
FA_MILPOL = fa_rx([
    "حمله", "حملات", "موشک", "پهپاد", "جنگ$", "انفجار", "سپاه$", "ارتش", "پدافند", "ترامپ", "نتانیاهو", "اسرائیل",
    "آمریکا", "مذاکره", "مذاکرات", "توافق", "تحریم", "هرمز$", "حوثی", "حزب الله", "عراقچی", "خامنه ای", "رهبر",
    "آتش بس", "نظامی", "امنیتی", "تهدید", "هشدار", "شورای امنیت", "ناو", "جنگنده", "بمباران", "رهگیری",
    "نیروی هوایی", "هواپیمای نظارتی", "شناسایی", "جاسوسی", "رادار", "میانجی", "العربیه", "سوخت رسان", "ترابری",
])
FA_NOISE = fa_rx([
    "فوتبال", "والیبال", "فوتسال", "بسکتبال", "جام جهانی", "لیگ برتر", "المپیک", "سینما", "کنسرت",
    "تیم ملی", "پرسپولیس", "استقلال تهران", "سریال", "جشنواره فیلم",
    "هواشناسی", "توده تندری", "توده های تندری", "بارش", "بارندگی", "سیلاب", "گرد و خاک", "طوفان شن", "آبگرفتگی",
    "قیمت بلیط", "قیمت بلیت", "نرخ بلیط", "قیمت پرواز", "بوت کمپ", "بوتکمپ",
    "حمله قلبی", "حمله عصبی", "حمله آسم", "حمله سگ", "سگ ولگرد", "سگهای ولگرد", "سگ های ولگرد", "زورگیری",
    "پدافند غیرعامل", "پدافند غیر عامل", "آلودگی هوا", "کیفیت هوا", "هوای آلوده", "زلزله", "زمین لرزه", "ترافیک",
])
# weather, checked in the headline and the start of the text ("هشدار دریایی… افزایش سرعت باد و ارتفاع موج",
# "تشدید ناپایداری‌های جوی… در هرمزگان")
_WEATHER_FA = ["هواشناسی", "پیش بینی هوا", "ناپایداری جوی", "ناپایداری های جوی", "ناپایداری هوا", "توفان تندری",
               "توفان های تندری", "طوفان تندری", "طوفان های تندری", "توده تندری", "توده های تندری", "رعد و برق",
               "سامانه بارشی", "سرعت باد", "وزش باد", "تندباد", "ارتفاع موج", "ارتفاع امواج", "دمای هوا", "مه گرفتگی",
               "هشدار سطح زرد", "هشدار سطح نارنجی", "هشدار سطح قرمز"]
FA_WEATHER_LEAD = fa_rx(_WEATHER_FA)
# in the headline also words that can be figures of speech in the text ("بارش موشک" keeps its missile)
FA_WEATHER = fa_rx(_WEATHER_FA + ["بارش", "بارندگی", "تگرگ", "سیلاب", "کاهش دما", "افزایش دما", "مه آلود",
                                  "گرد و خاک", "طوفان شن"])
# sport, checked in the headline and the start of the text: "attack" and "war" are figures of speech there
FA_SPORT = fa_rx([
    "فوتبال", "فوتسال", "والیبال", "بسکتبال", "هندبال", "سرمربی", "تیم ملی", "لیگ برتر", "جام جهانی", "المپیک",
    "پرسپولیس", "استقلال تهران", "سپاهان", "تراکتور", "پیکان تهران", "فدراسیون فوتبال", "بازیکن", "دروازه بان",
    "لیگ قهرمانان", "لیگ نخبگان", "جام حذفی",
])
# what still makes a sport or weather item war news: concrete weapons and casualties
FA_HARD = fa_rx([
    "موشک", "پهپاد", "بمباران", "حمله هوایی", "حمله موشکی", "حمله پهپادی", "انفجار", "شهید", "شهادت", "کشته",
    "ترور", "پدافند", "اسرائیل", "صهیونیست",
])


def _distinct(rx, text):
    return {m.lower() for m in rx.findall(text)} if text else set()


def _me_anchor_en(text):
    return bool(_distinct(EN_CORE, text) or (_distinct(EN_MID, text) - _distinct(EN_MID_GENERIC, text)))


def _me_anchor_fa(text):
    return bool(FA_IRAN.search(text) or (_distinct(FA_CORE, text) - _distinct(FA_CORE_US, text))
                or (_distinct(FA_MID, text) - _distinct(FA_MID_GENERIC, text)) or FA_CITY.search(text))


def _iran_anchor_fa(text):
    return bool(FA_IRAN.search(text) or FA_IR_TOP.search(text) or FA_IRAN_CORE.search(text) or FA_CITY.search(text)
                or FA_ME.search(text))


def _iran_anchor_en(text):
    return bool(EN_CORE.search(text) or EN_ME.search(text))


# Iranian-made weapons over Ukraine ("Russia fires Iranian-designed Shaheds at Kyiv") are still the Ukraine war
_WEAPON_EN = re.compile(r"\biran(ian)?[\s-]*(made|designed|built|supplied)?[\s-]*(shahed|geran|drone|uav|missile)s?\b"
                        r"|\b(shahed|geran)s?\b", re.I)
_WEAPON_FA = re.compile(r"(پهپاد|موشک|پرنده)(های|ها)?\s*(ساخت\s*)?ایران(ی)?|ساخت\s*ایران|شاهد\s*\d*")


def ukraine_war(title, summary, lang="en"):
    """About the Russia-Ukraine war. A headline that names it is about it unless it also names Iran or the Middle
    East (Putin offering to mediate with Iran); Ukraine with Israel or Saudi Arabia alone (Zelensky thanking Israel,
    talks in Riyadh) is still the Ukraine war. When only the opening of the text names it, any Middle East
    reference keeps the report."""
    if lang == "fa":
        t = fa_norm(title or "")
        s = fa_norm(summary or "")[:300].replace("خبرگزاری جمهوری اسلامی", "")
        war, strong, anchor = FA_UKRAINE, _iran_anchor_fa, _me_anchor_fa
    else:
        t, s = title or "", (summary or "")[:300]
        war, strong, anchor = EN_UKRAINE, _iran_anchor_en, _me_anchor_en
    if war.search(t):
        return not strong((_WEAPON_FA if lang == "fa" else _WEAPON_EN).sub(" ", t))
    return bool(war.search(s)) and not anchor(t + " " + s)


def relevance_en(title: str, summary: str):
    t, s = title or "", summary or ""
    ct, cs = _distinct(EN_CORE, t), _distinct(EN_CORE, s)
    mt, ms = _distinct(EN_MID, t), _distinct(EN_MID, s)
    st, ss = _distinct(EN_SEC, t), _distinct(EN_SEC, s)
    wt, ws = _distinct(EN_WEAK, t), _distinct(EN_WEAK, s)
    at = _distinct(EN_AIR, t)
    st |= at
    ut, us = _distinct(EN_US, t), _distinct(EN_US, s)
    pt = _distinct(EN_POWERS, t)
    score = 1.5 * (4 * len(ct) + 2 * len(mt) + len(st) + 0.5 * len(wt) + len(ut)) + \
        (3 * len(cs - ct) + 1.5 * len(ms - mt) + 0.7 * len(ss - st) + 0.3 * len(ws - wt) + 0.7 * len(us - ut))
    other = len(mt | ms) + len(st | ss) + len(wt | ws) + len(ut | us)
    ok = bool(ct) or (bool(cs) and other >= 1) \
        or (bool(mt) and bool(st) and score >= 4.5) \
        or (bool(mt) and bool(ss) and len(mt | ms) >= 2 and score >= 6) \
        or (bool(ut) and bool(mt | cs) and bool(st | ss | wt)) or score >= 10 \
        or (bool(at) and bool(ut | mt | ms | cs)) or (bool(pt) and bool(ct | mt | cs)) \
        or bool(ECON_A.search(t) and ECON_B.search(t)) or bool(GOLD.search(t))
    if ok and EN_NOISE.search(t) and not ct:
        ok = False
    if ok and EN_NOISE.search(t) and ct and not (st | ss):
        ok = False   # e.g. "Iran beat Japan in the World Cup qualifier"
    if ok and not EN_NOISE.search(t) and EN_SPORT.search(s[:300]) and not EN_HARD.search(t):
        ok = False   # a sports story whose headline doesn't say so ("Iran coach attacks critics")
    if ok and (EN_WEATHER.search(t) or EN_WEATHER.search(s[:200])) and not EN_HARD.search(t):
        ok = False   # a storm warning or the weather in the Gulf
    if ok and ukraine_war(t, s):
        ok = False
    if not ok and internet("en", t, s):
        ok = True    # Iran's internet cut, throttled or restored
    return round(score, 1), ok


def relevance_fa(title: str, summary: str):
    """Read in Persian. Relevant if the headline names a core actor or place (the US, Israel, Hormuz…), two
    regional or military terms, one of them with a generic war word or an Iranian place, an Iranian place with an
    explosion, attack or air-defence word, or enough of these in the text as well."""
    t, s = fa_norm(title or ""), fa_norm(summary or "")
    ct, cs = _distinct(FA_CORE, t), _distinct(FA_CORE, s)
    mt, ms = _distinct(FA_MID, t), _distinct(FA_MID, s)
    gt, city, kin = _distinct(FA_GEN, t), _distinct(FA_CITY, t), _distinct(FA_KIN, t)
    pw = _distinct(FA_POWERS, t)
    iran_war = bool(FA_IRAN.search(t) and FA_WAR.search(t))          # "ایران" with attack, war or explosion
    top = bool(FA_IR_TOP.search(t) and (mt or ct or pw))
    # something from the Middle East itself: a core actor or place, a regional term, an Iranian city, Iran
    region = bool(ct or (mt - _distinct(FA_MID_GENERIC, t)) or city or FA_IRAN.search(t) or cs
                  or FA_IRAN.search(s[:300]))
    score = 4 * len(ct) + 2 * len(mt) + len(gt) + len(city) + 2.5 * len(cs - ct) + 1 * len(ms - mt) + \
        (2 * len(pw) if region else 0)
    ok = bool(ct) or len(mt) >= 2 or bool(mt and (gt or city)) or bool(city and kin) or iran_war or top \
        or (score >= 6 and bool(ct | mt | cs)) or bool(pw and region)
    if ok and pw and not region and not top:
        ok = False                       # Russia, China or Europe with nothing from the Middle East
    if ok and not ct and FA_FOREIGN.search(t) and not FA_IRAN.search(t):
        ok = False                       # e.g. drone attacks in the Black Sea, riots in France
    if ok and (FA_NOISE.search(t) or FA_SPORT.search(t) or FA_SPORT.search(s[:300])) and not FA_HARD.search(t):
        ok = False                       # football, weather, a heart attack… ("حمله" alone is no reason to keep it)
    if ok and (FA_WEATHER.search(t) or FA_WEATHER_LEAD.search(s[:250])) and not FA_HARD.search(t):
        ok = False                       # weather: storms, wind and waves, rain
    if ok and ukraine_war(title, summary, "fa"):
        ok = False                       # the Russia-Ukraine war
    if not ok and internet("fa", title, summary):
        ok = True                        # Iran's internet cut, throttled or restored
    return round(score, 1), ok


# press reviews and other roundups: the text runs through several unrelated stories ("Next: … Also: … Finally …"),
# so one line about Iran in it doesn't make the episode Iran news; such an item is judged by its headline alone
_ROUNDUP_URL = re.compile(r"/press-reviews?/|press-review-|/newsletters?/", re.I)
_ROUNDUP_MARK = re.compile(r"\b(?:next|also|finally|plus|elsewhere|meanwhile)\b\s*:", re.I)
_ROUNDUP_PAPERS = re.compile(r"\b(?:papers|newspapers|front pages|editorials|columnists)\b.{0,40}?\b(?:react\w*|weigh in"
                             r"|lead with|focus on|dominat\w*)", re.I)
FA_ROUNDUP = fa_rx(["مرور مطبوعات", "صفحه نخست روزنامه", "صفحه اول روزنامه", "روزنامه های امروز", "تیتر روزنامه",
                    "گزیده روزنامه", "نگاهی به روزنامه"])


def roundup(item):
    """A press review or digest whose text covers several unrelated stories."""
    if _ROUNDUP_URL.search(item.get("u") or ""):
        return True
    if item.get("lang") == "fa":
        return bool(FA_ROUNDUP.search(fa_norm(item.get("ti", ""))))
    s = (item.get("su") or "")[:600]
    return len(_ROUNDUP_MARK.findall(s)) >= 2 or bool(_ROUNDUP_PAPERS.search(s[:300]))


def is_relevant(item):
    if roundup(item):
        item = dict(item, su="")                       # a roundup counts by its headline only
    if item.get("lang") == "fa":
        sc, ok = relevance_fa(item.get("ti", ""), item.get("su", ""))
        if ok and _noecon(item.get("s")) and not internet("fa", item.get("ti", ""), item.get("su", "")):
            t = fa_norm(item.get("ti", ""))
            if FA_ECON.search(t) and not FA_MILPOL.search(t):
                ok = False                                  # market news from a mixed Telegram channel
            elif not FA_MILPOL.search(t + " " + fa_norm(item.get("su", ""))[:300]):
                ok = False                                  # nothing political or military in it
        return sc, ok
    return relevance_en(item.get("ti", ""), item.get("su", ""))


def _noecon(sid):
    from .sources import BY_ID
    return bool(BY_ID.get(sid, {}).get("noecon"))


if __name__ == "__main__":
    tests = [
        ("US strikes Iranian drone sites near Bandar Abbas", ""),
        ("Iran beat Japan in World Cup qualifier", "Tehran fans celebrate"),
        ("Saudi Arabia hosts tourism expo", "Riyadh"),
        ("Trump says talks with Tehran could resume next week", ""),
        ("Oil prices rise as tanker traffic slows in the Strait of Hormuz", ""),
        ("Stocks rally on Wall Street", "Tech shares led gains"),
        ("Qatar mediates between Washington and Tehran", ""),
    ]
    for t, s in tests:
        print(relevance_en(t, s), t)
    for t in ["عراقچی با وزیر خارجه عمان دیدار کرد", "قیمت دلار امروز", "رزمایش پدافند هوایی در اصفهان",
              "پیروزی تیم ملی فوتبال ایران", "ترامپ: ایران باید پای میز مذاکره بیاید"]:
        print(relevance_fa(t, ""), t)
