"""Extracts Van Gogh's brushstroke directions from the painting itself.

This is what makes the render read as the painting rather than as noise:
instead of scattering random characters, we measure the local stroke
orientation at every point and later pick a glyph that visually points the
same way, so lines of text curve along the swirls.

Method: Sobel gradients -> structure tensor -> smooth the tensor ->
eigen-decompose. The dominant stroke direction is perpendicular to the
averaged gradient; coherence says how strongly directional the texture is
(high along a brushstroke, low inside a flat blob like a star's core).
"""
import numpy as np

from .imageops import box_blur


def _sobel(gray):
    padded = np.pad(gray, 1, mode="edge")
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    ky = kx.T
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    for dy in range(3):
        for dx in range(3):
            window = padded[dy:dy + gray.shape[0], dx:dx + gray.shape[1]]
            gx += kx[dy, dx] * window
            gy += ky[dy, dx] * window
    return gx, gy


def compute(rgb, smooth_radius=2):
    """Returns (angle, coherence) arrays shaped like the image.

    angle: stroke direction in radians, in [0, pi) -- orientation only, since
           a stroke has no head or tail.
    coherence: 0 (isotropic blob) .. 1 (crisp directional stroke).
    """
    gray = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0

    gx, gy = _sobel(gray)

    jxx = box_blur(gx * gx, smooth_radius)
    jyy = box_blur(gy * gy, smooth_radius)
    jxy = box_blur(gx * gy, smooth_radius)

    # Dominant gradient orientation; stroke runs perpendicular to it.
    gradient_angle = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    angle = np.mod(gradient_angle + np.pi / 2.0, np.pi)

    trace = jxx + jyy
    diff = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2)
    coherence = np.where(trace > 1e-9, diff / (trace + 1e-9), 0.0)

    return angle, np.clip(coherence, 0.0, 1.0)
