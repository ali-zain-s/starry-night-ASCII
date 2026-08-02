"""Tunable constants. Nothing here touches the network or the filesystem --
the painting is embedded in painting_data.py."""

CELL_ASPECT = 0.5     # terminal character width / height

# --- animation -------------------------------------------------------------
# Inverse warp: for each cell we compute which source pixel to read at time t.
# Angles are functions of t (not accumulated), so the motion never drifts.

SKY_FRACTION = 0.76   # normalized y below which the ground stops swirling
GROUND_BLEND = 0.08   # band over which the sky warp fades into the ground

# Large swirls, in normalized image coords: (nx, ny, radius_frac, strength, speed)
SWIRLS = [
    (0.42, 0.40, 0.26, 0.55, 0.16),
    (0.70, 0.27, 0.17, 0.45, 0.22),
    (0.13, 0.17, 0.13, 0.30, 0.19),
]

# Every bright star + the moon slowly rotates its own halo.
STAR_SPIN_RADIUS = 0.055    # normalized-width radius of each spin zone
STAR_SPIN_STRENGTH = 1.45
STAR_SPIN_SPEED = (0.45, 0.95)
SPIN_SUPPRESS_RADIUS = 0.085   # of image width; must clear the moon's halo,
                                # or the moon alone claims every spin slot
SPIN_MIN_SCORE = 0.40
SPIN_MAX_CENTERS = 14

# Slow drifting current so the whole sky breathes.
CURRENT_AMPLITUDE = 0.013
CURRENT_WAVELENGTH = 1.5
CURRENT_SPEED = 0.13

# --- glyph flicker ---------------------------------------------------------
# Only a small share of cells re-roll at a time: the picture must stay
# readable, with the Matrix shimmer as texture rather than noise.
GLYPH_MIN_INTERVAL = 0.5
GLYPH_MAX_INTERVAL = 2.6

# --- tone ------------------------------------------------------------------
# The painting only spans about 0.06..0.75 luminance, so it is normalized to
# use the full range, then gamma-lifted: thin glyphs cover little of their
# cell, and without this lift a faithful copy reads as a dim grey smudge.
UNSHARP_RADIUS = 2
UNSHARP_AMOUNT = 0.75

# Glow bled out of the brightest paint, so the stars and moon read as
# luminous discs with visible halos rather than a couple of stray cells.
BLOOM_THRESHOLD = 0.50
BLOOM_RADIUS = 3
BLOOM_STRENGTH = 0.35


# A glyph inks only part of its cell, so it reads darker than the color it
# is drawn in; this gain compensates. Kept small on purpose -- everything
# beyond it trades away color accuracy.
EXPOSURE = 1.30
TONE_GAMMA = 1.0
BLACK_FLOOR = 0.05      # normalized luminance below this renders as blank

# Coherence (how directional the local texture is) above this uses a stroke
# glyph aligned to the flow; below it uses a rounded/blobby glyph instead.
COHERENCE_THRESHOLD = 0.44   # ~25th percentile: strokes dominate, blobs stay round

# --- output ----------------------------------------------------------------
# Truecolor keeps hue precision in the shadows (the 256-color cube does not);
# snapping to a step keeps invisible drift from dirtying cells every frame.
TRUECOLOR = True
COLOR_STEP = 16

# Wider structure-tensor smoothing averages the stroke direction over a
# larger neighbourhood, so glyphs stay aligned across long runs and the
# swirls read as continuous lines instead of breaking up cell to cell.
FLOW_SMOOTH_RADIUS = 2

# Bounds on the per-glyph color compensation, so a very light character
# never demands an absurd over-exposure.
MAX_GAIN = 1.0   # color cannot exceed full brightness

# Add the shade blocks to the glyph ladder. They lift the brightness
# ceiling 3.2x, but measured against this painting they pull the deep
# ultramarine toward grey and flatten the stroke texture, so letters win
# here. Flip it on for a brighter, blockier picture.
SHADE_BLOCKS = False

# How much of the tonal range the glyph carries. Lower = heavier characters
# sooner (brighter, but the shade blocks take over and the lettering is
# lost); higher = letters hold on longer at the cost of peak brightness.
INK_EXPONENT = 0.5
