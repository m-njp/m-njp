"""Every picture on the profile, each a function of time."""
import math
import os

import numpy as np
from PIL import Image

from .engine import (HERE, Canvas, ease, grow, halftone, lines, meter, moon,
                     osc, text_width)
from . import sky
from . import props as P

TERM = [[3, 4], [5], [3, 3, 6], [7, 2], [3, 5, 4], [4, 6]]


def twinkle(c, t, stars, period=8.0):
    for i, (sx, sy) in enumerate(stars):
        c.px(sx, sy)
        if osc(t, period + (i % 4) * 1.5, i * 1.7) > 0.8:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c.px(sx + dx, sy + dy)


# ------------------------------------------------------------ live desk header
def desk(t, loop, now):
    W, H = 256, 114
    c = Canvas(W, H)
    dy_ = 72
    elev, az = sky.sun(now)
    phase = sky.moon_phase(now)
    local = sky.manila(now)

    # window onto the real Manila sky
    x0, y0, x1, y1 = 14, 8, 86, 56
    inside = c.rect_mask(x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    stars = [(20, 14), (31, 12), (44, 21), (24, 27), (78, 31), (38, 33), (19, 44), (57, 47), (70, 44),
             (28, 50), (49, 13), (62, 24), (81, 15), (66, 51)]
    if elev < -6:
        twinkle(c, t, stars)
        moon(c, 70, 20, 7, phase)
        P.shooting_star(c, t, 6.0, 1.2, 82, 12, -44, 20, mask=inside)
    elif elev < 2:
        c.L = np.maximum(c.L, np.clip(3 - (y1 - c.yy) / 3, 0, 3) * inside)
        twinkle(c, t, stars[::3])
        if elev > -1:
            c.disc(22 if az < 180 else 78, y1 - 2, 5)
    else:
        f = (az - 70) / 220
        sx = x0 + 8 + max(0, min(1, f)) * (x1 - x0 - 16)
        sy = y1 - 6 - min(1, elev / 80) * (y1 - y0 - 14)
        c.pool(sx, sy, 11, 6, mask=inside)
        c.disc(sx, sy, 4)
        rot = math.pi * t / loop
        for k in range(8):
            a = rot + k * math.pi / 4
            for r in (6.5, 7.5):
                c.px(sx + math.cos(a) * r, sy + math.sin(a) * r)
        for cx0, cy0, ph in ((22, 46, 0.0), (58, 48, 2.0)):
            cx = cx0 + round(osc(t, loop, ph) * 3)
            cl = np.zeros((H, W), bool)
            for ox, oy, rr in ((0, 0, 4), (5, -2, 5), (10, 0, 4)):
                cl |= (c.xx - cx - ox) ** 2 + (c.yy - cy0 - oy) ** 2 <= rr * rr
            cl &= (c.yy <= cy0 + 2) & inside
            c.set_mask(cl, False)
            c.P |= grow(cl) & ~cl & inside
    c.box(x0, y0, x1, y1)
    c.box(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    c.vline((x0 + x1) // 2, y0, y1)
    c.hline(x0, x1, (y0 + y1) // 2)
    c.hline(x0 - 5, x1 + 5, y1 + 3)

    # hanging planter from the ceiling, beside the window
    c.line(92, 0, 89, 13); c.line(92, 0, 95, 13)
    P.pot(c, 88, 14, 96, 20)
    P.vine(c, 88, 20, 22, t, loop, 0.0, -1)
    P.vine(c, 95, 20, 16, t, loop, 1.3, 1)

    # snake plant on the floor under the window
    P.snake_plant(c, 48, 82, 22, t, loop)
    P.pot(c, 39, 82, 57, 95)

    # the lamp sits at the back left of the desk and points down at the work
    P.angle_lamp(c, 106, dy_ - 1, (99, 44), (112, 30), 0.3, (120, 41), dy_, 126)

    # desk
    c.hline(96, 252, dy_)
    c.hline(96, 252, dy_ + 4)
    c.vline(96, dy_, dy_ + 4)
    c.vline(252, dy_, dy_ + 4)
    for lx in (101, 246):
        c.vline(lx, dy_ + 5, 95)
        c.vline(lx + 2, dy_ + 5, 95)
    # pc tower under the desk, its light breathing
    P.knock_out(c, c.rect_mask(220, 79, 236, 95))
    c.box(220, 79, 236, 95)
    for yy in range(82, 93, 2):
        c.hline(223, 228, yy, step=2)
    if osc(t, 3.0) > -0.3:
        c.px(233, 82)

    # framed art: the Nightlight orb, its light circling and a moon on orbit
    P.frame(c, 152, 4, 186, 27)
    P.orb(c, 169, 16, 7, t, loop, moon_r=1.8, orbit=(12, 3))

    # wall shelf, right, with books and a trailing pothos
    P.shelf(c, 200, 252, 40)
    P.books_upright(c, 203, 39, [9, 11, 8, 10])
    P.pot(c, 231, 33, 239, 39)
    for dx, h in ((-3, 4), (0, 6), (3, 4)):
        c.line(235, 33, 235 + dx, 33 - h)
    P.vine(c, 230, 40, 18, t, loop, 0.6, -1)
    P.vine(c, 240, 40, 13, t, loop, 2.1, 1)

    # wall clock on Manila time
    ccx, ccy = 238, 16
    c.ring(ccx, ccy, 7.2, 8.2)
    for k in range(0, 12, 3):
        a = k * math.pi / 6
        c.px(ccx + math.sin(a) * 6, ccy - math.cos(a) * 6)
    hh = (local.hour % 12 + local.minute / 60) / 12 * 2 * math.pi
    mm = local.minute / 60 * 2 * math.pi
    c.line(ccx, ccy, ccx + math.sin(hh) * 3.5, ccy - math.cos(hh) * 3.5)
    c.line(ccx, ccy, ccx + math.sin(mm) * 5.5, ccy - math.cos(mm) * 5.5)

    # monitor and terminal
    m0x, m0y, m1x, m1y = 142, 31, 196, 64
    P.knock_out(c, c.rect_mask(m0x, m0y, m1x, m1y))
    c.box(m0x, m0y, m1x, m1y)
    c.box(m0x + 2, m0y + 2, m1x - 2, m1y - 2)
    c.fill(166, m1y + 1, 172, dy_ - 3)
    c.hline(160, 178, dy_ - 1)
    c.hline(160, 178, dy_ - 2)
    total = sum(sum(l) + len(l) for l in TERM)
    typed = int(total * min(1, t / (loop * 0.82)))
    yl = m0y + 7
    n = 0
    cur = (m0x + 10, yl)
    for row in TERM:
        x = m0x + 6
        c.px(x, yl - 1)
        c.px(x + 1, yl)
        c.px(x, yl + 1)
        x += 4
        for wl in row:
            for k in range(wl):
                if n < typed:
                    c.px(x, yl)
                    if (k * 7 + len(row)) % 3 == 0:
                        c.px(x, yl - 1)
                    cur = (x + 2, yl)
                    x += 2
                n += 1
            if n <= typed:
                x += 2
            n += 1
        yl += 4
        if n > typed:
            break
    if osc(t, 1.0) > -0.2:
        c.fill(cur[0], cur[1] - 1, cur[0] + 1, cur[1] + 1)

    # keyboard and mouse
    P.knock_out(c, c.rect_mask(150, dy_ - 3, 190, dy_ - 1))
    c.box(150, dy_ - 3, 190, dy_ - 1)
    c.hline(152, 188, dy_ - 2, step=2)
    c.fill(194, dy_ - 2, 197, dy_ - 1)
    c.px(195, dy_ - 3); c.px(196, dy_ - 3)

    # mug with steam
    gx = 206
    P.knock_out(c, c.rect_mask(gx - 2, dy_ - 8, gx + 6, dy_ - 1))
    c.box(gx - 2, dy_ - 6, gx - 1, dy_ - 3)
    c.box(gx, dy_ - 8, gx + 6, dy_ - 1)
    for k in range(4):
        ph = (t / 2.5 + k / 4) % 1
        if ph < 0.7:
            c.px(gx + 3 + osc(ph * 4, 4, k) * 1.4, dy_ - 11 - ph * 12)

    # pen cup and a succulent
    P.knock_out(c, c.rect_mask(216, dy_ - 7, 222, dy_ - 1))
    c.box(216, dy_ - 7, 222, dy_ - 1)
    c.line(218, dy_ - 8, 217, dy_ - 13); c.line(220, dy_ - 8, 221, dy_ - 14); c.line(219, dy_ - 8, 219, dy_ - 11)
    P.succulent(c, 233, dy_ - 7)
    P.pot(c, 229, dy_ - 6, 237, dy_ - 1)

    # a cat asleep on the desk, under the lamp
    ox = -85
    br = 0.5 + 0.5 * osc(t, 3.4)
    body = (((c.xx - 211 - ox) / 8.5) ** 2 + ((c.yy - (68.4 - br * 0.6)) / (3.8 + br * 0.6)) ** 2 <= 1) & (c.yy < dy_)
    head = ((c.xx - 201 - ox) ** 2 + (c.yy - 67.5) ** 2 <= 12.5) & (c.yy < dy_)
    ears = (c.rect_mask(198 + ox, 63, 199 + ox, 64) | c.rect_mask(203 + ox, 63, 204 + ox, 64)
            | c.rect_mask(198 + ox, 62, 198 + ox, 62) | c.rect_mask(204 + ox, 62, 204 + ox, 62))
    cm = body | head | ears
    c.set_mask(cm, False)
    c.P |= grow(cm) & ~cm & (c.yy < dy_)
    c.hline(199 + ox, 200 + ox, 68)
    c.hline(202 + ox, 203 + ox, 68)
    flick = round(osc(t, 2.6, 1.0))
    c.hline(205 + ox, 219 + ox, 71)
    c.px(220 + ox, 70 + flick)
    c.px(220 + ox, 69 + flick)
    zp = (t % 4.0) / 4.0
    if zp < 0.75:
        zx, zy = round(196 + ox - zp * 4), round(58 - zp * 9)
        for dx, dy in ((0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)):
            c.px(zx + dx, zy + dy)

    strip(c, 96, now)
    return c


# ------------------------------------------------------------ live now strip
def strip(c, oy, now):
    """The now band: Manila time, the day as a Meter, and the sun or the moon."""
    W = c.w
    local = sky.manila(now)
    elev, _ = sky.sun(now)
    phase = sky.moon_phase(now)
    c.hline(0, W - 1, oy, step=2)
    left = "MANILA " + local.strftime("%H:%M")
    c.text(4, oy + 1, left, 13)
    if elev > 0:
        label = "sun up"
    elif elev > -6:
        label = "twilight"
    else:
        label = sky.phase_name(phase)
    lw = text_width(label, 13)
    c.text(W - 4 - lw, oy + 1, label, 13)
    ix = W - 4 - lw - 9
    if elev > -6:
        c.disc(ix, oy + 9, 3)
        for k in range(8):
            a = k * math.pi / 4
            c.px(ix + math.cos(a) * 5, oy + 9 + math.sin(a) * 5)
    else:
        moon(c, ix, oy + 9, 4, phase, halo=False)
    mx0 = 4 + text_width(left, 13) + 8
    mx1 = ix - 10
    cells, gap = 24, 1
    cw = max(2, (mx1 - mx0 - (cells - 1) * gap) // cells)
    total = cells * cw + (cells - 1) * gap
    meter(c, mx0 + (mx1 - mx0 - total) // 2, oy + 6, cells, sky.day_fraction(now), cw=cw, ch=7, gap=gap)


# ------------------------------------------------------------ dividers
def divider():
    W, H = 256, 7
    c = Canvas(W, H)
    for x in range(2, W, 4):
        c.px(x, 3)
    for sx in (64, 128, 192):
        c.clear(sx - 4, 0, sx + 4, H - 1)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            c.px(sx + dx, 3 + dy)
    return c


# ------------------------------------------------------------ cat, in halftone
def cat_scene(t, loop):
    """A cat on a desktop computer. Tone for the halftone, plus crisp marks on top."""
    W, H = 360, 216
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    g = np.zeros((H, W))
    ink = np.zeros((H, W), bool)
    paper = np.zeros((H, W), bool)

    def ell(cx, cy, rx, ry, base, light=0.3):
        nx = (xx - cx) / rx
        ny = (yy - cy) / ry
        d = nx * nx + ny * ny
        m = d <= 1
        nz = np.sqrt(np.clip(1 - d, 0, 1))
        g[m] = np.clip(base + light * (-0.45 * nx - 0.55 * ny + 0.5 * nz) - 0.12, 0, 1)[m]
        return m

    def tri(p0, p1, p2):
        d = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
        a = ((p1[1] - p2[1]) * (xx - p2[0]) + (p2[0] - p1[0]) * (yy - p2[1])) / d
        b = ((p2[1] - p0[1]) * (xx - p2[0]) + (p0[0] - p2[0]) * (yy - p2[1])) / d
        return (a >= 0) & (b >= 0) & (a + b <= 1)

    def seg(x0, y0, x1, y1, mask):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            f = i / n
            x, y = int(round(x0 + (x1 - x0) * f)), int(round(y0 + (y1 - y0) * f))
            if 0 <= x < W and 0 <= y < H:
                mask[y, x] = True

    ph = (t % loop) / loop
    # computer
    cx0, cy0, cx1, cy1 = 112, 104, 252, 194
    case = (xx >= cx0) & (xx <= cx1) & (yy >= cy0) & (yy <= cy1)
    g[case] = 0.38 + (cy1 - yy[case]) / (cy1 - cy0) * 0.12
    scr = (xx >= cx0 + 14) & (xx <= cx1 - 14) & (yy >= cy0 + 12) & (yy <= cy1 - 18)
    g[scr] = 0
    # screen marks, crisp
    sx, sy = cx0 + 22, cy0 + 22
    seg(sx, sy, sx + 3, sy + 3, paper); seg(sx + 3, sy + 3, sx, sy + 6, paper)
    if osc(t, 1.0) > -0.2:
        paper[sy - 1:sy + 8, sx + 8:sx + 13] = True
    for i, ln in enumerate((60, 38, 74, 50)):
        paper[sy + 14 + i * 9, sx:sx + ln:2] = True
    # base and keyboard
    seg(cx0 + 40, cy1 + 1, cx0 + 40, cy1 + 6, paper); seg(cx1 - 40, cy1 + 1, cx1 - 40, cy1 + 6, paper)
    seg(20, 202, W - 20, 202, paper)
    kb = (xx >= 120) & (xx <= 244) & (yy >= 206) & (yy <= 212)
    g[kb] = 0.5

    # cat loafing on top of the computer
    body = ell(206, 86, 50, 26, 0.8)
    # tail hangs off the right side and sways
    sway = osc(t, loop / 2) * 7
    for i in range(70):
        f = i / 69
        tx = 250 + f * 10 + sway * f * f
        ty = 96 + f * 70
        r = 7 - f * 2
        m = (xx - tx) ** 2 + (yy - ty) ** 2 <= r * r
        g[m] = np.maximum(g[m], 0.8 - f * 0.15)
    ell(176, 108, 10, 5, 1.0, 0.1)
    ell(198, 109, 10, 5, 1.0, 0.1)
    hx, hy = 162, 70
    tw = 3 if 0.6 < ph < 0.64 else 0
    for sgn in (-1, 1):
        ex = hx + sgn * 15
        tip = (ex + sgn * 4, hy - 44 - (tw if sgn > 0 else 0))
        g[tri(tip, (ex - 12, hy - 14), (ex + 12, hy - 14))] = 0.8
        g[tri((tip[0], tip[1] + 10), (ex - 6, hy - 16), (ex + 6, hy - 16))] = 1.0
    head = ell(hx, hy, 30, 26, 0.85)
    # face, crisp
    blink = 0.3 < ph < 0.34 or 0.82 < ph < 0.86
    for sgn in (-1, 1):
        ex, ey = hx + sgn * 12, hy - 2
        if blink:
            ink |= (np.abs(yy - ey) < 1.5) & (np.abs(xx - ex) < 6)
        else:
            ink |= ((xx - ex) / 5.5) ** 2 + ((yy - ey) / 7) ** 2 <= 1
            paper |= ((xx - ex - 1.5) ** 2 + (yy - ey + 3) ** 2) <= 2.5
    ink |= tri((hx - 4, hy + 8), (hx + 4, hy + 8), (hx, hy + 12))
    seg(hx, hy + 12, hx - 4, hy + 16, ink); seg(hx, hy + 12, hx + 4, hy + 16, ink)
    for sgn in (-1, 1):
        for k, dy in enumerate((-2, 2, 6)):
            seg(hx + sgn * 30, hy + 8 + dy, hx + sgn * 46, hy + 4 + dy * 2.2, paper)
    return g, ink, paper


def cat(t, loop):
    g, ink, paper = cat_scene(t, loop)
    pad = 60
    g = np.pad(g, ((0, 0), (pad, 0)))
    ink = np.pad(ink, ((0, 0), (pad, 0)))
    paper = np.pad(paper, ((0, 0), (pad, 0)))
    c = Canvas(g.shape[1], g.shape[0])
    c.P = halftone(g, cell=5, angle=45)
    c.P |= paper
    c.P &= ~ink
    room(c, t, loop, ink)
    # speech bubble, crisp, to the left of the cat's face
    x0, y0, x1, y1 = 48, 74, 160, 98
    P.knock_out(c, c.rect_mask(x0, y0, x1, y1))
    c.hline(x0 + 2, x1 - 2, y0)
    c.hline(x0 + 2, x1 - 2, y1)
    c.vline(x0, y0 + 2, y1 - 2)
    c.vline(x1, y0 + 2, y1 - 2)
    for px_, py_ in ((x0 + 1, y0 + 1), (x1 - 1, y0 + 1), (x0 + 1, y1 - 1), (x1 - 1, y1 - 1)):
        c.px(px_, py_)
    c.vline(x1, y0 + 7, y0 + 17, on=False)
    c.line(x1, y0 + 7, x1 + 18, y0 + 6)
    c.line(x1, y0 + 17, x1 + 18, y0 + 6)
    c.P |= c.text_mask((x0 + x1) // 2, y0 + 6, "hi, welcome.", 13, anchor="ma")
    return c


def room(c, t, loop, keep):
    """The night room around the cat, in the house Bayer style."""
    fy = 202
    # window, top right, with a crescent moon, stars and the odd shooting star
    x0, y0, x1, y1 = 334, 16, 406, 96
    c.clear(x0, y0, x1, y1)
    inside = c.rect_mask(x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    stars = [(342, 24), (356, 21), (348, 40), (362, 52), (341, 64), (398, 70), (352, 84), (378, 88), (395, 52), (371, 30)]
    twinkle(c, t, stars)
    moon(c, 390, 32, 6, 0.2)
    P.shooting_star(c, t, 5.0, 1.2, 404, 20, -50, 26, mask=inside)
    c.box(x0, y0, x1, y1)
    c.box(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    c.vline((x0 + x1) // 2, y0, y1)
    c.hline(x0, x1, (y0 + y1) // 2)
    c.hline(x0 - 5, x1 + 5, y1 + 3)
    c.pool(372, fy + 6, 46, 5, ry=0.22, mask=c.yy > fy + 1)

    # wall shelf, top left: books, the orb as a little desk globe, and a trailing pothos
    P.shelf(c, 18, 150, 40)
    nx = P.books_upright(c, 22, 39, [12, 14, 10, 13, 11])
    gx0 = nx + 18
    P.orb(c, gx0, 25, 10, t, loop, moon_r=2.0, orbit=(15, 3))
    c.vline(gx0, 36, 38)
    c.hline(gx0 - 5, gx0 + 5, 39)
    P.pot(c, 118, 32, 128, 39)
    for dx, h in ((-3, 5), (0, 7), (3, 5)):
        c.line(123, 32, 123 + dx, 32 - h)
    P.vine(c, 117, 41, 24, t, loop, 0.4, -1)
    P.vine(c, 129, 41, 18, t, loop, 1.9, 1)
    P.vine(c, 141, 41, 12, t, loop, 3.0, 1)


    # stacked books and a mug, left of the computer
    for i, (a, b) in enumerate(((84, 132), (88, 128), (82, 126))):
        y = fy - 1 - i * 6
        P.knock_out(c, c.rect_mask(a, y - 5, b, y))
        c.box(a, y - 5, b, y)
        c.hline(a + 3, b - 3, y - 2 - (i % 2), step=2)
    gx = 142
    P.knock_out(c, c.rect_mask(gx - 3, fy - 13, gx + 9, fy - 1))
    c.box(gx - 3, fy - 9, gx - 1, fy - 4)
    c.box(gx, fy - 13, gx + 9, fy - 1)
    for k in range(4):
        ph = (t / 2.5 + k / 4) % 1
        if ph < 0.7:
            c.px(gx + 4 + osc(ph * 4, 4, k) * 1.6, fy - 16 - ph * 14)


    # a quiet floor band
    c.level_rect(0, fy + 10, c.w - 1, fy + 10, 3)
    c.K |= keep
    c.P &= ~keep
