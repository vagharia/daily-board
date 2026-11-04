"""Live results of the US midterm election (3 Nov 2026): the Senate and the House, for the pinned story.

Source: The Associated Press, the count and the race calls every newsroom uses (AP's own results pages read the same
files): interactives.apelections.org/election-results/data-live/2026-11-03/results/national/ — metadata.json (every
race, its candidates, AP's call status, the party holding the seat) and progress.json (votes, share of the expected
vote counted, the winner AP called, a flipped seat). States certify their results weeks later; until then AP's calls
are the reference.

Seats: the House is all 435 seats; the Senate is the 65 seats not up this year (their parties worked out from the
chamber before the election, 53 Republicans and 47 Democrats with the two independents who caucus with them) plus the
35 races, counted as AP calls them. A winner who is neither a Democrat nor a Republican counts with the party they
caucus with when AP says so.

Writes uselection.json to the `uselection` branch (its own branch, so it never races the news data).

    python -m engine.uselection          # loop: a round every 3 minutes, ROUNDS rounds
"""
import calendar
import gzip
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = "https://interactives.apelections.org/election-results/data-live/2026-11-03/results/national/"
PAGE = "https://apnews.com/projects/elections-2026/"
BRANCH = "uselection"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
# the Senate before the election (119th Congress): 53 Republicans, 45 Democrats and 2 independents with them
SENATE_BEFORE = {"gop": 53, "dem": 47}
SENATE, SENATE_MAJ = 100, 51          # 50 seats and the vice president (a Republican) also hold it for Republicans
HOUSE, HOUSE_MAJ = 435, 218
KEEP_AFTER_DONE = 24 * 3600            # the story stays a day after the last race is called
LAST_DAY = calendar.timegm((2026, 12, 1, 0, 0, 0))   # and goes in any case on 1 December


def _get(name):
    req = urllib.request.Request(BASE + name, headers={"User-Agent": UA, "Referer": PAGE, "Origin": "https://apnews.com",
                                                       "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def _side(party, caucus=None):
    p = caucus or party
    return "dem" if p == "Dem" else "gop" if p == "GOP" else "oth"


def _iso(s):
    try:
        return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError):
        return None


def build(meta, prog, prev=None, t=None):
    t = t or int(time.time())
    states, sen_up, latest = {}, {"dem": 0, "gop": 0, "oth": 0}, 0
    sen = {"dem": 0, "gop": 0, "oth": 0}
    hou = {"dem": 0, "gop": 0, "oth": 0}
    sen_flip = {"dem": 0, "gop": 0, "oth": 0}
    hou_flip = {"dem": 0, "gop": 0, "oth": 0}
    sen_called = hou_called = sen_races = hou_races = 0
    for rid, m in meta.items():
        office = m.get("officeID")
        if office not in ("S", "H") or m.get("statePostal") in (None, "US") or not m.get("raceCallStatus"):
            continue
        p = prog.get(rid) or {}
        st = m["statePostal"]
        cands = m.get("candidates") or {}
        rows = []
        for c in p.get("candidates") or []:
            md = cands.get(c["candidateID"], {})
            if md.get("last") == "Total Write-ins":
                continue
            rows.append({"n": md.get("last", ""), "f": md.get("first", ""), "p": _side(md.get("party"), md.get("caucusWith")),
                         "pa": md.get("party", ""), "v": c.get("voteCount", 0), "pct": c.get("votePct", 0),
                         "w": 1 if c.get("winner") == "X" else 0, "i": 1 if md.get("incumbent") else 0})
        rows.sort(key=lambda r: (-r["w"], -r["v"]))
        win = next((r for r in rows if r["w"]), None)
        lead = rows[0] if rows and rows[0]["v"] > 0 else None
        before = _side(m.get("currentPartyCaucus")) if m.get("currentPartyCaucus") else None
        latest = max(latest, _iso(p.get("lastUpdated")) or 0)
        race = {"id": rid, "seat": m.get("seatNum"), "name": m.get("seatName"), "e": round(p.get("eevp") or 0, 1),
                "win": win["p"] if win else None, "lead": lead["p"] if lead else None, "was": before,
                "flip": 1 if win and before and win["p"] != before else 0,
                "c": [{k: r[k] for k in ("n", "f", "p", "pa", "pct", "w", "i")} for r in rows[:3]]}
        s = states.setdefault(st, {"name": (p.get("stateName") or st), "s": [], "h": []})
        if office == "S":
            sen_races += 1
            if before:
                sen_up[before] += 1
            s["s"].append(race)
            if win:
                sen_called += 1
                sen[win["p"]] += 1
                if race["flip"]:
                    sen_flip[win["p"]] += 1
        else:
            hou_races += 1
            race["c"] = race["c"][:2]
            s["h"].append(race)
            if win:
                hou_called += 1
                hou[win["p"]] += 1
                if race["flip"]:
                    hou_flip[win["p"]] += 1
    for s in states.values():
        s["h"].sort(key=lambda r: int(r["seat"]) if str(r["seat"]).isdigit() else 0)
    held = {k: SENATE_BEFORE.get(k, 0) - sen_up.get(k, 0) for k in ("dem", "gop")}
    prev = prev or {}
    done_t = prev.get("done_t")
    if not done_t and sen_races and sen_called == sen_races and hou_called == hou_races:
        done_t = t
    until = min(done_t + KEEP_AFTER_DONE, LAST_DAY) if done_t else LAST_DAY
    return {"v": 1, "updated": t, "asof": latest or None, "source": "AP", "page": PAGE,
            "senate": {"total": SENATE, "maj": SENATE_MAJ, "held": held, "won": sen, "flips": sen_flip,
                       "races": sen_races, "called": sen_called},
            "house": {"total": HOUSE, "maj": HOUSE_MAJ, "won": hou, "flips": hou_flip, "races": hou_races,
                      "called": hou_called},
            "states": states, "done": bool(done_t), "done_t": done_t, "until": until}


def _git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def publish(doc):
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=json.dumps(doc, ensure_ascii=False,
                                                                                    separators=(",", ":")),
                          check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "mktree"], input=f"100644 blob {blob}\tuselection.json\n", check=True,
                          capture_output=True, text=True).stdout.strip()
    commit = _git("commit-tree", tree, "-m", "uselection " + time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()))
    _git("push", "-f", "origin", f"{commit}:refs/heads/{BRANCH}")


def previous():
    try:
        _git("fetch", "-q", "origin", BRANCH)
        return json.loads(_git("show", f"origin/{BRANCH}:uselection.json"))
    except Exception:  # noqa: BLE001 - first run
        return None


def main():
    rounds = int(os.environ.get("USELECTION_ROUNDS", "9"))
    prev = previous()
    for i in range(rounds):
        t0 = time.time()
        if prev and prev.get("until") and t0 > prev["until"]:
            print("all races called and their day is over: nothing more to do")
            open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a").write("done=1\n")
            return
        try:
            doc = build(_get("metadata.json"), _get("progress.json"), prev)
            key = lambda d: {k: v for k, v in d.items() if k != "updated"}  # noqa: E731
            if not prev or key(doc) != key(prev) or t0 - prev.get("updated", 0) > 1800:
                publish(doc)
                print(f"round {i + 1}: published senate={doc['senate']['won']} held={doc['senate']['held']} "
                      f"house={doc['house']['won']} called={doc['senate']['called']}/{doc['house']['called']}")
            else:
                print(f"round {i + 1}: no change")
            prev = doc
        except Exception as e:  # noqa: BLE001
            print(f"round {i + 1}: failed: {str(e)[:300]}", file=sys.stderr)
        if i < rounds - 1:
            time.sleep(max(0, 180 - (time.time() - t0)))


if __name__ == "__main__":
    main()
