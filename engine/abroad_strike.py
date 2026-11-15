"""One attack of Iran abroad on one place, one story: the main front's counterpart of the Gulf rule, for Iran (or an
unnamed side) striking an Arab country of the Middle East or one of America's bases (us_bases.py).

The news tells one attack in many words all day long ("Iran Attacks Bahrain as Conflict Escalates", «رادار سایت
پدافندی آمریکا در پایگاه بالگردی الرفاع بحرین با ۶ فروند پهپاد مورد هدف قرار گرفت», "Bahrain says air defenses
intercepted, destroyed Iranian drones", "Iran claims attack on US military airbase in Bahrain"): their headlines share
few words, and the Gulf rule leaves out every headline naming Iran or America. This rule reads the place instead.

A report's Mark (mark): the country, the city (fronts' Gulf cities: all of Bahrain is one, "bahrain"; Qatar and
Kuwait too) and the targets it names: one of America's bases (us_bases.BASES), "a US base" unnamed (GENERIC), or a
named site (fronts._TARGETS: the Bapco refinery…). Reports are one attack (same):
  2 = the same target (a named base and "a US base" in the same country are the same), or, neither naming a target,
      the same city (in Bahrain: the country);
  1 = one names a target, the other only its city or country ("Iran attacks Bahrain" and the Riffa base), or neither
      names a city: it joins only when one story of that country fits (cluster._abroad_matches);
  0 = another country, another city, another target (Riffa and Isa; a base and the Bapco refinery).
When (cluster.abroad_when) decides with the story's time label (cluster.EV_ON): a report giving a time within the
story's joins it whenever it comes (up to two days); otherwise one told as it happens (sirens, blasts heard,
interceptions) after a quiet spell, or one saying it is a new attack as it happens ("another", «مجدد»; not "the
second attack in three days", which compares with an earlier one) is a new attack; a later account (damage, details,
a video) joins for a day; anything else while the story is still being told.
Only reports of an attack told as done or as it happens (no threat, plan, denial, analysis, reaction or
retelling of the past), Iran the one striking (not "Iran-backed" groups, the Houthis, Iraq's militias, nor
America or Israel striking Iran); at sea the ship rules decide. A Telegram channel's post joins a news story, never
another channel's."""
import re

from . import fronts
from .us_bases import BASES
from .util import fa_norm

GENERIC = "us_base"            # "a US base" in the country, unnamed: the same as any named base there
BASE_KEYS = frozenset(BASES)

_L = r"ؠ-ۿ"


def _rx_fa(forms):
    return re.compile(rf"(?<![{_L}])(?:" + "|".join(re.escape(fa_norm(x)).replace(r"\ ", r"\s*")
                                                    for x in sorted(forms, key=len, reverse=True)) + rf")(?![{_L}])")


def _rx_en(forms):
    return re.compile(r"\b(?:" + "|".join(re.escape(x).replace(r"\ ", r"[\s-]+")
                                          for x in sorted(forms, key=len, reverse=True)) + r")\b", re.I)


_BASE_RX = [(k, _rx_fa(v[2]), _rx_en(v[3])) for k, v in BASES.items()]

# Iran the one striking; "Iran-backed" is someone else, "strikes on Iran" is Iran struck
_IRAN_EN = re.compile(r"\b(iran|iranian|irgc|revolutionary guards?|tehran|islamic republic)\b", re.I)
_IRAN_FA = re.compile(fa_norm("ایران|ایرانی|سپاه|پاسداران|هوافضا|تهران|جمهوری اسلامی"))
_ON_IRAN_EN = re.compile(r"\b(?:on|against|at|into|over)\s+(?:(?:southern|northern|western|eastern|central)\s+)?"
                         r"(?:iran|tehran)\b(?!ian)|\b(?:strikes?|attacks?|raids?|bombing)\s+(?:on|against)\s+"
                         r"(?:\w+\s+){0,2}iran\w*"
                         r"|\b(?:strikes?|struck|attacks?|attacked|hits?|bomb\w*|target\w*|raids?|raided)\s+"
                         r"(?:(?:southern|northern|western|eastern|central)\s+)?(?:iran|tehran)\b(?!ian)", re.I)
_ON_IRAN_FA = re.compile(fa_norm("(?:به|علیه|بر ضد) (?:خاک |جنوب |شمال |غرب |شرق |مرکز )?(?:ایران|تهران)"
                                 "|تجاوز (?:\\S+ ){0,2}(?:به|علیه) (?:\\S+ ){0,2}ایران"))
# someone else striking: the Houthis, Iraq's militias, Hezbollah, "Iran-backed" groups
_OTHER_EN = re.compile(r"\b(houthis?|yemen\w*|ansar ?allah|sanaa|hezbollah|kataib|islamic resistance|militias?"
                       r"|militants?|proxies|proxy|(?:iran|tehran)[- ](?:backed|aligned|allied|supported|sponsored)"
                       r"|isis|islamic state|al[- ]shabaab)\b", re.I)
_OTHER_FA = re.compile(fa_norm("حوثی|یمن|انصارالله|صنعا|حزب الله|حزب‌الله|کتائب|مقاومت اسلامی عراق|گروه های مقاومت"
                               "|گروه‌های مقاومت|شبه نظامی|حشد|نیابتی|داعش"))
# America's site or base, unnamed: "US base in Bahrain", "base hosting US helicopters", «پایگاه آمریکا در بحرین»
_US_SITE_EN = re.compile(r"\b(?:u\.?s\.?|american|america'?s|us-run|us-led)\s+(?:(?:military|air|naval|navy|army"
                         r"|air[- ]force|defen[cs]e|air[- ]defen[cs]e|radar|key|main|major|largest|biggest|helicopter"
                         r"|drone|missile|early[- ]warning|logistics|forces?'?)\s+){0,3}"
                         r"(?:bases?|air ?bases?|airfields?|radars?|facilit(?:y|ies)|sites?|installations?|camps?"
                         r"|headquarters|garrisons?)\b"
                         r"|\b(?:bases?|air ?bases?|facilit(?:y|ies))\s+(?:hosting|housing|used by|of)\s+(?:the\s+)?"
                         r"(?:u\.?s\.?|american)\b", re.I)
_US_SITE_FA = re.compile(fa_norm("(?:پایگاه|پایگاه‌های|پایگاه های|رادار|رادارهای|سایت|تاسیسات|تأسیسات|مقر|قرارگاه)"
                                 "(?: [^ ]+){0,5}? (?:آمریکا|آمریکایی|آمریکایی‌ها|امریکا|امریکایی|ایالات متحده)"))
# a base, whoever's: Iran striking a base in a country hosting America's is taken as one ("Iran Strikes Bahrain Base")
_BASE_WORD_EN = re.compile(r"\b(?:air ?bases?|bases?|airfields?|military facilit(?:y|ies))\b", re.I)
_BASE_WORD_FA = re.compile(fa_norm("پایگاه|پایگاه‌های|پایگاه های|قرارگاه"))
# an attack told as done or as it happens
_HIT_EN = re.compile(r"\b(attack\w*|strikes?|struck|target\w*|hit|hits|bomb\w*|drones?|missiles?|rockets?|blasts?"
                     r"|explosions?|intercept\w*|shot down|shoots? down|downed|destroy\w*|retaliat\w*)\b", re.I)
_HIT_FA = re.compile(fa_norm("حمله|حملات|هدف|اصابت|پهپاد|موشک|راکت|انفجار|رهگیری|منهدم|انهدام|سرنگون|بمباران"
                             "|را زد|را زده|کوبید|ضربه زد"))
# a threat, a plan, a condition, a question: not an attack told
_SOFT_EN = re.compile(r"\b(will|would|could|may|might|threatens?|threatened|vows?|vowed|warns?|warned|plans?"
                      r"|ready to|prepared to|if|unless|whether|denies|denied|debunks?|false|rejects?|condemn\w*)\b", re.I)
_SOFT_FA = re.compile(fa_norm("خواهد|خواهیم|خواهند|تهدید|آماده|در صورت|اگر|چنانچه|تکذیب|رد کرد|محکوم|ادعای دروغ"))
# told as it happens: sirens, blasts heard, interceptions, now
_FRESH_EN = re.compile(r"\b(heard|sirens?|alarms?|blasts?|explosions?|rattles?|rock(?:s|ed)?|intercept\w*|shoots? down"
                       r"|shot down|air defen[cs]es? (?:activ\w+|fir\w+|engag\w+)|now|ongoing|under way|underway"
                       r"|moments ago|minutes ago)\b", re.I)
_FRESH_FA = re.compile(fa_norm("صدای انفجار|انفجار|انفجارهای|شنیده|آژیر|پدافند (?:هوایی )?(?:\\S+ )?فعال|فعال شدن پدافند"
                               "|شلیک پدافند|رهگیری|سرنگون|هم اکنون|هم‌اکنون|لحظاتی پیش|دقایقی پیش|در حال"))
_NOW_EN = re.compile(r"\b(now|moments ago|minutes ago|just now|right now|ongoing|under way|underway)\b", re.I)
_NOW_FA = re.compile(fa_norm("هم اکنون|هم‌اکنون|هماکنون|لحظاتی پیش|لحظاتی قبل|دقایقی پیش|دقایقی قبل|همین الان|در حال"))
# a statement of what was done ("Bahrain says air defences intercepted…", «سپاه: …»): told afterwards, not as it happens
_SAID_EN = re.compile(r"\b(says?|said|claims?|claimed|announces?|announced|confirms?|confirmed|according to|reports?"
                      r"|reported)\b", re.I)
_SAID_FA = re.compile(fa_norm("اعلام کرد|اعلام شد|گفت|ادعا|مدعی|اطلاعیه|بیانیه|تایید کرد|خبر داد|خبر دادند|روابط عمومی"))
_SPEAKER = re.compile(r"^[^:،,]{2,40}:\s")      # «سپاه: …», "IRGC: …": a statement
# a new attack ("another", «مجدد»), unless compared with an earlier one ("second attack in three days", "again after
# months", "first … since September")
_NEW_EN = re.compile(r"\b(new|another|fresh|second|third|again|renewed|wave|round|more)\b", re.I)
_NEW_FA = re.compile(fa_norm("دوباره|مجدد|مجددا|جدید|تازه|دومین|سومین|بار دیگر|باز هم|موج"))
_COMPARE_EN = re.compile(r"\b(?:in|within|over|this|past|last)\s+(?:(?:\d+|two|three|four|five|six|seven|a few|several"
                         r"|a|one)\s+)?(?:days?|weeks?|months?)\b|\bafter (?:\w+\s+){0,2}(?:days?|weeks?|months?)\b"
                         r"|\btwice\b|\bsince (?:january|february|march|april|may|june|july|august|september|october"
                         r"|november|december|the (?:war|ceasefire|truce))\b|\bresum\w+", re.I)
_COMPARE_FA = re.compile(fa_norm("در (?:\\S+ ){0,2}(?:روز|هفته|ماه)(?: های| ها|‌های)? (?:گذشته|اخیر)|پس از (?:\\S+ ){0,2}"
                                 "(?:روز|هفته|ماه)|از سر گیری|ازسرگیری|مرحله"))
# a later account of the attack: damage, details, a video, an infographic; nothing happening now
_LATER_EN = re.compile(r"\b(damag\w*|debris|aftermath|footage|videos?|images?|photos?|satellite|details?|what we know"
                       r"|explainer|infographic|confirm\w*|responsibility|claims? responsibility|investigat\w*)\b", re.I)
_LATER_FA = re.compile(fa_norm("خسارت|آسیب|بقایای|فیلم|تصاویر|ویدئو|ویدیو|ماهواره|جزئیات|اینفوگرافی|اینفوگرافیک"
                               "|پیامد|تایید|مسئولیت|پس از حمله|در پی حمله"))
_NOT = {"denial", "past", "controlled", "scheduled", "speculative", "analysis", "opinion", "digest", "reaction"}
# "Bahraini defence forces": Bahrain (fronts' places read the country's name only)
_DEMONYM = re.compile(r"\b(bahrain|qatar|kuwait|oman)is?\b", re.I)
# Oman, the country (fronts read only its cities); not the Gulf or Sea of Oman
_OMAN_EN = re.compile(r"\boman\b", re.I)
_NOT_OMAN_EN = re.compile(r"\b(?:gulf|sea) of oman\b", re.I)
_OMAN_FA = re.compile(rf"(?<![{_L}])عمان(?![{_L}])")
_NOT_OMAN_FA = re.compile(fa_norm("دریای عمان|خلیج عمان|دریای مکران"))


class Mark(tuple):
    """(country, cities, targets) of a report; fresh: told as it happens; now: it says so; new: it says it is a new
    attack (not compared with an earlier one); later: a later account (damage, details, a video)."""
    fresh = False
    now = False
    new = False
    later = False


def _heads(m):
    """The headline as the rule reads it: a Persian report in Persian, an English one in English."""
    fa = m.get("lang") == "fa"
    en = m.get("en_ti") or ("" if fa else m.get("ti")) or ""
    fat = fa_norm(m.get("ti") or "") if fa else ""
    return fa, en, fat


def _iran_strikes(en, fat, fa):
    """Iran is named, as the one striking: not only "strikes on Iran" («حمله به ایران»)."""
    if fa:
        t = _ON_IRAN_FA.sub(" ", fronts._BACKED_FA.sub(" ", fat))
        return bool(_IRAN_FA.search(t))
    t = _ON_IRAN_EN.sub(" ", fronts._BACKED_EN.sub(" ", en))
    return bool(_IRAN_EN.search(t))


def bases_in(en, fat, fa):
    """America's named bases a headline tells of (keys of us_bases.BASES)."""
    return {k for k, rf, re_ in _BASE_RX if (rf.search(fat) if fa else re_.search(en))}


def mark(m):
    """The Mark of a report of an attack of Iran on a place abroad, or None (see above). The caller checks that it is
    not at sea and not a citizens' post."""
    if set(m.get("flags") or []) & _NOT:
        return None
    fa, en, fat = _heads(m)
    t = fat if fa else en
    if not t:
        return None
    if (_OTHER_FA if fa else _OTHER_EN).search(t) or (_SOFT_FA if fa else _SOFT_EN).search(t):
        return None                                  # someone else striking; a threat, a plan, a denial, a reaction
    if not (_HIT_FA if fa else _HIT_EN).search(t):
        return None
    bases = bases_in(en, fat, fa)
    us_site = bool((_US_SITE_FA if fa else _US_SITE_EN).search(t))
    iran = _iran_strikes(en, fat, fa)
    if not iran and not bases and not us_site:
        return None                                  # neither Iran striking nor America's base struck
    us_site = us_site or (iran and bool((_BASE_WORD_FA if fa else _BASE_WORD_EN).search(t)))
    cities, ctry = fronts._gulf_places(t if fa else _DEMONYM.sub(r"\1", t), fa)
    if (_OMAN_FA.search(_NOT_OMAN_FA.sub(" ", t)) if fa else _OMAN_EN.search(_NOT_OMAN_EN.sub(" ", t))):
        ctry = set(ctry) | {"om"}
    targets = set(fronts.gulf_targets(t, fa, cities))
    if bases:
        bctry = {BASES[k][4] for k in bases}
        if len(bctry) > 1:
            return None                              # several countries' bases: a roundup
        ctry = bctry
        cities |= {BASES[k][5] for k in bases if BASES[k][5]}
        targets |= bases
    if len(ctry) != 1:
        return None                                  # no country, or several (a roundup, a reaction)
    c = next(iter(ctry))
    if us_site and not bases:
        targets.add(GENERIC)
    if len(cities) > 2:
        return None
    g = Mark((c, frozenset(cities), frozenset(targets)))
    said = bool((_SAID_FA if fa else _SAID_EN).search(t) or _SPEAKER.match(t))
    g.fresh = bool((_FRESH_FA if fa else _FRESH_EN).search(t)) and not said
    g.now = bool((_NOW_FA if fa else _NOW_EN).search(t))
    g.new = bool((_NEW_FA if fa else _NEW_EN).search(t)) and not (_COMPARE_FA if fa else _COMPARE_EN).search(t)
    g.later = bool((_LATER_FA if fa else _LATER_EN).search(t)) and not g.fresh
    return g


def _bases_only(s):
    return bool(s) and s <= BASE_KEYS | {GENERIC}


def same(a, b):
    """2 = the same target, or the same city (a small country: the country) with no target named; 1 = one names a
    target, the other only its city or country, or neither names a city; 0 = not the same attack (see above)."""
    if not a or not b or a[0] != b[0]:
        return 0
    ta, tb = a[2], b[2]
    if ta and tb:
        if ta & tb:
            return 2
        if (GENERIC in ta and _bases_only(tb)) or (GENERIC in tb and _bases_only(ta)):
            return 2                                 # "a US base in Bahrain" and the Riffa base
        return 0
    if a[1] and b[1] and not a[1] & b[1]:
        return 0                                     # another city
    if ta or tb:
        return 1
    if a[1] and b[1]:
        return 2
    return 1


def iran_named(m):
    """The report's Mark, with Iran named as the one striking (not only America's base struck), or None."""
    g = mark(m)
    if not g:
        return None
    fa, en, fat = _heads(m)
    return g if _iran_strikes(en, fat, fa) else None
