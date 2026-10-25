"""Free machine translation (Google web endpoint, Microsoft Edge endpoint as fallback),
with caching, batching and a small glossary so names and terms come out right in Persian."""
import json
import re
import time

from . import config, http
from .util import log, now, sha

# ------------------------------------------------------------------ glossary
EN_PRE = [
    (re.compile(r"\bArabian Gulf\b"), "Persian Gulf"),
    (re.compile(r"\bthe Gulf\b(?!\s+of\b)"), "the Persian Gulf"),
    (re.compile(r"\bGulf (states|countries|nations|Arab states|monarchies|allies|neighbou?rs|region|Cooperation Council)\b"),
     r"Persian Gulf \1"),
    (re.compile(r"\bGulf Arab\b"), "Persian Gulf Arab"),
]

FA_POST = [
    ("خلیج عربی", "خلیج فارس"), ("خلیج فارس فارس", "خلیج فارس"),
    ("رهبر عالی ایران", "رهبر ایران"), ("رهبر عالی", "رهبر ایران"), ("رهبر معظم ایران ایران", "رهبر ایران"),
    ("هگزث", "هگست"), ("هگسث", "هگست"), ("هگزت", "هگست"), ("ویتکوف", "ویتکاف"),
    ("اراقچی", "عراقچی"), ("ارقچی", "عراقچی"),
    ("حزب الله", "حزب‌الله"), ("حوثی ها", "حوثی‌ها"), ("سپاه پاسداران انقلاب اسلامی", "سپاه پاسداران"),
    ("فرماندهی مرکزی ایالات متحده", "سنتکام"), ("فرماندهی مرکزی آمریکا", "سنتکام"),
    ("آژانس بین المللی انرژی اتمی", "آژانس بین‌المللی انرژی اتمی"),
    ("ایالات متحده آمریکا", "آمریکا"),
]
FA_RX_POST = [
    (re.compile(r"(?<=\S) ها(?=[\s،.؛:!؟]|$)"), "‌ها"),
    (re.compile(r"(?<=\S) های(?=[\s،.؛:!؟]|$)"), "‌های"),
    (re.compile(r"(?<![؀-ۿ])می (?=[؀-ۿ])"), "می‌"),
    (re.compile(r"(?<![؀-ۿ])نمی (?=[؀-ۿ])"), "نمی‌"),
    (re.compile(r"\s+([،.؛:!؟])"), r"\1"),
]


def _pre(text, sl):
    if sl == "en":
        for rx, rep in EN_PRE:
            text = rx.sub(rep, text)
    return text


def _post(text, tl):
    if tl == "fa":
        for a, b in FA_POST:
            text = text.replace(a, b)
        for rx, rep in FA_RX_POST:
            text = rx.sub(rep, text)
    return text.strip()


# ------------------------------------------------------------------ engines
def _google(texts, sl, tl):
    """Translate a list of single-line texts in one request (newline separated)."""
    joined = "\n".join(t.replace("\n", " ") for t in texts)
    r = http.post("https://translate.googleapis.com/translate_a/single",
                  params={"client": "gtx", "sl": sl, "tl": tl, "dt": "t"},
                  data={"q": joined}, timeout=25, retries=1)
    data = r.json()
    out = "".join(seg[0] for seg in data[0] if seg and seg[0])
    parts = [p.strip() for p in out.split("\n")]
    if len(parts) != len(texts):
        raise ValueError(f"google split mismatch {len(parts)} != {len(texts)}")
    return parts


_MS_TOKEN = {"t": None, "exp": 0}


def _microsoft(texts, sl, tl):
    if not _MS_TOKEN["t"] or time.time() > _MS_TOKEN["exp"]:
        tok = http.get("https://edge.microsoft.com/translate/auth", timeout=15).text.strip()
        _MS_TOKEN.update(t=tok, exp=time.time() + 480)
    params = {"to": tl, "api-version": "3.0"}
    if sl != "auto":
        params["from"] = sl
    r = http.post("https://api-edge.cognitive.microsofttranslator.com/translate",
                  params=params,
                  headers={"Authorization": "Bearer " + _MS_TOKEN["t"], "Content-Type": "application/json"},
                  json_body=[{"Text": t} for t in texts], timeout=25, retries=1)
    return [x["translations"][0]["text"] for x in r.json()]


def _offline(texts, sl, tl):
    """Deterministic stand-in used by the offline test suite."""
    table = {}
    try:
        with open(f"{config.FIXTURES}/translations.json", encoding="utf-8") as f:
            table = json.load(f)
    except FileNotFoundError:
        pass
    return [table.get(t, ("[FA] " if tl == "fa" else "[EN] ") + t) for t in texts]


class Translator:
    def __init__(self, cache):
        self.cache = cache if cache is not None else {}
        self.stats = {"google": 0, "microsoft": 0, "cached": 0, "failed": 0}

    def key(self, text, sl, tl):
        return sha(f"{sl}>{tl}:{text}", 20)

    def get(self, text, sl, tl):
        e = self.cache.get(self.key(text, sl, tl))
        return e[0] if e else None

    def translate_many(self, texts, sl, tl):
        """Return dict text -> translation (missing on failure)."""
        result, todo = {}, []
        for t in dict.fromkeys(x for x in texts if x and x.strip()):
            e = self.cache.get(self.key(t, sl, tl))
            if e:
                result[t] = e[0]
                e[1] = now()
                self.stats["cached"] += 1
            else:
                todo.append(t)
        batch, size = [], 0
        for t in todo:
            if batch and (size + len(t) > 3200 or len(batch) >= 12):
                self._run(batch, sl, tl, result)
                batch, size = [], 0
            batch.append(t)
            size += len(t)
        if batch:
            self._run(batch, sl, tl, result)
        return result

    def _run(self, batch, sl, tl, result):
        pre = [_pre(t, sl) for t in batch]
        out = None
        engines = [("offline", _offline)] if config.OFFLINE else [("google", _google), ("microsoft", _microsoft)]
        for name, fn in engines:
            try:
                out = fn(pre, sl, tl)
                self.stats[name] = self.stats.get(name, 0) + len(batch)
                break
            except Exception as e:  # noqa: BLE001
                log(f"translate {name} failed ({len(batch)} items): {str(e)[:100]}")
                if name == "google" and len(batch) > 1 and "mismatch" in str(e):
                    # translate one by one with google before giving up on it
                    try:
                        out = [_google([p], sl, tl)[0] for p in pre]
                        self.stats["google"] += len(batch)
                        break
                    except Exception as e2:  # noqa: BLE001
                        log("translate google single failed:", str(e2)[:100])
                time.sleep(1.0)
        if out is None:
            self.stats["failed"] += len(batch)
            return
        for src, tr in zip(batch, out):
            tr = _post(tr, tl)
            if tr:
                result[src] = tr
                self.cache[self.key(src, sl, tl)] = [tr, now()]

    def prune(self, max_age=9 * 24 * 3600):
        cut = now() - max_age
        for k in [k for k, v in self.cache.items() if v[1] < cut]:
            del self.cache[k]
