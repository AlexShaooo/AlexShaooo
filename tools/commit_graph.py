#!/usr/bin/env python3
"""
Render the contribution line graph that sits where the Links section used to be
on the profile card: a thin grayscale interpolated curve drawn as an SVG <path>
(crisp, no ASCII row seams). The right axis is labeled with the max value and
"contribs" beneath it; the baseline is 0; month/day ticks run along the bottom.
Everything but the curve stays monospace text so the terminal look holds.

today.py fetches 12 monthly totals + tick labels and calls inject() to write the
output between the <!--graph:start--> / <!--graph:end--> markers that
build_cards.py leaves in each card. Geometry matches build_cards.py: the right
column starts at x=390 and its section rules reach ~x=1004.

Preview (writes both themes into scratch/, no commit touched):
    python tools/commit_graph.py            # fake sample data
    python tools/commit_graph.py --real     # live data (needs ACCESS_TOKEN, USER_NAME)
    python tools/commit_graph.py --out DIR   # custom output directory
"""
import math
import re

# Layout (aligned with tools/build_cards.py right column at x=390, rule edge ~1004).
X_LEFT = 390
X_AXIS_R = 958          # curve/axis right edge; leaves room for the y labels
YLAB_X = 966            # y-axis label left edge (clear of the curve)
Y_TOP = 468             # top of plot area (the peak reaches here)
Y_BASE = 512            # baseline (value 0)
TICK_Y = 528            # x-axis tick label baseline
YLAB_FS = 11            # y-axis value font size
UNIT_FS = 7             # "contribs" label, ~2/3 of YLAB_FS, to fit the margin

GRAPH_START, GRAPH_END = "<!--graph:start-->", "<!--graph:end-->"

# Per-theme colors. Dark: light stroke on the dark card. Light: dark stroke on white.
THEME = {
    True:  {"stroke": "#e8e8e6", "axis": "#3d444d", "muted": "#8b949e"},   # dark card
    False: {"stroke": "#24292f", "axis": "#d0d7de", "muted": "#57606a"},   # light card
}

# Sample data for previews (12 months, oldest -> newest) + month/day ticks.
SAMPLE_VALUES = [60, 45, 80, 120, 95, 70, 110, 140, 100, 75, 160, 190]
SAMPLE_TICKS = ["07/01", "09/01", "11/01", "01/01", "03/01", "05/01"]


def _mono_tangents(ys):
    """Fritsch-Carlson tangents for monotone cubic Hermite (dx == 1)."""
    n = len(ys)
    d = [ys[i + 1] - ys[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    return m


def _interp(ys, m, x):
    n = len(ys)
    if x <= 0:
        return ys[0]
    if x >= n - 1:
        return ys[-1]
    i = int(math.floor(x))
    t = x - i
    h00 = (1 + 2 * t) * (1 - t) ** 2
    h10 = t * (1 - t) ** 2
    h01 = t * t * (3 - 2 * t)
    h11 = t * t * (t - 1)
    return max(0.0, h00 * ys[i] + h10 * m[i] + h01 * ys[i + 1] + h11 * m[i + 1])


def _points(values, n_pts=160):
    """Monotone-cubic samples of `values` mapped to the plot rectangle."""
    m = _mono_tangents(values)
    mx = max(values) or 1
    pts = []
    for i in range(n_pts):
        xf = i / (n_pts - 1)
        v = _interp(values, m, xf * (len(values) - 1)) / mx
        x = X_LEFT + xf * (X_AXIS_R - X_LEFT)
        y = Y_BASE - v * (Y_BASE - Y_TOP)
        pts.append((round(x, 1), round(y, 1)))
    return pts, mx


def render_graph(values, ticks, dark=True):
    """Return SVG elements (path + axis + labels) for the contribution line graph.

    values : list of monthly contribution totals, oldest -> newest.
    ticks  : list of x-axis tick labels (e.g. "08/01"), spread at regular intervals.
    dark   : True for the dark card palette, False for the light card.

    The right axis is labeled with the max value and the word "contribs" beneath
    it (smaller, to fit the margin); the baseline is labeled 0.
    """
    if not values:
        return ""
    c = THEME[bool(dark)]
    pts, mx = _points(values)
    d = "M " + " L ".join(f"{x},{y}" for x, y in pts)

    out = [f'<line x1="{X_LEFT}" y1="{Y_BASE}" x2="{X_AXIS_R}" y2="{Y_BASE}" '
           f'stroke="{c["axis"]}" stroke-width="1"/>']
    out.append(f'<path d="{d}" fill="none" stroke="{c["stroke"]}" stroke-width="1.5" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')
    out.append(f'<text x="{YLAB_X}" y="{Y_TOP + 4}" font-size="{YLAB_FS}px" fill="{c["muted"]}">{mx:,}</text>')
    out.append(f'<text x="{YLAB_X}" y="{Y_TOP + 4 + UNIT_FS + 3}" font-size="{UNIT_FS}px" '
               f'fill="{c["muted"]}">contribs</text>')
    out.append(f'<text x="{YLAB_X}" y="{Y_BASE}" font-size="{YLAB_FS}px" fill="{c["muted"]}">0</text>')
    for i, t in enumerate(ticks):
        x = X_LEFT + (i / (len(ticks) - 1) if len(ticks) > 1 else 0) * (X_AXIS_R - X_LEFT)
        anchor = "start" if i == 0 else ("end" if i == len(ticks) - 1 else "middle")
        out.append(f'<text x="{round(x, 1)}" y="{TICK_Y}" font-size="10px" fill="{c["muted"]}" '
                   f'text-anchor="{anchor}">{t}</text>')
    return "\n".join(out)


def inject(svg, values, ticks, dark=True):
    """Return `svg` with the graph written between the markers. If the markers are
    absent, insert a fresh pair before </svg>. Idempotent either way."""
    payload = GRAPH_START + "\n" + render_graph(values, ticks, dark) + "\n" + GRAPH_END
    if GRAPH_START in svg:
        return re.sub(re.escape(GRAPH_START) + ".*?" + re.escape(GRAPH_END),
                      lambda _: payload, svg, flags=re.DOTALL)
    return svg.replace("</svg>", payload + "\n</svg>")


def _preview():
    """Write both themed cards with the graph injected into scratch/ for a look."""
    import argparse, os, datetime

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="Preview the contribution graph on both cards.")
    ap.add_argument("--real", action="store_true",
                    help="fetch live data via today.graph_monthly (needs ACCESS_TOKEN, USER_NAME)")
    ap.add_argument("--out", default=os.path.join(repo, "scratch", "preview"),
                    help="output directory (default scratch/preview)")
    a = ap.parse_args()

    if a.real:
        import sys
        sys.path.insert(0, repo)
        import today
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=365)
        values, ticks = today.graph_monthly(start.isoformat(), end.isoformat())
    else:
        values, ticks = SAMPLE_VALUES, SAMPLE_TICKS

    os.makedirs(a.out, exist_ok=True)
    for name in ("dark_mode.svg", "light_mode.svg"):
        src = os.path.join(repo, name)
        if not os.path.exists(src):
            print(f"(no {name}; skipping)")
            continue
        with open(src, encoding="utf-8") as f:
            svg = f.read()
        svg = inject(svg, values, ticks, dark="dark" in name)
        dst = os.path.join(a.out, name)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {os.path.relpath(dst, repo)}")


if __name__ == "__main__":
    _preview()
