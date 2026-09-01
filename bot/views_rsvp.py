"""The two buttons under an are-you-coming RSVP prompt."""

import discord

from . import i18n
from .embeds import build_rsvp_embed
from .errors import ViewErrorMixin
from .logic import assign


class RSVPView(ViewErrorMixin, discord.ui.View):
    """The two buttons under an 'are you coming?' prompt.

    Persistent (fixed custom_ids). The prompt is a separate message, so its
    buttons find their event through `events.rsvp_prompt_id`.
    """

    _LABELS = {
        "rsvp:yes": "rsvp.btn_coming",
        "rsvp:no": "rsvp.btn_not_coming",
    }

    def __init__(self, lang: str = "en"):
        super().__init__(timeout=None)
        for child in self.children:
            key = self._LABELS.get(getattr(child, "custom_id", None))
            if key is not None:
                child.label = i18n.t(key, lang)

    @discord.ui.button(
        label="I'm coming",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="rsvp:yes",
    )
    async def coming(self, interaction: discord.Interaction, _):
        await self._respond(interaction, "yes")

    @discord.ui.button(
        label="Can't make it",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        custom_id="rsvp:no",
    )
    async def not_coming(self, interaction: discord.Interaction, _):
        await self._respond(interaction, "no")

    async def _respond(self, interaction: discord.Interaction, status: str):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await db.get_event_by_rsvp_prompt(interaction.message.id)
        if event is None or event["status"] != "open":
            # The event was cancelled or completed after the prompt went out:
            # don't record a response for it.
            await interaction.response.send_message(
                i18n.t("rsvp.inactive", lang), ephemeral=True
            )
            return
        signups = await db.get_signups(event["message_id"])
        party, _waitlist = assign(event["compo"], event["size"], signups)
        if interaction.user.id not in {s["user_id"] for s in party}:
            await interaction.response.send_message(
                i18n.t("rsvp.sign_up_first", lang), ephemeral=True
            )
            return
        await db.set_rsvp(event["message_id"], interaction.user.id, status)
        rsvps = await db.get_rsvps(event["message_id"])
        embed = build_rsvp_embed(event, party, rsvps, lang)
        await interaction.response.edit_message(embed=embed, view=self)
