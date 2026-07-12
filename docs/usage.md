# Building the profile cards

Run from the repo root:

```sh
python tools/build_cards.py
python tools/portrait.py portrait.jpeg          --inject dark_mode.svg
python tools/portrait.py portrait.jpeg --invert --inject light_mode.svg
```

`build_cards.py` clears the portrait, so re-run the two portrait commands after
it. The only difference between them is `--invert` (the light card uses the
inverted ramp), so both render the same framing and the faces line up.

## Contribution graph

```sh
python tools/commit_graph.py            # fake sample data, dark + light
python tools/commit_graph.py --real     # live data (needs ACCESS_TOKEN, USER_NAME)
python tools/commit_graph.py --out DIR   # custom output dir (default scratch/preview)
```

Open the resulting `scratch/preview/dark_mode.svg` / `scratch/preview/light_mode.svg`.

## portrait.py arguments

```
--invert         invert the ramp (dark pixel -> dense glyph); use for light_mode.svg
--crop WxH+X+Y   ImageMagick crop, applied before the resize
--bc BxC         brightness-contrast, e.g. 0x10
--width N        grid columns (default 74, computed to clear the text column)
--height N       grid rows (default 50)
--inject SVG...  write between the portrait markers in these files
```
