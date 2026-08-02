#!/usr/bin/env python3
"""Van Gogh's Starry Night as living ASCII: the painting is embedded in the
source, its brushstroke directions steer the characters, and the sky swirls
while the stars turn. Runs fully offline. Ctrl+C to quit."""
import argparse
import signal
import sys
import time

from . import config, inline, painting, sixel, terminal
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


def run_image_mode(args, art, img_w, img_h):
    """Rasterize the glyphs ourselves and hand the terminal one image per
    frame, so the character size stops being the terminal's decision."""
    use_sixel = args.protocol == "sixel"
    # Sixel costs more per frame than a JPEG, so it starts a little coarser.
    columns = args.columns or (inline.SIXEL_COLUMNS if use_sixel else inline.DEFAULT_COLUMNS)
    cols, rows = inline.grid_for(columns, img_w, img_h)
    renderer = Renderer(cols, rows)
    image = inline.ImageRenderer(cols, rows)
    # The sky drifts slowly; 6 fps is indistinguishable from 20 here and
    # costs a third as much to push through the terminal.
    fps = args.fps if args.fps > 0 else 6.0

    def handle_exit(*_):
        terminal.restore()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    terminal.enter()
    start = time.time()
    frame_time = 1.0 / fps
    try:
        while True:
            frame_start = time.time()
            t = frame_start - start
            term_cols, term_lines = terminal.get_size()

            chars, colors, visible = renderer.frame(t)
            if use_sixel:
                frame = image.compose(chars, colors, visible)
                out = "\x1b[H" + sixel.encode(frame, max_colors=inline.SIXEL_COLORS)
            else:
                payload, _, _ = image.encode(chars, colors, visible)
                out = inline.emit(payload, term_cols, term_lines)
            sys.stdout.write(out)
            sys.stdout.flush()

            if args.duration and t >= args.duration:
                break
            elapsed = time.time() - frame_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
    finally:
        terminal.restore()


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
        print(f"This is what --text mode is limited to. The default mode draws")
        print(f"the glyphs as an image instead and is not bound by it:")
        print(f"~30,000 cells here, roughly {30000 / max(cells, 1):.0f}x more.")
        print()
        print(f"To get there in --text mode, shrink the terminal font")
        print(f"(Cmd+- / Ctrl+-) and maximize the window: about {factor:.1f}x smaller")
        print(f"type reaches ~60,000 cells.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=0.0,
                         help="0 = pick automatically from the terminal size")
    parser.add_argument("--duration", type=float, default=0.0,
                         help="seconds to run, 0 = forever (Ctrl+C to quit)")
    parser.add_argument("--image", action="store_true",
                         help="draw the glyphs as an inline image: ~6x the detail, "
                              "but needs a terminal with image support turned on "
                              "(in VS Code: settings > terminal.integrated.enableImages)")
    parser.add_argument("--columns", type=int, default=0,
                         help="glyph columns in image mode; more = finer detail")
    parser.add_argument("--protocol", choices=("sixel", "iterm"), default="sixel",
                         help="how to hand the image to the terminal. sixel works "
                              "in VS Code and iTerm2; iterm is cheaper but iTerm2 only")
    parser.add_argument("--info", action="store_true",
                         help="report how much detail this terminal size can hold")
    args = parser.parse_args()

    if args.info:
        print_density_report()
        return

    art = painting.load()
    img_h, img_w = art.shape[0], art.shape[1]

    # Text is the default because it works everywhere. Image mode is far
    # more detailed but a terminal that does not support inline images just
    # swallows the escape and shows a blank screen, with no error to explain
    # it -- a worse outcome than a coarser picture. Opt in with --image.
    #
    # The dependency is probed here rather than around the render loop, so a
    # stray ImportError from deep inside a running animation can never be
    # mistaken for a missing Pillow and silently swap modes mid-flight.
    if args.image:
        try:
            import PIL  # noqa: F401
        except ImportError:
            print("image mode needs Pillow (python3 -m pip install pillow); "
                  "falling back to text", file=sys.stderr)
        else:
            run_image_mode(args, art, img_w, img_h)
            return

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
