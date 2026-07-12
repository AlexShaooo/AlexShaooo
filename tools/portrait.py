#!/usr/bin/env python3
"""
Convert a photo into an ASCII-art portrait sized for the profile card's left
column, and (optionally) inject it straight into the card SVGs. This keeps the
portrait reproducible: change the source or the knobs, re-run one command, done.

Requirements: ImageMagick (`magick` on PATH). No Python packages needed; the
luminance ramp is applied in pure stdlib from ImageMagick's text pixel dump.

Grid: COLS columns x 50 rows, mapped to <tspan x="15" y="30..520" step 10>, which
is exactly the left <text> block of dark_mode.svg / light_mode.svg (rendered at
8px, half the body size). COLS is derived so the portrait's right edge clears the
text column at x=390; the photo is cover-scaled and center-cropped to the grid so
the face keeps its proportions (no stretching).

Examples:
    # preview only (prints ASCII + the <tspan> block)
    python tools/portrait.py portrait.jpeg

    # write the portrait into both cards, same framing, opposite ramps
    python tools/portrait.py portrait.jpeg          --inject dark_mode.svg
    python tools/portrait.py portrait.jpeg --invert --inject light_mode.svg

Both cards render from the same photo, so the faces line up exactly (the light
card's glyphs are the dark card's inverse).

Knobs:
    --invert         dark->dense instead of bright->dense. Puts the dense glyphs
                     on the dark parts of the photo, for a card that draws dark
                     ink on a light background (light_mode.svg).
    --crop WxH+X+Y   ImageMagick crop geometry applied before the grid fit
    --bc BxC         brightness-contrast, e.g. 0x10
    --width / --height   grid size (advanced; defaults are layout-derived)

The card SVGs must contain a pair of marker comments around the left tspans:
    <!--portrait:start-->
    ... generated tspans ...
    <!--portrait:end-->
"""
import argparse
import re
import subprocess
import sys

RAMP = " .:-=+*#%@"  # index 0 = darkest cell, index 9 = densest glyph
START, END = "<!--portrait:start-->", "<!--portrait:end-->"

# Layout, mirrored from build_cards.py (keep in sync). The portrait is a grid of
# glyphs at font-size FS, laid out from (X0, Y0) with a DY row step over ROWS rows.
# The right text column starts at TEXT_X, so the portrait must stay left of it.
X0, Y0, DY, FS, ROWS, TEXT_X = 15, 30, 10, 8, 50, 390
GUTTER = 12                       # px kept clear between the portrait and TEXT_X

# Monospace advance width as a fraction of the em, measured for the card font
# stack (0.613 on macOS: Menlo / SF Mono, via a Chrome render; DejaVu Sans Mono
# is ~0.60, Consolas ~0.55). This is what makes the glyph cell non-square: CELL_W
# is ~0.49 of CELL_H, so the crop aspect below must use it, or the face stretches.
ADVANCE = 0.613
CELL_W, CELL_H = ADVANCE * FS, DY

# Grid width chosen so the portrait's right edge clears TEXT_X by GUTTER. The
# region (COLS*CELL_W wide, ROWS*CELL_H tall) then has an aspect the source photo
# is cropped to, so no dimension is stretched.
COLS = int((TEXT_X - X0 - GUTTER) / CELL_W)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(path, invert=False, crop=None, bc=None, width=COLS, height=ROWS):
    """Return a list of `height` ASCII rows (right-trimmed) for the image.

    The glyph cell is CELL_W x CELL_H, so the grid renders over a display region
    of (width*CELL_W) x (height*CELL_H). The photo is scaled to cover that region
    and center-cropped to it (trimming the overflow evenly from both sides), then
    squashed to the width x height grid. The anisotropic squash is exactly undone
    by the non-square cells at render time, so the face keeps its proportions."""
    dw, dh = round(width * CELL_W), round(height * CELL_H)
    cmd = ["magick", path]
    if crop:
        cmd += ["-gravity", "North", "-crop", crop, "+repage"]
    if bc:
        cmd += ["-brightness-contrast", bc]
    cmd += ["-resize", f"{dw}x{dh}^", "-gravity", "center", "-extent", f"{dw}x{dh}",
            "-resize", f"{width}x{height}!", "-colorspace", "Gray",
            "-normalize", "-depth", "8", "txt:-"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("error: ImageMagick not found. Install it (e.g. `brew install imagemagick`).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"error: ImageMagick failed:\n{e.stderr}")

    cells, maxx, maxy = {}, 0, 0
    for line in out.splitlines():
        m = re.match(r"\s*(\d+),(\d+):.*#([0-9A-Fa-f]{6})", line)
        if not m:
            continue
        x, y, hx = int(m.group(1)), int(m.group(2)), m.group(3)
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
        cells[(x, y)] = 0.299 * r + 0.587 * g + 0.114 * b
        maxx, maxy = max(maxx, x), max(maxy, y)

    n = len(RAMP) - 1                 # last ramp index; RAMP length is free to change
    rows = []
    for y in range(maxy + 1):
        row = []
        for x in range(maxx + 1):
            idx = min(n, int(cells.get((x, y), 0) / 255 * n))
            row.append(RAMP[n - idx] if invert else RAMP[idx])
        rows.append("".join(row).rstrip())
    return rows


def to_tspans(rows):
    return "\n".join(
        f'<tspan x="{X0}" y="{Y0 + i * DY}">{esc(row)}</tspan>'
        for i, row in enumerate(rows)
    )


def inject(files, tspan_block):
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    replacement = f"{START}\n{tspan_block}\n{END}"
    for f in files:
        text = open(f, encoding="utf-8").read()
        if not pattern.search(text):
            sys.exit(f"error: {f} has no {START} / {END} markers to inject into.")
        open(f, "w", encoding="utf-8").write(pattern.sub(replacement, text))
        print(f"injected portrait into {f}")


def main():
    ap = argparse.ArgumentParser(description="Photo -> ASCII portrait for the profile card.")
    ap.add_argument("image")
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--crop", default=None)
    ap.add_argument("--bc", default=None)
    ap.add_argument("--width", type=int, default=COLS,
                    help=f"grid columns (advanced; default {COLS} clears the text column)")
    ap.add_argument("--height", type=int, default=ROWS,
                    help=f"grid rows (advanced; default {ROWS} fills the card height)")
    ap.add_argument("--inject", nargs="+", metavar="SVG",
                    help="SVG files to write the portrait into (between markers)")
    a = ap.parse_args()

    rows = render(a.image, a.invert, a.crop, a.bc, a.width, a.height)
    block = to_tspans(rows)
    if a.inject:
        inject(a.inject, block)
    else:
        print("\n".join(rows))
        print("\n----- tspan -----")
        print(block)


if __name__ == "__main__":
    main()
