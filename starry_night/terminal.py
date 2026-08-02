"""Terminal output.

Repainting every cell every frame costs ~160 KB (a color escape on nearly
all of them); at 20 fps that is 3.2 MB/s for the terminal emulator to
parse, which is enough to pin a CPU core. Two things fix it:

  * snapping colors to a coarse step, so drift too small to see stops
    marking cells dirty;
  * differential redraw -- only ~15% of cells then actually change
    between frames, so we repaint just those runs and leave the rest.

Together that is a ~4.4x cut in bytes written (0.74 MB/s).

A 256-color mode is also here and is cheaper still, but it is not the
default: that palette's cube jumps 0 -> 95 at the dark end, so Van Gogh's
near-black cypress falls back to the achromatic gray ramp and renders as
literal grey, throwing its green away.
"""
import shutil
import sys

import numpy as np

CSI = "\x1b["
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
ALT_SCREEN_ON = CSI + "?1049h"
ALT_SCREEN_OFF = CSI + "?1049l"
CLEAR = CSI + "2J"
HOME = CSI + "H"
RESET = CSI + "0m"

_CUBE_LEVELS = np.array([0, 95, 135, 175, 215, 255], dtype=np.int16)
_GRAY_LEVELS = np.array([8 + 10 * i for i in range(24)], dtype=np.int16)

# value 0..255 -> nearest index into the 6-level color cube
_CUBE_LUT = np.abs(np.arange(256, dtype=np.int16)[:, None] - _CUBE_LEVELS).argmin(1).astype(np.uint8)
_GRAY_LUT = np.abs(np.arange(256, dtype=np.int16)[:, None] - _GRAY_LEVELS).argmin(1).astype(np.uint8)

# Pre-rendered SGR strings for all 256 palette entries.
_FG256 = [f"{CSI}38;5;{i}m" for i in range(256)]


def to_256(rgb):
    """(H, W, 3) uint8 -> (H, W) uint8 of xterm-256 palette indices.

    Picks whichever is closer: the 6x6x6 color cube or the 24-step gray
    ramp. The gray ramp matters here because so much of the painting is
    desaturated dark blue-grey.
    """
    rgb = rgb.astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    ci = _CUBE_LUT[r], _CUBE_LUT[g], _CUBE_LUT[b]
    cube_rgb = _CUBE_LEVELS[np.stack(ci, -1)]
    cube_err = np.abs(cube_rgb - rgb).sum(-1)
    cube_code = 16 + ci[0].astype(np.int16) * 36 + ci[1].astype(np.int16) * 6 + ci[2].astype(np.int16)

    lum = ((r * 2 + g * 5 + b) // 8).astype(np.uint8)
    gi = _GRAY_LUT[lum]
    gray_rgb = _GRAY_LEVELS[gi][..., None]
    gray_err = np.abs(gray_rgb - rgb).sum(-1)
    gray_code = 232 + gi.astype(np.int16)

    return np.where(gray_err < cube_err, gray_code, cube_code).astype(np.uint8)


def get_size(fallback=(120, 45)):
    size = shutil.get_terminal_size(fallback=fallback)
    return size.columns, size.lines


def enter():
    sys.stdout.write(ALT_SCREEN_ON + HIDE_CURSOR + CLEAR)
    sys.stdout.flush()


def restore():
    sys.stdout.write(RESET + SHOW_CURSOR + ALT_SCREEN_OFF)
    sys.stdout.flush()


class Screen:
    """Tracks what is on screen so each frame only repaints what moved.

    Truecolor is the default despite costing more bytes than the 256-color
    cube: that cube's levels jump 0 -> 95 at the dark end, so Van Gogh's
    near-black cypress falls back to the achromatic gray ramp and renders
    as literal grey, throwing its green away. Colors are snapped to a
    coarse step instead, which keeps full hue precision while stopping
    sub-perceptual drift from marking cells dirty every frame.
    """

    def __init__(self, cols, lines, x_offset, y_offset, truecolor=True, step=16):
        self.cols = cols
        self.lines = lines
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.truecolor = truecolor
        self.step = max(1, step)
        self.prev_chars = None
        self.prev_codes = None
        self.prev_visible = None
        self._esc_cache = {}

    def _escape(self, key):
        cached = self._esc_cache.get(key)
        if cached is None:
            if self.truecolor:
                r, g, b = key
                cached = f"{CSI}38;2;{r};{g};{b}m"
            else:
                cached = _FG256[key]
            self._esc_cache[key] = cached
        return cached

    def frame(self, chars, colors, visible):
        # Visibility is tracked as its own plane rather than folded into the
        # color: a dark-but-visible cell can quantize to pure black, and
        # using black as the "blank" sentinel silently swallowed those
        # characters.
        if self.truecolor:
            q = (colors.astype(np.int16) // self.step) * self.step
            codes = np.clip(q, 0, 255).astype(np.uint8)
        else:
            codes = to_256(colors)
        cells = np.where(visible, chars, " ")
        vis = visible.astype(bool)

        if self.prev_chars is None or self.prev_chars.shape != cells.shape:
            return self._full(cells, codes, vis)
        return self._delta(cells, codes, vis)

    def _key(self, codes, vis, row, col):
        """Color key for a cell, or None if it should render blank."""
        if not vis[row, col]:
            return None
        if self.truecolor:
            r, g, b = codes[row, col]
            return (int(r), int(g), int(b))
        return int(codes[row, col])

    def _full(self, cells, codes, vis):
        out = [RESET, HOME]
        h, w = cells.shape
        pad = " " * self.x_offset
        last = None
        for row in range(h):
            out.append(f"{CSI}{row + self.y_offset + 1};1H")
            if pad:
                out.append(RESET)
                last = None
                out.append(pad)
            trow = cells[row]
            for col in range(w):
                key = self._key(codes, vis, row, col)
                if key is None:
                    if last is not None:
                        out.append(RESET)
                        last = None
                    out.append(" ")
                else:
                    if key != last:
                        out.append(self._escape(key))
                        last = key
                    out.append(trow[col])
        out.append(RESET)
        self._remember(cells, codes, vis)
        return "".join(out)

    def _delta(self, cells, codes, vis):
        color_changed = (codes != self.prev_codes)
        if self.truecolor:
            color_changed = color_changed.any(axis=-1)
        changed = (cells != self.prev_chars) | color_changed | (vis != self.prev_visible)
        rows = np.flatnonzero(changed.any(axis=1))
        if rows.size == 0:
            return ""

        out = []
        last = None
        truecolor = self.truecolor
        cache = self._esc_cache
        # Python ints beat numpy scalars in the inner loop below.
        codes_list = codes.tolist()
        cells_list = cells.tolist()
        vis_list = vis.tolist()

        for row in rows:
            row_mask = changed[row]
            cols = np.flatnonzero(row_mask)
            trow = cells_list[row]
            crow = codes_list[row]
            vrow = vis_list[row]

            # Walk the changed columns, coalescing near-adjacent ones into a
            # single run so we pay for one cursor move instead of many.
            start = cols[0]
            prev = cols[0]
            for col in list(cols[1:]) + [None]:
                if col is not None and col - prev <= 3:
                    prev = col
                    continue

                out.append(f"{CSI}{row + self.y_offset + 1};{start + self.x_offset + 1}H")
                # Inlined rather than calling _key/_escape per cell: at high
                # density this loop runs tens of thousands of times a frame
                # and the call overhead alone was measurable.
                for c in range(start, prev + 1):
                    if not vrow[c]:
                        if last is not None:
                            out.append(RESET)
                            last = None
                        out.append(" ")
                        continue
                    key = tuple(crow[c]) if truecolor else crow[c]
                    if key != last:
                        esc = cache.get(key)
                        if esc is None:
                            esc = (f"{CSI}38;2;{key[0]};{key[1]};{key[2]}m"
                                   if truecolor else _FG256[key])
                            cache[key] = esc
                        out.append(esc)
                        last = key
                    out.append(trow[c])

                if col is not None:
                    start = prev = col

        out.append(RESET)
        self._remember(cells, codes, vis)
        return "".join(out)

    def _remember(self, cells, codes, vis):
        self.prev_chars = cells.copy()
        self.prev_codes = codes.copy()
        self.prev_visible = vis.copy()
