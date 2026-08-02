"""Per-cell Matrix-style glyph cycling: each cell re-rolls its character on
its own randomized timer, independent of its neighbours."""
import numpy as np

from . import config

_CHARS = np.array(list(config.GLYPH_CHARS))


class GlyphGrid:
    def __init__(self, rows, cols, seed=None):
        self.rows = rows
        self.cols = cols
        self._rng = np.random.default_rng(seed)
        self.char_idx = self._rng.integers(0, len(_CHARS), size=(rows, cols))
        self.next_change = self._rng.uniform(
            0.0, config.GLYPH_MAX_INTERVAL, size=(rows, cols)
        )

    def update(self, t):
        mask = self.next_change <= t
        n_changed = int(mask.sum())
        if n_changed:
            self.char_idx[mask] = self._rng.integers(0, len(_CHARS), size=n_changed)
            self.next_change[mask] = t + self._rng.uniform(
                config.GLYPH_MIN_INTERVAL, config.GLYPH_MAX_INTERVAL, size=n_changed
            )

    def chars(self):
        return _CHARS[self.char_idx]
