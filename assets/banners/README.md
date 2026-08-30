# Event banners

Original, per-event-type banners shown on event embeds (and the panel uses the
top-level `assets/banner.png`). One per activity type:

`dungeon` · `raid` · `battleground` · `pvp` · `rift` · `abyss` · `other`

The `.svg` files are the source. Discord embeds only display raster images, so
render them to `.png` and commit both:

```bash
pip install cairosvg
python scripts/render_banners.py
```

The bot references them by URL (`ASSET_BASE_URL/banners/<type>.png`), so the
PNGs must be publicly reachable at that base (see `bot/branding.py`). Until the
PNGs exist and are hosted, event embeds simply render without a banner.

To restyle a type, edit its `.svg` and re-run the script. To add a type, add the
SVG here and map it in `bot/branding.py` (`_ACTIVITY_SLUG`).
