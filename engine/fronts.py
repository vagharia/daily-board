"""Rules for particular fronts.

The Saudi-Houthi war produces dozens of reports a day. Only direct attacks and what they hit are red there:
Houthi missiles and drones fired at Saudi Arabia (cities, airports, bases, oil and energy sites), attacks on
shipping in the Red Sea and Bab el-Mandeb, Saudi or coalition strikes on Yemen, interceptions, impacts,
explosions and falling debris. Casualty counts, condemnations, accusations, statements, talks, market stories and
fighting inside Yemen (Houthis against Yemeni government forces in Aden, Taiz, Marib…) stay orange at most.
A report on this front that names Israel, Iran or the US is left to the general rules."""
import re

from .util import fa_norm

_I = re.I

# ------------------------------------------------------------------ English
_EN_FRONT = re.compile(r"\b(houthis?|ansar ?allah|yemen\w*|sanaa|sana'a|saada|sa'ada|hodeidah|hudaydah|aden|lahij|lahj"
                       r"|taiz|ta'iz|marib|ma'rib|shabwa|hadramout|hadramawt|mukalla|abyan"
                       r"|bab[- ]el[- ]mandeb|bab al[- ]mandab|saree|sarea)\b", _I)
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


def saudi_houthi(title, lang="en", flags=()):
    """None when the report is not on the Saudi-Houthi front (or names Israel, Iran or the US), "direct" for a
    direct attack or its immediate result, "secondary" for everything else on that front."""
    if lang == "fa":
        t = fa_norm(title or "")
        front, other, proxy, saudi, attack, sea, toll, talk, review, future = (
            _FA_FRONT, _FA_OTHER, _FA_PROXY, _FA_SAUDI, _FA_ATTACK, _FA_SEA, _FA_TOLL, _FA_TALK, _FA_REVIEW, _FA_FUTURE)
    else:
        t = title or ""
        front, other, proxy, saudi, attack, sea, toll, talk, review, future = (
            _EN_FRONT, _EN_OTHER, _EN_PROXY, _EN_SAUDI, _EN_ATTACK, _EN_SEA, _EN_TOLL, _EN_TALK, _EN_REVIEW, _EN_FUTURE)
    if not front.search(t) or other.search(t):
        return None
    if "evac" in flags:
        return "direct"                  # staff told to leave an oil city is itself an event
    if toll.search(t) or review.search(t) or future.search(t):
        return "secondary"
    a, w = attack.search(t), talk.search(t)
    if w and (not a or w.start() < a.start()):
        return "secondary"               # framed as a reaction, a warning or talks ("GCC condemns Houthi attack")
    if a and (saudi.search(proxy.sub(" ", t)) or sea.search(t)):
        return "direct"
    return "secondary"                   # fighting inside Yemen, claims about past numbers, everything else
