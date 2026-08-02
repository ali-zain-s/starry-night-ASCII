"""Fits the source image's aspect ratio into the terminal grid (letterboxed)."""
from . import config


def fit_canvas(term_cols, term_lines, img_w, img_h, cell_aspect=None):
    cell_aspect = config.CELL_ASPECT if cell_aspect is None else cell_aspect

    canvas_w = term_cols
    canvas_h = round(canvas_w * cell_aspect * img_h / img_w)

    if canvas_h > term_lines:
        canvas_h = term_lines
        canvas_w = round(canvas_h * img_w / (img_h * cell_aspect))
        canvas_w = min(canvas_w, term_cols)

    canvas_w = max(1, canvas_w)
    canvas_h = max(1, canvas_h)

    x_offset = (term_cols - canvas_w) // 2
    y_offset = (term_lines - canvas_h) // 2
    return canvas_w, canvas_h, x_offset, y_offset
