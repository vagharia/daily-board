"""Group reports of the same event into one story ("cluster")."""
import re

from . import config
from .classify import cluster_severity, tier
from .lexicon import COUNTRIES_RX, PEOPLE, PEOPLE_RX, PLACES, match_keys
from .sources import BY_ID
from .sport import CAP as SPORT_CAP
from .util import sha

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

ENTITY = set("""iran israel us trump hormuz tanker hezbollah houthi saudi qatar oman uae iraq yemen lebanon syria
gaza netanyahu khamenei irgc centcom pentagon nuclear iaea missile drone strike navy carrier bahrain kuwait
rubio vance bessent hegseth witkoff araghchi pezeshkian russia china europe jordan egypt turkey riyadh doha
dubai baghdad beirut damascus jerusalem hebron aramco opec brent oil embassy sanaa jeddah""".split())

# Stories outside the core theatre (Iran, the Persian Gulf states, Iraq, Yemen / Red Sea, Lebanon) are kept but
# toned down, so West Bank raids or Israeli domestic politics don't outrank the Iran-US-Israel confrontation.
CORE_CTRY = {"ir", "gulf", "yemen", "iraq", "lebanon"}
CORE_GEO = {"hormuz", "persian_gulf", "gulf_oman", "tehran", "isfahan", "natanz", "fordow", "bushehr", "bandar_abbas",
            "kharg", "tabriz", "shiraz", "chabahar", "baghdad", "erbil", "ain_asad", "sanaa", "hodeidah", "red_sea",
            "bab", "riyadh", "east_sa", "doha", "bahrain", "uae", "fujairah", "oman", "kuwait", "lebanon"}
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
# what only Telegram channels (not news organisations) report is an unconfirmed report: yellow at most and labelled
# so, until a news source reports the same story or CONFIRM_CHANNELS channels do; inside a story a news source has
# confirmed, the channels' own claims still count as unconfirmed (a news report of a gas explosion doesn't confirm a
# channel's claim of an assassination)
CONFIRM_CHANNELS = 3
UNCONFIRMED_CAP = 44.0
EVENT_FLAGS = {"kinetic", "maritime_incident", "hormuz_closure", "airspace", "evac", "deploy", "ultimatum", "nuclear_red",
               "alert", "kinetic_threat"}


def channel(m):
    """The report comes from a Telegram channel, not from a news organisation."""
    return BY_ID.get(m.get("s"), {}).get("kind") == "tg"


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


def tokens(title: str):
    t = LIVE_PREFIX.sub("", title or "").lower()
    t = re.sub(r"(\d),(\d{3})\b", r"\1\2", t)               # 1,500 -> 1500
    t = re.sub(r"[’'`]s\b", "", t)
    t = t.replace("u.s.", "us ").replace("u.k.", "uk ").replace("united states", "us").replace("united nations", "un")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    out = set()
    for w in t.split():
        w = SYN.get(w, w)
        if w in STOP or (len(w) < 3 and not w.isdigit() and w not in ("us", "uk", "un", "eu")):
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        w = SYN.get(w, _stem(w))
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


def features(m):
    title = m.get("en_ti") or ""
    return {"vars": variants(title), "cls": event_class(m), "geo": set(m.get("geo") or []),
            "ctry": set(m.get("ctry") or []), "ppl": set(m.get("ppl") or []), "spk": speaker(title),
            "nums": _numbers(title), "days": frozenset(d.lower() for d in _DAYS.findall(title)),
            "cite": frozenset(k for k, rx in _CITE.items() if rx.search(title))}


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
    ka, kb = KIND[a["cls"]], KIND[b["cls"]]
    if ka and kb and ka != kb:                      # what happened
        return False
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


def variants(title):
    """Token sets used for matching: the whole headline and, for "A / B" headlines, its first part alone."""
    full = tokens(title)
    head = _SUB.split(title or "", 1)[0]
    if head != (title or ""):
        h = tokens(head)
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
    old = [c for c in clusters if now_t - c["u"] > window]
    recent = [c for c in clusters if now_t - c["u"] <= window]
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
    if len(chans) < CONFIRM_CHANNELS:
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
    if all("sport" in m.get("flags", []) for m in ms):
        c["sev"] = min(c["sev"], SPORT_CAP)          # several outlets on a called-off match keep it yellow
    if len(chans) == len(srcs) and len(chans) < CONFIRM_CHANNELS:
        c["sev"] = min(c["sev"], UNCONFIRMED_CAP)    # only Telegram channels have it: an unconfirmed report
        c["unconf"] = True
    else:
        c.pop("unconf", None)
    c["tier"] = tier(c["sev"])
    for f in ("topics", "flags", "ppl", "geo", "ctry"):
        acc = []
        for m in sorted(ms, key=lambda m: -m.get("sev", 0)):
            for x in m.get(f, []):
                if x not in acc:
                    acc.append(x)
        c[f] = acc[:8]
    c["core"] = is_core(c)
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
    keep = [c for c in clusters if now - c["u"] <= config.KEEP]
    for c in keep:
        c["m"].sort(key=lambda m: m["t"])
    return keep
