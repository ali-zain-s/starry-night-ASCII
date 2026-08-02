# Starry Night - ASCII Art Rendereding 

Van Gogh's *The Starry Night* redrawn as thousands of coloured characters
and set in motion while the sky drifts, the swirls turn, and every star and
the moon rotate in place. Runs in a terminal, entirely offline.

![the animation](docs/starry-night.gif)

## Run it

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

No options. Ctrl+C to quit. It fills whatever window you give it, so a
bigger window with a smaller font gets you more detail.

## How it works

The painting ships inside the source as compressed data, so nothing is
downloaded at startup. Rather than mapping brightness onto a ramp of
characters, the renderer first works out which way the paint is running at
every point using Sobel gradients fed into a structure tensor, then picks a
character that leans the same way, so flat strokes, diagonals and uprights
each get glyphs that trace them while rounded ones fall where the paint has
no direction, which is exactly where the stars sit. Brightness is handled as
a product rather than a lookup, since how bright a cell reads is the ink a
character lays down multiplied by its colour: the ink is measured from the
font once, and the colour is then solved for whatever brightness remains,
which stops the lettering reading as a layer sitting on top of the image.
Nothing is ever drawn in motion either, because each frame simply samples
the painting from shifted coordinates under a few vortices, a slow drifting
current and a rotation centred on each bright disc, with every angle derived
from elapsed time instead of accumulated per frame so the shape never warps
as it runs. Speed comes from redrawing only the cells that genuinely
changed, rounding colours so imperceptible drift is not mistaken for a
change, and choosing the frame rate from the window size.

## Credit

Painting by Vincent van Gogh, 1889, public domain.
