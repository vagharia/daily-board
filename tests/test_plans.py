"""Regression checks: a plan, a demand or pressure to join an attack is not an attack. Neither a red story nor a line
on the main-front panel (flash.events); attacks told as done stay as they were. Run: python3 tests/test_plans.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.classify import classify  # noqa: E402
from engine.flash import events  # noqa: E402

CASES = [  # (an event on the panel?, at most this severity or None, lang, headline)
    (False, 66, "en", "Netanyahu presses US to join Israel in '4-7 day' campaign of airstrikes on Iran: NYT"),
    (False, 66, "en", "Israeli spy chief lobbied for joint Iran strikes on US visit, sources say"),
    (False, 66, "en", "Netanyahu urges Trump to strike Iran's nuclear sites"),
    (False, 66, "en", "Israel asks US to join strikes on Iran"),
    (False, 66, "fa", "نتانیاهو از آمریکا برای پیوستن به اسرائیل در حملات هوایی ۴-۷ روزه به ایران فشار می‌آورد: NYT"),
    (False, 66, "fa", "اسرائیل از آمریکا خواست به حملات هوایی علیه ایران بپیوندد"),
    (False, None, "en", "CENTCOM chief in Israel following US, Iran strikes in Gulf"),
    (True, None, "en", "Israel strikes Iran"),
    (True, None, "en", "Israel bombs Iran"),
    (True, None, "en", "Israel launches airstrikes on Iran"),
    (True, None, "en", "Iran fires missiles at Israel"),
    (True, None, "fa", "حمله هوایی اسرائیل به ایران"),
    (True, None, "fa", "حملات هوایی اسرائیل به ایران آغاز شد"),
]


def main():
    bad = 0
    for ev, cap, lang, t in CASES:
        m = classify({"ti": t, "lang": lang, "s": "test", "su": ""})
        m.update(t=1, k="test")
        got = bool(events(m))
        if got != ev or (cap is not None and m["sev"] > cap):
            bad += 1
            print("FAIL", t, "| event:", got, "sev:", m["sev"], m["flags"])
    print(f"{len(CASES) - bad}/{len(CASES)} ok")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
