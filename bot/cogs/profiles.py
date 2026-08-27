"""/profile commands and /roster: the legion's character directory (main + alt)."""

import discord
from discord import app_commands
from discord.ext import commands

from .. import config
from ..embeds import ROLE_EMOJI, ROLE_LABEL

# Class suggestions (inherited from Aion — free text is accepted: update this
# list in one place once the final Aion 2 class names are known).
AION_CLASSES = [
    "Gladiator",
    "Templar",
    "Assassin",
    "Ranger",
    "Sorcerer",
    "Spiritmaster",
    "Cleric",
    "Chanter",
]

SLOT_LABEL = {"main": "Main", "alt": "Alt"}


async def class_autocomplete(_: discord.Interaction, current: str):
    cur = current.lower()
    return [
        app_commands.Choice(name=c, value=c) for c in AION_CLASSES if cur in c.lower()
    ][:25]


def _character_line(p) -> str:
    """E.g. "🛡️ **Kratos** (⚔️ Templar)"."""
    emoji = config.CLASS_EMOJI.get(p["char_class"])
    char_class = f"{emoji} {p['char_class']}" if emoji else p["char_class"]
    return f"{ROLE_EMOJI[p['role']]} **{p['char_name']}** ({char_class})"


@app_commands.guild_only()
class Profile(commands.GroupCog, name="profile"):
    """Register and browse the members' characters."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="set", description="Register your main character or your alt")
    @app_commands.rename(char_class="class")
    @app_commands.describe(
        character="Main or alt?",
        name="The character's in-game name",
        char_class="Its class (suggestions offered, free text accepted)",
        role="Its party role",
    )
    @app_commands.choices(
        character=[
            app_commands.Choice(name="Main", value="main"),
            app_commands.Choice(name="Alt", value="alt"),
        ],
        role=[
            app_commands.Choice(name="🛡️ Tank", value="tank"),
            app_commands.Choice(name="💚 Heal", value="heal"),
            app_commands.Choice(name="🗡️ DPS", value="dps"),
        ],
    )
    @app_commands.autocomplete(char_class=class_autocomplete)
    async def set(
        self,
        interaction: discord.Interaction,
        character: app_commands.Choice[str],
        name: app_commands.Range[str, 1, 32],
        char_class: app_commands.Range[str, 1, 32],
        role: app_commands.Choice[str],
    ):
        await self.bot.db.set_profile(
            interaction.guild_id,
            interaction.user.id,
            character.value,
            name.strip(),
            char_class.strip(),
            role.value,
        )
        await interaction.response.send_message(
            f"{SLOT_LABEL[character.value]} saved: {ROLE_EMOJI[role.value]} "
            f"**{name.strip()}** ({char_class.strip()}, {ROLE_LABEL[role.value]}). "
            f"Your class will now show up in parties! ✅",
            ephemeral=True,
        )

    @app_commands.command(name="show", description="See a member's profile")
    @app_commands.describe(member="The member to look up (empty = you)")
    async def show(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ):
        target = member or interaction.user
        characters = await self.bot.db.get_profiles(interaction.guild_id, target.id)
        if not characters:
            who = (
                "You don't have"
                if target == interaction.user
                else f"{target.display_name} doesn't have"
            )
            await interaction.response.send_message(
                f"{who} a profile yet. Create one with `/profile set`!",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"👤 {target.display_name}'s profile",
            colour=discord.Colour.blurple(),
        )
        for p in characters:  # main first, then alt
            embed.add_field(
                name=SLOT_LABEL[p["slot"]], value=_character_line(p), inline=True
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="delete", description="Delete your profile (moderators can target a member)"
    )
    @app_commands.describe(
        character="Which character to remove (default: all)",
        member="Moderators only: whose profile to delete (default: yours)",
    )
    @app_commands.choices(
        character=[
            app_commands.Choice(name="Main", value="main"),
            app_commands.Choice(name="Alt", value="alt"),
            app_commands.Choice(name="All", value="all"),
        ],
    )
    async def delete(
        self,
        interaction: discord.Interaction,
        character: app_commands.Choice[str] | None = None,
        member: discord.Member | None = None,
    ):
        target = member or interaction.user
        if (
            target != interaction.user
            and not interaction.user.guild_permissions.manage_guild
        ):
            await interaction.response.send_message(
                "Only moderators can delete another member's profile.", ephemeral=True
            )
            return

        slot = None if character is None or character.value == "all" else character.value
        count = await self.bot.db.delete_profile(interaction.guild_id, target.id, slot)
        if count == 0:
            whose = (
                "You have"
                if target == interaction.user
                else f"{target.display_name} has"
            )
            await interaction.response.send_message(
                f"{whose} nothing to delete there.", ephemeral=True
            )
            return

        whose = "Your" if target == interaction.user else f"{target.display_name}'s"
        what = "profile" if slot is None else f"{SLOT_LABEL[slot]} character"
        await interaction.response.send_message(
            f"🗑️ {whose} {what} was deleted.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """When a member leaves (or is kicked/banned), forget their data."""
        if member.bot:
            return
        await self.bot.db.purge_member(member.guild.id, member.id)


@app_commands.guild_only()
class Roster(commands.Cog):
    """The /roster command, kept top-level for quick access."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roster", description="The legion's character roster")
    async def roster(self, interaction: discord.Interaction):
        characters = await self.bot.db.all_profiles(interaction.guild_id)
        if not characters:
            await interaction.response.send_message(
                "The roster is empty: add yourself with `/profile set`.",
                ephemeral=True,
            )
            return

        # Group main + alt per member (rows arrive sorted main first).
        by_member: dict[int, list] = {}
        for p in characters:
            by_member.setdefault(p["user_id"], []).append(p)

        lines = []
        for user_id, chars in by_member.items():
            line = f"• <@{user_id}>: {_character_line(chars[0])}"
            if len(chars) > 1:
                line += f" — alt: {_character_line(chars[1])}"
            lines.append(line)

        # Safety margin under Discord's 4096-character description limit.
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n…"

        embed = discord.Embed(
            title=f"📖 Legion roster ({len(by_member)} members)",
            description=text,
            colour=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
    await bot.add_cog(Roster(bot))
