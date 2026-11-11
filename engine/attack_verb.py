"""An attack told as a sentence: who struck, and what or where ("US strikes Iran's Qeshm Island", "Iran strikes
Kurdish region of Iraq", «حمله اسرائیل به جنوب لبنان», «آمریکا جزیره قشم را هدف قرار داد»).

The patterns in classify.py / classify_fa.py read an attack from its noun ("airstrikes", "strikes on …",
«حمله هوایی», «حمله … به ایران»), but not from the plain verb with an actor and a target. This module reads that
structure, strictly, in three parts that must all be there:

  1. an actor of the war (a state, its forces, or an armed group of the region: ACTOR_EN / ACTOR_FA), right before
     the verb (an adverb or a force word may stand between: "Israeli jets", "US forces reportedly");
  2. the verb of a done attack (strikes/struck/hits/bombed/pounded/shelled/raided/attacked;
     «را هدف قرار داد/بمباران کرد/کوبید/زد»; «حمله … به»; «هدف حمله … قرار گرفت»);
  3. what was hit: a place (a country, a city, a region, an island: PLACE_EN / PLACE_FA and lexicon.PLACES), a
     target (a base, a site, a ship, positions, a convoy…: TARGET_EN / TARGET_FA) or an armed group, within a few
     words of the verb and before the clause ends.

Never an attack (the guards):
  - the noun "Iran strikes" (strikes on Iran) followed by what is said of it: "Iran strikes unlikely", "Iran
    strikes kept quiet", "Trump weighs Iran strikes as region scrambles" (NOUN_NEXT; a clause word ends the search
    for a target), or with a word before the actor that makes it a noun or a plan: "fresh/renewed/possible Iran
    strikes", "weighs/orders/avoid Iran strikes" (NOUN_BEFORE);
  - a modal or a plan: "could/would/may strike", "to strike", "threatens to strike" (the verb must follow the
    actor directly; base forms "strike/hit/bomb" only after a plural subject such as "Israeli jets");
  - sanctions, tariffs, cyber attacks and hacks, lawsuits, words (SOFT_EN: "US hits Iran with sanctions",
    "US targets Iranian oil network", "Iran attacks US at UN over …");
  - Persian: a possibility, a threat, a plan, a fear, a warning, an anniversary, a film or a condition before the
    attack («احتمال حمله آمریکا به …», «تهدید به …», «در صورت حمله …»: NOT_BEFORE_FA), «… بعید است/نخواهد»
    after it, the future («قرار خواهد داد»), and «زد/کوبید» of words («حرف»، «رقم»، «دست»، «حرفها»…).

Russia is not an actor here: Russia–Ukraine content stays out of the bulletin. The rest of the rules (denial, past,
speculation, quote, side fronts, Telegram channels) apply to what this reads as to any other attack.
"""
import re

from .lexicon import PLACES
from .util import fa_norm

I = re.I

# ------------------------------------------------------------------ English
_FORCE = (r"(?:forces?|military|army|armed forces|troops|soldiers|jets|fighter jets|warplanes|aircraft|air ?force"
          r"|drones?|uavs?|navy|naval forces|warships?|gunboats?|missiles?|rockets?|artillery|tanks|helicopters"
          r"|bombers|b-2s?|b-52s?|f-35s?|f-15s?|f-16s?|special forces|commandos|marines|fighters|militants)")
_STATE = (r"(?:israel|israeli|the idf|idf|zionist regime|us|u\.s\.|u\.s|the us|the u\.s\.|united states|the united states"
          r"|america|american|pentagon|centcom|iran|iranian|irgc|the irgc|revolutionary guards?|islamic revolutionary"
          r" guard corps|tehran|hezbollah|hamas|islamic jihad|houthis?|yemen['’]s houthis|the houthis|ansar ?allah"
          r"|yemeni armed forces|yemen['’]s armed forces|iraqi militias?|kataib hezbollah|islamic resistance in iraq"
          r"|militias|uk|britain|british|royal air force|raf|france|french|saudi|saudi arabia|saudi-led coalition"
          r"|the coalition|coalition|uae|emirati|turkey|turkiye|turkish|pakistan|pakistani|jordan|jordanian|syria|syrian"
          r"|iraq|iraqi|lebanese army|egypt|egyptian|qatar|qatari|kuwait|kuwaiti|bahrain|bahraini|oman|omani)")
# an actor that is plural by itself, so a base verb follows it ("Houthis strike", "Israeli jets strike")
_PLURAL = (r"(?:houthis|the houthis|yemen['’]s houthis|militias|iraqi militias|the us and israel|us and israel"
           r"|israel and the us|israel and us|us,? israel|israel,? us|us and uk|us,? uk|us and britain)")
ACTOR_EN = (r"(?:" + _PLURAL + r"|" + _STATE + r"(?:['’]s)?(?:\s+" + _FORCE + r")?)")
_ADV = r"(?:\s+(?:reportedly|again|also|then|now|allegedly|repeatedly|overnight|newly|apparently|swiftly|heavily))?"
_VERB_DONE = (r"(?:strikes|struck|hits|hit|bombs|bombed|pounds|pounded|shells|shelled|raids|raided|attacks|attacked"
              r"|blasts|blasted|batters|battered|bombards|bombarded|rocks|rocked)")
_VERB_BASE = r"(?:strike|hit|bomb|pound|shell|raid|attack|blast|batter|bombard|target)"

_PLACE_LIST = [
    "iran", "israel", "iraq", "syria", "lebanon", "yemen", "gaza", "gaza strip", "west bank", "jordan",
    "saudi arabia", "qatar", "uae", "united arab emirates", "emirates", "bahrain", "kuwait", "oman", "egypt", "sinai",
    "turkey", "turkiye", "pakistan", "afghanistan", "kurdistan", "iraqi kurdistan", "kurdistan region",
    "kurdish region", "iran's kurdish region", "red sea", "gulf of aden", "persian gulf", "gulf of oman",
    "tehran", "isfahan", "esfahan", "natanz", "fordow", "fordo", "bushehr", "bandar abbas", "kharg", "kharg island",
    "qeshm", "qeshm island", "kish", "kish island", "abu musa", "tabriz", "shiraz", "mashhad", "karaj", "qom",
    "ahvaz", "ahwaz", "kermanshah", "chabahar", "jask", "hormuz", "strait of hormuz", "arak", "parchin", "khorramabad",
    "dezful", "hamadan", "urmia", "sanandaj", "zahedan", "kerman", "yazd", "semnan", "bandar lengeh", "assaluyeh",
    "asaluyeh", "south pars", "haifa", "tel aviv", "jerusalem", "eilat", "dimona", "beersheba", "negev", "golan",
    "golan heights", "galilee", "nevatim", "ramon", "ashdod", "ashkelon", "netanya", "herzliya", "rishon lezion",
    "beirut", "dahiyeh", "dahieh", "tyre", "sidon", "nabatieh", "bekaa", "baalbek", "damascus", "aleppo", "homs",
    "latakia", "tartus", "deir ez-zor", "deir ezzor", "baghdad", "erbil", "basra", "sulaymaniyah", "kirkuk", "mosul",
    "ain al-asad", "al-asad", "sanaa", "hodeidah", "hudaydah", "saada", "aden", "marib", "taiz", "ras isa", "riyadh",
    "jeddah", "abqaiq", "ras tanura", "yanbu", "dubai", "abu dhabi", "fujairah", "ras laffan", "doha", "al udeid",
    "manama", "kuwait city", "muscat", "duqm", "diego garcia", "rafah", "khan younis", "jenin", "nablus", "tulkarm",
]
for _v in PLACES.values():
    for _w in _v[4]:
        if not _w.startswith("re:"):
            _PLACE_LIST.append(_w.rstrip("$"))
PLACE_EN = (r"(?:(?:southern|northern|eastern|western|central|south|north|east|west|southeast|southwest|northeast"
            r"|northwest|south-east|south-west|north-east|north-west|occupied)\s+)?(?:"
            + "|".join(sorted({re.escape(p) for p in _PLACE_LIST}, key=len, reverse=True)) + r")\b")
TARGET_EN = (r"(?:(?:air ?|naval |military |army |missile |drone |nuclear |oil |gas |power |radar |command |launch )?"
             r"(?:bases?|sites?|facilit(?:y|ies)|targets?|positions?|depots?|ports?|airports?|airfields?|air ?strips?"
             r"|refiner(?:y|ies)|oil ?fields?|gas ?fields?|terminals?|plants?|power stations?|ships?|tankers?|vessels?"
             r"|boats?|warships?|frigates?|destroyers?|convoys?|launchers?|launch pads?|headquarters|hq|command (?:centers?"
             r"|centres?|posts?)|camps?|compounds?|buildings?|homes?|houses?|apartments?|cars?|vehicles?|trucks?"
             r"|suspects?|militants?|fighters?|gunmen|commanders?|leaders?|operatives?|cells?|infrastructure"
             r"|installations?|villages?|towns?|cities|city|markets?|neighbou?rhoods?|outposts?|bunkers?|tunnels?"
             r"|warehouses?|stockpiles?|arsenals?|radars?|air ?defen[cs]es?|embass(?:y|ies)|consulates?|hospitals?"
             r"|schools?|bridges?|islands?|region|areas?|province|border|troops|forces|soldiers|drones?|weapons"
             r"|factor(?:y|ies)|shipyards?|dockyards?|pipelines?|stations?|batter(?:y|ies)|silos?|hangars?"
             r"|checkpoints?|crossings?|refugee camps?|tents?|shelters?|mosques?|universit(?:y|ies)|labs?|laborator(?:y|ies)"
             r"|reactors?|centrifuges?|enrichment)"
             r"|hezbollah|hamas|houthis?|irgc|militias?|islamic jihad|isis|islamic state|al-qaeda|al-shabaab|pjak|pkk"
             r"|jaish al-adl|kurdish (?:groups?|militants|rebels|opposition|parties|fighters)|insurgents?|rebels?)\b")
# what is said of "Iran strikes" as a noun, right after it
NOUN_NEXT = re.compile(
    r"^\s*(?:unlikely|likely|remain\w*|kept|keep\w*|still|could|would|may|might|will|won['’]?t|can|cannot|are|is|was"
    r"|were|be|been|being|loom\w*|possible|coming|imminent|for|if|as|amid|after|before|resume\w*|threat\w*|fears?"
    r"|talks?|plans?|debate\w*|options?|deal|ceasefire|truce|agreement|accord|on|in|against|at|near|by|over|off|back"
    r"|from|to|of|and|or|but|this|that|these|those|appear\w*|seem\w*|set|expected|ahead|again|too|so|unnecessary"
    r"|needed|necessary|justified|illegal|legal|halted|paused|stopped|ended|delayed|postponed|canceled|cancelled"
    r"|called|ruled|unlikely|signal\w*|now|soon|later|yet|says?|said|report\w*|news|claims?|costs?|risk\w*"
    r"|helped|help|hurt|failed|worked|succeeded|backfired|boosted|drove|drive|sent|send|pushed|push|raised|lifted"
    r"|sparked|spark|trigger\w*|lead|led|leads|show|shows|showed|prove\w*|reveal\w*|expose\w*|marks?|marked|marking)\b", I)
# a word before the actor that makes "Iran strikes" a noun, a plan or a choice
NOUN_BEFORE = re.compile(
    r"\b(?:fresh|new|renewed|further|more|possible|potential|future|planned|any|no|of|on|for|about|over|against"
    r"|weighs?|weighing|weighed|considers?|considering|considered|orders?|ordered|ordering|approves?|approved"
    r"|authori[sz]es?|authori[sz]ed|avoid\w*|avert\w*|prevent\w*|halt\w*|pause\w*|resume\w*|unlikely|backs?|backing"
    r"|opposes?|opposed|rules? out|ruled out|delays?|delayed|postpones?|postponed|cancels?|cancell?ed|calls? off"
    r"|called off|holds? off(?: on)?|held off(?: on)?|plays? down|played down|downplays?|downplayed|confirms?"
    r"|confirmed|denies|denied|signals?|signaled|signalled|mulls?|mulled|threatens?|threatened|warns?|warned"
    r"|urges?|urged|eyes|eyed|readies|readying|prepares?|prepared|plans?|planning|seeks?|sought|wants?|wanted"
    r"|demands?|demanded|need|needs|vs\.?|versus|against|limited|massive|large-scale|retaliatory|preemptive"
    r"|pre-emptive|joint|two|three|several|multiple|repeated|daily|nightly|weekly|ongoing|continued|continuing)"
    r"\s+$", I)
SOFT_EN = re.compile(r"\b(?:sanction\w*|tariffs?|cyber\w*|hack\w*|lawsuits?|sues?|sued|fines?|fined|criticism|critics"
                     r"|rhetoric|remarks|speech|op-ed|tweet\w*|accus\w+|slam\w*|verbally|propaganda|campaign ads?"
                     r"|blacklist\w*|designat\w+|terror list|visa|travel ban|indictment|indict\w*|shadow fleet"
                     r"|smuggling ring|at the un|at un|in (?:a )?(?:speech|letter|interview|statement|op-ed)|narrative"
                     # money taken by force ("Houthis target Sanaa bakeries to fund war effort"): not an attack
                     r"|to fund|fund(?:s|ing)? (?:the |its |their )?war|financ\w*|tax\w*|levy|levies|extort\w*|ransom)\b", I)
_CLAUSE_END = re.compile(r"[,;:—–|]|\s(?:as|after|amid|while|but|if|despite|following|before|when|since|until|with"
                         r"|over|says?|said|claims?|reports?|according)\s", I)

_VERB_RX = re.compile(r"(?<![\w-])(" + ACTOR_EN + r")" + _ADV + r"\s+(" + _VERB_DONE + r"|" + _VERB_BASE + r")\b", I)
_TARGET_RX = re.compile(r"\b(?:" + PLACE_EN + r"|" + TARGET_EN + r")", I)
_PLURAL_RX = re.compile(r"(?:" + _PLURAL + r"|\b" + _FORCE + r")$", I)
# "US targets Iranian oil network", "US hits Iran's banks": sanctions, not an attack
_SOFT_OBJ = re.compile(r"^\s*(?:(?:a|an|the|its|their)\s+)?(?:\w+\s+){0,2}?(?:network|entities|firms?|companies"
                       r"|individuals|officials|exports?|imports?|banks?|exchanges?|traders?|smugglers?|shipping network"
                       r"|procurement|financ\w*|oil sales|sales|revenue\w*)\b", I)


# an adjective alone is no subject: "Israeli strikes", "American attacks" are nouns (with a force word it is:
# "Israeli jets strike")
_ADJ_ONLY = re.compile(r"(?:israeli|american|iranian|british|french|emirati|turkish|pakistani|jordanian|syrian|iraqi"
                       r"|egyptian|qatari|kuwaiti|bahraini|omani|yemeni|lebanese|saudi-led coalition['’]s)", I)
# the attack told in a side clause of a headline about something else ("… as Houthis target Riyadh")
_SIDE_CLAUSE = re.compile(r"\b(?:as|while|amid|whilst)\s+(?:\S+\s+){0,4}$", I)


def actor_strikes_en(title):
    """True when an English headline tells an actor of the war striking a place or a target (see the module doc)."""
    t = title or ""
    if not re.search(r"(?i)\b(strik|struck|hit|bomb|pound|shell|raid|attack|blast|batter|rock|target)", t):
        return False
    for m in _VERB_RX.finditer(t):
        actor, verb = m.group(1), m.group(2).lower()
        if _ADJ_ONLY.fullmatch(actor.strip()):
            continue                     # "Israeli attacks burned …", "Iranian strikes": a noun, not a verb
        if _SIDE_CLAUSE.search(t[:m.start()]):
            continue                     # "US expands pressure on Iran as Houthis target Riyadh": not the headline's event
        base = re.fullmatch(_VERB_BASE, verb, I) and verb not in ("hit",)
        if verb in ("rocks", "rocked") and not re.search(r"(?i)\b(?:explosions?|blasts?)\b", t):
            continue                     # "rocks" only of blasts; "Israel rocked by protests" is not an attack
        if base and not _PLURAL_RX.search(actor.strip()):
            continue                     # "Iran strike still on the table", "US strike Iran" as a noun phrase
        before = t[:m.start()]
        if NOUN_BEFORE.search(before) or re.search(r"(?i)\b(?:could|would|may|might|will|to|not|never|must|should"
                                                   r"|can|cannot|won['’]?t|didn['’]?t|doesn['’]?t)\s+$", before):
            continue
        rest = t[m.end():]
        if NOUN_NEXT.match(rest) or (verb.startswith(("hit", "target")) and _SOFT_OBJ.match(rest)):
            continue
        end = _CLAUSE_END.search(rest)
        obj = rest[:end.start()] if end else rest
        obj = " ".join(obj.split()[:7])
        if not _TARGET_RX.search(obj):
            continue
        clause = t[max(0, m.start() - 60):m.end() + len(obj) + 40]
        if SOFT_EN.search(clause):
            continue                     # sanctions, a hack, words, a plan or a market: not an attack
        return True
    return False


# ------------------------------------------------------------------ Persian
def _fa(*words):
    return "(?:" + "|".join(fa_norm(w).replace(" ", r"\s*") for w in words) + ")"


ACTOR_FA = _fa("آمریکا", "امریکا", "ایالات متحده", "ارتش آمریکا", "نیروهای آمریکایی", "نیروهای امریکایی",
               "جنگنده های آمریکایی", "جنگنده های آمریکا", "سنتکام", "پنتاگون", "اسرائیل", "اسراییل",
               "رژیم صهیونیستی", "رژیم اسرائیل", "ارتش اسرائیل", "ارتش اسراییل", "ارتش رژیم صهیونیستی",
               "جنگنده های اسرائیلی", "جنگنده های رژیم صهیونیستی", "صهیونیست ها", "ایران", "سپاه",
               "سپاه پاسداران", "نیروی هوافضای سپاه", "نیروی دریایی سپاه", "ارتش ایران", "ارتش جمهوری اسلامی",
               "جمهوری اسلامی", "حزب الله", "حماس", "جهاد اسلامی", "حوثی ها", "حوثیها", "انصارالله", "انصار الله",
               "ارتش یمن", "نیروهای مسلح یمن", "مقاومت اسلامی عراق", "حشد الشعبی", "کتائب حزب الله", "عربستان",
               "ائتلاف سعودی", "ائتلاف عربی", "انگلیس", "بریتانیا", "فرانسه", "ترکیه", "ارتش ترکیه", "پاکستان",
               "ارتش پاکستان", "اردن", "امارات", "قطر", "عراق", "سوریه", "ارتش سوریه")
_PLACE_FA_LIST = [
    "ایران", "اسرائیل", "اسراییل", "عراق", "سوریه", "لبنان", "یمن", "غزه", "نوار غزه", "کرانه باختری", "اردن",
    "عربستان", "قطر", "امارات", "بحرین", "کویت", "عمان", "مصر", "صحرای سینا", "ترکیه", "پاکستان", "افغانستان",
    "اقلیم کردستان", "کردستان عراق", "شمال عراق", "دریای سرخ", "خلیج عدن", "خلیج فارس", "دریای عمان",
    "فلسطین اشغالی", "سرزمین های اشغالی", "اراضی اشغالی", "تهران", "اصفهان", "نطنز", "فردو", "بوشهر", "بندرعباس",
    "بندر عباس", "خارک", "قشم", "جزیره قشم", "کیش", "جزیره کیش", "ابوموسی", "تبریز", "شیراز", "مشهد", "کرج", "قم",
    "اهواز", "کرمانشاه", "چابهار", "جاسک", "هرمز", "تنگه هرمز", "اراک", "پارچین", "خرم آباد", "دزفول", "همدان",
    "ارومیه", "سنندج", "زاهدان", "کرمان", "یزد", "سمنان", "بندر لنگه", "عسلویه", "پارس جنوبی", "حیفا", "تل آویو",
    "قدس", "بیت المقدس", "ایلات", "دیمونا", "بئرشبع", "نقب", "جولان", "الجلیل", "جلیل", "نواتیم", "رامون",
    "اشدود", "عسقلان", "بیروت", "ضاحیه", "صور", "صیدا", "نبطیه", "بقاع", "بعلبک", "دمشق", "حلب", "حمص", "لاذقیه",
    "طرطوس", "دیرالزور", "دیر الزور", "بغداد", "اربیل", "بصره", "سلیمانیه", "کرکوک", "موصل", "عین الاسد", "صنعا",
    "الحدیده", "حدیده", "صعده", "عدن", "مارب", "تعز", "ریاض", "جده", "ابقیق", "راس تنوره", "ینبع", "دبی", "ابوظبی",
    "فجیره", "دوحه", "العدید", "منامه", "مسقط", "دیه گو گارسیا", "رفح", "خان یونس", "جنین", "نابلس", "طولکرم",
]
for _v in PLACES.values():
    for _w in _v[5]:
        _PLACE_FA_LIST.append(_w.rstrip("$"))
_DIR_FA = _fa("جنوب", "شمال", "شرق", "غرب", "مرکز", "حومه", "اطراف", "نزدیکی", "حوالی", "جزیره", "استان", "شهر",
              "بندر", "منطقه", "مناطقی از", "مناطق", "اقلیم", "کرانه", "جنوب شرق", "جنوب غرب", "شمال شرق", "شمال غرب")
PLACE_FA = (r"(?:" + _DIR_FA + r"\s*)?" + "(?:" + "|".join(sorted({fa_norm(p).replace(" ", r"\s*")
                                                                     for p in _PLACE_FA_LIST}, key=len, reverse=True))
            + r")(?![؀-ۿ])")
TARGET_FA = _fa("پایگاه", "پایگاه های", "مقر", "مقرهای", "اردوگاه", "انبار", "انبارهای", "پادگان", "فرودگاه",
                "بندر", "اسکله", "پالایشگاه", "تاسیسات", "سفارت", "کنسولگری", "کاروان", "روستا", "روستاهای",
                "نیروگاه", "ساختمان", "خودرو", "مواضع", "موضع", "مراکز", "مرکز فرماندهی", "سکوی پرتاب",
                "سکوهای پرتاب", "سامانه", "رادار", "پدافند", "کشتی", "نفتکش", "شناور", "ناو", "ناوچه", "تونل",
                "تونل های", "پل", "کارخانه", "خط لوله", "نیروهای", "فرماندهان", "فرمانده", "گروهک", "گروهک های",
                "تروریست ها", "تجمع", "محل استقرار", "زیرساخت", "زیرساخت های", "مخفیگاه", "سایت", "سایت های",
                "رآکتور", "راکتور", "جنگنده", "پهپاد", "بالگرد", "مقر فرماندهی", "منازل", "خانه", "خانه های",
                "بیمارستان", "مدرسه", "دانشگاه", "مسجد", "بازار", "چادر", "چادرهای", "اردوگاه آوارگان")
_TGT_FA_RX = re.compile(r"(?:" + PLACE_FA + r"|" + TARGET_FA + r")")
_ATTACK_N = _fa("حمله", "حملات", "حمله هوایی", "حملات هوایی", "حمله موشکی", "حملات موشکی", "حمله پهپادی",
                "حملات پهپادی", "بمباران", "حمله توپخانه ای", "حمله جدید", "حملات جدید", "حمله گسترده",
                "حملات گسترده", "حمله شدید", "حملات شدید", "حمله مرگبار")
# a possibility, a threat, a plan, a fear, a warning, a condition, an anniversary or a film: not an attack told
NOT_BEFORE_FA = re.compile(r"(?:^|\s)(?:" + _fa(
    "احتمال", "امکان", "تهدید", "تهدید به", "خطر", "بیم", "ترس", "نگرانی", "هشدار", "هشدار درباره", "طرح", "نقشه",
    "قصد", "آماده", "آمادگی", "آماده سازی", "بعید", "عدم", "بدون", "توقف", "پایان", "لغو", "تعویق", "مخالفت",
    "درباره", "سناریو", "سناریوی", "گزینه", "جلوگیری از", "مانع", "سالگرد", "خاطره", "روایت", "فیلم", "مستند",
    "اگر", "در صورت", "چنانچه", "شایعه", "تکذیب", "رد", "ادعای", "برای", "پیامدهای", "پیامد", "هزینه", "ابعاد",
    "تحلیل", "چرا", "آیا", "نه به", "خطر", "وقوع", "تکرار", "بازگشت", "از سرگیری", "دور جدید", "مجوز", "دستور",
    "تصمیم", "تصمیم به", "موافقت با", "حمایت از", "محکومیت", "محکوم کردن", "واکنش به", "پس از") + r")\s*$")
NOT_AFTER_FA = re.compile(r"^\s*(?:\S+\s+){0,5}?" + _fa("بعید", "نخواهد", "نخواهند", "ممکن", "احتمال", "منتفی",
                                                     "می تواند", "می توانند", "خواهد بود", "خواهد شد", "نیست",
                                                     "بود؟", "است؟", "جنایت", "غیرقانونی", "نقض", "اشتباه",
                                                     "خطرناک", "فاجعه", "تکذیب", "صحت ندارد", "کذب"))
# «حمله صهیونیست‌ها به نابلس تروریسم سازمان‌یافته است»: a judgement of the attack, not a report of it
JUDGED_FA = re.compile(_fa("تروریسم", "تروریستی", "جنایت", "جنایتکارانه", "جنایت جنگی", "نقض", "غیرقانونی",
                           "غیر قانونی", "اشتباه", "تجاوز آشکار", "نسل کشی", "محکوم")
                       + r"[^،؛:.!؟?]{0,40}?(?:است|هستند|بود|می\s*باشد|محسوب\s*می\s*شود|شمرده\s*می\s*شود)"
                       + r"(?![\u0600-\u06FF])")
_FA_END = re.compile(r"[،؛:|\-–—.!؟?]|(?:^|\s)" + _fa("و", "اما", "ولی", "پس از", "در پی", "همزمان", "در حالی")
                     + r"(?:\s|$)")
# «… را هدف قرار داد/بمباران کرد/کوبید/زد»: done, never the future
_DONE_FA = _fa("را هدف قرار داد", "را هدف قرار دادند", "را بمباران کرد", "را بمباران کردند", "را موشک باران کرد",
               "را موشک باران کردند", "را گلوله باران کرد", "را گلوله باران کردند", "را توپ باران کرد",
               "را توپ باران کردند", "را کوبید", "را کوبیدند", "را زد", "را زدند", "را منهدم کرد", "را منهدم کردند",
               "را مورد حمله قرار داد", "را مورد حمله قرار دادند", "را آماج حملات قرار داد",
               "را آماج حملات قرار دادند", "را آماج حمله قرار داد", "را مورد اصابت قرار داد",
               "را مورد اصابت قرار دادند", "را درهم کوبید", "را در هم کوبید", "را درهم کوبیدند")
_WORDS_FA = re.compile(r"(?<![\u0600-\u06FF])" + _fa("حرف", "حرفها", "حرف های", "سخنان", "ادعا", "ادعای", "ادعاهای", "رقم", "دست", "گره",
                           "کنار", "قید", "ایده", "طرح", "برجام", "توافق", "نامه", "پیشنهاد", "شایعه", "شایعات",
                           "روایت", "استدلال", "سیاست", "منتقدان", "رسانه", "رسانه ها", "تحریم")
                       + r"(?![\u0600-\u06FF])")
_PREP_FA = r"(?:در|از|برای|علیه|به|با|که|بر|تا|نزد|درباره)"
# «حمله [هوایی/شبانه/دیروز] ACTOR [و ACTOR] به …»: no preposition before the actor («حمله تروریستی در آمریکا … به
# نیابت از ایران» is not America attacking) nor between the actor and «به»
_FORM_A = re.compile(_ATTACK_N + r"\s*(?:ای\s*)?(?:(?!" + _PREP_FA + r"\s)\S+\s+){0,2}?" + ACTOR_FA
                     + r"(?:\s+(?!" + _PREP_FA + r"\s)\S+){0,2}?\s*(?:به|علیه|بر)\s*"
                     r"((?:\S+\s+){0,3}?(?:" + PLACE_FA + r"|" + TARGET_FA + r"))")
_FORM_B = re.compile(r"(?:^|\s|:)" + ACTOR_FA + r"\s+((?:\S+\s+){1,7}?)" + _DONE_FA + r"(?![؀-ۿ])")
_FORM_C = re.compile(_fa("هدف", "آماج", "مورد") + r"\s*(?:حمله|حملات|بمباران|اصابت)\s*(?:\S+\s+){0,4}?"
                     r"(?:قرار\s*گرفت|قرار\s*گرفتند)(?![؀-ۿ])")


def actor_strikes_fa(t):
    """True when a Persian headline (normalised with fa_norm) tells an actor of the war striking a place or a target,
    or a place «هدف حمله … قرار گرفت» (see the module doc)."""
    if not t or not re.search(r"حمل|بمباران|هدف|کوبید|زد|منهدم|آماج|اصابت|باران", t):
        return False
    for m in _FORM_A.finditer(t):
        if NOT_BEFORE_FA.search(t[:m.start()]) or NOT_AFTER_FA.match(t[m.end():]):
            continue
        if JUDGED_FA.search(re.split(r"[،؛.!؟?]", t[m.end():])[0]):
            continue
        return True
    for m in _FORM_B.finditer(t):
        obj = m.group(1)
        end = _FA_END.search(obj)
        if end or not _TGT_FA_RX.search(obj) or _WORDS_FA.search(obj):
            continue
        if NOT_BEFORE_FA.search(t[:m.start()]):
            continue
        return True
    for m in _FORM_C.finditer(t):
        before = t[:m.start()]
        if NOT_BEFORE_FA.search(before) or re.search(_fa("اگر", "در صورت", "چنانچه", "ممکن است", "احتمال دارد"),
                                                       before[-40:]):
            continue
        return True
    return False
