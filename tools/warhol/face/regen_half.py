#!/usr/bin/env python3
"""
Regenerate the committed half-resolution collage faces half_<theme>.txt (in this
folder) from the source photo. Run locally when the portrait changes; the output
is committed so CI needs neither the photo (gitignored) nor ImageMagick.

    python tools/warhol/face/regen_half.py [reference/portrait.jpeg]

Light uses the inverted ramp (dark ink on white), dark the normal ramp, matching
build_cards.py. Grid is 37x25 = one quadrant of the 74x50 card grid.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # tools/warhol/face
TOOLS = os.path.dirname(os.path.dirname(HERE))             # tools/  (has portrait.py)
ROOT = os.path.dirname(TOOLS)                              # repo root
sys.path.insert(0, TOOLS)
import portrait  # noqa: E402

photo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reference", "portrait.jpeg")
for theme, invert in (("light", True), ("dark", False)):
    rows = portrait.render(photo, invert=invert, width=37, height=25)
    open(os.path.join(HERE, f"half_{theme}.txt"), "w").write("\n".join(rows) + "\n")
    print(f"wrote tools/warhol/face/half_{theme}.txt ({len(rows)} rows)")
