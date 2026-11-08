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
                                     r"(عربستان|سعودی|آل سعود)|(جنگنده های|هواپیماهای|ائتلاف|رژیم|متجاوزان|نیروهای) (سعودی|آل سعود)"
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


def side_front(title, lang="en", flags=(), src="", text=""):
    """(front, grade) of a report on a side front ("saudi_houthi" or "lebanon"; "major", "secondary" or "minor"), or None.
    src (the outlet) and text (the summary) tell who a ship attack in the Red Sea is told by."""
    g = saudi_houthi(title, lang, flags, src, text)
    if g:
        return "saudi_houthi", g
    g = israel_lebanon(title, lang, flags)
    return ("lebanon", g) if g else None


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
    "kuwait": r"kuwait", "muscat": r"muscat|duqm|salalah|sohar"}
_GULF_FA = {
    "riyadh": "ریاض|پایتخت عربستان|پایتخت سعودی", "najran": "نجران", "jizan": "جیزان|جازان", "abha": "ابها|خمیس مشیط",
    "jeddah": "جده", "mecca": "مکه", "medina": "مدینه", "taif": "طائف", "yanbu": "ینبع|رابغ",
    "east": "شرق عربستان|استان شرقی|منطقه شرقی|دمام|ظهران|الخبر|راس تنوره|رأس تنوره|ابقیق|جبیل|قطیف|الاحسا",
    "dubai": "دبی", "abu_dhabi": "ابوظبی|ابوظبى|الظفره", "fujairah": "فجیره", "sharjah": "شارجه|راس الخیمه",
    "qatar": "قطر|قطری|دوحه|العدید|راس لفان", "bahrain": "بحرین|منامه", "kuwait": "کویت", "muscat": "مسقط|دقم|صلاله|صحار"}
_GULF_CTRY = {"riyadh": "sa", "najran": "sa", "jizan": "sa", "abha": "sa", "jeddah": "sa", "mecca": "sa", "medina": "sa",
              "taif": "sa", "yanbu": "sa", "east": "sa", "dubai": "ae", "abu_dhabi": "ae", "fujairah": "ae",
              "sharjah": "ae", "qatar": "qa", "bahrain": "bh", "kuwait": "kw", "muscat": "om"}
_GULF_EN_RX = {k: re.compile(r"\b(?:" + v + r")\b", _I) for k, v in _GULF_EN.items()}
_GULF_FA_RX = {k: re.compile(_w(v)) for k, v in _GULF_FA.items()}
# the country alone ("over Saudi airspace", «مناطقی از عربستان»); not "Saudi-led strikes" on Yemen
_GULF_LAND_EN = {"sa": re.compile(r"\b(saudi(?: arabia)?|the kingdom)\b" + _NOT_SAUDI_ACT, _I),
                 "ae": re.compile(r"\b(uae|emirates|emirati)\b", _I)}
_GULF_LAND_FA = {"sa": re.compile(_w("عربستان|سعودی")), "ae": re.compile(_w("امارات|اماراتی"))}
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


def _gulf_places(t, fa):
    if fa:
        t = _GULF_NOT_FA.sub(" ", t)
        cities = {k for k, rx in _GULF_FA_RX.items() if rx.search(t)}
        land = {k for k, rx in _GULF_LAND_FA.items() if rx.search(t)}
    else:
        t = _GULF_NOT_EN.sub(" ", t)
        cities = {k for k, rx in _GULF_EN_RX.items() if rx.search(t)}
        land = {k for k, rx in _GULF_LAND_EN.items() if rx.search(t)}
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


def gulf_mark(title, lang="en"):
    """("attack" or "alert", places, countries) of a report of missiles or drones on a Gulf Arab country, or of the
    sirens and warnings there; None for anything else, and for a report naming the main front (see above)."""
    fa = lang == "fa"
    t = fa_norm(title or "") if fa else (title or "")
    r = _sh_rx(fa)
    if not t or _main(t, fa):
        return None
    cities, ctry = _gulf_places(r["proxy"].sub(" ", t), fa)
    if not ctry:
        return None
    hit = (_HIT_FA if fa else _HIT_EN).search(t)
    if (_ALERT_FA if fa else _ALERT_EN).search(t) and not hit:
        return "alert", frozenset(cities), frozenset(ctry)
    a, w = r["attack"].search(t), r["talk"].search(t)
    if not a or not hit or r["review"].search(t) or r["future"].search(t) or (w and w.start() < a.start()):
        return None                      # threats, reactions, talks, markets, analysis
    if r["toll"].search(t) or r["tally"].search(t):
        return None                      # casualty figures and counts (mostly of Saudi strikes on Yemen)
    if not cities and not (r["intercept"] if fa else _CAUGHT_EN).search(t):
        return None                      # the country alone: only an interception over it ("over Saudi airspace")
    return "attack", frozenset(cities), frozenset(ctry)
