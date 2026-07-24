# Building the profile cards

The hero card is two side-by-side images (see the README), both under `assets/`:

- `assets/left_*.webp` — the portrait ↔ Warhol flip. Fixed art, baked once.
- `assets/*_mode.svg` — the GitHub stats + contribution graph. Refreshed weekly.

Run every command from the repo root. The source photo lives at
`reference/portrait.jpeg` (gitignored).

## Rebake the left animation (only when the photo or flip design changes)

```sh
python tools/build_cards.py                                                 # writes assets/*.svg
python tools/portrait.py reference/portrait.jpeg          --inject assets/left_dark.svg
python tools/portrait.py reference/portrait.jpeg --invert --inject assets/left_light.svg
python tools/warhol/face/regen_half.py                                     # only if the photo changed
python tools/warhol/build_warhol.py                                        # -> assets/left_*.webp
```

`build_cards.py` resets the portrait markers, so run the two portrait commands
after it. `build_warhol.py` needs Chrome (set `CHROME_PATH` if it is not found)
and `img2webp`; `SCALE=2` (default) is retina, `SCALE=1` is lighter.

## Refresh the stats (weekly, automatic)

`.github/workflows/build.yaml` runs this every Saturday and on every push to
`main`. To run it by hand:

```sh
python today.py            # needs ACCESS_TOKEN, USER_NAME (see docs/access_token.md)
```

It rewrites the `assets/*_mode.svg` stat panels (stat text + graph), with no
rendering. `build_cards.py` leaves placeholder zeros in those files, so run this
(or let CI run it) after a rebake.

## Preview the contribution graph

```sh
python tools/commit_graph.py            # sample data, both themes
python tools/commit_graph.py --real     # live data (needs ACCESS_TOKEN, USER_NAME)
python tools/commit_graph.py --out DIR  # output dir (default scratch/preview)
```

Writes `scratch/preview/dark_mode.svg` / `scratch/preview/light_mode.svg`.

## portrait.py options

```
--invert         invert the ramp (dark pixel -> dense glyph); use for the light card
--crop WxH+X+Y   ImageMagick crop, applied before the resize
--bc BxC         brightness-contrast, e.g. 0x10
--width N        grid columns (default computed to clear the seam)
--height N       grid rows (default 50)
--inject SVG...  write the portrait between the markers in these files
```
