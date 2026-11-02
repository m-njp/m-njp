"""Nightlight: two inks, a 4 by 4 Bayer dither, a small grid scaled by whole pixels."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

INK = (0x11, 0x14, 0x1D)
PAPER = (0xEE, 0xE7, 0xD3)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
HERE = os.path.dirname(os.path.abspath(__file__))
PIXEL = os.path.join(HERE, "fonts", "GeistPixel.ttf")
PLUS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def grow(m):
    k = np.zeros_like(m)
    for dx, dy in PLUS:
        k |= np.roll(np.roll(m, dy, 0), dx, 1)
    return k


class Canvas:
    """L holds dither levels 0..16, P forces paper, K forces ink."""

    def __init__(s, w, h):
        s.w, s.h = w, h
        s.L = np.zeros((h, w))
        s.P = np.zeros((h, w), bool)
        s.K = np.zeros((h, w), bool)
        s.yy, s.xx = np.mgrid[0:h, 0:w]
        s.T = BAYER[s.yy % 4, s.xx % 4]

    # light
    def pool(s, cx, cy, r, peak, rx=1.0, ry=1.0, mask=None):
        d = np.sqrt(((s.xx - cx) / rx) ** 2 + ((s.yy - cy) / ry) ** 2)
        f = np.clip(peak * (1 - d / r), 0, 16)
        if mask is not None:
            f = f * mask
        s.L = np.maximum(s.L, f)

    def rect_mask(s, x0, y0, x1, y1):
        return (s.xx >= x0) & (s.xx <= x1) & (s.yy >= y0) & (s.yy <= y1)

    def level_disc(s, cx, cy, r, lv):
        m = (s.xx - cx) ** 2 + (s.yy - cy) ** 2 <= r * r
        s.L[m] = np.maximum(s.L[m], lv)

    def level_rect(s, x0, y0, x1, y1, lv):
        m = s.rect_mask(x0, y0, x1, y1)
        s.L[m] = np.maximum(s.L[m], lv)

    # line art
    def px(s, x, y, on=True):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < s.w and 0 <= y < s.h:
            s.P[y, x] = on
            if not on:
                s.K[y, x] = True

    def hline(s, x0, x1, y, on=True, step=1):
        for x in range(int(x0), int(x1) + 1, step):
            s.px(x, y, on)

    def vline(s, x, y0, y1, on=True, step=1):
        for y in range(int(y0), int(y1) + 1, step):
            s.px(x, y, on)

    def box(s, x0, y0, x1, y1, on=True):
        s.hline(x0, x1, y0, on)
        s.hline(x0, x1, y1, on)
        s.vline(x0, y0, y1, on)
        s.vline(x1, y0, y1, on)

    def fill(s, x0, y0, x1, y1, on=True):
        m = s.rect_mask(x0, y0, x1, y1)
        s.set_mask(m, on)

    def set_mask(s, m, on=True):
        if on:
            s.P |= m
        else:
            s.P &= ~m
            s.K |= m
            s.L[m] = 0

    def line(s, x0, y0, x1, y1, on=True):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n
            s.px(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, on)

    def disc(s, cx, cy, r, on=True):
        s.set_mask((s.xx - cx) ** 2 + (s.yy - cy) ** 2 <= r * r, on)

    def ring(s, cx, cy, r0, r1):
        d2 = (s.xx - cx) ** 2 + (s.yy - cy) ** 2
        s.P |= (d2 <= r1 * r1) & (d2 >= r0 * r0)

    def clear(s, x0, y0, x1, y1):
        m = s.rect_mask(x0, y0, x1, y1)
        s.L[m] = 0
        s.P &= ~m

    def stamp(s, m):
        """Draw a paper mask with an ink outline so it reads over dither."""
        k = grow(m) & ~m
        s.L[k] = 0
        s.P &= ~k
        s.P |= m

    def text_mask(s, x, y, txt, size=12, anchor="la"):
        f = ImageFont.truetype(PIXEL, size)
        im = Image.new("1", (s.w, s.h), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((x, y), txt, font=f, fill=1, anchor=anchor)
        return np.array(im, bool)

    def text(s, x, y, txt, size=12, anchor="la"):
        m = s.text_mask(x, y, txt, size, anchor)
        s.stamp(m)
        return m

    def bits(s):
        return ((s.L > s.T) & ~s.K) | s.P

    def render(s, scale):
        return to_image(s.bits(), scale)


def text_width(txt, size=12):
    f = ImageFont.truetype(PIXEL, size)
    b = f.getbbox(txt)
    return b[2] - b[0]


def to_image(bits, scale):
    rgb = np.where(bits[..., None], np.array(PAPER), np.array(INK)).astype(np.uint8)
    im = Image.fromarray(rgb, "RGB")
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def save_gif(frames, path, fps=12):
    pal = Image.new("P", (1, 1))
    pal.putpalette(list(INK) + list(PAPER) + [0] * 762)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=round(1000 / fps),
              loop=0, optimize=True, disposal=1)


def save_png(frame, path):
    pal = Image.new("P", (1, 1))
    pal.putpalette(list(INK) + list(PAPER) + [0] * 762)
    frame.quantize(palette=pal, dither=Image.Dither.NONE).save(path, optimize=True)


def ease(x):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))


def osc(t, period, offset=0.0):
    return math.sin(2 * math.pi * (t / period) + offset)


# ImageFx effects. gray is a float array, 0 for ink and 1 for paper.
def halftone(gray, cell=4, angle=45):
    h, w = gray.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    a = math.radians(angle)
    u = xx * math.cos(a) + yy * math.sin(a)
    v = -xx * math.sin(a) + yy * math.cos(a)
    cu = (np.floor(u / cell) + 0.5) * cell
    cv = (np.floor(v / cell) + 0.5) * cell
    # sample tone at the dot center so each dot is one size
    sx = np.clip(np.round(cu * math.cos(a) - cv * math.sin(a)), 0, w - 1).astype(int)
    sy = np.clip(np.round(cu * math.sin(a) + cv * math.cos(a)), 0, h - 1).astype(int)
    tone = gray[sy, sx]
    r = cell * 0.62 * np.sqrt(np.clip(tone, 0, 1))
    return (u - cu) ** 2 + (v - cv) ** 2 < r * r


def lines(gray, cell=4):
    h, w = gray.shape
    yy = np.mgrid[0:h, 0:w][0]
    centre = (yy % cell) - (cell - 1) / 2
    return np.abs(centre) < np.clip(gray, 0, 1) * cell / 2


# Components
def meter(c, x, y, cells, value, cw=5, ch=7, gap=2):
    """Segmented bar. Full cells solid, the leading cell steps through three dither levels."""
    filled = value * cells
    for i in range(cells):
        x0 = x + i * (cw + gap)
        f = filled - i
        if f >= 1:
            c.fill(x0, y, x0 + cw - 1, y + ch - 1)
        else:
            c.fill(x0 - 1, y - 1, x0 + cw, y + ch, on=False)
            c.K[y:y + ch, x0:x0 + cw] = False
            if f > 0:
                c.level_rect(x0, y, x0 + cw - 1, y + ch - 1, (4, 8, 12)[min(2, int(f * 3))])
            c.px(x0 + cw // 2, y + ch - 1)


def moon(c, cx, cy, r, phase, halo=True):
    """phase 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter."""
    dx = c.xx - cx
    dy = c.yy - cy
    inside = dx ** 2 + dy ** 2 <= r * r
    w = np.sqrt(np.clip(r * r - dy ** 2, 0, None))
    k = math.cos(2 * math.pi * phase)
    lit = (dx > k * w) if phase <= 0.5 else (dx < -k * w)
    lit &= inside
    frac = lit.sum() / max(1, inside.sum())
    if halo and frac > 0.15:
        c.pool(cx, cy, r + 4, 3.5 * frac + 1)
    c.set_mask(inside, False)
    c.K[inside] = False
    rim = inside & ~((dx ** 2 + dy ** 2) <= (r - 1) ** 2) & ~lit
    c.L[rim] = np.maximum(c.L[rim], 4)
    c.P |= lit
