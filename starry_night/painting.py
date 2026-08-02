"""Decodes the embedded painting into a numpy RGB array.

No network, no image file: painting_data.py carries a palette plus a
zlib-compressed index array, generated once by tools/embed_painting.py.
"""
import base64
import zlib

import numpy as np

from . import painting_data

_cache = None


def load():
    """Returns the painting as a (H, W, 3) uint8 array. Cached."""
    global _cache
    if _cache is None:
        palette = np.frombuffer(
            base64.b64decode(painting_data.PALETTE_B64), dtype=np.uint8
        ).reshape(-1, 3)
        indices = np.frombuffer(
            zlib.decompress(base64.b64decode(painting_data.INDICES_B64)), dtype=np.uint8
        ).reshape(painting_data.HEIGHT, painting_data.WIDTH)
        _cache = palette[indices]
    return _cache
