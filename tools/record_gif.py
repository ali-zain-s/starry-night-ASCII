#!/usr/bin/env python3
"""DEV TOOL -- records the animation to an animated GIF for the README.

    python3 tools/record_gif.py docs/starry-night.gif

Draws the same characters the terminal draws, just rasterized here at a
fixed glyph size so the result is a file rather than a live screen.
Requires Pillow (not needed at runtime).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starry_night import glyphs, painting  # noqa: E402
from starry_night.renderer import Renderer  # noqa: E402

CELL_W, CELL_H, FONT_PX = 4, 7, 7

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/Library/Fonts/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]

# The composite is dim by nature: a glyph inks a fraction of its cell and
# antialiases toward black, so a faithful render measures around 0.15 mean
# luminance. This lifts only the pixels the glyphs cover -- the gaps stay
# black, which is what gives the lettering its bite.
GAIN, SATURATION = 2.0, 1.75


def load_font():
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, FONT_PX)
            except OSError:
                continue
    return ImageFont.load_default()


def build_atlas(font):
    chars = sorted({c for row in glyphs.DIRECTIONAL for c in row} | set(glyphs.ROUNDED))
    atlas = np.zeros((len(chars) + 1, CELL_H, CELL_W), np.float32)  # index 0 = blank
    for i, c in enumerate(chars):
        tile = Image.new("L", (CELL_W, CELL_H), 0)
        ImageDraw.Draw(tile).text((0, -1), c, font=font, fill=255)
        atlas[i + 1] = np.asarray(tile, np.float32) / 255.0
    lookup = np.zeros(0x110000, np.int32)
    for i, c in enumerate(chars):
        lookup[ord(c)] = i + 1
    return atlas, lookup


def compose(atlas, lookup, chars, colors, visible):
    codes = np.frombuffer(
        np.char.encode(chars.astype("<U1"), "utf-32-le").tobytes(), dtype=np.uint32
    ).reshape(chars.shape)
    idx = np.where(visible, lookup[codes], 0)
    rows, cols = chars.shape

    alpha = atlas[idx].transpose(0, 2, 1, 3).reshape(rows * CELL_H, cols * CELL_W)
    tinted = np.repeat(np.repeat(colors, CELL_H, axis=0), CELL_W, axis=1)
    lit = alpha[:, :, None] * tinted

    lum = (0.2126 * lit[..., 0] + 0.7152 * lit[..., 1] + 0.0722 * lit[..., 2])[..., None]
    return np.clip((lum + (lit - lum) * SATURATION) * GAIN, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--columns", type=int, default=273)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--fps", type=float, default=6.0)
    ap.add_argument("--width", type=int, default=760)
    ap.add_argument("--colors", type=int, default=64)
    args = ap.parse_args()

    art = painting.load()
    cols = args.columns
    rows = round(cols * (art.shape[0] / art.shape[1]) * (CELL_W / CELL_H))
    print(f"grid {cols}x{rows} = {cols * rows:,} characters")

    renderer = Renderer(cols, rows, seed=1)
    atlas, lookup = build_atlas(load_font())

    frames = []
    for i in range(args.frames):
        rgb = compose(atlas, lookup, *renderer.frame(i / args.fps))
        frame = Image.fromarray(rgb)
        if frame.width > args.width:
            height = round(frame.height * args.width / frame.width)
            frame = frame.resize((args.width, height), Image.LANCZOS)
        frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=args.colors))
        print(f"\r  frame {i + 1}/{args.frames}", end="", flush=True)
    print()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    frames[0].save(
        args.out, save_all=True, append_images=frames[1:],
        duration=round(1000 / args.fps), loop=0, optimize=True,
    )
    print(f"wrote {args.out}  ({os.path.getsize(args.out) / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
