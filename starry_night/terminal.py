"""Low-level terminal control: ANSI escapes, alt-screen, and frame output."""
import shutil
import sys

CSI = "\x1b["
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
ALT_SCREEN_ON = CSI + "?1049h"
ALT_SCREEN_OFF = CSI + "?1049l"
HOME = CSI + "H"
RESET = CSI + "0m"


def fg(r, g, b):
    return f"{CSI}38;2;{r};{g};{b}m"


def get_size(fallback=(120, 45)):
    size = shutil.get_terminal_size(fallback=fallback)
    return size.columns, size.lines


def enter():
    sys.stdout.write(ALT_SCREEN_ON + HIDE_CURSOR)
    sys.stdout.flush()


def restore():
    sys.stdout.write(RESET + SHOW_CURSOR + ALT_SCREEN_OFF)
    sys.stdout.flush()


def render_frame_string(term_cols, term_lines, x_offset, y_offset, chars, colors, visible):
    canvas_h, canvas_w = chars.shape
    out = [HOME]
    last_color = None

    for row in range(term_lines):
        canvas_row = row - y_offset
        line = []
        if 0 <= canvas_row < canvas_h:
            if x_offset > 0:
                line.append(" " * x_offset)
            char_row = chars[canvas_row]
            color_row = colors[canvas_row]
            vis_row = visible[canvas_row]
            for col in range(canvas_w):
                if vis_row[col]:
                    rgb = (int(color_row[col, 0]), int(color_row[col, 1]), int(color_row[col, 2]))
                    if rgb != last_color:
                        line.append(fg(*rgb))
                        last_color = rgb
                    line.append(char_row[col])
                else:
                    if last_color is not None:
                        line.append(RESET)
                        last_color = None
                    line.append(" ")
            trailing = term_cols - x_offset - canvas_w
            if trailing > 0:
                line.append(" " * trailing)
        else:
            line.append(" " * term_cols)

        out.append("".join(line))
        out.append("\n")

    out.append(RESET)
    return "".join(out)
