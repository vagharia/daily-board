"""Telegram alerts: new red stories, warning lights switching on, index moving up a zone.

Setup for the user: create a bot with @BotFather, save its token as the repository secret
TELEGRAM_BOT_TOKEN, then send /start to the bot. The first chat that sends /start is locked in.
Its chat id is stored encrypted (key derived from the token), so it never appears in the
public repository or logs.
"""
import base64
import hashlib
import hmac
import html
import os

from . import config, http
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


def _chat_id(state, token):
    env = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if env:
        return env
    if state.get("chat"):
        cid = unseal(state["chat"], token)
        if cid:
            return cid
    try:
        updates = _call(token, "getUpdates", timeout=0, allowed_updates=["message"])
    except Exception as e:  # noqa: BLE001
        log("telegram getUpdates failed:", str(e)[:80])
        return None
    for u in updates or []:
        msg = u.get("message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") == "private" and (msg.get("text") or "").strip().startswith("/start"):
            cid = str(chat.get("id"))
            state["chat"] = seal(cid, token)
            try:
                _call(token, "sendMessage", chat_id=cid, parse_mode="HTML",
                      text="✅ <b>هشدارها فعال شد.</b>\nاز این به بعد خبرهای خیلی مهم و چراغ‌های هشدار اینجا ارسال می‌شن.",
                      link_preview_options={"is_disabled": True})
            except Exception as e:  # noqa: BLE001
                log("telegram welcome failed:", str(e)[:80])
            return cid
    return None


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
    more = f" و {len(names) - 3} منبع دیگر" if len(names) > 3 else ""
    body = f"🔴 <b>{title}</b>"
    if summ:
        body += f"\n{summ}"
    body += f"\n<i>{src}{more}</i>"
    return body


def run(state, clusters, lights, index, first_run=False):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    sent = state.setdefault("sent", [])
    prev_lights = state.setdefault("lights", {})
    t = now()
    red_new = [c for c in clusters if c["tier"] == "red" and c["id"] not in sent and t - c["u"] <= 6 * 3600
               and "denial" not in c.get("flags", []) and "past" not in c.get("flags", [])]
    lights_on = [l for l in lights if l["state"] == "on" and prev_lights.get(l["id"]) != "on"]
    zone_up = index and state.get("zone") is not None and index["zone"] > state["zone"]
    messages = []
    if not first_run:
        red_new.sort(key=lambda c: -c["sev"])
        for c in red_new[:4]:
            messages.append(_story(c))
        if len(red_new) > 4:
            messages.append(f"🔴 و {len(red_new) - 4} خبر قرمز دیگر در بولتن.")
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
        return {"enabled": False, "queued": len(messages)}
    cid = _chat_id(state, token)
    if not cid:
        return {"enabled": True, "chat": False, "queued": len(messages)}
    ok = 0
    link = f'\n\n<a href="{config.DASHBOARD_URL}">باز کردن بولتن</a>'
    for i, msg in enumerate(messages[:7]):
        try:
            _call(token, "sendMessage", chat_id=cid, text=msg + (link if i == len(messages[:7]) - 1 else ""),
                  parse_mode="HTML", link_preview_options={"is_disabled": True})
            ok += 1
        except Exception as e:  # noqa: BLE001
            log("telegram send failed:", str(e)[:80])
    return {"enabled": True, "chat": True, "sent": ok}
