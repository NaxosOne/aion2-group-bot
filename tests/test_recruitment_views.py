"""The application views must actually build.

A Discord Select fills a whole action row (width 5), so the Continue button
needs its own row — otherwise `add_item` raises `ValueError: item would not fit`
at runtime and the Apply button never responds. Regression: the button collided
with ClassSelect on row 0. These construct the views the way the cog does (inside
a running loop) so the layout is validated off Discord. Run: pytest
"""

import asyncio

import discord

from bot.cogs.recruitment import ApplicationModal, ApplicationSetupView


def test_setup_view_builds_without_row_overflow():
    async def build():
        return ApplicationSetupView(
            guild_id=1, guild_name="Kisk", ephemeral=True, lang="en"
        )

    view = asyncio.run(build())
    selects = [c for c in view.children if isinstance(c, discord.ui.Select)]
    buttons = [c for c in view.children if isinstance(c, discord.ui.Button)]
    assert len(selects) == 2
    assert len(buttons) == 1
    # The two selects each own a row; the Continue button sits on a different one.
    assert buttons[0].row not in {s.row for s in selects}


def test_application_modal_fits_discords_five_input_limit():
    async def build():
        return ApplicationModal(1, "Sorcerer", "dps", True, "en")

    modal = asyncio.run(build())
    inputs = [c for c in modal.children if isinstance(c, discord.ui.TextInput)]
    assert 1 <= len(inputs) <= 5
