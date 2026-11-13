"""All flights stopped across America or Israel (classify.grounded): red in the bulletin, colour only.
Run: python3 tests/test_ground.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.classify import grounded  # noqa: E402


def _fa(t):
    return {"lang": "fa", "ti": t}


def _en(t):
    return {"lang": "en", "ti": t, "en_ti": t}


def test_nationwide_stop():
    assert grounded(_fa("اداره هوانوردی فدرال آمریکا دستور توقف تمامی پروازها در سراسر ایالات‌متحده را صادر کرد")) == "us"
    assert grounded(_fa("توقف سراسری پروازها در آمریکا؛ دستور اضطراری سازمان هوانوردی فدرال")) == "us"
    assert grounded(_fa("سازمان هوانوردی فدرال آمریکا همهٔ پروازهای خروجی را به‌طور سراسری متوقف کرد")) == "us"
    assert grounded(_fa("تمام پروازهای آمریکا به‌دلیل اختلال در ارتباطات متوقف شد")) == "us"
    assert grounded(_en("FAA orders nationwide ground stop for all flights")) == "us"
    assert grounded(_en("FAA halts all flights across the US")) == "us"
    assert grounded(_fa("اسرائیل تمامی پروازهای فرودگاه بن‌گوریون را متوقف کرد")) == "il"


def test_not_a_nationwide_stop():
    assert not grounded(_en("Ground stop at Newark airport due to weather"))
    assert not grounded(_en("FAA lifts nationwide ground stop, flights resume"))
    assert not grounded(_en("Iran could ground all flights in the US, analyst says"))
    assert not grounded(_fa("توقف پروازها در فرودگاه نیوآرک به دلیل آب و هوا"))
    assert not grounded(_fa("ازسرگیری پروازها در آمریکا پس از توقف سراسری"))
    assert not grounded(_fa("ایران همه پروازها را متوقف کرد"))


if __name__ == "__main__":
    test_nationwide_stop()
    test_not_a_nationwide_stop()
    print("ok")
