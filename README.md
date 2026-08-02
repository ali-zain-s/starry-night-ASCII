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

The painting is stored inside the source as compressed data, so there is
nothing to download.

**Picking the characters.** Instead of mapping brightness to a ramp of
characters, the code measures which way the paint is running at each point
(Sobel gradients into a structure tensor) and picks a character that leans
the same way — `-` for flat strokes, `/` and `\` on diagonals, `|` for
uprights, and round ones like `o` and `0` where there is no clear
direction, which is where the stars are.

**Brightness.** How bright a cell looks is roughly how much ink the
character lays down times its colour. The ink each character uses is
measured from the font once, then the colour is worked out to fill in the
rest of the brightness. That keeps the characters from standing out as a
layer on top of the picture.

**Movement.** Nothing is drawn moving. Each frame just samples the
painting from slightly different coordinates — a few vortices rotate the
sky, a slow current drifts across it, and each bright disc spins in place.
The angles come from elapsed time rather than adding up per frame, so it
never drifts out of shape.

**Speed.** Only the cells that actually changed get redrawn each frame,
and colours are rounded so tiny changes don't count as a change. Frame
rate is picked from the window size.

## Credit

Painting by Vincent van Gogh, 1889, public domain.
