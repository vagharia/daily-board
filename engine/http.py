"""HTTP helpers: pooled sessions, retries, parallel fetches and an offline fixture mode."""
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from . import config


class FetchError(Exception):
    pass


class Resp:
    def __init__(self, url, status, content, headers=None, final_url=None):
        self.url = final_url or url
        self.status_code = status
        self.content = content or b""
        self.headers = headers or {}

    @property
    def text(self):
        enc = None
        m = re.search(r"charset=([\w-]+)", self.headers.get("content-type", ""), re.I)
        if m:
            enc = m.group(1)
        try:
            return self.content.decode(enc or "utf-8", errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content.decode("utf-8", errors="replace"))


_local = threading.local()


def _session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": config.UA,
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml,*/*;q=0.8",
        })
        ad = requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=0)
        s.mount("https://", ad)
        s.mount("http://", ad)
        _local.s = s
    return s


def request(url, method="GET", timeout=20, headers=None, retries=1, max_bytes=None,
            params=None, data=None, json_body=None):
    if config.OFFLINE:
        return _offline(url, params)
    last = None
    for attempt in range(retries + 1):
        try:
            s = _session()
            if method == "GET":
                r = s.get(url, timeout=timeout, headers=headers or {}, params=params,
                          stream=max_bytes is not None, allow_redirects=True)
            else:
                r = s.post(url, timeout=timeout, headers=headers or {}, params=params,
                           data=data, json=json_body)
            if max_bytes is not None:
                buf = bytearray()
                for chunk in r.iter_content(32768):
                    buf.extend(chunk)
                    if len(buf) >= max_bytes:
                        break
                content = bytes(buf)
                r.close()
            else:
                content = r.content
            code = r.status_code
            if code == 429 or code >= 500:
                raise FetchError(f"HTTP {code}")
            if code >= 400:
                last = FetchError(f"HTTP {code}")
                break                      # 4xx: no point retrying
            return Resp(url, code, content, {k.lower(): v for k, v in r.headers.items()}, r.url)
        except FetchError as e:
            last = e
        except Exception as e:  # noqa: BLE001 - network errors of all kinds
            last = FetchError(f"{type(e).__name__}: {str(e)[:120]}")
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise last or FetchError("unknown error")


def get(url, **kw):
    return request(url, "GET", **kw)


def post(url, **kw):
    return request(url, "POST", **kw)


def parallel(fn, items, workers=12):
    """Run fn over items in threads; returns list of (item, result, error)."""
    out = []
    if not items:
        return out

    def wrap(it):
        try:
            return it, fn(it), None
        except Exception as e:  # noqa: BLE001
            return it, None, e

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(wrap, items):
            out.append(res)
    return out


# ---------------------------------------------------------------- offline fixtures

_FIX = None


def _offline(url, params=None):
    """Serve fixtures for tests. tests/fixtures/index.json maps regex -> file."""
    global _FIX
    if _FIX is None:
        idx = os.path.join(config.FIXTURES, "index.json")
        try:
            with open(idx, encoding="utf-8") as f:
                _FIX = [(re.compile(k), v) for k, v in json.load(f).items()]
        except FileNotFoundError:
            _FIX = []
    full = url
    if params:
        full += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    for rx, fname in _FIX:
        if rx.search(full):
            with open(os.path.join(config.FIXTURES, fname), "rb") as f:
                return Resp(url, 200, f.read(), {"content-type": "text/plain; charset=utf-8"})
    raise FetchError("offline: no fixture")
