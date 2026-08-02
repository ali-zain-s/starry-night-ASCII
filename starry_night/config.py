"""Tunable constants for the Starry Night matrix renderer."""

SOURCE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/"
    "Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/"
    "1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
)
ASSET_PATH = "assets/starry_night.jpg"
SOURCE_MAX_WIDTH = 640          # working resolution the source image is resized to
SOURCE_BLUR_RADIUS = 1.4        # softens jpeg/brushstroke noise before sampling

CELL_ASPECT = 0.5                # terminal character width / height
SKY_FRACTION = 0.74              # normalized image y below which is "ground" (unwarped)
GROUND_BLEND = 0.06              # normalized-y band over which sky warp fades out

# Matrix-style glyph set: letters, digits, symbols -- no wide/ambiguous unicode.
GLYPH_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!@#$%^&*+=-/\\|<>?~"
)
GLYPH_MIN_INTERVAL = 0.06
GLYPH_MAX_INTERVAL = 0.45

# Big swirl "twirl" centers, in normalized image UV space, roughly matching
# the two dominant spirals in the real painting.
SKY_SWIRLS = [
    # (nx, ny, radius_frac_of_width, strength, rot_speed, phase)
    (0.42, 0.40, 0.22, 2.6, 0.18, 0.0),
    (0.70, 0.26, 0.14, 2.0, 0.26, 2.3),
]
CURRENT_AMPLITUDE = 0.018   # wavy "air flow" vertical displacement (uv units)
CURRENT_WAVELENGTH = 1.6    # in units of image width
CURRENT_SPEED = 0.10

STAR_TWIRL_RADIUS = 0.045   # normalized-width radius of each star's spin zone
STAR_TWIRL_STRENGTH = 3.2
STAR_MIN_SPEED = 0.6
STAR_MAX_SPEED = 1.4

MIN_BRIGHTNESS_FOR_GLYPH = 0.05   # below this, cell renders as blank space
DARK_GLYPH_SKIP_PROB = 0.35       # extra chance to skip a glyph in dim areas
