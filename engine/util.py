"""Small text, time and file helpers shared by the engine."""
import email.utils
import hashlib
import html
import json
import os
import re
import time
from datetime import datetime, timezone

from . import config


def now() -> int:
    return config.FIXED_NOW or int(time.time())


def sha(s: str, n: int = 12) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:n]


LOGS = []


def log(*a):
    line = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(line, flush=True)
    LOGS.append(line[:400])
    if len(LOGS) > 400:
        del LOGS[:100]


# ---------------------------------------------------------------- text

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_BOILER = [
    re.compile(r"The post .{3,200}? appeared first on .{2,120}?\.?\s*$", re.S),
    re.compile(r"\s*(Continue reading|Read more|Read More|Full story|ادامه مطلب|بیشتر بخوانید|ادامه خبر)\W*$"),
    re.compile(r"\s*\[(…|\.\.\.)\]\s*$"),
    re.compile(r"^\s*(?:[A-Z][A-Za-z .,'-]{1,40}\s)?\((?:Reuters|AP|AFP|AFP-JIJI|UPI)\)\s*[-—–]\s*"),
    re.compile(r"^\s*[A-Z][A-Z .,'-]{2,40}\s*[-—–]\s+"),           # DATELINE —
    re.compile(r"^\s*به گزارش [^،,]{2,60}[،,]\s*"),                 # «به گزارش خبرگزاری …،»
]


def strip_html(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s) if "&lt;" in s[:400] else s       # double-escaped feeds
    s = re.sub(r"(?is)<(script|style|figcaption|iframe|noscript)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", " ", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = s.replace(" ", " ").replace("​", "")
    return _WS.sub(" ", s).strip()


def clean_summary(s: str) -> str:
    s = strip_html(s)
    for rx in _BOILER:
        s = rx.sub("", s)
    return s.strip(" -—–|")


def clean_title(s: str) -> str:
    s = strip_html(s)
    s = re.sub(r"\s+[|]\s+[^|]{2,40}$", "", s)        # "Title | Site"
    return s.strip(" -—–|")


def truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    # prefer the end of a sentence
    m = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("؟ "))
    if m >= n * 0.55:
        return cut[: m + 1].strip()
    sp = cut.rfind(" ")
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(" ,،;:-") + "…"


def first_sentences(s: str, max_chars: int = 320) -> str:
    """Keep the first one or two sentences of a summary."""
    s = (s or "").strip()
    if len(s) <= max_chars:
        return s
    parts = re.split(r"(?<=[.!?؟])\s+", s)
    out = ""
    for p in parts:
        if len(out) + len(p) + 1 > max_chars:
            break
        out = (out + " " + p).strip()
    return out if len(out) > 60 else truncate(s, max_chars)


FA_MAP = str.maketrans({"ي": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه", "ؤ": "و", "إ": "ا", "أ": "ا", "ٱ": "ا", "ئ": "ی"})
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def fa_norm(s: str) -> str:
    s = (s or "").translate(FA_MAP)
    s = re.sub("[ً-ٰٟـ]", "", s)          # harakat + tatweel
    s = re.sub("[‌‍‎‏‪-‮]", " ", s)
    return _WS.sub(" ", s).strip()


def to_latin_digits(s: str) -> str:
    return (s or "").translate(DIGITS)


def has_fa(s: str) -> bool:
    return bool(re.search("[؀-ۿ]", s or ""))


def norm_url(u: str) -> str:
    u = (u or "").strip()
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("http://"):
        u = "https://" + u[7:]
    return u


# ---------------------------------------------------------------- dates

def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
        if d is not None:
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return int(d.timestamp())
    except Exception:
        pass
    try:
        x = s.replace("Z", "+00:00")
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", x):
            x = re.sub(r"(\.\d{1,6})\d*", r"\1", x)
        d = datetime.fromisoformat(x)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int(d.timestamp())
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d %b %Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc).timestamp())
        except Exception:
            continue
    return None


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- files

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj, pretty=False):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def data_path(*parts):
    return os.path.join(config.DATA_DIR, *parts)
