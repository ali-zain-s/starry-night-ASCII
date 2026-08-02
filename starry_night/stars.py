"""Normalized (x, y) positions of the painting's stars and moon.

Coordinates are fractions of image width/height, found by scanning the
actual downloaded painting for bright, yellow, sky-region peaks (see
scripts/find_stars.py) rather than guessed by eye -- so the spiral warp
lands exactly on the real stars in whatever source image is in use.
"""
import random

from . import config

MOON_POSITION = (0.906, 0.159)
MOON_TWIRL_RADIUS_MULT = 2.4  # the moon's halo is much bigger than a star's

STAR_POSITIONS = [
    (0.234, 0.170),
    (0.133, 0.479),
    (0.109, 0.028),
    (0.353, 0.517),
    (0.705, 0.229),
    (0.412, 0.069),
    (0.609, 0.091),
    (0.345, 0.034),
    (0.956, 0.391),
]


def build_star_states(min_speed, max_speed, seed=11):
    rng = random.Random(seed)
    states = []
    for nx, ny in STAR_POSITIONS:
        states.append({
            "nx": nx,
            "ny": ny,
            "radius_frac": config.STAR_TWIRL_RADIUS,
            "speed": rng.uniform(min_speed, max_speed) * rng.choice((-1, 1)),
        })

    mx, my = MOON_POSITION
    states.append({
        "nx": mx,
        "ny": my,
        "radius_frac": config.STAR_TWIRL_RADIUS * MOON_TWIRL_RADIUS_MULT,
        "speed": min_speed * 0.5,
    })
    return states
