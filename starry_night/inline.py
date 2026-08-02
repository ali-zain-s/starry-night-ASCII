"""High-detail mode: draw the glyphs into an image and show it inline.

A terminal cell is the smallest thing text mode can address, so at a normal
font size the whole picture only gets ~7,000 of them and the detail simply
is not there to be had. Shrinking the font fixes it, but so does this: we
rasterize the same glyphs ourselves at whatever size we like and hand the
terminal one image per frame. The characters are still characters -- just
drawn at 4x7 pixels instead of your font's 14x28 -- so a normal window
holds roughly six times the detail with nothing to zoom.

This is the default path. It needs a terminal that understands the iTerm2
inline-image escape: iTerm2, VS Code's terminal, WezTerm, Konsole. If yours
does not, you will see the escape as stray text -- use --text instead.
"""
import base64
import io
import os

import numpy as np

from . import glyphs

CELL_W = 4
CELL_H = 7
FONT_PX = 7

# Columns of *glyphs* to draw, independent of how many cells the terminal
# has. This is the whole trick: the image lands on the same patch of screen
# either way, so more columns simply means smaller characters and more
# detail, with no zooming.
DEFAULT_COLUMNS = 273

# Sixel encodes in Python rather than a C JPEG encoder, so it runs coarser
# to stay near 7 fps.
SIXEL_COLUMNS = 273
SIXEL_COLORS = 64

# Final grade applied to the composed frame -- see encode().
GAIN = 2.0
SATURATION = 1.75

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/Library/Fonts/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def grid_for(columns, img_w, img_h):
    """Glyph grid matching the painting's aspect at the requested width."""
    cols = max(40, int(columns))
    rows = max(20, round(cols * (img_h / img_w) * (CELL_W / CELL_H)))
    return cols, rows


class ImageRenderer:
    """Rasterizes a character grid into one image per frame."""

    def __init__(self, cols, rows):
        from PIL import Image, ImageDraw, ImageFont  # local: optional dependency

        self._Image = Image
        self.cols = cols
        self.rows = rows

        font = None
        for path in _FONT_CANDIDATES:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, FONT_PX)
                    break
                except OSError:
                    continue
        if font is None:
            font = ImageFont.load_default()

        # One alpha mask per glyph, so a frame is a lookup plus a multiply
        # instead of tens of thousands of text-drawing calls.
        self.chars = sorted({c for row in glyphs.DIRECTIONAL for c in row} | set(glyphs.ROUNDED))
        self.index = {c: i for i, c in enumerate(self.chars)}
        self.atlas = np.zeros((len(self.chars) + 1, CELL_H, CELL_W), np.float32)
        for i, c in enumerate(self.chars):
            tile = Image.new("L", (CELL_W, CELL_H), 0)
            ImageDraw.Draw(tile).text((0, -1), c, font=font, fill=255)
            self.atlas[i + 1] = np.asarray(tile, np.float32) / 255.0
        # index 0 stays all-zero: the blank cell

        self._lookup = np.zeros(0x110000, np.int32)
        for c, i in self.index.items():
            self._lookup[ord(c)] = i + 1

    def compose(self, chars, colors, visible):
        """Rasterize the character grid into an RGB frame."""
        codes = np.frombuffer(
            np.char.encode(chars.astype("<U1"), "utf-32-le").tobytes(), dtype=np.uint32
        ).reshape(chars.shape)
        idx = np.where(visible, self._lookup[codes], 0)

        alpha = self.atlas[idx].transpose(0, 2, 1, 3).reshape(
            self.rows * CELL_H, self.cols * CELL_W
        )
        tinted = np.repeat(np.repeat(colors, CELL_H, axis=0), CELL_W, axis=1)
        lit = alpha[:, :, None] * tinted

        # Grade the composed frame. A glyph inks a fraction of its cell and
        # its edges are antialiased toward the black background, so a
        # faithful composite measures out at 0.15 mean luminance with 14/255
        # saturation -- half the pixels are literally black and the colour is
        # washed to grey. Lifting here only touches pixels the glyphs
        # actually cover; the gaps stay black, which is what gives the
        # lettering its bite.
        lum = (0.2126 * lit[..., 0] + 0.7152 * lit[..., 1] + 0.0722 * lit[..., 2])[..., None]
        graded = (lum + (lit - lum) * SATURATION) * GAIN
        frame = np.clip(graded, 0, 255).astype(np.uint8)

        return frame

    def encode(self, chars, colors, visible):
        """Compose and JPEG-encode, for the iTerm2 inline-image escape."""
        frame = self.compose(chars, colors, visible)
        buf = io.BytesIO()
        self._Image.fromarray(frame).save(buf, "JPEG", quality=72, subsampling=2)
        return buf.getvalue(), frame.shape[1], frame.shape[0]


def emit(payload, term_cols, term_rows):
    """iTerm2 inline-image escape, stretched to fill the terminal window."""
    b64 = base64.b64encode(payload).decode("ascii")
    return (
        "\x1b[H"
        f"\x1b]1337;File=inline=1;size={len(payload)};"
        f"width={term_cols};height={term_rows};preserveAspectRatio=0:{b64}\a"
    )
