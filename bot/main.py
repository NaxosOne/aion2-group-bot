"""Point d'entrée du bot : `python -m bot.main`."""

import discord
from discord.ext import commands

from . import config
from .cogs.polls import DispoView, VoteView
from .db import Database
from .views import SignupView


class GroupBot(commands.Bot):
    def __init__(self):
        # L'intent "members" (à activer sur le portail développeur) permet
        # d'accueillir les nouveaux ; le reste passe par commandes et boutons.
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(config.DB_PATH)

    async def setup_hook(self):
        await self.db.connect()

        # Ré-enregistre les vues persistantes pour que les boutons des messages
        # déjà publiés fonctionnent encore après un redémarrage.
        self.add_view(SignupView())
        self.add_view(VoteView())
        self.add_view(DispoView())

        await self.load_extension("bot.cogs.groups")
        await self.load_extension("bot.cogs.profiles")
        await self.load_extension("bot.cogs.legion")
        await self.load_extension("bot.cogs.polls")

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
    try:
        GroupBot().run(config.TOKEN)
    except discord.PrivilegedIntentsRequired:
        raise SystemExit(
            "Il manque un réglage sur le portail développeur Discord :\n"
            "ton application -> onglet Bot -> active « SERVER MEMBERS INTENT »\n"
            "(nécessaire pour accueillir les nouveaux membres), puis relance le bot."
        ) from None


if __name__ == "__main__":
    main()
