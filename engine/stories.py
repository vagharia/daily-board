"""Stories: up to ten recent orange and yellow reports about the confrontation between Iran and Israel or the US,
chosen every two hours and shown as a row of stories at the top of the news tab (red stories have their own place
at the top of the feed and in the alerts). Unconfirmed reports from Telegram channels are left out."""
from . import config, media
from .http import parallel
from .util import log

EVERY = 2 * 3600
MAX = 10
FRESH = 6 * 3600            # the most important of the last six hours (the whole day when that is too few)
IR_PPL = {"ir_leader", "ir_pres", "ir_fm", "ir_snsc", "irgc_cmd", "ir_army", "ghalibaf", "ir_spox"}
IR_GEO = {"tehran", "isfahan", "natanz", "fordow", "bushehr", "bandar_abbas", "kharg", "tabriz", "shiraz", "chabahar",
          "hormuz", "persian_gulf", "gulf_oman"}
US_IL_PPL = {"trump", "vance", "rubio", "bessent", "hegseth", "witkoff", "us_mil", "il_pm", "il_def", "idf_chief"}


def iran_war(c):
    """Both sides of the confrontation appear: Iran (or its waters) and Israel or the US."""
    iran = "ir" in c.get("ctry", []) or set(c.get("ppl", [])) & IR_PPL or set(c.get("geo", [])) & IR_GEO
    other = set(c.get("ctry", [])) & {"us", "il"} or set(c.get("ppl", [])) & US_IL_PPL
    return bool(iran and other)


def pick(clusters, t, hidden=lambda c: False):
    """The most important such stories of the last few hours, shown newest first, each with a picture where one
    can be found."""
    pool = [c for c in clusters if c["tier"] in ("orange", "yellow") and t - c["t"] <= config.H24 and iran_war(c)
            and "opinion" not in c.get("flags", []) and not c.get("unconf") and not hidden(c)]
    recent = [c for c in pool if t - c["t"] <= FRESH]
    if len(recent) < MAX:
        recent = pool
    chosen = sorted(recent, key=lambda c: (-c["sev"], -c["t"]))[:MAX]
    chosen.sort(key=lambda c: -c["t"])
    _pictures(chosen)
    return chosen


def _pictures(chosen):
    targets = []
    for c in chosen:
        if c.get("img"):
            continue
        pages = [m for m in c["m"] if m.get("via") != "gn" and str(m.get("u", "")).startswith("http")]
        if pages:
            targets.append((c, max(pages, key=lambda m: m.get("rel") or 0)["u"]))
    found = 0
    for (c, _url), meta, err in parallel(lambda x: media.page_meta(x[1]), targets, workers=10):
        if err is None and meta and meta.get("img"):
            c["img"] = meta["img"]
            found += 1
    if targets:
        log(f"stories: pictures found for {found} of {len(targets)}")
