"""Group reports of the same event into one story ("cluster")."""
import re

from . import config, deploy, evac, pullback, vessel, witness
from .classify import cluster_severity, tier, trump_level
from .classify_fa import _ANY, _B, R
from .lexicon import COUNTRIES_RX, PEOPLE, PEOPLE_RX, PLACES, match_keys
from .relevance import FA_CITY, FA_IRAN
from .sources import BY_ID
from . import fronts
from .fronts import MINOR_CAP, SECONDARY_CAP
from .sport import CAP as SPORT_CAP
from .strike_sense import calm_en
from .util import fa_norm, sha

STOP = set("""
a an the and or of to in on at for from by with as is are was were be been being it its this that these those
after amid over under into about against between during before since until while new latest report reports
reported reportedly says said say saying tells told could would should may might will can just also more most
than then there their they them his her he she we our you your who what when where why how which not no yes
amid amidst near via per vs live update updates breaking news video watch photos analysis opinion explainer
day days week weeks month months year years today tonight yesterday tomorrow first second third one two three
up down out off back amid amidst within without across around official officials source sources state media
middle east region regional another again further yet still now more have has had same different past
strait but all any some such very much many both each other only even own its also amid among whether exclusive scoop
""".split())

# "Iran war live: …", "War in the Middle East: …", "Middle East crisis | …" — the prefix says nothing about the event
LIVE_PREFIX = re.compile(r"^\s*(?:[^:|–—]{0,40}\b(?:live|updates?|crisis|war|conflict|latest)\b[^:|–—]{0,20})\s*[:|–—]\s+",
                         re.I)


def strip_live(title):
    """A live page's label taken off its headline ("Iran war latest: Trump says …"), but only when a whole headline
    follows: "US fires top army general in latest ouster: media" is a headline, not a label."""
    m = LIVE_PREFIX.match(title or "")
    if m and len(title[m.end():].split()) >= 4:
        return title[m.end():]
    return title or ""

SYN = {
    "u.s": "us", "american": "us", "americans": "us", "washington": "us",
    "israeli": "israel", "israelis": "israel", "iranian": "iran", "iranians": "iran", "tehran": "iran",
    "struck": "strike", "strikes": "strike", "striking": "strike", "airstrike": "strike", "airstrikes": "strike",
    "attacks": "attack", "attacked": "attack", "attacking": "attack", "missiles": "missile", "drones": "drone",
    "tankers": "tanker", "ships": "ship", "vessels": "vessel", "talks": "talk", "negotiations": "talk",
    "warns": "warn", "warned": "warn", "warning": "warn", "threatens": "threat", "threatened": "threat",
    "threatening": "threat", "sanctions": "sanction", "sanctioned": "sanction", "killed": "kill", "kills": "kill",
    "seized": "seize", "seizes": "seize", "seizure": "seize", "hormuz's": "hormuz", "saudis": "saudi",
    "emirati": "uae", "emirates": "uae", "houthis": "houthi", "hezbollah's": "hezbollah", "gulf's": "gulf",
    # one name, several spellings in translations
    "qalibaf": "ghalibaf", "araqchi": "araghchi", "baghaie": "baghaei", "esfahan": "isfahan", "fordo": "fordow",
    "uav": "drone", "uavs": "drone", "blast": "explosion", "blasts": "explosion", "explosions": "explosion",
    "interception": "intercept", "interceptions": "intercept", "destruction": "destroy", "destroyed": "destroy",
    "destroys": "destroy",
    # one thing in several words: "minor" / "limited" / "small" strikes, "anti-aircraft" / "air defence" (tokens),
    # and "carries" with "carried" (the stemmer made them "carrie" and "carri")
    "limited": "minor", "small": "minor", "little": "minor", "partial": "minor",
    "carries": "carried",
    # a cyber attack and the fridges of the French supermarkets, told in other words ("cyber attack" is made one word
    # in tokens, as is "cooling system")
    "hack": "cyberattack", "hacks": "cyberattack", "hacked": "cyberattack", "hacking": "cyberattack",
    "hacker": "cyberattack", "hackers": "cyberattack", "cyberattacks": "cyberattack",
    "fridges": "fridge", "refrigerator": "fridge", "refrigerators": "fridge", "refrigeration": "fridge",
    "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "dozen": "12",
}

# the same thing named two ways, kept to sure equivalents (a seat of power and its country, one word's forms). They
# can only make two very close headlines match (same_story): headlines that match only thanks to them must share
# more than half their words, two of them more than a country's name or "war".
SAME = {"america": "us", "kremlin": "russia", "russian": "russia", "russians": "russia",
        "mediator": "mediate", "mediators": "mediate", "mediation": "mediate", "mediates": "mediate",
        "mediated": "mediate", "mediating": "mediate", "readiness": "ready",
        "offers": "offer", "offered": "offer", "proposal": "offer", "proposals": "offer", "propose": "offer",
        "proposes": "offer", "proposed": "offer", "french": "france", "store": "supermarket", "stores": "supermarket"}
# words too common to make two headlines the same story by themselves
_GENERIC = {"us", "iran", "israel", "russia", "uk", "france", "china", "war", "say", "new", "report"}
_SAME_PHRASES = (("white house", "us"), ("downing street", "uk"), ("élysée", "france"), ("elysee", "france"))

ENTITY = set("""iran israel us trump hormuz tanker hezbollah houthi saudi qatar oman uae iraq yemen lebanon syria
gaza netanyahu khamenei irgc centcom pentagon nuclear iaea missile drone strike navy carrier bahrain kuwait
rubio vance bessent hegseth witkoff araghchi pezeshkian russia china europe jordan egypt turkey riyadh doha
dubai baghdad beirut damascus jerusalem hebron aramco opec brent oil embassy sanaa jeddah""".split())

# Stories outside the core theatre (Iran, the Persian Gulf states, Iraq, Yemen / Red Sea, Lebanon) are kept but
# toned down, so West Bank raids or Israeli domestic politics don't outrank the Iran-US-Israel confrontation.
CORE_CTRY = {"ir", "gulf", "yemen", "iraq", "lebanon"}
CORE_GEO = {"hormuz", "persian_gulf", "gulf_oman", "tehran", "isfahan", "natanz", "fordow", "bushehr", "bandar_abbas",
            "kharg", "tabriz", "shiraz", "chabahar", "baghdad", "erbil", "ain_asad", "sanaa", "hodeidah", "red_sea",
            "bab", "riyadh", "east_sa", "doha", "bahrain", "uae", "fujairah", "oman", "kuwait", "lebanon", "baluchestan",
            "w_border", "arabian_sea"}
CORE_FLAGS = {"oil_spike", "maritime_incident", "hormuz_closure", "airspace", "nuclear_red", "internet"}
CORE_PPL = {"ir_leader", "ir_pres", "ir_fm", "ir_snsc", "irgc_cmd", "ir_army", "ghalibaf", "ir_spox", "houthi_l",
            "hzb_l", "grossi", "mbs", "sa_fm", "qa", "om", "uae"}
NONCORE_FACTOR, NONCORE_CAP = 0.6, 55.0
# a story about another war (Ukraine, Venezuela, Taiwan…) that never mentions the Middle East is market context at
# most (it can get in through oil or gold news), never an orange story
REGION_CTRY = {"ir", "il", "gulf", "yemen", "iraq", "lebanon", "syria"}
OTHER_WAR = re.compile(r"\b(ukrain\w*|kyiv|kiev|zelensk\w*|donbas+|donetsk|luhansk|crimea\w*|kursk|zaporizh\w*|kharkiv"
                       r"|odesa|odessa|venezuel\w*|caracas|maduro|taiwan\w*|sudan\w*|kashmir)\b"
                       r"|اوکراین|کی‌یف|کییف|زلنسکی|ونزوئلا|تایوان|سودان", re.I)
REGION_WORDS = re.compile(r"\b(middle east|mideast|west asia|levant|red sea|persian gulf|gulf (states|arab|countries"
                          r"|nations|region|allies)|hormuz|palestin\w*|hamas|hezbollah|houthis?|egypt\w*|suez|sinai"
                          r"|turk(ey|iye|ish)|qatar\w*|saudi\w*|emirat\w*|kuwait\w*|bahrain\w*|oman\w*|jordan\w*)\b"
                          r"|خاورمیانه|غرب آسیا|خلیج فارس|دریای سرخ|فلسطین|حماس|حزب[\s\u200c]?الله|حوثی|مصر|ترکیه"
                          r"|اردن|عربستان|امارات|قطر|کویت|بحرین|عمان", re.I)
OTHER_WAR_CAP = 40.0
CORROBORATE_BELOW = 0.75
# what only one Telegram channel (not a news organisation) reports is an unconfirmed report, labelled so: red when it
# tells of a strike as it happens (an explosion, a missile launch, fighter jets or air defence heard; channels often
# have these before the news) and sent as an alert, yellow otherwise. It counts as confirmed once a news source or a
# second channel reports the same story. Once a news source has it, the news decides the colour (a controlled
# detonation makes it yellow), and the channels' own claims no longer count beyond it; a strike the news confirms stays
# red. Explosions in Iran that officials put down to gas stay red: during the war they are likely to be assassinations.
CONFIRM_CHANNELS = 2
UNCONFIRMED_CAP = 44.0
RED_FLOOR = 70.0
STRIKE_FLAGS = {"kinetic", "maritime_incident", "hormuz_closure", "nuclear_red"}
NOT_A_STRIKE = {"denial", "controlled", "past"}
_BLAST_FA = re.compile(R("انفجار", _ANY % 35, "(?:گاز|منزل|مسکونی|ساختمان|واحد|آپارتمان|خانه|خودرو|ماشین|کپسول|لوله"
                         "|خیابان|کوچه|محله|مجتمع|برج)", "|", "(?:نشت\\s*گاز|منزل|مسکونی|ساختمان|آپارتمان|خانه|خودرو"
                         "|ماشین|کپسول)", _ANY % 25, "(?:انفجار|منفجر)"))
_BLAST_EN = re.compile(r"\b(explosions?|blasts?)\b.{0,40}\b(gas|homes?|houses?|residential|buildings?|apartments?|cars?"
                       r"|vehicles?|streets?)\b|\b(gas|residential|building|apartment|car)\b.{0,25}\b(explosions?|blasts?)\b"
                       r"|\bgas (leak|explosion|cylinder)s?\b", re.I)
# the news agency of the Islamic Republic names the country without the story being about it
_AGENCY_FA = re.compile(fa_norm("خبرگزاری جمهوری اسلامی") + "|" + fa_norm("ایرنا"))
_ABROAD_FA = re.compile(R(_B, "(?:سوریه|دمشق|حمص|حلب|لبنان|بیروت|عراق|بغداد|اربیل|یمن|صنعا|غزه|کرانه|فلسطین|اسرائیل|اسراییل"
                          "|تل\\s*آویو|حیفا|اردن|عربستان|ریاض|امارات|دبی|ابوظبی|قطر|دوحه|کویت|بحرین|منامه|مسقط|ترکیه"
                          "|استانبول|آنکارا|افغانستان|کابل|پاکستان|اوکراین|روسیه|آمریکا|امریکا|اروپا)"))
_ABROAD_EN = re.compile(r"\b(syria\w*|damascus|homs|aleppo|leban\w*|beirut|iraq\w*|baghdad|erbil|yemen\w*|sanaa|gaza"
                        r"|west bank|israel\w*|tel aviv|haifa|jordan\w*|saudi\w*|riyadh|emirat\w*|uae|dubai|abu dhabi"
                        r"|qatar\w*|doha|kuwait\w*|bahrain\w*|muscat|turk\w*|istanbul|ankara|afghan\w*|kabul"
                        r"|pakistan\w*|ukrain\w*|russia\w*)\b", re.I)
_IRAN_EN = re.compile(r"\b(iran\w*|tehran|isfahan|esfahan|tabriz|shiraz|mashhad|karaj|qom|ahvaz|ahwaz|kermanshah"
                      r"|bandar abbas|bushehr|urmia|kerman|yazd|rasht|zahedan|hamedan|arak|sanandaj|ilam|khorramabad"
                      r"|abadan|khorramshahr|chabahar|kish|qeshm)\b", re.I)
EVENT_FLAGS = {"deesc_event", "kinetic", "maritime_incident", "hormuz_closure", "airspace", "evac", "deploy", "ultimatum", "nuclear_red",
               "alert", "kinetic_threat", "pullback"}


# the same incident told in other words ("explosion of a home in Jafarabad, Kermanshah" / "building destroyed by an
# explosion in Kermanshah"): two reports of something that happened, in the same city, within the story's time window,
# about the same spot: a neighbourhood or street both name, or both an explosion of a home or building (in Tehran only
# a shared neighbourhood or street counts). A channel's claim never joins a news report this way: a different claim
# about the same spot ("targeted assassination" / "gas explosion") stays a story of its own.
_CITIES_FA = ["تهران", "تبریز", "اصفهان", "شیراز", "مشهد", "کرج", "قم", "اهواز", "بندرعباس", "بندر عباس", "بوشهر",
              "کرمانشاه", "ارومیه", "خرمشهر", "آبادان", "چابهار", "کیش", "قشم", "کرمان", "یزد", "رشت", "زاهدان",
              "همدان", "اراک", "سنندج", "ایلام", "خرم آباد", "بیروت", "دمشق", "بغداد", "اربیل", "صنعا", "حیفا",
              "تل آویو", "ریاض", "جده", "دبی", "ابوظبی", "دوحه", "منامه", "کویت"]
_CITY_FA = re.compile("|".join(_B + re.escape(fa_norm(x)).replace(r"\ ", r"\s*") + r"(?![\u0621-\u06FF])"
                               for x in _CITIES_FA))
_CITY_EN = re.compile(r"\b(tehran|tabriz|isfahan|esfahan|shiraz|mashhad|karaj|qom|ahvaz|ahwaz|bandar abbas|bushehr"
                      r"|kermanshah|urmia|khorramshahr|abadan|chabahar|kish|qeshm|kerman|yazd|rasht|zahedan|hamedan|arak"
                      r"|sanandaj|ilam|khorramabad|beirut|damascus|baghdad|erbil|sanaa|haifa|tel aviv|riyadh|jeddah"
                      r"|dubai|abu dhabi|doha|manama|kuwait city)\b", re.I)
_SPOT_FA = re.compile(R(_B, "(?:محله|خیابان|کوچه|بلوار|میدان|شهرک|بزرگراه)\\s+(?:شهید\\s+)?([\u0621-\u06FF]{3,})"))
_SPOT_EN = re.compile(r"\b([A-Z][a-z]{3,})\s+(?:neighbo(?:u)?rhood|district|street|avenue|square|boulevard)\b"
                      r"|\b(?:neighbo(?:u)?rhood|district|street|avenue|square) of ([A-Z][a-z]{3,})\b")


def place(m):
    """(cities, spots, building blast) of a report: read in its headline and the start of its text."""
    if m.get("lang") == "fa":
        t, s = fa_norm(m.get("ti") or ""), fa_norm(m.get("su") or "")[:250]
        cities = {fa_norm(x).replace(" ", "") for x in _CITY_FA.findall(t + " " + s)}
        spots = set(_SPOT_FA.findall(t + " " + s))
        return cities, spots, bool(_BLAST_FA.search(t))
    t = m.get("en_ti") or m.get("ti") or ""
    s = (m.get("en_su") or m.get("su") or "")[:250]
    cities = {x.lower() for x in _CITY_EN.findall(t + " " + s)}
    spots = {x.lower() for pair in _SPOT_EN.findall(t + " " + s) for x in pair if x}
    return cities, spots, bool(_BLAST_EN.search(t))


def same_spot(a, b):
    """Features of two reports of something that happened: the same incident at the same spot (see above)."""
    if a["cls"] not in PHYSICAL or b["cls"] not in PHYSICAL or a["chan"] != b["chan"]:
        return False
    common = a["cities"] & b["cities"]
    if not common:
        return False
    if a["spots"] & b["spots"]:
        return True
    tehran = {fa_norm("تهران"), "tehran"}
    return a["blast"] and b["blast"] and not common <= tehran


# what kind of unconfirmed report a channel post is: it relays a named outlet ("cited": awaiting that outlet), it quotes
# a person or a body without saying where the words come from ("quote": source not stated), or it tells of something
# that happened ("event": unconfirmed report)
_QUOTE_FA = re.compile(r"^[^:：]{2,45}[:：]" + "|" + R(_B, "(?:گفت|گفته\\s*است|اعلام\\s*کرد|تاکید\\s*کرد|هشدار\\s*داد"
                       "|افزود|اظهار\\s*داشت|مدعی\\s*شد|خاطرنشان\\s*کرد|تصریح\\s*کرد|نوشت)(?![\u0621-\u06FF])"))
_QUOTE_EN = re.compile(r"^[^:]{2,45}:|\b(says|said|told|tells|warns|warned|claims|claimed|stated)\b", re.I)


def unconf_kind(ms):
    from .citation import outlet_named             # citation builds on this module
    if any(outlet_named(m) for m in ms):
        return "cited"
    if any(strike(m) for m in ms):
        return "event"
    for m in ms:
        t = fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else (m.get("ti") or "")
        if (_QUOTE_FA if m.get("lang") == "fa" else _QUOTE_EN).search(t):
            return "quote"
    if all(_analysis_post(m) for m in ms):
        return "analysis"
    return "event"


# a channel's analysis, summary or guesswork, not a report of something that happened: an analysis, an opinion or a
# guess as the classifier reads it, or a piece about a market (oil, gold, the dollar, shares) and its worries
_EVENT_FLAGS = {"kinetic", "maritime_incident", "hormuz_closure", "airspace", "evac", "pullback", "deploy", "ultimatum",
                "nuclear_red", "witness", "internet", "cable_cut"}
_MARKET_FA = re.compile(fa_norm("قیمت نفت|نفت خام|برنت|طلا|دلار|بورس|سهام|بازار|معامله گران|معامله‌گران|سرمایه گذاران"
                                "|ریسک|پوشش ریسک"))
_MARKET_EN = re.compile(r"\b(oil prices?|crude|brent|gold|dollar|stocks?|shares|markets?|traders|investors|risk)\b", re.I)


_TELLS_FA = re.compile(fa_norm("به گزارش|به نقل از|گزارش داد|اعلام کرد|نظرسنجی|یادداشت اطلاعاتی|آژانس|شورای"))
_TELLS_EN = re.compile(r"\b(reports?|reported|according to|citing|poll|polls|survey|announced|said)\b", re.I)


def _analysis_post(m):
    """Not when it relays someone (an outlet, an agency, a poll: those are reports to confirm)."""
    fl = set(m.get("flags") or [])
    if fl & _EVENT_FLAGS:
        return False
    fa = m.get("lang") == "fa"
    t = fa_norm(m.get("ti") or "") if fa else (m.get("en_ti") or m.get("ti") or "")
    if (_TELLS_FA if fa else _TELLS_EN).search(t):
        return False
    if fl & {"analysis", "opinion"}:
        return True
    return bool((_MARKET_FA if fa else _MARKET_EN).search(t))


def channel(m):
    """The report comes from a Telegram channel, not from a news organisation."""
    return BY_ID.get(m.get("s"), {}).get("kind") == "tg"


def strike(m):
    """The report tells of a strike or an explosion as it happens (in its headline), not of a threat, a plan, a
    denial or a controlled detonation."""
    fl = set(m.get("flags", []))
    return bool(fl & STRIKE_FLAGS) and not fl & NOT_A_STRIKE and m.get("sev", 0) >= RED_FLOOR


def blast(m):
    """An explosion in a home, a building, a car or a street in Iran: the kind officials put down to gas. The place
    is read in the headline, or in the start of the text when the headline names no country or city."""
    if "kinetic" not in m.get("flags", []) or set(m.get("flags", [])) & NOT_A_STRIKE:
        return False
    if m.get("lang") == "fa":
        t = fa_norm(m.get("ti", ""))
        s = _AGENCY_FA.sub(" ", fa_norm(m.get("su") or "")[:300])
        if not _BLAST_FA.search(t):
            return False
        if FA_CITY.search(t) or FA_IRAN.search(t):
            return True
        return not _ABROAD_FA.search(t) and bool(FA_CITY.search(s) or FA_IRAN.search(s))
    t = m.get("en_ti") or m.get("ti", "")
    s = (m.get("en_su") or m.get("su") or "")[:300]
    if not _BLAST_EN.search(t):
        return False
    return bool(_IRAN_EN.search(t) or (not _ABROAD_EN.search(t) and _IRAN_EN.search(s)))


def is_core(c):
    return bool(set(c.get("ctry", [])) & CORE_CTRY or set(c.get("geo", [])) & CORE_GEO
                or set(c.get("flags", [])) & CORE_FLAGS or set(c.get("ppl", [])) & CORE_PPL)


def other_war(m):
    """A report about another war with no Middle East reference at all."""
    if set(m.get("ctry", [])) & REGION_CTRY or m.get("geo"):
        return False
    text = " ".join(m.get(k) or "" for k in ("ti", "su", "en_ti", "en_su"))
    return bool(OTHER_WAR.search(text)) and not REGION_WORDS.search(text)


def _stem(w):
    if len(w) > 6 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 5 and w.endswith("ed") and not w.endswith("eed"):
        return w[:-2]
    return w


def tokens(title: str, same=False):
    t = calm_en(strip_live(title)).lower()      # an earthquake that "strikes" shares no strike word (strike_sense.py)
    t = re.sub(r"(\d),(\d{3})\b", r"\1\2", t)               # 1,500 -> 1500
    t = re.sub(r"[’'`]s\b", "", t)
    t = t.replace("u.s.", "us ").replace("u.k.", "uk ").replace("united states", "us").replace("united nations", "un")
    if same:
        for a, b in _SAME_PHRASES:
            t = t.replace(a, b)
    t = re.sub(r"\banti[- ]?aircraft\b|\bair[- ]defen[cs]es?\b", " airdefense ", t)
    t = re.sub(r"\bcyber[\s-]*attack", "cyberattack", t)
    t = re.sub(r"\bcooling[\s-]+systems?\b", "fridge", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    out = set()
    for w in t.split():
        w = SYN.get(w, w)
        if same:
            w = SAME.get(w, w)
        if w in STOP or (len(w) < 3 and not w.isdigit() and w not in ("us", "uk", "un", "eu")):
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        w = SYN.get(w, _stem(w))
        if same:
            w = SAME.get(w, w)
        if w in STOP:
            continue
        out.add(w)
    return out


# --- strict matching. A report joins a story only if its headline is very close to one of the story's reports
# AND they agree on: what happened (the kind of event), where (places, else countries), when (a time window from
# the story's first report; named weekdays), who said it and who reported it (for statements), and the figures.
CLASS_ORDER = [("M", {"maritime_incident", "hormuz_closure"}), ("K", {"kinetic"}), ("A", {"airspace"}),
               ("V", {"evac", "pullback"}), ("D", {"deploy"}), ("U", {"ultimatum"}), ("N", {"nuclear_red"}), ("S", {"sanctions"}),
               ("T", {"threat", "retaliation", "kinetic_threat", "talks_fail"})]
PHYSICAL = {"M", "K", "A", "V", "D"}            # something happened somewhere; anything else is said or decided
# the classifier can tag one outlet's report of an attack at sea as maritime and another's as kinetic, so these
# kinds count as the same "what"; "O" means the kind wasn't recognised, which needs even closer headlines
KIND = {"M": "attack", "K": "attack", "A": "attack", "V": "evac", "D": "deploy", "U": "threat", "T": "threat",
        "N": "nuclear", "S": "sanctions", "O": None}
WINDOW = {"event": 4 * 3600, "other": 10 * 3600}
# a named person's words about an event ("Trump says US carried out 'minor' strikes") are retold for hours: a report
# quoting the same person as one of the story's reports may join an event story this long after its first report
SPEECH_WINDOW = 10 * 3600
# places within a wider one: a report of Qeshm and one of the Strait of Hormuz don't name different places
REGION = {"qeshm": "hormuz", "abu_musa": "hormuz"}


def _region(geo):
    return set(geo) | {REGION[g] for g in geo if g in REGION}


# ------------------------------------------------------------------ the same strike, told in other words
# Two news reports (never a Telegram channel or citizen reports) are one story, though their headlines share few
# words ("US has conducted defensive strikes in Hormuz" / "Report: U.S. struck Iran's Qeshm Island overnight"), when
# all of these hold: both tell of an attack (not denied, past, a threat or analysis); both name who struck, the
# same; both name the same city or island it hit (not Tehran, where several strikes a day are likely, nor a country);
# where both name what was hit (a port, a base, an airport, an oil site, air defence or radar, boats), the same; the
# days they give don't differ; neither says it is a new or another strike ("again", "second", «دوباره»,
# «موج جدید»); and the report comes within twelve hours of the story's first report.
STRIKE_WINDOW = 12 * 3600
_ATTACKERS = {"us": r"u\.?s\.?|united states|america\w*|pentagon|centcom|washington|trump",
              "il": r"israel\w*|idf",
              "ir": r"iran\w*|irgc|revolutionary guards?|tehran"}
_HIT = r"(?:strikes?|struck|attacks?|attacked|bomb\w*|hits?|raids?|carries out|carried out|conducts?|conducted|targets?|targeted)"
_ATT_RX = {k: re.compile(r"\b(?:" + v + r")\b(?:'s)?(?:\s+[\w'‘’-]+){0,4}?\s+" + _HIT + r"\b"
                         r"|\b(?:strikes?|attacks?|raids?|bombing)\s+(?:by|from)\s+(?:the\s+)?(?:" + v + r")\b", re.I)
           for k, v in _ATTACKERS.items()}
_STRIKE_CITY = re.compile(r"\b(isfahan|esfahan|tabriz|shiraz|mashhad|karaj|qom|ahvaz|ahwaz|bandar abbas|bushehr"
                          r"|kermanshah|urmia|khorramshahr|abadan|chabahar|kish|qeshm|kerman|yazd|rasht|zahedan|hamedan"
                          r"|arak|sanandaj|ilam|khorramabad|jask|sirik|abu musa|kharg|natanz|fordow|parchin|dezful"
                          r"|beirut|damascus|baghdad|erbil|sanaa|hodeidah|haifa|tel aviv|eilat|dimona|riyadh|jeddah"
                          r"|dubai|abu dhabi|doha|manama)\b", re.I)
_TARGET_KIND = {"port": r"ports?|harbou?rs?|docks?|jett(?:y|ies)|piers?", "base": r"bases?|garrisons?|barracks|headquarters",
                "airport": r"airports?|airfields?|air ?strips?", "oil": r"refiner(?:y|ies)|oil|fuel|depots?|terminals?",
                "airdef": r"air defen[cs]es?|radars?|missile (?:sites?|launchers?|batter(?:y|ies))|sam sites?|launchers?",
                "boats": r"boats?|speedboats?|vessels?|ships?|navy|naval"}
_TARGET_RX = {k: re.compile(r"\b(?:" + v + r")\b", re.I) for k, v in _TARGET_KIND.items()}
_NEW_EN = re.compile(r"\b(?:new|another|fresh|second|third|again|renewed|more|further|wave|round)\b", re.I)
_NEW_FA = re.compile(fa_norm("دوباره|مجدد|جدید|تازه|دومین|سومین|بار دیگر|باز هم|موج"))


def strike_key(m, chan_ok=False):
    """(attacker, places hit, kinds of target) of a news report of an attack, or None (see above). chan_ok: a
    Telegram channel's post gets one too (it joins a news story by it, never another channel's: see CHAN_JOIN)."""
    if (channel(m) and not chan_ok) or m.get("wit") or event_class(m) != "K":
        return None
    if set(m.get("flags") or []) & {"denial", "past", "controlled", "scheduled", "speculative", "threat", "analysis",
                                    "opinion", "quote", "digest", "reaction"}:
        return None
    t = m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or ""
    if not t or _NEW_EN.search(t) or (m.get("lang") == "fa" and _NEW_FA.search(fa_norm(m.get("ti") or ""))):
        return None
    who = {k for k, rx in _ATT_RX.items() if rx.search(t)}
    if len(who) != 1:
        return None                                 # nobody named, or two sides striking
    places = {x.lower().replace("esfahan", "isfahan").replace("ahwaz", "ahvaz") for x in _STRIKE_CITY.findall(t)}
    if not places:
        return None
    kinds = frozenset(k for k, rx in _TARGET_RX.items() if rx.search(t))
    return who.pop(), frozenset(places), kinds


def _chan_win(m):
    """How long after a news story's latest report a Telegram channel's post may still join it (rule 3 of the Gulf
    rules, and the same for every story): six hours for a post relaying a named outlet or telling no strike as it
    happens (a statement, a video, "WSJ: US struck Qeshm on Monday"), two hours for a post of a strike now."""
    from .citation import outlet_named             # citation builds on this module
    return CHAN_KEEP if outlet_named(m) or not strike(m) else CHAN_FRESH


def _chan_near(f, mf, t, c, k):
    """A channel's post and a news report of the same strike (same_strike) are one story only within the post's
    window (_chan_win) of each other: a channel's post hours later may be of a new strike."""
    if not (f.get("chan") or mf.get("chan")):
        return True
    tk = next((m["t"] for m in c["m"] if m["k"] == k), c["t"])
    return abs(t - tk) <= (f["cwin"] if f.get("chan") else CHAN_FRESH)


def same_strike(a, b):
    """Features of two news reports: the same strike, told in other words (see above)."""
    ka, kb = a.get("sk"), b.get("sk")
    if not ka or not kb or ka[0] != kb[0] or ka[1] != kb[1]:
        return False
    if a.get("chan") and b.get("chan"):
        return False                                # two channels: their short posts repeat for separate events
    if ka[2] and kb[2] and not ka[2] & kb[2]:
        return False                                # a port and an air-defence site: two targets
    if a["days"] and b["days"] and not a["days"] & b["days"]:
        return False
    return True
# ------------------------------------------------------------------ the Gulf Arab front: one attack, one story
# News reports (never a Telegram channel or citizen reports) of missiles or drones on a Gulf Arab city are one story
# when both tell of an attack, name the same city ("explosions heard in Riyadh", "2 Houthi missiles intercepted over
# Riyadh", «حمله هوایی به پایتخت عربستان»), or one names only the country ("over Saudi airspace"), and the report comes
# within two hours of the story's first report, or, while it is still being told, within an hour of its latest report
# and four hours of its first (later reports of the same attack: "Aramco building damaged as Houthis target Riyadh").
# Sirens and civil-defence warnings make a story of their own, joined
# the same way; never an attack's. Only for this front: a report naming Iran, Israel or America gets no mark
# (fronts.gulf_mark), and a story holding such a report takes no report by this rule; nor does a report that says
# it is a new or another attack. The main front's rules are untouched.
GULF_WINDOW = 2 * 3600
GULF_GAP = 1 * 3600           # still being told: within this of the story's latest report…
GULF_SPAN = 4 * 3600          # …and this of its first
# Beyond those windows (fronts.gulf_mark gives what each needs):
# 1. one named target (the Aramco tower in Riyadh's financial district, King Khalid airport, Abqaiq; fronts._TARGETS):
#    the reports naming it are one story for a day after its first report while the story is still being told
#    (TARGET_QUIET); after a quiet spell only later reports (damage, a confirmation) join, and one telling it as it
#    happens (sirens, explosions heard) two hours after the story went quiet is a new attack. A report saying it is
#    a new attack joins only within two hours of the story's latest report (gulf_key: new_ok);
# 2. a later report of an attack in an Arab country of the Middle East (damage, debris, a video, a ministry
#    confirming it, a claim of responsibility; nothing happening now) joins the attack on its city for twelve hours;
# 3. a Telegram channel's post joins a news story by these rules (never another channel's), within six hours of the
#    story's latest report, so a post retelling what the news has told is not a story of its own;
# 4. the Houthis' statement of their operations (fronts.gulf_claim), told by each outlet in its own slice, is one
#    story for sixteen hours after its first report, unless the counts of operations differ; a slice naming one
#    target also joins that target's attack story, one naming several stays with the statement.
TARGET_KEEP = 24 * 3600
TARGET_QUIET = 4 * 3600       # a named target's story quiet this long takes only later reports of its attack
AFTER_SPAN = 12 * 3600
CHAN_KEEP = 6 * 3600          # a channel's post relaying an outlet, or telling no strike, joins this long after…
CHAN_FRESH = 2 * 3600         # …a post of a strike as it happens only this long (it may be a new strike)
CHAN_SCORE = 0.4              # a post joining after the story's usual window needs a headline this close
CLAIM_SPAN = 16 * 3600
TARGET_FULL = 120             # a story with 60 reports takes no more, but one naming its target up to this many


def _gulf_time(t, c):
    """The report at time t comes within the Gulf rule's time window of story c. "Still being told" counts from
    the start of the story's latest run of reports (none two hours apart), not from an early report a later one
    joined to it hours before."""
    return abs(t - _since(c)) <= GULF_WINDOW or (abs(t - c["u"]) <= GULF_GAP and t - _run_start(c) <= GULF_SPAN)


def _run_start(c):
    ts = sorted((m["t"] for m in c["m"]), reverse=True)
    start = ts[0] if ts else c["t"]
    for x in ts[1:]:
        if start - x > GULF_WINDOW:
            break
        start = x
    return min(start, c["u"]) if not c.get("ongoing") else c["u"]


class GulfMark(tuple):
    """A Gulf mark (a tuple, as fronts.gulf_mark gives it) and what the headline says of its time: new (it says it
    is a new attack: "another", «جدید») and fresh (told as it happens: sirens, interceptions, explosions heard)."""
    new = False
    fresh = False


def gulf_key(m, chan_ok=False, new_ok=False):
    """(kind, places, countries, targets, later, count, several) of a news report on the Gulf Arab front
    (fronts.gulf_mark), or None. chan_ok: a Telegram channel's post gets one too (rule 3 above). new_ok: a report
    saying it is a new attack on a named target, and telling nothing happening now, gets a mark too (marked new):
    outlets call an attack "new" against earlier weeks' ("Saudi Arabia reports new attack on East-West pipeline"),
    so it joins that target's story while the story is still being told (gulf_when)."""
    if (channel(m) and not chan_ok) or m.get("wit") or _at_sea(m):
        return None
    if set(m.get("flags") or []) & {"denial", "past", "controlled", "scheduled", "speculative", "analysis", "opinion",
                                    "digest", "reaction", "quote"}:
        return None
    fa = m.get("lang") == "fa"
    if any(fronts.gulf_main(x, lang) for x, lang in ((m.get("ti"), m.get("lang") or "en"), (m.get("en_ti"), "en")) if x):
        return None
    en = m.get("en_ti") or ("" if fa else m.get("ti")) or ""
    fat = fa_norm(m.get("ti") or "") if fa else ""
    fresh = bool(fronts._FRESH_EN.search(en) or (fa and fronts._FRESH_FA.search(fat)))
    new = bool(_NEW_EN.search(en) or (fa and _NEW_FA.search(fat)))
    if new and not new_ok:
        return None                                 # "another attack", «موج جدید»: maybe a new one
    g = fronts.gulf_mark(m.get("ti") or "", "fa" if fa else "en") or (fronts.gulf_mark(en, "en") if fa else None)
    if not g:
        return None
    if new and (g[0] != "attack" or not g[3] or fresh):
        return None                                 # a new attack on a city, or one told as it happens
    g = GulfMark(g)
    g.new, g.fresh = new, fresh
    return g


def gulf_main(m):
    """True if the report's headline names the main front (a story holding one takes no report by the Gulf rule).
    The headline only: a Houthi attack whose text mentions Iran is still this front."""
    return any(
        fronts.gulf_main(x, lang) for x, lang in ((m.get("ti"), m.get("lang") or "en"), (m.get("en_ti"), "en")) if x)


def gulf_fit(a, b):
    """Two Gulf marks can be of one story: sirens only with sirens; the Houthis' statement with a statement, or,
    a slice of it naming one target only, with an attack on that target."""
    if a[0] == b[0]:
        return True
    if "alert" in (a[0], b[0]):
        return False
    c = a if a[0] == "claim" else b
    return bool(c[3]) and not c[6]


def _statement(x):
    """A Gulf mark of the Houthis' statement as a whole: several targets, a count, or no target named."""
    return x[0] == "claim" and (x[6] or not x[3])


def gulf_apart(a, marks):
    """True if a report with Gulf mark a is of a kind the story's marks keep apart: sirens and an attack; the
    Houthis' statement as a whole and an attack's story (a slice of it naming one target goes either way)."""
    if not marks:
        return False
    if not any(gulf_fit(a, x) for x in marks):
        return True
    if _statement(a) and any(x[0] == "attack" for x in marks):
        return True
    return a[0] == "attack" and any(_statement(x) for x in marks)


def same_gulf(a, b):
    """Gulf marks of two reports: one attack (or one round of sirens, or one statement) on one place. 3 = the same
    named target, 2 = the same city, 1 = one of them names only the country, 0 = not the same."""
    if not a or not b or not gulf_fit(a, b):
        return 0
    ra, rb = a[3] & fronts._ROUTES.keys(), b[3] & fronts._ROUTES.keys()
    if ra or rb:                                    # a long pipeline (no one city) is its own place: only the same
        return 3 if ra & rb else 0                  # pipeline, never another attack in that country
    if a[0] != b[0]:                                # a statement's slice naming one target, and an attack on it
        return 3 if a[3] & b[3] else 0
    if a[3] and b[3] and a[3] & b[3]:
        return 3
    if a[0] == "claim":                             # one statement: the same count, a place in common or none named
        if a[5] and b[5] and a[5] != b[5]:
            return 0
        if not a[2] & b[2]:
            return 0
        pa, pb = a[1] | a[3], b[1] | b[3]
        return 2 if (not pa or not pb or pa & pb) else 0
    if a[1] and b[1]:
        return 2 if a[1] & b[1] else 0
    return 1 if a[2] & b[2] else 0


def gulf_when(t, c, n, a, b, chan):
    """A report at time t with Gulf mark a, matching story c's mark b at level n (same_gulf), comes within the time
    the rules above give. chan: 0, or how long after the story's latest report a channel's post may join (_chan_win)."""
    if chan and abs(t - c["u"]) > chan:
        return False
    if a[0] == "claim" and b[0] == "claim":
        return abs(t - _since(c)) <= CLAIM_SPAN
    if getattr(a, "new", False):
        return n == 3 and abs(t - c["u"]) <= GULF_WINDOW   # "new attack" on the target: only while still told
    if n == 3:
        # the same named target, within a day of the story's first report, while it is still being told (no quiet
        # spell of TARGET_QUIET), or a later report (damage, a confirmation, a video); a report telling it as it
        # happens (sirens, explosions heard) after GULF_WINDOW of quiet is a new attack
        quiet = t - c["u"]
        if getattr(a, "fresh", False) and quiet > GULF_WINDOW:
            return False
        return abs(t - _since(c)) <= TARGET_KEEP and (quiet <= TARGET_QUIET or bool(a[4]))
    if n == 2 and (a[4] or b[4]) and a[2] & b[2] <= fronts.ARAB and abs(t - _since(c)) <= AFTER_SPAN:
        return True
    return _gulf_time(t, c)


PLACE_TOKENS = {w for v in PLACES.values() for w in tokens(v[1]) if len(w) >= 4} - {"gulf", "island", "persian"}
NAME_TOKENS = {w for v in PEOPLE.values() for x in v[2] if not x.startswith("re:") for w in tokens(x.rstrip("$"))
               if len(w) >= 4} - set("""minister foreign prime president leader chief commander defense defence staff
force armed council security national supreme countrie admiral general joint guard crown prince sheikh emir
revolutionary abdul abdullah abdulrahman moham mohamm malik""".split())
KEY = ENTITY | PLACE_TOKENS | NAME_TOKENS | tokens("""explosion intercept ballistic debris shrapnel mine seize
airport embassy base refinery facility vessel ship tanker cable carrier bomber fighter jet ultimatum sanction
enrichment uranium assassination evacuation airspace flight port""")
_PREFIX = re.compile(r"^([^:：]{2,45})[:：]\s")
_SAYS = re.compile(r"^(.{2,50}?)\s+(?:says|said|tells|told|warns|warned|claims|claimed|vows|vowed|announces"
                   r"|announced|confirms|confirmed|denies|denied|threatens|threatened|insists|insisted|urges|urged"
                   r"|calls|called|accuses|accused|rejects|rejected|demands|demanded|condemns|condemned|slams"
                   r"|slammed|welcomes|welcomed|praises|praised|criticizes|criticises|criticized|blames|blamed"
                   r"|dismisses|dismissed|stresses|stressed|reiterates|emphasizes|emphasised|emphasized|reacts"
                   r"|responds|hails|backs|supports|opposes|lauds|decries|denounces|denounced)\b", re.I)
_NOT_SPK = re.compile(r"\b(live|updates?|war|crisis|breaking|watch|video|report|exclusive|analysis|sources?|scoop"
                      r"|opinion|explainer|media|press|news|agency|channel|correspondent)\b", re.I)
_PERSON_CTRY = {"mbs": "gulf", "ghalibaf": "ir"}
for _pid, _v in PEOPLE.items():
    _c = match_keys(COUNTRIES_RX, " ".join([_v[1]] + [x for x in _v[2] if not x.startswith("re:")]))
    _PERSON_CTRY.setdefault(_pid, _c[0] if _c else None)


# outlets a headline cites ("…, Al-Arabiya reports", "Axios: …"): a claim from one outlet isn't the same story as a
# claim from another
_CITE = {k: re.compile(v, re.I) for k, v in {
    "reuters": r"\breuters\b", "ap": r"\b(?-i:AP)\b|associated press", "afp": r"\bafp\b|agence france",
    "bloomberg": r"\bbloomberg\b", "cnn": r"\bcnn\b", "fox": r"\bfox news\b", "nyt": r"new york times|\bnyt\b",
    "wsj": r"wall street journal|\bwsj\b", "wapo": r"washington post", "axios": r"\baxios\b",
    "politico": r"\bpolitico\b", "hill": r"(?<!capitol )\b(?:the )?hill\b", "nbc": r"\bnbc\b", "cbs": r"\bcbs\b",
    "abc": r"\babc news\b", "alarabiya": r"\bal[- ]?arabiya\b",
    "alaraby": r"\bal[- ]?arab[iy] al[- ]?jadeed\b|\bal[- ]?araby\b",
    "aljazeera": r"\bal[- ]?jazeera\b", "mayadeen": r"\bmayadeen\b", "masirah": r"\bal[- ]?masirah\b",
    "sky": r"\bsky news\b", "bbc": r"\bbbc\b", "kan": r"\b(?-i:Kan)\b|\bkan news\b", "ch12": r"\bchannel 12\b|\bn12\b",
    "ch13": r"\bchannel 13\b", "ch14": r"\bchannel 14\b", "ynet": r"\bynet\b|\byedioth\b", "haaretz": r"\bhaaretz\b",
    "toi": r"\btimes of israel\b", "jpost": r"\bjerusalem post\b", "hayom": r"\bisrael hayom\b",
    "maariv": r"\bmaariv\b", "tasnim": r"\btasnim\b", "fars": r"\bfars ?news\b|\bfars agency\b",
    "mehr": r"\bmehr news\b", "irna": r"\birna\b", "isna": r"\bisna\b", "nour": r"\bnour ?news\b",
    "iranintl": r"\biran international\b", "presstv": r"\bpress ?tv\b", "kayhan": r"\bkayhan\b",
    "sabereen": r"\bsaberee?n\b", "tass": r"\btass\b", "ria": r"\bria novosti\b", "xinhua": r"\bxinhua\b",
    "guardian": r"\bthe guardian\b", "telegraph": r"\bthe telegraph\b", "economist": r"\bthe economist\b",
    "ft": r"\bfinancial times\b", "isw": r"\bisw\b|study of war",
}.items()}
_DAYS = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_CLOCK = re.compile(r"\b\d{1,2}[:.]\d{2}\b|\b\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)", re.I)


def _numbers(title):
    """Counts and other figures in a headline (two -> 2), leaving out years and clock times."""
    out = set()
    for w in tokens(_CLOCK.sub(" ", title or "")):
        if w.isdigit():
            n = int(w)
            if not (1350 <= n <= 1450 or 1990 <= n <= 2035):     # years (Iranian and Gregorian)
                out.add(n)
    return frozenset(out)


def event_class(m):
    fl = set(m.get("flags") or [])
    for k, fs in CLASS_ORDER:
        if fl & fs:
            return k
    return "O"


def speaker(title):
    """Who the headline quotes, as (person id, country id, words): a known person or country, or else the
    words naming the speaker ("GCC chief", "ALECSO") when the headline reads "<speaker> says/condemns …".
    A bare "<name>:" prefix that is neither a person nor a country is often the outlet being cited, so it is
    not used. None if no speaker is found."""
    title = strip_live(title)
    m, says = _PREFIX.match(title), False
    if m and len(title[m.end():].split()) <= 2:
        m = None                                    # "Russia offers to mediate between Iran and US: report"
    if not m:
        m, says = _SAYS.match(title), True
    if not m or _NOT_SPK.search(m.group(1)):
        return None
    who = m.group(1)
    ppl = match_keys(PEOPLE_RX, who)
    if ppl:
        return ppl[0], _PERSON_CTRY.get(ppl[0]), None
    ctry = match_keys(COUNTRIES_RX, who)
    if ctry:
        return None, ctry[0], None
    words = frozenset(tokens(who))
    return (None, None, words) if says and words else None


def _other_speaker(sa, sb):
    """True if the two headlines quote different people, countries or organisations."""
    if not sa or not sb:
        return False
    if sa[0] and sb[0]:
        return sa[0] != sb[0]
    if sa[1] and sb[1]:
        return sa[1] != sb[1]
    if bool(sa[0] or sa[1]) != bool(sb[0] or sb[1]):
        return True                     # a known person or country vs an organisation we don't track
    return bool(sa[2] and sb[2] and not sa[2] & sb[2])


# two named people meeting or talking, or one arriving somewhere: told in many ways ("Putin held talks with Iranian
# president in Kremlin", "Pezeshkian and Putin meet in Moscow"), so headlines alone rarely match
_MEET = re.compile(r"\b(meets?|met|meeting|talks|discuss(es|ed)?|negotiat\w+|receives|received|hosts|hosted|welcomes"
                   r"|welcomed|greets|greeted|sits? down with)\b", re.I)
_CALL = re.compile(r"\b(phone|call|calls|called|telephone|video ?link|virtual\w*)\b", re.I)
_ARRIVE = re.compile(r"\b(arriv\w+|lands?|landed|lands in|entered|enters)\b", re.I)
_VISIT_NOT = re.compile(r"\b(will|to meet|to visit|next|plans?|expected|set to|schedul\w+|tomorrow|ahead of|before"
                        r"|after|left|leaves|departs?|departed)\b", re.I)


def visit(title):
    """'meet' / 'call' / 'arrive' for a headline about a meeting, a call or an arrival as it happens; None otherwise
    (an announced visit, a departure, anything else)."""
    t = title or ""
    if _VISIT_NOT.search(t):
        return None
    if _ARRIVE.search(t):
        return "arrive"
    if _MEET.search(t):
        return "call" if _CALL.search(t) else "meet"
    return None


def same_visit(a, b):
    """The same two (or more) people meeting or speaking by phone, or the same one person arriving in the same place:
    the people named must be exactly the same."""
    va, vb = a.get("visit"), b.get("visit")
    if not va or va != vb or a["ppl"] != b["ppl"] or a["chan"] != b["chan"]:
        return False
    if va == "arrive":
        return len(a["ppl"]) == 1 and bool((a["geo"] & b["geo"]) or (a["ctry"] & b["ctry"] - {"ir"}))
    return len(a["ppl"]) >= 2


def features(m):
    title = m.get("en_ti") or ""
    return {"vars": variants(title), "svars": variants(title, True), "cls": event_class(m), "geo": set(m.get("geo") or []), "visit": visit(title),
            "ctry": set(m.get("ctry") or []), "ppl": set(m.get("ppl") or []), "spk": speaker(title),
            "nums": _numbers(title), "days": frozenset(d.lower() for d in _DAYS.findall(title)),
            "cite": frozenset(k for k, rx in _CITE.items() if rx.search(title)),
            "chan": channel(m), **dict(zip(("cities", "spots", "blast"), place(m))),
            "wit": bool(m.get("wit")), "wcity": _wcities(m), "wtime": _wtimes(m),
            "strike_ok": not set(m.get("flags") or []) & NOT_A_STRIKE,
            "ship": vessel.mark(m), "sgen": _general(m), "dep": deploy.mark(m), "evac": evac.mark(m),
            "pull": pullback.mark(m), "dup": _dup_key(m),
            "stmt": vessel.signature(m), "when": vessel.when(m, fine=True) if _at_sea(m) else None,
            "sid": _ship_id(m), "sarea": vessel.area(m, head=True) if _at_sea(m) else None,
            "inc": _incident_report(m),
            "sk": strike_key(m, chan_ok=True), "gulf": gulf_key(m, chan_ok=True, new_ok=True), "gmain": gulf_main(m),
            "cwin": _chan_win(m) if channel(m) else 0,
            "dupsu": _norm_text(m.get("en_su") or m.get("su") or "")} | _ev_feats(m)


def _at_sea(m):
    en = m.get("en_ti") or m.get("ti") or ""
    return bool(vessel.SHIP_EN.search(en) or (m.get("lang") == "fa" and vessel.SHIP_FA.search(fa_norm(m.get("ti") or "")))
                or "maritime_incident" in (m.get("flags") or []))


def _ship_id(m):
    """The kind, flag, owner and name of the ship a report about ships tells of (vessel.ship_id), or None if none."""
    if not _at_sea(m):
        return None
    x = vessel.ship_id(m)
    return x if (x["kd"] or x["fl"] or x["nm"] or x["ow"]) else None


def _own_key(f):
    """(whose ship, sea area) of a report that tells both, else None."""
    sid = f.get("sid")
    return (sid["ow"], f["sarea"]) if sid and sid.get("ow") and f.get("sarea") else None


def _general(m):
    """A report about one ship in a sea area that gives no place, and is not an Iranian statement."""
    return None if vessel.statement(m) else vessel.general(m)


def _incident_report(m):
    """A report of an incident at sea told independently (UKMTO, outlets abroad), not an Iranian statement."""
    return bool(_at_sea(m) and "maritime_incident" in (m.get("flags") or []) and not vessel.statement(m)) \
        or bool(vessel.mark(m))


# the same article published again (an outlet re-posting it hours later, a wire story carried word for word): the
# same headline exactly and nearly the same text. Never for Telegram channels, citizen reports, or reports of an
# attack, an explosion, an incident at sea or a closed airspace, whose short headlines repeat for separate events.
DUP_WORDS = 8
DUP_TEXT = 0.9
DUP_KEEP = 24 * 3600
_DUP_NOT = {"kinetic", "maritime_incident", "hormuz_closure", "airspace", "witness"}


def _norm_text(x):
    return re.sub(r"[^\w]+", " ", (x or "").lower()).strip()


def _dup_key(m):
    if channel(m) or m.get("wit") or set(m.get("flags") or []) & _DUP_NOT:
        return None
    t = _norm_text(m.get("en_ti") or m.get("ti") or "")
    return t if len(t.split()) >= DUP_WORDS else None


def _same_text(a, b):
    if not a or not b:
        return False
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a[:600], b[:600]).ratio() >= DUP_TEXT


def _wcities(m):
    """Iranian cities (witness.CITIES keys) a report names: those of a post of citizen reports, or those in a
    report's headline and the start of its text."""
    if m.get("wit"):
        return frozenset(m["wit"].get("cities") or {})
    out = witness.cities_in((m.get("en_ti") or "") + " " + (m.get("en_su") or "")[:200], "en")
    if m.get("lang") == "fa":
        out |= witness.cities_in((m.get("ti") or "") + " " + (m.get("su") or "")[:200], "fa")
    return frozenset(out)


WIT_SAME = 30 * 60           # citizen reports from the same city: the same incident if the times they give are within
                             # half an hour of each other
WIT_UNTIMED = 2 * 3600       # or, when a post gives no time, if the posts are within two hours of each other
WIT_NEWS = 3 * 3600          # a news report of something that happened in that city joins them within three hours
TEHRAN = 12600               # Iran time, UTC+3:30 all year


def _wtimes(m):
    """(earliest, latest) moment of what a post of citizen reports tells, from the clock times in its messages (each
    the last such time at or before the post, give or take ten minutes); None if its messages give no time."""
    t = m.get("t") or 0
    hm = (m.get("wit") or {}).get("times") or []
    if not hm:
        return None
    day = (t + TEHRAN) // 86400 * 86400 - TEHRAN          # midnight in Tehran on the post's day
    out = []
    for x in hm:
        e = day + int(x[:2]) * 3600 + int(x[3:]) * 60
        if e > t + 600:
            e -= 86400                                     # 23:55 told in a post after midnight
        if t - e <= 6 * 3600:                              # a time far before the post is something else
            out.append(e)
    return (min(out), max(out)) if out else None


def _witness_match(a, b, dt):
    """Citizen reports (witness.py) join other citizen reports from the same city about the same moment, and a news or channel report of
    an attack, an explosion or air defence fire in that city (not a gas explosion, an exercise or a denial), so
    the story stops being unconfirmed once an outlet reports it. Nothing else joins them."""
    if not a["wcity"] & b["wcity"]:
        return False
    if a["wit"] and b["wit"]:
        if a["wtime"] and b["wtime"]:
            # both give clock times: the same incident if those are within half an hour (a blast is reported at once)
            gap = max(a["wtime"][0], b["wtime"][0]) - min(a["wtime"][1], b["wtime"][1])
            return 0.5 if gap <= WIT_SAME else False
        return 0.5 if dt <= WIT_UNTIMED else False
    o = b if a["wit"] else a
    if o["cls"] in ("K", "A", "M") and o["strike_ok"] and not o["blast"] and dt <= WIT_NEWS:
        return 0.5 + 0.4 * (1 - dt / WIT_NEWS)            # the closest citizen reports in time first
    return False


def _text_close(x, y, physical):
    """Very close headlines: most words shared, including a name, place, number or other key word."""
    inter = x & y
    n = len(inter)
    if n < 2:
        return 0.0
    jac = n / len(x | y)
    if n >= 4 and jac >= 0.5:
        return jac
    if not (inter & KEY or any(w.isdigit() for w in inter)):
        return 0.0
    if jac >= 0.5:
        return jac
    if n >= 3 and jac >= (0.4 if physical else 0.45):
        return jac
    if physical and n >= 3 and (x <= y or y <= x) and jac >= 0.3:
        return jac                                  # a short headline wholly inside a longer one
    return 0.0


ANCHOR_DT = 2 * 3600       # reports this close in time may also match on rare shared words (see same_story)
RARE_STORIES = 5           # a word found in at most this many stories counts as rare
LONG_POST = 16             # a channel's post this many words long is its whole text, not a headline…
LONG_HOLD = 0.75           # …and it is a headline's story if it holds this much of the headline's words


def same_story(a, b, dt=0, rare=frozenset()):
    """a, b: features of two reports published dt seconds apart; rare: the uncommon words of report a.
    Returns the headlines' similarity (0 = not the same story). Two reports are the same story only if they
    agree on what happened, where and who said it, and their headlines are very close.
    Reports within two hours of each other that share uncommon words (a place such as Pakdasht or Sirik, a
    rare name) need a little less overlap. The story's time window is checked by the caller."""
    if a.get("wit") or b.get("wit"):
        return _witness_match(a, b, dt)
    ka, kb = KIND[a["cls"]], KIND[b["cls"]]
    if ka and kb and ka != kb:                      # what happened
        return False
    if (a.get("stmt") and b.get("inc")) or (b.get("stmt") and a.get("inc")):
        return False                                # an Iranian statement and an incident told independently
    if a.get("when") and b.get("when") and not vessel.overlap(a["when"], b["when"]):
        return False                                # at sea, the times the reports give don't meet
    if a.get("sid") and b.get("sid"):              # at sea: another kind of ship, another flag, another name
        if not vessel.ships_fit(a["sid"], b["sid"]):
            return False
        if vessel.same_ship(a["sid"], b["sid"]):
            return 0.6
        if a["sid"].get("ow") and a["sid"]["ow"] == b["sid"].get("ow") and a["sid"]["kd"] and b["sid"]["kd"] \
                and a.get("sarea") and a["sarea"] == b.get("sarea") and dt <= SHIP_OWNER:
            return 0.5                              # "Qatari LNG tanker" and "Qatar's LNG carrier" in the Gulf the same day
    if a.get("stmt") and b.get("stmt"):             # an Iranian statement about ships (vessel.py)
        if vessel.same_statement(a["stmt"], b["stmt"]):
            return 0.6
        if vessel.other_statement(a["stmt"], b["stmt"]):
            return False
    if a.get("ship") and b.get("ship"):             # an incident at sea placed by distance and bearing (vessel.py)
        if vessel.same(a["ship"], b["ship"]):
            return 0.6
        if vessel.differ(a["ship"], b["ship"]):
            return False
    if same_spot(a, b):
        return 0.5                                  # the same incident at the same spot, in other words
    if same_visit(a, b):
        return 0.5                                  # the same leaders meeting, or the same leader arriving somewhere
    physical = a["cls"] in PHYSICAL or b["cls"] in PHYSICAL
    jac, anchored = 0.0, False
    for x in a["vars"]:
        for y in b["vars"]:
            j = _text_close(x, y, physical)
            if not j and dt <= ANCHOR_DT and rare:
                inter = x & y
                n, k = len(inter), len(inter & rare)
                j = n / len(x | y) if n >= 3 else 0.0
                if (k >= 1 and j >= 0.35) or (k >= 2 and j >= 0.3):
                    anchored = True
                else:
                    j = 0.0
            jac = max(jac, j)
    if not jac:
        # the same words in other forms ("Kremlin" / "Russia", "mediator" / "mediate"): only very close headlines
        for x in a.get("svars", ()):
            for y in b.get("svars", ()):
                j = _text_close(x, y, physical)
                if j > 0.5 and len(x & y) >= 3 and len((x & y) - _GENERIC) >= 2:
                    jac = max(jac, j)
    if not jac and rare and dt <= CHAN_KEEP and not physical:
        # a channel's post with no headline, its whole text in one (Vahidonline): it can't be as close as two headlines,
        # but it holds a news headline of the story nearly whole, a rare word with it
        for x in a.get("svars", ()):
            for y in b.get("svars", ()):
                lx, sy = (x, y) if a["chan"] and len(x) >= LONG_POST > len(y) else \
                    (y, x) if b["chan"] and len(y) >= LONG_POST > len(x) else (None, None)
                if lx is None or len(sy) < 4:
                    continue
                inter = lx & sy
                if len(inter) / len(sy) >= LONG_HOLD and inter & rare and len(inter - _GENERIC) >= 3:
                    jac, anchored = max(jac, 0.4), True
    if not jac:
        return False
    if (ka is None) != (kb is None) and jac < 0.5:
        # one report's kind wasn't recognised: rare shared words are enough only if the other isn't an event,
        # so a reaction ("… condemn the attack on …") doesn't join the attack itself
        if not anchored or physical:
            return False
    if a["geo"] and b["geo"]:                       # where
        if not _region(a["geo"]) & _region(b["geo"]):
            return False
    elif a["ctry"] and b["ctry"]:
        if not a["ctry"] & b["ctry"]:
            return False
    elif (a["geo"] or b["geo"]) and jac < 0.5:      # one names the place, the other doesn't
        return False
    if a["days"] and b["days"] and not a["days"] & b["days"]:
        return False                                # when: "on Sunday" vs "on Monday"
    if a["nums"] and b["nums"] and not a["nums"] & b["nums"] and jac < 0.6:
        return False                                # "11 killed" vs "16 killed"
    if not physical:                                # who said it, and who reported it
        if _other_speaker(a["spk"], b["spk"]):
            return False
        if a["ppl"] and b["ppl"] and not a["ppl"] & b["ppl"]:
            return False
        if a["cite"] and b["cite"] and not a["cite"] & b["cite"]:
            return False
    return jac


_SUB = re.compile(r"\s+/\s+|؛|\s+\|\s+")


def variants(title, same=False):
    """Token sets used for matching: the whole headline and, for "A / B" headlines, its first part alone."""
    full = tokens(title, same)
    head = _SUB.split(title or "", 1)[0]
    if head != (title or ""):
        h = tokens(head, same)
        if len(h) >= 2 and h != full:
            return [full, h]
    return [full]


# ------------------------------------------------------------------ when it happened: a time label for each story
# A story of an event (a strike, a blast, an incident at sea, an Iranian statement about ships) carries the span
# of time the event happened in (c["ev"]), worked out from its reports and narrowed as reports come in. A report is
# placed in time too: by the time it gives («بامداد امروز», "3 hours ago", "last night", a clock time), else, if it
# comes first-hand (an Iranian outlet, an Israeli outlet on Israel, an advisory placing a ship by distance; not a
# video, a recap, an analysis or a relayed outlet), within the 12 hours before it; else not at all. A report placed
# in time never joins a story whose span it misses: today's new "two tankers" statement is not yesterday's, however
# late yesterday's story got its last retelling. A report giving a time within an older story's span joins it
# beyond the usual windows (up to two days after its latest report). The other rules stay as they are.
EV_ON = True
EV_FIRST = 6 * 3600          # the first report of an event comes out within this of it
EV_FRESH = 12 * 3600         # a first-hand report that gives no time tells of something within this before it
EV_SLACK = 2 * 3600
EV_EXTEND = 48 * 3600
EV_CLOCK = 4 * 3600          # a clock time ("at 2 a.m.", "3 hours ago") is narrower than any part of the day
EV_NARROW = 18 * 3600        # a time the headline gives counts only if it is this narrow ("Friday", not "this week")
_NOT_NOW_EN = re.compile(r"\b(video|watch|footage|images?|photos?|pictures|recap|timeline|explainer|what we know)\b", re.I)
_NOT_NOW_FA = re.compile(fa_norm("فیلم|تصاویر|ویدئو|ویدیو|عکس|جمع بندی|مروری بر|روایت"))
_NOT_NOW_FLAGS = {"past", "analysis", "opinion", "digest", "speculative", "denial"}


def _ev_feats(m):
    return {"evp": None}                         # filled by _ev_report once the rest of the features are known


def _physical(f):
    return f["cls"] in PHYSICAL or bool(f.get("stmt") or f.get("ship"))


def _first_hand(m, f):
    """A report that tells of the event as it comes: it gives no reason to think it is told later."""
    if set(m.get("flags") or []) & _NOT_NOW_FLAGS or f["chan"]:
        return False
    en, fa = vessel._head(m)
    if _NOT_NOW_EN.search(en) or (fa and _NOT_NOW_FA.search(fa)):
        return False
    if f.get("ship"):
        return True                              # an advisory placing the ship by distance and bearing
    if f["cite"]:
        return False                             # a relayed outlet
    g = BY_ID.get((m.get("s") or "").split(":")[0], {}).get("group")
    return g == "iran" or (g == "il" and "il" in f["ctry"])


EV_ANCHOR, EV_INFER, EV_TOLD = 0, 1, 2       # how a time is known: a story's first report, a first-hand report, told


# parts of the day a headline names, in Tehran's time: (words, days back, from hour, to hour). Only for the
# bulletin's time labels; the Telegram rules read times through vessel.when as before.
_PART = [(fa_norm(w), d, a, b) for w, d, a, b in [
    ("بامداد دیروز|دیروز بامداد", 1, 0, 5), ("صبح دیروز|دیروز صبح", 1, 5, 12), ("ظهر دیروز|دیروز ظهر", 1, 11, 15),
    ("عصر دیروز|دیروز عصر|بعد از ظهر دیروز|بعدازظهر دیروز", 1, 14, 19), ("شب دیروز|دیروز شب", 1, 19, 24),
    ("دیشب|شب گذشته|نیمه شب گذشته|شامگاه دیروز", 0, -5, 5), ("بامداد|سحرگاه|سپیده دم|نیمه شب", 0, 0, 5),
    ("صبح امروز|امروز صبح|صبحگاه", 0, 5, 12), ("ظهر امروز|امروز ظهر", 0, 11, 15),
    ("عصر امروز|امروز عصر|بعد از ظهر امروز|بعدازظهر امروز", 0, 14, 19), ("امشب|شامگاه|شب امروز", 0, 18, 24)]]
_PART_EN = [(re.compile(r, re.I), d, a, b) for r, d, a, b in [
    (r"\b(early (\w+ )?morning|pre-?dawn|before dawn|at dawn|overnight)\b", 0, 0, 5),
    (r"\b(last night|late (yesterday|last night))\b", 0, -5, 5),
    (r"\b(this morning)\b", 0, 5, 12), (r"\b(this afternoon)\b", 0, 12, 18),
    (r"\b(this evening|tonight)\b", 0, 18, 24), (r"\b(yesterday morning)\b", 1, 5, 12),
    (r"\b(yesterday afternoon)\b", 1, 12, 18), (r"\b(yesterday evening)\b", 1, 18, 24)]]


def _part_of_day(m):
    """(earliest, latest) of the part of the day the headline names («بامداد امروز»: midnight to 5 a.m.), or None."""
    en, fa = vessel._head(m)
    t, d0 = m["t"], vessel._day0(m["t"])
    for rx, d, a, b, txt in [(re.compile(w), d, a, b, fa) for w, d, a, b in _PART] + \
                            [(rx, d, a, b, en) for rx, d, a, b in _PART_EN]:
        if txt and rx.search(txt):
            lo, hi = d0 - d * 86400 + a * 3600, min(t, d0 - d * 86400 + b * 3600)
            if lo > t and d == 0:                       # "this morning" before dawn, "dawn" said in the evening: today
                return None
            return (lo, hi) if lo < hi else None
    return None


def _ev_report(m, f):
    """(earliest, latest, how it is known) of the event a report tells of, or None. A time the headline of a news
    report gives (EV_TOLD; a clock time first, then a part of the day, «بامداد» = midnight to 5 a.m.; a channel's
    clock times are too loose: «ساعت ۱۲:۱۴» may be past midnight), else the 12 hours before a first-hand report
    (EV_INFER). Reports found through Bing search carry a guessed time: never placed."""
    if not _physical(f) or m.get("via") == "bing":
        return None
    w = None if f["chan"] else vessel.when({**m, "su": "", "en_su": ""}, fine=True)  # a summary recalls other days
    if w and w[1] - w[0] <= EV_CLOCK:
        return (w[0], w[1], EV_TOLD)
    p = None if f["chan"] else _part_of_day(m)
    if p:
        return (p[0], p[1], EV_TOLD)
    if w and w[1] - w[0] <= EV_NARROW:
        return (w[0], w[1], EV_TOLD)
    d = None if f["chan"] else vessel.past_day(m)   # "on Sunday, November 8" in the summary's first sentence
    if d:
        return (d[0], d[1], EV_TOLD)
    if _first_hand(m, f):
        return (m["t"] - EV_FRESH, m["t"], EV_INFER)
    return None


def _ev_mid_dist(a, b):
    """How far the middle of a report's time is from a story's likeliest moment: the middle of a time told, or, for a
    time inferred from reports, its end (a blast is mostly reported soon after it)."""
    at = b[1] if b[2] == EV_INFER else (b[0] + b[1]) / 2
    return abs((a[0] + a[1]) / 2 - at)


def _ev_gap(a, b):
    return max(0, a[0] - b[1], b[0] - a[1])


def _ev_meet(a, b):
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo <= hi else None


class Clusterer:
    def __init__(self, clusters):
        self.clusters = clusters
        self.merged_away = set()
        self.byid = {c["id"]: c for c in clusters}
        self.index = {}
        self.tok = {}
        self.ships = {}                                   # story id -> [(place of an incident at sea, time)]
        self.stmts = {}                                   # story id -> [(Iranian statement about ships, when, time)]
        self.incs = {}                                    # story id -> [(when, time)] of incidents at sea told independently
        self.sids = {}                                    # story id -> [kind, flag and name of the ship a report tells of]
        self.owns = {}                                    # (whose ship, sea area) -> story ids
        self.deps = {}                                    # (count, kind, destination) of a deployment -> story ids
        self.evacs = {}                                   # (who, country, how far) of an order to leave -> story ids
        self.pulls = {}                                   # story id -> [(forces taken out of a place: pullback.mark, time)]
        self.dups = {}                                    # a long headline, exactly -> [(story id, time, text)]
        self.ev = {}                                      # story id -> (earliest, latest): when its event happened
        self.gulfs = {}                                   # story id -> [(Gulf-front mark, channel's, time)] (gulf_key)
        self.gmain = set()                                # stories with a report naming the main front
        for c in clusters:
            self._index(c)

    def _index(self, c):
        feats = self.tok.setdefault(c["id"], {})
        for m in sorted(c["m"], key=lambda m: m["t"]):
            if m["k"] not in feats:
                feats[m["k"]] = features(m)
                self._ev_add(c, m, feats[m["k"]])
                for v in feats[m["k"]]["vars"]:
                    for w in v:
                        self.index.setdefault(w, set()).add(c["id"])
                if feats[m["k"]].get("ship"):
                    self.ships.setdefault(c["id"], []).append((feats[m["k"]]["ship"], m["t"]))
                if feats[m["k"]].get("stmt"):
                    self.stmts.setdefault(c["id"], []).append((feats[m["k"]]["stmt"], feats[m["k"]]["when"], m["t"]))
                if feats[m["k"]].get("inc"):
                    self.incs.setdefault(c["id"], []).append((feats[m["k"]]["when"], m["t"]))
                if feats[m["k"]].get("sid"):
                    self.sids.setdefault(c["id"], []).append(feats[m["k"]]["sid"])
                if _own_key(feats[m["k"]]):
                    self.owns.setdefault(_own_key(feats[m["k"]]), set()).add(c["id"])
                if feats[m["k"]].get("dep"):
                    self.deps.setdefault(feats[m["k"]]["dep"], set()).add(c["id"])
                if feats[m["k"]].get("evac"):
                    self.evacs.setdefault(feats[m["k"]]["evac"], set()).add(c["id"])
                if feats[m["k"]].get("pull"):
                    self.pulls.setdefault(c["id"], []).append((feats[m["k"]]["pull"], m["t"]))
                if feats[m["k"]].get("gulf"):
                    self.gulfs.setdefault(c["id"], []).append((feats[m["k"]]["gulf"], feats[m["k"]]["chan"], m["t"]))
                if feats[m["k"]].get("gmain"):
                    self.gmain.add(c["id"])
                if feats[m["k"]].get("dup"):
                    self.dups.setdefault(feats[m["k"]]["dup"], []).append((c["id"], m["t"], feats[m["k"]]["dupsu"]))

    def _ev_add(self, c, m, f):
        """Narrow the story's time label with a report (see EV_ON)."""
        if not EV_ON or not _physical(f):
            return
        w = f.get("evp") or _ev_report(m, f)
        f["evp"] = w
        cur = self.ev.get(c["id"])
        if m.get("via") == "bing" and not w:
            return                                   # Bing guesses the time of what it finds: it sets no label
        if cur is not None and cur[2] >= EV_INFER and m["t"] < cur[0] - EV_SLACK:
            return                                   # out before the event it tells of: its time is wrong
        if cur is None:                              # the first report comes out within six hours of the event
            cur = w if w and w[2] == EV_TOLD else (m["t"] - EV_FIRST, m["t"], w[2] if w else EV_ANCHOR)
        elif w and w[2] > cur[2]:
            cur = w                                      # a better known time replaces a weaker guess
        elif w and w[2] == cur[2]:
            x = _ev_meet(cur, w)                         # a report that misses it (joined by another rule) is left out
            cur = (x[0], x[1], cur[2]) if x else cur
        self.ev[c["id"]] = cur
        c["ev"] = [int(cur[0]), int(cur[1]), cur[2]]

    def _facts(self, f, cid):
        """How many particular facts the report shares with the story's closest report."""
        best = 0
        for mf in self.tok.get(cid, {}).values():
            n = sum((
                bool(same_spot(f, mf)),
                bool(f["cities"] & mf["cities"]),
                bool(f["nums"] and mf["nums"] and f["nums"] & mf["nums"]),
                bool(f["sk"] and mf["sk"] and same_strike(f, mf)),
                bool(f.get("sid") and mf.get("sid") and vessel.same_ship(f["sid"], mf["sid"])),
                bool(f.get("stmt") and mf.get("stmt") and vessel.same_statement(f["stmt"], mf["stmt"])),
                bool(f.get("ship") and mf.get("ship") and vessel.same(f["ship"], mf["ship"]))))
            best = max(best, n)
        return best

    def _ev_fits(self, f, cid):
        """The report's time meets the story's label, or one can't rule the other out: a label only assumed from the
        story's first report rules out nothing, nor does a first-hand report's assumed time rule out a time told (an
        event made known days later: «قطر حملهٔ ۲ روز قبل به کشتی خود را تأیید کرد»)."""
        if not EV_ON or not f.get("evp"):
            return True
        lab = self.ev.get(cid)
        if not lab or lab[2] == EV_ANCHOR or (f["evp"][2] == EV_INFER and lab[2] == EV_TOLD):
            return True
        return vessel.overlap(f["evp"], lab, EV_SLACK)

    def _ev_late(self, item, f, c):
        """A report giving a time within an older story's label: it may join beyond the usual windows."""
        if not EV_ON or not f.get("evp") or f["evp"][2] != EV_TOLD:
            return False
        lab = self.ev.get(c["id"])
        return bool(lab) and lab[2] != EV_ANCHOR and item["t"] - c["u"] <= EV_EXTEND \
            and vessel.overlap(f["evp"], lab, EV_SLACK)

    def _ev_back(self, item, f, c):
        """A report naming an earlier day (vessel.past_day) whose time meets the story's, or the day of its reports
        when the story has no better label: the same named target's attack retold the next day joins it (up to two
        days after its latest report)."""
        if not EV_ON or not f.get("evp") or f["evp"][2] != EV_TOLD or item["t"] - c["u"] > EV_EXTEND:
            return False
        if not vessel.past_day(item):
            return False
        lab = self.ev.get(c["id"])
        span = lab if lab and lab[2] != EV_ANCHOR else (c["t"] - EV_FIRST, c["u"])
        return vessel.overlap(f["evp"], span, EV_SLACK)

    def _chan_late(self, item, f, c):
        """A Telegram channel's post retelling a news story: it may join beyond the usual windows, within its window
        (_chan_win) of the story's latest report, if the story has a news report (rule 3 of the Gulf rules)."""
        return bool(f.get("chan")) and c["t"] <= item["t"] and item["t"] - c["u"] <= f["cwin"] \
            and any(not channel(m) for m in c["m"])

    def _rare(self, w, t):
        """True if at most RARE_STORIES stories of the two days around t use the word."""
        ids = self.index.get(w, ())
        if len(ids) <= RARE_STORIES:
            return True
        n = 0
        for cid in ids:
            c = self.byid.get(cid)
            if c and abs(t - c["t"]) <= 2 * 86400:
                n += 1
                if n > RARE_STORIES:
                    return False
        return True

    def add(self, item):
        """Attach the item to an existing cluster or start a new one. Returns (cluster, is_new_cluster)."""
        f = features(item)
        if EV_ON and _physical(f):
            f["evp"] = _ev_report(item, f)
        it_tok = set().union(*f["vars"])
        rare = frozenset(w for w in it_tok if len(w) >= 4 and not w.isdigit() and self._rare(w, item["t"]))
        cand = {}
        for w in it_tok:
            for cid in self.index.get(w, ()):
                cand[cid] = cand.get(cid, 0) + 1
        ranked = []
        for cid, n in cand.items():
            c = self.byid.get(cid)
            if c and (abs(item["t"] - _since(c)) <= (STRIKE_WINDOW if f["sk"] else WINDOW["other"])
                      or self._ev_late(item, f, c) or self._chan_late(item, f, c)):
                ranked.append((n, cid))
        matches = []
        for _, cid in sorted(ranked, reverse=True)[:40]:
            c = self.byid.get(cid)
            if not c or len(c["m"]) >= 60:
                continue
            if any(m["k"] == item["k"] for m in c["m"]):
                return c, False
            if self._ship_conflict(f["ship"], cid):
                continue                                   # an incident at sea placed elsewhere
            if self._kind_conflict(f, cid):
                continue                                   # an Iranian statement vs an incident told independently
            if self._ship_misfit(f, cid):
                continue                                   # another kind of ship, another flag or another name
            if not self._ev_fits(f, cid):
                continue                                   # it happened at another time
            if self._gulf_conflict(f, cid):
                continue                                   # sirens and the attack itself: two stories (Gulf front)
            late = self._ev_late(item, f, c)
            feats = self.tok.get(cid, {})
            if f["sk"] and (abs(item["t"] - _since(c)) <= STRIKE_WINDOW or late) \
                    and any(same_strike(f, mf) and _chan_near(f, mf, item["t"], c, k) for k, mf in feats.items()):
                matches.append((0.55, c))                  # the same strike told in other words (see same_strike)
                continue
            physical = f["cls"] in PHYSICAL or any(x["cls"] in PHYSICAL for x in feats.values())
            win = WINDOW["event" if physical else "other"]
            if f["spk"] and f["spk"][0] and any((x.get("spk") or (None,))[0] == f["spk"][0] for x in feats.values()):
                win = max(win, SPEECH_WINDOW)              # one person's words, retold for hours
            if abs(item["t"] - _since(c)) > win and not late and not self._chan_late(item, f, c):
                continue                                   # when: measured from the story's first report
            times = {m["k"]: m["t"] for m in c["m"]}
            score = max((same_story(f, mf, abs(item["t"] - times.get(k, c["t"])), rare) for k, mf in feats.items()),
                        default=0.0)
            if score and score < CHAN_SCORE and abs(item["t"] - _since(c)) > win and not late:
                continue                                   # a channel's late post: only a close headline (rule 3)
            if score:
                matches.append((score, c))
        for score, c in self._ship_matches(item, f) + self._same_matches(item, f) + self._stmt_matches(item, f) \
                + self._own_matches(item, f) + self._gulf_matches(item, f):
            if any(m["k"] == item["k"] for m in c["m"]):
                return c, False
            if not any(x is c for _, x in matches) and self._ev_fits(f, c["id"]):
                matches.append((score, c))
        for score, c in self._pull_matches(item, f):
            if any(m["k"] == item["k"] for m in c["m"]):
                return c, False
            # the same pullback retold the next day: only a time the headline gives can keep it apart, not one assumed
            if not any(x is c for _, x in matches) and (self._ev_fits(f, c["id"]) or not EV_ON or not f.get("evp")
                                                        or f["evp"][2] != EV_TOLD):
                matches.append((score, c))
        if EV_ON and f.get("evp") and f["evp"][2] == EV_TOLD and len(matches) > 1:
            # a report giving a time that fits several events (two or three blasts at dawn): the event whose time it
            # falls in, then the one sharing the most particular facts with it (the spot, the city, who struck, the
            # count, the ship, the statement), then the one whose time is nearest, then the closest headline
            def rank(x):
                lab = self.ev.get(x[1]["id"])
                known = lab and lab[2] != EV_ANCHOR
                return (_ev_gap(f["evp"], lab) if known else 0, -self._facts(f, x[1]["id"]),
                        _ev_mid_dist(f["evp"], lab) if known else 0, -x[0])
            matches.sort(key=rank)
            g = rank(matches[0])[0]
            matches = [x for x in matches if rank(x)[0] == g]
        else:
            matches.sort(key=lambda x: -x[0])
        best = matches[0][1] if matches else None
        for _, other in matches[1:]:
            # the report fits two stories: fold the smaller one in only if the two also match each other
            # directly (not merely through this report), remembering its id so its alert isn't sent twice
            fb, fo = self.tok.get(best["id"], {}), self.tok.get(other["id"], {})
            tb, to = {m["k"]: m["t"] for m in best["m"]}, {m["k"]: m["t"] for m in other["m"]}
            strike_pair = any(same_strike(x, y) and (not (x["chan"] or y["chan"])
                                                     or abs(to.get(kx, 0) - tb.get(ky, 0)) <= CHAN_KEEP)
                              for kx, x in fo.items() for ky, y in fb.items()) or bool(
                {_own_key(x) for x in fo.values()} & {_own_key(y) for y in fb.values()} - {None})
            gulf_pair = self._gulf_pair(best, other)
            if gulf_pair is False:
                continue                               # sirens and an attack on the Gulf front: kept apart
            if gulf_pair is None and f.get("gulf") and f["gulf"][4] and self._gulf_news(best) \
                    and self._gulf_news(other):
                continue                               # bridged by a later report only: the Gulf rule's times decide
            strike_pair = strike_pair or gulf_pair
            if (len(other["m"]) > 8 and not strike_pair) or len(best["m"]) + len(other["m"]) > 60:
                continue
            if best.get("manual") or other.get("manual"):
                continue                               # a story put together by hand is never folded either way
            if EV_ON and self.ev.get(best["id"]) and self.ev.get(other["id"]) \
                    and self.ev[best["id"]][2] == self.ev[other["id"]][2] != EV_ANCHOR \
                    and not vessel.overlap(self.ev[best["id"]], self.ev[other["id"]], EV_SLACK):
                continue                               # two events at different times
            if any(self._ship_conflict(x, best["id"]) for x, _ in self.ships.get(other["id"], [])):
                continue                               # two incidents at sea placed apart
            if self.sids.get(other["id"]) and self.sids.get(best["id"]) and not any(
                    vessel.ships_fit(x, y) for x in self.sids[other["id"]] for y in self.sids[best["id"]]):
                continue                               # two stories about different ships
            if not strike_pair and not any(same_story(x, y, abs(to.get(kx, 0) - tb.get(ky, 0))) for kx, x in fo.items()
                       for ky, y in fb.items()):
                continue
            best["m"].extend(other["m"])
            best["t"] = min(best["t"], other["t"])
            best["u"] = max(best["u"], other["u"])
            best["merged"] = sorted(set(best.get("merged", [])) | {other["id"]} | set(other.get("merged", [])))
            for k in ("img", "vid"):
                if other.get(k) and not best.get(k):
                    best[k] = other[k]
            self.clusters.remove(other)
            self.byid.pop(other["id"], None)
            self.merged_away.add(other["id"])
        if best is None:
            c = {"id": "c" + sha(item["k"] + str(item["t"]), 10), "t": item["t"], "u": item["t"], "m": [item],
                 "alerted": False}
            self.clusters.append(c)
            self.byid[c["id"]] = c
            self._index(c)
            return c, True
        best["m"].append(item)
        best["t"] = min(best["t"], item["t"])
        best["u"] = max(best["u"], item["t"])
        self._index(best)
        return best, False


    def _ship_conflict(self, mark, cid):
        """True if the story tells of an incident at sea placed elsewhere than `mark` and nowhere at `mark`."""
        if not mark:
            return False
        marks = [x for x, _ in self.ships.get(cid, [])]
        return bool(marks) and not any(vessel.same(mark, x) for x in marks) and any(vessel.differ(mark, x) for x in marks)

    def _own_matches(self, item, f):
        """The story of one country's ship hit in one sea area ("Qatari LNG carrier struck in the Gulf", «قطر حمله به
        کشتی خود در خلیج فارس را تأیید کرد»), for a day after its latest report, if its kind of ship fits."""
        out = []
        for cid in self.owns.get(_own_key(f), ()) if _own_key(f) else ():
            c = self.byid.get(cid)
            if c and len(c["m"]) < 60 and abs(item["t"] - c["u"]) <= SHIP_KEEP and not self._ship_misfit(f, cid) \
                    and not self._kind_conflict(f, cid):
                out.append((0.55, c))
        return out

    def _gulf_matches(self, item, f):
        """Stories of the same attack (or the same sirens, or the same Houthi statement) on the same place in an Arab
        country of the Middle East (see GULF_WINDOW and the rules after it)."""
        out = []
        if not f.get("gulf"):
            return out
        for cid, marks in self.gulfs.items():
            c = self.byid.get(cid)
            if not c or cid in self.gmain or len(c["m"]) >= TARGET_FULL:
                continue
            n = 0
            for x, xch, _ in marks:
                if f["chan"] and xch:
                    continue                           # a channel's post joins the news, never another channel
                k = same_gulf(f["gulf"], x)
                if k > n and (gulf_when(item["t"], c, k, f["gulf"], x, f["cwin"] if f["chan"] else (CHAN_FRESH if xch else 0))
                              or (k == 3 and self._ev_back(item, f, c))):
                    n = k
            if len(c["m"]) >= 60 and n < 3:
                continue                               # a full story takes only reports naming its target
            if n and not self._gulf_conflict(f, cid) and self._ev_fits(f, cid):
                # of two stories that fit as well, the one told most recently
                out.append((0.5 + 0.05 * n - min(abs(item["t"] - c["u"]), 86400) / 8640000, c))
        return out

    def _gulf_news(self, c):
        return c["id"] not in self.gmain and any(not ch for _, ch, _ in self.gulfs.get(c["id"], ()))

    def _gulf_conflict(self, f, cid):
        """True if the report is of one kind on the Gulf front (an attack, sirens, the Houthis' statement naming
        several targets) and the story only of another (gulf_fit)."""
        if not f.get("gulf"):
            return False
        if cid in self.gmain:
            return False
        return gulf_apart(f["gulf"], [x for x, _, _ in self.gulfs.get(cid, ())])

    def _gulf_pair(self, a, b):
        """Two Gulf-front stories: True if they tell of the same attack (or sirens, or statement) on the same place
        within the rules' times, False if they are of kinds kept apart (sirens and an attack; a statement naming
        several targets and an attack), None if the Gulf rule says nothing."""
        ma, mb = self.gulfs.get(a["id"]), self.gulfs.get(b["id"])
        if not ma or not mb:
            return None
        if a["id"] in self.gmain or b["id"] in self.gmain:
            return None                                # the main front: its own rules
        xs, ys = [x for x, _, _ in ma], [y for y, _, _ in mb]
        if any(gulf_apart(x, ys) for x in xs if x[0] != "claim" or _statement(x)) \
                or any(gulf_apart(y, xs) for y in ys if y[0] != "claim" or _statement(y)) \
                or not any(gulf_fit(x, y) for x in xs for y in ys):
            return False
        for x, xch, xt in ma:
            for y, ych, yt in mb:
                if xch and ych:
                    continue
                n = same_gulf(x, y)
                w = CHAN_FRESH if xch or ych else 0
                if n and (gulf_when(_since(b), a, n, y, x, w) or gulf_when(_since(a), b, n, x, y, w)):
                    return True
        return None

    def _ship_misfit(self, f, cid):
        """True if the report names a kind of ship, a flag or a name that fits none of the story's reports that name
        one (a container ship's report never joins a tanker's story)."""
        if not f.get("sid"):
            return False
        xs = self.sids.get(cid)
        return bool(xs) and not any(vessel.ships_fit(f["sid"], x) for x in xs)

    def _ship_matches(self, item, f):
        """Stories of the same incident at sea, beyond the usual time window: a report placing it at the same
        distance and bearing from the same point joins its story for a day after that story's latest report; a
        report about one ship in the same sea area that gives no place joins the one incident placed there, if there
        is exactly one, within six hours of its latest report giving the place and a day of its first."""
        out = []
        if f.get("ship"):
            for cid, marks in self.ships.items():
                c = self.byid.get(cid)
                if c and len(c["m"]) < 60 and abs(item["t"] - c["u"]) <= SHIP_KEEP \
                        and any(vessel.same(f["ship"], x) for x, _ in marks) and not self._kind_conflict(f, cid) \
                        and not self._ship_misfit(f, cid):
                    out.append((0.6, c))
        elif f.get("sgen"):
            cands = []
            for cid, marks in self.ships.items():
                c = self.byid.get(cid)
                first, latest = min(t for _, t in marks), max(t for _, t in marks)
                if c and len(c["m"]) < 60 and marks[0][0]["area"] == f["sgen"] and 0 <= item["t"] - first <= SHIP_KEEP \
                        and item["t"] - latest <= SHIP_FRESH and not self._kind_conflict(f, cid) \
                        and not self._ship_misfit(f, cid):
                    cands.append((c, marks))
            if cands and all(any(vessel.same(x, y) for x, _ in cands[0][1] for y, _ in mk) for _, mk in cands):
                out.append((0.45, max(cands, key=lambda x: len(x[0]["m"]))[0]))
        return out


    def _pull_matches(self, item, f):
        """The story of the same forces taken out of the same place (pullback.mark: whose, the country, the base, the
        round), whatever verb its reports use ("evacuated", "pulls", "moves … from", «فرار», «خارج کرد»), for PULL_KEEP
        after its latest report. The report's label must fit every label of the story; of several such stories, the
        latest."""
        x = f.get("pull")
        if not x:
            return []
        fit = []
        for cid, marks in self.pulls.items():
            c = self.byid.get(cid)
            if c and len(c["m"]) < 60 and abs(item["t"] - c["u"]) <= PULL_KEEP \
                    and all(pullback.fits(x, y) for y, _ in marks):
                fit.append(c)
        if not fit:
            return []
        return [(0.6, max(fit, key=lambda c: c["u"]))]

    def _kind_conflict(self, f, cid):
        """An Iranian statement about ships never joins a story of an incident told independently, nor the reverse;
        and at sea, a report whose time doesn't meet the story's never joins it."""
        st, inc = self.stmts.get(cid), self.incs.get(cid)
        if f.get("stmt") and inc and not st:
            return True
        if f.get("inc") and st and not inc:
            return True
        if f.get("when"):
            ws = [w for w, _ in (inc or [])] + [w for _, w, _ in (st or [])]
            ws = [w for w in ws if w]
            if ws and not any(vessel.overlap(f["when"], w) for w in ws):
                return True
        return False

    def _stmt_matches(self, item, f):
        """The story of the same Iranian statement (the same body, the same count, a super tanker, ships stopped),
        for twelve hours after that story's latest report."""
        out = []
        if not f.get("stmt"):
            return out
        for cid, sts in self.stmts.items():
            c = self.byid.get(cid)
            if not c or len(c["m"]) >= 60 or self._ship_misfit(f, cid) \
                    or (abs(item["t"] - c["u"]) > STMT_KEEP and not self._ev_late(item, f, c)):
                continue
            if any(vessel.same_statement(f["stmt"], x) and (not f.get("when") or not w or vessel.overlap(f["when"], w))
                   for x, w, _ in sts):
                out.append((0.6, c))
        return out

    def _same_matches(self, item, f):
        """The story of the same article published again (same headline, nearly the same text) or of the same
        deployment (the same count of the same forces to the same place), for a day after that story's latest report."""
        out = []
        for cid, t, su in self.dups.get(f.get("dup") or "", []):
            c = self.byid.get(cid)
            if c and len(c["m"]) < 60 and abs(item["t"] - c["u"]) <= DUP_KEEP and _same_text(f["dupsu"], su):
                out.append((0.9, c))
        for cid in self.deps.get(f.get("dep"), ()) if f.get("dep") else ():
            c = self.byid.get(cid)
            if c and len(c["m"]) < 60 and abs(item["t"] - c["u"]) <= DEP_KEEP:
                out.append((0.6, c))
        # the same order to leave a country (who, where, how far): outlets retell it for days
        for cid in self.evacs.get(f.get("evac"), ()) if f.get("evac") else ():
            c = self.byid.get(cid)
            if c and len(c["m"]) < 60 and abs(item["t"] - c["u"]) <= EVAC_KEEP:
                out.append((0.6, c))
        return out


SHIP_OWNER = 12 * 3600     # reports of one country's ship of one kind in one sea area this close are one incident
STMT_KEEP = 12 * 3600      # reports of the same Iranian statement join its story this long after its latest report
EVAC_KEEP = 7 * 86400      # reports of the same order to leave a country join its story this long after its latest report
DEP_KEEP = 24 * 3600       # reports of the same deployment join its story this long after its latest report
PULL_KEEP = 24 * 3600      # reports of the same forces taken out of the same place join its story this long after its latest
SHIP_KEEP = 24 * 3600      # reports placing an incident at sea at the same spot join its story this long after its latest
SHIP_FRESH = 6 * 3600      # a report about one ship that gives no place joins the one incident placed in that sea area
                           # this soon after its latest placed report


_SEA_PLACE = re.compile(r"\b(hormuz|persian gulf|gulf of oman|the gulf)\b", re.I)
_SEA_PLACE_FA = re.compile(fa_norm("هرمز|خلیج فارس|دریای عمان|تنگه"))


def _at_sea_vague(m):
    """An incident at sea, or an explosion or attack named only by the sea it was in ("Explosions in Hormuz")."""
    fl = m.get("flags") or []
    if "maritime_incident" in fl:
        return True
    if "kinetic" not in fl or channel(m):
        return False                        # a channel's "انفجار در هرمز" keeps the channels' own rules
    head = fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else (m.get("en_ti") or m.get("ti") or "")
    return bool((_SEA_PLACE_FA if m.get("lang") == "fa" else _SEA_PLACE).search(head)) \
        and not witness.cities_in(head, m.get("lang") or "en")


def _vague_at_sea(ms):
    if not any(_at_sea_vague(m) for m in ms):
        return False
    if any(vessel.statement(m) or vessel.mark(m) or vessel.when(m, fine=True) for m in ms):
        return False
    return len({(m.get("s") or "").split(":")[0] for m in ms}) < 2


_EVENT_EN = re.compile(r"\b(?:struck|strikes?|hit|attacked|attacks?|explod\w*|explosions?|blasts?|caught fire|ablaze|ablaze"
                       r"|downed|shot down|destroy\w*|seiz\w*|sank|sunk|intercept\w*|launch\w*|fired|killed)\b", re.I)
_EVENT_FA = re.compile(fa_norm("(?:منفجر|انفجار|اصابت|حمله|آتش گرفت|سرنگون|منهدم|توقیف|غرق|رهگیری|شلیک|پرتاب|کشته)"))
_JOIN_EN = re.compile(r"\s+(?:as|while|amid|meanwhile)\s+.*$", re.I)
_JOIN_FA = re.compile(fa_norm(r"\s*(?:همزمان با|در حالی که|در حالیکه|در بحبوحه).*$"))


def _joined_single(ms):
    """One outlet's headline that strings two happenings together and hangs a third thing on them ("Iran says enemy
    USV struck, violating tankers caught fire in Hormuz Strait as Qatari delegation visits Tehran"): a retelling,
    not the moment. A real event soon has many outlets."""
    if channel(ms[0]) or len({(m.get("s") or "").split(":")[0] for m in ms}) > 1:
        return False
    if any(vessel.mark(m) for m in ms):
        return False                        # a ship's report with an exact place
    m = ms[0]
    for t, join, ev, sep in ((m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or "", _JOIN_EN,
                              _EVENT_EN, r",\s+|\s+and\s+"),
                             (fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else "", _JOIN_FA, _EVENT_FA,
                              r"\s*[،,]\s*|\s+و\s+")):
        if not t or not join.search(t):
            continue                        # the headline also hangs something else on: "… as …"
        parts = [p for p in re.split(sep, join.sub("", t)) if len(p.split()) >= 2 and ev.search(p)]
        if len(parts) >= 2:
            return True
    return False


def _since(c):
    """When a story's time window starts: its first report, or for a story marked as ongoing by hand
    (c["ongoing"]) its latest one, so later reports of a long-running story keep joining it. Where the story sits
    in the feed and when it was first reported don't change: those go by its first report (c["t"])."""
    return c["u"] if c.get("ongoing") else c["t"]


def recluster(clusters, now_t, window=48 * 3600):
    """Rebuild the stories of the last `window` seconds from their reports with the current rules.
    Cluster ids are kept where a new story is mostly made of an old one's reports."""
    # stories put together by hand (c["manual"]) stay as they are; new reports can still join them
    old = [c for c in clusters if now_t - c["u"] > window or c.get("manual")]
    recent = [c for c in clusters if now_t - c["u"] <= window and not c.get("manual")]
    owner = {m["k"]: c["id"] for c in recent for m in c["m"]}
    extra = {c["id"]: {k: c[k] for k in ("img", "vid", "en", "fa", "alerted") if k in c} for c in recent}
    members = sorted((m for c in recent for m in c["m"]), key=lambda m: m["t"])
    cl = Clusterer(old)
    fresh = set()
    for m in members:
        c, new = cl.add(m)
        if new:
            fresh.add(c["id"])
    new = [c for c in cl.clusters if c["id"] in fresh]
    taken = {c["id"] for c in cl.clusters if c["id"] not in fresh}
    claims = []
    for c in new:
        votes = {}
        for m in c["m"]:
            oid = owner.get(m["k"])
            if oid:
                votes[oid] = votes.get(oid, 0) + 1
        for oid, n in votes.items():
            claims.append((n, oid, c))
    assigned = {}
    for n, oid, c in sorted(claims, key=lambda x: (-x[0], x[1])):
        if oid in taken or id(c) in assigned:
            continue
        assigned[id(c)] = oid
        taken.add(oid)
    sizes = {}
    for m in members:
        sizes[owner.get(m["k"])] = sizes.get(owner.get(m["k"]), 0) + 1
    for c in new:
        oid = assigned.get(id(c))
        if oid:
            c["id"] = oid
            same = len(c["m"]) == sizes.get(oid) and all(owner.get(m["k"]) == oid for m in c["m"])
            for k, v in extra.get(oid, {}).items():
                if k in ("en", "fa") and not same:
                    continue                         # the headline may belong to reports that moved away
                c.setdefault(k, v)
        else:
            base, i = c["id"], 0
            while c["id"] in taken:
                i += 1
                c["id"] = "c" + sha(base + str(i), 10)
            taken.add(c["id"])
        c.pop("en", None) if False else None
        refresh(c)
    return cl.clusters


def _pick(members, lang):
    def key(m):
        return (m.get("rel", 0.6) + (0.25 if m.get("su") else 0) + (0.1 if m.get("img") else 0)
                - (0.3 if m.get("via") == "gn" else 0) + m.get("sev", 20) / 200
                - (0.2 if len(m.get("ti", "")) > 160 else 0) - m["t"] / 1e12)
    pool = [m for m in members if m.get("lang") == lang]
    return max(pool, key=key) if pool else None


def refresh(c):
    """Recompute derived fields of a cluster after its membership changed."""
    ms = c["m"]
    srcs = {m["s"] for m in ms}
    c["ns"] = len(srcs)
    max_rel = max(m.get("rel", 0.6) for m in ms)
    # reports from outside the core theatre count at reduced weight, even inside a mixed story
    eff = [m.get("sev", 20) if is_core(m) else min(NONCORE_CAP, m.get("sev", 20) * NONCORE_FACTOR) for m in ms]
    chans = {m["s"] for m in ms if channel(m)}
    news = [m for m in ms if not channel(m)]
    claim = cluster_severity(eff, c["ns"], max_rel)     # what the reports claim, the channels' claims in full
    if news:
        # a news source has the story: it decides how serious it is, not the channels' own claims
        eff = [min(e, UNCONFIRMED_CAP) if channel(m) else e for e, m in zip(eff, ms)]
    c["sev"] = cluster_severity(eff, c["ns"], max_rel)
    top = ms[max(range(len(ms)), key=lambda i: eff[i])]
    if not set(top.get("flags", [])) & EVENT_FLAGS and not ("cyber_war" in top.get("flags", []) and max(eff) >= 70):
        # many outlets repeating a threat or a plan make it a big story, not a strike (a cyber attack on the main front
        # against something military or vital stays red: classify.cyber)
        c["sev"] = min(c["sev"], 69.0)
    if "secondary" in top.get("flags", []) or (any("secondary" in m.get("flags", []) for m in ms)
                                               and not any("side_major" in m.get("flags", []) for m in ms)
                                               and all(m.get("front") or e < 45
                                                       for e, m in zip(eff, ms))):
        # a side front's everyday report (Yemen and Saudi Arabia, Lebanon): many outlets repeating it don't make
        # it red, nor does one outlet's wording that the rules didn't place on that front
        c["sev"] = min(c["sev"], SECONDARY_CAP)
        claim = min(claim, SECONDARY_CAP)
    gk = [gulf_key(m) for m in ms]
    if len(ms) > 1 and any(gk) and not any(("side_major" in m.get("flags", []) and e >= 70) or gulf_main(m)
                                                     for e, m in zip(eff, ms)) \
            and all((g and "sa" in g[2]) or {"secondary", "side_minor"} & set(m.get("flags", [])) or e < 45
                    for g, e, m in zip(gk, eff, ms)):
        # missiles and drones on Saudi soil, or the sirens there, told by several outlets (joined by the Gulf rule,
        # GULF_WINDOW): orange at most, as the side-front rules have it, however many outlets tell it, unless one of
        # its reports is itself red (a big turn: a Saudi oil site hit…); a lone report keeps its own grade
        c["sev"] = min(c["sev"], SECONDARY_CAP)
        claim = min(claim, SECONDARY_CAP)
    if any("side_minor" in m.get("flags", []) for m in ms) and all("side_minor" in m.get("flags", [])
                                                                   or e <= MINOR_CAP for e, m in zip(eff, ms)):
        # a side front's everyday report (strikes inside Yemen, the daily strikes in Lebanon): yellow, however many
        # outlets tell it
        c["sev"] = min(c["sev"], MINOR_CAP)
        claim = min(claim, MINOR_CAP)
    if any({"judicial", "protest", "deesc_talk"} & set(m.get("flags", [])) for m in ms) and all(e < config.TIER_ORANGE for e in eff):
        # an execution or a verdict, a protest abroad, mediation "to prevent escalation": yellow, however many
        # outlets tell it
        c["sev"] = min(c["sev"], config.TIER_ORANGE - 1)
        claim = min(claim, config.TIER_ORANGE - 1)
    if c["ns"] == 1 and max_rel < CORROBORATE_BELOW:
        # a single less reliable outlet (state media, partisan or Telegram channels) can't make a red story
        # on its own; it turns red once another source reports it
        c["sev"] = min(c["sev"], 69.0)
        c["single"] = True
    else:
        c.pop("single", None)
    if all(other_war(m) for m in ms):
        c["sev"] = min(c["sev"], OTHER_WAR_CAP)
        claim = min(claim, OTHER_WAR_CAP)
    if all("sport" in m.get("flags", []) for m in ms):
        c["sev"] = min(c["sev"], SPORT_CAP)          # several outlets on a called-off match keep it yellow
        claim = min(claim, SPORT_CAP)
    if any("powers_soft" in m.get("flags", []) for m in ms) and \
            all("powers_soft" in m.get("flags", []) or m.get("sev", 20) < 45 for m in ms):
        # Putin and Iran on trade or gas: many outlets covering a visit don't make it an important story
        c["sev"] = min(c["sev"], UNCONFIRMED_CAP)
        claim = min(claim, UNCONFIRMED_CAP)
    ch_strike = any(channel(m) and strike(m) for m in ms)
    if not news and len(chans) < CONFIRM_CHANNELS and not c.get("verified"):
        # one Telegram channel alone: an unconfirmed report, red when it tells of a strike, yellow otherwise (a post
        # relaying a named outlet that really reported it is verified, see citation.py)
        c["sev"] = max(c["sev"], RED_FLOOR) if ch_strike else min(c["sev"], UNCONFIRMED_CAP)
        c["unconf"] = unconf_kind(ms)
        c["claim"] = round(claim, 1)                 # how serious the channel's claim would be if confirmed
    else:
        c.pop("unconf", None)
        c.pop("claim", None)
        if ch_strike and (not news or any(strike(m) for m in news)):
            c["sev"] = max(c["sev"], RED_FLOOR)      # a second channel or the news confirms the strike: still red
    if _vague_at_sea(ms):
        # an incident at sea told by one outlet only, with no time and no place: not red until a second outlet, a
        # time or a place makes sure it is new and not an incident told hours ago
        c["sev"] = min(c["sev"], 69.0)
    if any(blast(m) for m in ms) and not any(set(m.get("flags", [])) & {"controlled", "denial"} for m in ms):
        c["sev"] = max(c["sev"], RED_FLOOR)          # an explosion in Iran put down to gas stays red
    if any("cleric" in (m.get("flags") or []) for m in ms) and not any(
            set(m.get("flags") or []) & {"kinetic", "maritime_incident", "hormuz_closure", "nuclear_red"} for m in ms):
        c["sev"] = min(c["sev"], 40.0)               # a cleric's statement, however many outlets carry it: yellow
    if _joined_single(ms):
        c["sev"] = min(c["sev"], 40.0)               # one outlet tying two happenings together: yellow
    c["tier"] = tier(c["sev"])
    for f in ("topics", "flags", "ppl", "geo", "ctry"):
        acc = []
        for m in sorted(ms, key=lambda m: -m.get("sev", 0)):
            for x in m.get(f, []):
                if x not in acc:
                    acc.append(x)
        c[f] = acc[:8]
    c["core"] = is_core(c)
    lv = [trump_level(m) for m in news] if news and not c.get("unconf") else []
    if c["tier"] != "red" and lv and 2 * sum(x == 2 for x in lv) >= len(lv):
        # Trump's own words on the war's future with Iran (threats, attacks or war to come; at least half its news
        # reports): red in the bulletin; his other words on the conflict (talks, a deal, sanctions…) never yellow.
        # Only the colour: the severity, the index and the Telegram alerts (alerts.py leaves out `trump`) go by the
        # usual rules
        c["tier"] = "red"
        c["trump"] = 2
    elif c["tier"] == "yellow" and lv and 2 * sum(x >= 1 for x in lv) >= len(lv):
        c["tier"] = "orange"
        c["trump"] = 1
    else:
        c.pop("trump", None)
    # de-escalation (deesc.py): the green tag, and when a ceasefire or formal talks began, for the index
    for key, flag in (("cease_t", "ceasefire_on"), ("talks_t", "talks_held"), ("deny_t", "deesc_denial")):
        ts = [m["t"] for m in ms if flag in m.get("flags", []) and not channel(m)]
        if ts:
            c[key] = min(ts)
        else:
            c.pop(key, None)
    if any("deesc_sure" in m.get("flags", []) and not channel(m) for m in ms):
        c["green"] = True
    else:
        c.pop("green", None)
    en_rep = _pick(ms, "en")
    fa_native = [m for m in ms if m.get("lang") == "fa" and m.get("rel", 0) >= 0.8]
    fa_rep = _pick(fa_native, "fa") if fa_native else None
    if en_rep is None:
        en_rep = _pick(ms, "fa")
    if fa_rep is None and en_rep is not None and en_rep.get("lang") == "fa":
        fa_rep = en_rep
    c["en_from"] = en_rep["k"] if en_rep else None
    c["fa_from"] = fa_rep["k"] if fa_rep else None      # None -> translate English representative
    imgs = sorted([m for m in ms if m.get("img")], key=lambda m: -m.get("rel", 0))
    if imgs:
        c["img"] = imgs[0]["img"]
    vids = [m for m in ms if m.get("vid")]
    if vids:
        c["vid"] = vids[0]["vid"]
    return c


def prune(clusters, now):
    """Nothing older than a week is kept: stories last updated before that go, and so do the week-old reports of a
    story that is still running."""
    keep = []
    for c in clusters:
        if now - c["u"] > config.KEEP:
            continue
        ms = [m for m in c["m"] if now - m["t"] <= config.KEEP]
        if not ms:
            continue
        ms.sort(key=lambda m: m["t"])
        if len(ms) != len(c["m"]):
            c["m"] = ms
            c["t"] = ms[0]["t"]
            refresh(c)
        else:
            c["m"] = ms
        keep.append(c)
    return keep
