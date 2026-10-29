"""Group reports of the same event into one story ("cluster")."""
import re

from . import config, witness
from .classify import cluster_severity, tier
from .classify_fa import _ANY, _B, R
from .lexicon import COUNTRIES_RX, PEOPLE, PEOPLE_RX, PLACES, match_keys
from .relevance import FA_CITY, FA_IRAN
from .sources import BY_ID
from .sport import CAP as SPORT_CAP
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
strait but all any some such very much many both each other only even own its also amid among whether
""".split())

# "Iran war live: …", "War in the Middle East: …", "Middle East crisis | …" — the prefix says nothing about the event
LIVE_PREFIX = re.compile(r"^\s*(?:[^:|–—]{0,40}\b(?:live|updates?|crisis|war|conflict|latest)\b[^:|–—]{0,20})\s*[:|–—]\s+",
                         re.I)

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
        "proposes": "offer", "proposed": "offer"}
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
               "alert", "kinetic_threat"}


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
    from .citation import cited                    # citation builds on this module
    if any(cited(m) for m in ms):
        return "cited"
    if any(strike(m) for m in ms):
        return "event"
    for m in ms:
        t = fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else (m.get("ti") or "")
        if (_QUOTE_FA if m.get("lang") == "fa" else _QUOTE_EN).search(t):
            return "quote"
    return "event"


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
    t = LIVE_PREFIX.sub("", title or "").lower()
    t = re.sub(r"(\d),(\d{3})\b", r"\1\2", t)               # 1,500 -> 1500
    t = re.sub(r"[’'`]s\b", "", t)
    t = t.replace("u.s.", "us ").replace("u.k.", "uk ").replace("united states", "us").replace("united nations", "un")
    if same:
        for a, b in _SAME_PHRASES:
            t = t.replace(a, b)
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
               ("V", {"evac"}), ("D", {"deploy"}), ("U", {"ultimatum"}), ("N", {"nuclear_red"}), ("S", {"sanctions"}),
               ("T", {"threat", "retaliation", "kinetic_threat", "talks_fail"})]
PHYSICAL = {"M", "K", "A", "V", "D"}            # something happened somewhere; anything else is said or decided
# the classifier can tag one outlet's report of an attack at sea as maritime and another's as kinetic, so these
# kinds count as the same "what"; "O" means the kind wasn't recognised, which needs even closer headlines
KIND = {"M": "attack", "K": "attack", "A": "attack", "V": "evac", "D": "deploy", "U": "threat", "T": "threat",
        "N": "nuclear", "S": "sanctions", "O": None}
WINDOW = {"event": 4 * 3600, "other": 10 * 3600}
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
    title = LIVE_PREFIX.sub("", title or "")
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
            "strike_ok": not set(m.get("flags") or []) & NOT_A_STRIKE}


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
    if not jac:
        return False
    if (ka is None) != (kb is None) and jac < 0.5:
        # one report's kind wasn't recognised: rare shared words are enough only if the other isn't an event,
        # so a reaction ("… condemn the attack on …") doesn't join the attack itself
        if not anchored or physical:
            return False
    if a["geo"] and b["geo"]:                       # where
        if not a["geo"] & b["geo"]:
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


class Clusterer:
    def __init__(self, clusters):
        self.clusters = clusters
        self.merged_away = set()
        self.byid = {c["id"]: c for c in clusters}
        self.index = {}
        self.tok = {}
        for c in clusters:
            self._index(c)

    def _index(self, c):
        feats = self.tok.setdefault(c["id"], {})
        for m in c["m"]:
            if m["k"] not in feats:
                feats[m["k"]] = features(m)
                for v in feats[m["k"]]["vars"]:
                    for w in v:
                        self.index.setdefault(w, set()).add(c["id"])

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
        it_tok = set().union(*f["vars"])
        rare = frozenset(w for w in it_tok if len(w) >= 4 and not w.isdigit() and self._rare(w, item["t"]))
        cand = {}
        for w in it_tok:
            for cid in self.index.get(w, ()):
                cand[cid] = cand.get(cid, 0) + 1
        ranked = []
        for cid, n in cand.items():
            c = self.byid.get(cid)
            if c and abs(item["t"] - c["t"]) <= WINDOW["other"]:
                ranked.append((n, cid))
        matches = []
        for _, cid in sorted(ranked, reverse=True)[:40]:
            c = self.byid.get(cid)
            if not c or len(c["m"]) >= 60:
                continue
            if any(m["k"] == item["k"] for m in c["m"]):
                return c, False
            feats = self.tok.get(cid, {})
            physical = f["cls"] in PHYSICAL or any(x["cls"] in PHYSICAL for x in feats.values())
            if abs(item["t"] - c["t"]) > WINDOW["event" if physical else "other"]:
                continue                                   # when: measured from the story's first report
            times = {m["k"]: m["t"] for m in c["m"]}
            score = max((same_story(f, mf, abs(item["t"] - times.get(k, c["t"])), rare) for k, mf in feats.items()),
                        default=0.0)
            if score:
                matches.append((score, c))
        matches.sort(key=lambda x: -x[0])
        best = matches[0][1] if matches else None
        for _, other in matches[1:]:
            # the report fits two stories: fold the smaller one in only if the two also match each other
            # directly (not merely through this report), remembering its id so its alert isn't sent twice
            if len(other["m"]) > 8 or len(best["m"]) + len(other["m"]) > 60:
                continue
            if best.get("manual") or other.get("manual"):
                continue                               # a story put together by hand is never folded either way
            tb, to = {m["k"]: m["t"] for m in best["m"]}, {m["k"]: m["t"] for m in other["m"]}
            fb, fo = self.tok.get(best["id"], {}), self.tok.get(other["id"], {})
            if not any(same_story(x, y, abs(to.get(kx, 0) - tb.get(ky, 0))) for kx, x in fo.items()
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
    if not set(top.get("flags", [])) & EVENT_FLAGS:
        # many outlets repeating a threat or a plan make it a big story, not a strike
        c["sev"] = min(c["sev"], 69.0)
    if "secondary" in top.get("flags", []):
        # its strongest report is a casualty count, a reaction or fighting inside Yemen: many outlets repeating it
        # don't make it red
        c["sev"] = min(c["sev"], 69.0)
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
    if any(blast(m) for m in ms) and not any(set(m.get("flags", [])) & {"controlled", "denial"} for m in ms):
        c["sev"] = max(c["sev"], RED_FLOOR)          # an explosion in Iran put down to gas stays red
    c["tier"] = tier(c["sev"])
    for f in ("topics", "flags", "ppl", "geo", "ctry"):
        acc = []
        for m in sorted(ms, key=lambda m: -m.get("sev", 0)):
            for x in m.get(f, []):
                if x not in acc:
                    acc.append(x)
        c[f] = acc[:8]
    c["core"] = is_core(c)
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
