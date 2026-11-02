"""python -m nightlight static --out DIR   the cat card and the divider, used by the README
python -m nightlight live --out DIR     archived: the Manila desk scene with its time band"""
import argparse
import os
from datetime import datetime, timezone

from . import scenes
from .engine import save_gif, save_png

FPS = 12


def frames(fn, loop, scale):
    return [fn(i / FPS).render(scale) for i in range(int(loop * FPS))]


def live(out, now):
    loop = 10
    save_gif(frames(lambda t: scenes.desk(t, loop, now), loop, 4), os.path.join(out, "desk.gif"))


def static(out):
    save_png(scenes.divider().render(4), os.path.join(out, "divider-stars.png"))
    save_gif(frames(lambda t: scenes.cat(t, 8), 8, 2), os.path.join(out, "cat.gif"))


def main():
    ap = argparse.ArgumentParser(prog="nightlight")
    ap.add_argument("what", choices=["live", "static"])
    ap.add_argument("--out", default=".")
    ap.add_argument("--at", help="ISO time for live, for testing, e.g. 2026-11-02T12:00:00+08:00")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.what == "live":
        now = datetime.fromisoformat(a.at) if a.at else datetime.now(timezone.utc)
        live(a.out, now)
    else:
        static(a.out)


if __name__ == "__main__":
    main()
