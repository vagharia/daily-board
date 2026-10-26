/* Daily Brief — mobile web app. Data comes from the `data` branch of this repository. */
(function () {
  'use strict';

  // ------------------------------------------------------------------ config
  var qs = new URLSearchParams(location.search);
  function dataBase() {
    if (qs.get('data')) return qs.get('data').replace(/\/?$/, '/');
    var h = location.hostname;
    if (/\.github\.io$/.test(h)) {
      var owner = h.split('.')[0];
      var repo = location.pathname.split('/').filter(Boolean)[0] || '';
      return 'https://raw.githubusercontent.com/' + owner + '/' + repo + '/data/';
    }
    return 'data/';
  }
  var BASE = dataBase();

  // ------------------------------------------------------------------ storage
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem('db.' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem('db.' + k, JSON.stringify(v)); } catch (e) { /* storage full or blocked */ } }
  };

  // ------------------------------------------------------------------ strings
  var T = {
    fa: {
      app: 'بولتن روزانه', usd: 'دلار آزاد', brent: 'نفت برنت', gold: 'اونس طلا', index: 'شاخص تنش',
      z0: 'آرام نسبی', z1: 'تنش متوسط', z2: 'تنش بالا', z3: 'بحرانی', breaking: 'فوری',
      tNews: 'خبرها', tMap: 'نقشه و سیگنال‌ها', tX: 'ایکس', r24: '۲۴ ساعت', rWeek: 'هفته',
      all: 'همه', red: 'خیلی مهم', orange: 'مهم', yellow: 'کم‌اهمیت‌تر',
      now: 'همین الان', minAgo: '{n} دقیقه پیش', hAgo: '{n} ساعت پیش', updated: '{t}',
      sources: '{n} منبع', moreSrc: '+{n}', fresh: 'جدید', sev: 'شدت {n}',
      firstRep: 'اولین گزارش {t}', lastRep: 'آخرین گزارش {t}',
      mt: 'ترجمه ماشینی', showOrig: 'نمایش متن اصلی', showTr: 'نمایش ترجمه', srcList: 'منابع این خبر',
      tagsH: 'موضوع، مکان و افراد', searchPh: 'جستجو در خبرها و منابع',
      empty: 'خبری با این فیلترها پیدا نشد.', clear: 'پاک کردن فیلترها', showYellow: 'نمایش خبرهای کم‌اهمیت‌تر',
      storiesH: 'استوری خبرها', fullStory: 'خبر کامل', close: 'بستن', srcLabel: 'منبع:', prev: 'قبلی', next: 'بعدی',
      noData: 'هنوز داده‌ای ساخته نشده. موتور هر چند دقیقه اجرا می‌شود؛ کمی بعد دوباره سر بزن.',
      offline: 'اتصال برقرار نیست؛ آخرین داده ذخیره‌شده نمایش داده می‌شود.',
      lightsH: 'چراغ‌های هشدار', lightsOn: '{n} چراغ روشن:', lightsWatch: 'چراغی روشن نیست؛ {n} مورد زیر نظر',
      lightsOff: 'همه چراغ‌ها خاموش‌اند', on: 'روشن', watch: 'زیر نظر', off: 'خاموش',
      lightsNote: 'روشن یعنی رویداد در ۲۴ ساعت گذشته؛ زیر نظر یعنی ۲۴ تا ۷۲ ساعت پیش.',
      noEvidence: 'شاهدی در سه روز اخیر نیست.',
      d24: 'نسبت به ۲۴ ساعت قبل', idxH: 'شاخص تنش', idxNews: 'اخبار', idxSig: 'سیگنال‌های هوایی و دریایی',
      idxWeek: 'هفت روز اخیر', idxMethod: 'چطور محاسبه می‌شود',
      method1: 'هر خبر بر اساس نوع رویداد امتیاز ۰ تا ۱۰۰ می‌گیرد: اقدام نظامی مستقیم، حادثه در هرمز، اولتیماتوم، بسته شدن حریم هوایی و اعزام ناو و بمب‌افکن قرمز؛ جابه‌جایی هواپیماهای نظامی و سوخت‌رسان، تهدید، تحریم، رزمایش و گزارش آژانس نارنجی؛ بیانیه، مذاکره و تحلیل زرد. خبرهای بیرون از میدان اصلی (مثل کرانه باختری یا سیاست داخلی اسرائیل) هم می‌آیند، ولی امتیاز و وزنشان کمتر است. هر خبر به زبان خودش خوانده می‌شود: خبرهای فارسی با قواعد فارسی روی متن اصلی، و خبرهای خارجی با قواعد انگلیسی؛ ترجمه فقط برای نمایش و برای تطبیق خبرهای فارسی و خارجی با هم است.',
      method2: 'میانگین ساده نیست: رویدادهای جدی‌تر وزن نمایی بیشتری دارند تا یک حمله زیر سی خبر روتین گم نشود، خبرهای تازه سنگین‌ترند (نیمه‌عمر ۶ ساعت)، و هر رویداد فقط یک بار شمرده می‌شود هر چند رسانه گزارشش کنند. اعتبار منبع هم اثر دارد.',
      method3: 'شاخص نهایی ۷۰٪ اخبار و ۳۰٪ سیگنال‌های عینی است: تردد و حوادث تنگه هرمز، و سطح ریسک و هشدارهای رسمی تازه برای حریم هوایی کشورهای منطقه. این یک نشانگر است، نه پیش‌بینی.',
      method4: 'گزارش‌های چند رسانه فقط وقتی زیر یک تیتر می‌آیند که تیترهایشان خیلی شبیه باشد و در نوع رویداد، مکان، زمان (حداکثر ۴ ساعت بعد از اولین گزارش برای رویدادها و ۱۰ ساعت برای اظهارات)، گوینده، رسانه‌ی نقل‌شده و عددها هم یکی باشند. زمان هر خبر، زمان اولین گزارش آن است.',
      mkH: 'بازار', lastTrade: 'آخرین معامله', vsPrev: 'نسبت به معامله قبل', vsDay: 'نسبت به دیروز',
      dayHL: 'بیشترین و کمترین امروز', trades: 'تعداد معامله امروز', toman: 'تومان', stale: 'داده قدیمی است',
      usdNote: 'فقط پست‌های «معامله شد ✅» کانال خوانده می‌شود؛ قیمت‌های خرید و فروش نادیده گرفته می‌شوند.',
      refresh: 'دلار، بازارها و اخبار حدوداً هر ۵ دقیقه به‌روز می‌شوند؛ گاهی گیت‌هاب اجرا را چند دقیقه دیرتر شروع می‌کند.', nextNews: 'به‌روزرسانی بعدی اخبار: حدود {n} دقیقه دیگر',
      settings: 'تنظیمات', lang: 'زبان', sound: 'صدای هشدار خبر خیلی مهم', lock: 'قفل با رمز',
      lockSet: 'تنظیم رمز', lockOff: 'برداشتن رمز', pinEnter: 'رمز چهاررقمی را وارد کن', pinNew: 'رمز جدید را وارد کن',
      pinAgain: 'دوباره وارد کن', pinWrong: 'رمز اشتباه است', pinMismatch: 'دو رمز یکی نبود؛ دوباره',
      tg: 'هشدار تلگرام', tgOn: 'فعال', tgWait: 'منتظر /start در ربات', tgOff: 'غیرفعال',
      tgHelp: 'توکن ربات را در تنظیمات ریپو (Secrets) با نام TELEGRAM_BOT_TOKEN ثبت کن و به ربات ‎/start بفرست.',
      srcH: 'وضعیت منابع', srcSum: '{ok} از {n} منبع در آخرین اجرا جواب دادند', srcGn: 'از مسیر گوگل‌نیوز', srcBing: 'از مسیر بینگ', srcTg: 'از کانال تلگرام', srcFail: 'بدون پاسخ',
      items: '{n} خبر', methodH: 'روش محاسبه', about: 'زمان‌بندی', filtersH: 'فیلترها', sortBy: 'ترتیب',
      sortTime: 'جدیدترین', sortSev: 'مهم‌ترین', topics: 'موضوع', countries: 'کشورها', people: 'افراد',
      apply: 'نمایش {n} خبر', layNews: 'خبرها',
      avH: 'هشدارهای حریم هوایی منطقه', avNew: 'هشدار تازه', avUntil: 'تا {d}', avIssued: 'صدور {d}', avOngoing: 'بدون تاریخ پایان', avMore: 'صفحه کامل در Safe Airspace',
      avNote: 'سطح ریسک هر کشور و هشدارهای رسمی در جریان (نوتام کشورها، بولتن‌های EASA و هشدارهای FAA) از Safe Airspace؛ حدوداً هر ساعت به‌روز می‌شود. روی هر کشور بزن تا جزئیات باز شود.', avNone: 'داده هشدارهای هوایی هنوز نرسیده.',
      hzH: 'تردد تنگه هرمز', hzUnit: 'عبور در روز (میانگین ۷ روز)', hzPre: 'عادی پیش از بحران: {n}', hzPct: '{n}٪ حالت عادی',
      hzLag: 'داده IMF PortWatch تا {d}؛ حدود یک هفته تأخیر دارد.', hzTank: 'نفتکش: {a} در روز (عادی {b})', babH: 'باب‌المندب',
      warnH: 'هشدارهای دریانوردی فعال', warnNone: 'هشدار فعالی برای منطقه نیست.',
      liveSea: 'نقشه زنده کشتی‌ها', placeH: 'خبرهای {p}',
      xGeo: 'سیاسی و نظامی', xEcon: 'نفت و طلا', xNote: 'ایکس API رایگان ندارد؛ این‌ها پست‌های حساب‌های معتبرند که رسانه‌های معتبر نقل کرده‌اند، به‌علاوه پست‌های تروث‌سوشال ترامپ.',
      xEmpty: 'هنوز پستی از حساب‌های منتخب ثبت نشده. با هر به‌روزرسانی اضافه می‌شود.', cites: '{n} رسانه نقل کرده', openX: 'باز کردن', telegram: 'تلگرام',
      newRed: 'خبر خیلی مهم جدید', refreshed: 'به‌روز شد', loading: 'در حال دریافت…', stories: '{n} خبر',
      tEcon: 'اکونومیست', ecIssue: 'شماره‌ی {d}', ecCount: '{n} مطلب برگزیده', ecImpact: 'اثرات',
      ecRead: 'متن کامل در سایت اکونومیست', ecPage: 'صفحه‌ی {n}', ecEmpty: 'این هفته در اکونومیست مطلبی برای دسته‌ی «{c}» نبود.',
      ecTierEmpty: 'با این سطح‌ها مطلبی نیست.', ecNone: 'هنوز شماره‌ای از اکونومیست ثبت نشده.',
      ecNote: 'خلاصه‌ها برداشت آزاد از مقاله‌هاست، نه ترجمه‌ی متن کامل. تصویرها پیش‌نمایش خود سایت اکونومیست‌اند.',
      cats: { tanker: 'سوخت‌رسان', isr: 'شناسایی', bomber: 'بمب‌افکن', transport: 'ترابری', other: 'سایر' }
    },
    en: {
      app: 'Daily Brief', usd: 'Tehran dollar', brent: 'Brent', gold: 'Gold oz', index: 'Escalation index',
      z0: 'Calm', z1: 'Moderate', z2: 'High', z3: 'Critical', breaking: 'Breaking',
      tNews: 'News', tMap: 'Map & signals', tX: 'X posts', r24: '24 hours', rWeek: 'Week',
      all: 'All', red: 'Critical', orange: 'Important', yellow: 'Lower',
      now: 'just now', minAgo: '{n} min ago', hAgo: '{n} h ago', updated: '{t}',
      sources: '{n} sources', moreSrc: '+{n}', fresh: 'New', sev: 'Severity {n}',
      firstRep: 'First reported {t}', lastRep: 'Last update {t}',
      mt: 'Machine translated', showOrig: 'Show original', showTr: 'Show translation', srcList: 'Sources for this story',
      tagsH: 'Topics, places and people', searchPh: 'Search stories and sources',
      empty: 'No stories match these filters.', clear: 'Clear filters', showYellow: 'Show lower-importance stories',
      storiesH: 'News stories', fullStory: 'Full story', close: 'Close', srcLabel: 'Source:', prev: 'Previous', next: 'Next',
      noData: 'No data yet. The engine runs every few minutes; check back shortly.',
      offline: 'You are offline; showing the last saved data.',
      lightsH: 'Warning lights', lightsOn: '{n} lights on:', lightsWatch: 'No lights on; {n} on watch',
      lightsOff: 'All lights are off', on: 'On', watch: 'Watch', off: 'Off',
      lightsNote: 'On means an event in the last 24 hours; watch means 24–72 hours ago.',
      noEvidence: 'Nothing in the last three days.',
      d24: 'vs 24h ago', idxH: 'Escalation index', idxNews: 'News', idxSig: 'Air & sea signals',
      idxWeek: 'Last seven days', idxMethod: 'How it is calculated',
      method1: 'Each story scores 0–100 by event type: direct military action, Hormuz incidents, ultimatums, airspace closures and carrier or bomber deployments are red; military aircraft and tanker movements, threats, sanctions, exercises and IAEA findings orange; statements, talks and analysis yellow. Stories outside the main theatre (such as the West Bank or Israeli domestic politics) still appear, with lower scores and less weight. Each report is read in its own language: Persian reports by Persian rules on the original text, foreign ones by English rules; translations are only for display and for matching Persian and foreign reports.',
      method2: 'It is not a plain average: serious events weigh exponentially more so one strike is not drowned out by thirty routine stories, recent events weigh more (6-hour half-life), and each event counts once however many outlets report it. Source reliability also counts.',
      method3: 'The index is 70% news and 30% objective signals: Hormuz traffic and incidents, and the risk level and fresh official warnings for the region\'s airspace. It is an indicator, not a forecast.',
      method4: 'Reports from several outlets share a headline only when the headlines are very close and they also agree on the kind of event, the place, the time (within 4 hours of the first report for events, 10 hours for statements), the speaker, the outlet being cited and the figures. Each story is timed by its first report.',
      mkH: 'Markets', lastTrade: 'Last trade', vsPrev: 'vs previous trade', vsDay: 'vs yesterday',
      dayHL: 'Today high / low', trades: 'Trades today', toman: 'toman', stale: 'Data is stale',
      usdNote: 'Only "traded ✅" posts are read; buy and sell quotes are ignored.',
      refresh: 'Dollar, markets and news refresh about every 5 minutes; GitHub sometimes starts a run a few minutes late.', nextNews: 'Next news update in about {n} min',
      settings: 'Settings', lang: 'Language', sound: 'Sound for critical stories', lock: 'Passcode lock',
      lockSet: 'Set passcode', lockOff: 'Remove passcode', pinEnter: 'Enter your 4-digit passcode', pinNew: 'Enter a new passcode',
      pinAgain: 'Enter it again', pinWrong: 'Wrong passcode', pinMismatch: 'They did not match; try again',
      tg: 'Telegram alerts', tgOn: 'On', tgWait: 'Waiting for /start', tgOff: 'Off',
      tgHelp: 'Save the bot token as the repository secret TELEGRAM_BOT_TOKEN, then send /start to the bot.',
      srcH: 'Source status', srcSum: '{ok} of {n} sources responded in the last run', srcGn: 'via Google News', srcBing: 'via Bing News', srcTg: 'via its Telegram channel', srcFail: 'no response',
      items: '{n} items', methodH: 'Method', about: 'Schedule', filtersH: 'Filters', sortBy: 'Sort',
      sortTime: 'Latest', sortSev: 'Most important', topics: 'Topic', countries: 'Countries', people: 'People',
      apply: 'Show {n} stories', layNews: 'Stories',
      avH: 'Regional airspace warnings', avNew: 'New warning', avUntil: 'until {d}', avIssued: 'issued {d}', avOngoing: 'no end date', avMore: 'Full page on Safe Airspace',
      avNote: 'Each country\'s risk level and the official warnings in force (state NOTAMs, EASA bulletins, FAA advisories) from Safe Airspace; refreshed about hourly. Tap a country for details.', avNone: 'No airspace data yet.',
      hzH: 'Strait of Hormuz traffic', hzUnit: 'transits per day (7-day avg)', hzPre: 'Pre-crisis normal: {n}', hzPct: '{n}% of normal',
      hzLag: 'IMF PortWatch data through {d}; about a week behind.', hzTank: 'Tankers: {a}/day (normal {b})', babH: 'Bab el-Mandeb',
      warnH: 'Active navigational warnings', warnNone: 'No active warnings for the region.',
      liveSea: 'Live ship map', placeH: 'Stories: {p}',
      xGeo: 'Politics & military', xEcon: 'Oil & gold', xNote: 'X has no free API; these are posts from credible accounts cited by reputable media, plus Trump\'s Truth Social posts.',
      xEmpty: 'No posts from the selected accounts yet. They are added with each update.', cites: 'cited by {n} outlets', openX: 'Open', telegram: 'Telegram',
      newRed: 'New critical story', refreshed: 'Updated', loading: 'Loading…', stories: '{n} stories',
      tEcon: 'Economist', ecIssue: 'Issue of {d}', ecCount: '{n} selected articles', ecImpact: 'Why it matters',
      ecRead: 'Read on economist.com', ecPage: 'p. {n}', ecEmpty: 'No Economist article for “{c}” this week.',
      ecTierEmpty: 'No articles at these levels.', ecNone: 'No Economist issue yet.',
      ecNote: 'Summaries are free paraphrases, not translations. Pictures are the site’s own previews.',
      cats: { tanker: 'Tankers', isr: 'ISR', bomber: 'Bombers', transport: 'Transport', other: 'Other' }
    }
  };
  var TOPICS = { military: ['نظامی', 'Military'], nuclear: ['هسته‌ای', 'Nuclear'], maritime: ['هرمز و دریا', 'Hormuz & sea'],
    air: ['هوایی', 'Air & airspace'], diplomacy: ['دیپلماسی', 'Diplomacy'], economy: ['تحریم و اقتصاد', 'Sanctions & economy'],
    statement: ['بیانات', 'Statements'] };
  var COUNTRIES = { us: ['آمریکا', 'US'], il: ['اسرائیل', 'Israel'], ir: ['ایران', 'Iran'], gulf: ['خلیج فارس', 'Persian Gulf states'],
    iraq: ['عراق', 'Iraq'], yemen: ['یمن', 'Yemen'], lebanon: ['لبنان', 'Lebanon'], syria: ['سوریه', 'Syria'], europe: ['اروپا', 'Europe'],
    russia: ['روسیه', 'Russia'], china: ['چین', 'China'], un: ['سازمان ملل و آژانس', 'UN & IAEA'] };
  var PEOPLE = { trump: ['ترامپ', 'Trump'], vance: ['ونس', 'Vance'], rubio: ['روبیو', 'Rubio'], bessent: ['بسنت', 'Bessent'],
    hegseth: ['هگست', 'Hegseth'], witkoff: ['ویتکاف', 'Witkoff'], us_mil: ['فرماندهان نظامی آمریکا', 'US military chiefs'],
    il_pm: ['نخست‌وزیر اسرائیل', 'Israeli PM'], il_def: ['وزیر جنگ اسرائیل', 'Israeli defense minister'],
    idf_chief: ['رئیس ستاد ارتش اسرائیل', 'IDF chief'], ir_leader: ['رهبر ایران', 'Iran\'s Supreme Leader'],
    ir_pres: ['رئیس‌جمهور ایران', 'Iran\'s President'], ir_fm: ['وزیر خارجه ایران', 'Iran\'s FM'],
    ir_snsc: ['شورای عالی امنیت ملی', 'Iran\'s Security Council'], irgc_cmd: ['فرماندهان سپاه', 'IRGC commanders'],
    ir_army: ['ستاد کل نیروهای مسلح', 'Iran\'s armed forces chief'], ghalibaf: ['قالیباف', 'Ghalibaf'],
    ir_spox: ['سخنگوی وزارت خارجه ایران', 'Iran FM spokesperson'], grossi: ['گروسی', 'Grossi'], guterres: ['گوترش', 'Guterres'],
    mbs: ['بن‌سلمان', 'MBS'], sa_fm: ['وزیر خارجه عربستان', 'Saudi FM'], qa: ['مقامات قطر', 'Qatari leaders'],
    om: ['وزیر خارجه عمان', 'Omani FM'], uae: ['مقامات امارات', 'UAE leaders'], houthi_l: ['رهبر حوثی‌ها', 'Houthi leader'],
    hzb_l: ['دبیرکل حزب‌الله', 'Hezbollah chief'], putin: ['پوتین', 'Putin'], xi: ['شی جین‌پینگ', 'Xi Jinping'],
    e3: ['رهبران اروپایی', 'European leaders'] };
  var LAMP_ICON = { strike: 'crosshair', hormuz: 'tanker', airspace: 'planeoff', deploy: 'ship',
    evac: 'exit', ultimatum: 'hourglass', oil: 'drop' };
  var TIER_ORDER = ['red', 'orange', 'yellow'];
  // which importance levels the feed shows; each can be switched on or off (lower-importance ones are off at first)
  var DEF_TIERS = { red: true, orange: true, yellow: false };
  function savedTiers(key, def) {
    var v = store.get(key || 'tiers', null), out = {};
    def = def || DEF_TIERS;
    TIER_ORDER.forEach(function (k) { out[k] = v && typeof v[k] === 'boolean' ? v[k] : def[k]; });
    return out.red || out.orange || out.yellow ? out : Object.assign({}, def);
  }
  // the Economist tab: five fixed categories (one may be empty in a given week), sections of the magazine
  var EC_CATS = ['pol', 'gold', 'oil', 'money', 'ai'];
  var EC_CAT = { pol: ['سیاسی و نظامی', 'Politics & military', 'shield'], gold: ['طلا', 'Gold', 'gold'], oil: ['نفت', 'Oil', 'drop'],
    money: ['پولی و بانکی', 'Money & banking', 'bank'], ai: ['هوش مصنوعی', 'AI', 'chip'] };
  var EC_SEC = { leaders: ['سرمقاله', 'Leaders'], briefing: ['گزارش ویژه', 'Briefing'], wtw: ['رویدادهای هفته', 'The world this week'],
    us: ['آمریکا', 'United States'], americas: ['قاره‌ی آمریکا', 'The Americas'], asia: ['آسیا', 'Asia'], china: ['چین', 'China'],
    mea: ['خاورمیانه و آفریقا', 'Middle East & Africa'], europe: ['اروپا', 'Europe'], britain: ['بریتانیا', 'Britain'],
    intl: ['بین‌الملل', 'International'], business: ['کسب‌وکار', 'Business'], finance: ['مالی و اقتصاد', 'Finance & economics'],
    science: ['علم و فناوری', 'Science & technology'], culture: ['فرهنگ', 'Culture'] };
  var EC_TIERS = { red: true, orange: true, yellow: true };

  // ------------------------------------------------------------------ state
  var S = {
    lang: store.get('lang', 'fa'), tab: 'news', range: store.get('range', '24h'), tiers: savedTiers(), topic: null, ctry: null,
    ppl: null, sort: store.get('sort', 'time'), q: '', xseg: 'geo', layers: { news: true },
    econCat: store.get('econCat', 'pol'), econTiers: savedTiers('econTiers', EC_TIERS),
    sound: store.get('sound', true), d: { ticker: null, signals: null, news24: null, newsWeek: null, x: null, health: null, econ: null },
    seen: null, newIds: {}, shown: 0, list: [], gaugeSet: false, mapData: null, offline: false, origX: {}
  };
  var seenArr = store.get('seen', null);
  S.seen = seenArr ? new Set(seenArr) : null;      // null = very first visit: nothing is "new"

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function L() { return S.lang; }
  function t(k, vars) {
    var s = (T[L()][k] !== undefined ? T[L()][k] : T.fa[k]) || k;
    if (vars) for (var v in vars) s = s.split('{' + v + '}').join(vars[v]);
    return s;
  }
  function pick(pair) { return pair ? pair[L() === 'fa' ? 0 : 1] : ''; }
  function ic(name, cls) { return '<svg class="ic ' + (cls || '') + '"><use href="#i-' + name + '"/></svg>'; }

  // ------------------------------------------------------------------ formatting
  function nfmt(n, d) {
    if (n == null || isNaN(n)) return '—';
    d = d || 0;
    return new Intl.NumberFormat(L() === 'fa' ? 'fa-IR' : 'en-US', { maximumFractionDigits: d, minimumFractionDigits: d }).format(n);
  }
  function pctStr(n, d) {
    if (n == null || isNaN(n)) return '';
    var s = nfmt(Math.abs(n), d == null ? 2 : d);
    return (L() === 'fa' ? s + '٪' : s + '%');
  }
  function nowS() { return Date.now() / 1000; }
  function ago(ts) {
    var s = nowS() - ts;
    if (s < 60) return t('now');
    if (s < 3600) return t('minAgo', { n: nfmt(Math.round(s / 60)) });
    if (s < 86400) return t('hAgo', { n: nfmt(Math.floor(s / 3600)) });
    return dshort(ts);
  }
  var LOC = function () { return L() === 'fa' ? 'fa-IR-u-ca-persian' : 'en-GB'; };
  function clock(ts) { return new Intl.DateTimeFormat(LOC(), { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Tehran' }).format(new Date(ts * 1000)); }
  function dshort(ts) { return new Intl.DateTimeFormat(LOC(), { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Asia/Tehran' }).format(new Date(ts * 1000)); }
  function dlong(ts) { return new Intl.DateTimeFormat(LOC(), { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Tehran' }).format(new Date(ts * 1000)); }
  function dtime(ts) { return dshort(ts) + '، ' + clock(ts); }
  function dayKey(ts) { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tehran' }).format(new Date(ts * 1000)); }
  function isoDate(s) { var d = new Date(s + 'T12:00:00Z'); return new Intl.DateTimeFormat(LOC(), { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(d); }
  function norm(s) { return String(s || '').toLowerCase().replace(/[يى]/g, 'ی').replace(/ك/g, 'ک').replace(/[‌ً-ٟ]/g, ' ').replace(/\s+/g, ' '); }

  // gauge colour along the yellow → orange → red ramp
  function heat(v) {
    var stops = [[0, [255, 210, 63]], [52, [255, 138, 42]], [100, [255, 61, 87]]];
    v = Math.max(0, Math.min(100, v));
    for (var i = 0; i < stops.length - 1; i++) {
      var a = stops[i], b = stops[i + 1];
      if (v <= b[0]) {
        var f = (v - a[0]) / (b[0] - a[0]);
        return a[1].map(function (c, j) { return Math.round(c + (b[1][j] - c) * f); });
      }
    }
    return stops[2][1];
  }
  function rgba(c, a) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }

  // ------------------------------------------------------------------ data
  function getJSON(name, fresh) {
    var url = BASE + name + '?t=' + Math.floor(Date.now() / (fresh ? 1000 : 60000));
    var ctl = 'AbortController' in window ? new AbortController() : null;
    var tm = setTimeout(function () { if (ctl) ctl.abort(); }, 15000);
    return fetch(url, { cache: 'no-store', signal: ctl ? ctl.signal : undefined }).then(function (r) {
      clearTimeout(tm);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }, function (e) { clearTimeout(tm); throw e; });
  }
  var KEYS = { ticker: 'ticker.json', signals: 'signals.json', news24: 'news_24h.json', newsWeek: 'news_week.json', x: 'x.json', health: 'health.json',
    stories: 'stories.json', econ: 'economist.json' };
  function load(keys, fresh) {
    return Promise.all(keys.map(function (k) {
      return getJSON(KEYS[k], fresh).then(function (j) { return [k, j, null]; }, function (e) { return [k, null, e]; });
    })).then(function (res) {
      var changed = {}, failed = 0;
      res.forEach(function (r) {
        if (r[1]) {
          var old = S.d[r[0]];
          if (!old || old.updated !== r[1].updated) changed[r[0]] = true;
          S.d[r[0]] = r[1];
          if (r[0] !== 'newsWeek' && r[0] !== 'health') store.set('cache.' + r[0], r[1]);
        } else failed++;
      });
      S.offline = failed === res.length;
      return changed;
    });
  }
  function bootCache() {
    ['ticker', 'signals', 'news24', 'x', 'stories', 'econ'].forEach(function (k) {
      var c = store.get('cache.' + k, null);
      if (c) S.d[k] = c;
    });
  }

  // ------------------------------------------------------------------ language
  function applyLang() {
    var html = document.documentElement;
    html.lang = L();
    html.dir = L() === 'fa' ? 'rtl' : 'ltr';
    $$('[data-t]').forEach(function (el) { el.textContent = t(el.getAttribute('data-t')); });
    $('#searchInput').placeholder = t('searchPh');
    document.title = t('app');
  }

  // ------------------------------------------------------------------ header & markets
  function newsUpdated() {
    var n = S.d.news24 && S.d.news24.updated;
    var s = S.d.signals && S.d.signals.updated;
    return Math.max(n || 0, s || 0);
  }
  function renderHeader() {
    var u = newsUpdated();
    var el = $('#updated');
    if (!u) { el.innerHTML = '<i class="live off"></i>' + esc(t('loading')); return; }
    var age = nowS() - u;
    var cls = S.offline ? 'off' : age < 50 * 60 ? '' : age < 3 * 3600 ? 'stale' : 'off';
    el.innerHTML = '<i class="live ' + cls + '"></i>' + esc(S.offline ? t('offline').split('؛')[0].split(';')[0] : ago(u));
    var idx = S.d.signals && S.d.signals.index;
    $('#miniIdx').innerHTML = idx ? '<i style="--v:' + idx.value + '%"></i>' + nfmt(idx.value) : '';
    var usd = S.d.ticker && S.d.ticker.dollar;
    $('#miniUsd').textContent = usd && usd.price ? nfmt(usd.price) : '';
  }
  function chgHtml(v, pctv, digits) {
    if (pctv == null || isNaN(pctv)) return '';
    var dir = pctv > 0 ? 'up' : pctv < 0 ? 'down' : '';
    return '<span class="mk-c ' + dir + '">' + (dir ? ic(dir) : '') + pctStr(pctv, digits) + '</span>';
  }
  function setMk(id, label, value, pctv, stale) {
    var el = $(id);
    el.classList.toggle('stale', !!stale);
    el.innerHTML = '<span class="mk-l">' + esc(label) + '</span><b class="mk-v num">' + value + '</b>' + (chgHtml(null, pctv) || '<span class="mk-c">&nbsp;</span>');
  }
  function renderMarkets() {
    var tk = S.d.ticker;
    if (!tk) return;
    var u = tk.dollar || {};
    if (u.price) setMk('#mkUsd', t('usd'), nfmt(u.price), u.chgDayPct, u.status !== 'ok');
    else setMk('#mkUsd', t('usd'), '—', null, true);
    var b = tk.brent || {}, g = tk.gold || {};
    setMk('#mkBrent', t('brent'), b.price ? (L() === 'en' ? '$' : '') + nfmt(b.price, 2) : '—', b.chgPct, b.status !== 'ok');
    setMk('#mkGold', t('gold'), g.price ? (L() === 'en' ? '$' : '') + nfmt(g.price, 0) : '—', g.chgPct, g.status !== 'ok');
  }

  // ------------------------------------------------------------------ gauge
  function renderGauge() {
    var idx = S.d.signals && S.d.signals.index;
    var wrap = $('#gauge'), bar = $('#gaugeBar');
    if (!idx) { $('#gaugeNum').textContent = '—'; return; }
    var v = idx.value, c = heat(v);
    wrap.style.setProperty('--zc', rgba(c, 1));
    wrap.style.setProperty('--zone-glow', rgba(c, 0.2));
    wrap.style.setProperty('--glow-x', (L() === 'fa' ? 100 - v : v) + '%');
    bar.style.setProperty('--needle-glow', rgba(c, 0.6));
    if (!S.gaugeSet) {
      bar.style.setProperty('--v', '0%');
      requestAnimationFrame(function () { requestAnimationFrame(function () { bar.style.setProperty('--v', v + '%'); }); });
      S.gaugeSet = true;
    } else bar.style.setProperty('--v', v + '%');
    $('#gaugeNum').textContent = nfmt(v);
    var zl = L() === 'fa' ? idx.label_fa : idx.label_en;
    $('#gaugeZone').innerHTML = '<i></i>' + esc(zl);
    var d = idx.delta24, de = $('#gaugeDelta');
    if (d == null || d === 0) { de.className = 'gauge-delta'; de.innerHTML = ''; }
    else { de.className = 'gauge-delta ' + (d > 0 ? 'up' : 'down'); de.innerHTML = ic(d > 0 ? 'up' : 'down') + nfmt(Math.abs(d)); de.title = t('d24'); }
  }

  // ------------------------------------------------------------------ lamps
  function lightsList() { return (S.d.signals && S.d.signals.lights) || []; }
  function renderLamps() {
    var ls = lightsList();
    var box = $('#lamps');
    if (!ls.length) {
      box.innerHTML = Object.keys(LAMP_ICON).map(function (k) { return '<button class="lamp" data-a="lights" data-state="off">' + ic(LAMP_ICON[k]) + '</button>'; }).join('');
      return;
    }
    // the lamps alone; tapping any of them opens the list with names and evidence
    box.innerHTML = ls.map(function (l) {
      return '<button class="lamp" data-a="lights" data-state="' + l.state + '" aria-label="' + esc(L() === 'fa' ? l.fa : l.en) + '">' + ic(LAMP_ICON[l.id] || 'alert') + '</button>';
    }).join('');
  }

  // ------------------------------------------------------------------ flash
  function renderFlash() {
    var d = S.d.news24, box = $('#flash');
    var reds = d ? d.clusters.filter(function (c) { return c.tier === 'red' && nowS() - c.t < 6 * 3600 && c.flags.indexOf('denial') < 0; }) : [];
    reds.sort(function (a, b) { return b.t - a.t; });
    reds = reds.slice(0, 6);
    if (!reds.length) { box.hidden = true; return; }
    box.hidden = false;
    var one = reds.map(function (c) { return '<button data-story="' + c.id + '">' + esc(txt(c).ti) + '</button>'; }).join('');
    var tr = $('#flashTrack');
    tr.innerHTML = one + one;
    var len = reds.reduce(function (a, c) { return a + txt(c).ti.length; }, 0);
    tr.style.setProperty('--dur', Math.max(22, Math.round(len * 0.32)) + 's');
  }

  // ------------------------------------------------------------------ stories
  function txt(c) {
    var o = L() === 'fa' ? c.fa : c.en;
    if (!o || !o.ti) o = L() === 'fa' ? c.en : c.fa;
    return o || { ti: '', su: '' };
  }
  function srcName(s) { return L() === 'fa' ? (s.nf || s.n) : (s.n || s.nf); }
  function currentNews() { return S.range === 'week' ? S.d.newsWeek : S.d.news24; }
  function filtered(ignoreTier) {
    var d = currentNews();
    var list = d ? d.clusters.slice() : [];
    if (!ignoreTier) list = list.filter(function (c) { return S.tiers[c.tier]; });
    if (S.topic) list = list.filter(function (c) { return c.topics.indexOf(S.topic) >= 0; });
    if (S.ctry) list = list.filter(function (c) { return c.ctry.indexOf(S.ctry) >= 0; });
    if (S.ppl) list = list.filter(function (c) { return c.ppl.indexOf(S.ppl) >= 0; });
    if (S.q) {
      var q = norm(S.q);
      list = list.filter(function (c) {
        return norm(c.fa.ti + ' ' + c.fa.su + ' ' + c.en.ti + ' ' + c.en.su + ' ' + c.src.map(function (s) { return s.n + ' ' + s.nf; }).join(' ')).indexOf(q) >= 0;
      });
    }
    // a story's time is its first report; later reports from other outlets don't move it up
    if (S.sort === 'sev') list.sort(function (a, b) { return b.sev - a.sev || b.t - a.t; });
    else list.sort(function (a, b) { return b.t - a.t; });
    return list;
  }
  function metaHtml(c) {
    var first = c.src[0] || { n: '', nf: '' };
    var more = c.ns > 1 ? '<span class="more">' + ic('users') + nfmt(c.ns) + '</span>' : '';
    var fresh = S.newIds[c.id] ? '<span class="fresh">' + esc(t('fresh')) + '</span>' : '';
    return '<div class="s-meta"><span class="src">' + esc(srcName(first)) + '</span>' + more + fresh + '<span class="time">' + esc(ago(c.t)) + '</span></div>';
  }
  // a broken image collapses its frame instead of leaving an empty box
  window.imgFail = function (img) {
    var box = img.parentNode;
    img.remove();
    if (!box || box.querySelector('.s-play')) return;
    if (box.classList.contains('s-media')) box.classList.add('s-noimg');
    else if (box.classList.contains('s-thumb')) { var card = box.parentNode; box.remove(); if (card) card.classList.add('noimg'); }
  };
  function mediaInner(c, cls) {
    var play = c.vid ? '<div class="s-play"><span>' + ic('play') + '</span></div>' : '';
    if (c.img) return '<img loading="lazy" decoding="async" referrerpolicy="no-referrer" src="' + esc(c.img) + '" alt="" onerror="imgFail(this)">' + play;
    return play;
  }
  function cardRed(c) {
    var x = txt(c);
    var media = c.img || c.vid
      ? '<div class="s-media">' + mediaInner(c) + '<span class="s-tag"><i class="t-dot red"></i>' + esc(t('red')) + '</span></div>'
      : '<div class="s-media s-noimg">' + ic('image') + '<span class="s-tag"><i class="t-dot red"></i>' + esc(t('red')) + '</span></div>';
    return '<article class="story story--red' + (S.newIds[c.id] ? ' is-new' : '') + '" data-story="' + c.id + '">' + media +
      '<div class="s-body"><h3 class="s-title">' + esc(x.ti) + '</h3>' + (x.su ? '<p class="s-sum">' + esc(x.su) + '</p>' : '') + metaHtml(c) + '</div></article>';
  }
  function cardOrange(c) {
    var x = txt(c);
    var thumb = c.img || c.vid ? '<div class="s-thumb">' + mediaInner(c) + '</div>' : '';
    return '<article class="story story--orange' + (thumb ? '' : ' noimg') + (S.newIds[c.id] ? ' is-new' : '') + '" data-story="' + c.id + '">' +
      '<div><h3 class="s-title">' + esc(x.ti) + '</h3>' + metaHtml(c) + '</div>' + thumb + '</article>';
  }
  function cardYellow(c) {
    var x = txt(c);
    return '<article class="story story--yellow' + (S.newIds[c.id] ? ' is-new' : '') + '" data-story="' + c.id + '"><i class="ydot"></i>' +
      '<div><h3 class="s-title">' + esc(x.ti) + '</h3>' + metaHtml(c) + '</div></article>';
  }
  function card(c) { return c.tier === 'red' ? cardRed(c) : c.tier === 'orange' ? cardOrange(c) : cardYellow(c); }

  function renderChips() {
    var base = filtered(true);
    var counts = { red: 0, orange: 0, yellow: 0 };
    base.forEach(function (c) { counts[c.tier]++; });
    var h = '';
    TIER_ORDER.forEach(function (k) {
      var on = !!S.tiers[k];
      h += '<button class="chip chip--tier' + (on ? ' on' : '') + '" data-tier="' + k + '" aria-pressed="' + on + '">' +
        '<i class="t-dot ' + k + '"></i>' + esc(t(k)) + ' <b>' + nfmt(counts[k]) + '</b></button>';
    });
    $('#chips').innerHTML = h;
    $('#filterDot').hidden = !(S.topic || S.ctry || S.ppl || S.sort === 'sev');
  }

  var PAGE = 25;
  function renderFeed(keepScroll) {
    var feed = $('#feed');
    var d = currentNews();
    if (!d) {
      if (S.range === 'week' && !S.d.newsWeek) {
        feed.innerHTML = skeleton();
        load(['newsWeek']).then(function () { renderChips(); renderFeed(); });
        return;
      }
      feed.innerHTML = S.offline || S.d.news24 === null && S.loaded ? '<div class="empty">' + ic('offline') + '<p>' + esc(S.offline ? t('offline') : t('noData')) + '</p></div>' : skeleton();
      return;
    }
    S.list = filtered();
    if (!S.list.length) {
      var y = !S.tiers.yellow && filtered(true).some(function (c) { return c.tier === 'yellow'; })
        ? '<button data-tier="yellow">' + esc(t('showYellow')) + '</button>' : '';
      feed.innerHTML = '<div class="empty">' + ic('search') + '<p>' + esc(t('empty')) + '</p>' + y +
        '<button data-a="clear">' + esc(t('clear')) + '</button></div>';
      return;
    }
    S.shown = 0;
    feed.innerHTML = '';
    if (!keepScroll && S.tab === 'news') { /* keep position on refresh */ }
    more();
  }
  function more() {
    var feed = $('#feed');
    var part = S.list.slice(S.shown, S.shown + PAGE);
    if (!part.length) return;
    var h = '', lastDay = S.shown ? dayKey(S.list[S.shown - 1].t) : null;
    part.forEach(function (c) {
      if (S.sort === 'time' && S.range === 'week') {
        var dk = dayKey(c.t);
        if (dk !== lastDay) { h += '<div class="day-sep">' + esc(dlong(c.t)) + '</div>'; lastDay = dk; }
      }
      h += card(c);
    });
    feed.insertAdjacentHTML('beforeend', h);
    S.shown += part.length;
  }
  function skeleton() { return '<div class="skel skel-card"></div><div class="skel skel-row"></div><div class="skel skel-row"></div><div class="skel skel-row"></div>'; }

  // ------------------------------------------------------------------ story tray & viewer
  // Up to ten orange and yellow stories about Iran and Israel or the US, chosen by the engine every two hours.
  // Which ones this browser has opened is remembered here only: blue ring = not seen yet, grey = seen.
  var STORY_MS = 7000;
  var SV = null;
  S.storySeen = new Set(store.get('storySeen', []));
  function storyList() { return (S.d.stories && S.d.stories.stories) || []; }
  function markSeen(id) {
    if (S.storySeen.has(id)) return;
    S.storySeen.add(id);
    store.set('storySeen', Array.from(S.storySeen).slice(-300));
  }
  window.styFail = function (img) {
    var f = img.parentNode;
    img.remove();
    if (f && !f.classList.contains('noimg')) { f.classList.add('noimg'); f.insertAdjacentHTML('afterbegin', ic('news', 'sty-ic')); }
  };
  function renderStories() {
    var box = $('#stories'), list = storyList();
    if (!list.length) { box.hidden = true; box.innerHTML = ''; return; }
    box.hidden = false;
    box.setAttribute('aria-label', t('storiesH'));
    box.innerHTML = list.map(function (c, i) {
      var x = txt(c), seen = S.storySeen.has(c.id);
      var pic = c.img ? '<img loading="lazy" decoding="async" referrerpolicy="no-referrer" src="' + esc(c.img) + '" alt="" onerror="styFail(this)">'
        : ic('news', 'sty-ic');
      return '<button class="sty' + (seen ? ' seen' : '') + '" role="listitem" data-sty="' + i + '" aria-label="' + esc(x.ti) + '">' +
        '<span class="sty-f t-' + c.tier + (c.img ? '' : ' noimg') + '">' + pic + '<i class="sty-d t-dot ' + c.tier + '"></i>' +
        '<span class="sty-t" dir="auto">' + esc(x.ti) + '</span></span></button>';
    }).join('');
  }
  function openStories(i) {
    var list = storyList();
    if (!list.length || SV) return;
    var el = document.createElement('div');
    el.className = 'sv';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-label', t('storiesH'));
    el.innerHTML = '<div class="sv-bg" id="svBg"></div>' +
      '<div class="sv-top"><div class="sv-bars">' + list.map(function () { return '<i><b></b></i>'; }).join('') + '</div><div class="sv-head" id="svHead"></div></div>' +
      '<div class="sv-stage" id="svStage"></div><div class="sv-body" id="svBody"></div>';
    document.body.appendChild(el);
    document.body.classList.add('sv-on');
    SV = { el: el, list: list, i: -1, timer: null, left: STORY_MS, t0: 0, paused: false };
    try { history.pushState({ sv: 1 }, ''); } catch (e) { /* ignore */ }
    bindViewer(el);
    showStoryAt(i);
  }
  function showStoryAt(i) {
    if (!SV) return;
    if (i >= SV.list.length) { closeStories(); return; }
    i = Math.max(0, i);
    SV.i = i;
    var c = SV.list[i], x = txt(c), src = c.src[0] || {}, name = srcName(src) || '';
    markSeen(c.id);
    $$('.sv-bars i', SV.el).forEach(function (b, k) {
      var f = b.firstChild;
      f.style.animation = 'none'; void f.offsetWidth; f.style.animation = '';
      b.className = k < i ? 'done' : k === i ? 'run' : '';
    });
    // the picture at its own shape in the middle, a blurred copy of it filling the screen behind
    var bg = $('#svBg'), stage = $('#svStage');
    bg.className = 'sv-bg t-' + c.tier + (c.img ? '' : ' noimg');
    bg.innerHTML = c.img ? '<img referrerpolicy="no-referrer" src="' + esc(c.img) + '" alt="" onerror="this.remove()">' : '';
    stage.innerHTML = c.img ? '<figure class="sv-pic"><img referrerpolicy="no-referrer" src="' + esc(c.img) + '" alt="" onerror="svNoPic(this)"></figure>'
      : '<span class="sv-glyph">' + ic('news') + '</span>';
    $('#svHead').innerHTML = '<span class="sv-av t-' + c.tier + '">' + esc(name.trim().charAt(0) || '•') + '</span>' +
      '<div class="sv-who"><b dir="auto">' + esc(name) + '</b><span>' + esc(ago(c.t)) + '</span></div>' +
      '<button class="sv-x" data-sv="close" aria-label="' + esc(t('close')) + '">' + ic('x') + '</button>';
    var others = c.ns > 1 ? '<span>' + esc(t('sources', { n: nfmt(c.ns) })) + '</span>' : '';
    $('#svBody').innerHTML = '<span class="sv-tier"><i class="t-dot ' + c.tier + '"></i>' + esc(t(c.tier)) + '</span>' +
      '<h2 class="sv-title" dir="auto">' + esc(x.ti) + '</h2>' +
      '<div class="sv-src"><span>' + esc(t('srcLabel')) + ' <b dir="auto">' + esc(name) + '</b></span>' + others + '</div>' +
      '<button class="sv-open" data-sv="open">' + esc(t('fullStory')) + ic('chev', 'ic-sm flip') + '</button>';
    SV.left = STORY_MS;
    SV.paused = false;
    SV.el.classList.remove('paused');
    runStoryTimer();
  }
  window.svNoPic = function (img) {
    var st = img.closest('.sv-stage'), bg = $('#svBg');
    if (st) st.innerHTML = '<span class="sv-glyph">' + ic('news') + '</span>';
    if (bg) { bg.classList.add('noimg'); bg.innerHTML = ''; }
  };
  function runStoryTimer() {
    clearTimeout(SV.timer);
    SV.t0 = Date.now();
    SV.timer = setTimeout(function () { showStoryAt(SV.i + 1); }, SV.left);
  }
  function pauseStory() {
    if (!SV || SV.paused) return;
    SV.paused = true;
    clearTimeout(SV.timer);
    SV.left = Math.max(300, SV.left - (Date.now() - SV.t0));
    SV.el.classList.add('paused');
  }
  function resumeStory() {
    if (!SV || !SV.paused) return;
    SV.paused = false;
    SV.el.classList.remove('paused');
    runStoryTimer();
  }
  function stepStory(dir) { if (SV) showStoryAt(dir < 0 && SV.i === 0 ? 0 : SV.i + dir); }
  function closeStories(keepHistory) {
    if (!SV) return;
    clearTimeout(SV.timer);
    SV.el.remove();
    SV = null;
    document.body.classList.remove('sv-on');
    if (!keepHistory && history.state && history.state.sv) { try { history.back(); } catch (e) { /* ignore */ } }
    renderStories();
  }
  function bindViewer(el) {
    var x0 = 0, y0 = 0, held = false, holdT = null, active = false;
    el.addEventListener('pointerdown', function (e) {
      if (e.target.closest('[data-sv]')) return;
      active = true; held = false; x0 = e.clientX; y0 = e.clientY;
      holdT = setTimeout(function () { held = true; pauseStory(); }, 220);      // press and hold to read longer
    });
    el.addEventListener('pointerup', function (e) {
      clearTimeout(holdT);
      if (!active) return;
      active = false;
      if (held) { resumeStory(); return; }
      var dx = e.clientX - x0, dy = e.clientY - y0, rtl = L() === 'fa';
      if (dy > 80 && dy > Math.abs(dx)) { closeStories(); return; }            // swipe down closes
      // swipe against the reading direction for the next story (leftward in English, rightward in Persian), the
      // other way for the previous one
      if (Math.abs(dx) > 40) { stepStory((dx < 0) !== rtl ? 1 : -1); return; }
      // a tap on the edge the stories came from (right in Persian, left in English) goes back; anywhere else moves on
      var w = window.innerWidth, edge = Math.max(24, Math.min(36, w * 0.08));     // a narrow strip, ~30px on a phone
      stepStory((rtl ? e.clientX > w - edge : e.clientX < edge) ? -1 : 1);
    });
    el.addEventListener('pointercancel', function () { clearTimeout(holdT); active = false; if (held) resumeStory(); });
    el.addEventListener('click', function (e) {
      var b = e.target.closest('[data-sv]');
      if (!b || !SV) return;
      e.stopPropagation();
      if (b.dataset.sv === 'close') closeStories();
      else if (b.dataset.sv === 'open') {
        var id = SV.list[SV.i].id;
        closeStories(true);
        try { history.replaceState({ sheet: 1 }, ''); } catch (er) { /* ignore */ }
        openStory(id, true);
      }
    });
  }
  window.addEventListener('popstate', function () { if (SV) closeStories(true); });
  document.addEventListener('keydown', function (e) {
    if (!SV) return;
    if (e.key === 'Escape') closeStories();
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') stepStory((e.key === 'ArrowRight') !== (L() === 'fa') ? 1 : -1);
  });
  document.addEventListener('visibilitychange', function () { if (SV) { if (document.hidden) pauseStory(); else resumeStory(); } });

  // ------------------------------------------------------------------ new-story tracking & alerts
  function trackNew(isRefresh) {
    var d = S.d.news24;
    if (!d) return;
    var ids = d.clusters.map(function (c) { return c.id; });
    S.newIds = {};
    if (S.seen) {
      var newReds = [];
      d.clusters.forEach(function (c) {
        if (!S.seen.has(c.id)) {
          S.newIds[c.id] = true;
          if (c.tier === 'red' && c.flags.indexOf('denial') < 0) newReds.push(c);
        }
      });
      if (isRefresh && newReds.length) alertRed(newReds);
    }
    var keep = new Set(ids);
    if (S.seen) S.seen.forEach(function (id) { if (keep.size < 2500) keep.add(id); });
    S.seen = keep;
    store.set('seen', Array.from(keep).slice(0, 2500));
  }
  var audioCtx = null;
  function unlockAudio() {
    if (audioCtx) return;
    try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { audioCtx = null; }
  }
  function beep() {
    if (!S.sound || !audioCtx) return;
    try {
      var tt = audioCtx.currentTime;
      [0, 0.22].forEach(function (off, i) {
        var o = audioCtx.createOscillator(), g = audioCtx.createGain();
        o.type = 'sine'; o.frequency.value = i ? 660 : 880;
        g.gain.setValueAtTime(0.0001, tt + off); g.gain.exponentialRampToValueAtTime(0.25, tt + off + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, tt + off + 0.18);
        o.connect(g); g.connect(audioCtx.destination); o.start(tt + off); o.stop(tt + off + 0.2);
      });
      if (navigator.vibrate) navigator.vibrate([120, 60, 120]);
    } catch (e) { /* audio unavailable */ }
  }
  var toastTimer = null;
  function toast(html, storyId, red) {
    var el = $('#toast');
    el.innerHTML = (red ? '<i class="t-dot red"></i>' : ic('check')) + '<span>' + html + '</span>';
    el.style.borderColor = red ? '' : 'var(--line-2)';
    el.dataset.story = storyId || '';
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, red ? 9000 : 2500);
  }
  function alertRed(list) {
    var c = list[0];
    toast('<b>' + esc(t('newRed')) + ':</b> ' + esc(txt(c).ti), c.id, true);
    beep();
  }

  // ------------------------------------------------------------------ sheet
  var sheetOpen = false;
  function openSheet(html, mount, reuseHistory) {
    var layer = $('#sheetLayer');
    $('#sheetBody').innerHTML = html;
    $('#sheetBody').scrollTop = 0;
    layer.hidden = false;
    requestAnimationFrame(function () { layer.classList.add('open'); });
    if (!sheetOpen && !reuseHistory) { try { history.pushState({ sheet: 1 }, ''); } catch (e) { /* ignore */ } }
    sheetOpen = true;
    if (mount) mount($('#sheetBody'));
  }
  function closeSheet(fromPop) {
    if (!sheetOpen) return;
    sheetOpen = false;
    var layer = $('#sheetLayer');
    layer.classList.remove('open');
    $('#sheet').style.transform = '';
    setTimeout(function () { if (!sheetOpen) { layer.hidden = true; $('#sheetBody').innerHTML = ''; } }, 340);
    if (!fromPop && history.state && history.state.sheet) { try { history.back(); } catch (e) { /* ignore */ } }
  }
  window.addEventListener('popstate', function () { if (sheetOpen) closeSheet(true); });
  (function dragSheet() {
    var grip = $('#sheetGrip'), sheet = $('#sheet'), y0 = null, dy = 0;
    grip.addEventListener('pointerdown', function (e) { y0 = e.clientY; dy = 0; sheet.classList.add('dragging'); grip.setPointerCapture(e.pointerId); });
    grip.addEventListener('pointermove', function (e) { if (y0 === null) return; dy = Math.max(0, e.clientY - y0); sheet.style.transform = 'translateY(' + dy + 'px)'; });
    function end() { if (y0 === null) return; sheet.classList.remove('dragging'); y0 = null; if (dy > 110) closeSheet(); else sheet.style.transform = ''; }
    grip.addEventListener('pointerup', end); grip.addEventListener('pointercancel', end);
  })();

  function findStory(id) {
    var lists = [S.d.news24 && S.d.news24.clusters, S.d.newsWeek && S.d.newsWeek.clusters, S.d.stories && S.d.stories.stories];
    for (var i = 0; i < lists.length; i++) {
      if (!lists[i]) continue;
      for (var j = 0; j < lists[i].length; j++) if (lists[i][j].id === id) return lists[i][j];
    }
    return null;
  }
  function storyMedia(c) {
    if (c.vid && c.vid.type === 'yt') return '<div class="st-media"><iframe src="https://www.youtube-nocookie.com/embed/' + esc(c.vid.src) + '?rel=0&playsinline=1" allow="encrypted-media; picture-in-picture" allowfullscreen loading="lazy" referrerpolicy="strict-origin"></iframe></div>';
    if (c.vid && c.vid.type === 'mp4') return '<div class="st-media"><video controls playsinline preload="none"' + (c.img ? ' poster="' + esc(c.img) + '"' : '') + ' src="' + esc(c.vid.src) + '"></video></div>';
    if (c.img) return '<div class="st-media"><img referrerpolicy="no-referrer" src="' + esc(c.img) + '" alt="" onerror="this.parentNode.remove()"></div>';
    return '';
  }
  function openStory(id, reuseHistory) {
    var c = findStory(id);
    if (!c) return;
    var showOrig = false;
    function body() {
      var primary = txt(c);
      var other = L() === 'fa' ? c.en : c.fa;
      var isMT = !!primary.mt;
      var shown = showOrig && other && other.ti ? other : primary;
      var h = storyMedia(c);
      h += '<div class="st-tier"><span class="pill"><i class="t-dot ' + c.tier + '"></i>' + esc(t(c.tier)) + '</span><span>' + esc(t('sev', { n: nfmt(Math.round(c.sev)) })) + '</span><span>' + esc(t('sources', { n: nfmt(c.ns) })) + '</span></div>';
      h += '<h2 class="st-title" dir="auto">' + esc(shown.ti) + '</h2>';
      if (shown.su) h += '<p class="st-sum" dir="auto">' + esc(shown.su) + '</p>';
      h += '<div class="st-mt">';
      if (isMT || primary.fallback) h += '<span>' + esc(t('mt')) + '</span>';
      if (other && other.ti && other.ti !== primary.ti) h += '<button data-a="toggleOrig">' + esc(showOrig ? t('showTr') : t('showOrig')) + '</button>';
      h += '</div>';
      h += '<div class="st-mt"><span>' + esc(t('firstRep', { t: dtime(c.t) })) + '</span>' + (c.u - c.t > 600 ? '<span>' + esc(t('lastRep', { t: dtime(c.u) })) + '</span>' : '') + '</div>';
      h += '<h4>' + esc(t('srcList')) + '</h4><div class="srcs">' + c.src.map(function (s) {
        return '<a href="' + esc(s.u) + '" target="_blank" rel="noopener noreferrer"><span class="n">' + esc(srcName(s)) + '</span><span class="t">' + esc(ago(s.t)) + '</span>' + ic('ext') + '</a>';
      }).join('') + '</div>';
      var tags = [];
      c.topics.forEach(function (k) { if (TOPICS[k]) tags.push(pick(TOPICS[k])); });
      c.ctry.forEach(function (k) { if (COUNTRIES[k]) tags.push(pick(COUNTRIES[k])); });
      c.ppl.forEach(function (k) { if (PEOPLE[k]) tags.push(pick(PEOPLE[k])); });
      if (tags.length) h += '<h4>' + esc(t('tagsH')) + '</h4><div class="tags">' + tags.map(function (x) { return '<span class="tag">' + esc(x) + '</span>'; }).join('') + '</div>';
      return h;
    }
    openSheet(body(), function (root) {
      root.onclick = function (e) {
        if (e.target.closest('[data-a=toggleOrig]')) { e.stopPropagation(); showOrig = !showOrig; root.innerHTML = body(); }
      };
    }, reuseHistory);
  }

  function openLights() {
    var ls = lightsList();
    var h = '<h2>' + esc(t('lightsH')) + '</h2><p class="subnote">' + esc(t('lightsNote')) + '</p>';
    ls.forEach(function (l) {
      h += '<div class="light-row"><span class="lamp" data-state="' + l.state + '">' + ic(LAMP_ICON[l.id] || 'alert') + '</span><div><h5>' + esc(L() === 'fa' ? l.fa : l.en) +
        ' <span class="st ' + l.state + '">' + esc(t(l.state)) + '</span></h5>';
      if (!l.evidence.length) h += '<span class="ev">' + esc(t('noEvidence')) + '</span>';
      l.evidence.forEach(function (ev) {
        var tx = L() === 'fa' ? ev.fa : ev.en;
        if (ev.type === 'cluster') {
          var col = ev.tier === 'red' ? 'var(--red)' : ev.tier === 'orange' ? 'var(--orange)' : 'var(--yellow)';
          h += '<button class="ev" style="--ev:' + col + '" data-story="' + ev.id + '">' + esc(tx || ev.en) + '</button>';
        } else h += '<span class="ev">' + esc(tx) + '</span>';
      });
      h += '</div></div>';
    });
    openSheet(h);
  }

  function openIndex() {
    var idx = S.d.signals && S.d.signals.index;
    if (!idx) return;
    var h = '<h2>' + esc(t('idxH')) + ': ' + nfmt(idx.value) + '</h2>';
    h += '<div class="hrows hrows--wide">';
    h += '<div class="hrow"><span class="l">' + esc(t('idxNews')) + '</span><span class="htrack"><i style="--w:' + idx.news + '%;background:' + rgba(heat(idx.news), 1) + '"></i></span><span class="v">' + nfmt(Math.round(idx.news)) + '</span></div>';
    if (idx.signals != null) h += '<div class="hrow"><span class="l">' + esc(t('idxSig')) + '</span><span class="htrack"><i style="--w:' + idx.signals + '%;background:' + rgba(heat(idx.signals), 1) + '"></i></span><span class="v">' + nfmt(Math.round(idx.signals)) + '</span></div>';
    h += '</div>';
    h += '<h4>' + esc(t('idxWeek')) + '</h4><div class="chart" id="idxChart"></div>';
    h += '<h4>' + esc(t('idxMethod')) + '</h4><div class="method"><p>' + esc(t('method1')) + '</p><p>' + esc(t('method2')) + '</p><p>' + esc(t('method3')) + '</p><p>' + esc(t('method4')) + '</p></div>';
    openSheet(h, function (root) {
      chart($('#idxChart', root), {
        data: idx.history || [], height: 150, min: 0, max: 100, heat: true,
        fmt: function (v) { return nfmt(Math.round(v)); }, xfmt: function (ts) { return dtime(ts); }, ticks: [25, 50, 75]
      });
    });
  }

  function openMarkets() {
    var tk = S.d.ticker || {};
    var u = tk.dollar || {}, b = tk.brent || {}, g = tk.gold || {};
    var h = '<h2>' + esc(t('mkH')) + '</h2>';
    h += '<h4>' + esc(u.label || t('usd')) + '</h4>';
    if (u.price) {
      h += '<div class="readout"><b>' + nfmt(u.price) + '</b><span>' + esc(t('toman')) + '</span>' + chgHtml(null, u.chgDayPct) + '</div>';
      h += '<div class="mrow"><span>' + esc(t('lastTrade')) + '</span><b>' + esc(dtime(u.t)) + '</b></div>';
      if (u.chg != null) h += '<div class="mrow"><span>' + esc(t('vsPrev')) + '</span><b dir="ltr">' + (u.chg > 0 ? '+' : u.chg < 0 ? '−' : '') + nfmt(Math.abs(u.chg)) + '</b></div>';
      if (u.chgDay != null) h += '<div class="mrow"><span>' + esc(t('vsDay')) + '</span><b dir="ltr">' + (u.chgDay > 0 ? '+' : u.chgDay < 0 ? '−' : '') + nfmt(Math.abs(u.chgDay)) + '</b></div>';
      h += '<div class="mrow"><span>' + esc(t('dayHL')) + '</span><b>' + nfmt(u.dayHigh) + ' / ' + nfmt(u.dayLow) + '</b></div>';
      h += '<div class="mrow"><span>' + esc(t('trades')) + '</span><b>' + nfmt(u.trades) + '</b></div>';
      if (u.status !== 'ok') h += '<p class="subnote">' + esc(t('stale')) + '</p>';
      h += '<div class="chart" id="usdChart"></div>';
    } else h += '<p class="subnote">' + esc(t('noData')) + '</p>';
    h += '<p class="subnote">' + esc(t('usdNote')) + '</p>';
    [['brent', b, 2], ['gold', g, 0]].forEach(function (m) {
      var d = m[1];
      h += '<h4>' + esc(t(m[0])) + '</h4>';
      if (d.price) {
        h += '<div class="readout"><b>' + nfmt(d.price, m[2]) + '</b><span>$</span>' + chgHtml(null, d.chgPct) + '</div><div class="chart" id="' + m[0] + 'Chart"></div>';
      } else h += '<p class="subnote">—</p>';
    });
    h += '<h4>' + esc(t('about')) + '</h4><p class="subnote">' + esc(t('refresh')) + nextNewsLine() + '</p>';
    openSheet(h, function (root) {
      if (u.series && u.series.length > 1) chart($('#usdChart', root), { data: u.series, height: 130, step: true, fmt: function (v) { return nfmt(v); }, xfmt: dtime });
      if (b.series && b.series.length > 1) chart($('#brentChart', root), { data: b.series, height: 110, fmt: function (v) { return nfmt(v, 2); }, xfmt: dtime });
      if (g.series && g.series.length > 1) chart($('#goldChart', root), { data: g.series, height: 110, fmt: function (v) { return nfmt(v, 0); }, xfmt: dtime });
    });
  }
  function nextNewsMin() {
    var u = (currentNews() || {}).updated;
    if (!u) return null;
    var mins = (Date.now() / 1000 - u) / 60;
    return mins > 6 ? null : Math.max(1, Math.round(5.5 - mins));
  }
  function nextNewsLine() {
    var n = nextNewsMin();
    return n == null ? '' : '<br>' + esc(t('nextNews', { n: nfmt(n) }));
  }

  function openFilters() {
    var tc = {}, cc = {}, pc = {};
    (currentNews() ? currentNews().clusters : []).forEach(function (c) {
      if (!S.tiers[c.tier]) return;
      c.topics.forEach(function (k) { tc[k] = (tc[k] || 0) + 1; });
      c.ctry.forEach(function (k) { cc[k] = (cc[k] || 0) + 1; });
      c.ppl.forEach(function (k) { pc[k] = (pc[k] || 0) + 1; });
    });
    function sec(title, map, labels, key) {
      var keys = Object.keys(map).filter(function (k) { return labels[k]; }).sort(function (a, b) { return map[b] - map[a]; });
      if (!keys.length) return '';
      return '<h4>' + esc(title) + '</h4><div class="tags">' + keys.map(function (k) {
        return '<button class="chip' + (S[key] === k ? ' on' : '') + '" data-f="' + key + '" data-v="' + k + '">' + esc(pick(labels[k])) + ' <b>' + nfmt(map[k]) + '</b></button>';
      }).join('') + '</div>';
    }
    function body() {
      var h = '<h2>' + esc(t('filtersH')) + '</h2>';
      h += '<h4>' + esc(t('sortBy')) + '</h4><div class="seg"><button data-sort="time" class="' + (S.sort === 'time' ? 'on' : '') + '">' + esc(t('sortTime')) + '</button><button data-sort="sev" class="' + (S.sort === 'sev' ? 'on' : '') + '">' + esc(t('sortSev')) + '</button></div>';
      h += sec(t('topics'), tc, TOPICS, 'topic');
      h += sec(t('countries'), cc, COUNTRIES, 'ctry');
      h += sec(t('people'), pc, PEOPLE, 'ppl');
      h += '<div class="btns"><button class="btn" data-a="clear">' + esc(t('clear')) + '</button><button class="btn" data-close style="border-color:rgba(94,200,255,.6)">' + esc(t('apply', { n: nfmt(filtered().length) })) + '</button></div>';
      return h;
    }
    openSheet(body(), function (root) {
      root.onclick = function (e) {
        var b = e.target.closest('[data-sort],[data-f]');
        if (!b) return;
        e.stopPropagation();
        if (b.dataset.sort) { S.sort = b.dataset.sort; store.set('sort', S.sort); }
        if (b.dataset.f) { S[b.dataset.f] = S[b.dataset.f] === b.dataset.v ? null : b.dataset.v; }
        root.innerHTML = body();
        renderChips(); renderFeed();
      };
    });
  }

  function openSettings() {
    var al = (S.d.signals && S.d.signals.alerts) || {};
    var tgState = al.linked ? t('tgOn') : al.enabled ? t('tgWait') : t('tgOff');
    var hasPin = !!store.get('pin', null);
    var h = '<h2>' + esc(t('settings')) + '</h2>';
    h += '<button class="set-row" data-a="lang">' + ic('globe') + '<span>' + esc(t('lang')) + '</span><span class="r">' + (L() === 'fa' ? 'فارسی' : 'English') + '</span></button>';
    h += '<button class="set-row" data-a="sound">' + ic('sound') + '<span>' + esc(t('sound')) + '</span><span class="r"><i class="switch' + (S.sound ? ' on' : '') + '"></i></span></button>';
    h += '<button class="set-row" data-a="pin">' + ic('lock') + '<span>' + esc(t('lock')) + '</span><span class="r">' + esc(hasPin ? t('lockOff') : t('lockSet')) + '</span></button>';
    h += '<div class="set-row">' + ic('send') + '<span>' + esc(t('tg')) + '</span><span class="r">' + esc(tgState) + '</span></div>';
    if (!al.linked) h += '<p class="subnote">' + esc(t('tgHelp')) + '</p>';
    h += '<button class="set-row" data-a="sources">' + ic('signal') + '<span>' + esc(t('srcH')) + '</span><span class="r">' + ic('chev', 'flip') + '</span></button>';
    h += '<button class="set-row" data-a="index">' + ic('info') + '<span>' + esc(t('methodH')) + '</span><span class="r">' + ic('chev', 'flip') + '</span></button>';
    h += '<p class="subnote">' + esc(t('refresh')) + nextNewsLine() + '</p>';
    openSheet(h, function (root) {
      root.onclick = function (e) {
        var a = e.target.closest('[data-a]');
        if (!a) return;
        e.stopPropagation();
        var act = a.dataset.a;
        if (act === 'sound') { S.sound = !S.sound; store.set('sound', S.sound); unlockAudio(); $('.switch', a).classList.toggle('on', S.sound); if (S.sound) beep(); }
        else if (act === 'lang') { setLang(L() === 'fa' ? 'en' : 'fa'); openSettings(); }
        else if (act === 'pin') { closeSheet(); setTimeout(function () { hasPin ? removePin() : setPin(); }, 350); }
        else if (act === 'sources') openSources();
        else if (act === 'index') openIndex();
      };
    });
  }

  function openSources() {
    function render(hd) {
      var h = '<h2>' + esc(t('srcH')) + '</h2>';
      if (!hd) { openSheet(h + '<div class="skel skel-row"></div>'); return; }
      h += '<p class="subnote">' + esc(t('srcSum', { ok: nfmt(hd.ok_sources), n: nfmt(hd.total_sources) })) + ' — ' + esc(ago(hd.updated)) + '</p>';
      var groups = {};
      hd.sources.forEach(function (s) { (groups[s.group] = groups[s.group] || { name: L() === 'fa' ? s.group_fa : s.group_en, list: [] }).list.push(s); });
      Object.keys(groups).forEach(function (g) {
        h += '<div class="src-group"><h5>' + esc(groups[g].name) + '</h5>';
        groups[g].list.forEach(function (s) {
          var viaKey = { gn: 'srcGn', bing: 'srcBing', tg: 'srcTg' }[s.via];
          var cls = !s.ok ? 'bad' : viaKey ? 'gn' : '';
          var c = s.ok ? t('items', { n: nfmt(s.items) }) + (viaKey ? ' · ' + t(viaKey) : '') : t('srcFail');
          h += '<div class="src-line"><i class="' + cls + '"></i><span>' + esc(L() === 'fa' ? s.fa : s.en) + '</span><span class="c">' + esc(c) + '</span></div>';
        });
        h += '</div>';
      });
      openSheet(h);
    }
    render(S.d.health);
    load(['health']).then(function () { if (sheetOpen) render(S.d.health); });
  }

  function openPlace(hs) {
    var list = (hs.ids || []).map(findStory).filter(Boolean);
    var h = '<h2>' + esc(t('placeH', { p: L() === 'fa' ? hs.fa : hs.en })) + '</h2><div class="feed">' + list.map(card).join('') + '</div>';
    openSheet(h);
  }

  // ------------------------------------------------------------------ chart (single series, crosshair tooltip)
  function niceTicks(lo, hi, n) {
    var span = hi - lo; if (span <= 0) return [lo];
    var raw = span / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
    var step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag;
    var out = [];
    for (var v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
    return out;
  }
  function chart(el, o) {
    if (!el || !o.data || o.data.length < 2) return;
    var W = el.clientWidth || 320, H = o.height || 120, pt = 8, pb = 18, pl = 4, pr = 36;
    var xs = o.data.map(function (d) { return d[0]; }), ys = o.data.map(function (d) { return d[1]; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var y0 = o.min != null ? o.min : Math.min.apply(null, ys), y1 = o.max != null ? o.max : Math.max.apply(null, ys);
    if (o.ref != null) { y0 = Math.min(y0, o.ref); y1 = Math.max(y1, o.ref); }
    if (y1 === y0) { y1 += 1; y0 -= 1; }
    var pad = (y1 - y0) * 0.08; if (o.min == null) y0 -= pad; if (o.max == null) y1 += pad;
    var rtl = false; // time always runs left → right on charts
    function X(v) { return pl + (W - pl - pr) * (v - x0) / Math.max(1, x1 - x0); }
    function Y(v) { return pt + (H - pt - pb) * (1 - (v - y0) / (y1 - y0)); }
    var pts = o.data.map(function (d) { return [X(d[0]), Y(d[1])]; });
    var line = '';
    pts.forEach(function (p, i) {
      if (!i) line += 'M' + p[0].toFixed(1) + ' ' + p[1].toFixed(1);
      else if (o.step) line += 'H' + p[0].toFixed(1) + 'V' + p[1].toFixed(1);
      else line += 'L' + p[0].toFixed(1) + ' ' + p[1].toFixed(1);
    });
    var area = line + 'L' + pts[pts.length - 1][0].toFixed(1) + ' ' + (H - pb) + 'L' + pts[0][0].toFixed(1) + ' ' + (H - pb) + 'Z';
    var id = 'c' + Math.random().toString(36).slice(2, 7);
    var stroke = o.heat ? 'url(#' + id + 'g)' : (o.color || '#5EC8FF');
    var defs = '<defs>';
    if (o.heat) {
      defs += '<linearGradient id="' + id + 'g" gradientUnits="userSpaceOnUse" x1="0" y1="' + Y(0) + '" x2="0" y2="' + Y(100) + '"><stop offset="0" stop-color="#FFD23F"/><stop offset=".52" stop-color="#FF8A2A"/><stop offset="1" stop-color="#FF3D57"/></linearGradient>';
    }
    defs += '</defs>';
    var grid = '';
    var ticks = o.ticks || niceTicks(y0, y1, 3);
    var lastY = Y(ys[ys.length - 1]);
    ticks.forEach(function (tv) {
      if (tv < y0 || tv > y1) return;
      var ty = Y(tv);
      grid += '<line class="gridl" x1="' + pl + '" x2="' + (W - pr) + '" y1="' + ty.toFixed(1) + '" y2="' + ty.toFixed(1) + '"/>';
      if (Math.abs(ty - lastY) > 13) grid += '<text class="axis" x="' + (W - pr + 6) + '" y="' + (ty + 3.5).toFixed(1) + '">' + esc(o.fmt ? o.fmt(tv) : tv) + '</text>';
    });
    var ref = '';
    if (o.ref != null) ref = '<line class="refl" x1="' + pl + '" x2="' + (W - pr) + '" y1="' + Y(o.ref).toFixed(1) + '" y2="' + Y(o.ref).toFixed(1) + '"/><text class="reft" x="' + (pl + 4) + '" y="' + (Y(o.ref) - 5).toFixed(1) + '">' + esc(o.refLabel || '') + '</text>';
    var last = pts[pts.length - 1];
    var lastLbl = '<text class="axis" style="fill:var(--ink);font-weight:700" x="' + (W - pr + 6) + '" y="' + (last[1] + 4).toFixed(1) + '">' + esc(o.fmt ? o.fmt(ys[ys.length - 1]) : ys[ys.length - 1]) + '</text>';
    var areaFill = o.heat ? 'rgba(255,138,42,.10)' : 'rgba(94,200,255,.10)';
    el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '" dir="ltr">' + defs + grid + ref +
      '<path class="ar" d="' + area + '" fill="' + areaFill + '"/><path class="ln" d="' + line + '" stroke="' + stroke + '"/>' +
      '<circle cx="' + last[0].toFixed(1) + '" cy="' + last[1].toFixed(1) + '" r="4" fill="' + (o.heat ? rgba(heat(ys[ys.length - 1]), 1) : (o.color || '#5EC8FF')) + '" stroke="#0B1D3C" stroke-width="2"/>' +
      lastLbl + '<g class="xg" style="opacity:0"><line class="xh" y1="' + pt + '" y2="' + (H - pb) + '" x1="0" x2="0"/><circle class="xd" r="4.5" cx="0" cy="0" fill="#fff" stroke="#0B1D3C" stroke-width="2"/></g></svg>' +
      '<div class="chart-tip" hidden></div>';
    var svg = el.querySelector('svg'), tip = el.querySelector('.chart-tip'), xh = el.querySelector('.xh'), xd = el.querySelector('.xd'), xg = el.querySelector('.xg');
    function move(e) {
      var r = svg.getBoundingClientRect();
      var px = (e.clientX - r.left) * (W / r.width);
      var best = 0, bd = 1e9;
      pts.forEach(function (p, i) { var dd = Math.abs(p[0] - px); if (dd < bd) { bd = dd; best = i; } });
      var p = pts[best];
      xg.style.opacity = 1;
      xh.setAttribute('x1', p[0]); xh.setAttribute('x2', p[0]);
      xd.setAttribute('cx', p[0]); xd.setAttribute('cy', p[1]);
      tip.hidden = false;
      tip.innerHTML = '<b>' + esc(o.fmt ? o.fmt(ys[best]) : ys[best]) + '</b> <span style="color:var(--ink-3)">' + esc(o.xfmt ? o.xfmt(xs[best]) : '') + '</span>';
      tip.style.left = Math.max(60, Math.min(r.width - 60, p[0] * r.width / W)) + 'px';
      tip.style.top = (p[1] * r.height / H - 6) + 'px';
    }
    function leave() { tip.hidden = true; xg.style.opacity = 0; }
    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerdown', move);
    svg.addEventListener('pointerleave', leave);
    svg.style.touchAction = 'pan-y';
  }

  // ------------------------------------------------------------------ map
  var MAPP = { lon0: 31.5, lon1: 63.5, lat0: 11.5, lat1: 40.5, k: Math.cos(27 * Math.PI / 180), sc: 14 };
  function proj(lat, lon) { return [(lon - MAPP.lon0) * MAPP.k * MAPP.sc, (MAPP.lat1 - lat) * MAPP.sc]; }
  var MW = (MAPP.lon1 - MAPP.lon0) * MAPP.k * MAPP.sc, MH = (MAPP.lat1 - MAPP.lat0) * MAPP.sc;
  var CLABELS = [['ایران', 'Iran', 32.6, 54.6], ['عراق', 'Iraq', 33.2, 43.4], ['عربستان', 'Saudi Arabia', 23.8, 45.2],
    ['سوریه', 'Syria', 35.1, 38.6], ['اردن', 'Jordan', 30.9, 37.2], ['ترکیه', 'Türkiye', 39.4, 37.5], ['یمن', 'Yemen', 15.7, 47.4],
    ['عمان', 'Oman', 20.9, 56.6], ['امارات', 'UAE', 23.4, 54.0], ['کویت', 'Kuwait', 29.6, 47.4], ['افغانستان', 'Afghanistan', 33.6, 62.3],
    ['مصر', 'Egypt', 27.0, 32.6]];
  var SEAS = [['خلیج فارس', 'Persian Gulf', 27.2, 51.1], ['دریای عمان', 'Gulf of Oman', 24.3, 59.6], ['دریای سرخ', 'Red Sea', 20.2, 38.9],
    ['دریای خزر', 'Caspian Sea', 39.6, 51.2], ['دریای عرب', 'Arabian Sea', 16.0, 59.5], ['مدیترانه', 'Mediterranean', 33.6, 33.0]];
  function loadMapData() {
    if (S.mapData !== null) return Promise.resolve(S.mapData);
    return fetch('assets/map.json').then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) { S.mapData = j; return j; }, function () { S.mapData = false; return false; });
  }
  function renderMap() {
    var box = $('#map');
    var sig = S.d.signals || {};
    loadMapData().then(function (md) {
      var h = '<svg viewBox="0 0 ' + MW.toFixed(1) + ' ' + MH.toFixed(1) + '" preserveAspectRatio="xMidYMid slice" role="img">';
      var g = '';
      for (var lo = 35; lo <= 60; lo += 5) { var a = proj(MAPP.lat0, lo), b = proj(MAPP.lat1, lo); g += 'M' + a[0].toFixed(1) + ' ' + a[1].toFixed(1) + 'L' + b[0].toFixed(1) + ' ' + b[1].toFixed(1); }
      for (var la = 15; la <= 40; la += 5) { var c = proj(la, MAPP.lon0), d = proj(la, MAPP.lon1); g += 'M' + c[0].toFixed(1) + ' ' + c[1].toFixed(1) + 'L' + d[0].toFixed(1) + ' ' + d[1].toFixed(1); }
      h += '<path class="grat" d="' + g + '"/>';
      if (md && md.countries) md.countries.forEach(function (cn) { h += '<path class="land' + (cn.id === '364' ? ' focus' : '') + '" d="' + cn.d + '"/>'; });
      SEAS.forEach(function (s) { var p = proj(s[2], s[3]); h += '<text class="sea-label" x="' + p[0].toFixed(1) + '" y="' + p[1].toFixed(1) + '">' + esc(L() === 'fa' ? s[0] : s[1]) + '</text>'; });
      CLABELS.forEach(function (s) { var p = proj(s[2], s[3]); h += '<text class="clabel" x="' + p[0].toFixed(1) + '" y="' + p[1].toFixed(1) + '">' + esc(L() === 'fa' ? s[0] : s[1]) + '</text>'; });
      var hs = (sig.hotspots && sig.hotspots[S.range === 'week' ? 'week' : '24h']) || [];
      if (S.layers.news) {
        hs.slice().reverse().forEach(function (s, i) {
          var p = proj(s.lat, s.lon), r = Math.min(13, 5 + s.n * 1.6);
          var col = s.tier === 'red' ? '#FF3D57' : s.tier === 'orange' ? '#FF8A2A' : '#FFD23F';
          h += '<g class="hs" data-hs="' + s.id + '"><circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + (r + 8) + '" fill="transparent"/>';
          if (s.tier === 'red') h += '<circle class="ring" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + r + '" stroke="' + col + '"/>';
          h += '<circle class="core" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + r + '" fill="' + col + '" fill-opacity=".85"/>';
          if (s.n > 1) h += '<text x="' + p[0].toFixed(1) + '" y="' + (p[1] + 4).toFixed(1) + '" text-anchor="middle">' + nfmt(s.n) + '</text>';
          h += '</g>';
        });
      }
      var hz = sig.sea && sig.sea.hormuz;
      if (hz && hz.avg7 != null) {
        var hp = proj(25.6, 57.4);
        h += '<g><text class="sea-label" style="fill:var(--ink-2);font-style:normal;font-weight:700" x="' + hp[0].toFixed(1) + '" y="' + hp[1].toFixed(1) + '">' + esc(L() === 'fa' ? 'هرمز: ' : 'Hormuz: ') + nfmt(hz.avg7, 0) + '/' + nfmt(hz.pre || 0, 0) + '</text></g>';
      }
      h += '</svg><div class="map-tip" id="mapTip" hidden></div>';
      box.innerHTML = h;
      $('#mapLegend').innerHTML = '<span><i class="dot-red"></i>' + esc(t('red')) + '</span><span><i class="dot-orange"></i>' + esc(t('orange')) + '</span><span><i class="dot-yellow"></i>' + esc(t('yellow')) + '</span>';
      box.onclick = function (e) {
        var tip = $('#mapTip');
        var hsEl = e.target.closest('[data-hs]');
        if (hsEl) { var spot = hs.filter(function (s) { return s.id === hsEl.dataset.hs; })[0]; if (spot) openPlace(spot); return; }
        tip.hidden = true;
      };
    });
    var lay = '<button class="chip' + (S.layers.news ? ' on' : '') + '" data-layer="news">' + ic('pin', 'ic-sm') + esc(t('layNews')) + '</button>' +
      '<button class="chip" data-range-toggle="1">' + ic('clock', 'ic-sm') + esc(S.range === 'week' ? t('rWeek') : t('r24')) + '</button>';
    $('#mapLayers').innerHTML = lay;
  }

  var SRC_FA = { France: 'فرانسه', Germany: 'آلمان', Italy: 'ایتالیا', EASA: 'آژانس ایمنی هوانوردی اروپا', USA: 'آمریکا',
    'United States': 'آمریکا', UK: 'بریتانیا', 'United Kingdom': 'بریتانیا', Canada: 'کانادا', Russia: 'روسیه', Iraq: 'عراق',
    Israel: 'اسرائیل', Iran: 'ایران', Netherlands: 'هلند', Turkey: 'ترکیه', Australia: 'استرالیا', India: 'هند', China: 'چین',
    Japan: 'ژاپن', 'Saudi Arabia': 'عربستان', UAE: 'امارات', Qatar: 'قطر', Kuwait: 'کویت', Bahrain: 'بحرین', Oman: 'عمان',
    Jordan: 'اردن', Lebanon: 'لبنان', Syria: 'سوریه', Egypt: 'مصر', Switzerland: 'سوئیس', Austria: 'اتریش', Poland: 'لهستان',
    Spain: 'اسپانیا', Belgium: 'بلژیک', 'New Zealand': 'نیوزیلند', Ireland: 'ایرلند', Sweden: 'سوئد', Norway: 'نروژ',
    Denmark: 'دانمارک', Finland: 'فنلاند', Greece: 'یونان', Cyprus: 'قبرس', Yemen: 'یمن', ICAO: 'ایکائو' };
  function aviationCard(av) {
    var h = '<div class="card"><div class="card-h">' + ic('planeoff') + '<h3>' + esc(t('avH')) + '</h3><span class="meta">' + (av && av.updated ? esc(ago(av.updated)) : '') + '</span></div>';
    var cs = (av && av.countries) || [];
    if (!cs.length) return h + '<p class="subnote">' + esc(t('avNone')) + '</p></div>';
    var now = Date.now() / 1000;
    h += '<div class="av-list">';
    cs.forEach(function (c) {
      var lv = c.level || 4;
      var fresh = (c.warnings || []).filter(function (w) { return w.issued && now - w.issued < 3 * 86400; }).length;
      h += '<details class="av"><summary><span class="av-lv lv' + lv + '">' + nfmt(lv) + '</span><b>' + esc(L() === 'fa' ? c.fa : c.en) + '</b>' +
        '<span class="av-t">' + esc(L() === 'fa' ? c.level_fa : c.level_en) + '</span>' + (fresh ? '<span class="av-new">' + esc(t('avNew')) + '</span>' : '') +
        '<span class="r">' + ic('chev') + '</span></summary>';
      var sum = L() === 'fa' ? (c.summary_fa || c.summary) : c.summary;
      if (sum) h += '<p class="av-sum">' + esc(sum) + '</p>';
      (c.warnings || []).slice(0, 4).forEach(function (w) {
        var src = L() === 'fa' ? (SRC_FA[w.src] || w.src) : w.src;
        var until = w.until_t ? t('avUntil', { d: dshort(w.until_t) }) : (/ongoing|further/i.test(w.until || '') ? t('avOngoing') : (w.until || ''));
        var note = L() === 'fa' ? (w.note_fa || w.note) : w.note;
        var isNew = w.issued && now - w.issued < 3 * 86400;
        h += '<div class="av-w' + (isNew ? ' is-new' : '') + '"><div><b>' + esc(src) + '</b> <span dir="ltr">' + esc(w.ref) + '</span></div>' +
          '<div class="av-d">' + (w.issued ? esc(t('avIssued', { d: dshort(w.issued) })) : '') + (until ? ' · ' + esc(until) : '') + '</div>' +
          (note ? '<p>' + esc(note) + '</p>' : '') + '</div>';
      });
      if (c.url) h += '<a class="av-link" target="_blank" rel="noopener" href="' + esc(c.url) + '">' + esc(t('avMore')) + ' ' + ic('ext', 'ic-sm') + '</a>';
      h += '</details>';
    });
    h += '</div><p class="subnote">' + esc(t('avNote')) + '</p></div>';
    return h;
  }

  function renderSignals() {
    var sig = S.d.signals;
    var box = $('#signals');
    if (!sig) { box.innerHTML = '<div class="skel skel-row" style="margin-top:12px"></div>'; return; }
    var h = '';
    h += aviationCard(sig.aviation);
    // --- Hormuz
    var hz = sig.sea && sig.sea.hormuz;
    h += '<div class="card"><div class="card-h">' + ic('tanker') + '<h3>' + esc(t('hzH')) + '</h3></div>';
    if (hz) {
      h += '<div class="readout"><b>' + nfmt(hz.avg7, 1) + '</b><span>' + esc(t('hzUnit')) + '</span></div>';
      h += '<div class="subnote" style="margin-top:4px">' + esc(t('hzPre', { n: nfmt(hz.pre, 0) })) + (hz.pct7 != null ? '  —  ' + esc(t('hzPct', { n: nfmt(hz.pct7) })) : '') + '</div>';
      if (hz.tank7 != null) h += '<div class="subnote" style="margin-top:2px">' + esc(t('hzTank', { a: nfmt(hz.tank7, 1), b: nfmt(hz.pre_tank, 0) })) + '</div>';
      h += '<div class="chart" id="hzChart"></div>';
      h += '<p class="subnote">' + esc(t('hzLag', { d: isoDate(hz.last_date) })) + '</p>';
      var bab = sig.sea.bab;
      if (bab && bab.avg7 != null) h += '<div class="mrow"><span>' + esc(t('babH')) + '</span><b>' + nfmt(bab.avg7, 1) + ' / ' + nfmt(bab.pre, 0) + '</b></div>';
    } else h += '<p class="subnote">—</p>';
    h += '</div>';
    // --- warnings
    var ws = (sig.sea && sig.sea.warnings) || [];
    h += '<div class="card"><div class="card-h">' + ic('alert') + '<h3>' + esc(t('warnH')) + '</h3><span class="meta">' + nfmt(ws.length) + '</span></div>';
    if (!ws.length) h += '<p class="subnote">' + esc(t('warnNone')) + '</p>';
    ws.slice(0, 6).forEach(function (w) { h += '<div class="warn-item"><b>' + esc(w.id) + ' — ' + esc(w.date) + '</b>' + esc(w.text) + '</div>'; });
    h += '</div>';
    h += '<div class="btns"><a class="btn" target="_blank" rel="noopener" href="https://www.marinetraffic.com/en/ais/home/centerx:56.3/centery:26.4/zoom:8">' + ic('anchor') + esc(t('liveSea')) + '</a></div>';
    box.innerHTML = h;
    if (hz && hz.series && hz.series.length > 2) {
      var data = hz.series.map(function (r) { return [Date.parse(r[0] + 'T12:00:00Z') / 1000, r[1]]; });
      chart($('#hzChart'), { data: data, height: 120, min: 0, ref: hz.pre, refLabel: t('hzPre', { n: nfmt(hz.pre, 0) }), fmt: function (v) { return nfmt(Math.round(v)); }, xfmt: function (ts) { return dshort(ts); }, ticks: [] });
    }
  }

  // ------------------------------------------------------------------ X
  function renderX() {
    var box = $('#xFeed');
    $$('#xSeg button').forEach(function (b) { b.classList.toggle('on', b.dataset.seg === S.xseg); });
    var d = S.d.x;
    if (!d) { box.innerHTML = skeleton(); return; }
    var posts = d.posts.filter(function (p) { return p.seg === S.xseg; });
    if (!posts.length) { box.innerHTML = '<div class="empty">' + ic('quote') + '<p>' + esc(t('xEmpty')) + '</p></div>'; return; }
    box.innerHTML = posts.map(postHtml).join('');
  }
  function postHtml(p) {
    var showOrig = S.origX[p.id];
    var tr = L() === 'fa' ? (p.fa || p.text) : (p.en || p.text);
    var body = showOrig ? p.text : tr;
    var canToggle = tr && tr !== p.text;
    var av = p.img ? '<span class="avatar"><img loading="lazy" referrerpolicy="no-referrer" src="' + esc(p.img) + '" alt="" onerror="this.remove()"></span>'
      : '<span class="avatar">' + esc((p.n || p.h || '?').trim().charAt(0)) + '</span>';
    var media = '';
    (p.media || []).slice(0, 1).forEach(function (m) {
      if (m.type === 'photo') media = '<div class="post-media"><img loading="lazy" referrerpolicy="no-referrer" src="' + esc(m.url) + '" alt="" onerror="this.parentNode.remove()"></div>';
      else if (m.type === 'video') media = '<div class="post-media"><video controls playsinline preload="none" poster="' + esc(m.poster || '') + '" src="' + esc(m.url) + '"></video></div>';
    });
    var role = L() === 'fa' ? p.role_fa : p.role_en;
    return '<article class="post"><div class="post-h">' + av + '<div style="min-width:0"><div class="post-n"><span dir="auto">' + esc(p.n || p.h) + '</span>' + (p.v ? ic('check') : '') +
      (p.platform === 'truth' ? '<span class="platform">Truth Social</span>' : p.platform === 'telegram' ? '<span class="platform">' + esc(t('telegram')) + '</span>' : '') + '</div><div class="post-r">' + esc(role || '') + ' <span dir="ltr">@' + esc(p.h) + '</span></div></div>' +
      '<span class="post-t">' + esc(ago(p.t)) + '</span></div><p class="post-text" dir="auto">' + esc(body) + '</p>' +
      (canToggle ? '<button class="toggle-orig" data-orig="' + esc(p.id) + '">' + esc(showOrig ? t('showTr') : t('showOrig')) + '</button>' : '') + media +
      '<div class="post-f">' + (p.likes ? '<span>' + ic('heart') + nfmt(p.likes) + '</span>' : '') + (p.cites ? '<span>' + ic('news') + esc(t('cites', { n: nfmt(p.cites) })) + '</span>' : '') +
      '<a href="' + esc(p.url) + '" target="_blank" rel="noopener noreferrer">' + esc(t('openX')) + ic('ext', 'ic-sm') + '</a></div></article>';
  }

  // ------------------------------------------------------------------ Economist
  // The week's issue, summarised by hand into five categories; politics also has red / orange / yellow levels.
  // Each card links to the article; its picture is the site's own preview, with a news-search thumbnail as backup.
  function issueDate(s) {
    var d = new Date(String(s) + 'T12:00:00Z');
    if (isNaN(d)) return s || '';
    return new Intl.DateTimeFormat(LOC(), { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(d);
  }
  function ecLabel(k) { return L() === 'fa' ? EC_CAT[k][0] : EC_CAT[k][1]; }
  window.ecImgFail = function (img) {
    var alt = img.getAttribute('data-alt');
    if (alt) { img.removeAttribute('data-alt'); img.src = alt; return; }
    var box = img.parentNode;
    img.remove();
    if (box && !box.classList.contains('noimg')) {
      box.classList.add('noimg');
      box.insertAdjacentHTML('beforeend', ic((EC_CAT[box.getAttribute('data-cat')] || EC_CAT.pol)[2], 'ec-glyph'));
    }
  };
  function ecCard(a, cat) {
    var x = a[L()] && a[L()].t ? a[L()] : a.fa;
    var tier = cat === 'pol' && TIER_ORDER.indexOf(a.tier) >= 0 ? a.tier : null;
    var tag = tier ? '<span class="s-tag"><i class="t-dot ' + tier + '"></i>' + esc(t(tier)) + '</span>' : '';
    var src = a.img || a.alt;
    var pic = src
      ? '<div class="ec-pic" data-cat="' + cat + '"><img loading="lazy" decoding="async" referrerpolicy="no-referrer" src="' + esc(src) + '"' +
        (a.img && a.alt ? ' data-alt="' + esc(a.alt) + '"' : '') + ' alt="" onerror="ecImgFail(this)">' + tag + '</div>'
      : '<div class="ec-pic noimg" data-cat="' + cat + '">' + tag + ic(EC_CAT[cat][2], 'ec-glyph') + '</div>';
    var sec = EC_SEC[a.sec] ? pick(EC_SEC[a.sec]) : '';
    var col = a.col ? (L() === 'fa' ? a.col.fa : a.col.en) : '';
    var kick = '<div class="ec-kick">' + (sec ? '<b>' + esc(sec) + '</b>' : '') + (col ? '<span>' + esc(col) + '</span>' : '') +
      (a.page ? '<span class="pg">' + esc(t('ecPage', { n: nfmt(a.page) })) + '</span>' : '') + '</div>';
    var paras = String(x.s || '').split(/\n\s*\n/).map(function (p) { return '<p>' + esc(p.trim()) + '</p>'; }).join('');
    var imp = x.i ? '<div class="ec-impact"><b>' + ic('signal', 'ic-sm') + esc(t('ecImpact')) + '</b><p>' + esc(x.i) + '</p></div>' : '';
    return '<article class="ec-card' + (tier ? ' t-' + tier : '') + '">' + pic + '<div class="ec-body">' + kick +
      '<h3 class="ec-title">' + esc(x.t) + '</h3><div class="ec-sum">' + paras + '</div>' + imp +
      '<a class="ec-link" href="' + esc(a.url) + '" target="_blank" rel="noopener noreferrer">' + esc(t('ecRead')) + ic('ext', 'ic-sm') + '</a></div></article>';
  }
  function renderEcon() {
    var d = S.d.econ, feed = $('#ecFeed'), tiers = $('#ecTiers');
    if (!d || !d.articles) {
      $('#ecHead').innerHTML = ''; $('#ecCats').innerHTML = ''; tiers.hidden = true;
      feed.innerHTML = S.offline ? '<div class="empty">' + ic('offline') + '<p>' + esc(t('offline')) + '</p></div>'
        : S.econTried ? '<div class="empty">' + ic('book') + '<p>' + esc(t('ecNone')) + '</p></div>' : skeleton();
      return;
    }
    var byId = {};
    d.articles.forEach(function (a) { byId[a.id] = a; });
    var ids = function (k) { return ((d.cats || {})[k] || []).filter(function (id) { return byId[id]; }); };
    if (EC_CATS.indexOf(S.econCat) < 0) S.econCat = 'pol';
    $('#ecHead').innerHTML = '<span class="ec-mark">' + ic('book') + '</span><div><b>' + esc(t('ecIssue', { d: issueDate(d.issue) })) + '</b>' +
      '<span>' + esc(t('ecCount', { n: nfmt(d.articles.length) })) + '</span></div>';
    $('#ecCats').innerHTML = EC_CATS.map(function (k) {
      var n = ids(k).length, on = S.econCat === k;
      return '<button class="ec-cat' + (on ? ' on' : '') + (n ? '' : ' empty') + '" data-ecat="' + k + '" role="tab" aria-selected="' + on + '">' +
        ic(EC_CAT[k][2]) + '<span>' + esc(ecLabel(k)) + '</span>' + (n ? '<b>' + nfmt(n) + '</b>' : '') + '</button>';
    }).join('');
    var all = ids(S.econCat).map(function (id) { return byId[id]; }), list = all;
    if (S.econCat === 'pol' && all.length) {
      var counts = { red: 0, orange: 0, yellow: 0 };
      all.forEach(function (a) { if (counts[a.tier] != null) counts[a.tier]++; });
      tiers.innerHTML = TIER_ORDER.map(function (k) {
        var on = !!S.econTiers[k];
        return '<button class="chip chip--tier' + (on ? ' on' : '') + '" data-etier="' + k + '" aria-pressed="' + on + '"><i class="t-dot ' + k + '"></i>' +
          esc(t(k)) + ' <b>' + nfmt(counts[k]) + '</b></button>';
      }).join('');
      tiers.hidden = false;
      list = all.filter(function (a) { return TIER_ORDER.indexOf(a.tier) < 0 || S.econTiers[a.tier]; });
      list = TIER_ORDER.reduce(function (acc, k) { return acc.concat(list.filter(function (a) { return a.tier === k; })); },
        list.filter(function (a) { return TIER_ORDER.indexOf(a.tier) < 0; }));
    } else tiers.hidden = true;
    if (!list.length) {
      feed.innerHTML = '<div class="empty">' + ic(EC_CAT[S.econCat][2]) + '<p>' +
        esc(all.length ? t('ecTierEmpty') : t('ecEmpty', { c: ecLabel(S.econCat) })) + '</p></div>';
      return;
    }
    feed.innerHTML = list.map(function (a) { return ecCard(a, S.econCat); }).join('') + '<p class="ec-note">' + esc(t('ecNote')) + '</p>';
  }
  // a dot on the tab until this browser has opened the current issue
  function econDot() {
    var d = S.d.econ;
    $('#ecDot').hidden = !(d && d.issue && S.tab !== 'econ' && store.get('econSeen', null) !== d.issue);
  }
  function econSeen() {
    if (S.d.econ && S.d.econ.issue) store.set('econSeen', S.d.econ.issue);
    econDot();
  }

  // ------------------------------------------------------------------ PIN lock
  function sha256(s) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode('db:' + s)).then(function (b) {
      return Array.prototype.map.call(new Uint8Array(b), function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
    });
  }
  function pinPad(msgKey, onDone) {
    var lock = $('#lock'), dots = $$('#pinDots i'), val = '';
    $('#lockMsg').textContent = t(msgKey);
    lock.hidden = false;
    var keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'];
    $('#pinpad').innerHTML = keys.map(function (k) { return k ? '<button data-k="' + k + '">' + (k === '⌫' ? k : nfmt(+k)) + '</button>' : '<span></span>'; }).join('');
    function paint() { dots.forEach(function (d, i) { d.classList.toggle('f', i < val.length); }); }
    paint();
    $('#pinpad').onclick = function (e) {
      var b = e.target.closest('[data-k]'); if (!b) return;
      if (b.dataset.k === '⌫') val = val.slice(0, -1); else if (val.length < 4) val += b.dataset.k;
      paint();
      if (val.length === 4) { var v = val; val = ''; setTimeout(function () { paint(); onDone(v); }, 120); }
    };
  }
  function shake(key) { var d = $('#pinDots'); d.classList.remove('shake'); void d.offsetWidth; d.classList.add('shake'); $('#lockMsg').textContent = t(key); }
  function checkLock() {
    var h = store.get('pin', null);
    if (!h || !window.crypto || !crypto.subtle) return;
    pinPad('pinEnter', function next(v) {
      sha256(v).then(function (x) { if (x === h) $('#lock').hidden = true; else { shake('pinWrong'); pinPad('pinWrong', next); } });
    });
  }
  function setPin() {
    if (!window.crypto || !crypto.subtle) return;
    pinPad('pinNew', function (a) {
      pinPad('pinAgain', function (b) {
        if (a !== b) { shake('pinMismatch'); setTimeout(setPin, 700); return; }
        sha256(a).then(function (x) { store.set('pin', x); $('#lock').hidden = true; toast(esc(t('lock')) + ' ✓'); });
      });
    });
  }
  function removePin() {
    var h = store.get('pin', null);
    pinPad('pinEnter', function next(v) {
      sha256(v).then(function (x) { if (x === h) { store.set('pin', null); $('#lock').hidden = true; toast(esc(t('lockOff')) + ' ✓'); } else { shake('pinWrong'); pinPad('pinWrong', next); } });
    });
  }

  // ------------------------------------------------------------------ navigation & events
  function setLang(l) {
    S.lang = l; store.set('lang', l);
    applyLang(); renderAll(true);
  }
  function setTab(tab) {
    S.tab = tab;
    $$('#tabs button').forEach(function (b) { b.classList.toggle('on', b.dataset.tab === tab); });
    $$('.pane').forEach(function (p) { p.hidden = p.dataset.pane !== tab; });
    if (tab === 'map') { renderMap(); renderSignals(); }
    if (tab === 'x') renderX();
    if (tab === 'econ') {
      renderEcon(); econSeen();
      if (!S.d.econ && !S.econBusy) {
        S.econBusy = true;
        getJSON(KEYS.econ).then(function (j) { S.d.econ = j; store.set('cache.econ', j); }, function () { /* not published yet */ })
          .then(function () { S.econBusy = false; S.econTried = true; if (S.tab === 'econ') { renderEcon(); econSeen(); } });
      }
    } else econDot();
    var panel = $('#panel');
    var top = panel.offsetTop + panel.offsetHeight - 10;
    if (window.scrollY > top) window.scrollTo(0, top);
  }
  function renderAll(langChanged) {
    renderHeader(); renderMarkets(); renderGauge(); renderLamps(); renderFlash(); renderStories();
    $$('#rangeSeg button').forEach(function (b) { b.classList.toggle('on', b.dataset.range === S.range); });
    renderChips(); renderFeed(true);
    if (S.tab === 'map') { renderMap(); renderSignals(); }
    if (S.tab === 'x' || langChanged) renderX();
    if (S.tab === 'econ' || langChanged) renderEcon();
    econDot();
  }

  document.addEventListener('click', function (e) {
    unlockAudio();
    var el;
    if ((el = e.target.closest('[data-close]'))) { closeSheet(); return; }
    if ((el = e.target.closest('[data-sty]'))) { openStories(+el.dataset.sty); return; }
    if ((el = e.target.closest('[data-story]')) && el.dataset.story) { if (el.id === 'toast') el.hidden = true; openStory(el.dataset.story); return; }
    if ((el = e.target.closest('[data-tab]'))) { setTab(el.dataset.tab); return; }
    if ((el = e.target.closest('[data-ecat]'))) {
      S.econCat = el.dataset.ecat; store.set('econCat', S.econCat); renderEcon();
      var top = $('#pane-econ').offsetTop - 64;
      if (window.scrollY > top) window.scrollTo(0, top);
      return;
    }
    if ((el = e.target.closest('[data-etier]'))) {
      var et = Object.assign({}, S.econTiers);
      et[el.dataset.etier] = !et[el.dataset.etier];
      if (!et.red && !et.orange && !et.yellow) return;              // at least one level stays on
      S.econTiers = et; store.set('econTiers', et); renderEcon(); return;
    }
    if ((el = e.target.closest('[data-tier]'))) {
      var nt = Object.assign({}, S.tiers);
      nt[el.dataset.tier] = !nt[el.dataset.tier];
      if (!nt.red && !nt.orange && !nt.yellow) return;              // at least one level stays on
      S.tiers = nt; store.set('tiers', nt); renderChips(); renderFeed(); return;
    }
    if ((el = e.target.closest('[data-range]'))) { S.range = el.dataset.range; store.set('range', S.range); renderAll(); return; }
    if ((el = e.target.closest('[data-range-toggle]'))) { S.range = S.range === 'week' ? '24h' : 'week'; store.set('range', S.range); if (S.range === 'week' && !S.d.newsWeek) load(['newsWeek']).then(function () { renderAll(); }); renderAll(); return; }
    if ((el = e.target.closest('[data-layer]'))) { var k = el.dataset.layer; S.layers[k] = !S.layers[k]; store.set('layers', S.layers); renderMap(); return; }
    if ((el = e.target.closest('[data-seg]'))) { S.xseg = el.dataset.seg; renderX(); return; }
    if ((el = e.target.closest('[data-orig]'))) { var id = el.dataset.orig; S.origX[id] = !S.origX[id]; renderX(); return; }
    if ((el = e.target.closest('[data-a]'))) {
      var a = el.dataset.a;
      if (a === 'settings') openSettings();
      else if (a === 'lights') openLights();
      else if (a === 'index') openIndex();
      else if (a === 'markets') openMarkets();
      else if (a === 'filters') openFilters();
      else if (a === 'clear') { S.tiers = Object.assign({}, DEF_TIERS); store.set('tiers', S.tiers); S.topic = S.ctry = S.ppl = null; S.q = ''; $('#searchInput').value = ''; $('#searchBox').hidden = true; renderChips(); renderFeed(); if (sheetOpen) closeSheet(); }
    }
  });
  $('#langBtn').addEventListener('click', function () { setLang(L() === 'fa' ? 'en' : 'fa'); });
  $('#searchBtn').addEventListener('click', function () { var b = $('#searchBox'); b.hidden = !b.hidden; if (!b.hidden) $('#searchInput').focus(); });
  $('#searchClose').addEventListener('click', function () { $('#searchBox').hidden = true; S.q = ''; $('#searchInput').value = ''; renderChips(); renderFeed(); });
  var qTimer;
  $('#searchInput').addEventListener('input', function (e) { clearTimeout(qTimer); qTimer = setTimeout(function () { S.q = e.target.value.trim(); renderChips(); renderFeed(); }, 220); });

  // infinite scroll
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (en) { if (en[0].isIntersecting && S.tab === 'news') more(); }, { rootMargin: '600px' }).observe($('#sentinel'));
    new IntersectionObserver(function (en) { document.body.classList.toggle('compact', !en[0].isIntersecting); }, { rootMargin: '-60px 0px 0px 0px' }).observe($('#gauge'));
  }

  // pull to refresh
  (function ptr() {
    var y0 = null, dy = 0, el = $('#ptr'), busy = false;
    window.addEventListener('touchstart', function (e) { if (window.scrollY <= 0 && !sheetOpen && !busy) { y0 = e.touches[0].clientY; dy = 0; } }, { passive: true });
    window.addEventListener('touchmove', function (e) {
      if (y0 === null) return;
      dy = e.touches[0].clientY - y0;
      if (dy <= 0) { el.style.opacity = 0; return; }
      var p = Math.min(1, dy / 90);
      el.style.opacity = p; el.style.transform = 'translateY(' + (dy * 0.45 - 30) + 'px) rotate(' + (dy * 3) + 'deg) scale(' + (0.8 + p * 0.2) + ')';
    }, { passive: true });
    window.addEventListener('touchend', function () {
      if (y0 === null) return;
      y0 = null;
      if (dy > 90) {
        busy = true; el.classList.add('spin');
        refreshAll(true).then(function () { busy = false; el.classList.remove('spin'); el.style.opacity = 0; toast(esc(t('refreshed'))); });
      } else el.style.opacity = 0;
    });
  })();

  // ------------------------------------------------------------------ refresh loop
  function refreshAll(fresh) {
    var keys = ['ticker', 'signals', 'news24', 'x', 'stories', 'econ'];
    if (S.range === 'week' || S.d.newsWeek) keys.push('newsWeek');
    S.econAt = nowS();
    return load(keys, fresh).then(function (ch) {
      S.loaded = true; S.econTried = true;
      if (ch.news24) trackNew(!!S.firstDone);
      S.firstDone = true;
      renderAll();
    });
  }
  function tickTicker() {
    load(['ticker']).then(function (ch) { if (ch.ticker) { renderMarkets(); renderHeader(); } });
  }
  function tickNews() {
    var keys = ['signals', 'news24'];
    if (S.tab === 'x' || Math.random() < 0.5) keys.push('x');
    if (S.range === 'week') keys.push('newsWeek');
    if (!S.d.stories || nowS() > (S.d.stories.next || 0) - 60) keys.push('stories');      // a new set every two hours
    if (nowS() - (S.econAt || 0) > 1800) { S.econAt = nowS(); keys.push('econ'); }       // a new issue once a week
    load(keys).then(function (ch) {
      if (ch.stories && !SV) renderStories();
      if (ch.econ) { if (S.tab === 'econ') { renderEcon(); econSeen(); } else econDot(); }
      if (ch.news24) trackNew(true);
      if (ch.news24 || ch.signals || ch.newsWeek) {
        renderHeader(); renderGauge(); renderLamps(); renderFlash(); renderChips();
        if (window.scrollY < 400) renderFeed(true);
        if (S.tab === 'map') { renderMap(); renderSignals(); }
      }
      if (ch.x && S.tab === 'x') renderX();
      renderHeader();
    });
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { tickTicker(); tickNews(); } });
  setInterval(function () { if (!document.hidden) tickTicker(); }, 60 * 1000);
  setInterval(function () { if (!document.hidden) tickNews(); }, 150 * 1000);
  setInterval(function () { if (!document.hidden) renderHeader(); }, 30 * 1000);

  // ------------------------------------------------------------------ boot
  applyLang();
  bootCache();
  if (S.d.news24) { S.loaded = true; trackNew(false); }
  renderAll();
  S.firstDone = !!S.d.news24;
  refreshAll(false).then(function () { S.firstDone = true; });
  checkLock();
  if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(function () { /* optional */ });
})();
