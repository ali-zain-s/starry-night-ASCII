#!/usr/bin/env python3
"""DEV TOOL -- renders one frame to a PNG so the output can be inspected
outside a terminal. Requires Pillow (not needed at runtime).

    python3 tools/preview.py out.png --cols 200 --lines 74 --time 3
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starry_night import painting  # noqa: E402
from starry_night.renderer import Renderer, fit_canvas  # noqa: E402

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/Library/Fonts/Courier New.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--cols", type=int, default=200)
    ap.add_argument("--lines", type=int, default=74)
    ap.add_argument("--time", type=float, default=0.0)
    ap.add_argument("--cell", type=int, default=10, help="cell height in px")
    args = ap.parse_args()

    art = painting.load()
    canvas_w, canvas_h, _, _ = fit_canvas(args.cols, args.lines, art.shape[1], art.shape[0])
    renderer = Renderer(canvas_w, canvas_h, seed=3)
    chars, colors, visible = renderer.frame(args.time)

    ch = args.cell
    cw = max(1, round(ch * 0.5))
    font = load_font(ch)

    img = Image.new("RGB", (canvas_w * cw, canvas_h * ch), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    for row in range(canvas_h):
        for col in range(canvas_w):
            if not visible[row, col]:
                continue
            c = chars[row, col]
            if c == " ":
                continue
            rgb = tuple(int(v) for v in colors[row, col])
            draw.text((col * cw, row * ch), c, font=font, fill=rgb)

    img.save(args.out)
    print(f"wrote {args.out}  ({canvas_w}x{canvas_h} cells -> {img.width}x{img.height}px)")


if __name__ == "__main__":
    main()
