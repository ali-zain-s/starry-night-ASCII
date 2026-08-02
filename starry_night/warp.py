"""Vectorized image-space warps: swirling sky, spinning stars, wavy current.

Everything here is an *inverse* warp: for each output pixel we compute the
coordinate to sample FROM in the static source image at time t. Because we
always sample from the pristine source, the swirl angle is a direct
function of t (not accumulated frame to frame), so the animation is stable
and resolution-independent.
"""
import numpy as np

from . import config


def sky_mask(Y, img_h):
    y_norm = Y / img_h
    edge = config.SKY_FRACTION
    band = config.GROUND_BLEND
    t = (edge - y_norm) / band
    return np.clip(t, 0.0, 1.0)


def twirl(X, Y, cx, cy, radius, strength, angle):
    dx = X - cx
    dy = Y - cy
    r = np.sqrt(dx * dx + dy * dy)
    falloff = np.clip(1.0 - r / radius, 0.0, 1.0) ** 1.5
    local_angle = falloff * (strength + angle)
    cosA = np.cos(local_angle)
    sinA = np.sin(local_angle)
    Xs = cx + dx * cosA - dy * sinA
    Ys = cy + dx * sinA + dy * cosA
    return Xs, Ys


def current_wave(X, img_w, t):
    wavelength = config.CURRENT_WAVELENGTH * img_w
    phase = 2 * np.pi * X / wavelength + t * config.CURRENT_SPEED * 2 * np.pi
    return config.CURRENT_AMPLITUDE * img_w * np.sin(phase)


def apply_all(X, Y, t, img_w, img_h, star_states):
    mask = sky_mask(Y, img_h)

    Xs, Ys = X.astype(np.float64).copy(), Y.astype(np.float64).copy()

    dy_wave = current_wave(Xs, img_w, t)
    Ys = Ys + dy_wave * mask

    for nx, ny, radius_frac, strength, rot_speed, phase in config.SKY_SWIRLS:
        cx, cy = nx * img_w, ny * img_h
        radius = radius_frac * img_w
        Xt, Yt = twirl(Xs, Ys, cx, cy, radius, strength, t * rot_speed + phase)
        Xs = Xs + (Xt - Xs) * mask
        Ys = Ys + (Yt - Ys) * mask

    for star in star_states:
        cx, cy = star["nx"] * img_w, star["ny"] * img_h
        radius = star["radius_frac"] * img_w
        angle = t * star["speed"]
        Xt, Yt = twirl(Xs, Ys, cx, cy, radius, config.STAR_TWIRL_STRENGTH, angle)
        Xs = Xs + (Xt - Xs) * mask
        Ys = Ys + (Yt - Ys) * mask

    np.clip(Xs, 0, img_w - 1, out=Xs)
    np.clip(Ys, 0, img_h - 1, out=Ys)
    return Xs, Ys
