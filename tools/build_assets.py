"""One-time asset build (runs in GitHub Actions): downloads open-licensed fonts and builds the
regional map geometry from Natural Earth (world-atlas) into docs/."""
import io
import json
import math
import os
import sys
import tarfile
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
UA = {"User-Agent": "Mozilla/5.0 (asset-build)"}

# must match MAPP in docs/app.js
LON0, LON1, LAT0, LAT1 = 31.5, 63.5, 11.5, 40.5
K = math.cos(math.radians(27))
SC = 14.0


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def first_ok(urls, check=None):
    for u in urls:
        try:
            b = fetch(u)
            if check is None or check(b):
                print("ok:", u, len(b))
                return b
            print("bad content:", u)
        except Exception as e:  # noqa: BLE001
            print("fail:", u, e)
    return None


def from_npm_tarball(pkg, version, inner):
    url = f"https://registry.npmjs.org/{pkg}/-/{pkg.split('/')[-1]}-{version}.tgz"
    b = fetch(url)
    with tarfile.open(fileobj=io.BytesIO(b)) as t:
        return t.extractfile("package/" + inner).read()


def is_woff2(b):
    return b[:4] == b"wOF2"


def fonts():
    out = os.path.join(DOCS, "fonts")
    os.makedirs(out, exist_ok=True)
    vz = "fonts/webfonts/Vazirmatn[wght].woff2"
    q = urllib.parse.quote(vz)
    b = first_ok([
        f"https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/{q}",
        f"https://unpkg.com/vazirmatn@33.0.3/{q}",
        f"https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/{q}",
    ], is_woff2)
    if b is None:
        try:
            b = from_npm_tarball("vazirmatn", "33.0.3", vz)
        except Exception as e:  # noqa: BLE001
            print("vazirmatn tarball failed:", e)
    if b:
        open(os.path.join(out, "vazirmatn.woff2"), "wb").write(b)
    for w in (400, 500, 600, 700):
        f = f"files/ibm-plex-sans-latin-{w}-normal.woff2"
        b = first_ok([f"https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-sans@5/{f}",
                      f"https://unpkg.com/@fontsource/ibm-plex-sans@5/{f}"], is_woff2)
        if b:
            open(os.path.join(out, f"plex-{w}.woff2"), "wb").write(b)


# ------------------------------------------------------------------ map
def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def ring_from(arcs, idxs):
    ring = []
    for i in idxs:
        a = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
        if ring:
            a = a[1:]
        ring.extend(a)
    return ring


def clip_ring(ring, box):
    """Sutherland-Hodgman clip of a polygon ring against an axis-aligned box (lon/lat)."""
    x0, y0, x1, y1 = box

    def clip(pts, inside, inter):
        out = []
        if not pts:
            return out
        prev = pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
            prev = cur
        return out

    def ix(xv):
        return lambda p, q: (xv, p[1] + (q[1] - p[1]) * (xv - p[0]) / ((q[0] - p[0]) or 1e-12))

    def iy(yv):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (yv - p[1]) / ((q[1] - p[1]) or 1e-12), yv)

    pts = ring
    pts = clip(pts, lambda p: p[0] >= x0, ix(x0))
    pts = clip(pts, lambda p: p[0] <= x1, ix(x1))
    pts = clip(pts, lambda p: p[1] >= y0, iy(y0))
    pts = clip(pts, lambda p: p[1] <= y1, iy(y1))
    return pts


def dp(pts, eps):
    """Douglas-Peucker simplification (iterative)."""
    if len(pts) < 4:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-12
        best, bi = 0.0, None
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / L
            if d > best:
                best, bi = d, i
        if bi is not None and best > eps:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


def proj(lon, lat):
    return ((lon - LON0) * K * SC, (LAT1 - lat) * SC)


def build_map():
    raw = first_ok(["https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json",
                    "https://unpkg.com/world-atlas@2/countries-50m.json"], lambda b: b[:1] == b"{")
    if raw is None:
        raw = from_npm_tarball("world-atlas", "2.0.2", "countries-50m.json")
    topo = json.loads(raw)
    arcs = decode_arcs(topo)
    box = (LON0 - 3, LAT0 - 3, LON1 + 3, LAT1 + 3)
    out = []
    for g in topo["objects"]["countries"]["geometries"]:
        polys = g.get("arcs") or []
        if g["type"] == "Polygon":
            polys = [polys]
        elif g["type"] != "MultiPolygon":
            continue
        d = []
        for poly in polys:
            for ring_idx in poly:
                ring = ring_from(arcs, ring_idx)
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                if max(xs) < box[0] or min(xs) > box[2] or max(ys) < box[1] or min(ys) > box[3]:
                    continue
                ring = clip_ring(ring, box)
                if len(ring) < 3:
                    continue
                pp = dp([proj(x, y) for x, y in ring], 0.35)
                if len(pp) < 3:
                    continue
                d.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pp) + "Z")
        if d:
            out.append({"id": str(g.get("id", "")), "n": (g.get("properties") or {}).get("name", ""), "d": "".join(d)})
    W = (LON1 - LON0) * K * SC
    H = (LAT1 - LAT0) * SC
    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    with open(os.path.join(DOCS, "assets", "map.json"), "w") as f:
        json.dump({"v": 1, "w": round(W, 1), "h": round(H, 1), "countries": out}, f, separators=(",", ":"))
    print("map countries:", len(out))


if __name__ == "__main__":
    what = sys.argv[1:] or ["fonts", "map"]
    if "fonts" in what:
        fonts()
    if "map" in what:
        build_map()
