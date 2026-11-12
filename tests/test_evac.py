"""Regression checks for the evacuation lamp (index.compute_lights → "evac"): only an order to leave a country lights
it; rescues, fires and forces taken out of a place never do. Run: python3 tests/test_evac.py"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import evac  # noqa: E402
from engine.classify import classify  # noqa: E402


def item(ti, su="", lang="en"):
    it = {"ti": ti, "su": su, "lang": lang, "t": time.time(), "k": ti}
    if lang != "fa":
        it["en_ti"], it["en_su"] = ti, su
    return classify(it)


def lamp(it):
    """Whether a report could light the evacuation lamp (the per-report part of index.compute_lights)."""
    return "evac" in it["flags"] and "evac" in (it.get("tf") or []) and bool(evac.mark(it))


NOT_LAMP = [  # (headline, summary, lang, must be red?)
    ("22 sailors evacuated by UAE Coast Guard after attack on tanker: Indian minister", "", "en", None),
    ("Iran unveils underground ‘Missile City’ after US evacuates second RAF base", "", "en", None),
    ("Fire breaks out at Iran's South Pars gas platform",
     "Operational, safety teams bring blaze under control, all personnel evacuated from SPD14D platform", "en", None),
    ("UAE rescues 22 after fire breaks out on cargo ship in Gulf of Oman",
     "All 22 Arab nationals were safely evacuated by the National Guard's Coast Guard division.", "en", None),
    ("امارات از نجات ۲۲ تن از خدمه یک کشتی باری در دریای عمان خبر داد", "خدمه کشتی تخلیه شدند", "fa", None),
    ("US evacuates aircraft from Qatar's Al Udeid base over Iran threat", "", "en", True),
    ("US troops evacuate Iraq's Ain al-Asad base fearing Iranian retaliation", "", "en", True),
]
LAMP = [
    ("US orders non-emergency staff to leave embassy in Iraq", "", "en"),
    ("Britain tells citizens to leave Lebanon immediately", "", "en"),
    ("UK evacuates embassy staff from Tehran", "", "en"),
    ("آمریکا دستور تخلیه کارکنان غیرضروری سفارت خود در بغداد را صادر کرد", "", "fa"),
]


def main():
    bad = 0
    for ti, su, lang, red in NOT_LAMP:
        it = item(ti, su, lang)
        ok = not lamp(it) and "evac" not in it["flags"] and (red is None or (it["sev"] >= 70) == red)
        bad += not ok
        print("ok  " if ok else "FAIL", "no lamp", it["sev"], sorted(it["flags"]), "|", ti)
    for ti, su, lang in LAMP:
        it = item(ti, su, lang)
        ok = lamp(it)
        bad += not ok
        print("ok  " if ok else "FAIL", "lamp   ", it["sev"], sorted(it["flags"]), it.get("tf"), "|", ti)
    print("failures:", bad)
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
