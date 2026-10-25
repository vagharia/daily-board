"""The fixed list of 94 sources checked on every run.

Each source has its own feeds; when they fail or don't exist, the engine falls back to a
Google News query restricted to the source's domain(s). `rel` is a 0-1 reliability weight
used for picking the headline of a story and for weighting the escalation index.
"""

GROUPS = {
    "wire": ("خبرگزاری‌ها و رسانه‌های جهانی", "Global wires & broadcasters"),
    "us": ("آمریکا", "United States"),
    "eu": ("اروپا", "Europe"),
    "il": ("اسرائیل", "Israel"),
    "arab": ("جهان عرب و منطقه", "Arab world & region"),
    "gulf": ("خبرگزاری‌های رسمی خلیج فارس", "Official Persian Gulf agencies"),
    "powers": ("قدرت‌ها و کشورهای دیگر", "Other powers"),
    "defense": ("نظامی و امنیتی", "Defense & security"),
    "maritime": ("دریایی و انرژی", "Maritime & energy"),
    "official": ("منابع رسمی", "Official sources"),
    "fa_intl": ("فارسی‌زبان خارج از ایران", "Persian-language international"),
    "iran": ("ایرانی", "Iranian"),
}


def S(id, en, fa, group, rel, domains, feeds=(), lang="en", gn=True, gnq=None, kind="news", tg=(), tz=0,
      via_media=False):
    """tz: correction in seconds for feeds that print local time as UTC. via_media: the source is found
    through other outlets' reports (UKMTO, CENTCOM), so items show the reporting outlet's name."""
    if isinstance(domains, str):
        domains = [domains]
    return dict(id=id, en=en, fa=fa, group=group, rel=rel, domains=list(domains),
                feeds=list(feeds), lang=lang, gn=gn, gnq=gnq, kind=kind, tg=list(tg), tz=tz, via_media=via_media)


SOURCES = [
    # ------------------------------------------------------------ wires & global (12)
    S("reuters", "Reuters", "رویترز", "wire", 1.0, "reuters.com"),
    S("ap", "AP", "آسوشیتدپرس", "wire", 1.0, "apnews.com"),
    S("afp", "AFP", "خبرگزاری فرانسه", "wire", 0.95, "barrons.com",
      gnq="site:barrons.com/news"),
    S("bloomberg", "Bloomberg", "بلومبرگ", "wire", 0.95, "bloomberg.com", [
        "https://feeds.bloomberg.com/politics/news.rss",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/economics/news.rss"]),
    S("bbc", "BBC", "بی‌بی‌سی", "wire", 0.95, "bbc.com", [
        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml"]),
    S("cnn", "CNN", "سی‌ان‌ان", "wire", 0.85, "cnn.com"),          # CNN's RSS feeds are stale
    S("aljazeera", "Al Jazeera", "الجزیره", "wire", 0.85, "aljazeera.com", [
        "https://www.aljazeera.com/xml/rss/all.xml"]),
    S("skynews", "Sky News", "اسکای نیوز", "wire", 0.85, "news.sky.com", [
        "https://feeds.skynews.com/feeds/rss/world.xml"]),
    S("france24", "France 24", "فرانس ۲۴", "wire", 0.85, "france24.com", [
        "https://www.france24.com/en/middle-east/rss",
        "https://www.france24.com/en/rss"]),
    S("dw", "DW", "دویچه وله", "wire", 0.85, "dw.com", [
        "https://rss.dw.com/rdf/rss-en-world",
        "https://rss.dw.com/rdf/rss-en-all"]),
    S("euronews", "Euronews", "یورونیوز", "wire", 0.8, "euronews.com", [
        "https://www.euronews.com/rss?level=theme&name=news",
        "https://www.euronews.com/rss"]),
    S("npr", "NPR", "ان‌پی‌آر", "wire", 0.85, "npr.org", [
        "https://feeds.npr.org/1004/rss.xml"]),

    # ------------------------------------------------------------ United States (12)
    S("nyt", "New York Times", "نیویورک تایمز", "us", 0.95, "nytimes.com", [
        "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"]),
    S("wapo", "Washington Post", "واشنگتن پست", "us", 0.9, "washingtonpost.com", [
        "https://feeds.washingtonpost.com/rss/world"]),
    S("wsj", "Wall Street Journal", "وال‌استریت ژورنال", "us", 0.95, "wsj.com", [
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml"]),
    S("axios", "Axios", "اکسیوس", "us", 0.9, "axios.com", [
        "https://api.axios.com/feed/"]),
    S("politico", "Politico", "پولیتیکو", "us", 0.85, "politico.com", [
        "https://rss.politico.com/politics-news.xml",
        "https://rss.politico.com/defense.xml"]),
    S("thehill", "The Hill", "د هیل", "us", 0.8, "thehill.com", [
        "https://thehill.com/policy/international/feed/",
        "https://thehill.com/policy/defense/feed/"]),
    S("fox", "Fox News", "فاکس نیوز", "us", 0.75, "foxnews.com", [
        "https://moxie.foxnews.com/google-publisher/world.xml",
        "https://moxie.foxnews.com/google-publisher/politics.xml"]),
    S("nbc", "NBC News", "ان‌بی‌سی", "us", 0.85, "nbcnews.com", [
        "https://feeds.nbcnews.com/nbcnews/public/world"]),
    S("cbs", "CBS News", "سی‌بی‌اس", "us", 0.85, "cbsnews.com", [
        "https://www.cbsnews.com/latest/rss/world"]),
    S("abc", "ABC News", "ای‌بی‌سی", "us", 0.85, "abcnews.go.com", [
        "https://feeds.abcnews.com/abcnews/internationalheadlines"]),
    S("cnbc", "CNBC", "سی‌ان‌بی‌سی", "us", 0.85, "cnbc.com", [
        "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "https://www.cnbc.com/id/19836768/device/rss/rss.html"]),
    S("fp", "Foreign Policy", "فارن پالیسی", "us", 0.85, "foreignpolicy.com", [
        "https://foreignpolicy.com/feed/"]),

    # ------------------------------------------------------------ Europe (6)
    S("guardian", "The Guardian", "گاردین", "eu", 0.9, "theguardian.com", [
        "https://www.theguardian.com/world/middleeast/rss",
        "https://www.theguardian.com/world/iran/rss"]),
    S("ft", "Financial Times", "فایننشال تایمز", "eu", 0.95, "ft.com", [
        "https://www.ft.com/world/mideast?format=rss",
        "https://www.ft.com/world?format=rss"]),
    S("economist", "The Economist", "اکونومیست", "eu", 0.9, "economist.com", [
        "https://www.economist.com/middle-east-and-africa/rss.xml"]),
    S("independent", "The Independent", "ایندیپندنت", "eu", 0.8, "independent.co.uk", [
        "https://www.independent.co.uk/news/world/middle-east/rss"]),
    S("telegraph", "The Telegraph", "تلگراف", "eu", 0.8, "telegraph.co.uk", [
        "https://www.telegraph.co.uk/world-news/rss.xml"]),
    S("lemonde", "Le Monde", "لوموند", "eu", 0.9, "lemonde.fr", [
        "https://www.lemonde.fr/en/international/rss_full.xml"]),

    # ------------------------------------------------------------ Israel (6)
    S("toi", "Times of Israel", "تایمز اسرائیل", "il", 0.85, "timesofisrael.com", [
        "https://www.timesofisrael.com/feed/"]),
    S("jpost", "Jerusalem Post", "جروزالم پست", "il", 0.75, "jpost.com", [
        "https://www.jpost.com/rss/rssfeedsmiddleeastnews.aspx",
        "https://www.jpost.com/rss/rssfeedsfrontpage.aspx"]),
    S("haaretz", "Haaretz", "هاآرتص", "il", 0.85, "haaretz.com", [
        "https://www.haaretz.com/srv/haaretz-latest-headlines"]),
    S("ynet", "Ynet News", "وای‌نت", "il", 0.75, "ynetnews.com", [
        "https://www.ynetnews.com/Integration/StoryRss3089.xml"]),
    S("i24", "i24NEWS", "آی۲۴ نیوز", "il", 0.7, "i24news.tv"),
    S("hayom", "Israel Hayom", "اسرائیل هیوم", "il", 0.7, "israelhayom.com", [
        "https://www.israelhayom.com/feed/"]),

    # ------------------------------------------------------------ Arab world & region (11)
    S("alarabiya", "Al Arabiya", "العربیه", "arab", 0.75, "alarabiya.net", [
        "https://english.alarabiya.net/feed/rss2/en.xml"]),
    S("aawsat", "Asharq Al-Awsat", "الشرق الاوسط", "arab", 0.75, "aawsat.com", [
        "https://english.aawsat.com/feed"]),
    S("arabnews", "Arab News", "عرب نیوز", "arab", 0.75, "arabnews.com", [
        "https://www.arabnews.com/cat/1/rss.xml",
        "https://www.arabnews.com/rss.xml"]),
    S("thenational", "The National", "نشنال", "arab", 0.8, "thenationalnews.com", [
        "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml"]),
    S("gulfnews", "Gulf News", "گلف نیوز", "arab", 0.75, "gulfnews.com"),
    S("khaleej", "Khaleej Times", "خلیج تایمز", "arab", 0.75, "khaleejtimes.com", [
        "https://www.khaleejtimes.com/arc/outboundfeeds/rss/?outputType=xml"]),
    S("almonitor", "Al-Monitor", "المانیتور", "arab", 0.85, "al-monitor.com", [
        "https://www.al-monitor.com/rss"]),
    S("mee", "Middle East Eye", "میدل ایست آی", "arab", 0.75, "middleeasteye.net", [
        "https://www.middleeasteye.net/rss"]),
    S("newarab", "The New Arab", "العربی الجدید", "arab", 0.75, "newarab.com", [
        "https://www.newarab.com/rss"]),
    S("lorient", "L'Orient Today", "لوریان تودی", "arab", 0.75, "lorientlejour.com"),
    S("rudaw", "Rudaw", "رووداو", "arab", 0.7, "rudaw.net"),

    # ------------------------------------------------------------ official Persian Gulf agencies (6)
    S("spa", "Saudi Press Agency", "خبرگزاری عربستان", "gulf", 0.75, "spa.gov.sa"),
    S("wam", "WAM (UAE)", "خبرگزاری امارات", "gulf", 0.75, "wam.ae"),
    S("qna", "Qatar News Agency", "خبرگزاری قطر", "gulf", 0.75, "qna.org.qa", [
        "https://qna.org.qa/en/Pages/RSS-Feeds/General"], tz=-3 * 3600),
    S("ona", "Oman News Agency", "خبرگزاری عمان", "gulf", 0.75, "omannews.gov.om"),
    S("kuna", "KUNA (Kuwait)", "خبرگزاری کویت", "gulf", 0.75, "kuna.net.kw"),
    S("bna", "Bahrain News Agency", "خبرگزاری بحرین", "gulf", 0.75, "bna.bh"),

    # ------------------------------------------------------------ other powers (6)
    S("trt", "TRT World", "تی‌آر‌تی ورلد", "powers", 0.7, "trtworld.com"),
    S("anadolu", "Anadolu", "آناتولی", "powers", 0.75, "aa.com.tr", [
        "https://www.aa.com.tr/en/rss/default?cat=middle-east",
        "https://www.aa.com.tr/en/rss/default?cat=world"]),
    S("tass", "TASS", "تاس", "powers", 0.6, "tass.com", [
        "https://tass.com/rss/v2.xml"]),
    S("xinhua", "Xinhua", "شین‌هوا", "powers", 0.6, "news.cn"),
    S("scmp", "South China Morning Post", "ساوت چاینا مورنینگ پست", "powers", 0.8, "scmp.com", [
        "https://www.scmp.com/rss/91/feed",
        "https://www.scmp.com/rss/5/feed"]),
    S("dawn", "Dawn", "داون", "powers", 0.75, "dawn.com", [
        "https://www.dawn.com/feeds/world"]),

    # ------------------------------------------------------------ defense & security (7)
    S("isw", "ISW / Critical Threats", "اندیشکده مطالعات جنگ", "defense", 0.85,
      ["understandingwar.org", "criticalthreats.org"]),
    S("usni", "USNI News", "USNI News", "defense", 0.9, "news.usni.org", [
        "https://news.usni.org/feed"]),
    S("defensenews", "Defense News", "دیفنس نیوز", "defense", 0.85, "defensenews.com", [
        "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"]),
    S("breakingdef", "Breaking Defense", "بریکینگ دیفنس", "defense", 0.85, "breakingdefense.com", [
        "https://breakingdefense.com/feed/"]),
    S("twz", "The War Zone", "د وار زون", "defense", 0.8, "twz.com", [
        "https://www.twz.com/feed"]),
    S("lwj", "Long War Journal", "لانگ وار ژورنال", "defense", 0.8, "longwarjournal.org", [
        "https://www.longwarjournal.org/feed"]),
    S("miltimes", "Military Times", "میلیتاری تایمز", "defense", 0.8, "militarytimes.com", [
        "https://www.militarytimes.com/arc/outboundfeeds/rss/?outputType=xml"]),

    # ------------------------------------------------------------ maritime & energy (6)
    S("ukmto", "UKMTO (via media)", "UKMTO", "maritime", 0.85, "ukmto.org",
      gnq='(UKMTO OR "Maritime Trade Operations" OR JMIC)', via_media=True),
    S("lloyds", "Lloyd's List", "لویدز لیست", "maritime", 0.85, "lloydslist.com"),
    S("gcaptain", "gCaptain", "جی‌کاپیتان", "maritime", 0.8, "gcaptain.com", [
        "https://gcaptain.com/feed/"]),
    S("splash", "Splash247", "اسپلش۲۴۷", "maritime", 0.8, "splash247.com", [
        "https://splash247.com/feed/"]),
    S("marex", "Maritime Executive", "ماریتایم اگزکیوتیو", "maritime", 0.8, "maritime-executive.com", [
        "https://maritime-executive.com/articles.rss"]),
    S("oilprice", "OilPrice", "اویل‌پرایس", "maritime", 0.65, "oilprice.com", [
        "https://oilprice.com/rss/main"]),

    # ------------------------------------------------------------ official sources (8)
    S("whitehouse", "White House", "کاخ سفید", "official", 0.8, "whitehouse.gov", [
        "https://www.whitehouse.gov/news/feed/",
        "https://www.whitehouse.gov/feed/"]),
    S("state", "US State Dept", "وزارت خارجه آمریکا", "official", 0.8, "state.gov", [
        "https://www.state.gov/rss-feed/press-releases/feed/",
        "https://www.state.gov/rss-feed/department-press-briefings/feed/"]),
    S("pentagon", "Pentagon", "پنتاگون", "official", 0.8, ["war.gov", "defense.gov"], [
        "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=15",
        "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=15"]),
    S("treasury", "US Treasury", "خزانه‌داری آمریکا", "official", 0.8, "home.treasury.gov"),
    S("centcom", "CENTCOM (via media)", "سنتکام", "official", 0.8, "centcom.mil", [
        "https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=808&max=15"],
      gnq='(CENTCOM OR "Central Command") (statement OR said OR says OR announced)', via_media=True),
    S("iaea", "IAEA", "آژانس انرژی اتمی", "official", 0.85, "iaea.org", [
        "https://www.iaea.org/feeds/topnews"]),
    S("un", "UN News", "اخبار سازمان ملل", "official", 0.85, "news.un.org", [
        "https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml"]),
    S("truth", "Truth Social (Trump)", "تروث‌سوشال ترامپ", "official", 0.8, "trumpstruth.org", [
        "https://trumpstruth.org/feed"], gn=False, kind="social"),

    # ------------------------------------------------------------ Persian-language international (4)
    S("bbcpersian", "BBC Persian", "بی‌بی‌سی فارسی", "fa_intl", 0.85, "bbc.com/persian", [
        "https://feeds.bbci.co.uk/persian/rss.xml"], lang="fa", tg=["bbcpersian"]),
    S("iranintl", "Iran International", "ایران اینترنشنال", "fa_intl", 0.7, "iranintl.com", [
        "https://www.iranintl.com/fa/feed", "https://www.iranintl.com/en/feed"], lang="fa", tg=["iranintltv"]),
    S("radiofarda", "Radio Farda", "رادیو فردا", "fa_intl", 0.75, "radiofarda.com", [
        "https://www.radiofarda.com/api/", "https://www.radiofarda.com/api/zpoqil-vomx-tpe_kip",
        "https://www.radiofarda.com/api/zmoqpl-vomx-tpeykim"], lang="fa", tg=["radiofarda"]),
    S("indypersian", "Independent Persian", "ایندیپندنت فارسی", "fa_intl", 0.7,
      "independentpersian.com", ["https://www.independentpersian.com/rss.xml"], lang="fa", tg=["indypersian"]),

    # ------------------------------------------------------------ Iranian (10)
    S("tasnim", "Tasnim", "تسنیم", "iran", 0.6, "tasnimnews.com", [
        "https://www.tasnimnews.com/fa/rss/feed/0/7/0/"], lang="fa",
      tg=["tasnimnews", "tasnimnews_ir", "tasnim_news", "tasnimnewsen"]),
    S("fars", "Fars", "فارس", "iran", 0.55, "farsnews.ir", [
        "https://www.farsnews.ir/rss"], lang="fa", tg=["farsna"]),
    S("irna", "IRNA", "ایرنا", "iran", 0.65, "irna.ir", [
        "https://www.irna.ir/rss"], lang="fa", tg=["irna_1313"]),
    S("isna", "ISNA", "ایسنا", "iran", 0.65, "isna.ir", [
        "https://www.isna.ir/rss"], lang="fa", tg=["isna94"]),
    S("mehr", "Mehr", "مهر", "iran", 0.6, "mehrnews.com", [
        "https://www.mehrnews.com/rss"], lang="fa", tg=["mehrnews"]),
    S("iribnews", "IRIB News", "خبرگزاری صداوسیما", "iran", 0.6, "iribnews.ir", [
        "https://www.iribnews.ir/fa/rss/allnews"], lang="fa", tg=["iribnews"]),
    S("nournews", "Nour News", "نورنیوز", "iran", 0.6, "nournews.ir", [
        "https://nournews.ir/fa/rss/allnews"], lang="fa", tg=["nournews_ir"]),
    S("defapress", "Defa Press", "دفاع‌پرس", "iran", 0.55, "defapress.ir", [
        "https://www.defapress.ir/fa/rss/allnews"], lang="fa", tg=["defapress_ir"]),
    S("khabaronline", "Khabar Online", "خبرآنلاین", "iran", 0.65, "khabaronline.ir", [
        "https://www.khabaronline.ir/rss"], lang="fa", tg=["khabaronline_ir"]),
    S("entekhab", "Entekhab", "انتخاب", "iran", 0.65, "entekhab.ir", [
        "https://www.entekhab.ir/fa/rss/allnews"], lang="fa", tg=["entekhab_ir"]),
]

BY_ID = {s["id"]: s for s in SOURCES}
assert len(SOURCES) == 94, len(SOURCES)
assert len(BY_ID) == 94


def source_for_domain(host: str):
    """Map a hostname (from a Google News <source url>) to one of our sources."""
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    best = None
    for s in SOURCES:
        for d in s["domains"]:
            base = d.split("/")[0]
            if host == base or host.endswith("." + base):
                # prefer the most specific (longest) domain match
                if best is None or len(base) > best[1]:
                    best = (s, len(base))
    return best[0] if best else None
