#!/usr/bin/env python3
"""Van Gogh's Starry Night as living ASCII: the painting is embedded in the
source, its brushstroke directions steer the characters, and the sky swirls
while the stars turn. Runs fully offline. Ctrl+C to quit."""
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


def main():
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
    frame_time = 1.0 / auto_fps(canvas_w * canvas_h)

    # Nothing here writes to stdout: a signal can land in the middle of a
    # flush, and flushing again from the handler re-enters the same buffered
    # writer and raises. Ctrl+C is left to raise KeyboardInterrupt at a safe
    # point, SIGTERM just sets a flag, and the teardown happens in `finally`.
    stopping = False

    def request_stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)

    terminal.enter()
    start = time.time()

    try:
        while not stopping:
            frame_start = time.time()
            t = frame_start - start

            new_size = terminal.get_size(fallback=(cols, lines))
            if new_size != (cols, lines):
                cols, lines = new_size
                canvas_w, canvas_h, x_off, y_off = fit_canvas(cols, lines, img_w, img_h)
                renderer = Renderer(canvas_w, canvas_h)
                screen = terminal.Screen(cols, lines, x_off, y_off,
                              truecolor=config.TRUECOLOR, step=config.COLOR_STEP)
                frame_time = 1.0 / auto_fps(canvas_w * canvas_h)
                sys.stdout.write(terminal.CLEAR)

            chars, colors, visible = renderer.frame(t)
            out = screen.frame(chars, colors, visible)
            if out:
                sys.stdout.write(out)
                sys.stdout.flush()

            elapsed = time.time() - frame_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        terminal.restore()


if __name__ == "__main__":
    main()
