"""Sixel encoder.

VS Code's terminal renders sixel but not the iTerm2 inline-image escape,
which is why the same frame shows up in iTerm and stays blank there. Sixel
is the older, more widely implemented of the two, so this is the fallback
that actually reaches the most terminals.

Format, briefly: the image is cut into horizontal bands six pixels tall.
Within a band each colour is drawn in its own pass, one byte per column,
where the low six bits say which of the six rows that colour occupies
(offset by 63 to land in printable ASCII). `$` returns to the start of the
band for the next colour, `-` moves to the next band.
"""
import numpy as np


def _rle(codes):
    """Sixel run-length encoding: !<count><char> once a run pays for itself."""
    changes = np.flatnonzero(codes[1:] != codes[:-1]) + 1
    starts = np.concatenate(([0], changes))
    lengths = np.diff(np.concatenate((starts, [len(codes)])))
    values = codes[starts]

    out = []
    append = out.append
    for value, run in zip(values.tolist(), lengths.tolist()):
        ch = chr(value)
        append(f"!{run}{ch}" if run > 3 else ch * run)
    return "".join(out)


def encode(rgb, max_colors=64):
    """(H, W, 3) uint8 -> a sixel escape string."""
    from PIL import Image

    img = Image.fromarray(rgb).convert(
        "P", palette=Image.ADAPTIVE, colors=max_colors, dither=Image.NONE
    )
    idx = np.asarray(img, dtype=np.uint8)
    height, width = idx.shape
    palette = img.getpalette()[: max_colors * 3]
    used = np.unique(idx)

    out = [f'\x1bPq"1;1;{width};{height}']
    for c in used:
        r, g, b = palette[c * 3: c * 3 + 3]
        # Sixel colour registers are 0..100, not 0..255.
        out.append(f"#{c};2;{r * 100 // 255};{g * 100 // 255};{b * 100 // 255}")

    weights = (1 << np.arange(6)).astype(np.uint16)

    for top in range(0, height, 6):
        band = idx[top: top + 6]
        rows = band.shape[0]
        present = np.unique(band)

        # All colours in the band at once: (colours, rows, width) equality
        # collapsed against the row weights. Looping colours in Python here
        # cost more than the rest of the encoder combined.
        eq = band[None, :, :] == present[:, None, None]
        bits = (eq * weights[None, :rows, None]).sum(axis=1).astype(np.uint8) + 63

        pieces = []
        for i, c in enumerate(present):
            row = bits[i]
            if not (row - 63).any():
                continue
            pieces.append(f"#{c}" + _rle(row))

        out.append("$".join(pieces))
        out.append("-")

    out.append("\x1b\\")
    return "".join(out)
