#!/usr/bin/env python3
"""
Bake the animated "Warhol collage" profile card into frozen-frame SVGs, one set
per theme. Each frame is static: for every portrait cell we draw ONE glyph, the
single-portrait glyph or its collage counterpart, whichever is face-up at that
instant, squashed vertically by the flip's scaleY, coloured foreground (single)
or by quadrant (collage). Motion is smooth because we sample the continuous flip
curve; nothing animates live at view time.

The single portrait is read from the committed card SVG (whatever today.py last
wrote, so the baked frames carry live stats + graph). The half-resolution
collage face is read from tools/warhol/face/half_<theme>.txt (committed; the
source photo is gitignored, so the face is precomputed by
tools/warhol/face/regen_half.py when the photo changes). No ImageMagick or photo
needed here or in CI.

    python tools/warhol/warhol.py <theme> <out-dir>     # theme: light | dark

Writes <out-dir>/f####.svg + manifest.json (per-frame delays). The render +
assemble steps (tools/warhol/warhol_render.js, tools/warhol/build_warhol.py)
turn these into the animated WebP.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # tools/warhol
ROOT = os.path.dirname(os.path.dirname(HERE))              # repo root

# --- layout, mirrored from portrait.py / build_cards.py -------------------
COLS, ROWS = 74, 50
X0, Y0, DY, FS = 15, 30, 10, 8
CW = 0.613 * FS                         # fixed cell advance (spacing is defined, not inherited)
HC, HR = COLS // 2, ROWS // 2           # 37 x 25 per quadrant

THEMES = {
    "light": {"file": "light_mode.svg", "fg": "#24292f"},
    "dark":  {"file": "dark_mode.svg",  "fg": "#c9d1d9"},
}
# Pastel quadrant colours [top-left, top-right, bottom-left, bottom-right],
# tuned per ground: light inks darker, dark inks lighter.
PASTEL = {
    "light": ["#c05a8f", "#2f9a94", "#c9962f", "#d1704a"],
    "dark":  ["#ffb3d6", "#a3ece4", "#ffe6ad", "#ffc4a3"],
}

# --- animation timeline (loop fractions) ----------------------------------
LOOP_S = 8.0
FPS = 30
STAGGER = 0.03                          # diagonal wave width
FLIP = 0.0375                           # half-flip duration
S1 = 0.395                              # single held 0..S1
F1 = S1 + FLIP                          # edge-on (swap out)
F2 = F1 + FLIP                          # collage fully up
OUT_END = F2 + STAGGER
C1 = 0.895                              # collage held OUT_END..C1
G1 = C1 + FLIP
G2 = G1 + FLIP
BACK_END = G2 + STAGGER                 # last band finishes at ~1.0


def esc(ch):
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch)


def quad(r, c):
    return (0 if r < HR else 2) + (0 if c < HC else 1)


def single_grid(svg_path):
    """The injected single portrait, 50 rows padded to 74 columns.

    Handles both tspan forms: content `<tspan ...>glyphs</tspan>` and empty
    self-closing `<tspan .../>` (a blank row). today.py round-trips the SVG
    through lxml, which rewrites empty tspans as self-closing, so the parser
    must not treat `/>` as an opening tag (that would swallow following markup
    into the row and render it as literal text)."""
    svg = open(svg_path, encoding="utf-8").read()
    block = re.search(r"<!--portrait:start-->(.*?)<!--portrait:end-->", svg, re.S).group(1)
    rows = re.findall(r"<tspan\b[^>]*?(?:/>|>(.*?)</tspan>)", block, re.S)
    rows = [r.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") for r in rows]
    rows = (rows + [""] * ROWS)[:ROWS]
    return [(r + " " * COLS)[:COLS] for r in rows]


def collage_grid(theme):
    """Half-res face (face/half_<theme>.txt) tiled 2x2 into a 50x74 grid."""
    half = open(os.path.join(HERE, "face", f"half_{theme}.txt"), encoding="utf-8").read().split("\n")
    half = (half + [""] * HR)[:HR]
    half = [(r + " " * HC)[:HC] for r in half]
    return ["".join(half[r if r < HR else r - HR][c if c < HC else c - HC]
                    for c in range(COLS)) for r in range(ROWS)]


def state(local):
    """(scaleY, face) at loop-local fraction; face 'A'=single, 'B'=collage."""
    l = local % 1.0
    if l < S1:  return 1.0, 'A'
    if l < F1:  return 1.0 - (l - S1) / FLIP, 'A'
    if l < F2:  return (l - F1) / FLIP, 'B'
    if l < C1:  return 1.0, 'B'
    if l < G1:  return 1.0 - (l - C1) / FLIP, 'B'
    if l < G2:  return (l - G1) / FLIP, 'A'
    return 1.0, 'A'


def schedule():
    """(p, delay_cs). Two static holds as single long frames; flips at FPS."""
    step = 1.0 / (FPS * LOOP_S)
    dm = round(100 / FPS)
    out = [(round(S1 * 0.5, 4), round(S1 * LOOP_S * 100))]        # single hold
    p = S1
    while p < OUT_END:
        out.append((round(p, 4), dm)); p += step
    out.append((round((OUT_END + C1) / 2, 4), round((C1 - OUT_END) * LOOP_S * 100)))  # collage hold
    p = C1
    while p < BACK_END:
        out.append((round(p, 4), dm)); p += step
    return out


def frozen_layer(single, coll, colors, fg, p):
    out = []
    dmax = (ROWS - 1) + (COLS - 1)
    for r in range(ROWS):
        y = Y0 + r * DY
        cy = y - 3                                # flip hinge at glyph mid-height
        for c in range(COLS):
            a, b = single[r][c], coll[r][c]
            if a == " " and b == " ":
                continue
            s, face = state(p - (r + c) / dmax * STAGGER)
            g = a if face == 'A' else b
            if g == " " or s <= 0.02:
                continue
            col = fg if face == 'A' else colors[quad(r, c)]
            x = round(X0 + c * CW, 1)
            out.append(f'<text x="{x}" y="{y}" fill="{col}" '
                       f'transform="matrix(1 0 0 {round(s, 3)} 0 {round(cy * (1 - s), 2)})">'
                       f'{esc(g)}</text>')
    return "".join(out)


def bake(theme, outdir):
    t = THEMES[theme]
    base = open(os.path.join(ROOT, t["file"]), encoding="utf-8").read()
    single = single_grid(os.path.join(ROOT, t["file"]))
    coll = collage_grid(theme)
    colors = PASTEL[theme]

    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        os.remove(os.path.join(outdir, f))

    manifest = []
    for i, (p, delay) in enumerate(schedule()):
        layer = frozen_layer(single, coll, colors, t["fg"], p)
        svg = re.sub(r'<text x="15" y="30"[^>]*class="ascii">.*?</text>',
                     f'<g font-size="{FS}px">{layer}</g>', base, count=1, flags=re.S)
        name = f"f{i:04d}.svg"
        open(os.path.join(outdir, name), "w", encoding="utf-8").write(svg)
        manifest.append({"svg": name, "png": f"f{i:04d}.png", "delay_cs": delay})
    json.dump({"theme": theme, "w": 1025, "h": 540, "frames": manifest},
              open(os.path.join(outdir, "manifest.json"), "w"))
    return len(manifest)


if __name__ == "__main__":
    n = bake(sys.argv[1], sys.argv[2])
    print(f"baked {n} frames -> {sys.argv[2]}")
