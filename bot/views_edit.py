"""The modal that edits a posted event: title, schedule and description."""

import time

import discord

from . import config, i18n
from .errors import ModalErrorMixin
from .logic import assign
from .utils.mentions import join_mentions
from .utils.time_parse import (
    ParseError,
    format_when_for_edit,
    parse_when,
    should_rearm_after_reschedule,
)
from .views_common import refresh_event_message


class EventEditModal(ModalErrorMixin, discord.ui.Modal):
    """Edit a posted event's text fields: title, schedule and description.

    Type, composition and size stay fixed (a Discord modal holds text inputs
    only). The schedule field is prefilled so submitting it unchanged keeps the
    same time; clearing it drops the schedule. A change to the time re-arms the
    reminder / RSVP prompt and pings the party.
    """

    def __init__(self, event, lang: str = "en"):
        super().__init__(title=i18n.t("signup.edit_modal_title", lang)[:45])
        self.event = event
        self.lang = lang

        self.event_title = discord.ui.TextInput(
            label=i18n.t("signup.edit_field_title", lang),
            default=event["title"],
            max_length=100,
        )
        self.add_item(self.event_title)

        self.when = discord.ui.TextInput(
            label=i18n.t("signup.edit_field_when", lang),
            placeholder=i18n.t("signup.edit_field_when_ph", lang),
            default=format_when_for_edit(event["starts_at"], config.TIMEZONE),
            required=False,
            max_length=30,
        )
        self.add_item(self.when)

        self.description = discord.ui.TextInput(
            label=i18n.t("signup.edit_field_description", lang),
            style=discord.TextStyle.paragraph,
            default=event["description"] or "",
            required=False,
            max_length=500,
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        # The event may have been closed or cancelled while the modal was open.
        event = await db.get_event(self.event["message_id"])
        if event is None or event["status"] != "open":
            await interaction.response.send_message(
                i18n.t("signup.edit_gone", self.lang), ephemeral=True
            )
            return

        starts_at = None
        if self.when.value.strip():
            try:
                starts_at = int(
                    parse_when(
                        self.when.value, config.TIMEZONE, lang=self.lang
                    ).timestamp()
                )
            except ParseError as err:
                await interaction.response.send_message(str(err), ephemeral=True)
                return

        rearm = should_rearm_after_reschedule(
            event["starts_at"], starts_at, int(time.time())
        )
        await db.update_event_details(
            event["message_id"],
            title=self.event_title.value.strip(),
            starts_at=starts_at,
            description=self.description.value.strip() or None,
            rearm_notifications=rearm,
        )

        fresh = await db.get_event(event["message_id"])
        await interaction.response.send_message(
            i18n.t("signup.edited", self.lang), ephemeral=True
        )
        await refresh_event_message(interaction.client, fresh)
        if starts_at != event["starts_at"]:
            await self._announce_reschedule(interaction, fresh, starts_at)

    async def _announce_reschedule(self, interaction, event, starts_at):
        signups = await interaction.client.db.get_signups(event["message_id"])
        party, waitlist = assign(event["compo"], event["size"], signups)
        recipients = party + waitlist
        if not recipients:
            return
        when = (
            f"<t:{starts_at}:F>"
            if starts_at
            else i18n.t("signup.edit_when_cleared", self.lang)
        )
        mentions = join_mentions(s["user_id"] for s in recipients)
        channel = interaction.client.get_channel(event["channel_id"])
        if channel is None:
            channel = await interaction.client.fetch_channel(event["channel_id"])
        await channel.send(
            i18n.t(
                "signup.rescheduled",
                self.lang,
                title=event["title"],
                when=when,
                mentions=mentions,
            ),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
