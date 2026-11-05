"""Rules for the side fronts: the Saudi-Houthi war and Israel against Hezbollah in Lebanon.

Both produce dozens of reports a day, and the bulletin is about the main front (Iran against America and Israel).
On these fronts a report is red only when it is a big turn ("major"); everything else stays orange at most
("secondary", SECONDARY_CAP), and the index counts it lightly (index.py).

Saudi-Houthi, major: a Houthi attack that hits Saudi oil or energy sites (Aramco, refineries, oil terminals,
pipelines, power and desalination plants), an attack on America's interests in Saudi Arabia (its bases, troops,
embassy or consulates), wide damage to a Saudi airport (on fire, destroyed, closed), attacks on shipping in the Red
Sea and Bab el-Mandeb, and staff told to leave. Not major: missiles and drones intercepted, airports and cities
"targeted" with no damage told, the Houthi spokesman's claims alone, Saudi or coalition strikes on Yemen, fighting
inside Yemen, counts of attacks, casualty figures, statements, talks, markets. A report that names Israel or Iran,
or America striking, is left to the general rules.

Lebanon, major: Hezbollah firing at Israel (rockets, missiles, drones, sirens in the north), Israeli strikes on
Beirut and its southern suburbs, a senior Hezbollah leader or commander killed, a ground invasion or a new
offensive, the ceasefire collapsing, the heaviest strikes in a long time or strikes across the country. Not major:
the daily air strikes, drone strikes and shelling in the south and the Bekaa, a local commander killed, statements,
casualty figures (those are yellow, classify._local_toll). A report that names Iran is left to the general rules."""
import re

from .util import fa_norm

_I = re.I
SECONDARY_CAP = 64.0          # an orange story, below the main front's orange ones

# ------------------------------------------------------------------ English
_EN_FRONT = re.compile(r"\b(houthis?|ansar ?allah|yemen\w*|sanaa|sana'a|saada|sa'ada|hodeidah|hudaydah|aden|lahij|lahj"
                       r"|taiz|ta'iz|marib|ma'rib|shabwa|hadramout|hadramawt|mukalla|abyan"
                       r"|bab[- ]el[- ]mandeb|bab al[- ]mandab|saree|sarea)\b", _I)
# Saudi Arabia's side telling of what it intercepted, with no Houthi named
_EN_FRONT2 = re.compile(r"\b(saudi[- ]led coalition|arab coalition|coalition (says|spokes\w*|forces))\b"
                        r"|\bcoalition\b[^.;]{0,60}\bsaudi|\bsaudi\b[^.;]{0,30}\bcoalition\b"
                        r"|\b(intercept\w*|shoots? down|shot down|downs?|downed|destroy\w*)\b[^.;]{0,60}\b(saudi\w*|riyadh|jeddah"
                        r"|mecca|makkah|medina|madinah|jizan|jazan|najran|abha|khamis mushait|dhahran|dammam|the kingdom)\b", _I)
_EN_OTHER = re.compile(r"\b(israel\w*|tel aviv|eilat|haifa|jerusalem|iran\w*|tehran|islamic republic|united states"
                       r"|american|pentagon|uss|us navy|centcom|trump|hegseth|rubio)\b"
                       r"|(?<![A-Za-z])(US|U\.S\.)(?![A-Za-z])", _I)
# Yemeni forces on Saudi Arabia's side are still Yemeni forces
_EN_PROXY = re.compile(r"\b(saudi[- ]backed|riyadh[- ]backed|saudi[- ]supported|backed by (saudi( arabia)?|riyadh)"
                       r"|loyal to (saudi( arabia)?|riyadh)|affiliated (to|with) (saudi( arabia)?|riyadh))\b", _I)
_EN_SAUDI = re.compile(r"\b(saudi\w*|riyadh|jeddah|jiddah|mecca|makkah|medina|madinah|taif|rabigh|khamis mushait"
                       r"|jizan|jazan|najran|abha|dhahran|ras tanura|abqaiq|yanbu|aramco|kingdom|coalition)\b", _I)
_EN_ATTACK = re.compile(r"\b(attack\w*|strik\w*|struck|hit|hits|target\w*|launch\w*|fir(e|ed|es|ing)|missiles?"
                        r"|clash\w*|trade blows|exchange\w* fire"
                        r"|drones?|rockets?|ballistic|intercept\w*|downs?|downed|shoots? down|shot down|raids?"
                        r"|bomb\w*|shell\w*|airstrikes?|air strikes?|explosions?|blasts?|debris|shrapnel"
                        r"|impact\w*|ablaze)\b", _I)
_EN_SEA = re.compile(r"\b(ships?|vessels?|tankers?|freighters?|bulk carrier|container ship|merchant)\b.{0,80}"
                     r"\b(red sea|bab[- ]el[- ]mandeb|bab al[- ]mandab|gulf of aden)\b"
                     r"|\b(red sea|bab[- ]el[- ]mandeb|bab al[- ]mandab|gulf of aden)\b.{0,80}"
                     r"\b(ships?|vessels?|tankers?|freighters?|bulk carrier|container ship|merchant)\b", _I)
_EN_TOLL = re.compile(r"^\W*([^:]{2,40}:\s*)?(\d[\d,]*|two|three|four|five|six|seven|eight|nine|ten|dozens|scores"
                      r"|hundreds|several)\b[^.;:]{0,30}?\b(killed|dead|die[ds]?|injured|wounded|hurt|martyr\w*"
                      r"|casualt\w*)\b"
                      r"|\b(death toll|toll (rises|climbs|reaches)|casualt(y|ies)|injured by|wounded by|hurt by"
                      r"|bloody toll|killed by (falling )?debris)\b"
                      r"|\b(debris|shrapnel|fragments?|remnants?)\b[^.;]{0,50}\b(injur\w*|wound\w*|hurt\w*|kill\w*)"
                      # running totals ("the target of 3,179 Saudi strikes", "780 strikes in 24 hours")
                      r"|\b\d{3,}[\d,]*\s+(\w+\s+){0,3}(attacks|strikes|raids|airstrikes|air strikes|missiles)\b", _I)
_EN_TALK = re.compile(r"\b(condemn\w*|denounc\w*|accus\w*|blames?|blamed|deplor\w*|slams?|criticiz\w*|urges?"
                      r"|calls? (for|on)|demands?|appeals?|talks|meeting|summit|discuss\w*|negotiat\w*"
                      r"|statement)\b", _I)
# threats and plans, wherever they sit in the headline ("Houthis vow to keep up attacks on Riyadh airport")
_EN_FUTURE = re.compile(r"\b(will|vows?|vowed|warns?|warned|threat\w*|plans?|could|may)\b", _I)
_EN_REVIEW = re.compile(r"\b(oil (prices?|hits|jumps|rises|falls|climbs|little changed|steady|surges?)|prices?"
                        r"|stocks?|econom\w*|imf|investors?|insurance|analysis|explainer|what we know|why|how"
                        r"|airlines?|flights? (cancel\w*|suspend\w*))\b", _I)

# ------------------------------------------------------------------ Persian (matched on normalised text)
_FA_FRONT = re.compile(fa_norm("حوثی|انصارالله|یمن|صنعا|صعده|الحدیده|حدیده|عدن|لحج|تعز|مأرب|مارب|شبوه|حضرموت|مکلا"
                               "|ابین|باب المندب|یحیی سریع"))
_FA_FRONT2 = re.compile(fa_norm("ائتلاف سعودی|ائتلاف عربی|ائتلاف متجاوز|سخنگوی ائتلاف"
                                "|(رهگیری|سرنگون|ساقط)[^.؛]{0,60}(عربستان|سعودی|ریاض|جده|مکه|مدینه|جیزان|جازان|نجران|ابها|دمام)"))
_FA_OTHER = re.compile(fa_norm("اسرائیل|اسراییل|صهیونیست|تل آویو|ایلات|حیفا|ایران|تهران|جمهوری اسلامی|آمریکا|امریکا"
                               "|ایالات متحده|پنتاگون|سنتکام|ترامپ"))
_FA_PROXY = re.compile(fa_norm("(وابسته به|مورد حمایت|تحت حمایت|طرفدار|مزدوران)\\s*(ریاض|عربستان|سعودی|آل سعود)"))
_FA_SAUDI = re.compile(fa_norm("عربستان|سعودی|ریاض|جده|مکه|مدینه|طائف|رابغ|خمیس مشیط|جیزان|جازان|نجران|ابها|ظهران"
                               "|راس تنوره|ابقیق|ینبع|آرامکو|ائتلاف"))
_FA_ATTACK = re.compile(fa_norm("حمله|حملات|هدف قرار|اصابت|شلیک|پرتاب|موشک|پهپاد|رهگیری|رهگیر|سرنگون|منهدم|انهدام"
                                "|بمباران|انفجار|آوار|بقایای موشک|ترکش|آتش سوزی|عملیات"))
_FA_SEA = re.compile(fa_norm("(کشتی|نفتکش|شناور)[^.؛]{0,60}(دریای سرخ|باب المندب|خلیج عدن)"
                             "|(دریای سرخ|باب المندب|خلیج عدن)[^.؛]{0,60}(کشتی|نفتکش|شناور)"))
_FA_TOLL = re.compile(fa_norm(r"^\W*([^:]{2,40}:\s*)?(\d+|ده ها|دهها|صدها|چند|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده)"
                              r"\s*(تن|نفر|شهید|کشته|زخمی|مجروح|غیرنظامی|کودک|زن)"
                              r"|(آوار|ترکش|بقایای)[^.؛]{0,50}(زخمی|مجروح|کشته)"
                              r"|\d{3,}\s*(حمله|حملات|عملیات|موشک|بمباران)"
                              r"|(تعداد|آمار|شمار)\s*(شهدا|شهیدان|کشته|کشته شدگان|تلفات|مجروحان|زخمی|قربانیان)"
                              r"|زخمی شدن|مجروح شدن|کشته شدن|به شهادت رسیدن|جان باختن"))
_FA_TALK = re.compile(fa_norm("محکوم|محکومیت|متهم ک|اتهام|هشدار داد|هشدار می|تهدید کرد|خواستار|مذاکره|مذاکرات|نشست"
                              "|دیدار|گفتگو|گفت و گو|واکنش|انتقاد|بیانیه|اعتراض|نقض"))
_FA_FUTURE = re.compile(fa_norm("ادامه می دهیم|ادامه خواهیم|خواهیم|خواهد|نخواهد|تهدید|هشدار داد|هشدار می"))
_FA_REVIEW = re.compile(fa_norm("آخرین تحولات|مروری بر|گزارش تصویری|تحلیل|چرا |چگونه|قیمت|بازار|بورس|اقتصاد"
                                "|سرمایه گذار|صندوق بین المللی پول|بیمه|ایرلاین|شرکت های هواپیمایی|لغو پرواز"))


# what makes a report on the Saudi-Houthi front major
_EN_MAIN = re.compile(r"\b(israel\w*|tel aviv|eilat|haifa|jerusalem|iran\w*|tehran|islamic republic)\b", _I)
_EN_US = re.compile(r"\b(united states|american|pentagon|uss|us navy|centcom|trump|hegseth|rubio|washington)\b"
                    r"|(?<![A-Za-z])(US|U\.S\.)(?![A-Za-z])", _I)
_EN_US_SITE = re.compile(r"\b((u\.?s\.?|american|america's|washington's) (\w+ ){0,2}(bases?|air ?base|embassy|consulates?"
                         r"|troops|forces|soldiers|service ?members|personnel|diplomats?|compound|military|warships?"
                         r"|destroyers?|carriers?|aircraft|jets?|staff)|prince sultan( air ?base)?|eskan village)\b", _I)
_EN_US_ACT = re.compile(r"\b(u\.?s\.?|american|centcom|pentagon|washington)\b[^.;]{0,30}\b(strik\w*|struck|bomb\w*"
                        r"|raids?|hits?|targets?|targeted|attack\w*)\b", _I)
_EN_ENERGY = re.compile(r"\b(aramco|refiner(y|ies)|oil (facilit\w*|fields?|plants?|terminals?|installations?|depots?"
                        r"|tanks?|infrastructure|sites?|ports?|processing|production)|pipelines?|petrochemical\w*"
                        r"|gas (plants?|fields?|facilit\w*)|power (plants?|stations?)|desalination|energy (facilit\w*"
                        r"|infrastructure|sites?)|abqaiq|ras tanura|khurais|jafurah|samref|satorp|yasref|jizan economic)\b", _I)
_EN_AIRPORT = re.compile(r"\b(airports?|air ?ports?)\b", _I)
_EN_DAMAGE = re.compile(r"\b((heavy|extensive|widespread|major|significant|severe|serious|massive) damage|damag\w*"
                        r"|destroy\w*|ablaze|on fire|fires?|blaze|burn\w*|in flames|closed|closes|shut\w*|suspend\w*"
                        r"|halt\w*|grounded|paralys\w*|paralyz\w*|out of (service|action)|runways?|terminal (hit|struck))\b", _I)
_EN_HIT = re.compile(r"\b(hits?|struck|damag\w*|destroy\w*|ablaze|on fire|fires?|blaze|burn\w*|in flames|explosions?"
                     r"|blasts?|halt\w*|shut\w*|suspend\w*|impact\w*)\b", _I)
# the Houthis' own account of what they hit, not yet told by anyone else
_EN_HCLAIM = re.compile(r"\b(saree|sarea|houthis? (say|says|said|claim\w*)|claims?|claimed|(yemeni|houthi) (armed forces"
                        r"|army|military|spokes\w*)|ansar ?allah (say|says|said|claim\w*))\b", _I)
_EN_INTERCEPT = re.compile(r"\b(intercept\w*|shoots? down|shot down|downs?|downed|destroy\w* (a |an |two |three )?"
                           r"(drones?|missiles?|projectiles?))\b", _I)
_EN_YEMEN_SITE = re.compile(r"\b(in yemen|yemen's|sanaa|sana'a|saada|hodeidah|hudaydah|ras isa|salif|marib|ma'rib|aden"
                            r"|taiz|lahj|shabwa|hadramout|mukalla|al-jawf|jawf|amran|dhamar)\b", _I)

_FA_MAIN = re.compile(fa_norm("اسرائیل|اسراییل|صهیونیست|تل آویو|ایلات|حیفا|ایران|تهران|جمهوری اسلامی"))
_FA_US = re.compile(fa_norm("آمریکا|امریکا|ایالات متحده|پنتاگون|سنتکام|ترامپ|واشنگتن"))
_FA_US_SITE = re.compile(fa_norm("(پایگاه|سفارت|کنسولگری|نیروهای|نظامیان|سربازان|دیپلمات|ناو|ناوشکن|کارکنان)[^.؛]{0,12}"
                                 "(آمریکا|امریکا|ایالات متحده)|شاهزاده سلطان|پرنس سلطان"))
_FA_US_ACT = re.compile(fa_norm("(آمریکا|امریکا|سنتکام|پنتاگون|واشنگتن)[^.؛]{0,30}(حمله|حملات|بمباران|هدف قرار|اصابت)"))
_FA_ENERGY = re.compile(fa_norm("آرامکو|پالایشگاه|تاسیسات نفتی|تأسیسات نفتی|میدان نفتی|میادین نفتی|پایانه نفتی|ترمینال نفتی"
                                "|خط لوله|مخازن نفت|انبار نفت|بندر نفتی|تاسیسات انرژی|تأسیسات انرژی|زیرساخت های انرژی"
                                "|زیرساخت انرژی|زیرساخت نفتی|نیروگاه|آب شیرین کن|پتروشیمی|تاسیسات گازی|تأسیسات گازی|ابقیق"
                                "|راس تنوره|خریص"))
_FA_AIRPORT = re.compile(fa_norm("فرودگاه"))
_FA_DAMAGE = re.compile(fa_norm("خسارت|خسارات|تخریب|ویران|منهدم|نابود|آتش گرفت|آتش سوزی|در آتش|شعله|سوخت|تعطیل|بسته شد"
                                "|متوقف|توقف|لغو|از کار افتاد|باند"))
_FA_HIT = re.compile(fa_norm("اصابت|خسارت|تخریب|منهدم|آتش گرفت|آتش سوزی|در آتش|شعله|انفجار|متوقف|توقف|تعطیل"))
_FA_HCLAIM = re.compile(fa_norm("یحیی سریع|سخنگوی (نیروهای مسلح|ارتش) یمن|نیروهای مسلح یمن|ارتش یمن|انصارالله|حوثی ها مدعی"
                                "|ادعا|مدعی|اعلام کرد|اعلام کردند"))
_FA_INTERCEPT = re.compile(fa_norm("رهگیری|رهگیر|سرنگون|ساقط|منهدم کرد|منهدم شد"))
_FA_YEMEN_SITE = re.compile(fa_norm("در یمن|خاک یمن|صنعا|صعده|الحدیده|حدیده|راس عیسی|صلیف|مأرب|مارب|عدن|تعز|لحج|شبوه"
                                    "|حضرموت|مکلا|الجوف|جوف|عمران|ذمار"))

_EN_SAUDI_PLACE = re.compile(r"\b(riyadh|jeddah|jiddah|mecca|makkah|medina|madinah|taif|rabigh|khamis mushait|jizan|jazan"
                             r"|najran|abha|dhahran|dammam|ras tanura|abqaiq|yanbu|aramco|khurais|in saudi( arabia)?"
                             r"|saudi arabia's|(eastern|southern|western) (saudi|province|region of saudi)|inside saudi"
                             r"|on saudi( arabia)?|at saudi( arabia)?)\b", _I)
_FA_SAUDI_PLACE = re.compile(fa_norm("ریاض|جده|مکه|مدینه|طائف|رابغ|خمیس مشیط|جیزان|جازان|نجران|ابها|ظهران|دمام|راس تنوره"
                                     "|ابقیق|ینبع|آرامکو|خریص|در عربستان|خاک عربستان|شرق عربستان|جنوب عربستان"
                                     "|(به|علیه)\\s*(عربستان|سعودی)"))


def _sh_rx(fa):
    if fa:
        return dict(front2=_FA_FRONT2, place2=_FA_SAUDI, front=_FA_FRONT, main=_FA_MAIN, us=_FA_US, proxy=_FA_PROXY, saudi=_FA_SAUDI, attack=_FA_ATTACK,
                    sea=_FA_SEA, toll=_FA_TOLL, talk=_FA_TALK, review=_FA_REVIEW, future=_FA_FUTURE,
                    us_site=_FA_US_SITE, us_act=_FA_US_ACT, energy=_FA_ENERGY, airport=_FA_AIRPORT, damage=_FA_DAMAGE,
                    hit=_FA_HIT, hclaim=_FA_HCLAIM, intercept=_FA_INTERCEPT, yemen=_FA_YEMEN_SITE, place=_FA_SAUDI_PLACE)
    return dict(front2=_EN_FRONT2, place2=_EN_SAUDI, front=_EN_FRONT, main=_EN_MAIN, us=_EN_US, proxy=_EN_PROXY, saudi=_EN_SAUDI, attack=_EN_ATTACK,
                sea=_EN_SEA, toll=_EN_TOLL, talk=_EN_TALK, review=_EN_REVIEW, future=_EN_FUTURE,
                us_site=_EN_US_SITE, us_act=_EN_US_ACT, energy=_EN_ENERGY, airport=_EN_AIRPORT, damage=_EN_DAMAGE,
                hit=_EN_HIT, hclaim=_EN_HCLAIM, intercept=_EN_INTERCEPT, yemen=_EN_YEMEN_SITE, place=_EN_SAUDI_PLACE)


def saudi_houthi(title, lang="en", flags=()):
    """None when the report is not on the Saudi-Houthi front (or names Israel or Iran, or America striking),
    "major" for what may be red there (see the module's text), "secondary" for everything else on that front."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    r = _sh_rx(fa)
    if r["main"].search(t):
        return None
    if "evac" in flags and (r["front"].search(t) or r["place2"].search(t)):
        return "major"                   # staff told to leave Saudi Arabia or an oil city is itself an event
    if not (r["front"].search(t) or r["front2"].search(t)
            or (r["attack"].search(t) and r["place"].search(r["proxy"].sub(" ", t)))):
        return None                      # (a missile or drone on a Saudi city, airport or site: this front)
    us = r["us"].search(t)
    rv = r["review"].search(t)
    if rv and r["airport"].search(t) and re.match(r"flight|airline|لغو پرواز|ایرلاین|شرکت", rv.group(0), _I):
        rv = None                        # flights halted at an attacked airport are its damage, not a market story
    if rv or r["future"].search(t):
        return "secondary"
    a, w = r["attack"].search(t), r["talk"].search(t)
    if w and (not a or w.start() < a.start()):
        return "secondary"               # framed as a reaction, a warning or talks ("GCC condemns Houthi attack")
    if not a:
        return "secondary"
    if us and r["us_act"].search(t) and not r["us_site"].search(t):
        return None                      # America striking the Houthis: the general rules
    tp = r["proxy"].sub(" ", t)
    # the target is in Saudi Arabia: a Saudi city or site named, or Saudi Arabia named and no place in Yemen
    in_saudi = bool(r["place"].search(tp)) or (bool(r["saudi"].search(tp)) and not r["yemen"].search(tp))
    claim = bool(r["hclaim"].search(t))
    caught = bool(r["intercept"].search(t))
    if r["sea"].search(t):
        return "major"                   # ships attacked in the Red Sea or Bab el-Mandeb
    if r["us_site"].search(t):
        return "major" if not caught or r["hit"].search(t) else "secondary"   # America's bases, troops or embassy
    if r["energy"].search(t) and in_saudi:
        # Saudi oil and energy: hit (not only intercepted), and told by more than the Houthis' own spokesman
        if r["hit"].search(t) and not (claim and not r["damage"].search(t)):
            return "major"
        return "secondary"
    if r["airport"].search(t) and in_saudi and r["damage"].search(t) and not claim:
        return "major"                   # a Saudi airport on fire, destroyed or closed
    if us:
        return None if not in_saudi else "secondary"
    return "secondary"                   # interceptions, "targeted", strikes on Yemen, fighting inside Yemen, counts


# ------------------------------------------------------------------ Lebanon: Israel against Hezbollah
_EN_LEB = re.compile(r"\b(leban\w*|beirut|dahiyeh|dahieh|dahiya|tyre|sidon|nabatieh|nabatiyeh|bekaa|baalbek|bint jbeil"
                     r"|marjayoun|khiam|litani|hezbollah|hizbollah|hizballah|radwan|unifil)\b", _I)
_EN_LEB_OTHER = re.compile(r"\b(iran\w*|tehran|irgc|islamic republic|hormuz|houthis?|yemen\w*)\b", _I)
_EN_LEB_ATTACK = re.compile(r"\b(strik\w*|struck|airstrikes?|air strikes?|raids?|bomb\w*|shell\w*|hits?|target\w*"
                            r"|attack\w*|fire[sd]?|firing|launch\w*|rockets?|missiles?|drones?|killed|kills?|assassinat\w*"
                            r"|eliminat\w*|invasion|invad\w*|incursion|offensive|operation)\b", _I)
# Hezbollah firing at Israel
_EN_HZB_FIRE = re.compile(r"(^|[:;,|\u2013\u2014-]\s*|\b(as|after|says|said|while|and)\s+)(hezbollah|hizbollah|hizballah)\s+"
                          r"(\w+\s+){0,2}?(fires?|fired|launch\w*|strikes|struck|attacks|attacked|targets|targeted|shoots"
                          r"|shot|hits|hit|claims?|shells|shelled)\b"
                          r"|\b(rockets?|missiles?|drones?|projectiles?|barrage|anti-tank)\b[^.;]{0,40}\b(from|out of) "
                          r"(southern )?lebanon\b"
                          r"|\b(sirens?|rockets?|missiles?|drones?)\b[^.;]{0,40}\b(northern israel|galilee|haifa|kiryat shmona"
                          r"|metula|nahariya|safed|tiberias|golan|tel aviv)\b", _I)
_EN_BEIRUT = re.compile(r"\b(beirut|dahiyeh|dahieh|dahiya|southern suburbs?)\b", _I)
_EN_BEIRUT_NOT = re.compile(r"\b(port blast|port explosion|probe|investigat\w*|trial|court|anniversary|airport (reopen\w*"
                            r"|flights?)|parliament|cabinet|elect\w*)\b", _I)
_EN_STRIKE = re.compile(r"\b(strik\w*|struck|airstrikes?|air strikes?|raids?|bomb\w*|hits?|targets?|targeted|attack\w*"
                        r"|drone strike)\b", _I)
_EN_SENIOR = re.compile(r"\b(kill\w*|assassinat\w*|eliminat\w*|dead|death of)\b[^.;]{0,60}\b(senior|top|chief|leader"
                        r"|secretary[- ]general|naim qassem|qassem|head of|second[- ]in[- ]command|deputy (chief|leader))\b"
                        r"|\b(senior|top|chief|leader|secretary[- ]general|naim qassem|qassem|head of)\b[^.;]{0,60}"
                        r"\b(killed|assassinated|eliminated|dead)\b", _I)
_EN_WAR = re.compile(r"\b(ground (invasion|offensive|operation|incursion|forces? (enter|advance|push))|invad\w*"
                     r"|(launch\w*|begins?|began|starts?|started|expands?|expanded|widens?) (a |an |its )?(new |wide\w* "
                     r"|large\w* |major |broad\w* |full[- ]scale )?(military |air |ground )?(offensive|campaign|invasion"
                     r"|war)|war (resumes|returns|with hezbollah (resumes|erupts))|ceasefire (collaps\w*|ends|is over|breaks? down"
                     r"|broken)|all-out war|full-scale war|(heaviest|largest|biggest|widest|fiercest|most intense) (\w+ ){0,3}"
                     r"(strikes?|attacks?|bombing|raids?|wave|barrage)|across lebanon|wave of (air ?)?strikes across)\b", _I)
_EN_LEB_FUTURE = re.compile(r"\b(will|would|vows?|vowed|warns?|warned|threat\w*|plans?|could|may|might|prepar\w*|ready"
                            r"|if)\b", _I)

_FA_LEB = re.compile(fa_norm("لبنان|بیروت|ضاحیه|صور|صیدا|نبطیه|بقاع|بعلبک|بنت جبیل|مرجعیون|خیام|لیطانی|حزب الله|رضوان|یونیفل"))
_FA_LEB_OTHER = re.compile(fa_norm("ایران|تهران|سپاه|جمهوری اسلامی|هرمز|حوثی|یمن"))
_FA_LEB_ATTACK = re.compile(fa_norm("حمله|حملات|بمباران|هدف قرار|اصابت|شلیک|پرتاب|موشک|پهپاد|راکت|ترور|کشته|شهید|شهادت"
                                    "|تهاجم|یورش|عملیات|گلوله باران|توپخانه"))
_FA_HZB_FIRE = re.compile("(?:^|[:؛،.\\-]\\s*)" + fa_norm("حزب الله[^.؛]{0,30}(شلیک|پرتاب|حمله کرد|حمله به|هدف قرار داد|موشک|راکت|پهپاد|عملیات)")
                          + "|" + fa_norm("(موشک|راکت|پهپاد)[^.؛]{0,40}(از لبنان|از خاک لبنان|از جنوب لبنان)"
                                  "|(آژیر|موشک|راکت|پهپاد)[^.؛]{0,40}(شمال اسرائیل|شمال اسراییل|شمال فلسطین اشغالی|الجلیل|جلیل"
                                  "|حیفا|کریات شمونه|متولا|نهاریا|صفد|طبریه|جولان|تل آویو)"))
_FA_BEIRUT = re.compile(fa_norm("بیروت|ضاحیه|حومه جنوبی"))
_FA_BEIRUT_NOT = re.compile(fa_norm("انفجار بندر|تحقیقات|دادگاه|محاکمه|سالگرد|پارلمان|کابینه|انتخابات|پرواز"))
_FA_STRIKE = re.compile(fa_norm("حمله|حملات|بمباران|هدف قرار|اصابت|ترور|موشک باران"))
_FA_SENIOR = re.compile(fa_norm("(ترور|کشته|شهید|شهادت|به شهادت)[^.؛]{0,60}(ارشد|عالی رتبه|عالیرتبه|رئیس|دبیرکل|نعیم قاسم"
                                "|جانشین|معاون دبیرکل|رهبر)"
                                "|(ارشد|عالی رتبه|عالیرتبه|دبیرکل|نعیم قاسم|جانشین)[^.؛]{0,60}(ترور شد|کشته شد|به شهادت رسید"
                                "|شهید شد)"))
_FA_WAR = re.compile(fa_norm("حمله زمینی|تهاجم زمینی|عملیات زمینی|یورش زمینی|ورود (نیروهای|ارتش) [^.؛]{0,20}به لبنان|اشغال"
                             "|آغاز (جنگ|عملیات گسترده|حملات گسترده|تهاجم)|از سرگیری جنگ|جنگ تمام عیار|جنگ همه جانبه"
                             "|فروپاشی آتش بس|پایان آتش بس|آتش بس (شکست|فرو پاشید)|(شدیدترین|سنگین ترین|گسترده ترین|بزرگترین)"
                             "[^.؛]{0,30}(حمله|حملات|بمباران)|سراسر لبنان|موج (جدید )?حملات"))
_FA_LEB_FUTURE = re.compile(fa_norm("خواهد|خواهیم|نخواهد|تهدید|هشدار|آماده|در صورت|اگر|احتمال"))


def israel_lebanon(title, lang="en", flags=()):
    """None when the report is not about Lebanon (or names Iran), "major" for a big turn between Israel and
    Hezbollah (see the module's text), "secondary" for everything else there."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    if fa:
        front, other, attack, hzb, beirut, bnot, strike, senior, war, future, talk, review = (
            _FA_LEB, _FA_LEB_OTHER, _FA_LEB_ATTACK, _FA_HZB_FIRE, _FA_BEIRUT, _FA_BEIRUT_NOT, _FA_STRIKE, _FA_SENIOR,
            _FA_WAR, _FA_LEB_FUTURE, _FA_TALK, _FA_REVIEW)
    else:
        front, other, attack, hzb, beirut, bnot, strike, senior, war, future, talk, review = (
            _EN_LEB, _EN_LEB_OTHER, _EN_LEB_ATTACK, _EN_HZB_FIRE, _EN_BEIRUT, _EN_BEIRUT_NOT, _EN_STRIKE, _EN_SENIOR,
            _EN_WAR, _EN_LEB_FUTURE, _EN_TALK, _EN_REVIEW)
    if not front.search(t) or other.search(t):
        return None
    if "evac" in flags:
        return "major"                   # embassies telling their people to leave Lebanon
    a, w = attack.search(t), talk.search(t)
    if not a or future.search(t) or review.search(t) or (w and w.start() < a.start()):
        return "secondary"               # threats, plans, reactions, talks, politics in Beirut
    if hzb.search(t) or senior.search(t) or war.search(t):
        return "major"
    if beirut.search(t) and strike.search(t) and not bnot.search(t):
        return "major"                   # Israel striking Beirut or its southern suburbs
    return "secondary"                   # the daily strikes, drone strikes and shelling in the south and the Bekaa


def side_front(title, lang="en", flags=()):
    """(front, grade) of a report on a side front ("saudi_houthi" or "lebanon"; "major" or "secondary"), or None."""
    for name, fn in (("saudi_houthi", saudi_houthi), ("lebanon", israel_lebanon)):
        g = fn(title, lang, flags)
        if g:
            return name, g
    return None
