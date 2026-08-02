"""Small numpy image helpers shared by the flow and tone stages."""
import numpy as np


def box_blur(a, radius):
    """Separable box blur via cumulative sums -- cheap and dependency-free."""
    if radius < 1:
        return a.astype(np.float64, copy=True)
    k = 2 * radius + 1
    a = a.astype(np.float64, copy=False)

    padded = np.pad(a, ((radius + 1, radius), (0, 0)), mode="edge")
    cs = np.cumsum(padded, axis=0)
    out = (cs[k:, :] - cs[:-k, :]) / k

    padded = np.pad(out, ((0, 0), (radius + 1, radius)), mode="edge")
    cs = np.cumsum(padded, axis=1)
    return (cs[:, k:] - cs[:, :-k]) / k


def unsharp(channel, radius, amount):
    """Local-contrast boost: pushes each pixel away from its neighbourhood
    mean, so Van Gogh's brushstroke ridges survive being flattened into
    one character per cell."""
    blurred = box_blur(channel, radius)
    return channel + amount * (channel - blurred)


def bloom(rgb, threshold, radius, strength):
    """Bleeds light out of the brightest paint into its surroundings.

    The stars and moon are small and would otherwise occupy only a couple
    of cells; spreading their glow makes them read as luminous discs and
    reveals the halo rings Van Gogh painted around them.
    """
    lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0
    excess = np.clip((lum - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0)
    lit = rgb * excess[..., None]
    spread = np.stack([box_blur(lit[..., c], radius) for c in range(3)], axis=-1)
    return rgb + spread * strength

