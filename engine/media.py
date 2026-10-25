"""Pick images / videos for stories, and find posts on X embedded in article pages."""
import re
from urllib.parse import urljoin

from . import http
from .util import norm_url

IMG_EXT = re.compile(r"\.(jpe?g|png|webp|gif|avif)(\?|$)", re.I)
BAD_IMG = re.compile(r"(logo|placeholder|default[-_]?image|blank|spacer|1x1|pixel|avatar|icon|sprite|\.svg)", re.I)
YT = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([\w-]{11})")
TWEET = re.compile(r"https?://(?:www\.|mobile\.)?(?:twitter|x)\.com/([A-Za-z0-9_]{1,15})/status(?:es)?/(\d{8,20})")
IMG_TAG = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
META = re.compile(r"<meta\s+[^>]*?(?:property|name)=[\"']([^\"']+)[\"'][^>]*?content=[\"']([^\"']*)[\"'][^>]*>"
                  r"|<meta\s+[^>]*?content=[\"']([^\"']*)[\"'][^>]*?(?:property|name)=[\"']([^\"']+)[\"'][^>]*>", re.I)


def _ok_img(u):
    return u and u.startswith("http") and not BAD_IMG.search(u)


def from_entry(entry, link=""):
    """Return (image_url, video) from a raw feed entry."""
    img, img_w, vid = None, -1, None
    for m in entry.get("media", []):
        u = norm_url(m.get("url", ""))
        typ = (m.get("type") or "").lower()
        med = (m.get("medium") or "").lower()
        if typ.startswith("video/") or med == "video":
            if u.endswith(".mp4") or "mp4" in typ:
                vid = vid or {"type": "mp4", "src": u}
            continue
        if typ.startswith("image/") or med == "image" or IMG_EXT.search(u) or (not typ and not med):
            if _ok_img(u) and (m.get("w", 0) or 0) >= img_w:
                img, img_w = u, (m.get("w", 0) or 0)
    html = (entry.get("summary") or "") + " " + (entry.get("content") or "")
    if not img:
        for u in IMG_TAG.findall(html):
            u = norm_url(u)
            if _ok_img(u):
                img = u
                break
    if not vid:
        y = YT.search(link or "") or YT.search(html)
        if y:
            vid = {"type": "yt", "src": y.group(1)}
    return img, vid


def tweets_in(html):
    """(handle, id) pairs of posts on X referenced in html."""
    seen, out = set(), []
    for h, i in TWEET.findall(html or ""):
        if i not in seen and h.lower() not in ("i", "intent", "share", "home", "search", "hashtag"):
            seen.add(i)
            out.append((h, i))
    return out


def page_meta(url):
    """Fetch an article page (first ~450KB) and return og image/video and embedded posts."""
    r = http.get(url, timeout=15, retries=0, max_bytes=450_000)
    html = r.text
    meta = {}
    for a, b, c, d in META.findall(html):
        k, v = (a, b) if a else (d, c)
        k = k.lower()
        if k not in meta and v:
            meta[k] = v
    img = meta.get("og:image") or meta.get("og:image:secure_url") or meta.get("twitter:image") or \
        meta.get("twitter:image:src")
    img = norm_url(urljoin(r.url, img)) if img else None
    if img and not _ok_img(img):
        img = None
    vid = None
    for k in ("og:video:secure_url", "og:video:url", "og:video"):
        v = meta.get(k)
        if v:
            y = YT.search(v)
            if y:
                vid = {"type": "yt", "src": y.group(1)}
            elif ".mp4" in v:
                vid = {"type": "mp4", "src": norm_url(v)}
            if vid:
                break
    if not vid:
        y = YT.search(html)
        if y and "embed" in html[max(0, y.start() - 80):y.start()]:
            vid = {"type": "yt", "src": y.group(1)}
    return {"img": img, "vid": vid, "tweets": tweets_in(html)}
