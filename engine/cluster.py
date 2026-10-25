"""Group reports of the same event into one story ("cluster")."""
import re

from . import config
from .classify import cluster_severity, tier
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
strait""".split())

# reports of an event (an attack, an explosion, a seizure…) only join stories about an event, and statements only
# join statements, unless the headlines are very close
EVENT = {"kinetic", "maritime_incident", "hormuz_closure", "airspace", "evac", "deploy", "ultimatum", "nuclear_red"}

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
CORE_FLAGS = {"oil_spike", "maritime_incident", "hormuz_closure", "airspace", "nuclear_red"}
CORE_PPL = {"ir_leader", "ir_pres", "ir_fm", "ir_snsc", "irgc_cmd", "ir_army", "ghalibaf", "ir_spox", "houthi_l",
            "hzb_l", "grossi", "mbs", "sa_fm", "qa", "om", "uae"}
NONCORE_FACTOR, NONCORE_CAP = 0.6, 55.0
CORROBORATE_BELOW = 0.75
EVENT_FLAGS = {"kinetic", "maritime_incident", "hormuz_closure", "airspace", "evac", "deploy", "ultimatum", "nuclear_red",
               "alert", "kinetic_threat"}


def is_core(c):
    return bool(set(c.get("ctry", [])) & CORE_CTRY or set(c.get("geo", [])) & CORE_GEO
                or set(c.get("flags", [])) & CORE_FLAGS or set(c.get("ppl", [])) & CORE_PPL)


def _stem(w):
    if len(w) > 6 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 5 and w.endswith("ed") and not w.endswith("eed"):
        return w[:-2]
    return w


def tokens(title: str):
    t = LIVE_PREFIX.sub("", title or "").lower()
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


def similar(a, b, same_kind=True, events=False):
    if not a or not b:
        return False
    inter = a & b
    n = len(inter)
    if n < 2:
        return False
    jac = n / len(a | b)
    ovl = n / min(len(a), len(b))
    if not same_kind:
        return jac >= 0.5 and n >= 3
    has_entity = bool(inter & ENTITY) or any(x.isdigit() for x in inter)
    if not has_entity:
        return jac >= 0.6 and n >= 4
    return (ovl >= 0.6 and jac >= 0.3 and n >= 3) or (jac >= 0.5 and n >= 2) or (ovl >= 0.75 and n >= 3 and jac >= 0.25) \
        or (n >= 4 and ovl >= 0.55 and jac >= 0.3) \
        or (ovl == 1.0 and jac >= (0.18 if events else 0.25))           # a short headline fully inside a longer one


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


def is_event(m):
    return bool(set(m.get("flags") or []) & EVENT)


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
        toks = set()
        for m in c["m"][:6]:
            toks |= tokens(m.get("en_ti") or "")
        self.tok[c["id"]] = [(variants(m.get("en_ti") or ""), is_event(m)) for m in c["m"][:6]]
        for w in toks:
            self.index.setdefault(w, set()).add(c["id"])

    def add(self, item):
        """Attach the item to an existing cluster or start a new one. Returns (cluster, is_new_cluster)."""
        it_vars = variants(item.get("en_ti") or "")
        it_tok = set().union(*it_vars)
        it_ev = is_event(item)
        cand = {}
        for w in it_tok:
            for cid in self.index.get(w, ()):
                cand[cid] = cand.get(cid, 0) + 1
        matches = []
        for cid, _ in sorted(cand.items(), key=lambda kv: -kv[1])[:40]:
            c = self.byid.get(cid)
            if not c or abs(item["t"] - c["u"]) > (6 if it_ev else 20) * 3600 or len(c["m"]) >= 60:
                continue
            if any(m["k"] == item["k"] for m in c["m"]):
                return c, False
            if any(similar(x, y, ev == it_ev, ev and it_ev)
                   for mv, ev in self.tok.get(cid, []) for x in it_vars for y in mv):
                matches.append(c)
        best = matches[0] if matches else None
        for other in matches[1:]:
            # the report bridges two stories that are really one (e.g. a short and a long headline about the
            # same explosion): fold the smaller one in, remembering its id so its alert isn't sent twice
            if len(other["m"]) > 8 or len(best["m"]) + len(other["m"]) > 60:
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
    c["sev"] = cluster_severity(eff, c["ns"], max_rel)
    top = ms[max(range(len(ms)), key=lambda i: eff[i])]
    if not set(top.get("flags", [])) & EVENT_FLAGS:
        # many outlets repeating a threat or a plan make it a big story, not a strike
        c["sev"] = min(c["sev"], 69.0)
    if c["ns"] == 1 and max_rel < CORROBORATE_BELOW:
        # a single less reliable outlet (state media, partisan or Telegram channels) can't make a red story
        # on its own; it turns red once another source reports it
        c["sev"] = min(c["sev"], 69.0)
        c["single"] = True
    else:
        c.pop("single", None)
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
