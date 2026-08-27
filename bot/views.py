"""The buttons under an event message (Tank / Heal / DPS / Leave / Done / Cancel).

The view is "persistent": thanks to fixed custom_ids, the buttons keep
working even after a bot restart (it is re-registered at startup in main.py).
The custom_ids themselves are kept from earlier versions so already
published messages stay clickable.
"""

import time

import discord

from . import config
from .embeds import ROLE_EMOJI, ROLE_LABEL, build_event_embed
from .logic import assign


class SignupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ----- Sign-up buttons -----

    @discord.ui.button(
        label="Tank", emoji=config.EMOJI_TANK, style=discord.ButtonStyle.primary,
        custom_id="aion2:tank",
    )
    async def tank_button(self, interaction: discord.Interaction, _):
        await self._join(interaction, "tank")

    @discord.ui.button(
        label="Heal", emoji=config.EMOJI_HEAL, style=discord.ButtonStyle.success,
        custom_id="aion2:heal",
    )
    async def heal_button(self, interaction: discord.Interaction, _):
        await self._join(interaction, "heal")

    @discord.ui.button(
        label="DPS", emoji=config.EMOJI_DPS, style=discord.ButtonStyle.danger,
        custom_id="aion2:dps",
    )
    async def dps_button(self, interaction: discord.Interaction, _):
        await self._join(interaction, "dps")

    @discord.ui.button(
        label="Leave", emoji="🚪", style=discord.ButtonStyle.secondary,
        custom_id="aion2:leave", row=1,
    )
    async def leave_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        event = await self._open_event(interaction)
        if event is None:
            return

        party_before, _ = assign(
            event["compo"], event["size"], await db.get_signups(event["message_id"])
        )
        removed = await db.remove_signup(event["message_id"], interaction.user.id)
        if not removed:
            await interaction.response.send_message(
                "You're not signed up for this event.", ephemeral=True
            )
            return

        await self._refresh(interaction, event)
        await interaction.followup.send("You've left the event. 👋", ephemeral=True)
        await self._announce_promoted(interaction, event, party_before)

    @discord.ui.button(
        label="Done", emoji="✅", style=discord.ButtonStyle.success,
        custom_id="aion2:done", row=1,
    )
    async def done_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        event = await self._open_event(interaction)
        if event is None:
            return

        is_creator = interaction.user.id == event["creator_id"]
        is_mod = interaction.user.guild_permissions.manage_messages
        if not (is_creator or is_mod):
            await interaction.response.send_message(
                "Only the event creator (or a moderator) can close it.",
                ephemeral=True,
            )
            return

        await db.set_status(event["message_id"], "done")
        event = await db.get_event(event["message_id"])
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes)
        await interaction.response.edit_message(embed=embed, view=None)

        party, _ = assign(event["compo"], event["size"], signups)
        mentions = " ".join(f"<@{s['user_id']}>" for s in party)
        await interaction.followup.send(
            f"🎉 **{event['title']}** completed!" + (f" GG {mentions}" if mentions else "")
        )

    @discord.ui.button(
        label="Cancel event", emoji="🗑️", style=discord.ButtonStyle.secondary,
        custom_id="aion2:cancel", row=1,
    )
    async def cancel_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        event = await self._open_event(interaction)
        if event is None:
            return

        is_creator = interaction.user.id == event["creator_id"]
        is_mod = interaction.user.guild_permissions.manage_messages
        if not (is_creator or is_mod):
            await interaction.response.send_message(
                "Only the event creator (or a moderator) can cancel it.",
                ephemeral=True,
            )
            return

        await db.set_status(event["message_id"], "cancelled")
        event = await db.get_event(event["message_id"])
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes)
        await interaction.response.edit_message(embed=embed, view=None)

        party, waitlist = assign(event["compo"], event["size"], signups)
        mentions = " ".join(f"<@{s['user_id']}>" for s in party + waitlist)
        await interaction.followup.send(
            f"❌ **{event['title']}** was cancelled by {interaction.user.mention}."
            + (f"\n{mentions}" if mentions else "")
        )

    # ----- Shared machinery -----

    async def _join(self, interaction: discord.Interaction, role: str):
        db = interaction.client.db
        event = await self._open_event(interaction)
        if event is None:
            return

        existing = await db.get_signup(event["message_id"], interaction.user.id)
        if existing and existing["role"] == role:
            await interaction.response.send_message(
                f"You're already signed up as {ROLE_EMOJI[role]} **{ROLE_LABEL[role]}**.",
                ephemeral=True,
            )
            return

        party_before, _ = assign(
            event["compo"], event["size"], await db.get_signups(event["message_id"])
        )
        await db.upsert_signup(
            event["message_id"],
            interaction.user.id,
            interaction.user.display_name,
            role,
            time.time(),
        )

        signups = await self._refresh(interaction, event)
        party, waitlist = assign(event["compo"], event["size"], signups)
        if any(s["user_id"] == interaction.user.id for s in party):
            message = f"You're in as {ROLE_EMOJI[role]} **{ROLE_LABEL[role]}**! ✅"
        else:
            position = next(
                i for i, s in enumerate(waitlist, start=1)
                if s["user_id"] == interaction.user.id
            )
            message = (
                f"It's full for now: you're on the **waitlist** "
                f"(position {position}) as {ROLE_EMOJI[role]} {ROLE_LABEL[role]}. "
                f"You'll be moved in automatically if a spot opens up. ⏳"
            )
        await interaction.followup.send(message, ephemeral=True)
        await self._announce_promoted(interaction, event, party_before)

    async def _open_event(self, interaction: discord.Interaction):
        """Finds the event tied to the clicked message, if it's still open."""
        event = await interaction.client.db.get_event(interaction.message.id)
        if event is None:
            await interaction.response.send_message(
                "I can't find this event any more (database reset?).",
                ephemeral=True,
            )
            return None
        if event["status"] != "open":
            message = (
                "This event is already completed. ✅"
                if event["status"] == "done"
                else "This event was cancelled."
            )
            await interaction.response.send_message(message, ephemeral=True)
            return None
        return event

    async def _refresh(self, interaction: discord.Interaction, event) -> list:
        """Updates the message's embed and returns the fresh sign-ups."""
        db = interaction.client.db
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes)
        await interaction.response.edit_message(embed=embed, view=self)
        return signups

    async def _announce_promoted(self, interaction, event, party_before: list):
        """Publicly notifies players promoted from the waitlist to the party."""
        signups = await interaction.client.db.get_signups(event["message_id"])
        party, _ = assign(event["compo"], event["size"], signups)
        ids_before = {s["user_id"] for s in party_before}
        promoted = [
            s for s in party
            if s["user_id"] not in ids_before and s["user_id"] != interaction.user.id
        ]
        if promoted:
            mentions = " ".join(f"<@{s['user_id']}>" for s in promoted)
            await interaction.followup.send(
                f"📣 {mentions}: a spot opened up, you're in the party for "
                f"**{event['title']}**!"
            )
