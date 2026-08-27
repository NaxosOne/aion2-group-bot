"""Reporting unexpected errors back to the user.

Discord shows "the application did not respond" whenever an interaction gets
no answer within three seconds — an unhandled exception looks exactly like
that to a member. Every entry point (commands, buttons, forms) routes its
failures here so the user always gets an answer and we always get a log line.
"""

import logging
import traceback

import discord

log = logging.getLogger("kisk")

MESSAGE = "Something went wrong on my side. The error has been logged. 🛠️"


async def report_error(interaction: discord.Interaction, error: Exception, where: str):
    log.error("Error on %s:\n%s", where, "".join(traceback.format_exception(error)))
    try:
        if interaction.response.is_done():
            await interaction.followup.send(MESSAGE, ephemeral=True)
        else:
            await interaction.response.send_message(MESSAGE, ephemeral=True)
    except discord.HTTPException:
        pass  # interaction already expired: nothing left to answer with


class ModalErrorMixin:
    """Mixed into every pop-up form: a form that fails silently would show
    "the application did not respond" to the member."""

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await report_error(interaction, error, f"form {type(self).__name__}")


class ViewErrorMixin:
    """Same safety net for the buttons of a view."""

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        await report_error(interaction, error, f"button {item.custom_id}")
