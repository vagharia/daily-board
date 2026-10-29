"""Instant alerts from the main front: Iran's cities and islands, Hormuz and the waters around it, Israel and the
American bases of the region. Separate from the bulletin's stories and their colours, which these never change.

Every new report is read for signs of war at a place: (1) jets, drones or sirens heard, (2) air defence firing or
something intercepted or shot down, (3) missiles launched, (4) an explosion or an impact. What happens at one place
within half an hour is one incident, timed by the clock times citizen reports give, else by the report itself.
An incident is announced on Telegram at once, and again each time it reaches a higher step; the same step somewhere
else is a new incident and announced as well. A post of citizen reports counts when at least two messages come from
the same city, or messages from two cities. When a report of the incident comes from a news outlet (not a Telegram
channel) within half an hour of its first announcement, that confirmation is announced too, once.

The announcements are also kept as a list (state["log"]) for the bulletin."""
import html
import re

from . import witness
from .cluster import blast, channel
from .util import fa_norm

INCIDENT = 30 * 60          # one incident: the same place within half an hour
CONFIRM_WITHIN = 30 * 60    # a news outlet's report confirms it only this soon after the first announcement
KEEP = 48 * 3600            # incidents and the list are kept two days
TEHRAN = 12600

STEP_FA = {1: "صدا", 2: "پدافند", 3: "پرتاب موشک", 4: "انفجار"}

# places of the main front besides Iran's cities (witness.CITIES): key -> (Persian, English, Persian forms, English
# forms); the general names (Iran, Israel) only when nothing more precise is named
_FRONT = {
    "hormuz": ("تنگه هرمز", "the Strait of Hormuz", ["تنگه هرمز", "هرمز"], ["strait of hormuz", "hormuz"]),
    "persian_gulf": ("خلیج فارس", "the Persian Gulf", ["خلیج فارس"], ["persian gulf", "arabian gulf"]),
    "gulf_oman": ("دریای عمان", "the Gulf of Oman", ["دریای عمان"], ["gulf of oman"]),
    "tel_aviv": ("تل‌آویو", "Tel Aviv", ["تل آویو", "تلاویو"], ["tel aviv"]),
    "haifa": ("حیفا", "Haifa", ["حیفا"], ["haifa"]),
    "jerusalem": ("قدس", "Jerusalem", ["قدس", "اورشلیم", "بیت المقدس"], ["jerusalem"]),
    "dimona": ("دیمونا", "Dimona", ["دیمونا"], ["dimona"]),
    "eilat": ("ایلات", "Eilat", ["ایلات", "ام الرشراش"], ["eilat"]),
    "beersheba": ("بئرشبع", "Beersheba", ["بئرشبع", "بئر السبع"], ["beersheba", "beer sheva"]),
    "ashdod": ("اشدود", "Ashdod", ["اشدود"], ["ashdod"]),
    "ashkelon": ("عسقلان", "Ashkelon", ["عسقلان", "اشکلون"], ["ashkelon"]),
    "nevatim": ("نواتیم", "Nevatim", ["نواتیم"], ["nevatim"]),
    "north_israel": ("شمال اسرائیل", "northern Israel", ["شمال اسرائیل", "شمال سرزمین های اشغالی", "الجلیل"],
                     ["northern israel", "galilee"]),
    "al_udeid": ("پایگاه العدید", "Al Udeid base", ["العدید"], ["al udeid", "al-udeid"]),
    "al_dhafra": ("پایگاه الظفره", "Al Dhafra base", ["الظفره"], ["al dhafra", "al-dhafra"]),
    "ain_asad": ("پایگاه عین الاسد", "Ain al-Asad base", ["عین الاسد"], ["ain al-asad", "ain al asad"]),
    "fifth_fleet": ("مقر ناوگان پنجم آمریکا", "the US Fifth Fleet base", ["ناوگان پنجم"], ["fifth fleet"]),
}
_GENERAL = {"iran": ("ایران", "Iran", ["ایران"], ["iran"]), "israel": ("اسرائیل", "Israel", ["اسرائیل", "اسراییل",
            "سرزمین های اشغالی"], ["israel"])}
_L = r"ؠ-ۿ"


def _rx_fa(forms):
    return re.compile(rf"(?<![{_L}])(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in forms)
                      + rf")(?![{_L}])")


def _rx_en(forms):
    return re.compile(r"\b(?:" + "|".join(re.escape(x) for x in forms) + r")\b", re.I)


_FRONT_RX = [(k, _rx_fa(v[2]), _rx_en(v[3])) for k, v in _FRONT.items()]
_GENERAL_RX = [(k, _rx_fa(v[2]), _rx_en(v[3])) for k, v in _GENERAL.items()]
# another front named in the headline: not the main one, unless an Iranian city is named too
_OTHER_FA = re.compile(fa_norm("لبنان|بیروت|غزه|سوریه|دمشق|یمن|صنعا|حوثی|عراق|بغداد|اربیل|عربستان|ریاض|اردن|کرانه باختری"
                               "|اوکراین|روسیه|کی یف"))
_OTHER_EN = re.compile(r"\b(leban\w*|beirut|gaza|syria\w*|damascus|yemen\w*|sanaa|houthis?|iraq\w*|baghdad|erbil|saudi"
                       r"|riyadh|jordan\w*|west bank|ukrain\w*|russia\w*|kyiv)\b", re.I)

# the steps, strongest first; each with the words that tell it (Persian and English headlines)
_STEPS = [
    (4, "blast", fa_norm("انفجار|منفجر|اصابت|صدای مهیب|موج انفجار"),
     r"\b(explosions?|blasts?|exploded|impacts?|struck|hit by|detonations?)\b"),
    (3, "launch", fa_norm("پرتاب موشک|شلیک موشک|موشک ها شلیک|موشک ها پرتاب|موشک پرتاب|موشک شلیک|پرتاب شد|شلیک شد"),
     r"\b(launch(ed|es|ing)?|fires?|fired|firing)\b[^.;]{0,25}\bmissiles?\b|\bmissiles?\b[^.;]{0,20}\b(launch(ed|es)?"
     r"|fired)\b|\bmissile launch(es)?\b"),
    (2, "airdef", fa_norm("پدافند|ضدهوایی|ضد هوایی|رهگیری|رهگیر|منهدم|سرنگون"),
     r"\b(air defen[cs]es?|anti-aircraft|intercept\w*|shot down|shoots? down|downed)\b"),
    (1, "jet", fa_norm("جنگنده|جت|هواپیمای نظامی|دیوار صوتی"), r"\b(fighter jets?|warplanes?|jets?|sonic boom)\b"),
    (1, "drone", fa_norm("پهپاد|ریزپرنده"), r"\b(drones?|uavs?)\b"),
    (1, "siren", fa_norm("آژیر|اژیر"), r"\bsirens?\b"),
]
_STEPS = [(n, k, re.compile(fa), re.compile(en, re.I)) for n, k, fa, en in _STEPS]
_WIT_STEP = {"blast": 4, "launch": 3, "airdef": 2, "jet": 1, "drone": 1, "siren": 1}
# a report that is not of something happening now
_NOT_NOW = {"denial", "controlled", "past", "speculative", "threat", "analysis", "opinion", "reaction", "verbal",
            "civil_drill", "exercise", "sport", "local_toll", "earnings", "piracy", "far_off"}
_FROM_FA = re.compile(fa_norm("از"))
# not news of something happening now: a court case, an anniversary, figures for a month, a feature
_NOT_NOW_FA = re.compile(fa_norm("کیفرخواست|دادگاه|محاکمه|سالگرد|رکورد|آمار|تحلیل|گزارش ویژه|مستند|سال گذشته"))
_NOT_NOW_EN = re.compile(r"\b(indictment|trial|court|anniversary|record high|record low|statistics|figures|analyst|analysis"
                         r"|explainer|last year|in october|in september|this month|this year)\b", re.I)
# a statement ("Iran FM: …", "… says"): the general names (Iran, Israel) don't make it news of a place
_SAID_FA = re.compile(r"^[^:：]{2,45}[:：]|" + fa_norm("گفت|اعلام کرد|مدعی شد|ادعا"))
_SAID_EN = re.compile(r"^[^:]{2,45}:|\b(says?|said|claims?|claimed|told)\b", re.I)


def _name(key, lang):
    v = witness.CITIES.get(key) or _FRONT.get(key) or _GENERAL.get(key)
    return v[0] if lang == "fa" else v[1]


def _places(fa_t, en_t):
    """Main-front places a headline names: Iranian cities and the front's places; Iran or Israel only if nothing
    more precise is named and it isn't a statement. None if it names another front (Iraq, Lebanon, Yemen…)."""
    if (fa_t and _OTHER_FA.search(fa_t)) or (en_t and _OTHER_EN.search(en_t)):
        return set()                        # "Tehran strikes a Kurdish base in Iraq": another front
    cities = witness.cities_in(fa_t, "fa") | witness.cities_in(en_t, "en")
    front = {k for k, rf, re_ in _FRONT_RX if (fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t))}
    out = cities | front
    if "hormuz" in out and "hormuz_island" in out:
        out.discard("hormuz")
    if not out and not ((fa_t and _SAID_FA.search(fa_t)) or (en_t and _SAID_EN.search(en_t))):
        out = {k for k, rf, re_ in _GENERAL_RX if (fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t))}
    return out


def _step(fa_t, en_t):
    for n, k, rf, re_ in _STEPS:
        if (fa_t and rf.search(fa_t)) or (en_t and re_.search(en_t)):
            return n, k
    return 0, None


def _clock(t):
    import time as _t
    return _t.strftime("%H:%M", _t.gmtime(t + TEHRAN))


def _fa_digits(s):
    return s.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _wit_time(m):
    """The latest clock time a post of citizen reports gives, as a moment at or before the post; else the post's."""
    t = m["t"]
    hm = (m.get("wit") or {}).get("times") or []
    if not hm:
        return t
    day = (t + TEHRAN) // 86400 * 86400 - TEHRAN
    best = None
    for x in hm:
        e = day + int(x[:2]) * 3600 + int(x[3:]) * 60
        if e > t + 600:
            e -= 86400
        if 0 <= t - e <= 6 * 3600:
            best = e if best is None else max(best, e)
    return best or t


def _title(kind, step, place, lang, wit, frm):
    p = _name(place, lang)
    if lang == "fa":
        return {"blast": ("شنیده شدن صدای انفجار در " if wit else "انفجار در ") + p,
                "launch": ("پرتاب موشک از " if frm else "پرتاب موشک در ") + p,
                "airdef": "شلیک پدافند در " + p, "jet": "صدای جنگنده در " + p, "drone": "صدای پهپاد در " + p,
                "siren": "صدای آژیر در " + p}[kind]
    return {"blast": ("Explosion heard in " if wit else "Explosion in ") + p,
            "launch": ("Missiles launched from " if frm else "Missile launch in ") + p,
            "airdef": "Air defence fire in " + p, "jet": "Jets heard over " + p, "drone": "Drones heard over " + p,
            "siren": "Sirens in " + p}[kind]


def events(m):
    """Signs of war at main-front places in one report: [{place, step, kind, t, fa, en}]."""
    flags = set(m.get("flags") or [])
    w = m.get("wit")
    out = []
    if w:
        if w.get("official"):
            return []
        cities = w.get("cities") or {}
        if not (max(cities.values(), default=0) >= 2 or len(cities) >= 2):
            return []                       # one message alone waits for a second
        t = _wit_time(m)
        for c, kinds in (w.get("ck") or {c: list(w.get("kinds") or {}) for c in cities}).items():
            best = max(kinds, key=lambda k: _WIT_STEP.get(k, 0), default=None)
            if best:
                out.append({"place": c, "step": _WIT_STEP[best], "kind": best, "t": t,
                            "fa": _title(best, _WIT_STEP[best], c, "fa", True, False),
                            "en": _title(best, _WIT_STEP[best], c, "en", True, False)})
        return out
    if flags & _NOT_NOW or not flags & {"kinetic", "maritime_incident", "airspace"} or blast(m):
        return []
    fa_t = fa_norm(m.get("ti") or "") if m.get("lang") == "fa" else ""
    en_t = m.get("en_ti") or (m.get("ti") if m.get("lang") != "fa" else "") or ""
    if (fa_t and _NOT_NOW_FA.search(fa_t)) or (en_t and _NOT_NOW_EN.search(en_t)):
        return []
    step, kind = _step(fa_t, en_t)
    if not step:
        return []
    places = _places(fa_t, en_t)
    if places == {"iran", "israel"}:
        # "Iran fires missiles at Israel": one event, from the one named first towards the other
        txt = fa_t or en_t.lower()
        names = {k: txt.find(fa_norm(_GENERAL[k][0]) if fa_t else k) for k in places}
        a, b = sorted(places, key=lambda k: names[k] if names[k] >= 0 else 1e9)
        for k in places:                    # "… launched from Iran": the origin is named after "from"
            if re.search((r"\bfrom\s+" + k) if not fa_t else (fa_norm("از") + r"\s*" + fa_norm(_GENERAL[k][0])), txt):
                a, b = k, ({"iran", "israel"} - {k}).pop()
        fa_k = {"blast": "انفجار", "launch": "پرتاب موشک", "airdef": "رهگیری", "jet": "پرواز جنگنده",
                "drone": "پرتاب پهپاد", "siren": "آژیر"}[kind]
        en_k = {"blast": "Explosions", "launch": "Missiles launched", "airdef": "Interceptions", "jet": "Jets",
                "drone": "Drones launched", "siren": "Sirens"}[kind]
        return [{"place": a, "step": step, "kind": kind, "t": m["t"],
                 "fa": f"{fa_k} از {_name(a, 'fa')} به سمت {_name(b, 'fa')}",
                 "en": f"{en_k} from {_name(a, 'en')} towards {_name(b, 'en')}"}]
    if places & set(witness.CITIES):
        places &= set(witness.CITIES)       # "missiles from Sirik towards Hormuz": the city is the place
    for p in places:
        frm = bool(fa_t and re.search(_FROM_FA.pattern + r"\s*(?:جزیره\s*)?" + re.escape(fa_norm(_name(p, "fa"))), fa_t)) \
            or bool(en_t and re.search(r"\bfrom\b[^.;]{0,15}" + re.escape(_name(p, "en")), en_t, re.I))
        out.append({"place": p, "step": step, "kind": kind, "t": m["t"], "fa": _title(kind, step, p, "fa", False, frm),
                    "en": _title(kind, step, p, "en", False, frm)})
    return out


def _message(ev, m, kind_of_alert):
    """kind_of_alert: 'new', 'up' (a higher step) or 'ok' (confirmed by a news outlet)."""
    src = html.escape(m.get("sn_fa") or m.get("sn") or "")
    at = _fa_digits(_clock(ev["t"]))
    head = {"new": "🔴" if ev["step"] >= 3 else "🟠", "up": "⬆️", "ok": "✅"}[kind_of_alert]
    title = html.escape(ev["fa"])
    if kind_of_alert == "ok":
        return f"✅ <b>تأیید شد: {title}</b>، {at}\n<i>{src}</i>"
    if m.get("wit"):
        n = sum((m["wit"].get("cities") or {}).values())
        tail = f"گزارش‌های مردمی ({_fa_digits(str(n))} پیام)، {src}"
    elif channel(m):
        tail = f"{src} · ⚠️ تأییدنشده"
    else:
        tail = src
    return f"{head} <b>{title}</b>، {at}\n<i>{tail}</i>"


def process(state, items, now_t, story_start=None, quiet=False):
    """Read this round's new reports. story_start: report key -> when its story was first reported; a report that
    joins a story more than half an hour old tells of something already known (a later account, a recap) and is
    left out. Returns (Telegram messages, keys of the reports that are signs of war at the main front: their stories
    don't also get the usual red-story alert)."""
    story_start = story_start or {}
    inc = state.setdefault("inc", {})
    log_ = state.setdefault("log", [])
    for p in list(inc):
        if now_t - inc[p]["t1"] > KEEP:
            inc.pop(p)
    state["log"] = log_ = [x for x in log_ if now_t - x["t"] <= KEEP]
    seen = state.setdefault("keys", {})
    for k in [k for k, t in seen.items() if now_t - t > KEEP]:
        seen.pop(k)
    msgs, keys = [], set()
    for m in sorted(items, key=lambda m: m["t"]):
        if m["t"] - story_start.get(m["k"], m["t"]) > INCIDENT:
            continue
        evs = events(m)
        if not evs:
            continue
        keys.add(m["k"])
        seen[m["k"]] = now_t
        news = not channel(m)
        for ev in evs:
            p, t = ev["place"], ev["t"]
            cur = inc.get(p)
            if cur and -INCIDENT <= t - cur["t1"] <= INCIDENT:
                cur["t1"] = max(cur["t1"], t)
                if ev["step"] > cur["step"]:
                    cur["step"] = ev["step"]
                    msgs.append(_message(ev, m, "up"))
                    log_.append({"t": t, "p": p, "s": ev["step"], "fa": ev["fa"], "en": ev["en"], "src": m["s"],
                                 "conf": int(news or cur["conf"])})
                if news and not cur["conf"]:
                    cur["conf"] = 1
                    if now_t - cur["a"] <= CONFIRM_WITHIN:
                        msgs.append(_message(ev, m, "ok"))
                    for x in log_:
                        if x["p"] == p and x["t"] >= cur["t0"]:
                            x["conf"] = 1
            else:
                inc[p] = {"t0": t, "t1": t, "step": ev["step"], "conf": int(news), "a": now_t}
                msgs.append(_message(ev, m, "new"))
                log_.append({"t": t, "p": p, "s": ev["step"], "fa": ev["fa"], "en": ev["en"], "src": m["s"],
                             "conf": int(news)})
    log_.sort(key=lambda x: x["t"])
    return ([] if quiet else msgs), keys


_KIND_NOUN_FA = {"blast": "انفجار", "launch": "پرتاب موشک", "airdef": "شلیک پدافند", "jet": "صدای جنگنده",
                 "drone": "صدای پهپاد", "siren": "آژیر"}
_KIND_NOUN_EN = {"blast": "explosions", "launch": "missile launches", "airdef": "air defence fire", "jet": "jets",
                 "drone": "drones", "siren": "sirens"}


def story_texts(c):
    """For a main-front story told only by Telegram channels (citizen reports among them): a headline and a summary
    made of all its reports, strongest first ("گزارش‌های تأییدنشده از پرتاب موشک و انفجار در قشم، ۲۲:۴۸ تا ۲۳:۴۴"),
    or None. Once a news outlet reports it, the story takes that outlet's headline as usual."""
    ms = sorted(c["m"], key=lambda m: m["t"])
    if len(ms) < 2 or not all(channel(m) for m in ms):
        return None
    evs = [(e, m) for m in ms for e in events(m)]
    if not evs:
        return None
    kinds = sorted({e["kind"] for e, _ in evs}, key=lambda k: -max(e["step"] for e, _ in evs if e["kind"] == k))
    places = []
    for e, _ in evs:
        if e["place"] not in places:
            places.append(e["place"])
    lo, hi = min(e["t"] for e, _ in evs), max(e["t"] for e, _ in evs)
    def when(fa):
        a, b = _clock(lo), _clock(hi)
        if a == b:
            return f"، ساعت {_fa_digits(a)}" if fa else f", {a} Tehran time"
        return f"، {_fa_digits(a)} تا {_fa_digits(b)}" if fa else f", {a} to {b} Tehran time"
    def join(xs, fa):
        if len(xs) <= 1:
            return "".join(xs)
        return ("، ".join(xs[:-1]) + " و " + xs[-1]) if fa else (", ".join(xs[:-1]) + " and " + xs[-1])
    fa_places = [_name(p, "fa") for p in places[:3]] + (["چند جای دیگر"] if len(places) > 3 else [])
    en_places = [_name(p, "en") for p in places[:3]] + (["other places"] if len(places) > 3 else [])
    fa_ti = (f"گزارش‌های تأییدنشده از {join([_KIND_NOUN_FA[k] for k in kinds], True)} در {join(fa_places, True)}"
             + when(True))
    en_ti = (f"Unconfirmed reports of {join([_KIND_NOUN_EN[k] for k in kinds], False)} in {join(en_places, False)}"
             + when(False))
    chans = []
    for m in ms:
        n = m.get("sn_fa") or m.get("sn") or m["s"]
        if n not in chans:
            chans.append(n)
    parts_fa, parts_en, done = [], [], set()
    for e, m in sorted(evs, key=lambda x: x[0]["t"]):
        if (e["kind"], e["place"]) in done:
            continue
        done.add((e["kind"], e["place"]))
        src = m.get("sn_fa") or m.get("sn") or m["s"]
        parts_fa.append(f"{e['fa']} ({'گزارش‌های مردمی، ' if m.get('wit') else ''}{src}، {_fa_digits(_clock(e['t']))})")
        parts_en.append(f"{e['en']} ({'reports from residents, ' if m.get('wit') else ''}{m.get('sn') or m['s']}, "
                        f"{_clock(e['t'])})")
    n = len(chans)
    fa_su = (f"{_fa_digits(str(n))} کانال تلگرامی: " + "؛ ".join(parts_fa) + ". هنوز هیچ رسانه‌ای گزارشش نکرده.")
    en_su = (f"{n} Telegram channel{'s' if n != 1 else ''}: " + "; ".join(parts_en)
             + ". No news outlet has reported it yet.")
    return {"fa": {"ti": fa_ti, "su": fa_su}, "en": {"ti": en_ti, "su": en_su}}
