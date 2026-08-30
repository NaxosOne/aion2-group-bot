#!/usr/bin/env python3
"""Render the SVG banners in assets/banners/ to PNG for Discord embeds.

Discord embeds only display raster images, so the original SVG banners are
converted to PNG here. Run this whenever a banner SVG changes, then commit the
generated PNGs alongside them:

    pip install cairosvg
    python scripts/render_banners.py

cairosvg needs the Cairo library available on the system.
"""

from pathlib import Path

import cairosvg

BANNERS = Path(__file__).resolve().parent.parent / "assets" / "banners"
WIDTH, HEIGHT, SCALE = 1000, 300, 2  # 2x for a crisp result


def main() -> None:
    svgs = sorted(BANNERS.glob("*.svg"))
    if not svgs:
        print(f"No SVG banners found in {BANNERS}")
        return
    for svg in svgs:
        png = svg.with_suffix(".png")
        cairosvg.svg2png(
            url=str(svg),
            write_to=str(png),
            output_width=WIDTH * SCALE,
            output_height=HEIGHT * SCALE,
        )
        print(f"rendered {png.name}")


if __name__ == "__main__":
    main()
