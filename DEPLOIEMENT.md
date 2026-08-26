# Héberger le bot 24h/24

Un bot Discord doit rester connecté en permanence : il lui faut une machine qui
ne s'éteint jamais. État des lieux honnête en 2026 : le « gratuit illimité sans
carte bancaire » a quasiment disparu. Voici les options, de la plus simple à la
plus robuste.

## Option 0 — Ton PC (développement uniquement)

Gratuit et immédiat : `python -m bot.main` et le bot est en ligne... tant que le
PC est allumé. Parfait pour développer et tester, pas pour la guilde.

## Option 1 — Railway (le plus simple, ~2-3 €/mois)

[Railway](https://railway.com) déploie automatiquement depuis GitHub : tu
connectes le dépôt, il détecte le `Dockerfile`, et chaque `git push` redéploie.

1. Crée un compte sur railway.com (connexion GitHub).
2. **New Project → Deploy from GitHub repo** → choisis `discord-group-creator`.
3. Dans **Variables**, ajoute `DISCORD_TOKEN` (et `GUILD_ID`, `TIMEZONE`...).
4. Ajoute un **Volume** monté sur `/app/data` pour que la base SQLite survive
   aux redéploiements.

Le plan d'essai offre un petit crédit, ensuite un bot léger coûte environ
2-3 $/mois. C'est l'option « ça marche tout seul ».

## Option 2 — Oracle Cloud Free Tier (vraiment gratuit, plus technique)

Oracle offre une machine virtuelle ARM « Always Free » (jusqu'à 4 CPU / 24 Go
de RAM) — largement de quoi faire tourner le bot pour 0 €. En contrepartie :
création de compte avec carte bancaire (non débitée), et c'est un vrai serveur
Linux à administrer.

1. Crée un compte sur <https://www.oracle.com/cloud/free/> et lance une
   instance **Ampere A1** (Ubuntu).
2. Connecte-toi en SSH, puis :

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/NaxosOne/discord-group-creator.git
cd discord-group-creator
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env   # colle ton token
```

3. Crée un service systemd pour le démarrage automatique
   (`sudo nano /etc/systemd/system/aion2bot.service`) :

```ini
[Unit]
Description=Bot Discord Aion 2
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/discord-group-creator
ExecStart=/home/ubuntu/discord-group-creator/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now aion2bot
journalctl -u aion2bot -f     # voir les logs
```

## Option 3 — Un VPS classique (~4 €/mois)

Hetzner, OVH, Contabo... : mêmes étapes que l'option 2 (c'est aussi un serveur
Linux), sans les particularités d'Oracle. Simple, fiable, pas gratuit.

## À éviter pour un bot

- **Render (plan gratuit)** : les services web gratuits s'endorment après 15
  minutes d'inactivité, ce qui déconnecte le bot. Leur offre « background
  worker » qui conviendrait est payante.
- **Fly.io** : plus d'offre gratuite pour les nouveaux comptes.
- **Replit/« uptime robots »** : bricolages instables, à fuir pour un bot de
  guilde qui doit être fiable le soir de raid.

## Dans tous les cas

- Le fichier `data/bot.db` contient toutes les sorties : sur une plateforme à
  conteneurs, monte un volume persistant sur `/app/data`, sinon tout est perdu
  à chaque redéploiement.
- Ne mets **jamais** le token dans le code ou sur GitHub : toujours en variable
  d'environnement (fichier `.env` local, « Variables » chez l'hébergeur).
