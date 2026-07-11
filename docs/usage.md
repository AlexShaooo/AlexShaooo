# Building the profile cards

Run from the repo root:

```sh
python tools/build_cards.py
python tools/portrait.py portrait.jpeg          --left 6 --keep 74 --inject dark_mode.svg
python tools/portrait.py portrait.jpeg --invert --left 6 --keep 74 --inject light_mode.svg
```

`build_cards.py` clears the portrait, so re-run the two portrait commands after
it. Keep `--left` / `--keep` the same across both so the faces line up.

## portrait.py arguments

```
--invert         invert the ramp (dark pixel -> dense glyph); use for light_mode.svg
--left N         shave N grid columns off the left, sliding the rest to x=15
--keep N         keep N columns after the shave (clips the right)
--crop WxH+X+Y   ImageMagick crop, applied before the resize
--bc BxC         brightness-contrast, e.g. 0x10
--width N        grid columns (default 88)
--height N       grid rows (default 50)
--inject SVG...  write between the portrait markers in these files
```
