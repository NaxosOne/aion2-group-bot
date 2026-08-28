"""Reporting unexpected errors back to the user.

Discord shows "the application did not respond" whenever an interaction gets
no answer within three seconds — an unhandled exception looks exactly like
that to a member. Every entry point (commands, buttons, forms) routes its
failures here so the user always gets an answer and we always get a log line.
"""

import logging
import traceback

import discord

from . import i18n

log = logging.getLogger("kisk")


def _detail(error: Exception) -> str:
    """The error's type and message, short enough to fit in a chat reply.

    Naming the failure lets whoever hit it report something useful without
    reading the server logs.
    """
    text = f"{type(error).__name__}: {error}".strip()
    if len(text) > 300:
        text = text[:300] + "…"
    return text


async def report_error(interaction: discord.Interaction, error: Exception, where: str):
    log.error("Error on %s:\n%s", where, "".join(traceback.format_exception(error)))
    # Best-effort language: this runs inside the error path, so a failure to
    # read the setting must never mask the original error.
    try:
        lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
    except Exception:
        lang = i18n.DEFAULT
    message = f"{i18n.t('common.error', lang)}\n```\n{_detail(error)}\n```"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
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
