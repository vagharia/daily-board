"""Regression checks for the warning lamps (index.compute_lights; lamps.py): a headline, classified and made a story
of one report, lights only the lamps it should. Run: python3 tests/test_lamps.py"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.classify import classify, cluster_severity, tier  # noqa: E402
from engine.cluster import is_core  # noqa: E402
from engine.index import compute_lights  # noqa: E402

CASES = [  # (lamps that must be on, lang, headline)
    ("strike", "en", "US strikes Iran's Qeshm Island"),
    ("strike", "en", "Israeli jets bomb military sites near Tehran"),
    ("strike", "en", "Iran fires missiles at US base in Qatar"),
    ("strike", "fa", "حمله موشکی اسرائیل به اصفهان"),
    ("strike", "fa", "پایگاه آمریکا در بحرین هدف حمله موشکی ایران قرار گرفت"),
    ("strike", "en", "Iran attacks shipping navigation systems on Oman's Didamar island"),
    ("strike", "fa", "انفجارهای پی‌درپی در شیراز؛ پدافند فعال شد"),
    ("strike", "fa", "صدای انفجار در اصفهان شنیده شد"),
    ("", "fa", "انفجار در پالایشگاه آبادان بر اثر نشت گاز"),
    ("", "fa", "انفجار کپسول گاز در یک منزل مسکونی در شیراز"),
    ("", "en", "Iran says no commitment to IAEA monitoring because of attacks on nuclear sites"),
    ("", "en", "Qatar secured two-week window to prevent US attack on Iran"),
    ("", "en", "Trump says US could strike Iran within days"),
    ("", "en", "Oil prices rose after US forces downed Iranian drones"),
    ("", "fa", "انتقاد ایران از سکوت گروسی در برابر حملات به تأسیسات هسته‌ای"),
    ("", "fa", "ارتش اسرائیل: برای حمله به ایران آماده‌ایم"),
    ("", "en", "Houthis fire missile at Riyadh, Saudi coalition says"),
    ("", "en", "Iran denies reports of Israeli strike on Isfahan"),
    ("", "en", "Saudi Arabia suspends flights at Abha airport after Houthi drone attack"),
    ("", "en", "Israel strikes Hezbollah targets in southern Lebanon"),
    ("hormuz", "en", "Tanker hit by projectile in Strait of Hormuz, UKMTO says"),
    ("hormuz", "en", "Iran closes Strait of Hormuz to shipping"),
    ("hormuz", "en", "IRGC seizes foreign tanker in Strait of Hormuz"),
    ("hormuz", "fa", "سپاه: یک نفتکش متخلف در تنگه هرمز با مین برخورد کرد"),
    ("hormuz", "fa", "ارتش: یک نفت‌کش متخلف در شرق تنگه هرمز بر اثر برخورد با مین، دچار حریق شد"),
    ("hormuz", "fa", "انفجار یک نفتکش متخلف بر اثر برخورد با مین در تنگه هرمز"),
    ("hormuz", "en", "Iran says tanker carrying LNG hit mine, suffered explosion in Hormuz"),
    ("", "fa", "سپاه: هر نفتکشی از مسیر غیرمجاز عبور کند با مین برخورد می‌کند"),
    ("", "en", "Trump calls Hormuz blockade 'the greatest in history'"),
    ("", "en", "Iran will never close the Strait of Hormuz, foreign minister says"),
    ("", "en", "Iran threatens to close Strait of Hormuz if attacked"),
    ("", "en", "Shipping insurers raise Hormuz premiums"),
    ("airspace", "en", "Iran closes its airspace to all flights"),
    ("airspace", "fa", "حریم هوایی عراق بسته شد"),
    ("", "en", "Iran reopens airspace after brief closure"),
    ("", "en", "Flights cancelled at Dubai airport due to fog"),
    ("evac", "en", "US orders non-emergency staff to leave embassy in Baghdad"),
    ("evac", "fa", "انگلیس به اتباع خود دستور داد فوراً لبنان را ترک کنند"),
    ("", "en", "Residents evacuated after fire in Tehran high-rise"),
    ("", "en", "US denies plans to evacuate embassy in Bahrain"),
    ("ultimatum", "en", "Trump gives Iran 48-hour ultimatum to reopen Hormuz"),
    ("", "en", "Vance: we did not set a deadline for Iran"),
    ("", "fa", "مهلت ثبت‌نام کنکور تمدید شد"),
    ("deploy", "en", "US sends third aircraft carrier to Middle East"),
    ("", "en", "Chinese carrier Fujian enters South China Sea"),
]


def lamps_on(ti, lang):
    t = time.time()
    it = {"ti": ti, "su": "", "lang": lang, "t": t, "k": ti, "rel": 0.9, "src": "x"}
    if lang != "fa":
        it["en_ti"], it["en_su"] = ti, ""
    m = classify(it)
    c = {"id": "x", "t": t, "u": t, "m": [m], "sev": cluster_severity([m["sev"]], 1, 0.9), "flags": m["flags"],
         "ctry": m["ctry"], "geo": m["geo"], "ppl": m["ppl"], "en": {"ti": ti}, "fa": {"ti": ti}}
    c["tier"], c["core"] = tier(c["sev"]), is_core(c)
    return sorted(x["id"] for x in compute_lights([c], {}, {}, {}, t=t + 60) if x["state"] == "on")


def main():
    bad = 0
    for want, lang, ti in CASES:
        got = lamps_on(ti, lang)
        if got != sorted(x for x in want.split(",") if x):
            bad += 1
            print(f"FAIL want {want or '-'} got {got}: {ti}")
    print(f"{len(CASES) - bad}/{len(CASES)} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
