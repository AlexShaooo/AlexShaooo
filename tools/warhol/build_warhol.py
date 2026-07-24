#!/usr/bin/env python3
"""
Build the two animated LEFT portrait images (the fixed animation) as WebP:

    assets/left_light.webp   assets/left_dark.webp

Pipeline: bake frozen frames (tools/warhol/warhol.py, from left_<theme>.svg) ->
render to PNG with one headless Chrome (tools/warhol/warhol_render.js) -> assemble
a looping lossless animated WebP with img2webp, honouring per-frame delays.

The portrait flip is fixed art, so this runs LOCALLY on demand (when the photo or
flip design changes), not in the weekly Action. The weekly Action only reruns
today.py to refresh the separate right-panel stats SVGs.

Requirements: python3, node (>=21), a Chrome/Chromium (set CHROME_PATH if needed),
and img2webp (libwebp). Nothing writes outside a temp build dir except the two
final .webp files.

    python tools/warhol/build_warhol.py            # both themes at 2x
    SCALE=1 python tools/warhol/build_warhol.py    # 1x
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))          # tools/warhol
ROOT = os.path.dirname(os.path.dirname(HERE))              # repo root
sys.path.insert(0, HERE)
import warhol  # noqa: E402

SCALE = os.environ.get("SCALE", "2")
THEMES = ("light", "dark")


def main():
    build = tempfile.mkdtemp(prefix="warhol-build-")
    dirs = {th: os.path.join(build, th) for th in THEMES}
    try:
        for th in THEMES:
            n = warhol.bake(th, dirs[th])
            print(f"baked {th}: {n} frames")

        env = {**os.environ, "SCALE": SCALE}
        subprocess.run(["node", os.path.join(HERE, "warhol_render.js"), *dirs.values()],
                       check=True, env=env)

        for th in THEMES:
            man = json.load(open(os.path.join(dirs[th], "manifest.json")))
            out = os.path.join(ROOT, "assets", f"left_{th}.webp")
            args = ["img2webp", "-loop", "0", "-lossless", "-m", "6"]
            for fr in man["frames"]:
                args += ["-d", str(fr["delay_cs"] * 10), os.path.join(dirs[th], fr["png"])]
            args += ["-o", out]
            subprocess.run(args, check=True, stderr=subprocess.DEVNULL)
            print(f"wrote {os.path.basename(out)}  {os.path.getsize(out)/1024:.0f} KB "
                  f"({len(man['frames'])} frames @{SCALE}x)")
    finally:
        shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    main()
