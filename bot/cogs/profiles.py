"""/profile commands and /roster: the legion's character directory.

A member registers as many characters as they like (up to MAX_CHARACTERS);
exactly one of them is their main, and that is the one the bot falls back on
whenever a character isn't named explicitly.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import config, i18n
from ..embeds import ROLE_EMOJI, ROLE_LABEL
from ..branding import brand
from ..logic import MAX_CHARACTERS, ROLES
from ..utils.permissions import member_is_admin

# The playable classes, taken from the emoji configuration so that adding one
# (Fist Fighter, on release) is a single line in config.py. This is the whole
# list a member may pick from, in the slash command as in the onboarding form.
AION_CLASSES = list(config.CLASS_EMOJI)

# Discord caps a choice list at 25; the class list is far shorter, so it fits
# whole and needs no paging.
CLASS_CHOICES = [app_commands.Choice(name=name, value=name) for name in AION_CLASSES]

ALL_CHARACTERS = "all"

# How many absentees one pruning pass will confirm against the API. A member
# missing from the cache is almost always someone who left, but a guild whose
# cache never filled would put every profile in that bucket, so the work is
# spread over successive passes rather than fired off at once.
PRUNE_BATCH = 25

log = logging.getLogger(__name__)


def _target_of(interaction: discord.Interaction):
    """Whose characters a command is about: the `member` option, or the caller."""
    return getattr(interaction.namespace, "member", None) or interaction.user


async def _character_choices(interaction: discord.Interaction, current: str):
    target = _target_of(interaction)
    rows = await interaction.client.db.get_profiles(interaction.guild_id, target.id)
    cur = current.lower()
    return [
        app_commands.Choice(
            name=f"{'⭐ ' if row['is_main'] else ''}{row['char_name']} "
            f"({row['char_class']})"[:100],
            value=str(row["id"]),
        )
        for row in rows
        if cur in row["char_name"].lower()
    ]


async def character_autocomplete(interaction: discord.Interaction, current: str):
    return (await _character_choices(interaction, current))[:25]


async def deletable_autocomplete(interaction: discord.Interaction, current: str):
    """Same list, with "everything" as the first entry."""
    lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
    choices = [
        app_commands.Choice(
            name=i18n.t("profile.every_character", lang), value=ALL_CHARACTERS
        )
    ] + await _character_choices(interaction, current)
    return choices[:25]


async def resolve_character(db, guild_id: int, user_id: int, value: str):
    """The character an option refers to: the id an autocomplete choice
    carries, or a name typed out by hand. None when it matches nothing."""
    value = value.strip()
    if value.isdigit():
        row = await db.get_character(guild_id, user_id, int(value))
        if row is not None:
            return row
    for row in await db.get_profiles(guild_id, user_id):
        if row["char_name"].lower() == value.lower():
            return row
    return None


def _roster_order(entry) -> tuple:
    """Roster order: role first, then class, then character name.

    Keyed on the member's main, the character the roster line shows. Sorting
    by role first lines the roster up as tanks, then heals, then DPS — the
    question a legion actually asks it. A role that isn't one of the three
    (data from a future version) sorts last rather than raising.
    """
    main = entry[1][0]
    rank = ROLES.index(main["role"]) if main["role"] in ROLES else len(ROLES)
    return (rank, main["char_class"].lower(), main["char_name"].lower())


def character_line(row, *, star: bool = True) -> str:
    """E.g. "⭐ 💚 **Nami** (✨ Cleric)" — star, role icon, name, class."""
    emoji = config.CLASS_EMOJI.get(row["char_class"])
    char_class = f"{emoji} {row['char_class']}" if emoji else row["char_class"]
    prefix = "⭐ " if star and row["is_main"] else ""
    return f"{prefix}{ROLE_EMOJI[row['role']]} **{row['char_name']}** ({char_class})"


@app_commands.guild_only()
class Profile(commands.GroupCog, name="profile"):
    """Register and browse the members' characters."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    async def cog_load(self):
        self.prune_departed.start()

    async def cog_unload(self):
        self.prune_departed.cancel()

    @app_commands.command(
        name="set", description="Register one of your characters (or update it)"
    )
    @app_commands.rename(char_class="class")
    @app_commands.describe(
        name="The character's in-game name — an existing name updates it",
        char_class="Its class",
        role="Its party role",
        main="Make it your main character (your first one always is)",
    )
    @app_commands.choices(
        char_class=CLASS_CHOICES,
        role=[
            app_commands.Choice(name="🛡️ Tank", value="tank"),
            app_commands.Choice(name="💚 Heal", value="heal"),
            app_commands.Choice(name="🗡️ DPS", value="dps"),
        ],
    )
    async def set(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 1, 32],
        char_class: app_commands.Choice[str],
        role: app_commands.Choice[str],
        main: bool = False,
    ):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        name, char_class = name.strip(), char_class.value
        characters = await self.bot.db.get_profiles(
            interaction.guild_id, interaction.user.id
        )
        known = {row["char_name"].lower() for row in characters}
        if name.lower() not in known and len(characters) >= MAX_CHARACTERS:
            await interaction.response.send_message(
                i18n.t("profile.cap_reached", lang, max=MAX_CHARACTERS),
                ephemeral=True,
            )
            return

        await self.bot.db.add_character(
            interaction.guild_id, interaction.user.id,
            name, char_class, role.value, make_main=main,
        )
        was_first = not characters
        detail = (
            f"{ROLE_EMOJI[role.value]} **{name}** "
            f"({char_class}, {ROLE_LABEL[role.value]})"
        )
        note = i18n.t(
            "profile.note_main" if main or was_first else "profile.note_alt", lang
        )
        await interaction.response.send_message(
            i18n.t("profile.saved", lang, detail=detail, note=note), ephemeral=True
        )

    @app_commands.command(
        name="main", description="Choose which of your characters is your main"
    )
    @app_commands.describe(character="The character to promote")
    @app_commands.autocomplete(character=character_autocomplete)
    async def main(self, interaction: discord.Interaction, character: str):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        row = await resolve_character(
            self.bot.db, interaction.guild_id, interaction.user.id, character
        )
        if row is None:
            await interaction.response.send_message(
                i18n.t("profile.main_not_found", lang, character=character),
                ephemeral=True,
            )
            return

        await self.bot.db.set_main_character(
            interaction.guild_id, interaction.user.id, row["id"]
        )
        await interaction.response.send_message(
            i18n.t("profile.main_set", lang, name=row["char_name"]), ephemeral=True
        )

    @app_commands.command(name="show", description="See a member's profile")
    @app_commands.describe(member="The member to look up (empty = you)")
    async def show(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        target = member or interaction.user
        is_self = target == interaction.user
        characters = await self.bot.db.get_profiles(interaction.guild_id, target.id)
        if not characters:
            key = "profile.show_none_self" if is_self else "profile.show_none_other"
            await interaction.response.send_message(
                i18n.t(key, lang, name=target.display_name),
                ephemeral=True,
            )
            return

        title = (
            i18n.t("profile.show_title_self", lang)
            if is_self
            else i18n.t("profile.show_title_other", lang, name=target.display_name)
        )
        embed = discord.Embed(
            title=title,
            description="\n".join(character_line(row) for row in characters),
            colour=discord.Colour.blurple(),
        )
        brand(embed)
        embed.set_footer(
            text=i18n.t("profile.show_footer", lang, n=len(characters))
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="delete", description="Delete one character, or your whole profile"
    )
    @app_commands.describe(
        character="Which character to remove (empty = every one of them)",
        member="Moderators only: whose profile to delete (default: yours)",
    )
    @app_commands.autocomplete(character=deletable_autocomplete)
    async def delete(
        self,
        interaction: discord.Interaction,
        character: str | None = None,
        member: discord.Member | None = None,
    ):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        target = member or interaction.user
        is_self = target == interaction.user
        if not is_self and not await member_is_admin(self.bot.db, interaction.user):
            await interaction.response.send_message(
                i18n.t("profile.delete_mod_only", lang), ephemeral=True
            )
            return

        row = None
        if character is not None and character != ALL_CHARACTERS:
            row = await resolve_character(
                self.bot.db, interaction.guild_id, target.id, character
            )
            if row is None:
                key = (
                    "profile.delete_not_found_self"
                    if is_self
                    else "profile.delete_not_found_other"
                )
                await interaction.response.send_message(
                    i18n.t(
                        key, lang, name=target.display_name, character=character
                    ),
                    ephemeral=True,
                )
                return

        count = await self.bot.db.delete_profile(
            interaction.guild_id, target.id, None if row is None else row["id"]
        )
        if count == 0:
            key = "profile.delete_none_self" if is_self else "profile.delete_none_other"
            await interaction.response.send_message(
                i18n.t(key, lang, name=target.display_name), ephemeral=True
            )
            return

        if row is None:
            key = (
                "profile.deleted_self_profile"
                if is_self
                else "profile.deleted_other_profile"
            )
            message = i18n.t(
                key, lang, name=target.display_name, count=count
            )
        else:
            key = (
                "profile.deleted_self_char"
                if is_self
                else "profile.deleted_other_char"
            )
            message = i18n.t(
                key, lang, name=target.display_name, char=row["char_name"]
            )
        await interaction.response.send_message(message, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """When a member leaves (or is kicked/banned), forget their data."""
        if member.bot:
            return
        await self.bot.db.purge_member(member.guild.id, member.id)

    # ----- Catching the departures the listener missed -----

    @tasks.loop(hours=24)
    async def prune_departed(self):
        """Forgets members who left while the bot wasn't there to see it.

        on_member_remove only fires while the bot is connected, so anyone who
        left during a restart — or before that listener existed — keeps their
        characters on the roster forever. This runs once at startup and daily
        after that, and cleans them up.

        Deleting from a cold cache would wipe every profile on the server, so
        a member missing from it is never trusted: only an explicit 404 from
        the API counts as proof they are gone. Anything else (a network blip,
        a rate limit) leaves the profile alone for the next pass.
        """
        for guild in self.bot.guilds:
            checked = 0
            for user_id in await self.bot.db.profile_user_ids(guild.id):
                if guild.get_member(user_id) is not None:
                    continue
                if checked >= PRUNE_BATCH:
                    break
                checked += 1
                try:
                    await guild.fetch_member(user_id)
                except discord.NotFound:
                    await self.bot.db.purge_member(guild.id, user_id)
                    log.info(
                        "Purged %s: no longer a member of %s (%s)",
                        user_id, guild.name, guild.id,
                    )
                except discord.HTTPException:
                    continue

    @prune_departed.before_loop
    async def _wait_ready(self):
        # Guilds are chunked by the time the bot is ready (the members intent
        # is on), so the member cache is trustworthy for the cheap check.
        await self.bot.wait_until_ready()


@app_commands.guild_only()
class Roster(commands.Cog):
    """The /roster command, kept top-level for quick access."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roster", description="The legion's character roster")
    async def roster(self, interaction: discord.Interaction):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        characters = await self.bot.db.all_profiles(interaction.guild_id)
        if not characters:
            await interaction.response.send_message(
                i18n.t("roster.empty", lang),
                ephemeral=True,
            )
            return

        # Group each member's characters (rows arrive main first, then by
        # class, then by name).
        by_member: dict[int, list] = {}
        for row in characters:
            by_member.setdefault(row["user_id"], []).append(row)

        lines = []
        for user_id, chars in sorted(by_member.items(), key=_roster_order):
            line = f"• <@{user_id}>: {character_line(chars[0], star=False)}"
            if len(chars) > 1:
                alts = ", ".join(row["char_name"] for row in chars[1:])
                line += i18n.t("roster.alts", lang, alts=alts)
            lines.append(line)

        # Safety margin under Discord's 4096-character description limit.
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n…"

        embed = discord.Embed(
            title=i18n.t(
                "roster.title", lang,
                members=len(by_member), chars=len(characters),
            ),
            description=text,
            colour=discord.Colour.blurple(),
        )
        brand(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
    await bot.add_cog(Roster(bot))
