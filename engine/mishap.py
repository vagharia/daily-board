"""Accidents and natural disasters, and events across the border that name Iran only as a place.

- `mishap`: people killed or hurt by an accident or by nature (a crash, a collision, a train off its rails, a boat
  capsized, a mine collapse, a fire at a hospital or a market, gas poisoning, an earthquake, a flood, a landslide, a
  storm): never news of the war. A yellow story, never "military", whatever the toll. Anything with a word of the
  war, a plane or a helicopter, a ship, a refinery, a base or an unexplained cause is left as it is.
- `border_only`: a headline about a neighbouring country where Iran is only the place it is near ("9 killed in
  highway collision in E. Türkiye near Iran border", «… در نزدیکی مرز ایران»). 'violent' (clashes, gunmen, an
  attack: yellow) or 'other'; None when the headline names Iran or a main actor anywhere else.
"""
import re

from .lexicon import fa_rx
from .strike_sense import calm_en
from .util import fa_norm, first_sentences

I = re.I

# ------------------------------------------------------------------ English
_CAUSE_EN = re.compile(
    r"\b(earthquakes?|quakes?|tremors?|aftershocks?|floods?|flooding|flash floods?|landslides?|mudslides?|rockslides?"
    r"|avalanches?|snowstorms?|blizzards?|cyclones?|tornado\w*|heat ?waves?|heatstroke|lightning"
    r"|wildfires?|forest fires?|bush ?fires?"
    r"|coal ?mines?|mine collapse|mining (accident|disaster)|miners?"
    r"|(road|traffic|highway|head-on|car|bus|truck|minibus|vehicle|multi-vehicle|train|rail|motorway|lorry)[\s-]+"
    r"(crash|accident|collision|disaster)\w*"
    r"|(bus|buses|trucks?|cars?|vehicles?|trains?|minibus\w*|lorr(y|ies))\b[^.;:]{0,30}\b(collid\w*|crash\w*)"
    r"|collid\w*[^.;:]{0,30}\b(bus|truck|car|vehicle|train|minibus|lorry)"
    r"|(?<!by )accidents?|derail\w*|(bus|truck|car|vehicle|minibus|van|boat)s? (overturn\w*|plunge\w*|fell|falls)"
    r"|overturn\w* (bus|truck|car|vehicle|minibus|van|boat)|capsiz\w*|drown\w*|stampede\w*"
    r"|(building|bridge|roof|wall|ceiling|tunnel) collaps\w*|collaps\w* (building|bridge|roof|tunnel)"
    r"|gas (leak|poisoning)|carbon monoxide|(methanol|alcohol|food) poisoning|poisoned by (methanol|alcohol|gas)"
    r"|electrocut\w*"
    r"|(hospital|market|bazaar|hotel|school|dormitory|residential|apartment|house|home|building|mall|shop|restaurant"
    r"|clinic|wedding|factory) (fire|blaze)s?|(fire|blaze) (at|in|on|engulf\w*|gutt\w*|rips? through|swept through)"
    r" (an? |the )?(\w+ ){0,2}(hospital|market|bazaar|hotel|school|dormitory|residential|apartment|house|home"
    r"|building|mall|shop|restaurant|clinic|wedding))\b", I)
# a word of the war, an aircraft, a ship, a site of the war or a cause unknown: not an accident for us
_NOT_EN = re.compile(
    r"\b(attack\w*|strikes?|struck|air ?strikes?|drones?|missiles?|rockets?|bomb\w*|shell\w*|explosives?|ied"
    r"|landmines?|mines? (blast|explosion|explod\w*)|gunm[ae]n|gunfire|shoot\w*|shot|ambush\w*|militants?|insurgents?"
    r"|terror\w*|sabotage\w*|clash\w*|assassin\w*|war|warplanes?|military|army|soldiers?|troops|irgc|guards?"
    r"|planes?|aircraft|airliner|jets?|helicopters?|choppers?|flight|ships?|vessels?|tankers?|warships?|navy|naval"
    r"|refiner\w*|petrochemical|nuclear|bases?|ports?|depots?|ammunition|pipelines?|power (plant|station)"
    r"|israel\w*|u\.s\.?|us (army|military|forces|troops)|americans?|pentagon|suspicious|unknown|unexplained"
    r"|mysterious|elections?|electoral|midterms?|votes?|voters?|victory|wins?|won|polls?|party|parties)\b", I)

# ------------------------------------------------------------------ Persian
_CAUSE_FA = fa_rx([
    "زلزله", "زمین لرزه", "پس لرزه", "سیل$", "سیلاب", "طغیان رودخانه", "رانش زمین", "ریزش کوه", "سقوط سنگ",
    "ریزش بهمن", "زیر بهمن", "سقوط بهمن", "کولاک", "طوفان شدید", "توفان شدید", "صاعقه", "گرمازدگی", "آتش سوزی جنگل",
    "آتش سوزی مراتع", "حریق جنگل", "ریزش معدن", "حادثه معدن", "معدن زغال", "معدنچی", "معدنکار",
    "تصادف$", "تصادفات", "واژگونی خودرو", "واژگونی اتوبوس", "واژگونی مینی بوس", "واژگونی کامیون", "واژگونی تریلی",
    "واژگونی سواری", "واژگونی ون", "خودرو واژگون", "اتوبوس واژگون", "حادثه رانندگی", "سانحه رانندگی", "برخورد دو", "برخورد اتوبوس", "برخورد کامیون",
    "برخورد تریلی", "برخورد خودرو", "برخورد سواری", "برخورد قطار", "خروج قطار", "از ریل خارج", "غرق شد", "غرق شدن",
    "غرق شدند", "غریق", "واژگونی قایق", "ریزش ساختمان", "ریزش سقف", "ریزش دیوار", "فروریختن ساختمان",
    "فرو ریختن ساختمان", "ریزش پل", "ریزش تونل", "گازگرفتگی", "مسمومیت", "متانول", "مشروبات الکلی", "برق گرفتگی",
    "حادثه کار", "حوادث کار",
])
_FIRE_FA = fa_rx(["آتش سوزی", "حریق", "آتش گرفت"])
_FIRE_PLACE_FA = fa_rx(["بیمارستان", "بازار", "هتل", "مدرسه", "خوابگاه", "مسکونی", "آپارتمان", "منزل", "ساختمان",
                        "پاساژ", "مغازه", "رستوران", "درمانگاه", "مجتمع تجاری", "جنگل", "مراتع", "عروسی", "کارخانه"])
_NOT_FA = fa_rx([
    "حمله", "حملات", "پهپاد", "موشک", "بمب", "ترور", "اصابت", "شلیک", "پدافند", "جنگنده", "تیراندازی", "مسلح",
    "انتحاری", "خرابکار", "تروریست", "درگیری", "جنگ$", "مین$", "انفجار مین", "پالایشگاه", "پتروشیمی", "نیروگاه",
    "پادگان", "پایگاه", "سپاه", "ارتش", "نظامی", "هسته ای", "بندر", "اسکله", "کشتی", "نفتکش", "ناو$", "خط لوله",
    "مهمات", "اسرائیل", "آمریکا", "صهیونیست", "هواپیما", "بالگرد", "هلیکوپتر", "پرواز", "مشکوک", "نامعلوم",
    "ناشناخته",
])
_BLAST_FA = fa_rx(["انفجار", "منفجر"])
# an explosion in a coal mine (methane) is still a mine accident
_MINE_BLAST_FA = fa_rx(["معدن زغال", "متان"])
_BLAST_EN = re.compile(r"\b(explo\w+|blasts?)\b", I)
_MINE_BLAST_EN = re.compile(r"\b(coal ?mine|methane|firedamp)\b", I)


def mishap(lang, t, s=""):
    """An accident or a natural disaster (headline, and the first sentence for what is not war)."""
    if lang == "fa":
        t = fa_norm(t or "")
        lead = t + " " + fa_norm(first_sentences(s or "", 200))
        cause = _CAUSE_FA.search(t) or (_FIRE_FA.search(t) and _FIRE_PLACE_FA.search(lead))
        if not cause or _NOT_FA.search(lead):
            return False
        return not _BLAST_FA.search(lead) or bool(_MINE_BLAST_FA.search(lead))
    t = calm_en(t or "")                 # "earthquake strikes near Bushehr": the quake's verb, not an attack
    lead = t + " " + calm_en(first_sentences(s or "", 200))
    if not _CAUSE_EN.search(t) or _NOT_EN.search(lead):
        return False
    return not _BLAST_EN.search(lead) or bool(_MINE_BLAST_EN.search(lead))


# ------------------------------------------------------------------ across the border
_NEIGH_EN = (r"(?:turk\w*|t[uü]rkiye|pakistan\w*|iraq\w*|afghan\w*|azerbaijan\w*|azeri|armenia\w*|turkmen\w*"
             r"|kurdistan region)")
_BORDER_EN = re.compile(
    r"\b(?:near|close to|along|on|at|across|by|off)\s+(?:the\s+)?(?:iran|iranian)(?:['’]s)?\s+(?:border|frontier)s?\b"
    r"|\biran(?:ian)?[\s-]+" + _NEIGH_EN + r"\s+(?:border|frontier)s?\b"
    r"|\b" + _NEIGH_EN + r"[\s-]+iran(?:ian)?\s+(?:border|frontier)s?\b"
    r"|\b(?:border|frontier)\s+with\s+iran\b", I)
_PLACE_EN = re.compile(r"\b(" + _NEIGH_EN[3:-1] + r"|balochistan|baluchistan|quetta|herat|nimroz|kandahar|van|hakkari"
                       r"|agri|ağrı|dogubayazit|doğubayazıt|nakhchivan|baku|yerevan|basra|sulaymaniyah|erbil|diyala"
                       r"|kermanshah)\b", I)
_IRAN_EN = re.compile(r"\b(iran\w*|tehran|irgc|revolutionary guards?|khamenei|israel\w*|idf|u\.s\.?|united states"
                      r"|america\w*|pentagon|centcom|trump|hormuz|persian gulf)\b", I)
_VIOLENT_EN = re.compile(r"\b(attack\w*|strikes?|struck|air ?strikes?|drones?|missiles?|rockets?|bomb\w*|shell\w*"
                         r"|explo\w+|blasts?|ied|gunm[ae]n|gunfire|shoot\w*|shot|ambush\w*|militants?|insurgents?"
                         r"|rebels?|terror\w*|clash\w*|cross-border fire|exchange of fire|fire (at|on)|fighters|fighting|firefight|raid\w*|separatists?|baloch|baluch|pkk|pjak"
                         r"|jaish|smugglers?)\b", I)

_NEIGH_FA = ["ترکیه", "پاکستان", "عراق", "افغانستان", "جمهوری آذربایجان", "ارمنستان", "ترکمنستان", "اقلیم کردستان"]
_NEIGH_FA_RX = "(?:" + "|".join(fa_norm(x).replace(" ", r"\s+") for x in _NEIGH_FA) + ")"
_BORDER_FA = re.compile(
    r"(?:در\s+)?(?:نزدیک(?:ی)?|حوالی|کنار|نزدیک\s+به|در\s+امتداد|در)\s+مرز(?:های|ها)?\s+(?:مشترک\s+)?(?:با\s+)?ایران"
    r"|مرز(?:های|ها)?\s+(?:مشترک\s+)?ایران\s+(?:و|با)\s+" + _NEIGH_FA_RX +
    r"|مرز(?:های|ها)?\s+(?:مشترک\s+)?" + _NEIGH_FA_RX + r"\s+(?:و|با)\s+ایران"
    r"|مرز(?:های|ها)?\s+(?:مشترک\s+)?با\s+ایران")
_PLACE_FA = fa_rx(_NEIGH_FA + ["بلوچستان پاکستان", "کویته", "هرات", "نیمروز", "قندهار", "نخجوان", "باکو", "ایروان",
                               "بصره", "سلیمانیه", "اربیل", "دیاله", "وان$", "هکاری"])
_IRAN_FA = fa_rx(["ایران", "تهران", "جمهوری اسلامی", "سپاه", "خامنه ای", "اسرائیل", "صهیونیست", "آمریکا", "امریکا",
                  "ترامپ", "سنتکام", "هرمز$", "خلیج فارس", "مرزبان", "مرزبانی", "هنگ مرزی"])
_VIOLENT_FA = fa_rx(["حمله", "حملات", "پهپاد", "موشک", "بمب", "ترور", "اصابت", "شلیک", "بمباران", "انفجار",
                     "تیراندازی", "مسلح", "شبه نظامی", "شورشی", "تروریست", "درگیری", "کمین", "انتحاری", "جیش",
                     "پ ک ک", "پژاک", "قاچاقچی"])


def border_only(lang, t):
    """'violent' or 'other' when the headline is about a neighbouring country and names Iran only as the border the
    place is near; None otherwise."""
    if lang == "fa":
        t = fa_norm(t or "")
        m = _BORDER_FA.search(t)
        if not m:
            return None
        rest = t[:m.start()] + " " + t[m.end():]
        if _IRAN_FA.search(rest) or not (_PLACE_FA.search(t)):
            return None
        return "violent" if _VIOLENT_FA.search(t) else "other"
    t = t or ""
    m = _BORDER_EN.search(t)
    if not m:
        return None
    rest = t[:m.start()] + " " + t[m.end():]
    if _IRAN_EN.search(rest) or not _PLACE_EN.search(t):
        return None
    return "violent" if _VIOLENT_EN.search(t) else "other"


_HURT_EN = re.compile(r"\b(kill\w*|dead|deaths?|died|dies|wounded|injur\w*|hurt|casualt\w+|toll|fatalit\w+|missing"
                      r"|bodies)\b", I)
_HURT_FA = fa_rx(["کشته", "جان باخت", "جان خود را از دست", "مصدوم", "زخمی", "مجروح", "فوت", "مفقود", "جسد",
                  "قربانی", "تلفات", "حادثه", "سانحه"])


def border_drop(lang, t, s=""):
    """Across the border, nobody fighting: an accident, a disaster or a toll near Iran's border is not our news."""
    if border_only(lang, t) != "other":
        return False
    if mishap(lang, t, s):
        return True
    tt = fa_norm(t or "") if lang == "fa" else (t or "")
    return bool((_HURT_FA if lang == "fa" else _HURT_EN).search(tt))


# ------------------------------------------------------------------ roads
# road traffic is never news of the war: a crash, a road toll ("78,500 road deaths"), road or car safety rules. Such a
# report is dropped from the bulletin, in Iran or abroad, unless it has a word of the war in it.
_ROADNEWS_EN = re.compile(
    r"\b(road|traffic|highway|motorway)[\s-]+(deaths?|fatalit\w+|toll|safety|accidents?|crash\w*|collisions?|carnage)"
    r"|\b(car|vehicle|automobile|auto)[\s-]+safety\b|\bsafety (standards?|rules|regulations) (for|on) (cars|vehicles)"
    r"|\bdrivers? (killed|died)\b|\bpedestrians? (killed|died)\b"
    r"|\b(drivers?|motorists?)\b[^.;:]{0,15}\blos(es|t|ing) control\b", I)
_ROADNEWS_FA = fa_rx(["کشته در جاده", "کشته جاده", "کشتگان جاده", "تلفات جاده", "تصادفات جاده", "حوادث جاده",
                      "حوادث رانندگی", "سوانح رانندگی", "ایمنی خودرو", "استاندارد ایمنی خودرو",
                      "استانداردهای ایمنی خودرو", "قوانین ایمنی خودرو", "ایمنی جاده", "پلیس راه", "راهور", "کنترل خودرو", "کنترل کامیون",
                      "کنترل اتوبوس", "کنترل تریلی", "کنترل سواری"])
_ROAD_WAR_EN = re.compile(r"\b(attack\w*|strikes?|struck|air ?strikes?|drones?|missiles?|rockets?|bomb\w*|shell\w*"
                          r"|explosives?|ied|landmines?|gunm[ae]n|gunfire|shoot\w*|shot|ambush\w*|militants?"
                          r"|insurgents?|terror\w*|sabotage\w*|military|army|soldiers?|troops|irgc|convoy|israel\w*"
                          r"|u\.s\.?|pentagon|war)\b", I)


def road(lang, t, s=""):
    """A report about road traffic: a crash, a road toll, road or car safety (headline, first sentence for war)."""
    from .classify import _road
    if lang == "fa":
        tt = fa_norm(t or "")
        lead = tt + " " + fa_norm(first_sentences(s or "", 200))
        if _NOT_FA.search(lead) and not _ROADNEWS_FA.search(tt):
            return False
        hit = _ROADNEWS_FA.search(tt) or _road("fa", tt)
        return bool(hit) and not fa_rx(["حمله", "پهپاد", "موشک", "بمب", "ترور", "اصابت", "شلیک", "انفجار",
                                        "تیراندازی", "مسلح", "تروریست", "کمین", "سپاه", "ارتش", "نظامی", "اسرائیل",
                                        "آمریکا", "جنگ$"]).search(lead)
    tt = t or ""
    lead = tt + " " + first_sentences(s or "", 200)
    hit = _ROADNEWS_EN.search(tt) or _road("en", tt) or (mishap("en", tt, s) and re.search(
        r"\b(road|traffic|highway|motorway|bus|buses|truck|lorry|cars?|vehicles?|minibus\w*|van)\b", tt, I))
    return bool(hit) and not _ROAD_WAR_EN.search(lead)


# ------------------------------------------------------------------ nature far away
# a flood, a storm, an earthquake, a wildfire outside Iran and the Middle East (Colorado, Japan, Europe): not our
# news, dropped even when it names America ("floods destroy roads in Colorado and Arizona")
_NATURE_EN = re.compile(
    r"\b(earthquakes?|quakes?|tremors?|aftershocks?|floods?|flooding|flash floods?|landslides?|mudslides?|avalanches?"
    r"|snowstorms?|blizzards?|cyclones?|hurricanes?|typhoons?|tornado\w*|tsunamis?|volcan\w*|eruptions?|heat ?waves?"
    r"|droughts?|wildfires?|forest fires?|bush ?fires?|(snow|rain|tropical|winter|severe|dust|sand|ice|wind) ?storms?"
    r"|torrential rains?|heavy rains?)\b", I)
_NATURE_FA = fa_rx(["زلزله", "زمین لرزه", "سیل$", "سیلاب", "طغیان رودخانه", "رانش زمین", "بهمن گرفت",
                    "ریزش بهمن", "کولاک", "طوفان شدید", "توفان شدید", "گردباد", "تندباد", "هاریکن", "تایفون", "سونامی",
                    "آتشفشان", "فوران", "موج گرما", "خشکسالی", "آتش سوزی جنگل", "آتش سوزی جنگل ها", "باران شدید",
                    "بارش شدید", "باران های سیل آسا", "زیر آب رفت", "آبگرفتگی", "آب گرفتگی"])
_REGION_EN = re.compile(
    r"\b(iran\w*|tehran|persian gulf|gulf of oman|hormuz|middle east|mideast|israel\w*|gaza|west bank|lebanon|lebanese"
    r"|syria\w*|iraq\w*|jordan\w*|saudi\w*|yemen\w*|oman\w*|uae|emirat\w*|dubai|abu dhabi|qatar\w*|bahrain\w*"
    r"|kuwait\w*|egypt\w*|red sea|gulf|turk\w*|t[uü]rkiye|pakistan\w*|afghan\w*|azerbaijan\w*|armenia\w*|turkmen\w*"
    r"|isfahan|shiraz|mashhad|tabriz|ahvaz|bushehr|bandar abbas|kerman\w*|sistan|khuzestan|hormozgan|mazandaran"
    r"|gilan|golestan)\b", I)
_REGION_FA = fa_rx(["ایران", "تهران", "خلیج فارس", "دریای عمان", "هرمز$", "هرمزگان", "خاورمیانه", "غرب آسیا",
                    "اسرائیل", "فلسطین", "غزه", "لبنان", "سوریه", "عراق", "اردن", "عربستان", "یمن", "عمان",
                    "امارات", "دبی", "قطر", "بحرین", "کویت", "مصر", "دریای سرخ", "ترکیه", "پاکستان", "افغانستان",
                    "آذربایجان", "ارمنستان", "ترکمنستان", "استان", "شهرستان", "روستا", "اصفهان", "شیراز", "مشهد",
                    "تبریز", "اهواز", "بوشهر", "بندرعباس", "کرمان", "سیستان", "بلوچستان", "خوزستان", "مازندران",
                    "گیلان", "گلستان", "لرستان", "کردستان", "خراسان", "فارس$", "یزد", "سمنان", "زنجان", "قزوین",
                    "اردبیل", "ایلام", "همدان", "مرکزی$", "البرز", "کهگیلویه", "چهارمحال", "هلال احمر"])


_FAR_WAR_FA = fa_rx(["حمله", "پهپاد", "موشک", "بمب", "ترور", "اصابت", "شلیک", "انفجار", "تیراندازی", "مسلح",
                     "تروریست", "سپاه", "ارتش", "نظامی", "ناو$", "ناوگان", "پایگاه", "اسرائیل", "جنگ$", "تحریم",
                     "انتخابات", "انتخاباتی", "حزب", "کنگره", "بورس", "دلار", "بازار"])
_FAR_WAR_EN = re.compile(r"\b(carriers?|warships?|navy|naval|bases?|operations?|nuclear|sanction\w*|desert storm"
                         r"|elections?|electoral|midterms?|votes?|voters?|congress|senate|democrats?|republicans?|gop"
                         r"|party|polls?|markets?|stocks?|shares)\b", I)


def far_nature(lang, t, s=""):
    """A natural disaster with no place of Iran or the Middle East in the headline or the first sentence."""
    if lang == "fa":
        tt = fa_norm(t or "")
        lead = tt + " " + fa_norm(first_sentences(s or "", 200))
        return bool(_NATURE_FA.search(tt)) and not _REGION_FA.search(lead) and not _FAR_WAR_FA.search(lead)
    tt = t or ""
    lead = tt + " " + first_sentences(s or "", 200)
    return bool(_NATURE_EN.search(tt)) and not _REGION_EN.search(lead) and not _ROAD_WAR_EN.search(lead) \
        and not _FAR_WAR_EN.search(lead)


# ------------------------------------------------------------------ flights stopped by nature
# Flights halted or an airport shut by an earthquake, a storm, fog or snow ("earthquake briefly halts flights at
# Israel's Ramon Airport", «تعلیق پروازها در فرودگاه رامون پس از زمین‌لرزه»): no airspace event of the war, so no
# airspace flag and no airspace lamp. A word of the war in the headline or the first sentence leaves it as it is.
_AIR_NATURE_EN = re.compile(
    r"\b(earthquakes?|quakes?|tremors?|aftershocks?|seismic|storms?|sandstorms?|dust ?storms?|snow\w*|blizzards?"
    r"|fog|floods?|flooding|volcan\w*|ash cloud|heavy rain|bad weather|weather)\b", I)
_AIR_WAR_EN = re.compile(
    r"\b(attack\w*|strikes?|struck|air ?strikes?|drones?|uavs?|missiles?|rockets?|bomb\w*|intercept\w*|shell\w*"
    r"|war|warplanes?|military|army|troops|irgc|hezbollah|houthis?|hostile|threat\w*|security|escalat\w*"
    r"|retaliat\w*|gps|jamming|spoof\w*|explo\w+|blasts?)\b", I)
_AIR_NATURE_FA = fa_rx(["زلزله", "زمین لرزه", "پس لرزه", "لرزه", "طوفان", "توفان", "گرد و غبار", "گردوغبار",
                        "ریزگرد", "مه گرفتگی", "مه غلیظ", "برف", "کولاک", "سیل$", "سیلاب", "آتشفشان",
                        "شرایط جوی", "وضعیت جوی", "آب و هوا", "بارندگی"])
_AIR_WAR_FA = fa_rx(["حمله", "حملات", "پهپاد", "موشک", "بمب", "رهگیری", "پدافند", "اصابت", "شلیک", "جنگ$",
                     "جنگنده", "نظامی", "سپاه", "ارتش", "حزب الله", "حوثی", "انصارالله", "تهدید", "امنیتی",
                     "تنش", "انتقام", "انفجار", "جی پی اس", "اختلال"])


def air_nature(lang, t, s=""):
    """Flights or an airport stopped by an earthquake or the weather, with no word of the war."""
    if lang == "fa":
        tt = fa_norm(t or "")
        lead = tt + " " + fa_norm(first_sentences(s or "", 200))
        return bool(_AIR_NATURE_FA.search(lead)) and not _AIR_WAR_FA.search(lead)
    tt = t or ""
    lead = tt + " " + first_sentences(s or "", 200)
    # "earthquake strikes Gulf of Aqaba", "storm hit": the quake's verb, not an attack (strike_sense.py)
    return bool(_AIR_NATURE_EN.search(lead)) and not _AIR_WAR_EN.search(calm_en(lead))
