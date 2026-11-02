"""LinkedIn banners in the Nightlight style. 396 by 99 logical pixels at 4x gives 1584 by 396.

python -m nightlight.banners --out assets/banners
"""
import argparse
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw

from .engine import Canvas, grow, save_png, text_width

W, H, SCALE = 396, 99, 4
WORD_X, WORD_Y, WORD_SIZE = W - 22, 57, 20


# ---------------------------------------------------------------- helpers
def fl(v):
    return int(math.floor(v + 0.5))


def trace(pts):
    """Ordered integer pixels along a polyline, one pixel wide, corners tidied."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) * 2))
        for i in range(n + 1):
            p = (fl(x0 + (x1 - x0) * i / n), fl(y0 + (y1 - y0) * i / n))
            if not out or out[-1] != p:
                out.append(p)
    res = []
    for i, p in enumerate(out):
        if 0 < i < len(out) - 1:
            a, b = out[i - 1], out[i + 1]
            if abs(a[0] - b[0]) == 1 and abs(a[1] - b[1]) == 1:
                if (a[0] == p[0] or a[1] == p[1]) and (b[0] == p[0] or b[1] == p[1]):
                    continue
        res.append(p)
    return res


def spline(pts, n=10):
    """Catmull-Rom curve through the points."""
    ext = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(tuple(pts[-1]))
    return out


def draw(c, pts, dot=1, on=True, phase=0):
    """Draw a polyline, solid when dot is 1, dotted every dot pixels otherwise."""
    for i, p in enumerate(trace(pts)):
        if (i + phase) % dot == 0:
            c.px(p[0], p[1], on)


def poly_mask(c, pts):
    im = Image.new("1", (c.w, c.h), 0)
    ImageDraw.Draw(im).polygon([(fl(x), fl(y)) for x, y in pts], fill=1)
    return np.array(im, bool)


def disc_mask(c, cx, cy, r):
    return (c.xx - cx) ** 2 + (c.yy - cy) ** 2 <= r * r


def ink(c, m, margin=True):
    """Clear a mask to solid ink, with a one pixel margin so line art reads over dither."""
    k = grow(m) if margin else m
    k = np.logical_or(k, m)
    c.L[k] = 0
    c.P &= ~k
    c.K[k] = False


def sparkle(c, x, y, r=1, core=True):
    for d in range(1, r + 1):
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            c.px(x + dx, y + dy)
    if core:
        c.px(x, y)


def star_field(c, seed, count, avoid, gap=7, sparkles=4, area=None):
    """Scatter single pixel stars, a few as plus signs, keeping clear of avoid masks."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area or (1, 1, W - 2, H - 2)
    placed = []
    tries = 0
    while len(placed) < count and tries < 20000:
        tries += 1
        x, y = rnd.randint(x0, x1), rnd.randint(y0, y1)
        if avoid[y, x] or any(abs(x - a) < gap and abs(y - b) < gap for a, b in placed):
            continue
        if any(avoid[min(H - 1, max(0, y + dy)), min(W - 1, max(0, x + dx))]
               for dx in (-2, 0, 2) for dy in (-2, 0, 2)):
            continue
        placed.append((x, y))
    for i, (x, y) in enumerate(placed):
        if i < sparkles:
            sparkle(c, x, y, 2 if i == 0 else 1)
        else:
            c.px(x, y)
    return placed


def word(c, txt):
    m = c.text(WORD_X, WORD_Y, txt, WORD_SIZE, anchor="rs")
    return m


def word_box(txt):
    w = text_width(txt, WORD_SIZE)
    m = np.zeros((H, W), bool)
    m[WORD_Y - 24:WORD_Y + 12, WORD_X - w - 6:W] = True
    return m


def glow(c, cx, cy, r, peak, power=1.7, mask=None):
    """A round pool of light with a smooth fall off, so the dither stays round."""
    d = np.sqrt((c.xx - cx) ** 2 + (c.yy - cy) ** 2)
    f = peak * np.clip(1 - d / r, 0, 1) ** power
    if mask is not None:
        f = f * mask
    c.L = np.maximum(c.L, f)


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(c, hor, skip=None):
    """The horizon and a sparse lattice of dots that thickens toward us."""
    c.hline(0, W - 1, hor)
    for row, y in enumerate(range(hor + 4, H - 1, 4)):
        step = 7 - min(2, row // 2)
        for x in range(2 + (row % 2) * (step // 2), W - 1, step):
            if skip is None or not skip[y, x]:
                c.px(x, y)


# ---------------------------------------------------------------- 1. Orchestrate
# A night switchyard seen from above. One trunk line fans out into five tracks and
# every train sits exactly where the timetable wants it. One lamp sets the pace.
def orchestrate():
    c = Canvas(W, H)
    mid = 50
    ys = [16, 33, 50, 67, 84]
    split0, split1, x_end = 70, 160, 236
    branch = [(70, 90), (104, 56), (0, 1), (104, 56), (70, 90)]

    def track_y(i, x):
        b, ln = branch[i]
        return mid + (ys[i] - mid) * smooth((x - b) / ln)

    avoid = word_box("Orchestrate.")
    avoid[10:90, :262] = True
    star_field(c, 31, 22, avoid, gap=20, sparkles=3)

    # the one lamp, at the switch, and a small lamp at the end of every track
    lamp = (46, mid - 15)
    glow(c, lamp[0], lamp[1], 17, 12, power=2.2)
    for i in range(5):
        glow(c, x_end + 8, ys[i], 6, 6, power=1.6)

    # rails and sleepers
    for i in range(5):
        x_from = 6 if i == 2 else branch[i][0]
        for x in range(x_from, x_end):
            yc = fl(track_y(i, x))
            c.px(x, yc - 1)
            c.px(x, yc + 1)
            if x % 4 == 0:
                c.px(x, yc - 3)
                c.px(x, yc + 3)
        yc = ys[i]
        c.vline(x_end + 1, yc - 3, yc + 3)
        c.vline(x_end + 2, yc - 3, yc + 3)
        # the lamp that tells the track it may go
        ink(c, disc_mask(c, x_end + 8, yc, 2.6), margin=False)
        c.disc(x_end + 8, yc, 1.5)
    # the lamp at the switch
    c.vline(lamp[0], lamp[1], mid - 3)
    c.vline(lamp[0] + 1, lamp[1] + 5, mid - 3)
    ink(c, disc_mask(c, lamp[0], lamp[1], 3.2), margin=False)
    c.disc(lamp[0], lamp[1], 2.2)
    sparkle(c, lamp[0], lamp[1], 5, core=False)
    for d in (3, 4):
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            c.px(lamp[0] + dx, lamp[1] + dy, False)
    c.disc(lamp[0], lamp[1], 2.2)

    # trains, staggered along the timetable, all heading for the right
    trains = [(2, 8, 2), (0, 176, 3), (1, 196, 2), (2, 192, 2), (3, 164, 3), (4, 188, 2)]
    L = 10
    for i, x0, cars in trains:
        yc = ys[i] if x0 > split1 else mid
        for k in range(cars):
            x = x0 + k * (L + 2)
            m = c.rect_mask(x, yc - 2, x + L - 1, yc + 2)
            ink(c, m)
            c.box(x, yc - 2, x + L - 1, yc + 2)
            for wx in (x + 2, x + 5, x + 8 - (1 if k == cars - 1 else 0)):
                c.px(wx, yc)
            if k > 0:
                c.px(x - 1, yc)
        xf = x0 + (cars - 1) * (L + 2) + L
        c.px(xf, yc)
        c.px(xf + 1, yc)

    word(c, "Orchestrate.")
    return c


# ---------------------------------------------------------------- 2. Curiosity
# A jar of fireflies on a stump, its lid lifted off. One of them has wandered out
# and is still going, leaving a thin trail of light across the sky.
def curiosity():
    c = Canvas(W, H)
    hor = 82
    jx = 118
    avoid = word_box("Curiosity.")
    avoid[:, 96:262] = True
    avoid[hor - 6:, :] = True
    star_field(c, 17, 24, avoid, gap=22, sparkles=3, area=(1, 1, W - 2, hor - 8))

    ground(c, hor)
    # tufts of grass on the horizon
    for tx in (30, 54, 76, 150, 168, 196, 214, 244, 270, 300, 326, 352, 376):
        c.line(tx - 1, hor - 1, tx - 3, hor - 5)
        c.line(tx, hor - 1, tx + 1, hor - 6)
        c.line(tx + 1, hor - 1, tx + 4, hor - 4)

    # the glass jar: the light inside it is the brightest dither of the scene
    outline = [(jx - 5, 47), (jx - 5, 51), (jx - 8, 54), (jx - 8, 72), (jx - 6, 74), (jx + 6, 74),
               (jx + 8, 72), (jx + 8, 54), (jx + 5, 51), (jx + 5, 47)]
    inside = poly_mask(c, outline)
    glow(c, jx, 66, 15, 11, power=1.1, mask=inside)
    ink(c, np.logical_and(grow(inside), ~inside), margin=False)
    draw(c, outline)
    c.hline(jx - 6, jx + 6, 46)
    c.hline(jx - 6, jx + 6, 45)
    for yy in range(56, 70, 2):
        c.px(jx - 6, yy)
    for x, y in ((jx - 3, 68), (jx + 3, 61), (jx - 1, 56)):
        c.px(x, y)
        c.px(x + 1, y)
    # the stump
    stump = c.rect_mask(jx - 17, 75, jx + 17, hor - 1)
    ink(c, stump, margin=False)
    c.box(jx - 17, 75, jx + 17, hor)
    c.hline(jx - 17, jx + 17, 76, step=3)
    for gx in range(jx - 12, jx + 14, 7):
        c.vline(gx, 78, 80, step=2)
    # the lid, set aside at an angle
    ang = math.radians(-24)
    lc = (jx + 15, 38)
    pts = []
    for dx, dy in ((-8, -2), (8, -2), (8, 2), (-8, 2)):
        pts.append((lc[0] + dx * math.cos(ang) - dy * math.sin(ang), lc[1] + dx * math.sin(ang) + dy * math.cos(ang)))
    lid = poly_mask(c, pts)
    ink(c, lid)
    draw(c, pts + [pts[0]])

    # the firefly's wander, thinning out behind it
    path = [(jx, 42), (jx + 2, 33), (jx + 10, 26), (jx + 21, 27), (jx + 27, 35), (jx + 37, 40), (jx + 49, 35),
            (jx + 54, 24), (jx + 65, 18), (jx + 77, 22), (jx + 82, 32), (jx + 93, 36), (jx + 104, 29),
            (jx + 110, 22), (jx + 120, 19)]
    pix = trace(spline(path, 12))
    n = len(pix)
    for j, (x, y) in enumerate(pix):
        d = n - j
        step = 1 if d < 12 else 2 if d < 40 else 3 if d < 90 else 5
        if j % step == 0:
            c.px(x, y)
    fx, fy = path[-1]
    glow(c, fx, fy, 15, 13, power=2.3)
    ink(c, disc_mask(c, fx, fy, 3.2), margin=False)
    for d in range(3, 6):
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            c.px(fx + dx, fy + dy)
    c.disc(fx, fy, 2.0)

    word(c, "Curiosity.")
    return c


# ---------------------------------------------------------------- 3. Steady
# A long exposure of the night sky. Every star slides along its own circle, and the
# one at the centre does not move at all.
def steady():
    c = Canvas(W, H)
    hor = 80
    cx, cy = 166, 32
    rnd = random.Random(12)
    avoid = word_box("Steady.")
    avoid[hor - 6:, :] = True
    yy, xx = c.yy, c.xx
    avoid[np.hypot(xx - cx, yy - cy) < 96] = True
    star_field(c, 3, 20, avoid, gap=20, sparkles=2, area=(1, 1, W - 2, hor - 8))

    glow(c, cx, cy, 16, 13, power=2.3)
    radii = [7, 13, 20, 28, 37, 47, 58, 70, 83, 97]
    span = math.radians(46)
    for k, r in enumerate(radii):
        # the whole circle, faint
        full = [(cx + r * math.cos(2 * math.pi * i / 720), cy + r * math.sin(2 * math.pi * i / 720)) for i in range(721)]
        for i, (x, y) in enumerate(trace(full)):
            if i % 7 == 0 and 0 <= x < W and 0 <= y < hor - 2:
                c.px(x, y)
        # the trails, all the same length because the exposure is the same
        count = 1 if r < 14 else 2 if r < 50 else 3
        base = 1.1 + k * 0.42
        for j in range(count):
            a0 = base + j * 2 * math.pi / count
            seg = []
            for i in range(0, 61):
                a = a0 + span * i / 60
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                if 0 <= x < W - 1 and 1 <= y < hor - 3:
                    seg.append((x, y))
                elif len(seg) > 1:
                    draw(c, seg)
                    seg = []
                else:
                    seg = []
            if len(seg) > 1:
                draw(c, seg)
            hx, hy = cx + r * math.cos(a0 + span), cy + r * math.sin(a0 + span)
            if 2 <= hx < W - 3 and 3 <= hy < hor - 5:
                sparkle(c, fl(hx), fl(hy), 1 if r > 30 else 0)

    # the fixed star
    ink(c, disc_mask(c, cx, cy, 3.4), margin=False)
    for d in range(3, 8):
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            c.px(cx + dx, cy + dy)
    for d in (2, 3):
        for dx, dy in ((d, d), (-d, d), (d, -d), (-d, -d)):
            c.px(cx + dx, cy + dy)
    c.disc(cx, cy, 2.0)

    # a low hill and the ground
    hill = spline([(18, hor), (44, hor - 5), (84, hor - 9), (122, hor - 5), (150, hor)], 10)
    hm = poly_mask(c, hill + [(150, hor + 1), (18, hor + 1)])
    ink(c, hm, margin=False)
    ground(c, hor)
    draw(c, hill)
    for y in range(hor - 8, hor):
        for x in range(30, 140):
            if hm[y, x] and (x + y * 2) % 6 == 0:
                c.px(x, y)

    word(c, "Steady.")
    return c


SCENES = (("orchestrate", orchestrate), ("curiosity", curiosity), ("steady", steady))


def main():
    ap = argparse.ArgumentParser(prog="nightlight.banners")
    ap.add_argument("--out", default="assets/banners")
    ap.add_argument("--only", choices=[n for n, _ in SCENES])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, fn in SCENES:
        if a.only and a.only != name:
            continue
        im = fn().render(SCALE)
        assert im.size == (1584, 396), im.size
        save_png(im, os.path.join(a.out, "linkedin-" + name + ".png"))
        print(name, im.size)


if __name__ == "__main__":
    main()
