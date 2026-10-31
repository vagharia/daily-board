"""Telegram alerts: new red stories, warning lights switching on, index moving up a zone.

Setup for the user: create a bot with @BotFather, save its token as the repository secret
TELEGRAM_BOT_TOKEN, then send /start to the bot. Anyone who sends /start gets the alerts (the bot answers within a
round, about five minutes) and /stop ends them; the first chat is the owner's and also gets the technical reports.
Chat ids are stored encrypted (key derived from the token), so they never appear in the public repository or logs.
"""
import base64
import hashlib
import hmac
import html
import os
import time

import re

from . import evac, http, vessel
from .util import fa_norm, log, now, truncate

API = "https://api.telegram.org/bot{token}/{method}"


def _key(token):
    return hashlib.sha256(b"daily-board/" + token.encode()).digest()


def _xor(data: bytes, key: bytes) -> bytes:
    stream = b""
    i = 0
    while len(stream) < len(data):
        stream += hmac.new(key, i.to_bytes(4, "big"), hashlib.sha256).digest()
        i += 1
    return bytes(a ^ b for a, b in zip(data, stream))


def seal(chat_id: str, token: str) -> str:
    return base64.urlsafe_b64encode(_xor(str(chat_id).encode(), _key(token))).decode()


def unseal(blob: str, token: str):
    try:
        return _xor(base64.urlsafe_b64decode(blob.encode()), _key(token)).decode()
    except Exception:  # noqa: BLE001
        return None


def _call(token, method, **payload):
    r = http.post(API.format(token=token, method=method), json_body=payload, timeout=20, retries=1)
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(d.get("description", "telegram error"))
    return d.get("result")


WELCOME = ("✅ <b>هشدارها فعال شد.</b>\nاز این به بعد خبرهای خیلی مهم و چراغ‌های هشدار اینجا ارسال می‌شن.\n"
           "برای قطع هشدارها /stop بفرست.")
AGAIN = "✅ هشدارها برای شما فعال است. برای قطعشان /stop بفرست."
BYE = "هشدارها قطع شد. هر وقت خواستی دوباره /start بفرست."


def _subs(state, token):
    """The chat ids that get the alerts (stored sealed)."""
    out = []
    for blob in state.get("subs", []):
        cid = unseal(blob, token)
        if cid and cid not in out:
            out.append(cid)
    return out


def _set_subs(state, token, ids):
    state["subs"] = [seal(c, token) for c in ids]


def poll(state, token):
    """Read the messages sent to the bot since the last round: /start subscribes a chat (the first one is the
    owner, who also gets the technical reports), /stop unsubscribes it. Each gets a reply."""
    owner = _owner(state, token)
    subs = _subs(state, token)
    if owner and owner not in subs:
        subs.insert(0, owner)
    try:
        updates = _call(token, "getUpdates", offset=state.get("upd", 0) + 1, timeout=0, allowed_updates=["message"])
    except Exception as e:  # noqa: BLE001
        log("telegram getUpdates failed:", str(e)[:80])
        return subs
    for u in updates or []:
        state["upd"] = max(state.get("upd", 0), u.get("update_id", 0))
        msg = u.get("message") or {}
        chat = msg.get("chat") or {}
        text = (msg.get("text") or "").strip()
        if chat.get("type") != "private" or not text.startswith("/"):
            continue
        cid = str(chat.get("id"))
        reply = None
        if text.startswith("/start"):
            reply = AGAIN if cid in subs else WELCOME
            if cid not in subs:
                subs.append(cid)
            if not owner:
                owner = cid
                state["chat"] = seal(cid, token)
        elif text.startswith("/stop"):
            if cid in subs:
                subs.remove(cid)
            reply = BYE
        if reply:
            try:
                _call(token, "sendMessage", chat_id=cid, text=reply, parse_mode="HTML",
                      link_preview_options={"is_disabled": True})
            except Exception as e:  # noqa: BLE001
                log("telegram reply failed:", str(e)[:80])
    _set_subs(state, token, subs)
    return subs


def _owner(state, token):
    env = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if env:
        return env
    return unseal(state["chat"], token) if state.get("chat") else None


def _chat_id(state, token):
    """The owner's chat (technical reports go only there)."""
    return _owner(state, token)


def send_all(state, token, subs, messages):
    """Send each message to every subscriber; a chat that blocked the bot is dropped. Returns messages sent."""
    ok, gone = 0, []
    for cid in subs:
        for msg in messages:
            try:
                _call(token, "sendMessage", chat_id=cid, text=msg, parse_mode="HTML",
                      link_preview_options={"is_disabled": True})
                ok += 1
            except Exception as e:  # noqa: BLE001
                err = str(e)
                log("telegram send failed:", err[:80])
                if "blocked" in err or "chat not found" in err or "deactivated" in err:
                    gone.append(cid)
                    break
    if gone:
        _set_subs(state, token, [c for c in subs if c not in gone])
    return ok


def _story(c):
    fa = c.get("fa") or {}
    title = html.escape(fa.get("ti") or c.get("en", {}).get("ti", ""))
    summ = html.escape(truncate(fa.get("su") or "", 230))
    names = []
    for m in c["m"]:
        n = m.get("sn_fa") or m.get("sn")
        if n and n not in names:
            names.append(n)
    src = "، ".join(html.escape(n) for n in names[:3])
    more = f" و {_fa_num(len(names) - 3)} منبع دیگر" if len(names) > 3 else ""
    label = "منبع" if len(names) == 1 else "منابع"
    body = (f"✅ <b>{title}</b>\n🟢 کاهش تنش" if c.get("green") and not c.get("unconf") else f"🔴 <b>{title}</b>")
    if c.get("unconf"):
        body += "\n⚠️ " + {"cited": "در انتظار تأیید منبع", "quote": "منبع ذکر نشده", "analysis": "تحلیل کانال"}.get(c["unconf"],
                                                                                                  "گزارش تأییدنشده") \
            + "؛ فعلاً فقط یک کانال تلگرامی گزارشش کرده"
    if summ:
        body += f"\n{summ}"
    if names:
        body += f"\n\n<i>{label}: {src}{more}</i>"       # the sources, one blank line below the story
    return body


def _fa_num(n):
    return "یک" if n == 1 else str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


# ------------------------------------------------------------------ incidents at sea: one alert each
# Reports of one incident at sea come from many outlets over many hours and form many stories; an Iranian claim
# about tankers is published again and again. Telegram gets: one alert per incident (and at most one update when a
# report adds something important: a sinking, people hurt, who did it, how), no alert for a claim already
# announced, none for live pages and recaps. The bulletin is not affected.
SEA_KEEP = 24 * 3600         # an incident placed by distance and bearing is remembered this long
SEA_VAGUE = 6 * 3600         # a report that gives no place counts as the incident announced in that sea area this soon
CLAIM_KEEP = 36 * 3600       # an Iranian claim already announced is not announced again within this
SEA_UPDATES = 1
_RECAP_EN = re.compile(r"\blive\b|\bmore on\b|\blatest:|\bwhat we know\b|\bexplainer\b|\brecap\b|\bround-?up\b"
                       r"|\bwatch:|\bday \d+\b|\bas (?:\w+ ){0,3}(?:attacks?|tensions?|incidents?|strikes?) "
                       r"(?:escalate|mount|intensify|persist|grow|rise)", re.I)
_RECAP_FA = re.compile(fa_norm("لحظه به لحظه|جمع بندی|مروری بر|گزارش زنده|پخش زنده|اطلاعات بیشتر در مورد|جزئیات بیشتر"))


def _heads(c):
    return (c.get("en") or {}).get("ti") or "", fa_norm((c.get("fa") or {}).get("ti") or "")


def _at_sea(c):
    en, fa = _heads(c)
    return bool(vessel.SHIP_EN.search(en) or vessel.SHIP_FA.search(fa)
                or any("maritime_incident" in (m.get("flags") or []) for m in c["m"]))


def _recap(c):
    en, fa = _heads(c)
    return bool(_RECAP_EN.search(en) or _RECAP_FA.search(fa))


def _claims(c):
    """Keys of the Iranian statements about ships a story's reports tell: who, how many, a super tanker, ships stopped,
    "the third" ("irgc|3|||": the IRGC's three tankers)."""
    out = set()
    for m in c["m"]:
        x = vessel.signature(m)
        if x:
            out.add("|".join([x["who"], ",".join(str(n) for n in x["nums"]), "S" if x["super"] else "",
                              "T" if x["stop"] else "", str(x["ord"] or "")]))
    return out


def _repeatable(k):
    """Only a statement with a count and no "second", "third" can be a repeat: "IRGC: 3 tankers" told again."""
    who, nums, sup, stop, ord_ = k.split("|")
    return bool(nums) and not ord_


def _head_claim(c):
    """A story of an Iranian statement about ships: some of its reports are such statements, none an incident told
    independently."""
    sts = [m for m in c["m"] if vessel.signature(m)]
    return bool(sts) and not any(vessel.mark(m) or ("maritime_incident" in (m.get("flags") or [])
                                                     and not vessel.statement(m)) for m in c["m"])


SEA_FRESH = 6 * 3600         # an incident the reports place in time earlier than this is not announced


def _old(c, t):
    """True if the reports say when it happened and that is more than six hours ago."""
    ws = [w for w in (vessel.when(m) for m in c["m"]) if w]
    return bool(ws) and max(w[1] for w in ws) < t - SEA_FRESH


def _incident(c):
    """(place, sea area, facts, tells of another ship, time of its latest report giving the place) of a story."""
    ms = sorted(c["m"], key=lambda m: m["t"])
    marked = [(m, vessel.mark(m)) for m in ms]
    marked = [(m, x) for m, x in marked if x]
    mk = marked[0][1] if marked else None
    mt = marked[-1][0]["t"] if marked else None
    ar = mk["area"] if mk else next((a for a in (vessel.area(m, head=True) for m in ms) if a), None)
    fx = set().union(*(vessel.facts(m) for m in ms)) if ms else set()
    another = vessel.another({"en_ti": _heads(c)[0], "ti": (c.get("fa") or {}).get("ti") or "", "lang": "fa"})
    return mk, ar, fx, another, mt


SEA_ADOPT = 3 * 3600          # a placed report gives its place to a vague incident announced this soon before it


def _sea_pick(sea, c, t, quiet=False, first=None):
    """'send', 'update' or None (not announced) for a red story about ships; records what was announced.
    t: now (or, for a story already announced, its latest report); first: when the story was first reported.
    A report that gives no place counts as an incident in that sea area if it comes within six hours of the latest
    report that placed the incident (or of its first report), and within a day of its first report."""
    first = t if first is None else first
    claims = sea.setdefault("claims", {})
    incs = sea.setdefault("inc", [])
    if _recap(c):
        return None
    if _old(c, t):
        return None                                  # the reports place it hours ago: told again, not new
    keys = _claims(c)
    if _head_claim(c) and keys:
        new = {k for k in keys if not _repeatable(k) or first - claims.get(k, -1e12) > CLAIM_KEEP}
        for k in keys:
            claims[k] = max(claims.get(k, 0), t)
        return "send" if new and not quiet else None
    mk, ar, fx, another, mt = _incident(c)
    inc = None
    if mk:
        inc = next((i for i in incs if i.get("mk") and vessel.same(i["mk"], mk) and first - i["t"] <= SEA_KEEP), None)
        if not inc:
            inc = next((i for i in reversed(incs) if not i.get("mk") and i.get("area") == ar and ar
                        and 0 <= first - i["t0"] <= SEA_ADOPT), None)
            if inc:
                inc["mk"] = mk                       # the place the first, vague report didn't give
    elif ar and not another:
        inc = next((i for i in reversed(incs) if i.get("area") == ar and first - i.get("tm", i["t0"]) <= SEA_VAGUE
                    and first - i["t0"] <= SEA_KEEP), None)
    if inc:
        inc["t"] = max(inc["t"], t)
        if mt:
            inc["tm"] = max(inc.get("tm", inc["t0"]), mt)
        new = fx - set(inc.get("fx", []))
        inc["fx"] = sorted(set(inc.get("fx", [])) | fx)
        if new and inc.get("upd", 0) < SEA_UPDATES and not quiet:
            inc["upd"] = inc.get("upd", 0) + 1
            return "update"
        return None
    incs.append({"t0": first, "t": t, "tm": mt or first, "mk": mk, "area": ar, "fx": sorted(fx), "upd": 0})
    return None if quiet else "send"


def _sea_state(state, clusters, sent, t):
    """The memory of incidents and claims at sea; the first time, made from the red stories about ships already
    announced in the last day."""
    sea = state.setdefault("sea", {})
    sea["inc"] = [i for i in sea.get("inc", []) if t - i["t"] <= SEA_KEEP]
    for i in sea["inc"]:
        if i.get("mk"):
            i["mk"] = {**i["mk"], "nm": frozenset(i["mk"]["nm"])}
    sea["claims"] = {k: v for k, v in sea.get("claims", {}).items() if t - v <= CLAIM_KEEP}
    seen = sea["seen"] = {k: v for k, v in sea.get("seen", {}).items() if t - v <= SEA_KEEP}
    sent = set(sent)
    for c in sorted(clusters, key=lambda c: c["t"]):
        # stories already announced: what they tell is known, including the reports that joined them since
        if c["tier"] != "red" or c["id"] not in sent or t - c["u"] > SEA_KEEP or not _at_sea(c):
            continue
        if _head_claim(c):
            for k in _claims(c):
                sea["claims"].setdefault(k, c["u"])
        if c["id"] not in seen:
            _sea_pick(sea, c, c["u"], quiet=True, first=c["t"])
            seen[c["id"]] = c["u"]
    return sea


def _sea_save(sea):
    for i in sea.get("inc", []):
        if i.get("mk"):
            i["mk"] = {**i["mk"], "nm": sorted(i["mk"]["nm"])}


LATE = 2 * 3600            # a report seen this long after it was published is old news by then: no alert


def _late(c, seen):
    """Every report of the story reached the bulletin over two hours after it was published (a search feed showing
    it late): announced now it would be old news."""
    return bool(seen) and all(seen.get(m["k"], m["t"]) - m["t"] > LATE for m in c["m"])


def run(state, clusters, lights, index, first_run=False, flash_msgs=None, flash_keys=None, seen=None):
    """flash_msgs: the main front's instant alerts (flash.py), sent first; flash_keys: reports they cover, whose
    stories don't also get the red-story alert."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    sent = state.setdefault("sent", [])
    prev_lights = state.setdefault("lights", {})
    t = now()
    red_new = [c for c in clusters if c["tier"] == "red" and c["id"] not in sent
               and not any(x in sent for x in c.get("merged", [])) and t - c["u"] <= 6 * 3600
               and "denial" not in c.get("flags", []) and "past" not in c.get("flags", [])
               and not any(evac.stale(m) for m in c["m"]) and not _late(c, seen)]       # an order to leave retold days after it took effect
    lights_on = [l for l in lights if l["state"] == "on" and prev_lights.get(l["id"]) != "on"]
    zone_up = index and state.get("zone") is not None and index["zone"] > state["zone"]
    messages = []
    fk = flash_keys or set()
    red_msg = [c for c in red_new if not any(m["k"] in fk for m in c["m"])]
    sea = _sea_state(state, clusters, sent, t)
    upd = set()
    keep = []
    for c in sorted(red_msg, key=lambda c: c["t"]):     # stories about ships: one alert per incident (see above)
        if not _at_sea(c):
            keep.append(c)
            continue
        how = _sea_pick(sea, c, t, quiet=first_run, first=c["t"])
        sea["seen"][c["id"]] = t
        if how:
            keep.append(c)
            if how == "update":
                upd.add(c["id"])
    _sea_save(sea)
    red_msg = keep
    if not first_run:
        red_msg.sort(key=lambda c: -c["sev"])
        for c in red_msg[:4]:
            msg = _story(c)
            if c["id"] in upd:
                msg = msg.replace("🔴 <b>", "🔄 <b>به‌روزرسانی: ", 1)
            messages.append(msg)
        if len(red_msg) > 4:
            messages.append(f"🔴 و {_fa_num(len(red_msg) - 4)} خبر قرمز دیگر در بولتن.")
        for l in lights_on:
            ev = l["evidence"][0] if l["evidence"] else None
            line = html.escape(ev.get("fa", "")) if ev else ""
            messages.append(f"⚠️ <b>چراغ هشدار روشن شد: {html.escape(l['fa'])}</b>" + (f"\n{line}" if line else ""))
        if zone_up:
            messages.append(f"📈 <b>شاخص تنش: {index['value']}</b> ({html.escape(index['label_fa'])})")
    # remember state even without a token so enabling alerts later doesn't flood
    for c in red_new:
        sent.append(c["id"])
    state["sent"] = sent[-800:]
    state["lights"] = {l["id"]: l["state"] for l in lights}
    if index:
        state["zone"] = index["zone"]
    if not token:
        return {"enabled": False, "queued": len(messages) + len(flash_msgs or [])}
    subs = poll(state, token)
    if not subs:
        return {"enabled": True, "chat": False, "queued": len(messages)}
    messages = list(flash_msgs or []) + messages[:7]
    ok = send_all(state, token, subs, messages) if messages else 0
    return {"enabled": True, "chat": True, "subscribers": len(subs), "sent": ok}


# ------------------------------------------------------------------ engine self-check
def _names(hs):
    names = "، ".join(html.escape(h.get("fa") or h["id"]) for h in hs[:8])
    return names + (f" و {len(hs) - 8} منبع دیگر" if len(hs) > 8 else "")


def system(state, sources, ticker, tr_stats, full):
    """Tell the owner, with a silent message, when sources stay down for hours, the dollar channel stops
    yielding trades during trading hours, or translation breaks. One message per problem and one when it
    recovers. Returns the number of messages."""
    t = now()
    first = "sys" not in state
    sysst = state.setdefault("sys", {"down": {}, "told": {}})
    down, told = sysst.setdefault("down", {}), sysst.setdefault("told", {})
    msgs = []
    if full and sources:
        newly, back = [], []
        for h in sources:
            sid = h["id"]
            if not h.get("ok"):
                if sid not in down:
                    down[sid] = t
                    if first:
                        told[sid] = t          # already failing when the check started: not news
                elif t - down[sid] >= 3 * 3600 and sid not in told:
                    told[sid] = t
                    newly.append(h)
            elif sid in down:
                if sid in told and t - down[sid] >= 3 * 3600:
                    back.append(h)
                down.pop(sid, None)
                told.pop(sid, None)
        ok_n = sum(1 for h in sources if h.get("ok"))
        if ok_n < 0.6 * len(sources):
            if t - sysst.get("mass", 0) > 6 * 3600:
                sysst["mass"] = t
                msgs.append(f"⚙️ <b>گزارش فنی بولتن:</b> فقط {ok_n} از {len(sources)} منبع جواب دادند. احتمالاً مشکل از "
                            "شبکه سرور است و خودش برطرف می‌شود؛ اگر چند ساعت ادامه داشت، به Claude بگو بررسی کند.")
        elif newly:
            msgs.append(f"⚙️ <b>گزارش فنی بولتن:</b> این منابع بیش از ۳ ساعت است جواب نمی‌دهند: {_names(newly)}. "
                        "بقیه منابع کار می‌کنند؛ اگر برایت مهم است، به Claude بگو بررسی کند.")
        if back:
            msgs.append(f"✅ <b>گزارش فنی بولتن:</b> این منابع دوباره جواب می‌دهند: {_names(back)}")
    # the dollar channel going quiet is not reported: the market is closed on Fridays and holidays, and the bulletin
    # shows the time of the latest trade anyway
    sysst.pop("usd", None)
    # translation
    done = sum(v for k, v in (tr_stats or {}).items() if k in ("single", "multi", "clients5"))
    failed = (tr_stats or {}).get("failed", 0)
    if failed >= 20 and failed > 0.3 * (failed + done) and t - sysst.get("tr", 0) > 12 * 3600:
        sysst["tr"] = t
        msgs.append(f"⚙️ <b>گزارش فنی بولتن:</b> ترجمه خودکار در آخرین دور برای {failed} متن خطا داد؛ این خبرها "
                    "فعلاً به زبان اصلی نمایش داده می‌شوند و دور بعد دوباره ترجمه می‌شوند.")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not msgs or not token:
        return len(msgs)
    cid = _chat_id(state, token)
    if not cid:
        return len(msgs)
    for m in msgs[:3]:
        try:
            _call(token, "sendMessage", chat_id=cid, text=m, parse_mode="HTML", disable_notification=True,
                  link_preview_options={"is_disabled": True})
        except Exception as e:  # noqa: BLE001
            log("telegram system message failed:", str(e)[:80])
    return len(msgs)
