#!/usr/bin/env python3
"""DEV TOOL -- measures how much of its cell each glyph inks.

The renderer needs this to know how much tone a character already
supplies, so the color can supply exactly the rest. Run it if you change
the glyph set, and paste the result into glyphs.COVERAGE.

    python3 tools/measure_coverage.py

Requires Pillow (not needed at runtime).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starry_night import glyphs  # noqa: E402

FONT = "/System/Library/Fonts/Menlo.ttc"
SIZE = 40


def main():
    font = ImageFont.truetype(FONT, SIZE)
    chars = sorted({c for row in glyphs.DIRECTIONAL for c in row} | set(glyphs.ROUNDED))
    print("COVERAGE = {")
    for c in chars:
        img = Image.new("L", (SIZE, int(SIZE * 1.3)), 0)
        ImageDraw.Draw(img).text((SIZE // 6, 2), c, font=font, fill=255)
        print(f"    {c!r}: {np.asarray(img).mean() / 255:.4f},")
    print("}")


if __name__ == "__main__":
    main()
