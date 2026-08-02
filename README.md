# Starry Night - ASCII Art Rendereding 

Van Gogh's *The Starry Night* redrawn as thousands of coloured characters
and set in motion while the sky drifts, the swirls turn, and every star and
the moon rotate in place. Runs in a terminal, entirely offline.

![the animation](docs/starry-night.gif)

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

## The approach

Most text-art converters map brightness onto a ramp of characters. That
captures tone but throws away what makes a Van Gogh a Van Gogh: the paint
has *direction*. So the local orientation of every brushstroke is measured
from the pixels first, and characters are chosen to lie *along* it —
horizontal marks where the paint runs flat, slashes on the diagonals,
rounded glyphs where there's no direction at all, which is exactly where
the stars are.

Tone is split between ink and colour. A cell's apparent brightness is ink
coverage times colour, so encoding brightness in both squares the contrast
and leaves the lettering sitting on top of the picture. Instead the ink
each character lays down is measured from the font, the glyph carries part
of the range, and the colour supplies exactly the remainder — so the two
multiply back to the painting and the text dissolves into it.

Motion is a warp of where each cell *samples from*, never of anything
drawn. Vortices turn the sky, a current drifts across it, and every bright
disc spins in place. Angles are functions of elapsed time rather than
accumulated steps, so it runs for hours without drifting.

The painting lives inside the source as compressed data — nothing to
download, no image on disk.

## Detail

One character is one pixel of the result, so the character count is the
resolution. Smaller font and a bigger window is the only lever; `--info`
reports where a given terminal stands.

## Credit

Painting by Vincent van Gogh, 1889, public domain.
