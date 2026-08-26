# Hosting the bot 24/7

🇫🇷 [Version française](DEPLOYMENT.fr.md)

A Discord bot must stay connected at all times: it needs a machine that
never turns off. Honest state of play in 2026: "unlimited free with no
credit card" has all but disappeared. Here are the options, from simplest
to most robust.

## Option 0 — Your PC (development only)

Free and instant: `python -m bot.main` and the bot is online... as long as
the PC is on. Great for developing and testing, not for the guild.

## Option 1 — Railway (simplest, ~$2-3/month)

[Railway](https://railway.com) deploys straight from GitHub: connect the
repo, it detects the `Dockerfile`, and every `git push` redeploys.

1. Create an account on railway.com (GitHub sign-in).
2. **New Project → Deploy from GitHub repo** → pick `discord-group-creator`.
3. Under **Variables**, add `DISCORD_TOKEN` (and `GUILD_ID`, `TIMEZONE`...).
4. Add a **Volume** mounted on `/app/data` so the SQLite database survives
   redeployments.

The trial plan gives a small credit; after that a light bot costs about
$2-3/month. This is the "it just works" option.

## Option 2 — Oracle Cloud Free Tier (actually free, more technical)

Oracle offers an "Always Free" ARM virtual machine (up to 4 CPUs / 24 GB
RAM) — plenty to run this bot for $0. The trade-offs: account creation
requires a credit card (not charged), and it's a real Linux server to
administer.

1. Create an account at <https://www.oracle.com/cloud/free/> and launch an
   **Ampere A1** instance (Ubuntu).
2. SSH in, then:

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/NaxosOne/discord-group-creator.git
cd discord-group-creator
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env   # paste your token
```

3. Create a systemd service so it starts automatically
   (`sudo nano /etc/systemd/system/aion2bot.service`):

```ini
[Unit]
Description=Aion 2 Discord bot
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
journalctl -u aion2bot -f     # watch the logs
```

## Option 3 — A classic VPS (~$5/month)

Hetzner, OVH, Contabo...: same steps as option 2 (it's also a Linux
server), without Oracle's quirks. Simple, reliable, not free.

## What to avoid for a bot

- **Render (free plan)**: free web services go to sleep after 15 minutes of
  inactivity, which knocks the bot offline. Their "background worker" tier
  that would fit is paid.
- **Fly.io**: no more free tier for new accounts.
- **Replit / "uptime robots"**: unstable hacks — avoid for a guild bot that
  must be reliable on raid night.

## In every case

- The `data/bot.db` file holds every event: on container platforms, mount a
  persistent volume on `/app/data`, or everything is lost on each redeploy.
- **Never** put the token in the code or on GitHub: always an environment
  variable (local `.env` file, "Variables" at your host).
