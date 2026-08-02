#!/usr/bin/env python3
"""Scans the source painting for bright, yellow, sky-region peaks and
prints normalized (nx, ny) coordinates -- used to populate the hardcoded
lists in starry_night/stars.py. Run from the project root:

    python3 scripts/find_stars.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starry_night import image_source  # noqa: E402


def find_moon(img, box, threshold=0.85):
    h, w = img.shape[0], img.shape[1]
    x0, x1, y0, y1 = box
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    lum = (0.2126 * R + 0.7152 * G + 0.0722 * B) / 255.0
    region = lum[y0:y1, x0:x1]
    mask = region > (region.max() * threshold)
    ys, xs = np.nonzero(mask)
    return (xs.mean() + x0) / w, (ys.mean() + y0) / h


def find_stars(img, sky_fraction, exclude_box, count, min_dist, cell=16, threshold=0.42):
    h, w = img.shape[0], img.shape[1]
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    lum = (0.2126 * R + 0.7152 * G + 0.0722 * B) / 255.0
    yellow = np.clip((R + G) / 2 - B, 0, None) / 255.0
    score = lum * (0.4 + yellow)

    sky_rows = int(h * sky_fraction)
    score[sky_rows:, :] = 0
    ex0, ex1, ey0, ey1 = exclude_box
    score[ey0:ey1, ex0:ex1] = 0

    peaks = []
    for y0 in range(0, sky_rows, cell):
        for x0 in range(0, w, cell):
            block = score[y0:y0 + cell, x0:x0 + cell]
            if block.size == 0:
                continue
            idx = np.unravel_index(np.argmax(block), block.shape)
            val = block[idx]
            if val > threshold:
                peaks.append((val, x0 + idx[1], y0 + idx[0]))

    peaks.sort(reverse=True)
    chosen = []
    for val, x, y in peaks:
        if all((x - cx) ** 2 + (y - cy) ** 2 > min_dist ** 2 for _, cx, cy in chosen):
            chosen.append((val, x, y))
        if len(chosen) >= count:
            break
    return [(x / w, y / h) for _, x, y in chosen]


def main():
    img = image_source.load_source_array(blur_radius=0).astype(np.float32)
    h, w = img.shape[0], img.shape[1]

    moon_box = (int(0.76 * w), w, 0, int(0.34 * h))
    moon = find_moon(img, moon_box)
    print(f"MOON_POSITION = ({moon[0]:.3f}, {moon[1]:.3f})")

    stars = find_stars(img, sky_fraction=0.78, exclude_box=moon_box, count=9, min_dist=40)
    print("STAR_POSITIONS = [")
    for nx, ny in stars:
        print(f"    ({nx:.3f}, {ny:.3f}),")
    print("]")


if __name__ == "__main__":
    main()
