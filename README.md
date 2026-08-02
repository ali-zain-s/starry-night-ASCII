# Starry Night — Matrix Renderer

Van Gogh's *The Starry Night*, reconstructed live in the terminal from the
real painting and rendered as colorful, constantly-reshuffling
Matrix-style glyphs. The sky visibly swirls and the stars spin in place —
all done by warping *where in the source image each frame samples from*,
not by drawing shapes on top of it.

## How it works

1. **`image_source.py`** downloads the real painting (Wikimedia, cached
   locally after the first run) and loads it as a numpy pixel array.
2. **`warp.py`** computes, for every output cell and the current time `t`,
   which source pixel to sample. It composes three effects:
   - a "twirl" distortion (the same math as Photoshop's twirl filter) at
     two large centers, matching the painting's two dominant spirals
   - a wavy vertical current across the whole sky, for the air-flow feel
   - a smaller, faster twirl centered on every real star and the moon —
     because the angle is `time * speed` (not accumulated frame to
     frame), sampling is always from the pristine source image, so the
     spin is stable and can run forever
3. **`renderer.py`** samples the warped coordinates from the image and
   computes brightness per cell.
4. **`glyphs.py`** gives each terminal cell its own independent timer that
   swaps in a new random letter/digit/symbol — the Matrix-code flicker —
   while the *color* stays locked to the real (warped) painting pixel.
5. **`terminal.py`** turns all that into one ANSI-truecolor frame.

The exact star/moon coordinates in `stars.py` weren't eyeballed — they
were found by scanning the actual downloaded image for bright, yellow,
sky-region peaks (`scripts/find_stars.py`), so the spin always lands
exactly on a real star regardless of which source image is in use.

## Run

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

Ctrl+C to quit. First run needs internet to fetch the painting (~600KB,
cached at `assets/starry_night.jpg` after that).

## Options

```bash
python3 run.py --fps 24
python3 run.py --duration 10   # auto-quit after 10s
```

Works best in a truecolor terminal (iTerm2, VS Code, most modern terminal
emulators) with a wide/tall window — the image is letterboxed to fit
whatever size you give it.

## Layout

```
starry_night/
  config.py       tunable constants (warp strength, glyph timing, palette knobs)
  stars.py        real star/moon coordinates + per-point spin parameters
  image_source.py downloads/loads/caches the source painting
  layout.py       fits the image's aspect ratio into the terminal (letterbox)
  warp.py         the twirl / current-wave math (numpy, vectorized)
  glyphs.py       per-cell Matrix-glyph cycling state
  renderer.py     ties warp + image sampling + glyphs into a frame
  terminal.py     ANSI/alt-screen output
  main.py         CLI + event loop
scripts/
  find_stars.py   re-derive stars.py's coordinates from any source image
```
