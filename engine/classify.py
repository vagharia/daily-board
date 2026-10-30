"""Rule-based severity scoring (0-100) and tagging.

Red (>=70): direct military action, attacks on shipping / Hormuz, ultimatums, airspace closures,
evacuations, carrier / bomber deployments. Orange (45-69): threats, sanctions, exercises, proxy
attacks, IAEA findings. Yellow (<45): statements, diplomacy, analysis, and sports news touched by the war (a match
called off, a team that won't travel).
"""
import math
import re

from . import config, deesc, sport, witness
from .classify_fa import score_fa
from .fronts import saudi_houthi
from .internet import internet, severity as net_severity
from .lexicon import COUNTRIES_RX, PEOPLE_RX, PLACES_RX, TOPICS_RX, match_keys
from .util import fa_norm, first_sentences, strip_dateline, to_latin_digits

I = re.I


AIR = (r"tankers? (aircraft|planes|jets)|refuel(l)?ing (tankers?|aircraft|planes|jets)|aerial refuel\w*|kc-?135s?"
       r"|kc-?46s?|kc-?10s?|c-?17s?|c-?5s?|cargo (planes|aircraft|flights)|transport (planes|aircraft)"
       r"|military (flights|aircraft|planes|cargo)|warplanes?|fighter (jets|planes|squadrons?)|squadrons?|fighters"
       r"|f-?15s?|f-?16s?|f-?22s?|f-?35s?|e-?3s?|awacs|p-?8s?|mq-?9s?|reapers?|b-?52s?|b-?2s?|b-?1b?s?|bombers?")


POWERS = (r"putin|lavrov|peskov|zakharova|kremlin|medvedev|shoigu|ryabkov|nebenzia|ulyanov|xi jinping|president xi"
          r"|wang yi|mao ning|lin jian|guo jiakun|fu cong|(russian|chinese|russia's|china's) foreign (ministry|minister)")
REGION = (r"iran\w*|tehran|israel\w*|middle east|gulf|hormuz|gaza|lebanon|yemen|houthis?|syria|strikes?|war|nuclear"
          r"|sanctions")
IR_TOP = (r"araghchi|pezeshkian|larijani|ghalibaf|zarif|velayati|shamkhani|iran(ian|'s)? (president|foreign minister"
          r"|defen[cs]e minister|delegation|officials?)")


def P(rx, base, topics=(), flags=()):
    return (re.compile(rx, I), base, set(topics), set(flags))


# ------------------------------------------------------------------ English patterns
PATTERNS = [
    # --- critical / kinetic
    P(r"\b(declar(e|es|ed|ing) war|war (has )?(begun|broken out|erupted)"
      r"|ground (offensive|invasion|operation)|invad(e|es|ed|ing)\b|invasion of)", 90, ["military"], ["kinetic"]),
    P(r"\b(all-out|full-scale|full-blown|wider|regional|new|renewed) war\b|\bact of war\b|\bbrink of war\b", 58,
      ["military"], ["threat"]),
    P(r"\b(air ?strikes?|airstrikes?)\b", 80, ["military"], ["kinetic"]),
    P(r"\bstrikes? (on|against|at|in|near|hit|target)", 76, ["military"], ["kinetic"]),
    P(r"\b(struck|bombed|bombing|bombard\w*|shell(ed|ing))\b", 78, ["military"], ["kinetic"]),
    P(r"\b(missile|rocket|drone|ballistic)s? (attack|strike|barrage|salvo|assault)s?\b", 82, ["military"], ["kinetic"]),
    P(r"\b(launch(es|ed|ing)?|fir(es|ed|ing))\b(?! (a |an |its |the )?(new (?!wave|round|barrage|salvo|attack)|campaign"
      r"|initiative|program|app|service|platform|product|probe|investigation|inquiry|company|startup))"
      r".{0,30}\b(missiles?|rockets?|drones?)\b", 82, ["military"], ["kinetic"]),
    P(r"\b(missile|rocket) (launch|launches|firing|fired)\b|\blaunch(es)? of (\w+ ){0,2}(missiles?|rockets?)\b", 76,
      ["military"], ["kinetic"]),
    P(r"\bintercept\w*\b.{0,40}\b(missiles?|rockets?|ballistic|cruise)\b"
      r"|\b(missiles?|rockets?)\b.{0,60}\bintercept\w*", 76, ["military"], ["kinetic"]),
    P(r"\bintercept\w*\b.{0,40}\b(drones?|projectiles?|uavs?)\b"
      r"|\b(drones?|projectiles?|uavs?)\b.{0,60}\bintercept\w*", 64, ["military"], []),
    P(r"\bshrapnel\b|\bdebris (from|of) (an? )?(intercept\w*|missiles?|drones?)", 72, ["military"], ["kinetic"]),
    P(r"\bintercept(s|ed|ion|ions)?\b", 50, ["military"], []),
    P(r"\b(air[- ]raid )?sirens?\b", 74, ["military"], ["kinetic"]),
    P(r"\bair[- ]defen[cs]es?\b.{0,25}\b(activat\w*|active|fir(es|ed|ing)|engag\w*|open(ed)? fire|in action|heard)\b"
      r"|\banti[- ]aircraft (fire|guns?)\b", 74, ["military"], ["kinetic"]),
    # fighter jets heard or seen over a city (not a drill, a parade or an air show)
    P(r"^(?!.*\b(drills?|exercises?|parades?|air ?shows?|fly-?past|fly-?over)\b).*?(\b(fighter )?jets?\b.{0,30}"
      r"\b(heard|seen|spotted|roar\w*|scream\w*|flying (low )?over|flew (low )?over)\b|\bsonic booms?\b"
      r"|\bsound of (fighter )?jets\b)", 72, ["military", "air"], ["kinetic"]),
    P(r"\b(shoot|shoots|shooting|shot) down\b|\bdowned (a |an |the )?(\w+ ){0,2}(drone|jet|aircraft|uav)|\bdowning of\b"
      r"|\b(destroy\w*|hunt\w*) (of )?(an? |the )?(\w+ ){0,3}(drone|uav)s?\b", 78, ["military"], ["kinetic"]),
    P(r"\b(air ?strikes?|strikes?|shelling|bombardment|raids?|attacks?|barrage)\b.{0,25}\b(kill(s|ed|ing)?|wound\w*"
      r"|injur\w*|dead)\b", 82, ["military"], ["kinetic"]),
    P(r"\b(missiles?|rockets?|drones?|ballistic)\b.{0,15}\b(target(s|ed|ing)?|hit(s|ting)?|slam\w*|pound\w*|rain\w*)\b",
      80, ["military"], ["kinetic"]),
    P(r"\b(could|would|will|may|might|ready to|prepared to|threaten\w* to|vow\w* to|plans? to)\s+(\w+\s+){0,2}"
      r"(strike|attack|bomb|hit|target|invade)\b", 60, ["military"], ["threat"]),
    P(r"\b(attack(ed|s)? on|attacked|under attack|came under fire)\b", 74, ["military"], ["kinetic"]),
    # "Iran attacks US base", "Israel targets Hezbollah positions" (not sanctions or hackers "hitting" a target)
    P(r"^(?!.*\b(sanction\w*|cyber\w*|hack\w*|tariffs?)\b).*?\b(attack(s|ing)?|raid(s|ed|ing)?|storm(s|ed|ing)?"
      r"|hit(s|ting)?|target(s|ed|ing)?)\s+(a |an |the |its |their )?(\w+ ){0,3}(bases?|embass(y|ies)|consulates?"
      r"|convoys?|refiner(y|ies)|airports?|ports?|positions?|headquarters|depots?|facilit(y|ies)|sites?|plants?|camps?"
      r"|outposts?)\b", 74, ["military"], ["kinetic"]),
    P(r"^(?!.*\bsanction\w*\b).*?\b(attack(s|ing)?|hit(s|ting)?|strik(e|es|ing)|struck)\s+(a |an |the )?(\w+ ){0,2}"
      r"(tanker|vessel|ship|freighter|cargo ship|warship|container ship)s?\b", 80, ["maritime"],
      ["kinetic", "maritime_incident"]),
    P(r"\b(explosions?|blasts?|detonat\w+)\b", 70, ["military"], ["kinetic"]),
    P(r"\b(was |were |been |is |are )?assassinated\b|\bassassination of\b|\bkilled (a |an |the )?(senior|top) "
      r"(commander|official|general)", 84, ["military"], ["kinetic"]),
    P(r"\bassassination attempt\b|\battempt(ed)? to assassinate\b", 72, ["military"], ["kinetic"]),
    P(r"\bassassinat\w+", 60, ["military"], ["threat"]),
    P(r"\b(plot|plots|plotting|planning|plann?ed)\b.{0,40}\b(attacks?|strikes?|kill|killing|assassinat\w*|bomb\w*)\b",
      60, ["military"], ["threat"]),
    P(r"\bprepar\w+ (\w+ ){0,3}(for )?(\w+ )?escalat\w+|\bescalat\w+ (\w+ ){0,2}(war|conflict|fighting|strikes?)\b",
      62, ["military"], ["threat"]),
    P(r"\bescalat\w+", 48, ["military"], []),
    P(r"\b(seiz(e|es|ed|ing|ure)|hijack(s|ed|ing)?|board(s|ed|ing)?|captur(e|es|ed)) (\w+ ){0,3}(tanker|vessel|ship|cargo ship)s?\b",
      82, ["maritime"], ["kinetic", "maritime_incident"]),
    P(r"\b(tanker|vessel|ship|freighter)s? (was |were |is )?(seized|attacked|hit|struck|ablaze|on fire|explod\w+|sunk|sank|damaged|targeted)",
      82, ["maritime"], ["kinetic", "maritime_incident"]),
    P(r"\b(attack|strike|missile|drone|rocket)s? (on|against|at|targeting) (a |an |the )?(\w+ ){0,2}(tanker|vessel|ship|freighter|cargo ship|warship)s?\b",
      80, ["maritime"], ["kinetic", "maritime_incident"]),
    P(r"\b(limpet )?mines?\b.{0,40}\b(ship|tanker|vessel|strait|harbou?r|port)\b", 72, ["maritime"], ["maritime_incident"]),
    P(r"\b(clos(e|es|ed|ing|ure)|block(s|ed|ing|ade)?|shut(s|ting)?( down)?|mine[sd]?) (\w+ ){0,3}(strait|hormuz)\b",
      85, ["maritime"], ["kinetic", "maritime_incident", "hormuz_closure"]),
    P(r"\bhormuz\b.{0,20}\b(closed|closure|blockade|shut)\b", 85, ["maritime"], ["maritime_incident", "hormuz_closure"]),
    P(r"\bairspace\b.{0,25}\b(closed|closure|shut|closing|reopen\w*)\b|\bclos(e|es|ed|ing) (its |the )?airspace\b",
      80, ["air"], ["airspace"]),
    P(r"\bflights? (suspended|cancell?ed|halted|grounded|diverted)|\b(suspend|cancel|halt)s? (all )?flights?\b"
      r"|\b(rerout\w*|divert\w*|avoid\w*)\b.{0,40}\bairspace\b", 66, ["air"], ["airspace"]),
    P(r"\bevacuat\w*\b.{0,40}\b(embass\w+|consulat\w+|diplomat\w*|staff|citizens|nationals|personnel|troops"
      r"|outposts?|bases?|americans|britons|foreigners|expats|employees|families of)\b"
      r"|\b(embass\w+|consulat\w+|diplomats?|staff|citizens|nationals|personnel|troops|outposts?|bases?|americans"
      r"|foreigners|employees)\b.{0,40}\bevacuat\w*"
      r"|\b(order(s|ed|ing)? (the )?(departure|evacuation)|ordered departure|authorized departure"
      r"|leave (the country |iran |israel |lebanon |iraq )?immediately|shelter in place"
      r"|(non-?emergency|non-?essential) (staff|personnel|employees|diplomats))\b", 76, ["diplomacy"], ["evac"]),
    P(r"\b(travel warning|do not travel|travel advisory|level 4)\b", 58, ["diplomacy"], []),
    P(r"\bevacuat\w+", 52, ["diplomacy"], []),
    P(r"\b(deploy\w*|dispatch\w*|send(s|ing)?|sent|mov(e|es|ed|ing)|head(s|ing|ed)?|sail\w*|arriv\w*|redirect\w*)"
      r" (\w+ ){0,4}(aircraft carriers?|carrier strike groups?|carriers?|bombers?|b-2s?|b-52s?|b-1b?s?|f-35s?|f-22s?"
      r"|fighter jets?|warships?|destroyers?|thaad|patriot batter\w+|submarines?)\b", 72, ["military"], ["deploy"]),
    P(r"\b(aircraft carrier|carrier strike group|b-2 bombers?|b-52 bombers?|stealth bombers?)\b", 62, ["military"], ["deploy"]),
    # military aircraft movements: tankers, airlift, fighters, AWACS (media and flight-tracker reports)
    P(r"\b(deploy\w*|dispatch\w*|send(s|ing)?|sent|mov(e|es|ed|ing)|surg\w+|arriv\w*|land(s|ed|ing)?|fl(y|ies|ew|own)"
      r"|spott?\w*|track\w*|head(s|ing|ed)?|reposition\w*|rotat\w+|bolster\w*|reinforc\w*|station\w*|redeploy\w*)\b"
      r".{0,60}\b(" + AIR + r")\b", 66, ["military", "air"], ["deploy"]),
    P(r"\b(" + AIR + r")\b.{0,50}\b(deploy\w*|arriv\w*|land(s|ed|ing)?|head(s|ing|ed)? (to|for|toward)|spotted"
      r"|cross\w*|surge\w*|en route|redeploy\w*|stationed)\b", 66, ["military", "air"], ["deploy"]),
    P(r"\b(airlift|air bridge)\b", 56, ["military", "air"], ["deploy"]),
    P(r"\b(load\w*|arm(s|ed|ing)|stockpil\w+|pre-?position\w*|mov(e|es|ed|ing))\b.{0,40}\b(missiles?|bombs?|munitions"
      r"|bunker[- ]?bust\w*|tomahawks?|interceptors?)\b.{0,40}\b(warships?|bombers?|bases?|aircraft|submarines?"
      r"|destroyers?|region|middle east)\b", 66, ["military"], ["deploy"]),
    P(r"\bscrambl\w+\b.{0,30}\b(jets|fighters|aircraft|warplanes|interceptors)\b"
      r"|\b(jets|fighters|warplanes|interceptors)\b.{0,20}\bscrambl\w+", 62, ["military", "air"], ["deploy"]),
    P(r"\bultimatum\b", 74, ["statement"], ["ultimatum"]),
    P(r"\b(deadline|days to|hours to|or face)\b", 60, ["statement"], ["ultimatum"]),
    P(r"\b(nuclear test|weapons?-grade|90 ?(%|percent) enrich\w*|withdraw\w* from (the )?(npt|non-proliferation)"
      r"|nuclear (weapon|bomb) (test|breakout)|breakout)\b", 84, ["nuclear"], ["nuclear_red"]),
    P(r"\b(mobiliz\w+|state of emergency|martial law|high alert|maximum alert|full alert|war footing)\b", 70,
      ["military"], ["alert"]),
    P(r"\bprepar\w+ (to|for) (strike|attack|war|retaliat\w+|military action)\b", 76, ["military"], ["kinetic_threat"]),
    P(r"\b(\d+|dozens|hundreds|scores|several|many|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
      r"(\w+\s+){0,2}(killed|dead|died|wounded|injured|martyred|casualties)\b"
      r"|\b(killed|wounded|injured|martyred) (in|by|after|during|when|as)\b", 64, ["military"], []),
    P(r"\b(kill(s|ed)?|dead|deaths|casualties|wounded|injured|martyr\w*)\b", 44, ["military"], []),
    P(r"\b(retaliat\w+|reprisal|revenge|counter-?attack|response will be)\b", 64, ["military"], ["retaliation"]),
    P(r"\bcyber ?-?attacks?\b", 60, ["military"], []),
    # --- significant
    P(r"\b(threat(en|ens|ened|ening)?|warn(s|ed|ing)?|vow(s|ed|ing)?|pledg\w+ to (respond|retaliate|strike))\b", 52,
      ["statement"], ["threat"]),
    P(r"\bsanction\w*\b", 52, ["economy"], ["sanctions"]),
    P(r"\b(designat\w+ .{0,30}terror\w*|blacklist\w*)\b", 52, ["economy"], ["sanctions"]),
    P(r"\b((military|naval|air) )?(drills?|exercises?|war ?games|maneuvers?)\b", 50, ["military"], ["exercise"]),
    P(r"\b(militia|proxy|proxies)\b", 48, ["military"], []),
    P(r"\biaea\b.{0,60}\b(report|resolution|censure|board|inspectors?|access|non-?complian\w+)\b", 54, ["nuclear"], []),
    P(r"\b(enrichment|centrifuges?|uranium stockpile|highly enriched)\b", 50, ["nuclear"], []),
    P(r"\b(snapback|re-?impos\w+ (un )?sanctions)\b", 56, ["nuclear", "economy"], ["sanctions"]),
    P(r"\btalks? (collaps\w+|stall\w*|suspend\w*|fail\w*|break down|broke down|off)\b|\bwalk(ed|s)? out of talks\b"
      r"|\b(end|halt|suspend)(s|ed)? (the )?talks\b", 64, ["diplomacy"], ["talks_fail"]),
    P(r"\b(recall\w* (its |their )?ambassadors?|expel\w* (diplomats?|ambassadors?)|sever\w* (diplomatic )?ties)\b",
      58, ["diplomacy"], []),
    P(r"\b(troops?|forces) (deploy\w*|reinforc\w*|mass(ing|ed)|build-?up)\b|\bmilitary build-?up\b|\breinforcements?\b",
      60, ["military"], ["deploy"]),
    P(r"\b(gps|gnss) (jamming|spoofing|interference)\b", 56, ["maritime", "air"], []),
    P(r"\b(oil|crude|brent)( prices?)? (surg|soar|spik|jump|leap|rall|climb)\w*", 52, ["economy"], ["oil_spike"]),
    P(r"\b(arrest\w*|detain\w*|execut\w+|hang\w*)\b.{0,40}\b(spy|spies|espionage|mossad|cia)\b", 54, ["military"], []),
    P(r"\bhostages?\b", 56, ["military"], []),
    P(r"\bair defen[cs]e\b", 52, ["military"], []),
    # --- low
    P(r"\b(talks?|negotiat\w+|meeting|met with|meets|summit|visit\w*|phone call|spoke with|discuss\w*|dialogue"
      r"|mediat\w+|envoy|proposal|framework|agreement|deal)\b", 30, ["diplomacy"], []),
    P(r"\b(says|said|stated|statement|remarks|told|interview|press conference|briefing)\b", 26, ["statement"], []),
    P(r"\b(econom\w+|inflation|currency|rial|markets?|stocks?|oil exports?)\b", 28, ["economy"], []),
    # Russia and China on the conflict, and Iran's leaders in Moscow or Beijing
    P(r"\b(" + POWERS + r")\b.{0,80}\b(" + REGION + r")\b|\b(" + REGION + r")\b.{0,80}\b(" + POWERS + r")\b", 50,
      ["diplomacy", "statement"], ["powers"]),
    P(r"\b(" + IR_TOP + r")\b.{0,60}\b(moscow|beijing|kremlin|putin|xi|russia|china)\b"
      r"|\b(moscow|beijing|kremlin|putin|xi|russia|china)\b.{0,60}\b(" + IR_TOP + r")\b", 52, ["diplomacy"], ["powers"]),
]

KINETIC_BASE = 70

POWERS_SOFT_CAP = 40.0
CABLE_THREAT_SEV, CABLE_CUT_SEV, CABLE_ATTACK_SEV = 60.0, 64.0, 72.0
_CABLE_FA = re.compile(r"کابل(?:\s*ها(?:ی)?)?\s*(?:اینترنت|فیبر\s*نوری|ارتباطی|مخابراتی|زیر\s*دریایی|زیردریایی|دریایی|داده|انتقال\s*داده)"
                       r"|کابل[^.؛]{0,40}(?:زیر\s*دریا|زیردریایی|کف\s*دریا|بستر\s*دریا)")
_CABLE_EN = re.compile(r"\b(?:undersea|subsea|submarine|underwater|seabed|sea-?floor|fib(?:er|re)[- ]optic|internet|data)"
                       r"\s+(?:communications?\s+)?cables?\b", re.I)
_CABLE_THREAT_FA = re.compile(r"تهدید|هشدار|هدف\s*قرار\s*(?:می\s*گیرند|می\s*گیرد|خواهند|خواهد|دهیم|می\s*دهیم)"
                              r"|قطع\s*(?:می\s*کند|می\s*کنیم|خواهد|خواهیم|کنند)|ممکن|احتمال|نقشه|قادر|خطر|نگرانی"
                              r"|طرح|برنامه|قصد|آماده|در\s*صورت|هدف\s*قرار\s*دادن")
_CABLE_THREAT_EN = re.compile(r"\b(?:threat\w*|warn\w*|could|may|might|vow\w*|plans?|planning|capable|risk\w*|fears?"
                              r"|concerns?|target(?:s|ing)?)\b", re.I)
_CABLE_CUT_FA = re.compile(r"قطع|آسیب|پاره|بریده|خرابکاری|هدف\s*قرار\s*گرفت|اختلال")
_CABLE_CUT_EN = re.compile(r"\b(?:cut|severed|damag\w*|sabotag\w*|disrupt\w*|ruptur\w*|outages?|attacked|struck)\b", re.I)
_CABLE_TALK_FA = re.compile(r"واکنش|جبهه\s*جدید|تحلیل|بررسی|چرا|چگونه|به\s*کجا|\?|؟")
_CABLE_ATTACK_FA = re.compile(r"خرابکاری|هدف\s*قرار\s*گرفت|حمله|عمدی|بریده\s*شد|ترور")
_CABLE_ATTACK_EN = re.compile(r"\b(?:sabotag\w*|attack\w*|deliberate\w*|targeted|struck|hit by)\b", re.I)
_CABLE_REGION_FA = re.compile(r"ایران|سپاه|حوثی|یمن|هرمز|خلیج\s*فارس|دریای\s*سرخ|دریای\s*عمان|دریای\s*عرب|باب\s*المندب"
                              r"|عربستان|امارات|قطر|بحرین|کویت|عمان|خاورمیانه")
_CABLE_REGION_EN = re.compile(r"\b(?:iran\w*|irgc|houthis?|yemen\w*|hormuz|persian gulf|gulf|red sea|gulf of oman|arabian sea"
                              r"|bab el-?mandeb|saudi\w*|emirat\w*|uae|qatar\w*|bahrain\w*|kuwait\w*|oman\w*|middle east)\b",
                              re.I)


def cable(lang, t, s=""):
    """Undersea cables in the region: 'threat' (a threat to cut them), 'attack' (cut on purpose), 'cut' (cut or
    damaged), or None."""
    text = (t or "") + " " + first_sentences(s or "", 220)
    if lang == "fa":
        text = fa_norm(text)
        if not (_CABLE_FA.search(fa_norm(t or "")) and _CABLE_REGION_FA.search(text)):
            return None
        tt = fa_norm(t or "")
        if _CABLE_TALK_FA.search(tt):
            return None                           # a reaction or an analysis, not the event
        if _CABLE_THREAT_FA.search(tt):
            return "threat"
        if not _CABLE_CUT_FA.search(tt):
            return None
        return "attack" if _CABLE_ATTACK_FA.search(text) else "cut"
    if not (_CABLE_EN.search(t or "") and _CABLE_REGION_EN.search(text)):
        return None
    if re.search(r"\b(?:analysis|explainer|why|how|what)\b|\?", t or "", re.I):
        return None
    if _CABLE_THREAT_EN.search(t or ""):
        return "threat"
    if not _CABLE_CUT_EN.search(t or ""):
        return None
    return "attack" if _CABLE_ATTACK_EN.search(text) else "cut"
FAR_CAP = 40.0
_FA_L = "\u0600-\u06FF"
_FAR_FA = re.compile(r"(?<![" + _FA_L + r"])(?:چین|چینی|پکن|هند|هندی|هندوستان|دهلی|هیمالیا|کوبا|هاوانا|ونزوئلا|کاراکاس|تایوان|ژاپن"
                     r"|توکیو|کره|پیونگ\s*یانگ|سئول|فیلیپین|آمریکای\s*لاتین|آفریقا|روسیه|کرملین|مسکو|پوتین|اوکراین)"
                     r"(?![" + _FA_L + r"])")
_FAR_EN = re.compile(r"\b(china|chinese|beijing|india|indian|new delhi|himalaya\w*|cuba\w*|havana|venezuela\w*|taiwan\w*"
                     r"|japan\w*|tokyo|korea\w*|pyongyang|seoul|philippin\w*|south china sea|latin america\w*|africa\w*"
                     r"|russia\w*|kremlin|moscow|putin|ukrain\w*)\b", re.I)
_ME_FA = re.compile(r"ایران|تهران|اسرائیل|اسراییل|صهیونیست|خاورمیانه|خلیج\s*فارس|هرمز|غزه|حماس(?![" + _FA_L + r"])|لبنان"
                    r"|حزب\s*الله|یمن|حوثی|سوریه|عراق|عربستان|سعودی|ریاض|قطر|دوحه|امارات|عمان|بحرین|کویت|اردن|دریای\s*سرخ"
                    r"|نفت|اوپک|برنت|عراقچی|پزشکیان|سپاه|نتانیاهو")
_ME_EN = re.compile(r"\b(iran\w*|tehran|israel\w*|middle east|mideast|persian gulf|gulf|hormuz|gaza|hamas|lebanon|hezbollah"
                    r"|yemen\w*|houthis?|syria\w*|iraq\w*|saudi\w*|riyadh|qatar\w*|doha|emirat\w*|uae|oman\w*|bahrain\w*"
                    r"|kuwait\w*|jordan\w*|red sea|oil|crude|opec\+?|brent|tankers?|araghchi|pezeshkian|irgc|netanyahu)\b",
                    re.I)


_TG = None


def _is_channel(item):
    global _TG
    if _TG is None:
        from .sources import SOURCES
        _TG = {x["id"] for x in SOURCES if x.get("kind") == "tg" or x.get("group") == "tg"}
    return item.get("s") in _TG


def _anchor(lang, t, s):
    """Does a report name the Middle East, Iran's war or oil (title and first sentence)?"""
    text = (t or "") + " " + first_sentences(s or "", 220)
    return bool(_ME_FA.search(fa_norm(text)) if lang == "fa" else _ME_EN.search(text))


def _far(lang, t, s):
    text = (t or "") + " " + first_sentences(s or "", 220)
    return bool(_FAR_FA.search(fa_norm(text)) if lang == "fa" else _FAR_EN.search(text))
# casualty figures inside Yemen (the Saudi-Houthi war, a UN or WHO toll), Lebanon, Gaza, Syria or Jordan: yellow
# stories (_local_toll)
LOCAL_TOLL_CAP = 40.0
_YEM_EN = re.compile(r"\b(yemen\w*|houthis?|sanaa|sana'a|aden|hodeidah|hudaydah|taiz|marib|lahij|saada|abyan|shabwa"
                     r"|hadramout|hadramawt|mokha|dhamar|ibb|amran)\b", re.I)
_YEM_FA = re.compile(fa_norm("یمن|حوثی|انصارالله|صنعا|عدن|الحدیده|حدیده|تعز|مأرب|مارب|لحج|صعده|ابین|شبوه|حضرموت|مخا|ذمار|عمران"))
_TOLL_EN = re.compile(r"\b(killed|kills|kill|dead|deaths?|died|wounded|injured|injures|injuries|casualt\w+|toll|fatalit\w+"
                      r"|martyr\w*|murders?)\b", re.I)
_TOLL_FA = re.compile(fa_norm("کشته|تلفات|زخمی|مجروح|جان باخت|جان‌باخت|شهید|شهادت|شهدا|قربانی|کشتار|مصدوم"))
_SAUDI_PLACE_EN = re.compile(r"\b(riyadh|jeddah|jizan|jazan|najran|abha|taif|mecca|makkah|medina|dammam|khamis|yanbu"
                             r"|ras tanura|abqaiq|inside saudi|in (?:the )?(?:\w+ )?saudi|in the kingdom)\b"
                             r"|\b(attacks?|strikes?|missiles?|drones?|fire\w*|launch\w*)\b[^.;]{0,25}\b(on|at|against|toward|"
                             r"towards|targeting|into) (saudi|the kingdom)", re.I)
_SAUDI_PLACE_FA = re.compile(fa_norm("ریاض|جده|جیزان|جازان|نجران|ابها|طائف|مکه|مدینه|دمام|خمیس|ینبع|راس تنوره|ابقیق|در عربستان|خاک عربستان")
                             + "|" + fa_norm("(?:حمله|حملات|موشک|پهپاد|شلیک)[^.؛]{0,25}(?:به|علیه)\\s*(?:عربستان|خاک سعودی)"))
_BIG_ACTOR_EN = re.compile(r"\b(u\.?s\.?|america\w*|pentagon|centcom|israel\w*|idf|iran(?!-(?:backed|aligned|allied))\w*)\b",
                           re.I)
_BIG_ACTOR_FA = re.compile(fa_norm("آمریکا|امریکا|اسرائیل|اسراییل|صهیونیست|سنتکام|پنتاگون|ایران"))


_FB, _FE = r"(?<![\u0620-\u06FF])", r"(?![\u0620-\u06FF])"
_LEB_EN = re.compile(r"\b(leban\w*|beirut|dahiyeh|dahieh|tyre|sidon|nabatieh|nabatiyeh|bekaa|baalbek|bint jbeil|marjayoun"
                     r"|khiam|hezbollah)\b", re.I)
_LEB_FA = re.compile(_FB + "(?:" + fa_norm("لبنان|بیروت|ضاحیه|صور|صیدا|نبطیه|بقاع|بعلبک|بنت جبیل|مرجعیون|خیام|حزب الله|حزب‌الله")
                     + ")" + _FE)
_GAZA_EN = re.compile(r"\b(gaza\w*|khan younis|khan yunis|rafah|jabalia|jabaliya|deir al-balah|deir el-balah|nuseirat|bureij"
                      r"|maghazi|beit lahia|beit hanoun|hamas)\b", re.I)
_GAZA_FA = re.compile(_FB + "(?:" + fa_norm("غزه|خان یونس|خانیونس|رفح|جبالیا|دیر البلح|نصیرات|بریج|مغازی|بیت لاهیا|بیت حانون|حماس")
                      + ")" + _FE)
_SYR_EN = re.compile(r"\b(syria\w*|damascus|aleppo|homs|hama|idlib|deir ez-zor|deir ezzor|deir al-zor|daraa|deraa|sweida"
                     r"|suwayda|sweyda|latakia|tartus|quneitra|raqqa|hasakah|hasaka|qamishli|palmyra)\b", re.I)
_SYR_FA = re.compile(_FB + "(?:" + fa_norm("سوریه|دمشق|حلب|حمص|حماه|ادلب|دیرالزور|دیر الزور|درعا|سویدا|السویدا|لاذقیه|طرطوس"
                                           "|قنیطره|رقه|حسکه|قامشلی|تدمر") + ")" + _FE)
_JOR_EN = re.compile(r"\b(jordan\w*|amman|irbid|zarqa|aqaba|mafraq|ramtha)\b", re.I)
_JOR_FA = re.compile(_FB + "(?:" + fa_norm("اردن|اربد|زرقا|عقبه|مفرق|رمثا") + ")" + _FE)
# who was killed, when a report gives no figure ("an attack that killed civilians")
_VICTIM_EN = re.compile(r"\b(civilians?|famil(y|ies)|people|children|residents|women|villagers|palestinians|yemenis|lebanese"
                        r"|syrians|jordanians|smugglers)\b", re.I)
_VICTIM_FA = re.compile(fa_norm("غیرنظامی|غیر نظامی|خانواده|کودک|شهروند|مردم|ساکنان|زنان|فلسطینی|یمنی|لبنانی|سوری|قاچاقچی"))
# casualties on Israel's side of the border are not inside Lebanon or Gaza
_ISR_PLACE_EN = re.compile(r"\b(tel aviv|haifa|jerusalem|northern israel|southern israel|in israel|israeli (civilians?|soldiers?"
                           r"|troops)|kiryat|nahariya|metula|sderot|ashkelon|ashdod|galilee)\b"
                           r"|\b(rockets?|missiles?|drones?|attacks?)\b[^.;]{0,25}\b(on|at|into|against|toward) israel", re.I)
_ISR_PLACE_FA = re.compile(fa_norm("تل آویو|حیفا|قدس اشغالی|شمال اسرائیل|جنوب اسرائیل|سرزمین های اشغالی|نظامیان اسرائیلی|سربازان اسرائیلی"
                                   "|نظامی صهیونیست|کریات|نهاریا|متولا|سدیروت|عسقلان|اسدود|الجلیل|شهرک نشین"))
_LEADER_EN = re.compile(r"\b(commander|leader|chief|head of|official|spokesman|secretary[- ]general|top|senior)\b", re.I)
_LEADER_FA = re.compile(fa_norm("فرمانده|رهبر|دبیرکل|مسئول|سخنگو|ارشد|عالی رتبه|مقام"))
_US_IR_EN = re.compile(r"\b(u\.?s\.?|america\w*|pentagon|centcom|iran(?!-(?:backed|aligned|allied))\w*|irgc|quds force"
                       r"|revolutionary guards?)\b", re.I)
_US_IR_FA = re.compile(fa_norm("آمریکا|امریکا|سنتکام|پنتاگون|ایران|سپاه|نیروی قدس|مستشار"))
_COUNT_FA = re.compile(r"[0-9۰-۹]|" + _FB + "(?:" + fa_norm("یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|صدها|ده ها|هزاران|ده‌ها|ده ها تن|چندین") + ")" + _FE)
_COUNT_EN = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|dozens|hundreds|thousands|scores|several)\b", re.I)


def _local_region(fa, t):
    """The region (Yemen, Lebanon, Gaza, Syria, Jordan) a headline is inside of, or None: not when America or Iran is
    involved (nor Israel in Yemen), when it is about the other side of the border (Saudi Arabia, Israel), or when a
    commander or a leader is named. t is the headline, normalised for Persian."""
    if (_US_IR_FA if fa else _US_IR_EN).search(t) or (_LEADER_FA if fa else _LEADER_EN).search(t):
        return None
    if (_YEM_FA if fa else _YEM_EN).search(t):
        if (_SAUDI_PLACE_FA if fa else _SAUDI_PLACE_EN).search(t) or (_BIG_ACTOR_FA if fa else _BIG_ACTOR_EN).search(t):
            return None
        return "yemen"
    for region, rx in (("lebanon", _LEB_FA if fa else _LEB_EN), ("gaza", _GAZA_FA if fa else _GAZA_EN),
                       ("syria", _SYR_FA if fa else _SYR_EN), ("jordan", _JOR_FA if fa else _JOR_EN)):
        if rx.search(t):
            return None if (_ISR_PLACE_FA if fa else _ISR_PLACE_EN).search(t) else region
    return None


_BACKED_FA = re.compile(fa_norm(r"(?:وابسته|مورد حمایت|تحت حمایت|طرفدار|مزدور|مزدوران|حامی)\s*(?:به\s*)?(?:ائتلاف\s*)?(?:عربستان|سعودی|امارات)"))


def _local_headline(lang, t):
    fa = lang == "fa"
    t = fa_norm(t) if fa else re.sub(r"\biran[- ]backed\b", "", t or "", flags=re.I)
    if fa:
        t = t.replace(fa_norm("ایران ساخت"), "")
        t = _BACKED_FA.sub(" ", t)          # "forces backed by Saudi Arabia" are a side inside Yemen, not an attack on it
    return fa, t


def _local_toll(lang, t, s):
    """Casualty figures inside Yemen, Lebanon, Gaza, Syria or Jordan: the region, or None (see _local_region)."""
    fa, t = _local_headline(lang, t)
    if not ((_TOLL_FA if fa else _TOLL_EN).search(t)
            and ((_COUNT_FA if fa else _COUNT_EN).search(t) or (_VICTIM_FA if fa else _VICTIM_EN).search(t))):
        return None
    return _local_region(fa, t)


# the humanitarian situation in those places: hospitals, aid, hunger, disease, people displaced
_HUMAN_EN = re.compile(r"\b(hospitals?|humanitarian|aid (agenc\w+|workers?|groups?|convoys?|deliver\w*)|famine|hunger|starv\w+"
                       r"|malnutrition|malnourished|cholera|outbreaks?|epidemic|displaced|displacement|refugees?"
                       r"|shortages?|medicines?|food (crisis|insecurity|aid)|water (crisis|shortage)|unicef|wfp"
                       r"|health (system|care|workers?)|clinics?)\b", re.I)
_HUMAN_FA = re.compile(fa_norm("بیمارستان|بشردوستانه|کمک رسانی|کمک‌رسانی|امدادرسانی|قحطی|گرسنگی|سوءتغذیه|سوء تغذیه|وبا"
                               "|شیوع|آوارگان|آواره|پناهجو|پناهنده|کمبود دارو|کمبود غذا|کمبود آب|بحران غذا|یونیسف"
                               "|برنامه جهانی غذا|نظام سلامت|کادر درمان|درمانگاه"))
# a headline that tells of an attack is about the attack, not the humanitarian situation
_ATTACKED_EN = re.compile(r"\b(strikes?|struck|airstrikes?|attack\w*|bomb\w*|raids?|shell\w*|hits?|target\w*|shot|fired|"
                          r"missiles?|drones?|storm\w*)\b", re.I)
_ATTACKED_FA = re.compile(fa_norm("حمله|حملات|بمباران|اصابت|هدف|موشک|پهپاد|یورش|گلوله باران|شلیک|تهاجم"))


def _local_humanitarian(lang, t, s):
    """The humanitarian situation inside Yemen, Lebanon, Gaza, Syria or Jordan, told without an attack in the
    headline: the region, or None (see _local_region)."""
    fa, t = _local_headline(lang, t)
    if not (_HUMAN_FA if fa else _HUMAN_EN).search(t) or (_ATTACKED_FA if fa else _ATTACKED_EN).search(t):
        return None
    return _local_region(fa, t)


# a company's financial results ("Sinopec third-quarter profit jumps 64% as oil prices climb"): the oil price is the
# reason, not the news. Not about Iran's own oil revenue or sanctions, and not with an attack or Hormuz in it.
EARNINGS_CAP = 40.0
_EARN_EN = re.compile(r"\b(first|second|third|fourth|q[1-4]|quarter\w*|half-year|first-half|full-year|annual|nine-month)\b"
                      r"[^.;]{0,40}\b(profits?|earnings|revenues?|net income|results|loss(es)?|sales)\b"
                      r"|\b(profits?|earnings|net income|revenues?)\b[^.;]{0,20}\b(jumps?|rises?|rose|falls?|fell|drops?"
                      r"|dropped|surges?|surged|slumps?|slumped|climbs?|climbed|beats?|misses?|missed|doubles?|doubled|soars?"
                      r"|soared|tumbles?|tumbled|plunges?|plunged|declines?|declined)\b|\bdividends?\b|\bearnings (call|report|estimates?|forecasts?)\b"
                      r"|\b(beats?|miss(es)?|tops?|topped)\b[^.;]{0,25}\b(estimates|forecasts|expectations)\b",
                      re.I)
_EARN_FA = re.compile(fa_norm("سود خالص|سود فصلی|سود سه ماهه|سود سه‌ماهه|سود شش ماهه|سود سالانه|درآمد فصلی|درآمد سه ماهه"
                              "|گزارش مالی|صورت های مالی|صورت‌های مالی|ترازنامه|سود سهام|سود هر سهم|زیان خالص"))
_EARN_NOT_EN = re.compile(r"\b(iran\w*|irgc|nioc|sanction\w*|hormuz|attack\w*|strikes?|struck|missiles?|drones?|explosions?"
                          r"|blasts?|seiz\w+)\b", re.I)
_EARN_NOT_FA = re.compile(fa_norm("ایران|سپاه|تحریم|هرمز|حمله|موشک|پهپاد|انفجار|توقیف"))


def _earnings(lang, t):
    fa = lang == "fa"
    t = fa_norm(t) if fa else (t or "")
    return bool((_EARN_FA if fa else _EARN_EN).search(t)) and not (_EARN_NOT_FA if fa else _EARN_NOT_EN).search(t)


# piracy off Somalia, in the Gulf of Aden or the Horn of Africa: far from the war, even when a report links the two.
# Not when the IRGC is involved or it happens in the Persian Gulf, Hormuz or the Gulf of Oman.
PIRACY_CAP = 40.0
_PIRACY_EN = re.compile(r"\b(pirat\w*|piracy)\b", re.I)
_PIRACY_FA = re.compile(fa_norm("دزدی دریایی|دزدان دریایی|دزد دریایی|راهزنی دریایی|راهزنان دریایی"))
_PIRACY_NOT_EN = re.compile(r"\b(irgc|revolutionary guards?|hormuz|persian gulf|gulf of oman|arabian gulf)\b", re.I)
_PIRACY_NOT_FA = re.compile(fa_norm("سپاه|هرمز|خلیج فارس|دریای عمان"))


def _piracy(lang, t):
    fa = lang == "fa"
    t = fa_norm(t) if fa else (t or "")
    return bool((_PIRACY_FA if fa else _PIRACY_EN).search(t)) and not (_PIRACY_NOT_FA if fa else _PIRACY_NOT_EN).search(t)


# a memoir or a profile of the dead ("ناگفته‌های همسر شهید ظفرمند…", a martyr's family, a will, memoirs): told after
# the event, not an event. Read in the headline only.
TRIBUTE_CAP = 40.0
_TRIB_FA = re.compile(fa_norm("ناگفته") + "|" + fa_norm("(?:همسر|مادر|پدر|فرزند|فرزندان|خانواده|دختر|پسر)")
                      + r"\s*(?:" + fa_norm("پاسدار") + r"\s*)?" + fa_norm("شهید") + "|"
                      + fa_norm("زندگی") + r"\s*" + fa_norm("نامه") + "|" + fa_norm("سیره") + r"\s*" + fa_norm("شهید")
                      + "|" + fa_norm("وصیت") + r"\s*" + fa_norm("نامه") + "|" + fa_norm("خاطرات"))
_REL_EN = (r"(?:family|families|wife|husband|children|child|sons?|daughters?|parents|mother|father|brothers?|sisters?"
           r"|relatives|loved ones|fianc[eé]e?)")
_TRIB_EN = re.compile(r"\b(untold stor\w*|widow of|tribute to|remembering)\b"
                      # the story of victims: "Iranian man whose 12 family members were killed", "who lost his wife"
                      r"|\bwhose\b[^.;:]{0,25}\b" + _REL_EN + r"\b|\bwho lost\b"
                      r"|\blost (?:his|her|their|my) (?:\w+ ){0,2}" + _REL_EN + r"\b"
                      r"|\b" + _REL_EN + r" (?:members )?(?:were |was )?killed\b[^.;]{0,10}$"
                      r"|\b(?:widow|widower|orphan)\w*\b|\bsurvivors? (?:recall|recount|describe)"
                      # looking back: "43 years after Beirut terror attack…"
                      r"|\b\d+ years after\b", re.I)


def _tribute(lang, t):
    fa = lang == "fa"
    return bool((_TRIB_FA if fa else _TRIB_EN).search(fa_norm(t) if fa else (t or "")))


# hijab and dress-code enforcement inside Iran (a prosecutor calling on the IRGC to enforce it, arrests over it): a
# domestic matter, yellow, even when the IRGC or a "warning" is in the headline
# a statement of clerics (the seminary, Friday prayer leaders, grand ayatollahs): a yellow story, unless it tells of
# an attack
CLERIC_CAP = 40.0
_CLERIC_FA = re.compile(fa_norm("جامعه مدرسین|حوزه علمیه|حوزه های علمیه|حوزه‌های علمیه|مراجع تقلید|مرجع تقلید|امام جمعه"
                                "|ائمه جمعه|خطیب نماز جمعه|خطیب جمعه|مجمع جهانی اهل بیت|مجمع جهانی تقریب|علمای |روحانیون"))
_CLERIC_EN = re.compile(r"\b(seminar(y|ies)|friday prayer (leader|imam|sermon)|grand ayatollah|marja\w*|clerics?)\b", re.I)


def _cleric(lang, t):
    fa = lang == "fa"
    return bool((_CLERIC_FA if fa else _CLERIC_EN).search(fa_norm(t) if fa else (t or "")))


# mediators in Tehran in person: who comes, and that they have come (not "ready to mediate", "will visit")
MEDIATOR_VISIT_SEV = 55.0
_MED_WHO_EN = (r"(?:qatar\w*|oman\w*|saudi\w*|pakistan\w*|russia\w*|chin(?:a|ese)|egypt\w*|turk\w*|iraq\w*"
               r"|mecca|makkah|mediators?|delegations?|envoys?|emissar\w*|asim munir|bin salman|lavrov|wang yi)")
_MED_EN = re.compile(r"\b" + _MED_WHO_EN + r"\b[^.;?]{0,60}?\b(?:arriv\w* (?:in|at)|land\w* in|(?:are|is|were|was) (?:present )?in"
                     r"|in|visit(?:s|ed)?|return(?:s|ed)? to|travel+ed to|came to|heads? to|reach\w*)\s+tehran\b"
                     r"|\btehran\b[^.;?]{0,20}\b(?:hosts?|hosted|receives?|received|welcomes?|welcomed)\b[^.;?]{0,30}\b"
                     + _MED_WHO_EN, re.I)
_MED_NOT_EN = re.compile(r"\b(?:will|would|could|may|might|to visit|to travel|plans?|planned|ready|readiness|expected|set to"
                         r"|ahead of|upcoming|purpose|aim\w*|offers? to|proposes?|invit\w*|on (?:its|their) way|to (?:meet|hold|begin|arrive|head|go|attend|join)"
                         r"|due|next|tomorrow|before|on (?:mon|tues|wednes|thurs|fri|satur|sun)day)\b", re.I)
_MED_WHO_FA = ("(?:قطر|عمان|عربستان|سعودی|پاکستان|روسیه|چین|مصر|ترکیه|عراق|پیمان مکه|توافق مکه|میانجی|هیئت|هیات|فرستاده"
               "|عاصم منیر|بن سلمان|لاوروف|وانگ یی)")
_MED_FA = re.compile(fa_norm(_MED_WHO_FA + "[^.؛؟?]{0,60}?(?:وارد تهران شد|به تهران سفر کرد|به تهران آمد|به تهران آمدند"
                                           "|به تهران رسید|در تهران حضور|در تهران است|در تهران هستند|عازم تهران شد"
                                           "|به تهران بازگشت|وارد تهران شدند|به تهران سفر کردند|به تهران رسیدند"
                                           "|عازم تهران شدند)|(?:ورود|سفر|حضور)[^.؛؟?]{0,15}" + _MED_WHO_FA
                             + "[^.؛؟?]{0,30}(?:به|در) تهران"))
_MED_NOT_FA = re.compile(fa_norm("آماده|آمادگی|قرار است|خواهد|خواهند|در راه|هدف|با هدف|دعوت|پیشنهاد سفر|احتمال|ممکن|فردا|آینده|پیش از|قبل از"))


def _mediator_visit(lang, t):
    fa = lang == "fa"
    t = fa_norm(t) if fa else (t or "")
    if fa:
        return bool(_MED_FA.search(t)) and not _MED_NOT_FA.search(t)
    return bool(_MED_EN.search(t)) and not _MED_NOT_EN.search(t)


HIJAB_CAP = 40.0
_HIJAB_FA = re.compile(fa_norm("حجاب|عفاف|بدحجاب|بی حجاب|کشف حجاب|گشت ارشاد|پلیس اخلاق|قانون پوشش|پوشش اسلامی"))
_HIJAB_EN = re.compile(r"\b(hijab|headscarf|headscarves|morality police|dress code|chastity)\b", re.I)


def _hijab(lang, t):
    fa = lang == "fa"
    return bool((_HIJAB_FA if fa else _HIJAB_EN).search(fa_norm(t) if fa else (t or "")))


# a headline that strings several items together (a newsletter, a briefing, "…, and other Mideast news"): its own
# stories carry the news, so the bundle is yellow and not an attack. "U.S. and Israel" is not a second item: the
# second sentence must start with "And," or "Plus,".
DIGEST_CAP = 40.0
_DIGEST_EN = re.compile(r"[.;!?]\s+(?:And|Plus|Also),\s"
                        r"|(?i:\band other (?:\w+ ){0,2}news\b|\b(?:morning|evening|daily|weekly|news) (?:briefing|brief"
                        r"|digest|roundup|round-up|wrap)\b|\bnewsletter\b|\btop (?:stories|news|headlines)\b"
                        r"|\bnews in brief\b|\bwhat to know (?:today|this week)\b)")
_DIGEST_FA = re.compile(fa_norm("صبحانه خبری|خلاصه اخبار|مرور اخبار|مروری بر مهم ترین|مهم ترین اخبار|گزیده اخبار"
                                "|سرخط خبرها|سر خط خبرها|و دیگر اخبار|و سایر اخبار"))


def _digest(lang, t):
    fa = lang == "fa"
    return bool((_DIGEST_FA if fa else _DIGEST_EN).search(fa_norm(t) if fa else (t or "")))


# another market whose move the oil price only helps explain ("Copper Declines as Tech Selloff, Oil Rally Dent Risk
# Appetite"): the headline begins with that market, so it is not an oil price spike. Oil first stays as it is.
MARKET_CAP = 40.0
_MKT_EN = re.compile(r"^\W*(copper|gold|silver|platinum|palladium|alumin(i)?um|nickel|zinc|iron ore|base metals?|metals?"
                     r"|stocks?|equities|shares|bonds?|treasur\w+|yields?|dollar|yen|euro|sterling|pound|rupee|yuan"
                     r"|currenc\w+|bitcoin|crypto\w*|wheat|corn|soybeans?|palm oil|wall street|nikkei|ftse|s&p|dow"
                     r"|nasdaq|asian (stocks|shares|markets)|european (stocks|shares)|emerging[- ]market\w*)\b", re.I)
_MKT_FA = re.compile(r"^\W*(?:" + "|".join(fa_norm(x) for x in ("مس", "طلا", "نقره", "پلاتین", "آلومینیوم", "نیکل",
                     "فلزات", "سهام", "بورس", "اوراق", "دلار", "ین", "یورو", "پوند", "روپیه", "یوان", "ارز", "بیت کوین",
                     "رمزارز", "گندم", "ذرت", "وال استریت", "شاخص")) + r")(?![" + "ؠ-ۿ" + r"])")


def _other_market(lang, t):
    fa = lang == "fa"
    return bool((_MKT_FA if fa else _MKT_EN).search(fa_norm(t) if fa else (t or "")))


CIVIL_DRILL_CAP = 35.0
_CIVIL_FA = re.compile(r"خدمت\s*فاطمی|درمان|پزشک|دندان|سلامت|بهداشت|امداد|هلال\s*احمر|آتش\s*نشان|اطفا|زلزله|سیل|"
                       r"مدیریت\s*بحران|اورژانس|بیمارستان|جهادی|محرومیت|کمک\s*مومنانه|خدمت\s*رسانی|دانش\s*آموز|مدارس")
_MIL_FA = re.compile(r"نیروی\s*(?:زمینی|دریایی|هوایی|هوافضا)|ارتش|موشک|پهپاد|ناو|جنگنده|توپخانه|تانک|زرهی|تکاور|رزمی"
                     r"|پدافند\s*هوایی|اقتدار|ذوالفقار|پیامبر\s*اعظم|سپاه\s*پاسداران|قرارگاه|نظامی")
_CIVIL_EN = re.compile(r"\b(medical|health|clinic\w*|dental|emergency services|fire\s?fighters?|fire brigade|earthquake|"
                       r"disaster|rescue|red crescent|hospital\w*|relief)\b", re.I)
_MIL_EN = re.compile(r"\b(military|naval|navy|army|air force|missiles?|drones?|warships?|irgc|troops|combat|war ?games|"
                     r"live[- ]fire|fighter|tanks?|artillery)\b", re.I)


# a "drill" that is a rally: Basij or townspeople gathering to show support ("رزمایش جان‌فدایان", "اقتدار مردمی")
_RALLY_FA = re.compile(r"جان\s*فدا|مردمی|بسیج|حماسی|حماسه|اجتماع|همایش|راهپیمایی|مردم\s")
_HARD_MIL_FA = re.compile(r"نیروی\s*(?:زمینی|دریایی|هوایی|هوافضا)|ارتش|موشک|پهپاد|ناو|جنگنده|توپخانه|تانک|زرهی|تکاور"
                          r"|پدافند|شلیک|تیراندازی|قرارگاه")


def _civil_drill(lang, t, s):
    """A drill of doctors, rescuers or firefighters, or a rally called a drill, with nothing military in the title or
    first sentence."""
    text = (t or "") + " " + first_sentences(s or "", 220)
    if lang == "fa":
        text = fa_norm(text)
        if _RALLY_FA.search(text) and not _HARD_MIL_FA.search(text):
            return True
        return bool(_CIVIL_FA.search(text)) and not _MIL_FA.search(text)
    return bool(_CIVIL_EN.search(text)) and not _MIL_EN.search(text)
_TENSION_EN = re.compile(
    r"\b(wars?|warfare|strik\w*|attack\w*|military|missiles?|nuclear|enrich\w*|uranium|weapons?|arms|drones?|fighter"
    r"|s-400|su-35|air defen[cs]e|aggression|threat\w*|conflicts?|tensions?|escalat\w*|ceasefire|truce|peace|crisis"
    r"|security|blockade|sanction\w*|hormuz|persian gulf|gulf|middle east|region\w*|israel\w*|netanyahu|zionist"
    r"|gaza|lebanon|hezbollah|yemen|houthis?|syria|iraq|oil|opec\+?|crude|mediat\w*"
    r"|america\w*|washington|trump|pentagon|white house|diplomatic solution\w*|security council|united nations|iaea"
    r"|iran(ian)? (issue|question|file|crisis|situation|conflict|programme|program))\b"
    r"|(?<![A-Za-z])(U\.?S\.?A?|UN|UNSC)(?![A-Za-z])", re.I)
_TENSION_FA = re.compile(
    r"جنگ|حمله|حملات|نظامی|موشک|هسته|غنی\s*سازی|اورانیوم|سلاح|تسلیحات|پهپاد|جنگنده|سوخو|اس\s*-?\s*[۴4]۰۰|پدافند"
    r"|تجاوز|تهدید|درگیری|تنش|آتش\s*بس|صلح|بحران|امنیت|محاصره|تحریم|هرمز|خلیج\s*فارس|خاورمیانه|منطقه"
    r"|اسرائیل|اسراییل|نتانیاهو|صهیونیست|غزه|لبنان|حزب\s*الله|یمن|حوثی|سوریه|عراق|نفت|اوپک|میانجی"
    r"|آمریکا|امریکا|واشنگتن|ترامپ|پنتاگون|کاخ\s*سفید|سازمان\s*ملل|آژانس|راه\s*حل\s*دیپلماتیک|راهکار\s*دیپلماتیک"
    r"|(?:موضوع|مسئله|مساله|پرونده)\s*(?:هسته\s*ای\s*)?ایران")


def _tension(lang, t, s):
    """Does a report touch the war, America, Israel, the region's conflicts or oil? (title and first sentence)"""
    text = (t or "") + " " + first_sentences(s or "", 220)
    if lang == "fa":
        return bool(_TENSION_FA.search(fa_norm(text)))
    return bool(_TENSION_EN.search(text))

DENIAL = re.compile(r"\b(den(y|ies|ied|ying)(?! (access|entry|permission|visas?|requests?|them|it access))|rejects? (the )?(report|claim)s?|no plans?|rules? out|not (planning|seeking|interested)"
                    r"|false|fake|dismiss\w*|baseless|rumou?rs?|hoax|debunk\w*)\b", I)
SPEC = re.compile(r"\b(could|may|might|would|if|consider\w*|weigh(s|ing)?|mull\w*|possible|potential|risk of|fears? of"
                  r"|threat of|plan(s|ning)? to|options?)\b", I)
PAST = re.compile(r"\b(anniversary|years? ago|decades? ago|commemorat\w+|memorial|in (19|20)\d\d|recalls?|history of"
                  r"|look back|lessons from|a year after|one year on)\b", I)
OPINION = re.compile(r"^(opinion|op-ed|editorial|commentary|letters?)\b|\|\s*opinion|\bopinion:|^view:|^comment:", I)
ANALYSIS = re.compile(r"^(analysis|explainer|explained|q&a|podcast|newsletter|the big story|in charts|fact check)\b"
                      r"|\b(what to know|what we know|why it matters|how .{3,40} could|what .{3,40} means)\b", I)
LIVE = re.compile(r"^(live|live updates|live:|breaking)\b", I)
REACTION = re.compile(r"\b(condemn\w*|denounc\w*|deplor\w*|condolence\w*|sympath\w*|solidarity|unacceptable"
                      r"|calls? for (restraint|calm|de-?escalation)|urg(e|es|ed) restraint|welcom\w*|express\w* concern)\b", I)
HYPO = re.compile(r"\b(threat\w*|warn\w*|vow\w*|could|would|may|might|if|unless|prepar\w+|plan\w*|plot\w*"
                  r"|consider\w*|ready to|possible|possibility|scenario|restart\w*|resum\w*|fresh|renew\w*"
                  r"|push(es)? (for|to)|seeks?|wants? to|calls? for|weigh\w*|mull\w*|options?|draw(n|s)? up|drafts?"
                  r"|cards?|leverage|means|would mean)\b", I)
QUESTION = re.compile(r"[?؟]\s*(\W*$|[|/:-])")
# a question headline stays orange only when it asks about war or peace (an attack, a strike, an explosion, missiles,
# a ceasefire, peace) and names Iran, America or Israel; any other question is analysis or background: yellow
QUESTION_CAP = 44.0
Q_WAR = re.compile(r"\b(attack\w*|strikes?|struck|air ?strikes?|bomb\w*|explosions?|blasts?|missiles?|rockets?"
                   r"|drone strikes?|intercept\w*|retaliat\w*|invasion|invade\w*|ceasefire|cease-fire|truce|peace)\b", I)
Q_SIDE = re.compile(r"\b(iran\w*|tehran|irgc|u\.?s\.?|us|america\w*|washington|pentagon|trump|israel\w*|idf"
                    r"|netanyahu|tel aviv)\b", I)
# controlled detonations of unexploded ordnance: loud, but not an attack
CONTROLLED = re.compile(r"\b(non-?functional|unexploded|unfired|un-?detonated|controlled (explosions?|detonations?)"
                        r"|defus\w+|bomb disposal|ordnance|munitions? (clearance|disposal)|clearing (mines|munitions)"
                        r"|destruction of (\w+ ){0,3}(ammunition|munitions?|shells|bombs))\b", I)
# fact-checks and debunks of attack claims
FACTCHECK = re.compile(r"\b(does not show|doesn't show|did not show|didn't show|outdated (video|footage|image|photo)s?"
                       r"|old (video|footage)|fact[- ]?check\w*|misleading|miscaptioned|false claims?|no evidence of"
                       r"|is not from|isn't from)\b", I)
# words attacking a person: a speech, not a strike
VERBAL = re.compile(r"\b(strongly|sharply|harshly|verbally|fiercely)\s+(attack\w*|criticiz\w+)"
                    r"|\b(attack(s|ed|ing)?|slam(s|med)?|blast(s|ed)?|lash(es|ed)? out at|rebuk\w+)\s+(\w+\s+){0,2}"
                    r"(trump|biden|obama|netanyahu|khamenei|pezeshkian|araghchi|vance|rubio|harris|macron|starmer|erdogan"
                    r"|putin|the (president|government|prime minister|minister|administration|opposition))\b", I)
_EN_ATTACK = re.compile(r"\battack(s|ed|ing)?\b", I)
_EN_CRIT = re.compile(r"\b(criticiz\w*|criticis\w*|slamm?(s|ed|ing)?|lambast\w*|rebuk\w*|insult\w*|mock\w*"
                      r"|derid\w*|verbal\w*|tirade|rant\w*|war of words|swipe at|lash(es|ed)? out)\b", I)
_EN_CONCRETE = re.compile(r"\b(missiles?|drones?|rockets?|air ?strikes?|strikes?|bomb\w*|explosions?|blasts?|killed"
                          r"|wounded|injured|casualt\w+|bases?|ships?|tankers?|vessels?|troops|soldiers|artillery"
                          r"|air defen\w+|intercept\w*|shell\w*|gunmen|armed|embass\w+|facilit\w+|refiner\w+"
                          r"|airports?|ports?|convoy|hospital|military)\b", I)


def _verbal_attack(t, s):
    """'X attacks Y' with criticism words and nothing concrete (weapons, casualties, targets) around it."""
    lead = t + " " + (s or "")[:300]
    return bool(_EN_ATTACK.search(t) and _EN_CRIT.search(lead) and not _EN_CONCRETE.search(lead))


# "Foreign Policy: …", "The Economist: …" — Persian outlets summarising foreign commentary
MEDIA_CITE = re.compile(r"^(the )?(new york times|wall street journal|washington post|financial times|foreign policy"
                        r"|foreign affairs|economist|bloomberg|politico|axios|atlantic|haaretz|guardian|telegraph"
                        r"|times of israel|jerusalem post|cnn|fox news|al[- ]?monitor|middle east eye|newsweek|time"
                        r"|national interest|responsible statecraft|hill)( magazine| newspaper)?( claim| report| analysis)?\s*:", I)
EXTRA_ANALYSIS = re.compile(r"\b(interview|in conversation|podcast|poll|polls|survey|op-ed|column|watch:|review:)\b"
                            r"|^(watch|listen|video)\b", I)
ACTOR = re.compile(r"\b(trump|president|khamenei|supreme leader|netanyahu|prime minister|irgc|revolutionary guards?"
                   r"|pentagon|hegseth|centcom|idf|army chief|commander)\b", I)
TARGET = re.compile(r"\b(hormuz|nuclear (site|facility|facilities|plant)|natanz|fordow|isfahan|bushehr|dimona|tehran"
                    r"|tel aviv|kharg|ras tanura|abqaiq|refiner(y|ies)|oil (facility|facilities|field|terminal)"
                    r"|embassy|al udeid|al dhafra|ain al-asad|airbase|air base|naval base|power plant)\b", I)
CASUALTIES = re.compile(r"\b(\d{1,5})\s+(people |civilians |soldiers |troops |sailors |crew )?(killed|dead|died)\b", I)

_IMAGINE_EN = re.compile(r"^\W*(?:just\s+)?imagine\b|^\W*think (?:about|of) (?:it|this|that)\b", re.I)


# a channel admin's own aside, not news: "به نظرم…", "فکر می‌کنم…", "اگر X بشود Y می‌شود…", "فرض کنید…", "شاید…"
_ASIDE_FA = re.compile(fa_norm(
    r"^[^\u0600-\u06FFA-Za-z0-9]*(?:به نظرم|بنظرم|به نظر من|بنظر من|به نظر بنده|به نظر می رسد|بنظر میرسد|به نظر میرسه"
    r"|فکر می ?کنم|فکر میکنم|فکر کنم|فکرکنم|من فکر|گمانم|گمان می ?کنم|گمونم|حدس می ?زنم|حدسم|احساس می ?کنم|حسم"
    r"|معتقدم|من معتقدم|شخصا|به شخصه|به گمانم|به عقیده من|از نظر من|راستش|بعید نیست|بعید میدونم|شاید|نکنه|نکند"
    r"|یعنی ممکنه|یعنی میشه|ممکنه|احتمالش|اگه|اگر|چنانچه|در صورتی که|فرض کنیم|فرض کن|فرض کنید|فرضا|فرضاً|بیایید فرض"
    r"|فکر کنید|فکرشو بکنید|فکرش را بکنید|فکرش رو بکنید|تصور کنید|تصور کن|تصورش|فکر کن|جالبه|خدا کنه"
    r"|امیدوارم|کاش|ای کاش)(?![\u0600-\u06FF])"))
_ASIDE_EN = re.compile(r"^\W*(?:i think|i believe|i guess|i suspect|i feel|i bet|i doubt|i hope|in my (?:opinion|view)|imo|imho"
                       r"|personally|my guess|my take|let'?s (?:say|assume|suppose)|suppose|supposing|assume|assuming"
                       r"|what if|if|maybe|perhaps|just imagine|imagine|think (?:about|of) (?:it|this|that)|wonder if"
                       r"|hopefully|wouldn'?t it)\b", re.I)


def aside(text):
    """A channel post that is its admin's own opinion or what-if, not news. Only for Telegram channels: a news
    headline starting "If…" or "Maybe…" is read by the usual rules."""
    t = text or ""
    return bool(_ASIDE_FA.search(fa_norm(t)) or _ASIDE_EN.search(t))


def score_en(title: str, summary: str):
    t, s = title or "", summary or ""
    best, topics, flags, kinetic_in_title, title_best = 0.0, set(), set(), False, 0.0
    for rx, base, tp, fl in PATTERNS:
        if rx.search(t):
            val = base
            title_best = max(title_best, base)
            if base >= KINETIC_BASE:
                kinetic_in_title = True
        elif s and rx.search(s):
            val = base * (0.78 if base >= KINETIC_BASE else 0.9)
        else:
            continue
        topics |= tp
        flags |= fl
        best = max(best, val)
    if best == 0:
        best = 22.0
    if DENIAL.search(t) and best >= 45:
        best *= 0.65
        flags.add("denial")
    if kinetic_in_title and SPEC.search(t) and "kinetic_threat" not in flags:
        best *= 0.82
        flags.add("speculative")
    if PAST.search(t) or PAST.search(s[:160]):
        best *= 0.6
        flags.add("past")
    if ACTOR.search(t) and flags & {"ultimatum", "kinetic_threat"}:
        best += 6
    elif ACTOR.search(t) and flags & {"threat", "retaliation"}:
        best = max(best, min(best + 6, 68))      # a leader's threat is serious, but not a strike
    if TARGET.search(t) and flags & {"kinetic", "maritime_incident"}:
        best += 6
    m = CASUALTIES.search(to_latin_digits(t + " " + s[:200]))
    if m:
        n = int(m.group(1))
        best += 10 if n >= 50 else 6 if n >= 10 else 0
    if CONTROLLED.search(t) or CONTROLLED.search(s[:200]):
        best = min(best, 40)
        flags -= HARD_EVENTS
        flags.add("controlled")
    if FACTCHECK.search(t):
        best = min(best, 38)
        flags -= HARD_EVENTS
        flags.add("denial")
    if VERBAL.search(t) or _verbal_attack(t, s):
        best = min(best, 40)
        flags -= HARD_EVENTS
    if title_best < 45:
        best = min(best, 52)                       # nothing notable in the headline itself
    if MEDIA_CITE.search(t):
        best = min(best, 56)
        flags.add("analysis")
    if flags & HARD_EVENTS and not _strong_kinetic(t) and (HYPO.search(t) or _quote(t)):
        best = min(best, 66 if HYPO.search(t) else 64)   # "threatens to strike", "plans attacks", "X: …attack…"
        flags -= HARD_EVENTS
        flags |= {"speculative", "threat"} if HYPO.search(t) else {"quote"}
    if REACTION.search(t):
        best = min(best, 54)                       # reactions to an event rank below the event itself
        flags.add("reaction")
        flags.discard("kinetic")
    if QUESTION.search(t):
        if Q_WAR.search(t) and Q_SIDE.search(t):
            best = min(best, 56)                   # a question about an attack, a missile, peace… of Iran, the US, Israel
            flags.add("speculative")
        else:
            best = min(best, QUESTION_CAP)         # any other question in a headline: analysis, background
            flags -= HARD_EVENTS
            flags |= {"speculative", "analysis"}
    if OPINION.search(t) or _IMAGINE_EN.search(t):
        best = min(best, 38)
        flags.add("opinion")
        if _IMAGINE_EN.search(t):
            flags -= HARD_EVENTS            # "Imagine Iran declaring war on the Houthis!": an aside, nothing happened
    elif (ANALYSIS.search(t) or EXTRA_ANALYSIS.search(t)) and not LIVE.search(t):
        best = min(best, 44)
        flags.add("analysis")
    return max(5.0, min(98.0, best)), topics, flags


HARD_EVENTS = {"kinetic", "maritime_incident", "hormuz_closure", "nuclear_red"}
_STRONG = re.compile(r"\b(struck|bombed|killed|launch(ed|es)|fired|intercepted|intercepts|shot down|exploded|attacked"
                     r"|seized|seizes|pounded|hits|downs|downed|explosions?|sirens?|casualties|closed|closes|shut"
                     r"|blocked|announc\w+ withdrawal|withdr[ae]w)\b", I)
_QUOTE = re.compile(r"^([^:：]{2,45})[:：]\s")
_NOT_SPEAKER = re.compile(r"\b(live|updates?|war|crisis|breaking|watch|video|report|exclusive|analysis)\b", I)


def _quote(t):
    """'Araghchi: …' — a statement whose words may mention attacks without reporting one."""
    m = _QUOTE.match(t or "")
    return bool(m) and not _NOT_SPEAKER.search(m.group(1))


def _strong_kinetic(t):
    """A completed action in the headline keeps an item kinetic even if it also says 'warns' or 'could'."""
    return {"kinetic"} if _STRONG.search(t) else set()


def _head(t, s, limit=170):
    """Only the start of a very long headline counts as headline; the rest is scored like the summary."""
    if len(t) <= limit:
        return t, s
    return t[:limit], (t[limit:] + " " + s).strip()


_DIGEST_SEP = re.compile(r"\s*/\s+")


def _digest_part(t, s, lang):
    """A summary that strings several items together ("A/ B/ C", as some Persian outlets write): only the item about
    the headline counts, or none if no item is, so the other items' people, places and events don't join it."""
    parts = [x for x in _DIGEST_SEP.split(s or "") if x.strip()]
    if len(parts) < 2 or sum(len(x) >= 20 for x in parts) < 2:
        return s
    norm = fa_norm if lang == "fa" else str.lower
    words = lambda x: {w for w in re.findall(r"\w{3,}", norm(x))}  # noqa: E731
    tw = words(t)
    best = max(parts, key=lambda x: len(words(x) & tw))
    return best if len(words(best) & tw) >= 2 else ""


def classify(item):
    """Fill severity, topics, flags, people, places, countries on an item. Each report is read in its own
    language: a Persian report by the Persian rules and lexicon on its original text (its English translation is
    only for display and for matching it with foreign reports), anything else by the English rules."""
    if item.get("wit"):
        # citizen reports relayed by a channel: severity from how many people report what, and where (witness.py)
        sev, flags = witness.score(item["wit"])
        item["sev"], item["flags"], item["topics"] = sev, sorted(flags), ["military"]
        t, s = item.get("ti") or "", item.get("su") or ""
        item["ppl"] = []
        item["geo"] = match_keys(PLACES_RX, item.get("en_ti") or "", t)
        item["ctry"] = sorted(set(match_keys(COUNTRIES_RX, item.get("en_ti") or "", t)) | {"ir"})
        return item
    if item.get("lang") == "fa":
        t, s = _head(item.get("ti") or "", strip_dateline(item.get("su") or ""))
        s = _digest_part(t, s, "fa")
        sev, topics, flags = score_fa(t, s)
        en_t = en_s = ""
        fa_t, fa_s = t, s
    else:
        en_t, en_s = _head(item.get("en_ti") or item.get("ti") or "",
                           strip_dateline(item.get("en_su") or item.get("su") or ""))
        en_s = _digest_part(en_t, en_s, "en")
        sev, topics, flags = score_en(en_t, en_s)
        fa_t = fa_s = ""
    if item.get("via") == "tg" and aside(fa_t or en_t):
        # a channel admin's own opinion or what-if: yellow, and never an event
        sev = min(sev, 38)
        flags = (set(flags) - HARD_EVENTS) | {"opinion"}
    title_topics = match_keys(TOPICS_RX, en_t, fa_t)
    body_topics = [k for k in match_keys(TOPICS_RX, en_s, fa_s) if k != "statement"]
    topics |= set(title_topics) | set(body_topics)
    if "statement" in topics and not ({"statement"} & set(title_topics)) and "threat" not in flags:
        topics.discard("statement")
    if saudi_houthi(fa_t if item.get("lang") == "fa" else en_t, item.get("lang") or "en", flags) == "secondary":
        flags = set(flags) | {"secondary"}       # on the Saudi-Houthi front only direct attacks are red
        sev = min(sev, 69.0)
    net = internet("fa", fa_t, fa_s) if item.get("lang") == "fa" else internet("en", en_t, en_s)
    if net and "opinion" not in flags:
        flags = set(flags) | {"internet"}        # Iran's internet cut, throttled or restored: an orange story
        topics = set(topics) | {"net"}
        sev = max(sev, 46.0 if "analysis" in flags else net_severity(net))
    lang = "fa" if item.get("lang") == "fa" else "en"
    if sport.story(lang, fa_t or en_t, fa_s or en_s) == "sport":
        # a match called off or a team that won't travel for fear of the war is a yellow story, not a strike
        flags = (set(flags) - HARD_EVENTS) | {"sport"}
        sev = min(sev, sport.CAP)
    cb = cable(lang, fa_t or en_t, fa_s or en_s)
    if cb:
        # undersea internet cables in the region: a threat to cut them, or cables cut or damaged
        topics = set(topics) | {"net", "maritime"}
        if cb == "threat":
            flags = (set(flags) - {"internet"}) | {"threat", "cable"}      # a threat, not Iran's internet cut
            sev = max(sev, CABLE_THREAT_SEV)
        else:
            flags = set(flags) | {"cable", "cable_cut"} | ({"maritime_incident"} if cb == "attack" else set())
            sev = max(sev, CABLE_ATTACK_SEV if cb == "attack" else CABLE_CUT_SEV)
    if "exercise" in flags and _civil_drill(lang, fa_t or en_t, fa_s or en_s):
        # a medical, relief or fire-brigade drill (free clinics, earthquake or chemical-spill rescue): not military
        flags = (set(flags) - {"exercise"}) | {"civil_drill"}
        topics = set(topics) - {"military"}
        sev = min(sev, CIVIL_DRILL_CAP)
    if _local_toll(lang, fa_t or en_t, fa_s or en_s):
        # casualty figures inside Yemen, Lebanon, Gaza, Syria or Jordan: a yellow story
        flags = (set(flags) - HARD_EVENTS) | {"local_toll"}
        sev = min(sev, LOCAL_TOLL_CAP)
    elif _local_humanitarian(lang, fa_t or en_t, fa_s or en_s):
        # the humanitarian situation there (hospitals, aid, hunger, disease, the displaced): a yellow story
        flags = (set(flags) - HARD_EVENTS) | {"local_toll"}
        sev = min(sev, LOCAL_TOLL_CAP)
    if _earnings(lang, fa_t or en_t):
        # a company's financial results: a yellow story, whatever the oil price did
        flags = (set(flags) - HARD_EVENTS - {"oil_spike"}) | {"earnings"}
        sev = min(sev, EARNINGS_CAP)
    if _hijab(lang, fa_t or en_t):
        flags = (set(flags) - HARD_EVENTS - {"threat", "ultimatum"}) | {"domestic"}
        sev = min(sev, HIJAB_CAP)
    if _mediator_visit(lang, fa_t or en_t) and not set(flags) & {"speculative", "analysis", "opinion", "past",
                                                                     "denial", "reaction"}:
        # mediators who have come to Tehran in person (Qatar, Oman, Saudi Arabia, Pakistan, Russia, China…): orange
        flags = set(flags) | {"mediator_visit"}
        topics = set(topics) | {"diplomacy"}
        sev = max(sev, MEDIATOR_VISIT_SEV)
    if _cleric(lang, fa_t or en_t) and not set(flags) & HARD_EVENTS:
        flags = set(flags) | {"cleric"}
        sev = min(sev, CLERIC_CAP)
    if _digest(lang, fa_t or en_t):
        # several items in one headline: a yellow story, whatever one of them tells
        flags = (set(flags) - HARD_EVENTS) | {"digest"}
        sev = min(sev, DIGEST_CAP)
    if _tribute(lang, fa_t or en_t):
        # a memoir or a profile of the dead: a yellow story, whatever attack it recalls
        flags = (set(flags) - HARD_EVENTS) | {"tribute"}
        sev = min(sev, TRIBUTE_CAP)
    if "oil_spike" in flags and _other_market(lang, fa_t or en_t):
        # copper, gold, stocks or a currency moving, the oil price one reason among others: a yellow story
        flags = set(flags) - {"oil_spike"} | {"market"}
        sev = min(sev, MARKET_CAP)
    if _piracy(lang, fa_t or en_t):
        # piracy off Somalia or in the Gulf of Aden: a yellow story
        flags = (set(flags) - HARD_EVENTS) | {"piracy"}
        sev = min(sev, PIRACY_CAP)
    anchored = _anchor(lang, fa_t or en_t, fa_s or en_s)
    if not anchored and _far(lang, fa_t or en_t, fa_s or en_s):
        # China and India in the Himalayas, China and America over Cuba: nothing of the Middle East or of Iran's war
        flags = set(flags) | {"far_off"}
        sev = min(sev, FAR_CAP)
    if "powers" in flags and sev < 56 and not (anchored and _tension(lang, fa_t or en_t, fa_s or en_s)):
        # Putin or the Kremlin with Iran but nothing about the war, America, Israel, the region or oil (trade figures,
        # a gas exporters' summit, students, a courtesy call): a yellow story
        flags = set(flags) | {"powers_soft"}
        sev = min(sev, POWERS_SOFT_CAP)
    g = deesc.grade(lang, fa_t or en_t, fa_s or en_s, rel=item.get("rel", 0.6), channel=_is_channel(item))
    if g:
        # de-escalation: graded by how far it has got and who confirms it (deesc.py)
        topics = set(topics) | {"diplomacy"}
        flags = set(flags) | g["flags"]
        if g["stage"] >= 5 and g["core"]:
            flags -= {"sanctions"}                   # sanctions lifted are not new sanctions
        if g["stage"] >= 2 or "talks_fail" in g["flags"]:
            escal = flags & {"kinetic", "threat", "ultimatum", "deploy", "maritime_incident", "evac", "kinetic_threat",
                             "retaliation", "nuclear_red", "internet", "talks_fail"}
            sev = max(sev, g["sev"]) if escal else g["sev"]
    item["sev"] = round(sev, 1)
    item["topics"] = sorted(topics)
    item["flags"] = sorted(flags)
    item["ppl"] = match_keys(PEOPLE_RX, en_t + " " + en_s[:300], fa_t + " " + fa_s[:300])
    item["geo"] = match_keys(PLACES_RX, en_t + " " + en_s[:300], fa_t + " " + fa_s[:300])
    item["ctry"] = match_keys(COUNTRIES_RX, en_t + " " + en_s[:300], fa_t + " " + fa_s[:300])
    return item


def tier(sev: float) -> str:
    if sev >= config.TIER_RED:
        return "red"
    if sev >= config.TIER_ORANGE:
        return "orange"
    return "yellow"


def cluster_severity(member_sevs, n_sources, max_rel):
    base = max(member_sevs) if member_sevs else 20
    bonus = min(8.0, 3.0 * math.log2(max(1, n_sources))) if n_sources > 1 else 0.0
    sev = (base + bonus) * (0.85 + 0.15 * max_rel)
    return round(max(5.0, min(99.0, sev)), 1)


if __name__ == "__main__":
    tests = [
        "Israeli airstrikes hit targets near Isfahan, explosions reported",
        "Iran seizes oil tanker in the Strait of Hormuz",
        "Trump gives Iran 48-hour ultimatum to accept deal",
        "US sends second aircraft carrier to the Middle East",
        "Iran denies reports it fired missiles at US base",
        "Araghchi meets Omani foreign minister in Muscat",
        "Opinion | What a war with Iran would mean for oil",
        "Analysis: Why the Hormuz standoff could last months",
        "Iran warns of 'crushing response' if attacked",
        "Treasury sanctions network shipping Iranian oil to China",
        "Iran could strike Israel if talks fail, officials say",
        "Airlines suspend flights over Iraq and Iran airspace",
        "One year after the 12-day war, Tehran rebuilds",
        "US embassy orders departure of non-emergency staff from Baghdad",
    ]
    for t in tests:
        s, tp, fl = score_en(t, "")
        print(f"{s:5.1f} {tier(s):6s} {sorted(fl)} | {t}")
    for t in ["حمله موشکی به پایگاه آمریکا در عراق", "عراقچی: آماده مذاکره هستیم", "تکذیب شایعه حمله به نفتکش"]:
        print(score_fa(t, "")[0], score_fa(t, "")[2], t)
