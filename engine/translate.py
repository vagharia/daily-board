"""Free machine translation through Google's public web endpoints (two independent endpoints,
so one being throttled doesn't stop the run), with caching, size-limited batching and a small
glossary so names and terms come out right in Persian."""
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
# Google renders a shekel as a mithqal (the old weight) in Persian; put the currency back when the source names it
_SHEKEL = re.compile(r"shekel|\bNIS\b|שקל|ש\"ח|ש״ח", re.I)
_LINEBREAKS = re.compile(r"[\r\n  \u0085\v\f]+")


def _pre(text, sl):
    text = _LINEBREAKS.sub(" ", text)
    if sl == "en":
        for rx, rep in EN_PRE:
            text = rx.sub(rep, text)
    return text


def fix_terms(src, out, tl):
    """Corrections that depend on the source text."""
    if tl == "fa" and out and "مثقال" in out and _SHEKEL.search(src or ""):
        out = out.replace("مثقال", "شِکِل")
    return out


def _post(text, tl):
    if tl == "fa":
        for a, b in FA_POST:
            text = text.replace(a, b)
        for rx, rep in FA_RX_POST:
            text = rx.sub(rep, text)
    return text.strip()


# ------------------------------------------------------------------ engines
def _single(texts, sl, tl, host="translate.googleapis.com", client="gtx"):
    """Several single-line texts in one request, newline separated."""
    r = http.post(f"https://{host}/translate_a/single", params={"client": client, "sl": sl, "tl": tl, "dt": "t"},
                  data={"q": "\n".join(texts)}, timeout=25, retries=1)
    data = r.json()
    out = "".join(seg[0] for seg in (data[0] or []) if seg and seg[0])
    parts = [p.strip() for p in out.split("\n")]
    if len(parts) != len(texts):
        raise ValueError(f"split mismatch {len(parts)} != {len(texts)}")
    return parts


def _multi(texts, sl, tl, host="translate.googleapis.com", client="gtx"):
    """One request, one q parameter per text (no newline juggling)."""
    r = http.post(f"https://{host}/translate_a/t", params={"client": client, "sl": sl, "tl": tl},
                  data=[("q", t) for t in texts], timeout=25, retries=1)
    d = r.json()
    if len(texts) == 1 and isinstance(d, list) and d and isinstance(d[0], str) and len(d) == 2:
        d = [d]                       # single text with sl=auto comes back as [text, lang]
    out = [x if isinstance(x, str) else x[0] for x in d]
    if len(out) != len(texts):
        raise ValueError(f"multi mismatch {len(out)} != {len(texts)}")
    return out


def _clients5(texts, sl, tl):
    return _multi(texts, sl, tl, host="clients5.google.com", client="dict-chrome-ex")


def _offline(texts, sl, tl):
    """Deterministic stand-in used by the offline test suite."""
    table = {}
    try:
        with open(f"{config.FIXTURES}/translations.json", encoding="utf-8") as f:
            table = json.load(f)
    except FileNotFoundError:
        pass
    return [table.get(t, ("[FA] " if tl == "fa" else "[EN] ") + t) for t in texts]


ENGINES = [("single", _single), ("multi", _multi), ("clients5", _clients5)]
MAX_ITEMS = 10
MAX_BYTES = 2600          # UTF-8 bytes of source text per request (Persian is 2 bytes a letter)


class Translator:
    def __init__(self, cache):
        self.cache = cache if cache is not None else {}
        self.stats = {"cached": 0, "failed": 0, "requests": 0}
        self.errors = []
        self._dead = {}           # engine -> consecutive failures

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
            n = len(t.encode("utf-8"))
            if batch and (size + n > MAX_BYTES or len(batch) >= MAX_ITEMS):
                self._run(batch, sl, tl, result)
                batch, size = [], 0
            batch.append(t)
            size += n
        if batch:
            self._run(batch, sl, tl, result)
        return {k: fix_terms(k, v, tl) for k, v in result.items()}

    def _err(self, msg):
        log(msg)
        if len(self.errors) < 12:
            self.errors.append(msg[:160])

    def _run(self, batch, sl, tl, result):
        pre = [_pre(t, sl)[:1800] for t in batch]
        out = None
        engines = [("offline", _offline)] if config.OFFLINE else ENGINES
        for name, fn in engines:
            if self._dead.get(name, 0) >= 3:
                continue
            try:
                self.stats["requests"] += 1
                out = fn(pre, sl, tl)
                self.stats[name] = self.stats.get(name, 0) + len(batch)
                self._dead[name] = 0
                break
            except Exception as e:  # noqa: BLE001
                self._dead[name] = self._dead.get(name, 0) + 1
                self._err(f"translate {name} {sl}>{tl} ({len(batch)} items, "
                          f"{sum(len(p.encode()) for p in pre)}B): {str(e)[:100]}")
                time.sleep(0.6)
        if out is None and len(batch) > 1:
            # last resort: one text per request so a single bad text can't sink the batch
            out = []
            for p in pre:
                try:
                    self.stats["requests"] += 1
                    out.append(_multi([p], sl, tl)[0])
                except Exception as e:  # noqa: BLE001
                    self._err(f"translate one-by-one {sl}>{tl}: {str(e)[:100]}")
                    out.append(None)
                time.sleep(0.1)
        if out is None:
            self.stats["failed"] += len(batch)
            return
        if not config.OFFLINE:
            time.sleep(0.12)
        for src, tr in zip(batch, out):
            tr = _post(tr, tl) if tr else ""
            if tr:
                result[src] = tr
                self.cache[self.key(src, sl, tl)] = [tr, now()]
            else:
                self.stats["failed"] += 1

    def prune(self, max_age=9 * 24 * 3600, max_entries=24000):
        cut = now() - max_age
        for k in [k for k, v in self.cache.items() if v[1] < cut]:
            del self.cache[k]
        if len(self.cache) > max_entries:
            for k, _ in sorted(self.cache.items(), key=lambda kv: kv[1][1])[: len(self.cache) - max_entries]:
                del self.cache[k]
