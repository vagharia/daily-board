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
""".split())

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


def is_core(c):
    return bool(set(c.get("ctry", [])) & CORE_CTRY or set(c.get("geo", [])) & CORE_GEO
                or set(c.get("flags", [])) & CORE_FLAGS or set(c.get("ppl", [])) & CORE_PPL)


def tokens(title: str):
    t = (title or "").lower()
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
        out.add(w)
    return out


def similar(a, b):
    if not a or not b:
        return False
    inter = a & b
    n = len(inter)
    if n < 2:
        return False
    jac = n / len(a | b)
    ovl = n / min(len(a), len(b))
    has_entity = bool(inter & ENTITY) or any(x.isdigit() for x in inter)
    if not has_entity:
        return jac >= 0.6 and n >= 4
    return (ovl >= 0.6 and jac >= 0.3 and n >= 3) or (jac >= 0.5 and n >= 2) or (ovl >= 0.75 and n >= 3)


class Clusterer:
    def __init__(self, clusters):
        self.clusters = clusters
        self.byid = {c["id"]: c for c in clusters}
        self.index = {}
        self.tok = {}
        for c in clusters:
            self._index(c)

    def _index(self, c):
        toks = set()
        for m in c["m"][:6]:
            toks |= tokens(m.get("en_ti") or "")
        self.tok[c["id"]] = [tokens(m.get("en_ti") or "") for m in c["m"][:6]]
        for w in toks:
            self.index.setdefault(w, set()).add(c["id"])

    def add(self, item):
        """Attach the item to an existing cluster or start a new one. Returns (cluster, is_new_cluster)."""
        it_tok = tokens(item.get("en_ti") or "")
        cand = {}
        for w in it_tok:
            for cid in self.index.get(w, ()):
                cand[cid] = cand.get(cid, 0) + 1
        best = None
        for cid, _ in sorted(cand.items(), key=lambda kv: -kv[1])[:40]:
            c = self.byid.get(cid)
            if not c or abs(item["t"] - c["u"]) > 20 * 3600 or len(c["m"]) >= 60:
                continue
            if any(m["k"] == item["k"] for m in c["m"]):
                return c, False
            if any(similar(it_tok, mt) for mt in self.tok.get(cid, [])):
                best = c
                break
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


def _pick(members, lang):
    def key(m):
        return (m.get("rel", 0.6) + (0.25 if m.get("su") else 0) + (0.1 if m.get("img") else 0)
                - (0.3 if m.get("via") == "gn" else 0) - m["t"] / 1e12)
    pool = [m for m in members if m.get("lang") == lang]
    return max(pool, key=key) if pool else None


def refresh(c):
    """Recompute derived fields of a cluster after its membership changed."""
    ms = c["m"]
    srcs = {m["s"] for m in ms}
    c["ns"] = len(srcs)
    max_rel = max(m.get("rel", 0.6) for m in ms)
    c["sev"] = cluster_severity([m.get("sev", 20) for m in ms], c["ns"], max_rel)
    c["tier"] = tier(c["sev"])
    for f in ("topics", "flags", "ppl", "geo", "ctry"):
        acc = []
        for m in sorted(ms, key=lambda m: -m.get("sev", 0)):
            for x in m.get(f, []):
                if x not in acc:
                    acc.append(x)
        c[f] = acc[:8]
    c["core"] = is_core(c)
    if not c["core"]:
        c["sev"] = round(min(NONCORE_CAP, c["sev"] * NONCORE_FACTOR), 1)
        c["tier"] = tier(c["sev"])
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
