"""Regression checks for the tension-index Telegram message (alerts._zone_msg, _held_zone): a swing around a zone
boundary sends one message, not one per crossing. Run: python3 tests/test_zone.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.alerts import ZONE_QUIET, _held_zone, _zone_msg  # noqa: E402
from engine.index import zone  # noqa: E402


def play(values, step=600, state=None):
    state = state if state is not None else {"zone": zone(values[0])[0]}
    sent, t = [], 1_000_000
    for v in values:
        idx = {"value": v, "zone": zone(v)[0]}
        if _zone_msg(state, idx, t):
            sent.append(v)
        state["zone"] = _held_zone(state, idx)
        t += step
    return sent, state


CASES = [  # (values each round, messages expected)
    ([70, 79, 74, 74, 75, 74, 75, 74, 75], [79]),          # today's swing at 75: once
    ([70, 72, 71, 70], []),                                   # no zone change
    ([70, 76, 68, 76], [76]),                                 # left critical (68 < 70) but back within 6 h: quiet
    ([40, 52, 49, 51, 48, 50], [52]),                         # swing at 50
    ([40, 80], [80]),                                         # jump two zones: one message
]

bad = 0
for vals, want in CASES:
    got, _ = play(vals)
    if got != want:
        bad += 1
        print("FAIL", vals, "got", got, "want", want)

# left the zone for real and came back after the quiet time: announced again
got, st = play([70, 76, 65])
got2, _ = play([76], state=dict(st, zone_at={k: v - 2 * ZONE_QUIET for k, v in st["zone_at"].items()}))
if got + got2 != [76, 76]:
    bad += 1
    print("FAIL quiet time over", got, got2)

print("ok" if not bad else f"{bad} failed")
sys.exit(1 if bad else 0)
