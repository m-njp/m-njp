"""Room props in the Nightlight style: one pixel outlines, sparse patterns, dither only near a light."""
import math

import numpy as np

from .engine import Canvas, grow, osc


def dots(c, mask, gx=2, gy=2, ox=0, oy=0):
    """Fill a mask with a dot pattern anchored to the screen grid."""
    c.P |= mask & ((c.xx - ox) % gx == 0) & ((c.yy - oy) % gy == 0)


def knock_out(c, mask):
    """Clear a shape to ink with a one pixel ink margin, so it reads over light."""
    m = mask | grow(mask)
    c.L[m] = 0
    c.P &= ~m


def pot(c, x0, y0, x1, y1):
    knock_out(c, c.rect_mask(x0, y0, x1, y1))
    c.hline(x0 - 1, x1 + 1, y0)
    c.line(x0, y0 + 1, x0 + 1, y1)
    c.line(x1, y0 + 1, x1 - 1, y1)
    c.hline(x0 + 1, x1 - 1, y1)
    c.hline(x0 + 2, x1 - 2, y0 + 3, step=2)


def snake_plant(c, cx, base, height, t, loop, blades=5):
    """Upright pointed blades, banded with dashes, swaying a pixel."""
    for i in range(blades):
        f = i / max(1, blades - 1) - 0.5
        h = height * (0.7 + 0.3 * math.cos(f * 2.2))
        lean = f * height * 0.35 + osc(t, loop, i) * 0.8
        bx = cx + f * 8
        tip = (bx + lean, base - h)
        w = 2.2
        c.line(bx - w, base, tip[0], tip[1])
        c.line(bx + w, base, tip[0], tip[1])
        for k in range(3, int(h) - 3, 4):
            y = base - k
            x = bx + lean * (k / h)
            c.px(x, y)


def vine(c, x, y, length, t, loop, phase=0.0, side=1):
    """A trailing stem that hangs and sways, with leaves on alternate sides."""
    pts = []
    for k in range(length):
        f = k / max(1, length - 1)
        sway = osc(t, loop, phase) * 2.2 * f * f
        px_ = x + side * math.sin(f * 2.6 + phase) * 2 + sway
        pts.append((px_, y + k))
        c.px(px_, y + k)
    for k in range(3, length, 4):
        lx, ly = pts[k]
        s = 1 if (k // 4) % 2 else -1
        c.px(lx + s, ly)
        c.px(lx + 2 * s, ly - 1)
        c.px(lx + s, ly - 1)


def succulent(c, cx, base):
    for dx, h in ((-4, 3), (-2, 5), (0, 6), (2, 5), (4, 3)):
        c.line(cx, base, cx + dx, base - h)
    c.px(cx, base - 7)


def books_upright(c, x0, base, heights, lean_last=True):
    x = x0
    for i, h in enumerate(heights):
        w = 3 if i % 3 else 4
        if lean_last and i == len(heights) - 1:
            c.line(x, base, x + 4, base - h)
            c.line(x + 3, base, x + 7, base - h)
            c.line(x + 4, base - h, x + 7, base - h)
            x += 8
            continue
        knock_out(c, c.rect_mask(x, base - h, x + w, base))
        c.box(x, base - h, x + w, base)
        c.px(x + w // 2, base - h + 2)
        x += w + 1
    return x


def shelf(c, x0, x1, y):
    c.hline(x0, x1, y)
    c.hline(x0 + 1, x1 - 1, y + 1, step=2)
    for bx in (x0 + 4, x1 - 4):
        c.line(bx, y + 2, bx - 3, y + 5)


def shooting_star(c, t, start, length, x0, y0, dx, dy, mask=None):
    k = (t - start) / length
    if not 0 <= k <= 1:
        return
    pts = [(x0 + dx * k, y0 + dy * k)]
    for i in (2, 4, 6):
        tk = k - i * 0.03
        if tk >= 0:
            pts.append((x0 + dx * tk, y0 + dy * tk))
    for x, y in pts:
        xi, yi = int(round(x)), int(round(y))
        if mask is None or (0 <= yi < c.h and 0 <= xi < c.w and mask[yi, xi]):
            c.px(xi, yi)


def orb(c, cx, cy, R, t, period, moon_r=2.0, orbit=(13, 3)):
    """The Nightlight orb: a sphere lit by a light that circles it, and a small moon on an orbit."""
    a = 2 * math.pi * (t / period)
    lx, ly, lz = math.cos(a) * 0.85, -0.4, 0.5 + 0.5 * math.sin(a)
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    nx = (c.xx - cx) / R
    ny = (c.yy - cy) / R
    r2 = nx * nx + ny * ny
    inside = r2 < 1
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    d = nx * lx + ny * ly + nz * lz
    lv = np.round(np.clip((d + 0.25) / 1.05, 0, 1) * 4) * 4
    knock_out(c, inside)
    c.L[inside] = lv[inside]
    rim = inside & (np.sqrt((c.xx - cx) ** 2 + (c.yy - cy) ** 2) > R - 1.2) & (d > -0.25)
    c.P |= rim
    oa = 2 * math.pi * (t / period)
    mx = cx + math.cos(oa) * orbit[0]
    my = cy - 1 + math.sin(oa) * orbit[1]
    hidden = math.sin(oa) < 0 and abs(mx - cx) < R - 1
    if not hidden:
        m = (c.xx - mx) ** 2 + (c.yy - my) ** 2 <= (moon_r + 0.8) ** 2
        knock_out(c, m)
        c.disc(mx + lx, my + ly, moon_r * 0.7)


def angle_lamp(c, base_x, base_y, elbow, hinge, shade_dir, bulb, desk_y, pool_x, reach=26, peak=13):
    """An architect lamp at the back of the desk: base, two arms, a shade pointing down at the work."""
    bx, by = bulb
    # light first, so the lamp draws over it
    down = (c.yy > by) & (c.yy < desk_y)
    cone = down & (np.abs(c.xx - (bx + (c.yy - by) * shade_dir)) < (c.yy - by) * 0.5 + 2)
    d = np.sqrt((c.xx - bx) ** 2 + (c.yy - by) ** 2)
    c.L = np.maximum(c.L, np.clip(3.5 - d / 8, 0, 16) * cone)
    c.pool(pool_x, desk_y + 1, reach, peak, ry=0.3, mask=(c.yy > desk_y) & (c.yy < desk_y + 5))
    c.pool(bx, by + 1, 6, 8, mask=c.yy >= by)
    # base, arms, joints
    c.fill(base_x - 6, base_y - 1, base_x + 6, base_y)
    c.fill(base_x - 1, base_y - 3, base_x + 1, base_y - 2)
    for o in (0, 1):
        c.line(base_x + o, base_y - 3, elbow[0] + o, elbow[1])
        c.line(elbow[0] + o, elbow[1], hinge[0] + o, hinge[1])
    c.disc(elbow[0] + 0.5, elbow[1], 1.6)
    c.disc(hinge[0] + 0.5, hinge[1], 1.6)
    # shade: a cone from the hinge to an opening around the bulb
    ax, ay = bx - hinge[0], by - hinge[1]
    L = math.hypot(ax, ay)
    px_, py_ = -ay / L, ax / L
    e0 = (bx + px_ * 6 - ax / L * 1, by + py_ * 6 - ay / L * 1)
    e1 = (bx - px_ * 6 - ax / L * 1, by - py_ * 6 - ay / L * 1)
    sh = Canvas(c.w, c.h)
    for i in range(41):
        f = i / 40
        sh.line(hinge[0], hinge[1], e0[0] + (e1[0] - e0[0]) * f, e0[1] + (e1[1] - e0[1]) * f)
    m = sh.P | grow(sh.P)
    c.L[m] = 0
    c.P &= ~m
    c.line(hinge[0], hinge[1], *e0)
    c.line(hinge[0], hinge[1], *e1)
    c.line(*e0, *e1)
    c.disc(bx, by, 1.6)


def frame(c, x0, y0, x1, y1):
    knock_out(c, c.rect_mask(x0, y0, x1, y1))
    c.box(x0, y0, x1, y1)
    c.box(x0 + 2, y0 + 2, x1 - 2, y1 - 2)
