"""Rules for the side fronts: the Saudi-Houthi war and Israel against Hezbollah in Lebanon.

Both produce dozens of reports a day, and the bulletin is about the main front (Iran against America and Israel).
On these fronts a report is red only when it is a big turn ("major"). The everyday reports are yellow ("minor",
MINOR_CAP); on the Saudi-Houthi front an attack reaching Saudi soil that isn't a big turn stays orange at most
("secondary", SECONDARY_CAP). The index counts both lightly (index.py).

Saudi-Houthi, major: a Houthi attack that hits Saudi oil or energy sites (Aramco, refineries, oil terminals,
pipelines, power and desalination plants), an attack on America's interests in Saudi Arabia (its bases, troops,
embassy or consulates), wide damage to a Saudi airport (on fire, destroyed, closed), attacks on shipping in the Red
Sea and Bab el-Mandeb held to the Hormuz rules (a ship hit, on fire, sunk or seized, told by someone other than the
Houthis: UKMTO, Ambrey, a navy, the owner), and staff told to leave. Orange ("secondary"): missiles and drones on
Saudi soil intercepted, airports and cities "targeted" with no damage told, the Houthi spokesman's claims alone, ship
attacks claimed by the Houthis. Yellow ("minor"): Saudi or coalition strikes on Yemen, fighting inside Yemen, counts
of attacks, casualty figures inside Yemen, threats and vows of revenge, reactions, denials, statements, talks,
markets. A report that names Israel or Iran, or America striking, is left to the general rules.

Lebanon, major (a war, not the everyday strikes): a ground invasion or a new offensive, war resuming, the ceasefire
collapsing, the heaviest strikes in a long time or strikes across the country, a heavy Hezbollah barrage on Israel or
fire reaching Haifa or Tel Aviv, Hezbollah's own leader (secretary-general, deputy) killed, Israel and the Lebanese
state (its army, government) drawn into the fighting, embassies telling their people to leave. Everything else is
yellow ("minor"): the daily strikes anywhere in Lebanon (Beirut and its suburbs too), a commander killed, a single
launch at Israel, statements, protests, diplomacy, casualty figures. A report that names Iran is left to the
general rules."""
import re

from .util import fa_norm

_I = re.I
# whole Persian words: «عدن» is not in «معدن», «صور» not in «صورت», «ابها» not in «ابهام», «مخا» not in «مخالف»
_FL = "\u0620-\u06FF"


def _w(alts, suffix=""):
    """Persian alternatives as whole words (normalised), with an optional ending such as «ی» (یمنی، لبنانی)."""
    return (f"(?<![{_FL}])(?:" + fa_norm(alts) + ")" + (f"(?:{fa_norm(suffix)})?" if suffix else "")
            + f"(?![{_FL}])")

SECONDARY_CAP = 64.0          # an orange story, below the main front's orange ones
MINOR_CAP = 40.0              # a side front's everyday report: a yellow story

# ------------------------------------------------------------------ English
_EN_FRONT = re.compile(r"\b(houthis?|ansar ?allah|yemen\w*|sanaa|sana'a|saada|sa'ada|hodeidah|hudaydah|aden|lahij|lahj"
                       r"|taiz|ta'iz|marib|ma'rib|shabwa|hadramout|hadramawt|mukalla|abyan"
                       r"|bab[- ]el[- ]mandeb|bab al[- ]mandab|saree|sarea)\b", _I)
# Saudi Arabia's side telling of what it intercepted, with no Houthi named
_EN_FRONT2 = re.compile(r"\b(saudi[- ]led coalition|arab coalition|coalition (says|spokes\w*|forces))\b"
                        r"|\bcoalition\b[^.;]{0,60}\bsaudi|\bsaudi\b[^.;]{0,30}\bcoalition\b"
                        r"|\b(intercept\w*|shoots? down|shot down|downs?|downed|destroy\w*)\b[^.;]{0,60}\b(saudi\w*|riyadh|jeddah"
                        r"|mecca|makkah|medina|madinah|jizan|jazan|najran|abha|khamis mushait|dhahran|dammam|the kingdom)\b", _I)
_EN_OTHER = re.compile(r"\b(israel\w*|tel aviv|eilat|haifa|jerusalem|occupied palestine|dimona|beersheba|iran\w*|tehran|islamic republic|united states"
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
_EN_SEAS = (r"red sea|bab[- ]el[- ]mandeb|bab al[- ]mandab|gulf of aden|hodeidah|hudaydah|hodeida|mokha|mocha|salif"
            r"|ras isa|kamaran|perim|djibouti|assab|nishtun|mukalla|aden|yanbu|off (the coast of )?yemen")
_EN_SEA = re.compile(r"\b(ships?|vessels?|tankers?|freighters?|bulk carrier|container ship|merchant)\b.{0,80}"
                     r"\b(" + _EN_SEAS + r")\b"
                     r"|\b(" + _EN_SEAS + r")\b.{0,80}"
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
_FA_FRONT = re.compile(_w("حوثی|انصارالله|یمن", "ی|ها|های") + "|" + _w("صنعا|صعده|الحدیده|حدیده|عدن|لحج|تعز|مأرب|مارب|شبوه"
                                                                          "|حضرموت|مکلا|ابین|باب المندب|یحیی سریع"))
_FA_FRONT2 = re.compile(fa_norm("ائتلاف سعودی|ائتلاف عربی|ائتلاف متجاوز|سخنگوی ائتلاف"
                                "|(رهگیری|سرنگون|ساقط)[^.؛]{0,60}(عربستان|سعودی|ریاض|جده|مکه|مدینه|جیزان|جازان|نجران|ابها|دمام)"))
_FA_OTHER = re.compile(fa_norm("اسرائیل|اسراییل|صهیونیست|تل آویو|ایلات|حیفا|فلسطین اشغالی|سرزمین های اشغالی|سرزمینهای اشغالی|اراضی اشغالی|دیمونا|ایران|تهران|جمهوری اسلامی|آمریکا|امریکا"
                               "|ایالات متحده|پنتاگون|سنتکام|ترامپ"))
_FA_PROXY = re.compile(fa_norm("(وابسته به|مورد حمایت|تحت حمایت|طرفدار|مزدوران)\\s*(ریاض|عربستان|سعودی|آل سعود)"))
_FA_SAUDI = re.compile(_w("عربستان|سعودی|ائتلاف", "ی|ها|های") + "|" + _w("ریاض|جده|مکه|مدینه|طائف|رابغ|خمیس مشیط|جیزان"
                                                                           "|جازان|نجران|ابها|ظهران|راس تنوره|ابقیق|ینبع|آرامکو"))
_FA_ATTACK = re.compile(fa_norm("حمله|حملات|هدف قرار|اصابت|شلیک|پرتاب|موشک|پهپاد|رهگیری|رهگیر|سرنگون|منهدم|انهدام"
                                "|بمباران|انفجار|آوار|بقایای موشک|ترکش|آتش سوزی|عملیات"))
_FA_SEAS = "دریای سرخ|باب المندب|خلیج عدن|حدیده|الحدیده|مخا|صلیف|راس عیسی|کمران|میون|جیبوتی|عصب|نشطون|مکلا|عدن|ینبع|سواحل یمن"
_FA_SEA = re.compile(fa_norm("(کشتی|نفتکش|شناور)[^.؛]{0,60}") + _w(_FA_SEAS) + "|" + _w(_FA_SEAS)
                     + fa_norm("[^.؛]{0,60}(کشتی|نفتکش|شناور)"))
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
_EN_MAIN = re.compile(r"\b(israel\w*|tel aviv|eilat|haifa|jerusalem|occupied palestine|dimona|beersheba|iran\w*|tehran|islamic republic)\b", _I)
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
_EN_YEMEN_SITE = re.compile(r"\b(in yemen|yemen's|(on|against|across|of|over|into) yemen|yemeni|sanaa|sana'a|saada|hodeidah|hudaydah|ras isa|salif|marib|ma'rib|aden"
                            r"|taiz|lahj|shabwa|hadramout|mukalla|al-jawf|jawf|amran|dhamar)\b", _I)

# counts of attacks ("105 attacks in 24 hours", «۱۰۵ بار به یمن حمله کرد»)
_EN_TALLY = re.compile(r"\b\d{2,}[\d,]*\s+(\w+\s+){0,3}(attacks|strikes|raids|airstrikes|air strikes|times|operations)\b"
                       r"|\b(dozens|scores|hundreds) of (\w+ ){0,2}(attacks|strikes|raids|airstrikes)\b", _I)
_FA_TALLY = re.compile(fa_norm(r"\d{2,}\s*(بار|حمله|حملات|عملیات|بمباران|نوبت)|(ده ها|دهها|صدها)\s*(حمله|بار|عملیات)"))

# Saudi Arabia named as the one striking ("killed in Saudi air strike", «حمله هوایی عربستان»), not as the place hit
_EN_SAUDI_ACTOR = re.compile(r"\b(saudi|coalition)(-led| led)?( \w+)?( (air ?strikes?|airstrikes?|strikes?|raids?|attacks?"
                             r"|bombing|bombardment|jets?|warplanes?|fighters?|forces|troops|shelling|artillery|aggression))+\b"
                             r"|\bsaudi-led( coalition)?\b|\b(saudi|arab|saudi-led) coalition\b", _I)
_FA_SAUDI_ACTOR = re.compile(fa_norm(r"(حمله|حملات|بمباران|تجاوز|یورش)( هوایی| موشکی| توپخانه ای)? (رژیم |ائتلاف |جنگنده های |)"
                                     r"(عربستان سعودی|عربستان|سعودی|آل سعود)|(جنگنده های|هواپیماهای|ائتلاف|رژیم|متجاوزان|نیروهای) (سعودی|آل سعود)"
                                     r"|ائتلاف (متجاوز )?(عربستان|سعودی)"))
_FA_MAIN = re.compile(fa_norm("اسرائیل|اسراییل|صهیونیست|تل آویو|ایلات|حیفا|فلسطین اشغالی|سرزمین های اشغالی|سرزمینهای اشغالی|اراضی اشغالی|دیمونا|ایران|تهران|جمهوری اسلامی"))
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
_FA_YEMEN_SITE = re.compile(_w("در یمن|خاک یمن|به یمن|علیه یمن|بر یمن|یمنی|مردم یمن|مناطق یمن|استان های یمن|صنعا|صعده"
                               "|الحدیده|حدیده|راس عیسی|صلیف|مأرب|مارب|عدن|تعز|لحج|شبوه|حضرموت|مکلا|الجوف|جوف|عمران|ذمار"))

# "killed in Saudi strikes", "on Saudi-backed forces": Saudi Arabia acting, not a place in Saudi Arabia
_NOT_SAUDI_ACT = (r"(?![- ](led|backed|coalition|strikes?|air|airstrikes?|raids?|attacks?|bomb\w*|jets?|warplanes?|fighters?"
                  r"|shell\w*|artillery|missiles?|drones?|forces|troops|army|military|aggression)\b)")
_EN_SAUDI_PLACE = re.compile(r"\b(riyadh|jeddah|jiddah|mecca|makkah|medina|madinah|taif|rabigh|khamis mushait|jizan|jazan"
                             r"|najran|abha|dhahran|dammam|ras tanura|abqaiq|yanbu|aramco|khurais|in saudi( arabia)?" + _NOT_SAUDI_ACT +
                             r"|saudi arabia's|(eastern|southern|western) (saudi|province|region of saudi)|inside saudi"
                             r"|on saudi( arabia)?" + _NOT_SAUDI_ACT + r"|at saudi( arabia)?" + _NOT_SAUDI_ACT + r")\b", _I)
_FA_SAUDI_PLACE = re.compile(_w("ریاض|جده|مکه|مدینه|طائف|رابغ|خمیس مشیط|جیزان|جازان|نجران|ابها|ظهران|دمام|راس تنوره"
                                "|ابقیق|ینبع|آرامکو|خریص|در عربستان|خاک عربستان|شرق عربستان|جنوب عربستان"
                                "|(به|علیه)\\s*(عربستان|سعودی)"))


# Ships in the Red Sea, Bab el-Mandeb and the Gulf of Aden, held to the rules of ships in Hormuz: red only for an
# incident that happened (a ship hit, on fire, damaged, sunk, seized), told by someone other than the attacker. Not
# the Houthis' own claims ("we targeted the ship X"), nor an Iranian outlet's report that cites no one else, nor a
# tally of ships or something past. (A lone report with no time or place stays orange too: cluster._vague_at_sea.)
_EN_SEA_DONE = re.compile(r"\b(hit|hits|struck|ablaze|on fire|fire|burning|blaze|explosions?|exploded|blasts?|damag\w*"
                          r"|disabled|adrift|sank|sinks|sinking|sunk|capsiz\w*|seiz\w*|hijack\w*|boarded|taken over"
                          r"|crew (killed|injured|hurt|evacuated|abandon\w*)|abandon\w* ship|projectile)\b", _I)
_FA_SEA_DONE = re.compile(fa_norm("اصابت|آتش گرفت|آتش سوزی|در آتش|شعله|انفجار|منفجر|آسیب|خسارت|غرق|توقیف|ربوده|تصرف"
                                  "|از کار افتاد|خدمه[^.؛]{0,20}(کشته|زخمی|مجروح|تخلیه)"))
_EN_SEA_INDEP = re.compile(r"\b(ukmto|u\.?k\.? maritime|ambrey|vanguard|centcom|aspides|eunavfor|atalanta|maritime security"
                           r"|(ship|vessel|tanker)'s (owner|operator|manager)|owner|operator|shipping (company|firm)|maersk"
                           r"|lloyd'?s|windward|confirm\w*|coast ?guard|navy|naval)\b", _I)
_FA_SEA_INDEP = re.compile(fa_norm("ukmto|عملیات تجارت دریایی|آمبری|وانگارد|سنتکام|اسپیدس|آتالانتا|امنیت دریایی|مالک کشتی"
                                   "|شرکت کشتیرانی|اپراتور|مرسک|لویدز|تایید کرد|تأیید کرد|گارد ساحلی|نیروی دریایی"))
_EN_SEA_CLAIM = re.compile(r"\b(saree|sarea|houthis? (say|says|said|claim\w*)|claims?|claimed|(yemeni|houthi) (armed forces"
                           r"|army|military|navy|naval forces|spokes\w*)|ansar ?allah|al-?masirah|we (targeted|struck|hit)"
                           r"|targeted)\b", _I)
_FA_SEA_CLAIM = re.compile(fa_norm("یحیی سریع|سخنگوی (نیروهای مسلح|ارتش) یمن|نیروهای مسلح یمن|ارتش یمن|نیروی دریایی یمن"
                                   "|انصارالله|المسیره|ادعا|مدعی|هدف قرار دادیم|هدف قرار داد|هدف قرار گرفت"))
_EN_SEA_RECAP = re.compile(r"\b(\d+|dozens|several|multiple|scores|hundreds) (\w+ ){0,2}(ships|vessels|tankers|attacks)\b"
                           r"|\bsince\b|\b(last|past|previous) (week|month|year)|\bearlier this (week|month)|\bin \d{4}\b", _I)
_FA_SEA_RECAP = re.compile(fa_norm(r"(\d+|ده ها|دهها|چندین|صدها)\s*(فروند|کشتی|نفتکش|شناور|حمله)|از زمان|از ابتدای"
                                   r"|هفته گذشته|ماه گذشته|سال گذشته"))
_IR_OUTLETS = {"irna", "fars", "isna", "mehr", "iribnews", "nournews", "defapress", "tasnim", "presstv", "khabaronline",
               "entekhab", "masirah", "almasirah", "saba"}


def _red_sea(t, fa, src="", text=""):
    """"major" for a ship attack in the Red Sea that may be red (see above), else "secondary"."""
    done, indep, claim, recap = ((_FA_SEA_DONE, _FA_SEA_INDEP, _FA_SEA_CLAIM, _FA_SEA_RECAP) if fa
                                 else (_EN_SEA_DONE, _EN_SEA_INDEP, _EN_SEA_CLAIM, _EN_SEA_RECAP))
    told = t + " " + (text or "")[:400]
    if recap.search(t) or not done.search(t):
        return "minor" if recap.search(t) else "secondary"   # a tally or something past; only "targeted"
    if indep.search(told):
        return "major"                   # UKMTO, Ambrey, a navy, the ship's owner…
    if claim.search(t) or (src or "").split(":")[0] in _IR_OUTLETS:
        return "secondary"               # the Houthis' own account, or an outlet of their side citing no one
    return "major"


def _sh_rx(fa):
    if fa:
        return dict(front2=_FA_FRONT2, place2=_FA_SAUDI, front=_FA_FRONT, main=_FA_MAIN, us=_FA_US, proxy=_FA_PROXY, saudi=_FA_SAUDI, attack=_FA_ATTACK,
                    sea=_FA_SEA, toll=_FA_TOLL, talk=_FA_TALK, review=_FA_REVIEW, future=_FA_FUTURE,
                    tally=_FA_TALLY, actor=_FA_SAUDI_ACTOR, us_site=_FA_US_SITE, us_act=_FA_US_ACT, energy=_FA_ENERGY, airport=_FA_AIRPORT, damage=_FA_DAMAGE,
                    hit=_FA_HIT, hclaim=_FA_HCLAIM, intercept=_FA_INTERCEPT, yemen=_FA_YEMEN_SITE, place=_FA_SAUDI_PLACE)
    return dict(front2=_EN_FRONT2, place2=_EN_SAUDI, front=_EN_FRONT, main=_EN_MAIN, us=_EN_US, proxy=_EN_PROXY, saudi=_EN_SAUDI, attack=_EN_ATTACK,
                sea=_EN_SEA, toll=_EN_TOLL, talk=_EN_TALK, review=_EN_REVIEW, future=_EN_FUTURE,
                tally=_EN_TALLY, actor=_EN_SAUDI_ACTOR, us_site=_EN_US_SITE, us_act=_EN_US_ACT, energy=_EN_ENERGY, airport=_EN_AIRPORT, damage=_EN_DAMAGE,
                hit=_EN_HIT, hclaim=_EN_HCLAIM, intercept=_EN_INTERCEPT, yemen=_EN_YEMEN_SITE, place=_EN_SAUDI_PLACE)


def saudi_houthi(title, lang="en", flags=(), src="", text=""):
    """None when the report is not on the Saudi-Houthi front (or names Israel or Iran, or America striking),
    "major" for what may be red there, "secondary" (orange) for an attack on Saudi soil, "minor" (yellow) for the rest
    (see the module's text)."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    r = _sh_rx(fa)
    if r["main"].search(t):
        return None
    if "evac" in flags and (r["front"].search(t) or r["place2"].search(t)):
        return "major"                   # staff told to leave Saudi Arabia or an oil city is itself an event
    if not (r["front"].search(t) or r["front2"].search(t) or r["sea"].search(t)
            or (r["attack"].search(t) and r["place"].search(r["proxy"].sub(" ", t)))):
        return None                      # (a missile or drone on a Saudi city, airport or site: this front)
    us = r["us"].search(t)
    rv = r["review"].search(t)
    if rv and r["airport"].search(t) and re.match(r"flight|airline|لغو پرواز|ایرلاین|شرکت", rv.group(0), _I):
        rv = None                        # flights halted at an attacked airport are its damage, not a market story
    if rv or r["future"].search(t):
        return "minor"                   # threats, vows of revenge, markets, analysis
    a, w = r["attack"].search(t), r["talk"].search(t)
    if w and (not a or w.start() < a.start()):
        return "minor"                   # framed as a reaction, a warning or talks ("GCC condemns Houthi attack")
    if not a:
        return "minor"                   # statements, denials, troops rumoured, captures inside Yemen
    if us and r["us_act"].search(t) and not r["us_site"].search(t):
        return None                      # America striking the Houthis: the general rules
    tp = r["proxy"].sub(" ", t)
    # the target is in Saudi Arabia: a Saudi city or site named, or Saudi Arabia named and no place in Yemen
    in_saudi = bool(r["place"].search(tp)) or (bool(r["saudi"].search(r["actor"].sub(" ", tp))) and not r["yemen"].search(tp))
    claim = bool(r["hclaim"].search(t))
    caught = bool(r["intercept"].search(t))
    if r["sea"].search(t):
        return _red_sea(t, fa, src, fa_norm(text or "") if fa else text)   # ships in the Red Sea: strict
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
    if not in_saudi or r["tally"].search(t):
        return "minor"                   # strikes on Yemen, fighting inside Yemen, counts, casualty figures
    return "secondary"                   # missiles and drones on Saudi soil intercepted or "targeted"


# ------------------------------------------------------------------ Lebanon: Israel against Hezbollah
_EN_LEB = re.compile(r"\b(leban\w*|beirut|dahiyeh|dahieh|dahiya|tyre|sidon|nabatieh|nabatiyeh|bekaa|baalbek|bint jbeil"
                     r"|marjayoun|khiam|litani|hezbollah|hizbollah|hizballah|radwan|unifil)\b", _I)
_EN_LEB_OTHER = re.compile(r"\b(iran\w*|tehran|irgc|islamic republic|hormuz|houthis?|yemen\w*)\b", _I)
_EN_LEB_ATTACK = re.compile(r"\b(strik\w*|struck|airstrikes?|air strikes?|raids?|bomb\w*|shell\w*|hits?|target\w*"
                            r"|attack\w*|fire[sd]?|firing|launch\w*|rockets?|missiles?|drones?|killed|kills?|assassinat\w*"
                            r"|eliminat\w*|invasion|invad\w*|incursion|offensive|operation)\b", _I)
# Hezbollah firing at Israel
# a heavy barrage, or fire reaching deep into Israel: a battle, not one launch
_EN_HZB_BIG = re.compile(r"\b(barrages?|salvos?|waves?|dozens|scores|hundreds|massive|heavy|heaviest|largest|biggest"
                         r"|intense|widespread|\d{2,} (rockets?|missiles?|drones?|projectiles?))\b"
                         r"|\b(haifa|tel aviv|central israel|jerusalem|netanya|hadera)\b", _I)
_FA_HZB_BIG = re.compile(fa_norm(r"رگبار|موج|ده ها|دهها|صدها|گسترده|سنگین|سنگین ترین|بزرگترین|\d{2,}\s*(موشک|راکت|پهپاد)"
                                 r"|حیفا|تل آویو|مرکز اسرائیل|قدس|نتانیا|حدیره"))
# the Lebanese state drawn in: its army fighting Israel's, Israel striking its army or government, war between states
_EN_STATE = re.compile(r"\b(lebanese (army|armed forces|soldiers?|troops|government|state|president|military))\b[^.;]{0,60}"
                       r"\b(clash\w*|exchange\w* (of )?fire|fir(e|es|ed|ing) (at|on)|engag\w*|attacked|declares? war|at war)\b"
                       r"|\b(clash\w*|exchange\w* of fire|fighting|battles?)\b[^.;]{0,30}\blebanese (army|armed forces|soldiers"
                       r"|troops|military)\b"
                       r"|\b(israel\w*|idf)\b[^.;]{0,40}\b(strik\w*|struck|attack\w*|bomb\w*|target\w*)\b"
                       r"[^.;]{0,30}\b(lebanese (army|armed forces|government|state|military|ministry) (positions?|bases?"
                       r"|barracks|headquarters|posts?|buildings?|offices?)|lebanese (government|state|presidential|ministry)\b"
                       r"|(positions?|bases?|barracks|posts?) of the lebanese (army|armed forces))"
                       r"|\b(israel and lebanon|lebanon and israel) (at war|go to war|clash\w*)\b", _I)
_FA_STATE = re.compile(fa_norm(r"(ارتش|نیروهای مسلح|دولت|نظامیان|سربازان|رئیس جمهور) لبنان[^.؛]{0,60}(درگیری|درگیر شد|تبادل آتش"
                               r"|شلیک به|اعلام جنگ|حالت جنگ)"
                               r"|(درگیری|تبادل آتش|نبرد)[^.؛]{0,30}(ارتش|نیروهای مسلح|نظامیان|سربازان) لبنان"
                               r"|(اسرائیل|اسراییل|صهیونیست|اشغالگر)[^.؛]{0,40}(حمله|حملات|بمباران|هدف قرار)[^.؛]{0,30}"
                               r"(مواضع|پایگاه|پایگاه های|مقر|پادگان) (ارتش|نیروهای مسلح) لبنان|(حمله|حملات|بمباران)[^.؛]{0,30}"
                               r"(وزارت|دولت|کاخ ریاست جمهوری) لبنان"
                               r"|جنگ (میان|بین) (لبنان و اسرائیل|اسرائیل و لبنان)"))
_EN_HZB_FIRE = re.compile(r"(^|[:;,|\u2013\u2014-]\s*|\b(as|after|says|said|while|and)\s+)(hezbollah|hizbollah|hizballah)\s+"
                          r"(\w+\s+){0,2}?(fires?|fired|launch\w*|strikes|struck|attacks|attacked|targets|targeted|shoots"
                          r"|shot|hits|hit|claims?|shells|shelled)\b"
                          r"|\b(rockets?|missiles?|drones?|projectiles?|barrage|anti-tank)\b[^.;]{0,40}\b(from|out of) "
                          r"(southern )?lebanon\b"
                          r"|\b(sirens?|rockets?|missiles?|drones?)\b[^.;]{0,40}\b(northern israel|galilee|haifa|kiryat shmona"
                          r"|metula|nahariya|safed|tiberias|golan|tel aviv)\b", _I)
_EN_SENIOR = re.compile(r"\b(kill\w*|assassinat\w*|eliminat\w*|dead|death of)\b[^.;]{0,60}\b(hezbollah('s)? (leader|chief)"
                        r"|secretary[- ]general|naim qassem|qassem|second[- ]in[- ]command|deputy (secretary[- ]general|chief|leader))\b"
                        r"|\b(hezbollah('s)? (leader|chief)|secretary[- ]general|naim qassem|qassem)\b[^.;]{0,60}"
                        r"\b(killed|assassinated|eliminated|dead)\b", _I)
_EN_WAR = re.compile(r"\b(ground (invasion|offensive|operation|incursion|forces? (enter|advance|push))|invad\w*"
                     r"|(launch\w*|begins?|began|starts?|started|expands?|expanded|widens?) (a |an |its )?(new |wide\w* "
                     r"|large\w* |major |broad\w* |full[- ]scale )?(military |air |ground )?(offensive|campaign|invasion"
                     r"|war)|war (resumes|returns|with hezbollah (resumes|erupts))|ceasefire (collaps\w*|ends|is over|breaks? down"
                     r"|broken)|all-out war|full-scale war|(heaviest|largest|biggest|widest|fiercest|most intense) (\w+ ){0,3}"
                     r"(strikes?|attacks?|bombing|raids?|wave|barrage)|across lebanon|wave of (air ?)?strikes across)\b", _I)
_EN_LEB_FUTURE = re.compile(r"\b(will|would|vows?|vowed|warns?|warned|threat\w*|plans?|could|may|might|prepar\w*|ready"
                            r"|if)\b", _I)

_FA_LEB = re.compile(_w("لبنان", "ی|ها") + "|" + _w("بیروت|ضاحیه|صور|صیدا|نبطیه|بقاع|بعلبک|بنت جبیل|مرجعیون|خیام|لیطانی"
                                                     "|حزب الله|رضوان|یونیفل"))
_FA_LEB_OTHER = re.compile(fa_norm("ایران|تهران|سپاه|جمهوری اسلامی|هرمز|حوثی|یمن"))
_FA_LEB_ATTACK = re.compile(fa_norm("حمله|حملات|بمباران|هدف قرار|اصابت|شلیک|پرتاب|موشک|پهپاد|راکت|ترور|کشته|شهید|شهادت"
                                    "|تهاجم|یورش|عملیات|گلوله باران|توپخانه"))
_FA_HZB_FIRE = re.compile("(?:^|[:؛،.\\-]\\s*)" + fa_norm("حزب الله[^.؛]{0,30}(شلیک|پرتاب|حمله کرد|حمله به|هدف قرار داد|موشک|راکت|پهپاد|عملیات)")
                          + "|" + fa_norm("(موشک|راکت|پهپاد)[^.؛]{0,40}(از لبنان|از خاک لبنان|از جنوب لبنان)"
                                  "|(آژیر|موشک|راکت|پهپاد)[^.؛]{0,40}(شمال اسرائیل|شمال اسراییل|شمال فلسطین اشغالی|الجلیل|جلیل"
                                  "|حیفا|کریات شمونه|متولا|نهاریا|صفد|طبریه|جولان|تل آویو)"))
_FA_SENIOR = re.compile(fa_norm("(ترور|کشته|شهید|شهادت|به شهادت)[^.؛]{0,60}(دبیرکل|نعیم قاسم|معاون دبیرکل|رهبر حزب الله)"
                                "|(دبیرکل|نعیم قاسم|معاون دبیرکل|رهبر حزب الله)[^.؛]{0,60}(ترور شد|کشته شد|به شهادت رسید"
                                "|شهید شد)"))
_FA_WAR = re.compile(fa_norm("حمله زمینی|تهاجم زمینی|عملیات زمینی|یورش زمینی|ورود (نیروهای|ارتش) [^.؛]{0,20}به لبنان|اشغال (جنوب|مناطق|منطقه|شهر|روستا|خاک)"
                             "|آغاز (جنگ|عملیات گسترده|حملات گسترده|تهاجم)|از سرگیری جنگ|جنگ تمام عیار|جنگ همه جانبه"
                             "|فروپاشی آتش بس|پایان آتش بس|آتش بس (شکست|فرو پاشید)|(شدیدترین|سنگین ترین|گسترده ترین|بزرگترین)"
                             "[^.؛]{0,30}(حمله|حملات|بمباران)|سراسر لبنان|موج (جدید )?حملات"))
_FA_LEB_FUTURE = re.compile(fa_norm("خواهد|خواهیم|نخواهد|تهدید|هشدار|آماده|در صورت|اگر|احتمال"))


def israel_lebanon(title, lang="en", flags=()):
    """None when the report is not about Lebanon (or names Iran), "major" for a war between Israel and Hezbollah or
    Lebanon (see the module's text), "minor" for everything else there."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    if fa:
        front, other, attack, hzb, big, state, senior, war, future, talk, review = (
            _FA_LEB, _FA_LEB_OTHER, _FA_LEB_ATTACK, _FA_HZB_FIRE, _FA_HZB_BIG, _FA_STATE, _FA_SENIOR,
            _FA_WAR, _FA_LEB_FUTURE, _FA_TALK, _FA_REVIEW)
    else:
        front, other, attack, hzb, big, state, senior, war, future, talk, review = (
            _EN_LEB, _EN_LEB_OTHER, _EN_LEB_ATTACK, _EN_HZB_FIRE, _EN_HZB_BIG, _EN_STATE, _EN_SENIOR,
            _EN_WAR, _EN_LEB_FUTURE, _EN_TALK, _EN_REVIEW)
    if not front.search(t) or other.search(t):
        return None
    if "evac" in flags:
        return "major"                   # embassies telling their people to leave Lebanon
    a, w = attack.search(t), talk.search(t)
    if state.search(t) and not future.search(t):
        return "major"                   # Israel and the Lebanese state (its army, its government) drawn in
    if not a or future.search(t) or review.search(t) or (w and w.start() < a.start()):
        return "minor"                   # threats, plans, reactions, talks, protests, politics in Beirut
    if war.search(t) or senior.search(t) or (hzb.search(t) and big.search(t)):
        return "major"                   # a war: an invasion, an offensive, the Lebanese state drawn in, a heavy barrage
    return "minor"                       # the daily strikes anywhere in Lebanon (Beirut too), a commander, one launch


# ------------------------------------------------------------------ Gaza: Israel against Hamas
# Fighting in Gaza goes on every day: a strike, a toll, a hospital hit is a yellow story. Orange (never red) only for
# a big turn: a senior Hamas or Islamic Jihad leader or commander killed, the war resumed, a ground offensive, the
# ceasefire collapsed. Not when the headline names Iran, America, Yemen or Lebanon, or fire reaching Israel's soil.
_EN_GAZA = re.compile(r"\b(gaza\w*|khan younis|khan yunis|rafah|jabalia|jabaliya|deir al-balah|deir el-balah|nuseirat"
                      r"|bureij|maghazi|beit lahia|beit hanoun|nasser (hospital|medical complex)|al-shifa|shifa hospital"
                      r"|al-ahli (arab )?hospital|hamas|islamic jihad|qassam|al-quds brigades)\b", _I)
_EN_GAZA_OTHER = re.compile(r"\b(iran\w*|tehran|irgc|islamic republic|hormuz|houthis?|yemen\w*|leban\w*|hezbollah"
                            r"|u\.?s\.?|united states|american|pentagon|centcom|trump|washington"
                            r"|tel aviv|haifa|jerusalem|eilat|beersheba|ashkelon|ashdod|sderot|in israel|central israel"
                            r"|southern israel)\b", _I)
_EN_GAZA_SENIOR = re.compile(r"\b(kill\w*|assassinat\w*|eliminat\w*|dead|death of)\b[^.;]{0,60}\b((senior|top|chief|military"
                             r"|political) (hamas|islamic jihad|qassam|al-quds)|(hamas|islamic jihad|qassam|al-quds brigades)"
                             r"('s?)? (\w+ ){0,2}(leader|chief|head|commander|politburo|political bureau|founder|deputy)"
                             r"|sinwar|haddad|hayya|mashaal|meshaal)\b"
                             r"|\b((senior|top) (hamas|islamic jihad) (\w+ )?(leader|commander|official|figure)"
                             r"|(hamas|islamic jihad|qassam)('s?)? (\w+ ){0,2}(leader|chief|commander)|sinwar|haddad|hayya"
                             r"|mashaal|meshaal)\b[^.;]{0,60}\b(killed|assassinated|eliminated|dead)\b", _I)
_EN_GAZA_WAR = re.compile(r"\b(ground (invasion|offensive|operation|incursion|forces? (enter|advance|push))|invad\w*"
                          r"|(launch\w*|begins?|began|starts?|started|resumes?|resumed|expands?|expanded|widens?) (a |an |its |the )?"
                          r"(new |wide\w* |large\w* |major |broad\w* |full[- ]scale )?(military |air |ground )?(offensive|campaign"
                          r"|invasion|war)|war (in gaza )?(resumes|returns|erupts)|ceasefire (collaps\w*|ends|is over|breaks? down"
                          r"|broken|over)|(ends?|ended|collaps\w*) (the )?(gaza )?ceasefire|all-out war|full-scale war)\b", _I)
_FA_GAZA = re.compile(_w("غزه|خان یونس|خانیونس|رفح|جبالیا|دیر البلح|نصیرات|بریج|مغازی|بیت لاهیا|بیت حانون|حماس|جهاد اسلامی"
                         "|قسام|سرایا القدس|بیمارستان ناصر|مجتمع پزشکی ناصر|الشفا|بیمارستان شفا"))
_FA_GAZA_OTHER = re.compile(fa_norm("ایران|تهران|سپاه|جمهوری اسلامی|هرمز|حوثی|یمن|لبنان|حزب الله|آمریکا|امریکا|ایالات متحده"
                                    "|پنتاگون|سنتکام|ترامپ|واشنگتن|تل آویو|حیفا|قدس اشغالی|ایلات|بئرشبع|عسقلان|اسدود|سدیروت"
                                    "|فلسطین اشغالی|سرزمین های اشغالی|سرزمینهای اشغالی|اراضی اشغالی"))
_FA_GAZA_SENIOR = re.compile(fa_norm("(ترور|کشته|کشتن|شهید|شهادت|به شهادت|به قتل)[^.؛]{0,60}(فرمانده|رهبر|عضو ارشد|مقام ارشد|رئیس دفتر سیاسی"
                                     "|معاون|بنیانگذار|سنوار|حداد|الحیه|مشعل)"
                                     "|(فرمانده|رهبر|عضو ارشد|مقام ارشد|رئیس دفتر سیاسی|سنوار|حداد|الحیه|مشعل)[^.؛]{0,60}"
                                     "(ترور شد|کشته شد|به شهادت رسید|شهید شد|را[^.؛]{0,30}(کشت|ترور کرد|به شهادت رساند|به قتل رساند))"))
_FA_GAZA_WAR = re.compile(fa_norm("حمله زمینی|تهاجم زمینی|عملیات زمینی|یورش زمینی|آغاز (دوباره )?(جنگ|عملیات گسترده|حملات گسترده|تهاجم)"
                                  "|از سرگیری (جنگ|حملات)|ازسرگیری (جنگ|حملات)|جنگ تمام عیار|جنگ همه جانبه|فروپاشی آتش بس"
                                  "|پایان آتش بس|آتش بس (شکست|فرو پاشید|نقض شد و جنگ)"))


def israel_gaza(title, lang="en", flags=()):
    """None when the report is not about Gaza (or names Iran, America, Yemen, Lebanon or Israel's own soil),
    "secondary" for a big turn there (a senior leader or commander killed, the war resumed, a ground offensive),
    "minor" for everything else there."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    front, other, senior, war, future = (_FA_GAZA, _FA_GAZA_OTHER, _FA_GAZA_SENIOR, _FA_GAZA_WAR, _FA_LEB_FUTURE) if fa \
        else (_EN_GAZA, _EN_GAZA_OTHER, _EN_GAZA_SENIOR, _EN_GAZA_WAR, _EN_LEB_FUTURE)
    if not front.search(t) or other.search(t):
        return None
    if (senior.search(t) or war.search(t)) and not future.search(t):
        return "secondary"
    return "minor"


def side_front(title, lang="en", flags=(), src="", text=""):
    """(front, grade) of a report on a side front ("saudi_houthi", "lebanon" or "gaza"; "major", "secondary" or "minor"), or None.
    src (the outlet) and text (the summary) tell who a ship attack in the Red Sea is told by."""
    g = saudi_houthi(title, lang, flags, src, text)
    if g:
        return "saudi_houthi", g
    g = israel_lebanon(title, lang, flags)
    if g:
        return "lebanon", g
    g = israel_gaza(title, lang, flags)
    return ("gaza", g) if g else None


# ------------------------------------------------------------------ the Gulf Arab front: one attack, one story
# Missiles and drones on a Gulf Arab city (Riyadh, Najran, the Eastern Province, Dubai, Doha, Manama…) are told by
# each outlet from another side: "explosions heard in Riyadh", "two ballistic missiles intercepted over Riyadh",
# «حمله هوایی به پایتخت عربستان», "the civil defence reported a missile attack on Riyadh". Their headlines share few
# words, so the usual rules leave each in a story of its own. gulf_mark() gives such a report's kind ("attack", or
# "alert" for sirens and civil-defence warnings, which make a story of their own), the places it names and their
# countries; cluster.same_gulf() joins reports of one kind and place told within two hours. Only for this front: a
# report naming Iran, Israel or America (the main front) gets no mark, nor a story holding one (cluster.py).
_GULF_EN = {
    "riyadh": r"riyadh|saudi(?: arabia'?s?)? capital|capital of saudi(?: arabia)?|(?:the )?kingdom'?s capital",
    "najran": r"najran", "jizan": r"jizan|jazan|gizan", "abha": r"abha|khamis mushait", "jeddah": r"jeddah|jiddah",
    "mecca": r"mecca|makkah", "medina": r"medina|madinah", "taif": r"taif", "yanbu": r"yanbu|rabigh",
    "east": r"eastern (?:province|region)|east(?:ern)? (?:of )?saudi(?: arabia)?|dammam|dhahran|khobar|ras tanura"
            r"|abqaiq|jubail|qatif|al-?ahsa|hofuf",
    "dubai": r"dubai", "abu_dhabi": r"abu dhabi|al dhafra|emirati capital|uae'?s? capital", "fujairah": r"fujairah",
    "sharjah": r"sharjah|ras al[- ]khaimah", "qatar": r"doha|qatar|al udeid|ras laffan", "bahrain": r"bahrain|manama",
    "kuwait": r"kuwait", "muscat": r"muscat|duqm|salalah|sohar",
    # the Arab Middle East beyond the Gulf (item 2 of the Gulf rule: later reports of one attack): Jordan and Iraq.
    # Lebanon and Syria keep their own rules (several strikes a day in one city there are separate stories).
    "amman": r"amman|aqaba|zarqa|irbid", "baghdad": r"baghdad", "erbil": r"erbil|irbil|arbil",
    "basra": r"basra|basrah", "kirkuk": r"kirkuk", "mosul": r"mosul", "sulaymaniyah": r"sulaymaniyah|sulaimaniyah",
    "duhok": r"duhok|dohuk", "najaf": r"najaf", "karbala": r"karbala"}
_GULF_FA = {
    "riyadh": "ریاض|پایتخت عربستان|پایتخت سعودی", "najran": "نجران", "jizan": "جیزان|جازان", "abha": "ابها|خمیس مشیط",
    "jeddah": "جده", "mecca": "مکه", "medina": "مدینه", "taif": "طائف", "yanbu": "ینبع|رابغ",
    "east": "شرق عربستان|استان شرقی|منطقه شرقی|دمام|ظهران|الخبر|راس تنوره|رأس تنوره|ابقیق|جبیل|قطیف|الاحسا",
    "dubai": "دبی", "abu_dhabi": "ابوظبی|ابوظبى|الظفره", "fujairah": "فجیره", "sharjah": "شارجه|راس الخیمه",
    "qatar": "قطر|قطری|دوحه|العدید|راس لفان", "bahrain": "بحرین|منامه", "kuwait": "کویت", "muscat": "مسقط|دقم|صلاله|صحار",
    "amman": "پایتخت اردن|عقبه|زرقاء|اربد", "baghdad": "بغداد", "erbil": "اربیل", "basra": "بصره", "kirkuk": "کرکوک",
    "mosul": "موصل", "sulaymaniyah": "سلیمانیه", "duhok": "دهوک", "najaf": "نجف", "karbala": "کربلا"}
_GULF_CTRY = {"riyadh": "sa", "najran": "sa", "jizan": "sa", "abha": "sa", "jeddah": "sa", "mecca": "sa", "medina": "sa",
              "taif": "sa", "yanbu": "sa", "east": "sa", "dubai": "ae", "abu_dhabi": "ae", "fujairah": "ae",
              "sharjah": "ae", "qatar": "qa", "bahrain": "bh", "kuwait": "kw", "muscat": "om", "amman": "jo",
              "baghdad": "iq", "erbil": "iq", "basra": "iq", "kirkuk": "iq", "mosul": "iq", "sulaymaniyah": "iq",
              "duhok": "iq", "najaf": "iq", "karbala": "iq"}
ARAB = frozenset(_GULF_CTRY.values())        # the Arab countries of the Middle East these rules cover
_GULF_EN_RX = {k: re.compile(r"\b(?:" + v + r")\b", _I) for k, v in _GULF_EN.items()}
_GULF_FA_RX = {k: re.compile(_w(v)) for k, v in _GULF_FA.items()}
# the country alone ("over Saudi airspace", «مناطقی از عربستان»); not "Saudi-led strikes" on Yemen
_GULF_LAND_EN = {"sa": re.compile(r"\b(saudi(?: arabia)?|the kingdom)\b" + _NOT_SAUDI_ACT, _I),
                 "ae": re.compile(r"\b(uae|emirates|emirati)\b", _I),
                 "jo": re.compile(r"\b(jordan|jordanian)\b", _I), "iq": re.compile(r"\b(iraq|iraqi)\b", _I)}
_GULF_LAND_FA = {"sa": re.compile(_w("عربستان|سعودی")), "ae": re.compile(_w("امارات|اماراتی")),
                 "jo": re.compile(_w("اردن", "ی")), "iq": re.compile(_w("عراق", "ی"))}
# "Gulf of Oman", "Saudi capital" said of Yemen's capital and the like are not places in these countries
_GULF_NOT_EN = re.compile(r"\bgulf of oman\b|\byemen'?s capital\b|\b(?:riyadh|saudi|qatar|uae)[- ](?:backed|led|based"
                          r"|brokered|mediated|hosted)\b", _I)
_GULF_NOT_FA = re.compile(fa_norm("دریای عمان|خلیج عمان|پایتخت یمن"))
# sirens and civil-defence warnings (not "X warned Y", a threat or a statement)
_ALERT_EN = re.compile(r"\b(sirens?|alerts?|early[- ]warnings?|air[- ]raid|take shelter|shelters?|warnings? in"
                       r"|warning (?:sirens?|systems?|messages?))\b", _I)
_ALERT_FA = re.compile(fa_norm("آژیر|هشدار زودهنگام|اعلام هشدار|هشدارهای|هشدار در|هشدار برای|هشدار خطر|پناهگاه"
                               "|وضعیت قرمز|وضعیت اضطراری"))
_HIT_EN = re.compile(r"\b(explosions?|blasts?|intercept\w*|shot down|shoots? down|downed|destroy\w*|struck|hits?"
                     r"|impact\w*|attack\w*|strikes?|missiles?|drones?|rockets?|debris|shrapnel|target\w*|damag\w*)\b", _I)
_HIT_FA = re.compile(fa_norm("انفجار|رهگیری|رهگیر|سرنگون|ساقط|منهدم|اصابت|حمله|حملات|موشک|پهپاد|راکت|ترکش|بقایای|هدف|خسارت|آسیب"))
_CAUGHT_EN = re.compile(r"\b(intercept\w*|shoots? down|shot down|downs?|downed|destroy\w*)\b", _I)


# ------------------------------------------------------------------ named targets (one building, one airport, one plant)
# An attack on a named target is told all day long, in many words: "Aramco skyscraper damaged as Riyadh financial
# district targeted", «خسارت به برج آرامکو در ریاض بر اثر سقوط بقایای موشک», "Houthis claim attack on Riyadh
# financial centre", «یک ساختمان اداری آرامکو در پی حمله حوثی‌ها آسیب دید». Each target has a key and the city it is
# in, so a headline naming only the target («فرودگاه ملک خالد», "King Khalad airport" misspelt) still has its city.
# Reports naming the same target are one story for a day (cluster.TARGET_KEEP). (key, city, English, Persian)
_TARGETS = [
    ("kafd", "riyadh", r"riyadh'?s? financial (?:district|centre|center|hub)|financial (?:district|centre|center) (?:of|in)"
                       r" riyadh|king abdullah financial(?: district| center| centre)?|\bkafd\b",
     "منطقه مالی ریاض|مرکز مالی ریاض|منطقه مالی ملک عبدالله|مرکز مالی ملک عبدالله|منطقه تجاری ریاض"),
    ("aramco_bldg", None, r"aramco(?:'s)? (?:tower|skyscraper|high-?rise|building|office building|offices?|headquarters|hq)"
                          r"|(?:tower|skyscraper|high-?rise|building|offices?|headquarters) (?:of|owned by|belonging to)"
                          r" (?:saudi )?aramco",
     "برج آرامکو|ساختمان آرامکو|ساختمان اداری آرامکو|آسمان خراش آرامکو|ساختمان مجلل برج آرامکو|دفتر آرامکو|دفاتر آرامکو"
     "|مقر آرامکو|ساختمان شرکت آرامکو|برج شرکت آرامکو"),
    ("riyadh_airport", "riyadh", r"king khal[ae]?d (?:international )?(?:airport|air ?port)|king khalid international"
                                 r"|riyadh(?:'s)? (?:international )?airport|airport (?:in|of) riyadh",
     "فرودگاه ملک خالد|فرودگاه بین المللی ملک خالد|فرودگاه ریاض|فرودگاه بین المللی ریاض"),
    ("jeddah_airport", "jeddah", r"king abdul ?aziz (?:international )?airport|jeddah(?:'s)? (?:international )?airport",
     "فرودگاه ملک عبدالعزیز|فرودگاه جده|فرودگاه بین المللی جده"),
    ("abha_airport", "abha", r"abha(?:'s)? (?:international |regional )?airport", "فرودگاه ابها|فرودگاه بین المللی ابها"),
    ("jizan_airport", "jizan", r"(?:jizan|jazan|gizan)(?:'s)? (?:regional )?airport|king abdullah airport",
     "فرودگاه جیزان|فرودگاه جازان|فرودگاه ملک عبدالله"),
    ("dammam_airport", "east", r"king fahd (?:international )?airport|dammam(?:'s)? (?:international )?airport",
     "فرودگاه ملک فهد|فرودگاه دمام|فرودگاه بین المللی دمام"),
    ("najran_airport", "najran", r"najran(?:'s)? (?:domestic |regional )?airport", "فرودگاه نجران"),
    ("abqaiq", "east", r"abqaiq|buqayq", "ابقیق|بقیق"),
    ("ras_tanura", "east", r"ras tanura|ras tanurah", "راس تنوره|راس التنوره"),
    ("khurais", "east", r"khurais", "خریص"),
    ("shaybah", "east", r"shaybah", "شیبه"),
    ("jizan_refinery", "jizan", r"(?:jizan|jazan|gizan) (?:aramco )?refinery|refinery (?:in|at) (?:jizan|jazan)"
                                r"|jizan economic city",
     "پالایشگاه جیزان|پالایشگاه جازان|پالایشگاه آرامکو در جیزان|پالایشگاه آرامکو در جازان"),
    ("jeddah_plant", "jeddah", r"north jeddah bulk plant|jeddah (?:oil |fuel |aramco )?(?:depot|terminal|bulk plant|"
                               r"storage)|aramco (?:depot|terminal|plant|facility|facilities) in jeddah",
     "انبار نفت جده|پایانه نفتی جده|مخازن نفت جده|تاسیسات آرامکو در جده"),
    ("yanbu_plant", "yanbu", r"yanbu (?:refinery|terminal|port|aramco|industrial)|samref|yasref",
     "پالایشگاه ینبع|بندر ینبع|پایانه ینبع"),
    ("rabigh", "yanbu", r"rabigh (?:refinery|plant|terminal)|petro ?rabigh", "پالایشگاه رابغ"),
    ("dubai_airport", "dubai", r"dubai(?:'s)? (?:international )?airport|\bdxb\b|al maktoum (?:international )?airport",
     "فرودگاه دبی|فرودگاه بین المللی دبی|فرودگاه آل مکتوم"),
    ("abu_dhabi_airport", "abu_dhabi", r"abu dhabi(?:'s)? (?:international )?airport|zayed international airport",
     "فرودگاه ابوظبی|فرودگاه بین المللی ابوظبی"),
    ("jebel_ali", "dubai", r"jebel ali", "جبل علی"),
    ("burj_khalifa", "dubai", r"burj khalifa", "برج خلیفه"),
    ("ruwais", "abu_dhabi", r"ruwais", "رویس|الرویس"),
    ("musaffah", "abu_dhabi", r"mussafah|musaffah|adnoc (?:fuel )?(?:depot|tanks?)", "مصفح|المصفح"),
    ("ras_laffan", "qatar", r"ras laffan", "راس لفان"),
    ("bapco", "bahrain", r"bapco|sitra (?:refinery)?", "بابکو|سیتره"),
    ("ahmadi", "kuwait", r"mina al-?ahmadi|al-?ahmadi refinery|mina abdullah", "میناءالاحمدی|مینا الاحمدی|پالایشگاه الاحمدی"),
    ("erbil_airport", "erbil", r"erbil (?:international )?airport", "فرودگاه اربیل"),
    ("baghdad_airport", "baghdad", r"baghdad (?:international )?airport", "فرودگاه بغداد|فرودگاه بین المللی بغداد"),
    ("khor_mor", "sulaymaniyah", r"khor ?mor", "خورمور|کورمور"),
    # long pipelines: no one city (see _ROUTES)
    ("ew_pipeline", None, r"east[- ]west (?:oil |crude |crude oil )?pipeline|petroline|saudi (?:arabia'?s? )?(?:key |main "
                          r"|vital |major |crucial |critical )?(?:oil |crude )?pipeline|pipeline (?:in|across|to) saudi"
                          r"|saudi (?:arabia'?s? )?(?:red sea |yanbu )?(?:oil )?export pipeline",
     "خط لوله (?:(?:نفتی|نفت|اصلی|حیاتی|راهبردی|استراتژیک) ){0,2}(?:شرق|شرقی)(?: به |\\s*-\\s*|\\s*–\\s*| و | )(?:غرب|غربی)"
     "|خط لوله (?:(?:نفتی|نفت|اصلی|حیاتی|راهبردی|استراتژیک) ){0,2}(?:عربستان|سعودی)|پترولاین"
     "|ایستگاه پمپاژ (?:شماره )?(?:7|۷|هفت) (?:خط لوله|عربستان|سعودی)"),   # «خط لوله راهبردی عربستان»
    ("adcop", None, r"habshan[- –](?:to[- ])?fujairah (?:oil |crude )?pipeline|abu dhabi crude (?:oil )?pipeline|\badcop\b"
                    r"|(?:uae|emirati|adnoc) (?:oil |crude |export )*pipeline",
     "خط لوله (?:نفتی |نفت )?حبشان|خط لوله (?:نفتی |نفت )?(?:ابوظبی|امارات) به فجیره|خط لوله (?:نفتی |نفت )?امارات"),
    # oil and gas sites (Saudi Arabia)
    ("riyadh_refinery", "riyadh", r"riyadh (?:oil |aramco )?refinery|refinery (?:in|near) riyadh", "پالایشگاه ریاض"),
    ("jubail_plant", "east", r"satorp|sadara|jubail (?:refinery|industrial(?: city)?|petrochemical\w*|plant)",
     "پالایشگاه جبیل|شهر صنعتی جبیل|پتروشیمی جبیل|ساتورپ|صدارا"),
    ("juaymah", "east", r"ju'?aymah", "جعیمه"),
    ("jafurah", "east", r"jafurah", "جافوره"),
    ("hawiyah", "east", r"hawiyah|haradh", "حویه|حرض"),
    ("shedgum", "east", r"shedgum|ghawar|uthmaniyah", "شدقم|غوار|عثمانیه"),
    ("safaniya", "east", r"safaniy?ah?|manifa|marjan|zuluf|berri (?:field|oil|gas)", "سفانیه|منیفه|مرجان"),
    # the Emirates
    ("fujairah_oil", "fujairah", r"fujairah (?:oil |fuel |petroleum |storage )*(?:terminals?|storage|port|tanks?|depots?"
                                 r"|refinery|hub|facilit\w*|installations?|industry zone)|port of fujairah|\bfoiz\b"
                                 r"|(?:terminals?|storage|tanks?|depots?|facilit\w*|refinery) (?:in|at|of) fujairah",
     "بندر فجیره|پایانه نفتی فجیره|پایانه فجیره|مخازن نفت فجیره|مخازن فجیره|انبار نفت فجیره|تاسیسات نفتی فجیره"
     "|تأسیسات نفتی فجیره|پالایشگاه فجیره|منطقه صنعتی نفت فجیره|تاسیسات (?:نفتی |آرامکو |ادنوک )?در فجیره"),
    ("habshan", "abu_dhabi", r"habshan|bab (?:oil )?field|shah gas|asab (?:oil )?field|bu ?hasa", "حبشان|میدان باب|میدان شاه"),
    ("das_island", "abu_dhabi", r"das island|zirku|zirkuh|mubarraz|jebel dhanna", "جزیره داس|زرکوه|زیرکو|مبرز|جبل الظنه"),
    ("hamriyah", "sharjah", r"hamriyah|sajaa (?:gas)?", "الحمریه|حمریه"),
    # Oman
    ("duqm_refinery", "muscat", r"duqm (?:oil )?(?:refinery|port|terminal|storage)|ras markaz", "پالایشگاه دقم|بندر دقم|راس مرکز"),
    ("sohar_plant", "muscat", r"sohar (?:oil )?(?:refinery|port|terminal|industrial|aluminium|aluminum)",
     "پالایشگاه صحار|بندر صحار"),
    ("mina_fahal", "muscat", r"mina al[- ]?fahal", "مینا الفحل|میناء الفحل"),
    ("salalah_port", "muscat", r"salalah port|port of salalah", "بندر صلاله"),
    ("oman_lng", "muscat", r"oman lng|qalhat", "قلهات|ال ان جی عمان"),
    # Qatar, Kuwait, Iraq
    ("mesaieed", "qatar", r"mesaieed|umm said|dukhan", "مسیعید|ام سعید|دخان"),
    ("zour", "kuwait", r"al-?zour (?:refinery|terminal|plant)|az-?zour", "پالایشگاه الزور|پالایشگاه زور"),
    ("basra_oil", "basra", r"rumaila|west qurna|majnoon|zubair (?:oil )?field|basra (?:oil )?terminal|basrah oil terminal",
     "رمیله|غرب قرنه|مجنون|میدان زبیر|پایانه نفتی بصره"),
]
# Where a long pipeline runs: a city of its route named with it («خط لوله شرق به غرب در منطقه مدینه») is a place
# along the pipeline, not another attack. A pipeline's country stands for its city in gulf_mark.
_ROUTES = {"ew_pipeline": ("sa", frozenset({"medina", "yanbu"})),
           "adcop": ("ae", frozenset({"abu_dhabi", "fujairah"}))}
_TARGET_EN = [(k, c, re.compile(r"\b(?:" + e + r")", _I)) for k, c, e, _ in _TARGETS]
_TARGET_FA = [(k, c, re.compile(_w(f))) for k, c, _, f in _TARGETS]


def gulf_targets(t, fa, cities=()):
    """The named targets a (normalised) headline tells of, as keys. An Aramco building is the tower in Riyadh's
    financial district unless the headline names another city («ساختمان آرامکو در ظهران»: that city's)."""
    out = set()
    for k, c, rx in (_TARGET_FA if fa else _TARGET_EN):
        if rx.search(t):
            out.add(k)
    if "aramco_bldg" in out:
        out.discard("aramco_bldg")
        other = sorted(set(cities) - {"riyadh"})
        out.add("kafd" if not other else "aramco_bldg_" + other[0])
    return frozenset(out)


def _target_cities(targets):
    city = {k: c for k, c, _, _ in _TARGETS}
    return {city[k] for k in targets if city.get(k)}


def _gulf_places(t, fa):
    if fa:
        t = _GULF_NOT_FA.sub(" ", t)
        cities = {k for k, rx in _GULF_FA_RX.items() if rx.search(t)}
        land = {k for k, rx in _GULF_LAND_FA.items() if rx.search(t)}
    else:
        t = _GULF_NOT_EN.sub(" ", t)
        cities = {k for k, rx in _GULF_EN_RX.items() if rx.search(t)}
        land = {k for k, rx in _GULF_LAND_EN.items() if rx.search(t)}
    targets = gulf_targets(t, fa, cities)
    cities |= _target_cities(targets)                         # «فرودگاه ملک خالد»: Riyadh
    for k in targets & _ROUTES.keys():                        # a long pipeline: its country; a city of its route
        land.add(_ROUTES[k][0])                               # named with it is a place along it
        cities -= _ROUTES[k][1] - _target_cities(targets)
    return cities, land | {_GULF_CTRY[c] for c in cities}


# "Iran-backed Houthis" is still this front
_BACKED_EN = re.compile(r"\b(?:iran|iranian|tehran)[- ](?:backed|aligned|allied|supported|sponsored)\b", _I)
_BACKED_FA = re.compile(fa_norm("(مورد حمایت|تحت حمایت|وابسته به|نیابتی|متحد) (ایران|تهران|جمهوری اسلامی)"))


def _main(t, fa):
    r = _sh_rx(fa)
    t = (_BACKED_FA if fa else _BACKED_EN).sub(" ", t)
    return bool(r["main"].search(t) or r["us"].search(t))


def gulf_main(title, lang="en"):
    """True if the headline names the main front (Iran, Israel or America; not "Iran-backed Houthis")."""
    fa = lang == "fa"
    return _main(fa_norm(title or "") if fa else (title or ""), fa)


# Later reports of one attack (item 2): damage, debris, a video of it, a ministry confirming it, a claim of
# responsibility. In an Arab country of the Middle East they join the attack's story for longer
# (cluster.AFTER_SPAN), as long as they tell nothing that is happening now (sirens, explosions heard, interceptions).
_AFTER_EN = re.compile(r"\b(damag\w*|debris|shrapnel|remnants?|fragments?|wreckage|aftermath|footage|videos?|images?"
                       r"|photos?|pictures?|smoke|confirm\w*|ministry|responsibility|attempted attack|failed attack"
                       r"|thwart\w*|foiled|investigat\w*|postpon\w*|witness\w*|eyewitness\w*)\b", _I)
_AFTER_FA = re.compile(fa_norm("خسارت|خسارات|آسیب|بقایای|ترکش|قطعات|لاشه|فیلم|تصاویر|تصویر|ویدئو|ویدیو|دود|پیامد"
                               "|جزئیات|تایید|وزارت|مسئولیت|نافرجام|ناموفق|ناکام|شاهدان|به تعویق"))
_FRESH_EN = re.compile(r"\b(heard|sirens?|alarms?|intercept\w*|shoots? down|shot down|explosions? (?:rock|in|over)"
                       r"|now|ongoing|under way|underway)\b", _I)
_FRESH_FA = re.compile(fa_norm("شنیده شد|شنیده می|آژیر|رهگیری|رهگیر|سرنگون|هم اکنون|هم‌اکنون|لحظاتی پیش|در حال"))
# what makes a report of a failed attempt on a place an attack all the same («تلاش … برای آسیب به … ناموفق ماند»)
_ATTEMPT_EN = re.compile(r"\b(attempted attack|failed attack|attempt\w* to (?:hit|strike|damage|attack))\b", _I)
_ATTEMPT_FA = re.compile(fa_norm("نافرجام|ناموفق ماند|ناکام ماند|تلاش (?:[^ ]+ ){0,3}برای (?:آسیب|حمله|هدف)"))

# The Houthis' account of their operations (item 5): their military spokesman's statement, told by each outlet in
# its own slice ("Houthis say they attacked Aramco facilities in Abqaiq", "Houthis claim attack on King Khalid
# airport", «جزئیات ۴ عملیات ارتش یمن در عمق خاک عربستان», «حمله یمن به فرودگاه ملک خالد، تأسیسات آرامکو و اهدافی
# در ریاض»). One day's statements are one story (cluster.CLAIM_SPAN); a count of operations that differs makes
# another statement. A report that also tells what was seen (damage, witnesses, the Saudi side intercepting) is the
# attack's, not the statement's.
_HOUTHI_EN = re.compile(r"\b(houthis?|ansar ?allah|saree|sarea|yemen'?s? (?:army|armed forces|military)"
                        r"|yemeni (?:army|armed forces|military|forces)|yemen)\b", _I)
_HOUTHI_FA = re.compile(_w("حوثی|انصارالله|یمن", "ی|ها|های") + "|" + fa_norm("یحیی سریع|ارتش یمن|نیروهای مسلح یمن"))
_CLAIM_EN = re.compile(r"\b(?:houthis?|ansar ?allah|saree|sarea|yemen'?s? (?:army|armed forces|military)|yemeni (?:army|armed"
                       r" forces|military|forces)|yemen)\b[^.;:]{0,40}?\b(claim\w*|says?|said|announc\w*|statement)\b"
                       r"|\b(spokes\w*|operations?|claim(?:s|ed)? responsibility)\b", _I)
_CLAIM_FA = re.compile(fa_norm("مدعی|ادعا|اعلام کرد|اعلام کردند|بیانیه|سخنگو|جزئیات|عملیات|مسئولیت"))
_SEEN_EN = re.compile(r"\b(damag\w*|witness\w*|eyewitness\w*|intercept\w*|shot down|shoots? down|debris|ministry"
                      r"|coalition|civil defen[cs]e|saudi (?:says|said|defen[cs]es?|forces)|fire|ablaze|smoke"
                      r"|reports? of|reported|sources|media|explosions?|blasts?|heard|died|killed|dead|wounds?|injur\w*"
                      r"|last (?:month|week|year)|ago)\b", _I)
_SEEN_FA = re.compile(fa_norm("خسارت|آسیب|شاهدان|رهگیری|رهگیر|سرنگون|بقایای|وزارت|ائتلاف|دفاع مدنی|آتش|دود"
                              "|گزارش|منابع|رسانه|انفجار|شنیده|خبر حمله|اخبار|کشته|زخمی|مجروح|جان باخت|جان سپرد"
                              "|ماه گذشته|هفته گذشته|سال گذشته|پیش"))
# fighting inside Yemen (Saudi-backed forces, «مزدوران سعودی»): not an attack on Saudi soil
_INSIDE_EN = re.compile(r"\bmercenar\w*|\b(?:saudi[- ]backed|pro-saudi)\b", _I)
_INSIDE_FA = re.compile(fa_norm("مزدور|تحت فرمان افسران سعودی|نیروهای وابسته"))
_GENERIC_EN = {"airport": r"airports?", "oil": r"aramco|refiner(?:y|ies)|oil|facilit\w*|plants?|terminals?",
               "troops": r"troops|forces|military (?:sites?|targets?|positions?)|bases?", "city": r"targets? in"}
_GENERIC_FA = {"airport": "فرودگاه", "oil": "آرامکو|پالایشگاه|تاسیسات|نفتی", "troops": "نیروهای|مواضع|پایگاه",
               "city": "اهدافی در|اهداف حساس|اهداف"}
# the Houthis' own forces named as the speaker or the actor: never a target of the "troops" kind
_OWN_FORCES_EN = re.compile(r"\b(?:yemen'?s|yemeni|houthis?'?|ansar ?allah'?s?) (?:armed |military )?forces\b"
                            r"|\b(?:armed|military) forces of (?:yemen|the houthis)\b", _I)
_OWN_FORCES_FA = re.compile(fa_norm("نیروهای (?:مسلح |نظامی )?(?:یمن|یمنی|انصارالله|حوثی|حوثی ها|صنعا)"))
_GENERIC_EN_RX = {k: re.compile(r"\b(?:" + v + r")\b", _I) for k, v in _GENERIC_EN.items()}
_GENERIC_FA_RX = {k: re.compile(fa_norm(v)) for k, v in _GENERIC_FA.items()}
_NUM_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
              "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
_COUNT_EN = re.compile(r"\b(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten) (?:\w+ ){0,3}?operations\b", _I)
_COUNT_FA = re.compile(fa_norm(r"(\d{1,2}|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده) عملیات"))
_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _op_count(t, fa):
    m = (_COUNT_FA if fa else _COUNT_EN).search(t)
    if not m:
        return None
    x = m.group(1).lower().translate(_LATIN)
    return int(x) if x.isdigit() else _NUM_WORDS.get(x)


def gulf_claim(t, fa, targets, cities):
    """(count of operations or None, several targets) if the (normalised) headline is the Houthis' own account of
    their operations on an Arab country of the Middle East, else None."""
    if not (_HOUTHI_FA if fa else _HOUTHI_EN).search(t) or (_SEEN_FA if fa else _SEEN_EN).search(t):
        return None
    r = _sh_rx(fa)
    if r["actor"].search(t) or (_INSIDE_FA if fa else _INSIDE_EN).search(t):
        return None                      # Saudi Arabia striking («حمله عربستان به الشریه»), fighting inside Yemen
    if not cities and not targets and (not r["place"].search(r["proxy"].sub(" ", t)) or r["yemen"].search(t)) \
            and not (fa and re.search(fa_norm("عمق خاک عربستان|خاک عربستان|علیه اهداف سعودی|اهداف سعودی|در عربستان|علیه دشمن سعودی|دشمن سعودی"), t)) \
            and not (not fa and re.search(r"\b(?:deep )?(?:in|inside|into|on|against) (?:saudi(?: arabia)?|the kingdom)\b"
                                          r"(?![- ](?:led|backed))|\bsaudi (?:targets|territory|soil)\b|\bthe saudi enemy\b", t, _I)):
        return None                      # no place in the country named: a statement about the fighting in Yemen
    n = _op_count(t, fa)
    own = (_OWN_FORCES_FA if fa else _OWN_FORCES_EN).sub(" ", t)   # «نیروهای مسلح یمن»: who struck, not a target
    kinds = {k for k, rx in (_GENERIC_FA_RX if fa else _GENERIC_EN_RX).items() if rx.search(own)}
    # several targets: two named ones, a named one and another kind («فرودگاه ملک خالد، تأسیسات آرامکو و اهدافی در
    # ریاض»), or two kinds ("Aramco sites, Riyadh airport and troops")
    named_kinds = {"airport" if "airport" in k else "oil" for k in targets}
    multi = len(targets) >= 2 or len(kinds | named_kinds) >= 2 or len(set(cities) - _target_cities(targets)) >= 2
    if not (_CLAIM_FA if fa else _CLAIM_EN).search(t) and not multi:
        return None                      # "Houthi missile hits Riyadh": the attack, not a statement
    if n is not None and n >= 2:
        multi = True
    return n, multi


_PAST_EN = re.compile(r"\b(last (?:month|week|year)|(?:weeks|months|years) ago|earlier this (?:month|year)|anniversary)\b", _I)
_PAST_FA = re.compile(fa_norm("ماه گذشته|هفته گذشته|سال گذشته|ماه پیش|هفته پیش|سال پیش|هفته های گذشته|ماه های گذشته|سالگرد"))


def gulf_mark(title, lang="en"):
    """(kind, places, countries, targets, later, count, several) of a report of missiles or drones on an Arab
    country of the Middle East, of the sirens and warnings there, or of the Houthis' statement of their operations
    on it; None for anything else, and for a report naming the main front (see above).
    kind: "attack", "alert" (sirens) or "claim" (the Houthis' statement); targets: the named targets (gulf_targets);
    later: a later report of the attack (damage, debris, a video, a confirmation; nothing happening now); count: the
    number of operations a statement gives; several: a statement naming more than one target."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    r = _sh_rx(fa)
    if not t or _main(t, fa) or (_PAST_FA if fa else _PAST_EN).search(t):
        return None                      # the main front; an attack weeks ago ("died of wounds … last month")
    cities, ctry = _gulf_places(r["proxy"].sub(" ", t), fa)
    targets = gulf_targets(r["proxy"].sub(" ", t), fa, cities)
    if not ctry and fa and (_HOUTHI_FA.search(t) and _COUNT_FA.search(t)) and re.search(fa_norm("عربستان|سعودی"), t):
        ctry = {"sa"}
    if not ctry:
        return None
    later = bool((_AFTER_FA if fa else _AFTER_EN).search(t)) and not (_FRESH_FA if fa else _FRESH_EN).search(t)
    hit = (_HIT_FA if fa else _HIT_EN).search(t)
    if (_ALERT_FA if fa else _ALERT_EN).search(t) and not hit:
        return "alert", frozenset(cities), frozenset(ctry), frozenset(), False, None, False
    a, w = r["attack"].search(t), r["talk"].search(t)
    if not a and (_ATTEMPT_FA if fa else _ATTEMPT_EN).search(t) and (cities or targets):
        a = hit = True                   # «تلاش حوثی‌ها برای آسیب به آرامکو در ریاض ناموفق ماند»
    claim = gulf_claim(t, fa, targets, cities) if (a or (fa and _COUNT_FA.search(t)) or _op_count(t, fa)) else None
    if claim and not r["review"].search(t) and not r["future"].search(t) and not (w and (not a or w.start() < a.start())
                                                                                  and not (_CLAIM_FA if fa else _CLAIM_EN).search(w.group(0))):
        if not r["tally"].search(t) or claim[0]:
            return "claim", frozenset(cities), frozenset(ctry), targets, False, claim[0], claim[1]
    if not a or not hit or r["review"].search(t) or r["future"].search(t) or (w and w.start() < a.start()):
        return None                      # threats, reactions, talks, markets, analysis
    if r["toll"].search(t) or r["tally"].search(t):
        return None                      # casualty figures and counts (mostly of Saudi strikes on Yemen)
    if not cities and not targets and not (r["intercept"] if fa else _CAUGHT_EN).search(t):
        return None                      # the country alone: only an interception over it ("over Saudi airspace");
                                         # a long pipeline named stands for a place
    return "attack", frozenset(cities), frozenset(ctry), targets, later, None, False
