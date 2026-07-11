#!/usr/bin/env python3
"""
Generate the hero cards dark_mode.svg and light_mode.svg from one shared layout,
so the two themes never drift. The left column carries portrait markers that
tools/portrait.py fills in; the right column carries the <text id="..."> nodes
that today.py rewrites with live GitHub stats.

Build order (each step is one command, no hand-editing):
    python tools/build_cards.py                                    # the two SVGs
    python tools/portrait.py portrait.jpeg          --inject dark_mode.svg
    python tools/portrait.py portrait.jpeg --invert --inject light_mode.svg

The two themes use opposite ramps on purpose. The photo is a lit face on a
near-black background. Dark mode uses light ink on a dark card, so the default
ramp (bright pixel -> dense glyph) makes the lit face glow and the black
background falls away into empty cells. Light mode uses dark ink on a white
card; the same ramp would render the lit face as a dark mass. So light mode
inverts the ramp (--invert): the dark background becomes the dense (dark-ink)
panel and the face stays light. Both cards render from the same photo, so they
share one face (the light glyphs are the dark glyphs inverted); portrait.py
sizes the grid so the portrait clears this text column.

Re-running build_cards.py resets the portrait region to empty markers, so run
both portrait.py commands again afterwards.

Two things are computed here so no coordinate is ever hand-tuned:
  - Header dividers are padded per line to a common right edge (TARGET_COLS),
    so every "- Section ----" rule ends at the same column regardless of label.
  - The right column's line step is derived from the portrait's bottom baseline
    (PORTRAIT_ROWS at DY_PORTRAIT from Y0). Both columns then start at Y0 and end
    at the same y, so the text and the headshot bottom-align for any row count.
    Add or drop a section line and the spacing re-solves on the next build.

If assets/monogram.png exists, two extra cards are emitted, dark_mono.svg and
light_mono.svg, with the "S" mark (recolored to the brand accent) in place of the
portrait. today.py updates whichever of the four cards are present.
"""
import base64
import os

# Layout geometry. The portrait grid (tools/portrait.py) is PORTRAIT_ROWS rows at
# DY_PORTRAIT starting at Y0, so its last baseline is BOTTOM. Keep these in sync
# with portrait.py's --height/step if you ever change them.
Y0, DY_PORTRAIT, PORTRAIT_ROWS = 30, 10, 50
PORTRAIT_FS = 8                                   # portrait glyphs at half the 16px body size
BOTTOM = Y0 + (PORTRAIT_ROWS - 1) * DY_PORTRAIT   # 520
CARD_W, CARD_H = 1025, BOTTOM + 20                # 540
TARGET_COLS = 64                                  # header line length; rule reaches ~x=1004

MONO_SRC = "assets/monogram.png"

THEMES = {
    "dark_mode.svg": {
        "bg": "#121210", "fg": "#c9d1d9",
        "hdr": "#58a6ff", "key": "#79c0ff", "value": "#c9d1d9", "cc": "#3d444d",
        "add": "#8bab68", "delc": "#cc7a5a", "muted": "#8b949e",
    },
    "light_mode.svg": {
        "bg": "#ffffff", "fg": "#24292f",
        "hdr": "#0550ae", "key": "#0969da", "value": "#24292f", "cc": "#d0d7de",
        "add": "#2f6f3f", "delc": "#a5372a", "muted": "#57606a",
    },
}


def rule(label):
    """Box-drawing dashes that pad `label` out to a TARGET_COLS-wide header line.
    `label` may contain the &amp; entity, which renders as one glyph."""
    visible = label.replace("&amp;", "&")
    return "─" * max(0, TARGET_COLS - len(visible) - 1)


# Right column as an ordered list of logical rows. Headers carry class="hdr";
# a bare ". " row is a blank spacer. Section headers get a blank row after them.
# x and y are stamped on emit (see build_right), so nothing here is positioned.
def _rows():
    rows = []
    H = lambda label: rows.append(f'<tspan class="hdr">{label}</tspan><tspan class="cc"> {rule(label)}</tspan>')
    R = rows.append
    B = lambda: rows.append('<tspan class="cc">. </tspan>')

    H('alexshao@github')
    R('<tspan class="cc">. </tspan><tspan class="key">Role</tspan>:<tspan class="cc"> ..... </tspan><tspan class="value">Researcher @ Symbiokinetics</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="key">Field</tspan>:<tspan class="cc"> .... </tspan><tspan class="value">Robotic platforms for healthcare</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="key">Study</tspan>:<tspan class="cc"> .... </tspan><tspan class="value">Pure Mathematics, UC Berkeley</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="key">Uptime</tspan>: <tspan class="cc" id="age_data_dots"></tspan><tspan class="value" id="age_data">a few years</tspan>')
    B()
    H('─ Languages')
    R('<tspan class="cc">. </tspan><tspan class="value">Python  C  C++  CUDA  Rust  TypeScript</tspan>')
    B()
    H('─ Core Stack')
    R('<tspan class="cc">. </tspan><tspan class="value">ROS2  STM32  FreeRTOS  Linux  MuJoCo  Isaac Sim</tspan>')
    B()
    H('─ Research &amp; development interests')
    R('<tspan class="cc">. </tspan><tspan class="value">Real-time robotic control systems</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="value">Reinforcement learning, imitation learning, skill discovery</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="value">Embedded &amp; distributed real-time systems</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="value">GPU programming &amp; HPC</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="value">AI architecture &amp; interpretability</tspan>')
    B()
    H('─ GitHub Stats')
    R('<tspan class="cc">. </tspan><tspan class="key">Repos</tspan>:<tspan class="cc" id="repo_data_dots"> .... </tspan><tspan class="value" id="repo_data">0</tspan> {<tspan class="key">Contributed</tspan>: <tspan class="value" id="contrib_data">0</tspan>} | <tspan class="key">Stars</tspan>:<tspan class="cc" id="star_data_dots"> ........... </tspan><tspan class="value" id="star_data">0</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="key">Commits</tspan>:<tspan class="cc" id="commit_data_dots"> ................. </tspan><tspan class="value" id="commit_data">0</tspan> | <tspan class="key">Followers</tspan>:<tspan class="cc" id="follower_data_dots"> ....... </tspan><tspan class="value" id="follower_data">0</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="key">Lines of Code</tspan>:<tspan class="cc" id="loc_data_dots">. </tspan><tspan class="value" id="loc_data">0</tspan> ( <tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>, <tspan id="loc_del_dots"> </tspan><tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )')
    B()
    H('─ Links')
    R('<tspan class="cc">. </tspan><tspan class="value">alexshao.net</tspan><tspan class="cc">  ·  </tspan><tspan class="value">github.com/AlexShaooo</tspan><tspan class="cc">  ·  </tspan><tspan class="value">in/alex-shao</tspan>')
    R('<tspan class="cc">. </tspan><tspan class="key">Email</tspan>:<tspan class="cc"> </tspan><tspan class="value">alex.w.shao@gmail.com</tspan>')
    return rows


def build_right():
    """Stamp x=390 and a computed y on each row so the last baseline lands on
    BOTTOM, i.e. the text bottom-aligns with the portrait for any row count."""
    rows = _rows()
    dy = (BOTTOM - Y0) / (len(rows) - 1)
    out = []
    for i, r in enumerate(rows):
        y = round(Y0 + i * dy, 2)
        out.append(r.replace("<tspan ", f'<tspan x="390" y="{y}" ', 1))
    return "\n".join(out)


FONT = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

TEMPLATE = '''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="{font}" width="{w}px" height="{h}px" font-size="16px">
<style>
.hdr {{fill: {hdr};}}
.key {{fill: {key};}}
.value {{fill: {value};}}
.addColor {{fill: {add};}}
.delColor {{fill: {delc};}}
.cc {{fill: {cc};}}
.muted {{fill: {muted};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="{w}px" height="{h}px" fill="{bg}" rx="15"/>
<text x="15" y="30" fill="{fg}" font-size="{pfs}px" class="ascii">
<!--portrait:start-->
<!--portrait:end-->
</text>
<text x="390" y="30" fill="{fg}">
{right}
</text>
</svg>
'''


MONO_TEMPLATE = '''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="{font}" width="{w}px" height="{h}px" font-size="16px">
<style>
.hdr {{fill: {hdr};}}
.key {{fill: {key};}}
.value {{fill: {value};}}
.addColor {{fill: {add};}}
.delColor {{fill: {delc};}}
.cc {{fill: {cc};}}
.muted {{fill: {muted};}}
text, tspan {{white-space: pre;}}
</style>
<defs>
<filter id="tint" x="0" y="0" width="100%" height="100%">
<feColorMatrix type="matrix" values="0 0 0 0 {r}  0 0 0 0 {g}  0 0 0 0 {b}  0 0 0 1 0"/>
</filter>
</defs>
<rect width="{w}px" height="{h}px" fill="{bg}" rx="15"/>
<image x="115" y="150" width="160" height="160" filter="url(#tint)" href="data:image/png;base64,{mono_b64}"/>
<text x="195" y="360" text-anchor="middle" font-size="26px" fill="{key}">Alex Shao</text>
<text x="195" y="392" text-anchor="middle" font-size="15px" class="muted">@AlexShaooo</text>
<text x="390" y="30" fill="{fg}">
{right}
</text>
</svg>
'''


def hex_rgb(h):
    """'#rrggbb' -> normalized 'r g b' fields for feColorMatrix."""
    h = h.lstrip("#")
    return {k: round(int(h[i:i + 2], 16) / 255, 3) for k, i in (("r", 0), ("g", 2), ("b", 4))}


def main():
    right = build_right()
    for filename, t in THEMES.items():
        svg = TEMPLATE.format(font=FONT, right=right, w=CARD_W, h=CARD_H, pfs=PORTRAIT_FS, **t)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {filename}")

    if os.path.exists(MONO_SRC):
        mono_b64 = base64.b64encode(open(MONO_SRC, "rb").read()).decode("ascii")
        for portrait_name, t in THEMES.items():
            mono_name = portrait_name.replace("_mode.svg", "_mono.svg")
            svg = MONO_TEMPLATE.format(font=FONT, right=right, w=CARD_W, h=CARD_H,
                                       mono_b64=mono_b64, **t, **hex_rgb(t["key"]))
            with open(mono_name, "w", encoding="utf-8") as f:
                f.write(svg)
            print(f"wrote {mono_name}")
    else:
        print(f"(no {MONO_SRC}; skipping monogram cards)")


if __name__ == "__main__":
    main()
