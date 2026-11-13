"""Dates in translations (translate.fix_dates): a date of one calendar comes out right in the other.
Run: python3 tests/test_dates.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import translate  # noqa: E402
from engine.translate import fix_terms  # noqa: E402

translate.now = lambda: 1794607398           # 13 November 2026 (22 Aban 1405)


def test_dates():
    fa = "سازمان هوانوردی فدرال آمریکا روز جمعه ۲۲ آبان دستور توقف سراسری داد."
    assert fix_terms(fa, "On Friday, November 22, the FAA", "en") == "On Friday, November 13, the FAA"
    assert fix_terms(fa, "On Friday 22 Aban the FAA", "en") == "On Friday November 13 the FAA"
    assert fix_terms(fa, "On Friday, November 13, the FAA", "en") == "On Friday, November 13, the FAA"
    assert fix_terms("در ۵ فروردین", "on March 5", "en") == "on March 25"
    en = "The FAA on Friday, November 13, ordered all flights grounded."
    assert fix_terms(en, "روز جمعه ۱۳ آبان دستور داد", "fa") == "روز جمعه ۲۲ آبان دستور داد"
    assert fix_terms(en, "روز جمعه ۱۳ نوامبر دستور داد", "fa") == "روز جمعه ۱۳ نوامبر دستور داد"


if __name__ == "__main__":
    test_dates()
    print("ok")
