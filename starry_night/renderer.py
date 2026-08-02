"""Combines the warped image sample, luminance, and glyph grid into a frame."""
import numpy as np

from . import config, warp
from .glyphs import GlyphGrid


def build_base_grid(canvas_w, canvas_h, img_w, img_h):
    cols = np.arange(canvas_w)
    rows = np.arange(canvas_h)
    x = (cols + 0.5) / canvas_w * img_w
    y = (rows + 0.5) / canvas_h * img_h
    return np.meshgrid(x, y)  # each shape (canvas_h, canvas_w)


def sample_image(img, Xs, Ys):
    xi = Xs.astype(np.int32)
    yi = Ys.astype(np.int32)
    return img[yi, xi]


def luminance(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0


class Renderer:
    def __init__(self, img, canvas_w, canvas_h, star_states, seed=None):
        self.img = img
        self.img_h, self.img_w = img.shape[0], img.shape[1]
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.star_states = star_states
        self.base_x, self.base_y = build_base_grid(canvas_w, canvas_h, self.img_w, self.img_h)
        self.glyphs = GlyphGrid(canvas_h, canvas_w, seed=seed)
        self.rng = np.random.default_rng(seed)

    def frame(self, t):
        xs, ys = warp.apply_all(self.base_x, self.base_y, t, self.img_w, self.img_h, self.star_states)
        colors = sample_image(self.img, xs, ys)
        lum = luminance(colors)

        self.glyphs.update(t)
        chars = self.glyphs.chars()

        visible = lum > config.MIN_BRIGHTNESS_FOR_GLYPH
        dim = lum <= 0.25
        skip_roll = self.rng.random(lum.shape)
        extra_skip = dim & (skip_roll < config.DARK_GLYPH_SKIP_PROB)
        visible = visible & ~extra_skip

        return chars, colors, visible
