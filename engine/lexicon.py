"""Vocabulary: people, places, countries and topics (English + Persian aliases).

People are tracked by name AND by role, so the filters keep working when an office changes
hands. Places carry coordinates for the hotspot map.
"""
import re

from .util import fa_norm

FA_LETTER = "؀-ۿ"


def en_rx(terms):
    """Compile English terms. A trailing '$' means a whole-word match, otherwise suffixes
    are allowed (iran -> iranian, israel -> israeli)."""
    parts = []
    for t in terms:
        if t.startswith("re:"):          # raw regex (may carry scoped flags)
            parts.append(t[3:])
            continue
        whole = t.endswith("$")
        t = t.rstrip("$")
        p = r"\b" + re.escape(t).replace(r"\ ", r"[\s-]+")
        if whole:
            p += r"\b"
        parts.append(p)
    return re.compile("(?:" + "|".join(parts) + ")", re.I)


def fa_rx(terms):
    """Compile Persian terms on normalised text (ZWNJ -> space, Arabic letters unified)."""
    parts = []
    for t in terms:
        whole = t.endswith("$")
        t = fa_norm(t.rstrip("$"))
        p = rf"(?<![{FA_LETTER}])" + re.escape(t).replace(r"\ ", r"\s+")
        if whole:
            p += rf"(?![{FA_LETTER}])"
        parts.append(p)
    return re.compile("(?:" + "|".join(parts) + ")")


# ------------------------------------------------------------------ people
# id: (fa label, en label, english patterns, persian terms)
PEOPLE = {
    "trump": ("ترامپ", "Trump", ["trump"], ["ترامپ"]),
    "vance": ("ونس", "Vance", ["vance$", "jd vance"], ["ونس$", "جی دی ونس"]),
    "rubio": ("روبیو", "Rubio", ["rubio"], ["روبیو"]),
    "bessent": ("بسنت", "Bessent", ["bessent"], ["بسنت"]),
    "hegseth": ("هگست", "Hegseth", ["hegseth"], ["هگست", "هگزث", "هگزت", "هگسث"]),
    "witkoff": ("ویتکاف", "Witkoff", ["witkoff"], ["ویتکاف", "ویتکوف"]),
    "us_mil": ("فرماندهان نظامی آمریکا", "US military chiefs",
               ["centcom commander", "joint chiefs", "gen. caine", "general caine", "adm. cooper", "admiral cooper"],
               ["فرمانده سنتکام", "رئیس ستاد مشترک ارتش آمریکا", "رئیس ستاد مشترک نیروهای مسلح آمریکا",
                "ستاد مشترک ارتش آمریکا"]),
    "il_pm": ("نخست‌وزیر اسرائیل", "Israeli PM",
              ["netanyahu", "israeli prime minister", "israel's prime minister", "israeli pm$"],
              ["نتانیاهو", "نخست وزیر اسرائیل", "نخست وزیر رژیم صهیونیستی"]),
    "il_def": ("وزیر جنگ اسرائیل", "Israeli defense minister",
               ["israel katz", "israeli defense minister", "israeli defence minister", "israel's defense minister"],
               ["کاتز", "وزیر جنگ اسرائیل", "وزیر دفاع اسرائیل", "وزیر جنگ رژیم صهیونیستی"]),
    "idf_chief": ("رئیس ستاد ارتش اسرائیل", "IDF chief", ["eyal zamir", "zamir$", "idf chief", "idf chief of staff"],
                  ["زمیر$", "رئیس ستاد ارتش اسرائیل"]),
    "ir_leader": ("رهبر ایران", "Iran's Supreme Leader", ["khamenei", "supreme leader"],
                  ["خامنه ای", "رهبر انقلاب", "رهبر معظم", "رهبری$", "رهبر جمهوری اسلامی"]),
    "ir_pres": ("رئیس‌جمهور ایران", "Iran's President", ["pezeshkian", "iranian president", "iran's president"],
                ["پزشکیان", "رئیس جمهور ایران"]),
    "ir_fm": ("وزیر خارجه ایران", "Iran's Foreign Minister",
              ["araghchi", "araqchi", "iranian foreign minister", "iran's foreign minister"],
              ["عراقچی", "وزیر امور خارجه ایران", "وزیر خارجه ایران"]),
    "ir_snsc": ("شورای عالی امنیت ملی", "Iran's Security Council",
                ["supreme national security council", "larijani", "vahidi", "snsc$"],
                ["شورای عالی امنیت ملی", "لاریجانی", "وحیدی"]),
    "irgc_cmd": ("فرماندهان سپاه", "IRGC commanders",
                 ["irgc commander", "irgc chief", "revolutionary guards commander", "revolutionary guard commander",
                  "quds force commander", "pakpour"],
                 ["فرمانده کل سپاه", "فرمانده سپاه", "فرمانده نیروی قدس", "پاکپور"]),
    "ir_army": ("ستاد کل نیروهای مسلح", "Iran's armed forces chief",
                ["armed forces chief of staff", "chief of staff of the armed forces"],
                ["رئیس ستاد کل نیروهای مسلح", "ستاد کل نیروهای مسلح"]),
    "ghalibaf": ("قالیباف", "Ghalibaf", ["ghalibaf", "qalibaf"], ["قالیباف"]),
    "ir_spox": ("سخنگوی وزارت خارجه ایران", "Iran's FM spokesperson", ["baghaei", "baghaie"], ["بقائی", "بقایی"]),
    "grossi": ("گروسی", "Grossi (IAEA)", ["grossi"], ["گروسی"]),
    "guterres": ("گوترش", "Guterres", ["guterres"], ["گوترش", "گوترز"]),
    "mbs": ("بن‌سلمان", "Mohammed bin Salman", ["mohammed bin salman", "crown prince mohammed", "mbs$"],
            ["بن سلمان", "ولیعهد عربستان"]),
    "sa_fm": ("وزیر خارجه عربستان", "Saudi FM", ["faisal bin farhan", "saudi foreign minister"],
              ["فیصل بن فرحان", "وزیر خارجه عربستان"]),
    "qa": ("مقامات قطر", "Qatari leaders",
           ["qatari emir", "emir of qatar", "qatari prime minister", "qatar's prime minister", "sheikh tamim",
            "mohammed bin abdulrahman", "qatari foreign"],
           ["امیر قطر", "نخست وزیر قطر", "وزیر خارجه قطر"]),
    "om": ("وزیر خارجه عمان", "Omani FM", ["busaidi", "omani foreign minister", "oman's foreign minister"],
           ["البوسعیدی", "بوسعیدی", "وزیر خارجه عمان"]),
    "uae": ("مقامات امارات", "UAE leaders",
            ["mohamed bin zayed", "mbz$", "abdullah bin zayed", "gargash", "uae president", "emirati foreign minister"],
            ["بن زاید", "قرقاش", "رئیس امارات"]),
    "houthi_l": ("رهبر حوثی‌ها", "Houthi leader", ["abdul-malik al-houthi", "abdulmalik al-houthi"],
                 ["عبدالملک الحوثی", "عبدالملک حوثی"]),
    "hzb_l": ("دبیرکل حزب‌الله", "Hezbollah chief", ["naim qassem", "hezbollah chief", "hezbollah leader"],
              ["نعیم قاسم", "دبیرکل حزب الله"]),
    "putin": ("پوتین", "Putin", ["putin"], ["پوتین"]),
    "xi": ("شی جین‌پینگ", "Xi Jinping", ["xi jinping", "president xi"], ["شی جین پینگ"]),
    "e3": ("رهبران اروپایی", "European leaders",
           ["macron", "starmer", "merz$", "kallas", "e3 ministers", "e3 leaders", "e3 countries"],
           ["مکرون", "استارمر", "مرتس", "کالاس"]),
}

# ------------------------------------------------------------------ places (lat, lon)
PLACES = {
    "hormuz": ("تنگه هرمز", "Strait of Hormuz", 26.57, 56.25, ["hormuz"], ["هرمز"]),
    "persian_gulf": ("خلیج فارس", "Persian Gulf", 27.2, 51.2, ["persian gulf", "arabian gulf"], ["خلیج فارس"]),
    "gulf_oman": ("دریای عمان", "Gulf of Oman", 24.6, 58.6, ["gulf of oman"], ["دریای عمان"]),
    "tehran": ("تهران", "Tehran", 35.69, 51.39, ["tehran"], ["تهران"]),
    "isfahan": ("اصفهان", "Isfahan", 32.65, 51.67, ["isfahan", "esfahan"], ["اصفهان"]),
    "natanz": ("نطنز", "Natanz", 33.72, 51.73, ["natanz"], ["نطنز"]),
    "fordow": ("فردو", "Fordow", 34.88, 50.99, ["fordow", "fordo$"], ["فردو$"]),
    "bushehr": ("بوشهر", "Bushehr", 28.97, 50.84, ["bushehr"], ["بوشهر"]),
    "bandar_abbas": ("بندرعباس", "Bandar Abbas", 27.18, 56.27, ["bandar abbas"], ["بندرعباس", "بندر عباس"]),
    "kharg": ("خارک", "Kharg Island", 29.24, 50.31, ["kharg"], ["خارک"]),
    "tabriz": ("تبریز", "Tabriz", 38.08, 46.29, ["tabriz"], ["تبریز"]),
    "shiraz": ("شیراز", "Shiraz", 29.59, 52.58, ["shiraz"], ["شیراز"]),
    "chabahar": ("چابهار", "Chabahar", 25.29, 60.64, ["chabahar"], ["چابهار"]),
    "tel_aviv": ("تل‌آویو", "Tel Aviv", 32.08, 34.78, ["tel aviv"], ["تل آویو", "تلآویو"]),
    "jerusalem": ("بیت‌المقدس", "Jerusalem", 31.78, 35.22, ["jerusalem"], ["بیت المقدس", "اورشلیم"]),
    "haifa": ("حیفا", "Haifa", 32.79, 34.99, ["haifa"], ["حیفا"]),
    "dimona": ("دیمونا", "Dimona", 31.07, 35.03, ["dimona"], ["دیمونا"]),
    "eilat": ("ایلات", "Eilat", 29.56, 34.95, ["eilat"], ["ایلات$"]),
    "gaza": ("غزه", "Gaza", 31.45, 34.40, ["gaza"], ["غزه"]),
    "lebanon": ("لبنان", "Lebanon", 33.89, 35.50, ["lebanon", "beirut"], ["لبنان", "بیروت"]),
    "syria": ("سوریه", "Syria", 33.51, 36.29, ["syria", "damascus"], ["سوریه", "دمشق"]),
    "baghdad": ("بغداد", "Baghdad", 33.31, 44.36, ["baghdad"], ["بغداد"]),
    "erbil": ("اربیل", "Erbil", 36.19, 44.01, ["erbil", "kurdistan region"], ["اربیل", "اقلیم کردستان"]),
    "ain_asad": ("عین‌الاسد", "Ain al-Asad", 33.80, 42.44, ["ain al-asad", "ain al asad"], ["عین الاسد"]),
    "sanaa": ("صنعا", "Sanaa", 15.37, 44.19, ["sanaa", "houthi"], ["صنعا", "انصارالله", "حوثی"]),
    "hodeidah": ("حدیده", "Hodeidah", 14.80, 42.95, ["hodeidah"], ["حدیده", "الحدیده"]),
    "red_sea": ("دریای سرخ", "Red Sea", 19.5, 39.0, ["red sea"], ["دریای سرخ"]),
    "bab": ("باب‌المندب", "Bab el-Mandeb", 12.6, 43.4, ["bab el-mandeb", "bab al-mandab", "bab el mandeb"],
            ["باب المندب"]),
    "riyadh": ("ریاض", "Riyadh", 24.71, 46.68, ["riyadh"], ["ریاض$"]),
    "east_sa": ("ابقیق و راس‌تنوره", "Abqaiq / Ras Tanura", 26.10, 49.90, ["abqaiq", "ras tanura", "aramco"],
                ["ابقیق", "آرامکو", "رأس تنوره"]),
    "doha": ("قطر", "Qatar", 25.29, 51.53, ["doha", "qatar", "al udeid"], ["دوحه", "قطر$", "قطری", "العدید"]),
    "bahrain": ("بحرین", "Bahrain", 26.23, 50.59, ["bahrain", "manama", "fifth fleet"], ["بحرین", "منامه", "ناوگان پنجم"]),
    "uae": ("امارات", "UAE", 24.45, 54.38, ["abu dhabi", "uae$", "emirates", "al dhafra", "dubai"],
            ["ابوظبی", "امارات", "دبی$", "الظفره"]),
    "fujairah": ("فجیره", "Fujairah", 25.12, 56.33, ["fujairah"], ["فجیره"]),
    "oman": ("عمان", "Oman", 23.59, 58.41, ["muscat", "oman$", "omani"], ["مسقط", "عمان$", "عمانی"]),
    "kuwait": ("کویت", "Kuwait", 29.37, 47.98, ["kuwait"], ["کویت"]),
    "jordan": ("اردن", "Jordan", 31.95, 35.93, ["jordan$", "amman$"], ["اردن"]),
}

# ------------------------------------------------------------------ countries / actors
COUNTRIES = {
    "us": ("آمریکا", "US", ["u.s.", "united states", "american", "washington", "pentagon", "white house",
                            "trump", "rubio", "vance$", "bessent", "hegseth", "witkoff", "centcom",
                            r"re:(?-i:\bUS\b|\bUSA\b)"],
           ["آمریکا", "امریکا", "ایالات متحده", "واشنگتن", "پنتاگون", "کاخ سفید", "ترامپ", "سنتکام"]),
    "il": ("اسرائیل", "Israel", ["israel", "idf$", "netanyahu", "tel aviv", "mossad"],
           ["اسرائیل", "اسراییل", "رژیم صهیونیستی", "صهیونیست", "نتانیاهو", "تل آویو"]),
    "ir": ("ایران", "Iran", ["iran", "tehran", "irgc", "khamenei", "pezeshkian", "araghchi", "revolutionary guard"],
           ["ایران", "تهران", "سپاه$", "عراقچی", "پزشکیان"]),
    "gulf": ("خلیج فارس", "Persian Gulf states",
             ["saudi", "uae$", "emirat", "qatar", "oman$", "omani", "bahrain", "kuwait", "gcc$", "gulf states",
              "gulf countries", "gulf arab"],
             ["عربستان", "سعودی", "امارات", "قطر$", "قطری", "عمان", "بحرین", "کویت", "شورای همکاری خلیج فارس"]),
    "iraq": ("عراق", "Iraq", ["iraq", "baghdad", "erbil"], ["عراق$", "عراقی", "بغداد", "اربیل"]),
    "yemen": ("یمن", "Yemen", ["yemen", "houthi", "sanaa", "hodeidah"], ["یمن", "حوثی", "انصارالله", "صنعا"]),
    "lebanon": ("لبنان", "Lebanon", ["lebanon", "hezbollah", "beirut"], ["لبنان", "حزب الله", "بیروت"]),
    "syria": ("سوریه", "Syria", ["syria", "damascus"], ["سوریه", "دمشق"]),
    "europe": ("اروپا", "Europe", ["europe", "e3$", "france", "french", "germany", "german", "britain", "british",
                                   "uk$", "macron", "starmer", "merz$"],
               ["اروپا", "تروئیکا", "فرانسه", "آلمان", "انگلیس", "بریتانیا"]),
    "russia": ("روسیه", "Russia", ["russia", "kremlin", "putin", "moscow"], ["روسیه", "کرملین", "پوتین", "مسکو"]),
    "china": ("چین", "China", ["china", "chinese", "beijing", "xi jinping"], ["چین$", "چینی", "پکن"]),
    "un": ("سازمان ملل و آژانس", "UN & IAEA", ["united nations", "security council", "guterres", "iaea", "grossi"],
           ["سازمان ملل", "شورای امنیت", "آژانس", "گروسی"]),
}

# ------------------------------------------------------------------ topics
TOPICS = {
    "military": ("نظامی", "Military",
                 ["military", "strike$", "strikes$", "airstrike", "missile", "drone", "troops", "army", "air force",
                  "irgc", "idf$", "centcom", "pentagon", "bomber", "fighter jet", "warplane", "air defen",
                  "intercept", "attack", "war$", "artillery", "rocket"],
                 ["نظامی", "حمله", "حملات", "موشک", "پهپاد", "ارتش", "سپاه$", "پدافند", "جنگنده", "رزمایش",
                  "بمب افکن", "جنگ$", "جنگی", "نیروهای مسلح", "سرباز", "تسلیحات", "مهمات", "بمباران", "انفجار",
                  "نیروی هوایی", "یورش", "هواپیمای نظارتی"]),
    "nuclear": ("هسته‌ای", "Nuclear",
                ["nuclear", "enrich", "uranium", "iaea", "natanz", "fordow", "centrifuge", "npt$", "snapback",
                 "grossi", "atomic"],
                ["هسته ای", "غنی سازی", "اورانیوم", "آژانس", "نطنز", "فردو$", "سانتریفیوژ", "ان پی تی"]),
    "maritime": ("هرمز و دریا", "Hormuz & sea",
                 ["hormuz", "tanker", "shipping", "vessel", "ship$", "ships$", "navy$", "naval", "maritime", "strait",
                  "red sea", "bab el", "port$", "ukmto", "freighter", "seafarer", "warship", "aircraft carrier"],
                 ["هرمز", "نفتکش", "نفت کش", "کشتی", "دریایی", "ناو$", "ناوشکن", "ناوچه", "ناوگان پنجم", "ناوگان دریایی",
                  "تنگه", "دریای سرخ", "بندر", "کشتیرانی"]),
    "air": ("هوایی", "Air & airspace",
            ["airspace", "flight", "airline", "airport", "aviation", "air traffic", "notam"],
            ["حریم هوایی", "پرواز", "فرودگاه", "هواپیمایی"]),
    "diplomacy": ("دیپلماسی", "Diplomacy",
                  ["talks$", "negotiat", "diplomat", "foreign minister", "ambassador", "envoy", "summit", "mediat",
                   "meeting", "met with", "security council", "proposal", "agreement", "dialogue"],
                  ["مذاکره", "مذاکرات", "دیپلمات", "دیپلماسی", "وزیر خارجه", "وزیر امور خارجه", "سفیر", "کاردار",
                   "احضار", "سفارت", "دیدار", "گفتگو", "گفت وگو", "میانجی", "توافق", "رایزنی", "شورای امنیت",
                   "هیئت", "هیات", "نشست", "اجلاس"]),
    "economy": ("تحریم و اقتصاد", "Sanctions & economy",
                ["sanction", "oil price", "crude", "brent", "opec", "economy", "economic", "currency", "rial",
                 "export", "inflation", "gold price", "markets$", "treasury", "ofac$"],
                ["تحریم", "نفت", "اقتصاد", "ارز", "دلار", "ریال", "صادرات", "تورم", "طلا", "اوراق", "خزانه داری",
                 "بازار"]),
    "statement": ("بیانات", "Statements",
                  ["said$", "says$", "warned", "warns", "vowed", "vows", "told$", "statement", "remarks", "speech",
                   "interview", "posted", "wrote on", "truth social", "press conference", "briefing"],
                  ["گفت", "اظهار", "بیانیه", "تاکید کرد", "اعلام کرد", "هشدار داد", "سخنرانی", "مصاحبه"]),
}


# ------------------------------------------------------------------ compiled forms

def _compile(table):
    out = {}
    for k, v in table.items():
        en_terms, fa_terms = v[-2], v[-1]
        out[k] = (en_rx(en_terms) if en_terms else None, fa_rx(fa_terms) if fa_terms else None)
    return out


PEOPLE_RX = _compile(PEOPLE)
PLACES_RX = _compile(PLACES)
COUNTRIES_RX = _compile(COUNTRIES)
TOPICS_RX = _compile(TOPICS)


def match_keys(table_rx, en_text="", fa_text=""):
    """Return keys whose patterns match the English text or the (normalised) Persian text."""
    hits = []
    fa_n = fa_norm(fa_text) if fa_text else ""
    for k, (erx, frx) in table_rx.items():
        if (erx is not None and en_text and erx.search(en_text)) or \
           (frx is not None and fa_n and frx.search(fa_n)):
            hits.append(k)
    return hits
