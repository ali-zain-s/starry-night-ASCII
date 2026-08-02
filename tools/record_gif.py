#!/usr/bin/env python3
"""DEV TOOL -- records the animation to an animated GIF for the README.

    python3 tools/record_gif.py docs/starry-night.gif

Requires Pillow (not needed at runtime).
"""
import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starry_night import inline, painting  # noqa: E402
from starry_night.renderer import Renderer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--columns", type=int, default=inline.SIXEL_COLUMNS)
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--fps", type=float, default=8.0)
    ap.add_argument("--width", type=int, default=1000,
                     help="pixel width of the GIF; the render is downscaled to it")
    ap.add_argument("--colors", type=int, default=128)
    args = ap.parse_args()

    art = painting.load()
    cols, rows = inline.grid_for(args.columns, art.shape[1], art.shape[0])
    renderer = Renderer(cols, rows, seed=1)
    image = inline.ImageRenderer(cols, rows)
    print(f"grid {cols}x{rows} = {cols * rows:,} characters")

    frames = []
    for i in range(args.frames):
        rgb = image.compose(*renderer.frame(i / args.fps))
        frame = Image.fromarray(rgb)
        if frame.width > args.width:
            height = round(frame.height * args.width / frame.width)
            frame = frame.resize((args.width, height), Image.LANCZOS)
        frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=args.colors))
        print(f"\r  frame {i + 1}/{args.frames}", end="", flush=True)
    print()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    frames[0].save(
        args.out,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / args.fps),
        loop=0,
        optimize=True,
    )
    size = os.path.getsize(args.out) / 1024 / 1024
    print(f"wrote {args.out}  ({frames[0].width}x{frames[0].height}, {size:.1f} MB)")


if __name__ == "__main__":
    main()
