"""Looking for group (/lfg): a per-server pool of players who want a group.

A member signals they are looking for an activity in a given role; the pool is
shown on a persistent board (one per server, posted with /lfg board, like the
quick-actions panel). Entries expire on their own, and a background loop prunes
them and refreshes the board. Implements ROADMAP Phase 3 — LFG system.

Like every other button of the bot, the board buttons are persistent (fixed
custom_ids), so they keep working after a restart (re-registered in main.py).
"""

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config, i18n
from ..branding import brand
from ..embeds import ROLE_EMOJI, ROLE_LABEL
from ..errors import ViewErrorMixin
from ..logic import ROLES
from ..utils.lfg import (
    AVAILABLE_DURATIONS,
    DEFAULT_AVAILABLE,
    DEFAULT_DURATION,
    LFG_DURATIONS,
    active_entries,
    group_by_activity,
)
from ..utils.text import truncate_field

log = logging.getLogger(__name__)

# Keep the board comfortably under Discord's 6000-char embed ceiling by sharing
# a budget across the activity fields (see bot/embeds.py for the same guard).
EMBED_FIELD_BUDGET = 5000

_ACTIVITY_CHOICES = [
    app_commands.Choice(name=name, value=name) for name in config.ACTIVITIES
]
_ROLE_CHOICES = [
    app_commands.Choice(name=ROLE_LABEL[role], value=role) for role in ROLES
]
_DURATION_CHOICES = [
    app_commands.Choice(name=label, value=label) for label in LFG_DURATIONS
]
_AVAILABLE_DURATION_CHOICES = [
    app_commands.Choice(name=label, value=label) for label in AVAILABLE_DURATIONS
]
_ON_OFF_CHOICES = [
    app_commands.Choice(name="On", value="on"),
    app_commands.Choice(name="Off", value="off"),
]


def build_lfg_embed(pool: list, available: list, lang: str, now: int) -> discord.Embed:
    """The LFG board: who's available now, then the pool grouped by activity."""
    live_pool = active_entries(pool, now)
    live_available = active_entries(available, now)
    grouped = group_by_activity(live_pool, config.ACTIVITIES)

    embed = discord.Embed(
        title="🔎 " + i18n.t("lfg.title", lang),
        description=i18n.t("lfg.hint", lang),
        colour=discord.Colour.blurple(),
    )
    brand(embed)

    if not grouped and not live_available:
        embed.description += "\n\n" + i18n.t("lfg.empty", lang)
        return embed

    field_count = len(grouped) + (1 if live_available else 0)
    field_cap = min(1024, EMBED_FIELD_BUDGET // field_count)

    if live_available:
        mentions = " ".join(f"<@{row['user_id']}>" for row in live_available)
        embed.add_field(
            name=f"✋ {i18n.t('lfg.available_title', lang)} ({len(live_available)})",
            value=truncate_field(mentions, field_cap),
            inline=False,
        )

    for activity, members in grouped:
        emoji = config.EMOJI_ACTIVITY.get(activity, config.EMOJI_ACTIVITY["Other"])
        lines = []
        for entry in members:
            note = f" — {entry['note']}" if entry["note"] else ""
            lines.append(
                f"{ROLE_EMOJI[entry['role']]} <@{entry['user_id']}> "
                f"(⏳ <t:{entry['expires_at']}:R>){note}"
            )
        embed.add_field(
            name=f"{emoji} {activity} ({len(members)})",
            value=truncate_field("\n".join(lines), field_cap),
            inline=False,
        )
    embed.set_footer(
        text=i18n.t(
            "lfg.footer", lang, total=len(live_pool), available=len(live_available)
        )
    )
    return embed


async def refresh_lfg_board(client, guild_id: int, lang: str) -> None:
    """Redraws the guild's LFG board in place, if one has been posted."""
    stored = await client.db.get_lfg_board(guild_id)
    if stored is None:
        return
    channel_id, message_id = stored
    channel = client.get_channel(channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(channel_id)
        except discord.HTTPException:
            return
    now = int(time.time())
    pool = await client.db.get_lfg_pool(guild_id, now)
    available = await client.db.get_available(guild_id, now)
    embed = build_lfg_embed(pool, available, lang, now)
    try:
        await channel.get_partial_message(message_id).edit(
            embed=embed, view=LfgBoardView(lang)
        )
    except discord.HTTPException:
        pass  # message deleted or permissions revoked


class LfgActivitySelect(discord.ui.Select):
    """Dropdown of activities for the quick "I'm looking" flow."""

    def __init__(self, lang: str):
        super().__init__(
            placeholder=i18n.t("lfg.pick_activity", lang),
            row=0,
            options=[
                discord.SelectOption(label=name, emoji=config.EMOJI_ACTIVITY[name])
                for name in config.ACTIVITIES
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.activity = self.values[0]
        await interaction.response.defer()


class LfgRoleSelect(discord.ui.Select):
    """Dropdown of roles for the quick "I'm looking" flow."""

    def __init__(self, lang: str):
        super().__init__(
            placeholder=i18n.t("lfg.pick_role", lang),
            row=1,
            options=[
                discord.SelectOption(
                    label=ROLE_LABEL[role], value=role, emoji=ROLE_EMOJI[role]
                )
                for role in ROLES
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.role = self.values[0]
        await interaction.response.defer()


class LfgLookingView(ViewErrorMixin, discord.ui.View):
    """The private "I'm looking" step: pick an activity and a role, confirm.

    Short-lived and only visible to the member who clicked, so its state lives
    on the instance — nothing to persist across restarts. The free-text note is
    only offered on /lfg looking (a modal cannot host these dropdowns).
    """

    def __init__(self, lang: str):
        super().__init__(timeout=300)
        self.lang = lang
        self.activity: str | None = None
        self.role: str | None = None
        self.add_item(LfgActivitySelect(lang))
        self.add_item(LfgRoleSelect(lang))
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label is not None:
                child.label = i18n.t("lfg.btn_confirm", lang)

    @discord.ui.button(
        label="Confirm", emoji="✅", style=discord.ButtonStyle.success, row=2
    )
    async def confirm(self, interaction: discord.Interaction, _):
        if not self.activity or not self.role:
            await interaction.response.send_message(
                i18n.t("lfg.pick_both", self.lang), ephemeral=True
            )
            return
        db = interaction.client.db
        expires_at = int(time.time()) + LFG_DURATIONS[DEFAULT_DURATION]
        await db.set_lfg_looking(
            interaction.guild_id,
            interaction.user.id,
            self.activity,
            self.role,
            None,
            expires_at,
        )
        await refresh_lfg_board(interaction.client, interaction.guild_id, self.lang)
        await interaction.response.edit_message(
            content=i18n.t(
                "lfg.looking_added",
                self.lang,
                emoji=config.EMOJI_ACTIVITY[self.activity],
                activity=self.activity,
                role=ROLE_LABEL[self.role],
            ),
            embed=None,
            view=None,
        )


class LfgBoardView(ViewErrorMixin, discord.ui.View):
    """The persistent board buttons: signal, or stop, looking for a group."""

    _LABELS = {
        "lfg:looking": "lfg.btn_looking",
        "lfg:available": "lfg.btn_available",
        "lfg:stop": "lfg.btn_stop",
    }

    def __init__(self, lang: str = "en"):
        super().__init__(timeout=None)
        for child in self.children:
            key = self._LABELS.get(getattr(child, "custom_id", None))
            if key is not None:
                child.label = i18n.t(key, lang)

    @discord.ui.button(
        label="I'm looking",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="lfg:looking",
    )
    async def looking(self, interaction: discord.Interaction, _):
        lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
        await interaction.response.send_message(
            i18n.t("lfg.looking_prompt", lang),
            view=LfgLookingView(lang),
            ephemeral=True,
        )

    @discord.ui.button(
        label="I'm around now",
        emoji="✋",
        style=discord.ButtonStyle.success,
        custom_id="lfg:available",
    )
    async def available(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        now = int(time.time())
        expires_at = now + AVAILABLE_DURATIONS[DEFAULT_AVAILABLE]
        on = await db.toggle_available(
            interaction.guild_id, interaction.user.id, now, expires_at
        )
        await refresh_lfg_board(interaction.client, interaction.guild_id, lang)
        key = "lfg.available_on" if on else "lfg.available_off"
        await interaction.response.send_message(
            i18n.t(key, lang, duration=DEFAULT_AVAILABLE), ephemeral=True
        )

    @discord.ui.button(
        label="Stop looking",
        emoji="🛑",
        style=discord.ButtonStyle.secondary,
        custom_id="lfg:stop",
    )
    async def stop(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        removed = await db.remove_lfg(interaction.guild_id, interaction.user.id)
        await refresh_lfg_board(interaction.client, interaction.guild_id, lang)
        key = "lfg.stopped" if removed else "lfg.not_looking"
        await interaction.response.send_message(i18n.t(key, lang), ephemeral=True)


@app_commands.guild_only()
class Lfg(commands.Cog):
    """The /lfg command group and the pool-pruning background loop."""

    lfg = app_commands.Group(
        name="lfg", description="Looking for group", guild_only=True
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.prune_loop.start()

    async def cog_unload(self):
        self.prune_loop.cancel()

    @lfg.command(
        name="looking", description="Tell the server you're looking for a group"
    )
    @app_commands.describe(
        activity="What you want to play",
        role="The role you'll bring",
        note="Optional detail (e.g. 'need 1 for hardmode')",
        duration="How long to stay in the pool (default 3h)",
    )
    @app_commands.choices(
        activity=_ACTIVITY_CHOICES, role=_ROLE_CHOICES, duration=_DURATION_CHOICES
    )
    async def looking(
        self,
        interaction: discord.Interaction,
        activity: app_commands.Choice[str],
        role: app_commands.Choice[str],
        note: app_commands.Range[str, 1, 100] | None = None,
        duration: app_commands.Choice[str] | None = None,
    ):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        window = LFG_DURATIONS[duration.value if duration else DEFAULT_DURATION]
        expires_at = int(time.time()) + window
        await self.bot.db.set_lfg_looking(
            interaction.guild_id,
            interaction.user.id,
            activity.value,
            role.value,
            note.strip() if note else None,
            expires_at,
        )
        await refresh_lfg_board(self.bot, interaction.guild_id, lang)
        await interaction.response.send_message(
            i18n.t(
                "lfg.looking_added",
                lang,
                emoji=config.EMOJI_ACTIVITY[activity.value],
                activity=activity.value,
                role=ROLE_LABEL[role.value],
            ),
            ephemeral=True,
        )

    @lfg.command(name="stop", description="Stop looking (one activity, or all)")
    @app_commands.describe(activity="Leave empty to stop looking for everything")
    @app_commands.choices(activity=_ACTIVITY_CHOICES)
    async def stop(
        self,
        interaction: discord.Interaction,
        activity: app_commands.Choice[str] | None = None,
    ):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        removed = await self.bot.db.remove_lfg(
            interaction.guild_id,
            interaction.user.id,
            activity.value if activity else None,
        )
        await refresh_lfg_board(self.bot, interaction.guild_id, lang)
        key = "lfg.stopped" if removed else "lfg.not_looking"
        await interaction.response.send_message(i18n.t(key, lang), ephemeral=True)

    @lfg.command(
        name="available",
        description="Mark yourself available to play right now (or turn it off)",
    )
    @app_commands.describe(
        status="On to appear as available now, Off to clear it",
        duration="How long you stay available (default 2h)",
    )
    @app_commands.choices(status=_ON_OFF_CHOICES, duration=_AVAILABLE_DURATION_CHOICES)
    async def available(
        self,
        interaction: discord.Interaction,
        status: app_commands.Choice[str],
        duration: app_commands.Choice[str] | None = None,
    ):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        if status.value == "off":
            await self.bot.db.remove_available(
                interaction.guild_id, interaction.user.id
            )
            await refresh_lfg_board(self.bot, interaction.guild_id, lang)
            await interaction.response.send_message(
                i18n.t("lfg.available_off", lang), ephemeral=True
            )
            return
        window = duration.value if duration else DEFAULT_AVAILABLE
        expires_at = int(time.time()) + AVAILABLE_DURATIONS[window]
        await self.bot.db.set_available(
            interaction.guild_id, interaction.user.id, expires_at
        )
        await refresh_lfg_board(self.bot, interaction.guild_id, lang)
        await interaction.response.send_message(
            i18n.t("lfg.available_on", lang, duration=window), ephemeral=True
        )

    @lfg.command(
        name="board",
        description="Post the LFG board here, or refresh the existing one (moderators)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def board(self, interaction: discord.Interaction):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        now = int(time.time())
        pool = await db.get_lfg_pool(interaction.guild_id, now)
        available = await db.get_available(interaction.guild_id, now)
        embed = build_lfg_embed(pool, available, lang, now)

        # Refresh the remembered board in place, so re-running never leaves a
        # stale duplicate behind (mirrors /panel).
        stored = await db.get_lfg_board(interaction.guild_id)
        if stored is not None:
            channel_id, message_id = stored
            channel = self.bot.get_channel(channel_id)
            if channel is not None:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed, view=LfgBoardView(lang))
                    await interaction.response.send_message(
                        i18n.t("lfg.board_refreshed", lang, link=message.jump_url),
                        ephemeral=True,
                    )
                    return
                except discord.NotFound:
                    pass  # deleted: fall through and post a fresh one
                except discord.Forbidden:
                    await interaction.response.send_message(
                        i18n.t("lfg.board_forbidden", lang), ephemeral=True
                    )
                    return

        message = await interaction.channel.send(embed=embed, view=LfgBoardView(lang))
        await db.set_lfg_board(interaction.guild_id, interaction.channel_id, message.id)
        await interaction.response.send_message(
            i18n.t("lfg.board_posted", lang, link=message.jump_url), ephemeral=True
        )

    @tasks.loop(minutes=5)
    async def prune_loop(self):
        """Drops expired entries and refreshes the boards that changed."""
        now = int(time.time())
        pruned = await self.bot.db.prune_lfg(now)
        pruned += await self.bot.db.prune_available(now)
        if not pruned:
            return
        for row in await self.bot.db.guilds_with_lfg_board():
            guild = self.bot.get_guild(row["guild_id"])
            lang = await i18n.resolve_lang(self.bot.db, guild)
            await refresh_lfg_board(self.bot, row["guild_id"], lang)

    @prune_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Lfg(bot))
