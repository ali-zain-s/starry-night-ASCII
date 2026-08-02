"""Time-varying inverse warp: which source pixel each cell samples at time t.

Every angle is a direct function of t rather than something accumulated
frame to frame, so sampling always happens against the pristine painting --
the motion can run for hours without drifting or smearing.
"""
import numpy as np

from . import config


def sky_mask(y_norm):
    """1 in the sky, easing to 0 over the horizon so the village stays still."""
    t = (config.SKY_FRACTION - y_norm) / config.GROUND_BLEND
    return np.clip(t, 0.0, 1.0)


def twirl(x, y, cx, cy, radius, angle):
    dx = x - cx
    dy = y - cy
    r = np.sqrt(dx * dx + dy * dy)
    falloff = np.clip(1.0 - r / radius, 0.0, 1.0) ** 1.5
    a = falloff * angle
    cos_a = np.cos(a)
    sin_a = np.sin(a)
    return cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a


def apply(x, y, t, img_w, img_h, spin_centers):
    """x, y: float arrays of source pixel coords. Returns warped coords."""
    mask = sky_mask(y / img_h)

    xs = x.astype(np.float64, copy=True)
    ys = y.astype(np.float64, copy=True)

    wavelength = config.CURRENT_WAVELENGTH * img_w
    phase = 2 * np.pi * xs / wavelength + t * config.CURRENT_SPEED * 2 * np.pi
    ys = ys + config.CURRENT_AMPLITUDE * img_h * np.sin(phase) * mask

    for nx, ny, radius_frac, strength, speed in config.SWIRLS:
        cx, cy = nx * img_w, ny * img_h
        radius = radius_frac * img_w
        angle = strength * np.sin(t * speed)
        tx, ty = twirl(xs, ys, cx, cy, radius, angle)
        xs = xs + (tx - xs) * mask
        ys = ys + (ty - ys) * mask

    radius = config.STAR_SPIN_RADIUS * img_w
    for cx, cy, speed in spin_centers:
        angle = config.STAR_SPIN_STRENGTH * np.sin(t * speed)
        tx, ty = twirl(xs, ys, cx, cy, radius, angle)
        xs = xs + (tx - xs) * mask
        ys = ys + (ty - ys) * mask

    np.clip(xs, 0, img_w - 1.001, out=xs)
    np.clip(ys, 0, img_h - 1.001, out=ys)
    return xs, ys


def find_spin_centers(rgb, seed=5):
    """Locates the painting's bright yellow discs -- the stars and moon --
    so each one can rotate in place. Found from the pixels themselves, so
    they stay correct if the embedded art is ever regenerated."""
    rng = np.random.default_rng(seed)
    h, w = rgb.shape[0], rgb.shape[1]
    r, g, b = rgb[..., 0].astype(float), rgb[..., 1].astype(float), rgb[..., 2].astype(float)
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    yellow = np.clip((r + g) / 2.0 - b, 0, None) / 255.0
    score = lum * (0.35 + yellow)
    score[int(h * 0.72):, :] = 0.0   # ignore village lights

    # Greedy peak picking with disc suppression. The suppression radius must
    # exceed the moon's halo: with a small radius the moon's own glow yields
    # a dozen near-identical peaks and fills every slot, leaving the real
    # stars across the rest of the sky with no spin at all.
    lo, hi = config.STAR_SPIN_SPEED
    radius = max(4.0, w * config.SPIN_SUPPRESS_RADIUS)
    yy, xx = np.mgrid[0:h, 0:w]

    centers = []
    work = score.copy()
    for _ in range(config.SPIN_MAX_CENTERS):
        iy, ix = np.unravel_index(np.argmax(work), work.shape)
        if work[iy, ix] < config.SPIN_MIN_SCORE:
            break
        speed = rng.uniform(lo, hi) * rng.choice((-1.0, 1.0))
        centers.append((float(ix), float(iy), float(speed)))
        work[(xx - ix) ** 2 + (yy - iy) ** 2 <= radius ** 2] = 0.0

    return centers
