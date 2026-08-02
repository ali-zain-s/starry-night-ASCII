"""Chooses a character per cell, and reports how much ink it lays down.

The important idea here is that a glyph encodes *direction only*, never
brightness. Earlier versions picked heavy characters for bright cells and
faint ones for dark cells while *also* coloring those cells by brightness.
That encodes tone twice -- perceived output is roughly ink x color, i.e.
tone squared -- which exaggerates contrast and makes the lettering read as
a texture sitting on top of the picture instead of dissolving into it.

So: orientation picks the character, and `coverage()` reports the fraction
of the cell that character inks (measured from the actual font, see
tools/measure_coverage.py). The renderer divides the color by that
coverage, so every cell ends up with the same ink-times-color product the
painting has at that point. The glyph layer becomes a flat texture the eye
stops noticing, and the color layer carries the image.
"""
import numpy as np

from . import config

# orientation index: 0 = horizontal, 1 = "/", 2 = vertical, 3 = "\"
#
# Each ladder runs light -> heavy. The light rungs are orientation-specific
# so strokes keep their direction; the heavy rungs are the round digits,
# shared by every direction, because the only bright regions are the star
# and moon discs where the paint has no direction anyway.
DIRECTIONAL = [
    ["`", ".", "-", "~", "=", "c", "o", "O", "0"],
    ["`", "'", "/", "v", "y", "s", "o", "O", "0"],
    ["`", "!", "|", "l", "i", "1", "I", "o", "0"],
    ["`", "'", "\\", "v", "y", "s", "o", "O", "0"],
]

# Where the paint has no clear direction: star cores, flat sky.
ROUNDED = ["`", ".", ",", "c", "o", "e", "a", "6", "O", "0"]

# Optional heavy rungs. A letter inks at most ~15% of its cell, which is a
# hard ceiling on brightness; the shade blocks reach 49% and lift it 3.2x.
# Off by default: measured against this painting they wash the deep
# ultramarine toward grey and flatten the brushstroke texture, because a
# shade block is a uniform dither with no direction in it. Worth turning on
# for a brighter, blockier read -- see config.SHADE_BLOCKS.
SHADE_RUNGS = ["▒", "▓", "█"]

if config.SHADE_BLOCKS:
    DIRECTIONAL = [row + SHADE_RUNGS for row in DIRECTIONAL]
    ROUNDED = ROUNDED + SHADE_RUNGS

# Ink coverage per character, measured from Menlo at 40px. Values are the
# mean pixel intensity of the rendered glyph, i.e. the fraction of the cell
# it fills. Proportions hold across normal monospace faces.
COVERAGE = {
    "`": 0.0116, "'": 0.0253, ".": 0.0265, "-": 0.0299, "_": 0.0345,
    ",": 0.0365, ":": 0.0410, "~": 0.0467, "!": 0.0469, "^": 0.0488,
    ";": 0.0542, "+": 0.0582, "\\": 0.0590, "/": 0.0590, "=": 0.0595,
    "|": 0.0647, ">": 0.0649, "<": 0.0650, "c": 0.0693, "l": 0.0698,
    "v": 0.0747, "i": 0.0753, "t": 0.0778, "f": 0.0792, "s": 0.0817,
    "T": 0.0817, "1": 0.0855, "I": 0.0905, "y": 0.0914, "o": 0.0953,
    "e": 0.0989, "3": 0.0990, "5": 0.1007, "S": 0.1040, "a": 0.1044,
    "9": 0.1222, "6": 0.1222, "O": 0.1240, "0": 0.1509, " ": 0.0,
    # Shade blocks. A letter can only ink about 15% of its cell, which caps
    # how bright the picture can ever get; these reach 49%, so the stars and
    # moon finally have somewhere to go. They sit at the top of each ladder,
    # used only by the brightest few percent of cells -- the lettering still
    # carries everything else.
    "░": 0.0897, "▒": 0.2444, "▓": 0.3946, "█": 0.4901,
}

_LADDERS = [np.array(row) for row in DIRECTIONAL] + [np.array(ROUNDED)]
_LADDER_COV = [np.array([COVERAGE[c] for c in row]) for row in _LADDERS]
ROUND_LADDER = len(_LADDERS) - 1

MAX_COVERAGE = float(max(cov.max() for cov in _LADDER_COV))


def _rung_for(cov_array, target):
    """Index of the rung whose ink coverage is nearest `target`."""
    idx = np.searchsorted(cov_array, target)
    idx = np.clip(idx, 1, len(cov_array) - 1)
    lo = cov_array[idx - 1]
    hi = cov_array[idx]
    return np.where(np.abs(target - lo) <= np.abs(hi - target), idx - 1, idx)


class GlyphPicker:
    """Per-cell variation with a slow, independent re-roll -- the Matrix
    shimmer -- but only ever *within* the set the orientation already
    chose, so the flicker never disturbs the picture."""

    def __init__(self, rows, cols, seed=None):
        self._rng = np.random.default_rng(seed)
        self.slot = self._rng.integers(0, 4, size=(rows, cols))
        self.next_change = self._rng.uniform(
            config.GLYPH_MIN_INTERVAL, config.GLYPH_MAX_INTERVAL, size=(rows, cols)
        )

    def update(self, t):
        due = self.next_change <= t
        n = int(due.sum())
        if n:
            self.slot[due] = self._rng.integers(0, 4, size=n)
            self.next_change[due] = t + self._rng.uniform(
                config.GLYPH_MIN_INTERVAL, config.GLYPH_MAX_INTERVAL, size=n
            )

    def pick(self, orient_idx, directional, lum):
        """Choose a glyph per cell -> (chars, coverage).

        Ink coverage carries part of the tonal range and the color carries
        the rest. Letting coverage do none of the work caps the picture at
        ~7% brightness (a glyph inks only a sliver of its cell); letting it
        do all of the work is classic ASCII art and throws away color.
        Splitting keeps both.

        The target is spread across each ladder's own span. Scaling by
        MAX_COVERAGE instead pins every cell brighter than ~0.15 to the top
        rung -- which put 'O' or '0' in 92% of cells, so the picture lost
        all glyph structure and the lettering shouted over it.
        """
        lum = np.clip(lum, 0.0, 1.0)

        chars = np.empty(lum.shape, dtype="<U1")
        coverage = np.empty(lum.shape, dtype=np.float64)

        for ladder in range(len(_LADDERS)):
            mask = (orient_idx == ladder) & directional if ladder != ROUND_LADDER else ~directional
            if not mask.any():
                continue
            cov = _LADDER_COV[ladder]
            target = cov[0] + (cov[-1] - cov[0]) * lum[mask] ** config.INK_EXPONENT
            rung = _rung_for(cov, target)
            # A slow per-cell wobble of one rung is the Matrix shimmer; it
            # never moves far enough to disturb the tone.
            rung = np.clip(rung + (self.slot[mask] % 3) - 1, 0, len(cov) - 1)
            chars[mask] = _LADDERS[ladder][rung]
            coverage[mask] = cov[rung]

        return chars, coverage


def quantize_orientation(angle):
    """Stroke angle (0..pi) -> 0=horizontal, 1='/', 2=vertical, 3='\\'.

    Screen y points down, so an angle rising to the right in math
    coordinates draws as '/'.
    """
    sector = np.floor_divide(np.mod(angle + np.pi / 8.0, np.pi), np.pi / 4.0)
    return np.clip(sector, 0, 3).astype(np.int8)
