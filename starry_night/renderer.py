"""Builds one frame: warp -> sample -> tone/flow -> glyphs."""
import numpy as np

from . import animate, config, flow, glyphs, imageops, painting


def fit_canvas(term_cols, term_lines, img_w, img_h):
    """Largest character grid matching the painting's aspect, letterboxed."""
    canvas_w = term_cols
    canvas_h = round(canvas_w * config.CELL_ASPECT * img_h / img_w)

    if canvas_h > term_lines:
        canvas_h = term_lines
        canvas_w = min(term_cols, round(canvas_h * img_w / (img_h * config.CELL_ASPECT)))

    canvas_w = max(1, canvas_w)
    canvas_h = max(1, canvas_h)
    return canvas_w, canvas_h, (term_cols - canvas_w) // 2, (term_lines - canvas_h) // 2


def sample_bilinear(img, xs, ys):
    h, w = img.shape[0], img.shape[1]
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    fx = (xs - x0)[..., None]
    fy = (ys - y0)[..., None]

    x0c = np.clip(x0, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1)
    x1c = np.clip(x0 + 1, 0, w - 1)
    y1c = np.clip(y0 + 1, 0, h - 1)

    top = img[y0c, x0c] * (1.0 - fx) + img[y0c, x1c] * fx
    bot = img[y1c, x0c] * (1.0 - fx) + img[y1c, x1c] * fx
    return top * (1.0 - fy) + bot * fy


def sample_nearest(a, xs, ys):
    h, w = a.shape[0], a.shape[1]
    xi = np.clip(xs.astype(np.int32), 0, w - 1)
    yi = np.clip(ys.astype(np.int32), 0, h - 1)
    return a[yi, xi]


class Renderer:
    def __init__(self, canvas_w, canvas_h, seed=None):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h

        rgb = painting.load()
        self.img_h, self.img_w = rgb.shape[0], rgb.shape[1]

        # All of this is precomputed once on the source, so it costs nothing
        # per frame. One character per cell throws away the paint's fine
        # relief, so the brushstroke ridges are boosted first -- that is what
        # keeps the swirls reading as lines instead of a flat blue wash.
        work = np.stack(
            [
                imageops.unsharp(rgb[..., c].astype(np.float64),
                                  config.UNSHARP_RADIUS, config.UNSHARP_AMOUNT)
                for c in range(3)
            ],
            axis=-1,
        )
        work = imageops.bloom(
            np.clip(work, 0, 255),
            config.BLOOM_THRESHOLD, config.BLOOM_RADIUS, config.BLOOM_STRENGTH,
        )
        self.img = np.clip(work, 0, 255)

        angle, coherence = flow.compute(rgb, smooth_radius=config.FLOW_SMOOTH_RADIUS)
        self.flow_angle = angle
        self.flow_coherence = coherence
        self.spin_centers = animate.find_spin_centers(rgb)

        cols = (np.arange(canvas_w) + 0.5) / canvas_w * self.img_w
        rows = (np.arange(canvas_h) + 0.5) / canvas_h * self.img_h
        self.base_x, self.base_y = np.meshgrid(cols, rows)

        self.picker = glyphs.GlyphPicker(canvas_h, canvas_w, seed=seed)

    def frame(self, t):
        xs, ys = animate.apply(
            self.base_x, self.base_y, t, self.img_w, self.img_h, self.spin_centers
        )

        rgb = sample_bilinear(self.img, xs, ys)
        raw_lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0

        angle = sample_nearest(self.flow_angle, xs, ys)
        coherence = sample_nearest(self.flow_coherence, xs, ys)

        orient = glyphs.quantize_orientation(angle)
        directional = coherence > config.COHERENCE_THRESHOLD

        self.picker.update(t)
        chars, coverage = self.picker.pick(orient, directional, raw_lum)

        # The glyph inked `coverage` of the cell, so the color supplies the
        # rest of the tone; ink x color then tracks the painting and the
        # lettering dissolves into the image instead of sitting on top of it.
        #
        # The target is the painting scaled into the range ink can actually
        # reach. Even a solid '0' fills only ~15% of its cell, so absolute
        # brightness is capped there -- asking for the painting's true
        # luminance just pins every cell at that ceiling and flattens the
        # picture. Scaling instead keeps the tone *relative*, which is what
        # the eye adapts to.
        want = (raw_lum ** config.TONE_GAMMA) * glyphs.MAX_COVERAGE * config.EXPOSURE
        gain = np.clip(want / np.maximum(coverage, 1e-6), 0.0, config.MAX_GAIN)

        hue = rgb / np.maximum(raw_lum[..., None] * 255.0, 1e-6)
        colors = np.clip(hue * gain[..., None] * 255.0, 0, 255).astype(np.uint8)

        visible = raw_lum > config.BLACK_FLOOR
        return chars, colors, visible
