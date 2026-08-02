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

Use Ctrl+C to quit. 

It fills whatever window you give it, so a
bigger window with a smaller font gets you more detail.

## Implementation

The painting is stored directly in the program and rendered as **ASCII** art, 
so nothing needs to be downloaded. Instead of choosing ASCII characters only 
by brightness, the program matches them to the direction of the original 
brushstrokes, making the final result resemble the painting more closely.

## Credit

Painting by Vincent van Gogh, 1889, public domain.
