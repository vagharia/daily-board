"""Draw the app icons (a small gauge: arc, needle and a cyan hub) at several sizes with Pillow."""
import os
import sys

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "icons")
BG, INK, DOT = (7, 20, 43), (232, 238, 248), (94, 200, 255)


def draw(size, pad):
    s = 4                                       # supersample for smooth edges
    W = size * s
    im = Image.new("RGB", (W, W), BG)
    d = ImageDraw.Draw(im)
    inner = W - 2 * pad * s                     # the 24-unit drawing area
    u = inner / 24.0
    ox = oy = pad * s

    def P(x, y):
        return ox + x * u, oy + y * u

    cx, cy, r = 12, 15.2, 8.4
    lw = 2.5 * u
    box = [P(cx - r, cy - r), P(cx + r, cy + r)]
    d.arc([box[0][0], box[0][1], box[1][0], box[1][1]], 180, 360, fill=INK, width=int(lw))
    for ex, ey in ((cx - r, cy), (cx + r, cy)):                      # round arc ends
        x, y = P(ex, ey)
        x += (lw / 2) * (1 if ex < cx else -1)
        d.ellipse([x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2], fill=INK)
    x0, y0 = P(cx, cy)
    x1, y1 = P(cx + 4.6, cy - 5.4)
    nw = 2.2 * u
    d.line([x0, y0, x1, y1], fill=INK, width=int(nw))
    d.ellipse([x1 - nw / 2, y1 - nw / 2, x1 + nw / 2, y1 + nw / 2], fill=INK)
    hr = 2.6 * u
    d.ellipse([x0 - hr, y0 - hr, x0 + hr, y0 + hr], fill=DOT)
    return im.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    draw(192, 26).save(os.path.join(OUT, "icon-192.png"))
    draw(512, 68).save(os.path.join(OUT, "icon-512.png"))
    draw(512, 104).save(os.path.join(OUT, "icon-maskable-512.png"))     # safe zone for masks
    draw(180, 24).save(os.path.join(OUT, "apple-touch-icon.png"))
    print("icons written to", OUT)


if __name__ == "__main__":
    sys.exit(main())
