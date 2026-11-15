"""Regression checks for Iran's attacks abroad (abroad_strike.py; cluster.abroad_when and the rules after it): which
reports get a mark, which places are one attack, and how time keeps one attack one story and two attacks two.
Run: python3 tests/test_abroad.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import abroad_strike  # noqa: E402
from engine.classify import classify  # noqa: E402
from engine.cluster import Clusterer  # noqa: E402

MARKS = [  # (country, targets or "-" for no mark, lang, headline)
    ("bh", "us_base", "en", "Iran targets US military base in Bahrain with drone attack"),
    ("bh", "", "en", "Bahrain says air defenses intercepted, destroyed Iranian drones"),
    ("bh", "", "en", "Bahraini defence forces say several Iranian aerial attacks neutralised"),
    ("bh", "us_base", "en", "Iran Strikes Bahrain Base, Repeats Path to US Deal Remains Open"),
    ("bh", "riffa", "fa", "رادار سایت پدافندی آمریکا در پایگاه بالگردی الرفاع بحرین با ۶ فروند پهپاد مورد هدف قرار گرفت"),
    ("bh", "us_base", "fa", "حملات سپاه به پایگاه‌های آمریکا در بحرین"),
    ("bh", "us_base", "fa", "آژیرها در بحرین به صدا درآمد؛ سپاه می‌گوید رادار آمریکا را زده است"),
    ("qa", "al_udeid", "en", "Iranian missiles hit Al Udeid"),
    ("iq", "ain_asad", "en", "Drone attack on Ain al-Asad base"),
    ("om", "", "en", "Iranian drones hit port in Oman"),
    ("-", "", "en", "US strikes Iran from bases in Qatar"),
    ("-", "", "en", "Iran-backed militia attack US base in Iraq"),
    ("-", "", "en", "Houthis target Riyadh with ballistic missiles"),
    ("-", "", "en", "Iran threatens to strike US bases in Bahrain"),
    ("-", "", "en", "Saudi Arabia condemns Iranian attacks on Bahrain"),
    ("-", "", "en", "Iran seizes tanker in Gulf of Oman"),
    ("-", "", "fa", "صدا و سیمای جمهوری اسلامی اعلام کرد موشک خرمشهر می‌تواند به پایگاه آمریکا در بریتانیا برسد"),
]

SAME = [  # (level, headline a, headline b): all English
    (2, "Iran targets US military base in Bahrain", "Iranian drones hit Bahrain's Riffa base"),
    (0, "Iranian drones hit Bahrain's Riffa base", "Iranian drones hit Isa air base in Bahrain"),
    (0, "Iranian drones hit Bahrain's Riffa base", "Iranian drone hits Bapco refinery in Bahrain"),
    (1, "Iran attacks Bahrain", "Iranian drones hit Bahrain's Riffa base"),
    (2, "Iran attacks Bahrain", "Bahrain intercepts Iranian drones"),
    (0, "Iran attacks Bahrain", "Iranian missiles hit Al Udeid"),
]

H = 3600
T0 = 1794700000
EN_OF = {}  # Persian headline -> its English (as the translation would give)


def item(ti, t, lang="en", src=None, en=None):
    it = {"ti": ti, "su": "", "lang": lang, "t": T0 + t, "k": f"{ti}|{t}", "rel": 0.9,
          "s": src or ("fars" if lang == "fa" else "reuters"), "sn": src or "x"}
    it["en_ti"], it["en_su"] = (en or ti) if lang == "fa" else ti, ""
    return classify(it)


# stories as they should come out: each scenario is [(story label, hours after T0, lang, headline[, English])]
SCENARIOS = [
    ("one attack told all day, in many words", [
        ("A", 0.0, "fa", "حملات سپاه به پایگاه‌های آمریکا در بحرین", "IRGC attacks on US bases in Bahrain"),
        ("A", 0.2, "fa", "رادار سایت پدافندی آمریکا در پایگاه بالگردی الرفاع بحرین با ۶ فروند پهپاد مورد هدف قرار گرفت",
         "US air defence radar site at Riffa helicopter base in Bahrain targeted with 6 drones"),
        ("A", 0.9, "en", "Iran Attacks Bahrain as Conflict Escalates"),
        ("A", 2.0, "en", "Bahrain says air defenses intercepted, destroyed Iranian drones"),
        ("A", 4.2, "en", "Iran Strikes Bahrain Base, Repeats Path to US Deal Remains Open"),
        ("A", 6.5, "en", "Iran claims attack on US military airbase in Bahrain"),
        ("A", 7.4, "en", "Blasts rattle Bahrain as Iran launches second drone attack in 3 days"),
        ("A", 9.7, "en", "Iran targets US military base in Bahrain with drone attack"),
    ]),
    ("two targets in one country are two attacks", [
        ("A", 0.0, "en", "Iranian drones hit Bahrain's Riffa base"),
        ("B", 0.5, "en", "Iranian drone hits Bapco refinery in Bahrain"),
        ("A", 1.0, "en", "Iran says it struck Riffa base in Bahrain"),
    ]),
    ("two countries are two attacks", [
        ("A", 0.0, "en", "Iran attacks Bahrain as conflict escalates"),
        ("B", 0.3, "en", "Iranian missiles hit Al Udeid air base in Qatar"),
        ("C", 0.4, "en", "Houthi missiles intercepted over Riyadh"),
    ]),
    ("told as it happens after a quiet spell: a new attack", [
        ("A", 0.0, "en", "Iran targets US military base in Bahrain with drone attack"),
        ("A", 1.0, "en", "Bahrain says air defenses intercepted several Iranian attacks"),
        ("B", 5.0, "en", "Blasts heard in Bahrain as Iranian drones intercepted"),
    ]),
    ("the next day: a time told joins, a plain report is a new attack", [
        ("A", 0.0, "fa", "حمله پهپادی سپاه به پایگاه آمریکا در بحرین", "IRGC drone attack on US base in Bahrain"),
        ("A", 0.5, "en", "Bahrain says air defenses intercepted Iranian drones"),
        ("A", 20.0, "en", "Iran struck US base in Bahrain early this morning, officials say"),
        ("B", 20.5, "en", "Iran targets US military base in Bahrain with drones"),
    ]),
    ("a later account joins the latest attack only", [
        ("A", 0.0, "en", "Iran targets US military base in Bahrain with drone attack"),
        ("B", 26.0, "en", "Iranian drones hit US base in Bahrain"),
        ("B", 33.0, "en", "Satellite images show damage at US base in Bahrain after Iranian strike"),
    ]),
]


def run_scenario(steps):
    cl = Clusterer([])
    got = {}
    for s in steps:
        label, h, lang, ti = s[:4]
        c, _ = cl.add(item(ti, int(h * H), lang, en=s[4] if len(s) > 4 else None))
        got[(label, ti, h)] = c
    # the story each report ended in (folds may have moved it): by its key
    where = {m["k"]: c["id"] for c in cl.clusters for m in c["m"]}
    ids = {}
    bad = []
    for (label, ti, h) in got:
        sid = where[f"{ti}|{int(h * H)}"]
        ids.setdefault(label, set()).add(sid)
    for label, s in ids.items():
        if len(s) != 1:
            bad.append(f"story {label} split in {len(s)}")
    labels = list(ids)
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if ids[a] & ids[b]:
                bad.append(f"stories {a} and {b} joined")
    return bad


def main():
    bad = 0
    for want_c, want_t, lang, ti in MARKS:
        m = item(ti, 0, lang)
        g = abroad_strike.mark(m)
        got_c = g[0] if g else "-"
        got_t = ",".join(sorted(g[2])) if g else ""
        if got_c != want_c or (g and got_t != want_t):
            bad += 1
            print(f"FAIL mark want {want_c} {want_t} got {got_c} {got_t}: {ti}")
    for want, a, b in SAME:
        n = abroad_strike.same(abroad_strike.mark(item(a, 0)), abroad_strike.mark(item(b, 0)))
        if n != want:
            bad += 1
            print(f"FAIL same want {want} got {n}: {a} / {b}")
    for name, steps in SCENARIOS:
        errs = run_scenario(steps)
        if errs:
            bad += 1
            print(f"FAIL {name}: {'; '.join(errs)}")
    n = len(MARKS) + len(SAME) + len(SCENARIOS)
    print(f"{n - bad}/{n} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
