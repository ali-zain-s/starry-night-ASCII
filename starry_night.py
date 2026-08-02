#!/usr/bin/env python3
"""Van Gogh's Starry Night, animated live in the terminal.

A small vortex flow-field pushes hundreds of particles into swirling
brush-stroke trails, pulsing star bursts and a glowing crescent moon hang
over a silhouetted cypress tree and village skyline. Pure Python standard
library, ANSI truecolor. Ctrl+C to quit.
"""
import argparse
import math
import random
import shutil
import signal
import sys
import time

CSI = "\x1b["
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
ALT_SCREEN_ON = CSI + "?1049h"
ALT_SCREEN_OFF = CSI + "?1049l"
HOME = CSI + "H"
RESET = CSI + "0m"

SWIRL_RAMP = " .,:-=+*%#@"
BLOCK = "█"  # solid block for silhouettes

# Palette pulled from the actual painting: deep ultramarine sky, cobalt
# mid-tones, turquoise highlights where the paint catches light.
SKY_LOW = (13, 20, 66)
SKY_MID = (30, 74, 148)
SKY_HIGH = (150, 214, 200)
GOLD = (255, 221, 130)
GOLD_BRIGHT = (255, 244, 200)
MOON_CORE = (255, 214, 110)
MOON_BRIGHT = (255, 240, 180)
CYPRESS = (6, 16, 10)
HILL = (13, 16, 42)
WINDOW_LIT = (255, 175, 70)


def fg(rgb):
    r, g, b = rgb
    return f"{CSI}38;2;{r};{g};{b}m"


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(c_low, c_mid, c_high, t):
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        u = t / 0.5
        return tuple(int(lerp(c_low[i], c_mid[i], u)) for i in range(3))
    u = (t - 0.5) / 0.5
    return tuple(int(lerp(c_mid[i], c_high[i], u)) for i in range(3))


class Vortex:
    def __init__(self, base_cx, base_cy, strength, radius, drift_r, drift_speed, phase):
        self.base_cx = base_cx
        self.base_cy = base_cy
        self.strength = strength
        self.radius = radius
        self.drift_r = drift_r
        self.drift_speed = drift_speed
        self.phase = phase

    def center(self, t):
        a = t * self.drift_speed + self.phase
        return (self.base_cx + self.drift_r * math.cos(a),
                self.base_cy + self.drift_r * math.sin(a) * 0.5)


class Particle:
    __slots__ = ("x", "y", "age", "lifespan")

    def __init__(self, width, sky_h):
        self.respawn(width, sky_h)
        self.age = random.uniform(0, self.lifespan)

    def respawn(self, width, sky_h):
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, sky_h)
        self.age = 0.0
        self.lifespan = random.uniform(3.0, 7.0)


def build_vortices(width, sky_h):
    m = min(width, sky_h)
    return [
        Vortex(0.40 * width, 0.42 * sky_h, 1.4, 0.30 * m, 0.02 * m, 0.15, 0.0),
        Vortex(0.70 * width, 0.28 * sky_h, 1.0, 0.18 * m, 0.015 * m, 0.22, 2.1),
        Vortex(0.16 * width, 0.16 * sky_h, 0.6, 0.12 * m, 0.01 * m, 0.30, 4.4),
    ]


def field_velocity(x, y, t, vortices, width):
    # A long, gentle east-flowing current with a wavy vertical undulation,
    # so brush strokes sweep across the whole sky like the painting's band
    # of cloud, rather than staying trapped near the vortex clusters.
    n = x / width
    vx = 0.30
    vy = 0.35 * math.sin(2 * math.pi * n * 1.3 + t * 0.06)

    for v in vortices:
        cx, cy = v.center(t)
        dx = x - cx
        dy = (y - cy) * 2.0  # compensate character aspect ratio
        dist = math.hypot(dx, dy) + 0.001
        influence = v.radius * 4.0
        if dist > influence:
            continue
        falloff = v.radius / (v.radius + dist)
        speed = v.strength * falloff * 6.0
        vx += speed * (-dy / dist)
        vy += speed * (dx / dist) * 0.5
    return vx, vy


def make_stars(width, sky_h):
    random.seed(7)
    positions = []
    for _ in range(8):
        positions.append({
            "cx": random.uniform(0.06, 0.94) * width,
            "cy": random.uniform(0.05, 0.68) * sky_h,
            "phase": random.uniform(0, 2 * math.pi),
            "pulse_speed": random.uniform(0.7, 1.3),
            "rot_speed": random.uniform(0.5, 1.0) * random.choice((-1, 1)),
            "arms": random.choice((2, 3, 3)),
            "max_r": random.uniform(2.2, 3.4),
        })
    random.seed()
    return positions


def draw_spiral_corona(chars, colors, width, sky_h, cx, cy, t, arms, max_r, rot_speed,
                        core_color, glow_color, dim_color, turns=1.6, steps_per_arm=16):
    for a in range(arms):
        arm_phase = a * (2 * math.pi / arms)
        for i in range(1, steps_per_arm + 1):
            frac = i / steps_per_arm
            r = frac * max_r
            theta = arm_phase + t * rot_speed + frac * turns * 2 * math.pi
            x = cx + 2.0 * r * math.cos(theta)
            y = cy + r * math.sin(theta)
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < width and 0 <= yi < sky_h):
                continue
            b = (1.0 - frac) ** 1.3
            if b < 0.1:
                continue
            ch = "*" if b > 0.55 else ("+" if b > 0.3 else ".")
            chars[yi][xi] = ch
            colors[yi][xi] = tuple(int(lerp(dim_color[i], glow_color[i], b)) for i in range(3))

    cxi, cyi = int(round(cx)), int(round(cy))
    if 0 <= cxi < width and 0 <= cyi < sky_h:
        chars[cyi][cxi] = "@"
        colors[cyi][cxi] = core_color


def draw_star(chars, colors, width, sky_h, star, t):
    pulse = 0.5 + 0.5 * math.sin(t * star["pulse_speed"] + star["phase"])
    draw_spiral_corona(
        chars, colors, width, sky_h, star["cx"], star["cy"], t,
        arms=star["arms"], max_r=star["max_r"] * (0.7 + 0.3 * pulse),
        rot_speed=star["rot_speed"], core_color=GOLD_BRIGHT, glow_color=GOLD,
        dim_color=SKY_LOW, turns=1.4,
    )


def draw_moon(chars, colors, width, sky_h, t):
    mx, my = width * 0.86, sky_h * 0.16
    r = max(2.0, min(width, sky_h) * 0.05)

    draw_spiral_corona(
        chars, colors, width, sky_h, mx, my, t,
        arms=3, max_r=r * 2.3, rot_speed=0.22,
        core_color=MOON_BRIGHT, glow_color=GOLD, dim_color=SKY_LOW, turns=1.1,
    )

    ox, oy = r * 0.55, -r * 0.15
    x0, x1 = int(mx - r * 1.3), int(mx + r * 1.3)
    y0, y1 = int(my - r * 1.3), int(my + r * 1.3)
    for yi in range(max(0, y0), min(sky_h, y1 + 1)):
        for xi in range(max(0, x0), min(width, x1 + 1)):
            dx = (xi - mx) / 2.0
            dy = yi - my
            d = math.hypot(dx, dy)
            if d > r:
                continue
            dx2 = (xi - (mx + ox)) / 2.0
            dy2 = yi - (my + oy)
            d2 = math.hypot(dx2, dy2)
            if d2 > r * 0.82:
                chars[yi][xi] = "@"
                colors[yi][xi] = MOON_CORE


def hill_line(x, width, base):
    n = x / width
    return base + 3.0 * math.sin(n * 6.1 + 0.7) + 1.6 * math.sin(n * 13.0 + 2.0) + 1.0 * math.sin(n * 27.0)


def tree_half_width(row_frac, t, x_base):
    sway = math.sin(t * 0.6) * 1.4 * row_frac
    flame = 2.2 + 1.5 * math.sin(row_frac * 10.0) * (1.0 - row_frac) + 1.0 * math.sin(row_frac * 23.0 + 1.0) * (1.0 - row_frac)
    flame = max(0.4, flame * (1.0 - 0.55 * row_frac))
    return sway, flame


def render_frame(width, height, t, vortices, particles, stars, windows, energy, decay=0.90, deposit=0.55):
    chars = [[" "] * width for _ in range(height)]
    colors = [[None] * width for _ in range(height)]
    sky_h = int(height * 0.72)

    for row in energy:
        for i in range(len(row)):
            row[i] *= decay

    for p in particles:
        xi, yi = int(p.x), int(p.y)
        if 0 <= xi < width and 0 <= yi < sky_h:
            energy[yi][xi] = min(1.0, energy[yi][xi] + deposit)

    for yi in range(sky_h):
        row = energy[yi]
        for xi in range(width):
            e = row[xi]
            if e > 0.03:
                idx = min(len(SWIRL_RAMP) - 1, int(e * (len(SWIRL_RAMP) - 1)))
                ch = SWIRL_RAMP[idx]
                if ch != " ":
                    chars[yi][xi] = ch
                    colors[yi][xi] = lerp3(SKY_LOW, SKY_MID, SKY_HIGH, e)

    draw_moon(chars, colors, width, sky_h, t)
    for star in stars:
        draw_star(chars, colors, width, sky_h, star, t)

    ground_base = height * 0.86
    for x in range(width):
        hl = hill_line(x, width, ground_base)
        for y in range(int(hl), height):
            if 0 <= y < height:
                chars[y][x] = BLOCK
                colors[y][x] = HILL

    tree_x = width * 0.14
    tree_top = height * 0.06
    tree_base = height * 0.90
    for y in range(int(tree_top), int(tree_base)):
        row_frac = 1.0 - (y - tree_top) / (tree_base - tree_top)
        sway, half_w = tree_half_width(row_frac, t, tree_x)
        cx = tree_x + sway
        for x in range(int(cx - half_w), int(cx + half_w) + 1):
            if 0 <= x < width and 0 <= y < height:
                chars[y][x] = BLOCK
                colors[y][x] = CYPRESS

    for wx, wy, phase, on_speed in windows:
        yi, xi = int(wy), int(wx)
        if 0 <= yi < height and 0 <= xi < width:
            lit = math.sin(t * on_speed + phase) > 0.6
            if lit:
                chars[yi][xi] = "▪"
                colors[yi][xi] = WINDOW_LIT

    return chars, colors


def render_to_string(chars, colors):
    out = [HOME]
    last_color = None
    for row_c, row_col in zip(chars, colors):
        line = []
        for ch, col in zip(row_c, row_col):
            if col is None:
                if last_color is not None:
                    line.append(RESET)
                    last_color = None
                line.append(ch)
            else:
                if col != last_color:
                    line.append(fg(col))
                    last_color = col
                line.append(ch)
        out.append("".join(line))
        out.append("\n")
    out.append(RESET)
    return "".join(out)


def make_windows(width, height):
    random.seed(42)
    ground_base = height * 0.86
    windows = []
    x = width * 0.25
    while x < width * 0.98:
        y = ground_base + random.uniform(1.5, 4.0)
        windows.append((x, y, random.uniform(0, 6.28), random.uniform(0.15, 0.5)))
        x += random.uniform(2.5, 5.5)
    random.seed()
    return windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--duration", type=float, default=0.0,
                         help="seconds to run, 0 = forever (Ctrl+C to quit)")
    parser.add_argument("--particles", type=int, default=420)
    args = parser.parse_args()

    size = shutil.get_terminal_size(fallback=(120, 45))
    width, height = size.columns, max(20, size.lines - 1)
    sky_h = int(height * 0.72)

    vortices = build_vortices(width, sky_h)
    particles = [Particle(width, sky_h) for _ in range(args.particles)]
    stars = make_stars(width, sky_h)
    windows = make_windows(width, height)
    energy = [[0.0] * width for _ in range(sky_h)]

    def restore(*_):
        sys.stdout.write(RESET + SHOW_CURSOR + ALT_SCREEN_OFF)
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGINT, restore)
    signal.signal(signal.SIGTERM, restore)

    sys.stdout.write(ALT_SCREEN_ON + HIDE_CURSOR)
    sys.stdout.flush()

    start = time.time()
    frame_time = 1.0 / args.fps

    try:
        while True:
            frame_start = time.time()
            t = frame_start - start

            new_size = shutil.get_terminal_size(fallback=(width, height + 1))
            if new_size.columns != width or max(20, new_size.lines - 1) != height:
                width, height = new_size.columns, max(20, new_size.lines - 1)
                sky_h = int(height * 0.72)
                vortices = build_vortices(width, sky_h)
                stars = make_stars(width, sky_h)
                windows = make_windows(width, height)
                energy = [[0.0] * width for _ in range(sky_h)]

            for p in particles:
                vx, vy = field_velocity(p.x, p.y, t, vortices, width)
                p.x += vx * frame_time
                p.y += vy * frame_time
                p.age += frame_time
                if (p.age > p.lifespan or not (0 <= p.x < width) or not (0 <= p.y < sky_h)):
                    p.respawn(width, sky_h)

            chars, colors = render_frame(width, height, t, vortices, particles, stars, windows, energy)
            sys.stdout.write(render_to_string(chars, colors))
            sys.stdout.flush()

            if args.duration and t >= args.duration:
                break

            elapsed = time.time() - frame_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
    finally:
        sys.stdout.write(RESET + SHOW_CURSOR + ALT_SCREEN_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
