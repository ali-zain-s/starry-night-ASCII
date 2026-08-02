# Starry Night, Rendered in Characters

Van Gogh's *The Starry Night* redrawn as ~34,000 coloured characters and
set in motion — the sky drifts, the swirls turn, and every star and the
moon rotate in place. It runs in a terminal, entirely offline.

![the animation](docs/starry-night.gif)

```bash
python3 -m pip install -r requirements.txt
python3 run.py            # plain terminal cells, works anywhere
python3 run.py --image    # ~6x the detail, needs terminal image support
```

## The approach

Most text-art converters map brightness to a ramp of characters and stop
there. That reproduces a photograph's tone but throws away the thing that
makes a Van Gogh a Van Gogh: the paint has *direction*. So this starts by
recovering that direction — the local orientation of every brushstroke is
measured straight from the pixels, along with a confidence score saying
how strongly directional each patch really is. Characters are then chosen
to lie *along* the stroke: horizontal marks where the paint runs flat,
slashes on the diagonals, uprights where it climbs, and rounded glyphs
where the paint has no direction at all — which is exactly where the star
and moon discs are. Text stops looking scattered over the picture and
starts tracing it.

The second idea is about tone. A cell's apparent brightness is *ink
coverage times colour*, so encoding brightness in both — faint characters
in dark colours, heavy ones in bright — squares the contrast and makes the
lettering read as a texture sitting on top of the image. Instead, the ink
each character lays down is measured from the real font, the glyph is
asked to carry part of the tonal range, and the colour is calculated to
supply exactly the remainder. Their product then tracks the painting, and
the characters dissolve into it.

Motion is a warp of *where each cell samples from*, not of anything drawn.
Three large vortices turn the sky, a slow current drifts across it, and a
rotation is centred on every bright disc — those are found by scanning the
painting for them rather than placed by hand. Every angle is a function of
elapsed time rather than an accumulated step, so it can run for hours
without drifting or smearing.

The painting itself lives inside the source as a compressed palette and
index array, so there is no download, no image file on disk, and nothing
to fetch at startup.

## Detail, honestly

One character is one pixel of the finished picture, so the character count
*is* the resolution — and a terminal cell is the smallest thing text mode
can address. A normal window holds only about 5,000 of them, which is not
enough for a painting no matter how the rest is tuned.

`--image` sidesteps that by rasterising the characters at 4×7 pixels and
handing the terminal a picture each frame, reaching ~34,000 characters in
the same window with nothing to zoom. It needs a terminal that renders
inline images:

* **VS Code** — enable `terminal.integrated.enableImages`, then reopen the
  terminal.
* **iTerm2, WezTerm, Konsole** — works as-is.

If a terminal doesn't support it, the escape is silently swallowed and the
screen stays blank with no error — which is why plain text is the default.
In text mode the only lever is the font: make it smaller and the window
bigger. Running with `--info` reports where you stand.

## Options

```bash
python3 run.py --image --columns 320   # finer still
python3 run.py --image --protocol iterm  # cheaper, iTerm2/WezTerm only
python3 run.py --info                  # what this window can hold
python3 run.py --fps 12                # override the automatic pacing
python3 run.py --duration 10           # auto-quit
```

## Credit

Painting by Vincent van Gogh, 1889, public domain.
