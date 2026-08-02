#!/usr/bin/env python3
"""Van Gogh's Starry Night as living ASCII: the painting is embedded in the
source, its brushstroke directions steer the characters, and the sky swirls
while the stars turn. Runs fully offline. Ctrl+C to quit."""
import argparse
import signal
import sys
import time

from . import config, painting, terminal
from .renderer import Renderer, fit_canvas


def auto_fps(cells):
    """Frames per second the terminal can carry without pinning a core."""
    if cells <= 12000:
        return 20.0
    if cells <= 30000:
        return 15.0
    if cells <= 60000:
        return 11.0
    return 8.0


def print_density_report():
    """One character is one pixel of the finished picture, so the terminal's
    cell count *is* the resolution. This says where you stand and what a
    smaller font would buy."""
    art = painting.load()
    cols, lines = terminal.get_size()
    cw, ch, _, _ = fit_canvas(cols, lines, art.shape[1], art.shape[0])
    cells = cw * ch

    print(f"terminal      {cols} x {lines}")
    print(f"picture       {cw} x {ch}  =  {cells:,} cells")
    print()
    if cells >= 60000:
        print("That is plenty -- you are seeing close to the full detail.")
    elif cells >= 25000:
        print("Decent. Halving the font size again would still sharpen it noticeably.")
    else:
        factor = (60000 / max(cells, 1)) ** 0.5
        print(f"Low. Every character is one pixel of the image, so this is the")
        print(f"limit on detail -- not the code.")
        print()
        print(f"Shrink the terminal font (Cmd+- / Ctrl+-) and maximize the")
        print(f"window: about {factor:.1f}x smaller type reaches ~60,000 cells,")
        print(f"which is where the swirls and the village resolve properly.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=0.0,
                         help="0 = pick automatically from the terminal size")
    parser.add_argument("--duration", type=float, default=0.0,
                         help="seconds to run, 0 = forever (Ctrl+C to quit)")
    parser.add_argument("--info", action="store_true",
                         help="report how much detail this terminal size can hold")
    args = parser.parse_args()

    if args.info:
        print_density_report()
        return

    art = painting.load()
    img_h, img_w = art.shape[0], art.shape[1]

    cols, lines = terminal.get_size()
    canvas_w, canvas_h, x_off, y_off = fit_canvas(cols, lines, img_w, img_h)
    renderer = Renderer(canvas_w, canvas_h)
    screen = terminal.Screen(cols, lines, x_off, y_off,
                              truecolor=config.TRUECOLOR, step=config.COLOR_STEP)

    # Cost per frame scales with cell count, and the motion here is slow and
    # dreamy -- a big window does not need 20 fps. Pace to the size so a
    # detailed render never pins a core.
    fps = args.fps if args.fps > 0 else auto_fps(canvas_w * canvas_h)
    frame_time = 1.0 / fps

    def handle_exit(*_):
        terminal.restore()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    terminal.enter()
    start = time.time()

    try:
        while True:
            frame_start = time.time()
            t = frame_start - start

            new_size = terminal.get_size(fallback=(cols, lines))
            if new_size != (cols, lines):
                cols, lines = new_size
                canvas_w, canvas_h, x_off, y_off = fit_canvas(cols, lines, img_w, img_h)
                renderer = Renderer(canvas_w, canvas_h)
                screen = terminal.Screen(cols, lines, x_off, y_off,
                              truecolor=config.TRUECOLOR, step=config.COLOR_STEP)
                if args.fps <= 0:
                    frame_time = 1.0 / auto_fps(canvas_w * canvas_h)
                sys.stdout.write(terminal.CLEAR)

            chars, colors, visible = renderer.frame(t)
            out = screen.frame(chars, colors, visible)
            if out:
                sys.stdout.write(out)
                sys.stdout.flush()

            if args.duration and t >= args.duration:
                break

            elapsed = time.time() - frame_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
    finally:
        terminal.restore()


if __name__ == "__main__":
    main()
