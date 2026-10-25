"""Generate offline fixtures (synthetic sample data) for the end-to-end test.
Run:  python tests/make_fixtures.py   then   DB_OFFLINE=1 DB_NOW=<printed> python -m engine.run_news
"""
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "fixtures")
NOW = datetime(2026, 10, 25, 6, 30, tzinfo=timezone.utc)
os.makedirs(FX, exist_ok=True)


def ago(h):
    return NOW - timedelta(hours=h)


def rss(items, title="feed"):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>',
             f"<title>{escape(title)}</title>"]
    for it in items:
        parts.append("<item>")
        parts.append(f"<title>{escape(it['title'])}</title>")
        parts.append(f"<link>{escape(it['link'])}</link>")
        if it.get("desc"):
            parts.append(f"<description><![CDATA[{it['desc']}]]></description>")
        parts.append(f"<pubDate>{format_datetime(it['date'])}</pubDate>")
        if it.get("img"):
            parts.append(f'<media:thumbnail url="{escape(it["img"])}" width="1024"/>')
        if it.get("source"):
            parts.append(f'<source url="{it["source"][1]}">{escape(it["source"][0])}</source>')
        parts.append("</item>")
    parts.append("</channel></rss>")
    return "\n".join(parts)


def w(name, content):
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(os.path.join(FX, name), mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
        f.write(content)


IMG = "https://picsum.photos/seed/{}/1024/576"

bbc = [
    dict(title="Iranian navy seizes tanker near Strait of Hormuz, state media says",
         link="https://www.bbc.com/news/articles/sample-hormuz-tanker", date=ago(1.2), img=IMG.format("tanker"),
         desc="Iran's navy said it seized a foreign-flagged oil tanker it accused of smuggling fuel near the Strait of Hormuz. The vessel was escorted to Bandar Abbas."),
    dict(title="US sends second aircraft carrier to Middle East amid Iran tensions",
         link="https://www.bbc.com/news/articles/sample-carrier", date=ago(3.5), img=IMG.format("carrier"),
         desc="The Pentagon said a second carrier strike group is heading to the region. Officials described the move as a deterrent."),
    dict(title="Treasury sanctions shipping network moving Iranian oil",
         link="https://www.bbc.com/news/articles/sample-sanctions", date=ago(7), img=IMG.format("port"),
         desc="The US Treasury designated a dozen companies and vessels it says shipped Iranian crude to Asian buyers."),
    dict(title="Qatar and Saudi Arabia call for restraint after Hormuz incident",
         link="https://www.bbc.com/news/articles/sample-restraint", date=ago(0.6),
         desc="Both governments urged all sides to avoid escalation and protect freedom of navigation."),
    dict(title="World Cup qualifier: Iran beat Uzbekistan 2-1 in Tashkent",
         link="https://www.bbc.com/sport/football/sample", date=ago(5), desc="A late goal sealed the win."),
]
aj = [
    dict(title="Iran's navy seizes oil tanker in Hormuz, accusing it of smuggling",
         link="https://www.aljazeera.com/news/2026/10/25/sample-iran-seizes-tanker", date=ago(1.0),
         img=IMG.format("hormuz"), desc="The seizure comes amid heightened tension in the Gulf."),
    dict(title="Oman hosts new round of indirect US-Iran talks in Muscat",
         link="https://www.aljazeera.com/news/2026/10/24/sample-oman-talks", date=ago(9), img=IMG.format("muscat"),
         desc="Omani mediators shuttled between the two delegations, according to diplomats."),
    dict(title="Analysis: What a new Hormuz crisis means for Gulf states",
         link="https://www.aljazeera.com/features/sample-analysis", date=ago(4), img=IMG.format("gulf"),
         desc="Gulf economies are bracing for disruption to energy exports."),
    dict(title="Houthis claim missile attack on ship in Red Sea",
         link="https://www.aljazeera.com/news/2026/10/25/sample-houthi", date=ago(2.4), img=IMG.format("redsea"),
         desc="The group said it targeted a vessel it linked to Israel. There was no immediate confirmation."),
]
toi = [
    dict(title="IDF says it intercepted drone launched from Yemen over Eilat",
         link="https://www.timesofisrael.com/liveblog-sample-eilat-drone/", date=ago(2.0), img=IMG.format("eilat"),
         desc="Sirens sounded in Eilat; no injuries were reported."),
    dict(title="Netanyahu warns Iran will 'pay a heavy price' for any attack",
         link="https://www.timesofisrael.com/sample-netanyahu-warns/", date=ago(6), img=IMG.format("knesset"),
         desc="The prime minister spoke at the opening of a cabinet meeting."),
    dict(title="IAEA chief Grossi says inspectors still denied access to Fordow",
         link="https://www.timesofisrael.com/sample-grossi-fordow/", date=ago(11), img=IMG.format("iaea"),
         desc="Grossi told reporters in Vienna that the agency has lost continuity of knowledge."),
    dict(title="Tech startup raises $50m in funding round",
         link="https://www.timesofisrael.com/sample-startup/", date=ago(3), desc="The company builds AI tools."),
]
gn_wire = [
    dict(title="Iran seizes tanker in Strait of Hormuz - Reuters", link="https://news.google.com/rss/articles/SAMPLE1",
         date=ago(1.1), source=("Reuters", "https://www.reuters.com")),
    dict(title="Oil prices jump 4% after tanker seizure in Hormuz - Reuters",
         link="https://news.google.com/rss/articles/SAMPLE2", date=ago(0.8), source=("Reuters", "https://www.reuters.com")),
    dict(title="Airlines reroute flights away from Iraqi airspace - AP", link="https://news.google.com/rss/articles/SAMPLE3",
         date=ago(5.5), source=("AP News", "https://apnews.com")),
]
tasnim = [
    dict(title="سپاه: نفتکش متخلف در تنگه هرمز توقیف شد", link="https://www.tasnimnews.com/fa/news/sample1",
         date=ago(1.4), desc="نیروی دریایی سپاه یک نفتکش خارجی را به اتهام قاچاق سوخت توقیف کرد."),
    dict(title="عراقچی: مذاکرات غیرمستقیم با آمریکا در مسقط ادامه دارد", link="https://www.tasnimnews.com/fa/news/sample2",
         date=ago(8.5), desc="وزیر امور خارجه گفت دور جدید گفتگوها با میانجی‌گری عمان برگزار شد."),
    dict(title="قیمت دلار امروز در بازار آزاد", link="https://www.tasnimnews.com/fa/news/sample3", date=ago(2),
         desc="نرخ ارز در بازار آزاد امروز اعلام شد."),
]
bbcfa = [
    dict(title="آمریکا دومین ناو هواپیمابر را به خاورمیانه اعزام کرد", link="https://www.bbc.com/persian/articles/sample1",
         date=ago(3.0), img=IMG.format("navfa"), desc="پنتاگون اعلام کرد گروه ضربت دوم برای بازدارندگی به منطقه می‌رود."),
]
truth = [
    dict(title="Post", link="https://trumpstruth.org/statuses/31234", date=ago(2.2),
         desc="<p>Iran must stop playing games in the Strait of Hormuz. If they touch our ships, the response will be swift and very strong!</p>"),
    dict(title="Post", link="https://trumpstruth.org/statuses/31235", date=ago(4),
         desc="<p>Great rally last night, thank you to all the wonderful people!</p>"),
]

w("bbc.xml", rss(bbc, "BBC"))
w("aljazeera.xml", rss(aj, "Al Jazeera"))
w("toi.xml", rss(toi, "Times of Israel"))
w("gn_wire.xml", rss(gn_wire, "Google News"))
w("gn_empty.xml", rss([], "Google News"))
w("tasnim.xml", rss(tasnim, "Tasnim"))
w("bbcpersian.xml", rss(bbcfa, "BBC Persian"))
w("truth.xml", rss(truth, "Trump's Truth"))

w("article.html", """<html><head><meta property="og:image" content="https://picsum.photos/seed/ogimg/1200/630">
<meta property="og:title" content="sample"></head><body><blockquote class="twitter-tweet"><p>Statement</p>
<a href="https://twitter.com/CENTCOM/status/1850123456789012345">Oct 25, 2026</a></blockquote>
<a href="https://x.com/randomuser/status/1850000000000000001">x</a></body></html>""")

w("tweet.json", json.dumps({
    "__typename": "Tweet", "id_str": "1850123456789012345", "lang": "en",
    "text": "CENTCOM forces are monitoring the situation in the Strait of Hormuz and remain ready to protect freedom of navigation. https://t.co/abc",
    "created_at": (NOW - timedelta(hours=0.9)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "favorite_count": 18400, "conversation_count": 2100,
    "user": {"name": "U.S. Central Command", "screen_name": "CENTCOM", "is_blue_verified": True,
             "profile_image_url_https": "https://picsum.photos/seed/centcom/96/96"},
    "entities": {"urls": [], "media": [{"url": "https://t.co/abc"}]},
    "mediaDetails": [{"type": "photo", "media_url_https": "https://picsum.photos/seed/centcomphoto/1200/675"}],
}))

# ---- Telegram channel page (text from the user's screenshot + the pinned ad with a check mark)
def tg(mid, text, ts):
    return (f'<div class="tgme_widget_message_wrap"><div class="tgme_widget_message js-widget_message" '
            f'data-post="dollar_tehran3bze/{mid}"><div class="tgme_widget_message_text js-message_text" dir="auto">'
            f'{text}</div><div class="tgme_widget_message_footer"><a class="tgme_widget_message_date" href="#">'
            f'<time datetime="{ts.strftime("%Y-%m-%dT%H:%M:%S+00:00")}" class="time">x</time></a></div></div></div>')


E = lambda ch: f'<i class="emoji"><b>{ch}</b></i>'  # noqa: E731
base = NOW - timedelta(hours=10)   # evening yesterday (Tehran)
msgs = [
    tg(90001, f"{E('✅')} قبل از خرید یا فروش طلا، فقط چند ثانیه صبر کنید", base - timedelta(hours=3)),
    tg(90010, f"دلار فردایی تهران {E('⏳')} 268,000 معامله شد {E('✅')}", base - timedelta(minutes=50)),
    tg(90011, f"دلار فردایی تهران {E('⏳')} 268,200 خـرید {E('🔵')}", base - timedelta(minutes=20)),
    tg(90012, f"دلار فردایی تهران {E('⏳')} 268,300 فروش {E('🔴')}", base - timedelta(minutes=20)),
    tg(90013, f"دلار فردایی تهران {E('⏳')} 268,200 معامله شد {E('✅')}", base - timedelta(minutes=8)),
    tg(90014, f"دلار فردایی تهران {E('⏳')} 268,000 خـرید {E('🔵')}", base - timedelta(minutes=8)),
    tg(90015, f"دلار فردایی تهران {E('⏳')} 268,200 فروش {E('🔴')}", base - timedelta(minutes=8)),
    tg(90020, f"دلار فردایی تهران {E('⏳')} ۲۶۸,۹۰۰ معامله شد {E('✅')}", NOW - timedelta(minutes=35)),
    tg(90021, f"دلار فردایی تهران {E('⏳')} 269,400 معامله شد {E('✅')}", NOW - timedelta(minutes=12)),
    tg(90022, f"دلار فردایی تهران {E('⏳')} 269,300 خـرید {E('🔵')}", NOW - timedelta(minutes=6)),
]
w("tg.html", "<html><body><section class='tgme_channel_history'>" + "".join(msgs) + "</section></body></html>")

# ---- markets
def chart(price, prev, n=150, step=1800, drift=0.0):
    ts0 = int(NOW.timestamp()) - n * step
    closes = [round(prev + (price - prev) * i / n + (0.3 if i % 7 == 0 else -0.2) + drift * i, 2) for i in range(n)]
    return json.dumps({"chart": {"result": [{"meta": {"regularMarketPrice": price, "chartPreviousClose": prev,
                                                       "regularMarketTime": int(NOW.timestamp())},
                                              "timestamp": [ts0 + i * step for i in range(n)],
                                              "indicators": {"quote": [{"close": closes}]}}]}})


w("yahoo_brent.json", chart(82.4, 77.1))
w("yahoo_gold.json", chart(3412.5, 3366.0, drift=0.05))

# ---- air
w("air_mil.json", json.dumps({"ac": [
    {"hex": "ae0001", "flight": "QUID45 ", "t": "K35R", "lat": 26.1, "lon": 52.3, "alt_baro": 27000, "dbFlags": 1},
    {"hex": "ae0002", "flight": "QUID46 ", "t": "K35R", "lat": 25.4, "lon": 54.9, "alt_baro": 26000, "dbFlags": 1},
    {"hex": "ae0003", "flight": "SHELL72", "t": "KC46", "lat": 28.3, "lon": 48.9, "alt_baro": 25000, "dbFlags": 1},
    {"hex": "ae0004", "flight": "FORTE11", "t": "Q4", "lat": 24.2, "lon": 57.9, "alt_baro": 52000, "dbFlags": 1},
    {"hex": "ae0005", "flight": "RCH334 ", "t": "C17", "lat": 30.1, "lon": 37.2, "alt_baro": 33000, "dbFlags": 1},
    {"hex": "ae0006", "flight": "NAVY2  ", "t": "P8", "lat": 23.6, "lon": 59.4, "alt_baro": 24000, "dbFlags": 1},
    {"hex": "ae0099", "flight": "RCH001 ", "t": "C17", "lat": 52.1, "lon": 8.4, "alt_baro": 30000, "dbFlags": 1},
]}))
w("air_point_iran.json", json.dumps({"ac": [
    {"hex": f"7300{i:02d}", "flight": f"IRA{i}", "t": "A320", "lat": 33 + (i % 5) * 0.7, "lon": 50 + (i % 6) * 0.9,
     "alt_baro": 30000, "dbFlags": 0} for i in range(18)]}))
w("air_point_other.json", json.dumps({"ac": [
    {"hex": f"8800{i:02d}", "flight": f"QTR{i}", "t": "B77W", "lat": 25.5 + (i % 4) * 0.4, "lon": 51 + (i % 6) * 0.7,
     "alt_baro": 35000, "dbFlags": 0} for i in range(30)]}))

# ---- PortWatch: ~90/day before the crisis, ~5/day after
rows = []
d = datetime(2025, 3, 1, tzinfo=timezone.utc)
last = datetime(2026, 10, 18, tzinfo=timezone.utc)
while d <= last:
    pre = d < datetime(2026, 2, 28, tzinfo=timezone.utc)
    tot = (88 + (d.day % 9)) if pre else (3 + (d.day % 5))
    rows.append({"attributes": {"date": int(d.timestamp() * 1000), "portname": "Strait of Hormuz", "n_total": tot,
                                "n_tanker": tot // 2}})
    d += timedelta(days=1)
w("portwatch_hormuz.json", json.dumps({"features": list(reversed(rows))}))
rows = []
d = datetime(2025, 3, 1, tzinfo=timezone.utc)
while d <= last:
    rows.append({"attributes": {"date": int(d.timestamp() * 1000), "portname": "Bab el-Mandeb Strait",
                                "n_total": 30 + d.day % 6, "n_tanker": 9}})
    d += timedelta(days=1)
w("portwatch_bab.json", json.dumps({"features": list(reversed(rows))}))
w("nga.json", json.dumps({"broadcast-warn": [
    {"navArea": "HYDROPAC", "msgNumber": 1234, "msgYear": 2026, "issueDate": "241200Z OCT 2026",
     "text": "PERSIAN GULF. STRAIT OF HORMUZ. MILITARY EXERCISES IN PROGRESS WITHIN AREA BOUNDED BY 26-30N 056-10E."},
    {"navArea": "4", "msgNumber": 999, "msgYear": 2026, "issueDate": "231000Z OCT 2026",
     "text": "GULF OF MEXICO. BUOY ADRIFT."},
]}))

# ---- canned translations for the offline translator
tr = {
    "Iranian navy seizes tanker near Strait of Hormuz, state media says": "نیروی دریایی ایران نفتکشی را نزدیک تنگه هرمز توقیف کرد",
    "Iran's navy said it seized a foreign-flagged oil tanker it accused of smuggling fuel near the Strait of Hormuz. The vessel was escorted to Bandar Abbas.":
        "نیروی دریایی ایران اعلام کرد یک نفتکش با پرچم خارجی را به اتهام قاچاق سوخت نزدیک تنگه هرمز توقیف کرده و آن را به بندرعباس برده است.",
    "US sends second aircraft carrier to Middle East amid Iran tensions": "آمریکا در بحبوحه تنش با ایران دومین ناو هواپیمابر را به خاورمیانه می‌فرستد",
    "The Pentagon said a second carrier strike group is heading to the region. Officials described the move as a deterrent.":
        "پنتاگون اعلام کرد دومین گروه ضربت ناو هواپیمابر در راه منطقه است. مقام‌ها این اقدام را بازدارنده خواندند.",
    "Treasury sanctions shipping network moving Iranian oil": "خزانه‌داری آمریکا شبکه حمل نفت ایران را تحریم کرد",
    "The US Treasury designated a dozen companies and vessels it says shipped Iranian crude to Asian buyers.":
        "خزانه‌داری آمریکا ده‌ها شرکت و کشتی را که به گفته آن نفت ایران را به خریداران آسیایی منتقل کرده‌اند تحریم کرد.",
    "Qatar and Saudi Arabia call for restraint after Hormuz incident": "قطر و عربستان پس از حادثه هرمز خواستار خویشتنداری شدند",
    "Both governments urged all sides to avoid escalation and protect freedom of navigation.":
        "دو دولت از همه طرف‌ها خواستند از تشدید تنش پرهیز و از آزادی کشتیرانی محافظت کنند.",
    "Oman hosts new round of indirect US-Iran talks in Muscat": "عمان میزبان دور جدید مذاکرات غیرمستقیم ایران و آمریکا در مسقط شد",
    "Omani mediators shuttled between the two delegations, according to diplomats.": "به گفته دیپلمات‌ها، میانجی‌های عمانی میان دو هیئت رفت‌وآمد کردند.",
    "Analysis: What a new Hormuz crisis means for Gulf states": "تحلیل: بحران تازه هرمز برای کشورهای خلیج فارس چه معنایی دارد",
    "Gulf economies are bracing for disruption to energy exports.": "اقتصادهای خلیج فارس برای اختلال در صادرات انرژی آماده می‌شوند.",
    "Houthis claim missile attack on ship in Red Sea": "حوثی‌ها مدعی حمله موشکی به یک کشتی در دریای سرخ شدند",
    "The group said it targeted a vessel it linked to Israel. There was no immediate confirmation.":
        "این گروه گفت کشتی‌ای مرتبط با اسرائیل را هدف گرفته است. این ادعا فوراً تأیید نشد.",
    "IDF says it intercepted drone launched from Yemen over Eilat": "ارتش اسرائیل می‌گوید پهپادی را که از یمن شلیک شده بود بر فراز ایلات رهگیری کرد",
    "Sirens sounded in Eilat; no injuries were reported.": "آژیرها در ایلات به صدا درآمد؛ گزارشی از مجروح شدن کسی منتشر نشد.",
    "Netanyahu warns Iran will 'pay a heavy price' for any attack": "نتانیاهو هشدار داد ایران برای هر حمله‌ای «بهای سنگینی» خواهد پرداخت",
    "The prime minister spoke at the opening of a cabinet meeting.": "نخست‌وزیر در آغاز جلسه کابینه سخن می‌گفت.",
    "IAEA chief Grossi says inspectors still denied access to Fordow": "گروسی: بازرسان آژانس همچنان به فردو دسترسی ندارند",
    "Grossi told reporters in Vienna that the agency has lost continuity of knowledge.": "گروسی در وین به خبرنگاران گفت آژانس پیوستگی اطلاعات را از دست داده است.",
    "Iran seizes tanker in Strait of Hormuz": "ایران نفتکشی را در تنگه هرمز توقیف کرد",
    "Oil prices jump 4% after tanker seizure in Hormuz": "قیمت نفت پس از توقیف نفتکش در هرمز ۴ درصد جهش کرد",
    "Airlines reroute flights away from Iraqi airspace": "شرکت‌های هواپیمایی مسیر پروازها را از حریم هوایی عراق تغییر دادند",
    "Iran's navy seizes oil tanker in Hormuz, accusing it of smuggling": "نیروی دریایی ایران نفتکشی را در هرمز به اتهام قاچاق توقیف کرد",
    "سپاه: نفتکش متخلف در تنگه هرمز توقیف شد": "IRGC: Violating tanker seized in the Strait of Hormuz",
    "نیروی دریایی سپاه یک نفتکش خارجی را به اتهام قاچاق سوخت توقیف کرد.": "The IRGC Navy seized a foreign tanker on charges of fuel smuggling.",
    "عراقچی: مذاکرات غیرمستقیم با آمریکا در مسقط ادامه دارد": "Araghchi: Indirect talks with the US continue in Muscat",
    "وزیر امور خارجه گفت دور جدید گفتگوها با میانجی‌گری عمان برگزار شد.": "The foreign minister said a new round of talks was held with Omani mediation.",
    "آمریکا دومین ناو هواپیمابر را به خاورمیانه اعزام کرد": "US sends second aircraft carrier to the Middle East",
    "پنتاگون اعلام کرد گروه ضربت دوم برای بازدارندگی به منطقه می‌رود.": "The Pentagon said the second strike group is going to the region for deterrence.",
    "CENTCOM forces are monitoring the situation in the Strait of Hormuz and remain ready to protect freedom of navigation.":
        "نیروهای سنتکام وضعیت تنگه هرمز را زیر نظر دارند و برای حفاظت از آزادی کشتیرانی آماده‌اند.",
    "Iran must stop playing games in the Strait of Hormuz. If they touch our ships, the response will be swift and very strong!":
        "ایران باید بازی در تنگه هرمز را متوقف کند. اگر به کشتی‌های ما دست بزنند، پاسخ سریع و بسیار قوی خواهد بود!",
}
w("translations.json", json.dumps(tr, ensure_ascii=False, indent=1))

index = {
    r"feeds\.bbci\.co\.uk/news/world/middle_east": "bbc.xml",
    r"aljazeera\.com/xml/rss": "aljazeera.xml",
    r"timesofisrael\.com/feed": "toi.xml",
    r"news\.google\.com/rss/search\?q=.*reuters": "gn_wire.xml",
    r"news\.google\.com/rss/search": "gn_empty.xml",
    r"tasnimnews\.com/fa/rss": "tasnim.xml",
    r"feeds\.bbci\.co\.uk/persian": "bbcpersian.xml",
    r"trumpstruth\.org/feed": "truth.xml",
    r"bbc\.com/news/articles/sample-hormuz-tanker": "article.html",
    r"cdn\.syndication\.twimg\.com/tweet-result.*1850123456789012345": "tweet.json",
    r"t\.me/s/dollar_tehran3bze": "tg.html",
    r"finance\.yahoo\.com/v8/finance/chart/BZ": "yahoo_brent.json",
    r"finance\.yahoo\.com/v8/finance/chart/GC": "yahoo_gold.json",
    r"api\.airplanes\.live/v2/mil": "air_mil.json",
    r"api\.airplanes\.live/v2/point/(35|32|29|36|38|27)\.": "air_point_iran.json",
    r"api\.airplanes\.live/v2/point/": "air_point_other.json",
    r"Daily_Chokepoints_Data.*Hormuz": "portwatch_hormuz.json",
    r"Daily_Chokepoints_Data.*Mandeb": "portwatch_bab.json",
    r"msi\.nga\.mil": "nga.json",
}
w("index.json", json.dumps(index, indent=1))
print(int(NOW.timestamp()))
