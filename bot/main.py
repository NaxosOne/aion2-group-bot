"""Bot entry point: `python -m bot.main`."""

import discord
from discord.ext import commands

from . import config
from .cogs.polls import AvailabilityView, VoteView
from .db import Database
from .views import SignupView


class GroupBot(commands.Bot):
    def __init__(self):
        # The "members" intent (enabled on the developer portal) lets the bot
        # greet newcomers; everything else works through commands and buttons.
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(config.DB_PATH)

    async def setup_hook(self):
        await self.db.connect()

        # Re-register the persistent views so the buttons of already
        # published messages keep working after a restart.
        self.add_view(SignupView())
        self.add_view(VoteView())
        self.add_view(AvailabilityView())

        await self.load_extension("bot.cogs.groups")
        await self.load_extension("bot.cogs.profiles")
        await self.load_extension("bot.cogs.legion")
        await self.load_extension("bot.cogs.polls")

        if config.GUILD_ID:
            # Single-guild sync: the commands show up right away.
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
            except discord.Forbidden:
                raise SystemExit(
                    f"Discord refused to register the commands on server "
                    f"{config.GUILD_ID} (403 Missing Access). Two usual causes:\n"
                    "  1. The bot isn't a member of that server yet, or was invited "
                    "without the `applications.commands` scope\n"
                    "     -> re-invite it: developer portal > OAuth2 > URL Generator, "
                    "tick BOTH `bot` and `applications.commands`, open the URL.\n"
                    "  2. GUILD_ID in .env isn't your server's ID (right-click the "
                    "server name > Copy Server ID)."
                ) from None
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (id {self.user.id})")

    async def close(self):
        await self.db.close()
        await super().close()


def main():
    if not config.TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN is missing: copy .env.example to .env and fill in "
            "the bot token (see README.md)."
        )
    try:
        GroupBot().run(config.TOKEN)
    except discord.PrivilegedIntentsRequired:
        raise SystemExit(
            "A setting is missing on the Discord developer portal:\n"
            "your application -> Bot tab -> enable “SERVER MEMBERS INTENT”\n"
            "(needed to greet new members), then restart the bot."
        ) from None


if __name__ == "__main__":
    main()
