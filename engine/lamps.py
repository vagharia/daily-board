"""What a report must tell, in its own headline, to light a warning lamp (index.compute_lights); the deployment lamp
has its own (deploy.lamp). The classifier's flags are broad, for the bulletin; a lamp is narrower:

- strike («حمله نظامی مستقیم»): an attack in the war itself, told as done: an actor striking a place or a target
  (attack_verb), an attack or explosions in a city of Iran (city_strike), or a drone / jet of one side downed by the
  other. Iran on one side, the US or Israel on the other (or a place of Iran struck). Never a statement naming
  past attacks («حملات به تأسیسات هسته‌ای»), an attack to prevent ("avert a US strike"), a market or trade story
  ("oil rose after …", "UAE sells oil from the attacked supertanker"), the side fronts (Houthis and Saudi Arabia,
  Iraq, Lebanon), nor a ship or a mine at sea (the Hormuz lamp).
- hormuz («حادثه دریایی / هرمز»): an incident at sea told (hit, explosion, fire, a mine, a seizure, an attack), or
  the strait closed told as done; never a threat, a condition, a denial or a promise about closing it ("Iran will
  never close Hormuz", «تهدید به بستن تنگه»), nor words about a blockade ("Trump calls the blockade the greatest").
- airspace: a closure, flights stopped or rerouted; never a reopening alone.
"""
import re

from . import attack_verb, city_strike, vessel
from .util import fa_norm, to_latin_digits

_NOT = {"denial", "past", "speculative", "analysis", "opinion", "digest", "scheduled", "feature", "aside", "tribute",
        "far_off", "cyber", "controlled", "mishap"}
_SIDE = {"side_minor", "side_major", "secondary"}

_FA_L = "؀-ۿ"


def _fa(*ws):
    return "(?<![" + _FA_L + "])(?:" + "|".join(fa_norm(w).replace(" ", r"\s*") for w in ws) + ")"


def _head(m):
    """(text, is Persian): the headline in its own language."""
    if m.get("lang") == "fa":
        return to_latin_digits(fa_norm(m.get("ti") or "")), True
    return m.get("en_ti") or m.get("ti") or "", False


# ---- strike
_IRAN_EN = re.compile(r"\b(iran\w*|tehran|irgc|revolutionary guards?|islamic republic)\b", re.I)
_FOE_EN = re.compile(r"\b(u\.?s\.?|us|united states|america\w*|pentagon|centcom|israel\w*|idf|tel aviv)\b", re.I)
_IRAN_FA = re.compile(_fa("ایران", "تهران", "سپاه", "جمهوری اسلامی", "ارتش", "پدافند", "نیروی دریایی", "نیروی هوافضا"))
_FOE_FA = re.compile(_fa("آمریکا", "امریکا", "ایالات متحده", "پنتاگون", "سنتکام", "اسرائیل", "اسراییل",
                         "صهیونیست", "رژیم صهیونیستی", "تل آویو", "سرزمین های اشغالی", "فلسطین اشغالی"))
# a drone or a jet of one side brought down by the other
_DOWN_EN = re.compile(r"\b(shoots? down|shot down|down(?:s|ed)|destroy(?:s|ed)|intercept(?:s|ed))\b.{0,40}"
                      r"\b(drones?|uavs?|mq-?\d+|reapers?|predators?|global hawk|jets?|fighters?|f-?\d+|aircraft)\b"
                      r"|\b(drones?|uavs?|mq-?\d+|reapers?|predators?|jets?|aircraft)\b.{0,30}\b(shot down|downed|destroyed)\b",
                      re.I)
_DOWN_FA = re.compile(_fa("سرنگونی", "سرنگون", "انهدام", "منهدم", "شکار", "رهگیری و منهدم") + r".{0,40}"
                      + _fa("پهپاد", "جنگنده", "هواپیما", "ام کیو", "mq", "پریداتور", "ریپر", "گلوبال هاوک", "اف")
                      + "|" + _fa("پهپاد", "جنگنده", "هواپیما") + r".{0,40}" + _fa("سرنگون شد", "منهدم شد", "سرنگون کرد",
                                                                                    "منهدم کرد"), re.I)
# "Iran fires missiles at US base in Qatar"
_FIRE_EN = re.compile(r"\b(?:fires?|fired|launch(?:es|ed)?)\s+(?:\w+\s+){0,3}(?:missiles?|rockets?|drones?|ballistic\s+\w+)"
                      r"\s+(?:at|on|toward|towards|against|into)\b", re.I)
_EXCHANGE_EN = re.compile(r"\bexchang\w*\s+(?:\w+\s+)?(?:strikes|fire|attacks|blows)\b", re.I)
_GULF_EN = re.compile(r"\b(oman\w*|uae|emirat\w*|qatar\w*|bahrain\w*|kuwait\w*|saudi\w*|didamar)\b", re.I)
_GULF_FA = re.compile(_fa("عمان", "امارات", "قطر", "بحرین", "کویت", "عربستان", "دیدامار", "دیدمار"))
# the attack is not the news: a market, trade, a reaction or prevention
_STRIKE_NOT_EN = re.compile(r"\b(oil prices?|crude prices?|brent|stocks?|markets?|shares|sells?|selling|sold|insur\w+"
                            r"|avert\w*|prevent\w*|avoid\w*|window|commitment|monitoring|condemn\w*|criticiz\w*"
                            r"|anniversary|lawsuit|compensation|environmental|impacts?|effects?|aftermath)\b", re.I)
_STRIKE_NOT_FA = re.compile(_fa("قیمت نفت", "بازار", "بورس", "فروش", "می فروشد", "بیمه", "جلوگیری", "اجتناب",
                                "انتقاد", "محکوم", "سکوت", "تعهد", "نظارت", "سالگرد", "غرامت", "شکایت",
                                "تاثیرات", "تأثیرات", "پیامد", "زیست محیطی"))
_SEA_EN = re.compile(r"\b(tankers?|ships?|vessels?|cargo|carriers? of|lng|lpg|mines?|boats?|supertankers?)\b", re.I)
_SEA_FA = re.compile(_fa("نفتکش", "نفت کش", "کشتی", "تانکر", "شناور", "لنج", "مین", "قایق", "ناو"))


def strike(m):
    """Whether a report lights the strike lamp (see the module doc)."""
    fl = set(m.get("flags") or [])
    if "kinetic" not in fl or fl & (_NOT | _SIDE) or "maritime_incident" in fl:
        return False
    t, fa = _head(m)
    if (_SEA_FA if fa else _SEA_EN).search(t) or vessel.mark(m):
        return False                   # at sea: the Hormuz lamp
    if (_STRIKE_NOT_FA if fa else _STRIKE_NOT_EN).search(t):
        return False
    iran, foe = ((_IRAN_FA, _FOE_FA) if fa else (_IRAN_EN, _FOE_EN))
    told = attack_verb.actor_strikes_fa(t) if fa else (attack_verb.actor_strikes_en(t) or bool(_FIRE_EN.search(t))
                                                         or bool(_EXCHANGE_EN.search(t)))
    # Iran and the US or Israel; or Iran striking a Gulf state ("Iran attacks Oman's Didamar island")
    if told and iran.search(t) and (foe.search(t) or (_GULF_FA if fa else _GULF_EN).search(t)):
        return True
    if (_DOWN_FA if fa else _DOWN_EN).search(t) and iran.search(t) and foe.search(t):
        return True
    return bool(city_strike.mark(m))   # an attack or explosions in a city of Iran


# ---- hormuz
_INCIDENT_EN = re.compile(r"\b(hit|hits|struck|strikes?|explo\w+|blasts?|fire|ablaze|burn\w*|attack\w*|seiz\w*|board\w*"
                          r"|mines?|sank|sink\w*|projectiles?|drones?|missiles?|damag\w*|disabl\w*|harass\w*|fired on"
                          r"|captur\w*|detain\w*|hijack\w*)\b", re.I)
_INCIDENT_FA = re.compile(_fa("اصابت", "انفجار", "منفجر", "آتش", "حریق", "حمله", "توقیف", "مین", "غرق", "پرتابه",
                              "پهپاد", "موشک", "آسیب", "شلیک", "مصادره", "ربوده", "سوخت", "شعله ور"))
_ONLY_SAID_EN = re.compile(r"\b(never|not|no|won['’]?t|will|would|could|may|might|if|unless|threat\w*|warn\w*|vow\w*"
                           r"|pledg\w*|plans?|consider\w*|calls?|called|describ\w*|prais\w*|hail\w*|what if|should)\b",
                           re.I)
_ONLY_SAID_FA = re.compile(_fa("هرگز", "نمی", "نخواهد", "خواهد", "اگر", "در صورت", "چنانچه", "تهدید", "هشدار",
                               "ممکن", "احتمال", "قصد", "برنامه", "خواند", "توصیف", "ستود", "نباید"))

_MARKET_EN = re.compile(r"\boil (?:prices?|edges?|falls?|rises?|climbs?|slips?|jumps?|surges?|drops?|gains?|stead\w+"
                        r"|futures)\b|\b(brent|crude prices?|stocks?|markets?|shares|insur\w+|premiums?)\b", re.I)
_MARKET_FA = re.compile(_fa("قیمت نفت", "بازار", "بورس", "بیمه"))
_IF_EN = re.compile(r"\b(threat\w*|if|unless|never|would|could|might|what if)\b", re.I)
_IF_FA = re.compile(_fa("تهدید", "اگر", "در صورت", "چنانچه", "هرگز"))


def sea(m):
    """Whether a report lights the Hormuz lamp (see the module doc)."""
    fl = set(m.get("flags") or [])
    if fl & {"denial", "past", "digest", "scheduled", "tribute", "far_off", "piracy"}:
        return False
    t, fa = _head(m)
    if not fl & {"maritime_incident", "hormuz_closure"}:
        # an attack the classifier read without the sea ("Iran says tanker carrying LNG hit mine, suffered explosion
        # in Hormuz": kinetic only): a ship in the headline makes it the Hormuz lamp's, not the strike lamp's
        if "kinetic" not in fl or not ((_SEA_FA if fa else _SEA_EN).search(t) or vessel.mark(m)):
            return False
    if (_MARKET_FA if fa else _MARKET_EN).search(t):
        return False                   # "Oil edges lower as Trump plays down new US attacks": a market report
    if (_INCIDENT_FA if fa else _INCIDENT_EN).search(t):
        # a ship hit, a mine, a fire, a seizure: told; not a threat or a condition ("… to close Hormuz if attacked")
        return not (_IF_FA if fa else _IF_EN).search(t)
    # only the strait closed, or a blockade: told as done, not said, threatened or promised
    return not (_ONLY_SAID_FA if fa else _ONLY_SAID_EN).search(t)


# ---- airspace
_REOPEN_EN = re.compile(r"\b(reopen\w*|resum\w*|restor\w*|lift\w*)\b", re.I)
_CLOSED_EN = re.compile(r"\b(clos(e|es|ed|ing|ure)|shut\w*|suspend\w*|cancel\w*|halt\w*|ground\w*|divert\w*|rerout\w*)\b",
                        re.I)
_REOPEN_FA = re.compile(_fa("بازگشایی", "باز شد", "ازسرگیری", "از سرگیری", "برقراری مجدد"))
_CLOSED_FA = re.compile(_fa("بسته", "بستن", "مسدود", "تعلیق", "لغو", "توقف", "متوقف", "تغییر مسیر"))


def air(m):
    """Whether a report lights the airspace lamp: a closure or flights stopped, not a reopening alone."""
    if "airspace" not in (m.get("flags") or []):
        return False
    t, fa = _head(m)
    if (_REOPEN_FA if fa else _REOPEN_EN).search(t):
        # "Iran reopens airspace after brief closure": the closure is over; still a closure when something else shuts
        rest = (_REOPEN_FA if fa else _REOPEN_EN).sub(" ", t)
        rest = re.sub(r"(?i)\b(after|following)\b.*$|" + _fa("پس از", "بعد از") + ".*$", " ", rest)
        return bool((_CLOSED_FA if fa else _CLOSED_EN).search(rest))
    return True
