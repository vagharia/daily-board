"""Regression checks for the deployment lamp (index.compute_lights → "deploy", deploy.lamp): only forces of the war's
sides sent toward the Middle East or Iran, told in the headline, light it. Run: python3 tests/test_deploy.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import deploy  # noqa: E402
from engine.classify_fa import score_fa  # noqa: E402


def lamp(ti, lang):
    return deploy.lamp({"ti": ti, "lang": lang, "flags": ["deploy"]})


NOT_LAMP = [
    ("تقویت محور آنکارا-ر ریاض؛ تمرکز ترکیه و عربستان بر توسعه همکاری‌های صنایع دفاعی و انتقال فناوری", "fa"),
    ("بمب‌افکن ۷۰ ساله آمریکا تا دهه ۲۰۵۰ پرواز می‌کند؛ نوسازی B-52 با موتورهای رولزرویس", "fa"),
    ("درخواست بن سلمان از دمشق برای اعزام نیرو به مرز یمن", "fa"),
    ("یمن: مانع ورود جنگنده های اف ۱۵ سعودی به پایتخت شدیم", "fa"),
    ("پرواز پهپاد از عرشه ناو هواپیمابر انگلیسی", "fa"),
    ("ناو هواپیمابر فوجیان چین آماده عملیات هماهنگ با جنگنده‌های پنهان‌کار شد", "fa"),
    ("دبیرکل شورای همکاری خلیج فارس: بحرین، کویت، عمان، قطر، عربستان و امارات با ایجاد یک «مقر پیشرفته برای فرماندهی"
     " نظامی مشترک خود در کویت» و «استقرار نیرو‌های…", "fa"),
    ("دمشق اعزام نیروهای سوریه به یمن را رد کرد", "fa"),
    ("آسوشیتدپرس: سوریه به مرز عربستان با یمن نیرو اعزام می‌کند", "fa"),
    ("تهدید جدید ترامپ : سه ناو هواپیمابر ارتش آمریکا تو خاورمیانه حضور دارند و آماده شلیک به سمت ایران هستند", "fa"),
    ("فایننشال تایمز: واشنگتن برای انتقال سومین ناو هواپیمابر خود به منطقه خاورمیانه تلاش می‌کند", "fa"),
    ("آمریکا ناو هواپیمابر آبراهام لینکلن را از خاورمیانه خارج کرد", "fa"),
    ("Pentagon struggles to track millions of F-35 spare parts: Watchdog", "en"),
    ("Russian military aircraft makes 'unusual' landing at Israel's Ben Gurion Airport: Report", "en"),
    ("US-sanctioned Russian military aircraft makes mysterious landing in Israel", "en"),
    ("Syrian FM denies troop deployment to Yemen after defense deal with Riyadh", "en"),
    ("Egypt deployed forces to Saudi Arabia before Sisi's public pledge of military support, sources say", "en"),
    ("US and Iran near possible nuclear breakthrough as American military buildup continues", "en"),
    ("US considering sending more troops to Middle East", "en"),
    ("USS Ford leaves the Middle East", "en"),
]
LAMP = [
    ("بازگشت ناو هواپیمابر آمریکایی \"ثئودور روزولت\" و دو ناو جنگی همراه آن به مسیر دریایی به سمت خاورمیانه", "fa"),
    ("الجزیره: ناو هواپیمابر آمریکایی «روزولت» و گروه رزمی آن پس از توقفی دو روزه در پایگاه دریایی سنگاپور، این پایگاه"
     " را ترک کرد تا سفر خود به مقصد خاورمیانه را از…", "fa"),
    ("هواپیماهای ترابری نظامی آمریکایی همچنان به صورت پی در پی در حال حرکت از اروپا به سمت خاورمیانه می‌باشند", "fa"),
    ("اعزام ۱۲ فروند جنگنده اف-۳۵ آمریکایی به اسرائیل", "fa"),
    ("ورود بمب‌افکن‌های B-52 آمریکا به منطقه", "fa"),
    ("پنتاگون: ۳ هزار نیروی دیگر به خاورمیانه اعزام می‌شود", "fa"),
    ("US sends third aircraft carrier to Middle East", "en"),
    ("Pentagon deploys B-2 bombers to Diego Garcia", "en"),
    ("Dozens of US refueling aircraft head to the Middle East, flight trackers show", "en"),
    ("Carrier strike group arrives in Arabian Sea", "en"),
]


# the bulletin's «deploy» flag (classify_fa): «ناو», «تاد» only as words of their own
FA_NOT_FLAG = [
    "تقویت محور آنکارا-ر ریاض؛ تمرکز ترکیه و عربستان بر توسعه همکاری‌های صنایع دفاعی و انتقال فناوری",
    "انتقال استاد دانشگاه به بیمارستان پس از حادثه",
]
FA_FLAG = ["اعزام ناو آمریکایی به خلیج فارس", "استقرار سامانه تاد در اسرائیل", "اعزام ناوهای جنگی به منطقه"]


def main():
    bad = [("lit", t) for t, lang in NOT_LAMP if lamp(t, lang)] + [("dark", t) for t, lang in LAMP if not lamp(t, lang)]
    bad += [("flag", t) for t in FA_NOT_FLAG if "deploy" in score_fa(t, "")[2]]
    bad += [("no flag", t) for t in FA_FLAG if "deploy" not in score_fa(t, "")[2]]
    for why, t in bad:
        print(f"FAIL ({why}): {t}")
    n = len(NOT_LAMP) + len(LAMP) + len(FA_NOT_FLAG) + len(FA_FLAG)
    print(f"{n - len(bad)}/{n} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
