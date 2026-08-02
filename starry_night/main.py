#!/usr/bin/env python3
"""Van Gogh's Starry Night, reconstructed live in the terminal from the real
painting: a swirling image warp drives the sky and stars, rendered as
colorful, constantly reshuffling Matrix-style glyphs. Ctrl+C to quit."""
import argparse
import signal
import sys
import time

from . import config, image_source, layout, stars, terminal
from .renderer import Renderer


def build_renderer(term_cols, term_lines, img):
    img_h, img_w = img.shape[0], img.shape[1]
    canvas_w, canvas_h, x_off, y_off = layout.fit_canvas(term_cols, term_lines, img_w, img_h)
    star_states = stars.build_star_states(config.STAR_MIN_SPEED, config.STAR_MAX_SPEED)
    renderer = Renderer(img, canvas_w, canvas_h, star_states)
    return renderer, x_off, y_off


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=18.0)
    parser.add_argument("--duration", type=float, default=0.0,
                         help="seconds to run, 0 = forever (Ctrl+C to quit)")
    args = parser.parse_args()

    try:
        img = image_source.load_source_array()
    except image_source.SourceUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    term_cols, term_lines = terminal.get_size()
    renderer, x_off, y_off = build_renderer(term_cols, term_lines, img)

    def handle_exit(*_):
        terminal.restore()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    terminal.enter()
    start = time.time()
    frame_time = 1.0 / args.fps

    try:
        while True:
            frame_start = time.time()
            t = frame_start - start

            new_cols, new_lines = terminal.get_size(fallback=(term_cols, term_lines))
            if (new_cols, new_lines) != (term_cols, term_lines):
                term_cols, term_lines = new_cols, new_lines
                renderer, x_off, y_off = build_renderer(term_cols, term_lines, img)

            chars, colors, visible = renderer.frame(t)
            out = terminal.render_frame_string(
                term_cols, term_lines, x_off, y_off, chars, colors, visible
            )
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
