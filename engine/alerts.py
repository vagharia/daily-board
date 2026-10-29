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

from . import http
from .util import log, now, truncate

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
        body += "\n⚠️ " + {"cited": "در انتظار تأیید منبع", "quote": "منبع ذکر نشده"}.get(c["unconf"], "گزارش تأییدنشده") \
            + "؛ فعلاً فقط یک کانال تلگرامی گزارشش کرده"
    if summ:
        body += f"\n{summ}"
    if names:
        body += f"\n\n<i>{label}: {src}{more}</i>"       # the sources, one blank line below the story
    return body


def _fa_num(n):
    return "یک" if n == 1 else str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def run(state, clusters, lights, index, first_run=False, flash_msgs=None, flash_keys=None):
    """flash_msgs: the main front's instant alerts (flash.py), sent first; flash_keys: reports they cover, whose
    stories don't also get the red-story alert."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    sent = state.setdefault("sent", [])
    prev_lights = state.setdefault("lights", {})
    t = now()
    red_new = [c for c in clusters if c["tier"] == "red" and c["id"] not in sent
               and not any(x in sent for x in c.get("merged", [])) and t - c["u"] <= 6 * 3600
               and "denial" not in c.get("flags", []) and "past" not in c.get("flags", [])]
    lights_on = [l for l in lights if l["state"] == "on" and prev_lights.get(l["id"]) != "on"]
    zone_up = index and state.get("zone") is not None and index["zone"] > state["zone"]
    messages = []
    fk = flash_keys or set()
    red_msg = [c for c in red_new if not any(m["k"] in fk for m in c["m"])]
    if not first_run:
        red_msg.sort(key=lambda c: -c["sev"])
        for c in red_msg[:4]:
            messages.append(_story(c))
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
    # dollar: trades are posted through the Tehran trading day
    d = (ticker or {}).get("dollar") or {}
    last = d.get("t") or 0
    hour = time.gmtime(t + 12600).tm_hour            # Tehran time (UTC+3:30)
    if last and 11 <= hour < 21 and t - last > 4 * 3600:
        if not sysst.get("usd"):
            sysst["usd"] = t
            msgs.append("⚙️ <b>گزارش فنی بولتن:</b> بیش از ۴ ساعت است معامله تازه‌ای از کانال دلار خوانده نشده. "
                        "شاید کانال پستی نگذاشته یا قالب پیام‌هایش عوض شده؛ اگر ادامه داشت، به Claude بگو.")
    elif last and t - last < 3600 and sysst.get("usd"):
        sysst.pop("usd", None)
        msgs.append("✅ <b>گزارش فنی بولتن:</b> قیمت دلار دوباره به‌روز می‌شود.")
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
