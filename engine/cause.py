"""The announced cause of an explosion or a sound: a report that tells why a blast was heard, and the cause is not the
war ("صدای انفجار در بوشهر مربوط به یک طرح سینمایی است", "explosions heard in … are part of a military drill").

which() reads a headline and the start of its text and gives the kind of cause, or None. It needs both an explosion
or a sound and a cause: a film shoot or special effects, fireworks, a drill, the disposal of munitions, blasting at a
mine or quarry, an accident (gas, a transformer). The blast and its cause are read in one sentence.

Used by the bulletin (classify.py: such a report is a controlled detonation, yellow and never an event, except for
an accident, which mishap.py reads) and by the main-front panel (flash.py → `explain`): an explosion channels or
residents reported at the same place within a few hours is labelled with the cause as announced, «علت اعلامی», not
"confirmed"; it is what an official or an outlet says, not a judgement of ours."""
import re

from .util import first_sentences, fa_norm

# kind -> (Persian, English) for the label
NAMES = {
    "film": ("فیلم‌برداری سینمایی", "a film shoot"),
    "fireworks": ("آتش‌بازی", "fireworks"),
    "drill": ("رزمایش یا تمرین", "a drill"),
    "ordnance": ("انفجار کنترل‌شده", "a controlled detonation"),
    "mine": ("انفجار در معدن", "mine blasting"),
    "accident": ("حادثه", "an accident"),
}
# kinds that make a report a controlled detonation in the bulletin; an accident is mishap.py's
CONTROLLED_KINDS = {"film", "fireworks", "drill", "ordnance", "mine"}

_L = r"ؠ-ۿ"


def _fa(*terms):
    return re.compile(rf"(?<![{_L}])(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*") for x in terms) + ")")


_BLAST_FA = re.compile(_fa("انفجار", "صدای", "صداهای", "جلوه انفجاری").pattern + rf"|(?<![{_L}])منفجر(?![{_L}])")
_BLAST_EN = re.compile(r"\b(explosions?|blasts?|bangs?|booms?|detonations?|sounds?|noises?|loud)\b", re.I)
# the cause, strongest words first; some only after "مربوط به / ناشی از / به دلیل…" (a drill, a gas leak), since alone
# they may be the war itself ("حمله به رزمایش", "نشت گاز پس از حمله")
_FA = [
    # not "سینمایی" alone («عملیات سینمایی» praises a strike) nor "فیلم‌برداری" alone (someone filmed the blast)
    ("film", _fa("فیلم سینمایی", "طرح سینمایی", "پروژه سینمایی", "انفجارهای سینمایی", "انفجار سینمایی",
                 "جلوه های ویژه", "جلوه ویژه", "جلوه های انفجاری", "جلوه انفجاری", "تولید فیلم", "ساخت فیلم",
                 "تولید سریال")),
    ("fireworks", _fa("آتش بازی", "اتش بازی", "ترقه")),
    ("ordnance", _fa("انفجار کنترل شده", "انفجارهای کنترل شده", "انهدام کنترل شده", "انهدام مهمات", "امحای مهمات",
                     "امحا مهمات", "معدوم سازی مهمات", "به صورت کنترل شده")),
]
_MINE_FA = _fa("معدن", "معادن")
_MINE_EN = re.compile(r"\b(mines?|quarry|quarries)\b", re.I)
_WHY_FA = _fa("مربوط به", "ناشی از", "به دلیل", "به علت", "به خاطر", "بخاطر", "در جریان", "در پی", "علت")
# the war itself near the cause («به دلیل اصابت موشک به لوله گاز»): no cause of ours
_WAR_FA = _fa("حمله", "حملات", "موشک", "پهپاد", "اصابت", "بمباران", "پدافند", "جنگنده", "دشمن", "اسرائیل", "آمریکا",
              "صهیونیست", "تجاوز")
_WAR_EN = re.compile(r"\b(attack\w*|strikes?|struck|missiles?|drones?|rockets?|air ?raids?|bomb\w*|enemy|israel\w*"
                     r"|u\.s\.|american?)\b", re.I)
_AFTER_FA = [
    ("film", _fa("فیلم برداری", "فیلمبرداری", "فیلم", "سریال")),
    ("drill", _fa("رزمایش", "مانور", "تمرین")),
    ("mine", _fa("معدن", "معادن", "سنگ شکن", "عملیات معدنی", "عملیات عمرانی", "تخریب ساختمان", "راهسازی")),
    ("accident", _fa("نشت گاز", "انفجار گاز", "کپسول", "مخزن گاز", "لوله گاز", "گاز شهری", "ترکیدن", "ترکیدگی",
                     "ترانس", "پست برق", "اتصال برق", "اتصالی")),
]
_EN = [
    ("film", re.compile(r"\b(film(ing)? (shoot|set|crew|production)|movie (shoot|set|production|project)|shooting of (a|the) "
                        r"(film|movie)|special effects|cinematic (explosions?|blasts?|effects)|(film|movie) project)\b", re.I)),
    ("fireworks", re.compile(r"\bfireworks?\b", re.I)),
    ("ordnance", re.compile(r"\b(controlled (explosions?|detonations?|blasts?)|bomb disposal"
                            r"|(munitions?|ordnance|ammunition) (clearance|disposal|destruction))\b", re.I)),
    ("drill", re.compile(r"\b(part of|due to|during|because of|caused by|from|related to)\b[^.;]{0,30}\b(drills?|exercises?"
                         r"|manoeuvres?|maneuvers?)\b", re.I)),
    ("mine", re.compile(r"\b(quarry|mining (operations?|works?)|construction (blasting|works?)|demolition works?)\b", re.I)),
    ("accident", re.compile(r"\b(gas (leak|cylinder|canister|explosion)|cylinder exploded|boiler explosion"
                            r"|(power |electrical )?transformer)\b", re.I)),
]


_SPLIT = re.compile(r"[.!?؟؛;\n]+|\s/\s?|/\s")


def _sentences(title, summary, fa):
    t = fa_norm(title or "") if fa else (title or "")
    su = first_sentences(summary or "", 260)
    su = fa_norm(su) if fa else su
    return [x.strip() for x in _SPLIT.split(t) + _SPLIT.split(su) if x.strip()]


def _kind_fa(x):
    if not _BLAST_FA.search(x):
        return None
    for k, rx in _FA:
        if rx.search(x):
            # «انفجار کنترل‌شده در معدن…»: blasting at a mine
            return "mine" if k == "ordnance" and _MINE_FA.search(x) else k
    for w in _WHY_FA.finditer(x):
        near = x[w.end():w.end() + 50]
        if _WAR_FA.search(near):
            continue
        for k, rx in _AFTER_FA:
            if rx.search(near):
                return k
    return None


def _kind_en(x):
    if not _BLAST_EN.search(x):
        return None
    for k, rx in _EN:
        m = rx.search(x)
        if m and (k in ("film", "fireworks", "ordnance") or not _WAR_EN.search(x[max(0, m.start() - 40):m.end() + 40])):
            return "mine" if k == "ordnance" and _MINE_EN.search(x) else k
    return None


def find(lang, title, summary=""):
    """(kind of cause, the sentence that tells it) for a report, or (None, ""). The blast and its cause must be told
    in one sentence of the headline or of the start of the text."""
    fa = lang == "fa"
    for x in _sentences(title, summary, fa):
        k = _kind_fa(x) if fa else _kind_en(x)
        if k:
            return k, x
    return None, ""


def which(lang, title, summary=""):
    """The kind of cause a report gives for an explosion or a sound, or None."""
    return find(lang, title, summary)[0]


def of_item(m, sentence=False):
    """which() for a report: a Persian one in Persian, the rest in English; with sentence=True, find()."""
    if m.get("wit"):
        return (None, "") if sentence else None
    if m.get("lang") == "fa":
        r = find("fa", m.get("ti") or "", m.get("su") or "")
    else:
        r = find("en", m.get("en_ti") or m.get("ti") or "", m.get("en_su") or m.get("su") or "")
    return r if sentence else r[0]
