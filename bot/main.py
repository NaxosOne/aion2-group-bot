"""Point d'entrée du bot : `python -m bot.main`."""

import discord
from discord.ext import commands

from . import config
from .db import Database
from .views import SignupView


class GroupBot(commands.Bot):
    def __init__(self):
        # Les intents par défaut suffisent : le bot n'utilise que des commandes
        # slash et des boutons, pas de lecture des messages des utilisateurs.
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.db = Database(config.DB_PATH)

    async def setup_hook(self):
        await self.db.connect()

        # Ré-enregistre la vue persistante pour que les boutons des sorties
        # déjà publiées fonctionnent encore après un redémarrage.
        self.add_view(SignupView())

        await self.load_extension("bot.cogs.groups")
        await self.load_extension("bot.cogs.profiles")
        await self.load_extension("bot.cogs.legion")

        if config.GUILD_ID:
            # Sync sur un seul serveur : les commandes apparaissent tout de suite.
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Connecté en tant que {self.user} (id {self.user.id})")

    async def close(self):
        await self.db.close()
        await super().close()


def main():
    if not config.TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN manquant : copie .env.example vers .env et "
            "renseigne le token du bot (voir README.md)."
        )
    GroupBot().run(config.TOKEN)


if __name__ == "__main__":
    main()
