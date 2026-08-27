<p align="center">
  <img src="assets/banner.png" alt="Kisk — your legion's rally point" width="720">
</p>

# Kisk — Aion 2 party bot

🇫🇷 [Version française](README.fr.md)

**Kisk** is a Discord bot to organise parties for the launch of Aion 2:
dungeons, PvP runs, abyss farming. One command creates a call, and everyone
signs up in one click by picking their role (🛡️ Tank, 💚 Heal, 🗡️ DPS).
Like the in-game kisk, it's the rally point you drop before the fight.

## Features

- **`/event`**: creates a group call with a title, type (🏰 Dungeon, 🐉 Raid,
  🚩 Battleground, ⚔️ PvP, 🌀 Rift, 🌌 Abyss, 🎲 Other), schedule and description.
- **Three party setups**:
  - **Party of 5**: 1 tank / 1 heal / 3 DPS (the classic dungeon comp);
  - **Party of 10**: 2 tanks / 2 heals / 6 DPS (raids, battlegrounds);
  - **Open**: first come, first served, any roles (great for abyss farming),
    with an adjustable size (2 to 25 slots).
- **One-click sign-up buttons**: click your role, the display updates
  instantly. Switch roles or leave at any time.
- **Waitlist**: when it's full, you're queued up; if a spot opens, the first
  compatible player is **promoted and pinged automatically**.
- **Smart schedules**: type `21:00`, `9pm`, `tomorrow 20:30` or `30/08 21:00`
  (day/month) — the time is then shown in every player's own timezone
  (Discord timestamp magic). French input (`demain 21h`) works too.
- **Automatic reminders**: 15 minutes before start (configurable), the bot
  pings the party in the channel.
- **`/events`**: list of upcoming events with clickable links.
- **Cancellation**: the creator (or a moderator) can cancel; everyone signed
  up is notified.
- **Profiles**: `/profile set` registers your main and your alt (name, class,
  role); your class shows up next to your name in parties.
  `/profile show` and `/roster` to browse.
- **Absences**: `/away start: 30/08 until: 05/09` tells the legion,
  `/absences` lists who's missing, `/back` for an early return.
- **Announcements**: `/announce` (moderators) opens a form and publishes a
  formatted announcement, with an optional role ping.
- **Polls**: `/vote question: option1: option2: ...` (up to 5 options) with
  buttons and live results; the author or a moderator can close it.
- **Weekly availability**: `/availability post` publishes a Monday→Sunday
  board where everyone ticks their play evenings; `/availability weekly`
  re-posts it automatically every week in the chosen channel.
- **"Done ✅" button**: closes an event with a GG to the party and archives
  the announcement.
- **Welcoming newcomers**: `/welcome` (moderators) — the bot greets new
  members with the how-to.
- **Bot status**: the next event shows up in its Discord status
  ("Playing 🏰 Fire Temple — tomorrow 21:00").
- **Persistence**: everything is stored in SQLite — buttons keep working
  even if the bot restarts.

## How does a Discord bot work? (the basics)

1. You create an **application** on the Discord developer portal; it contains
   a **bot** with a **token** (its password).
2. Your program (this repo) connects to Discord with that token and stays
   online permanently: that's why it needs to be hosted somewhere.
3. It registers **slash commands** (`/event`...); when someone uses them or
   clicks a button, Discord sends the bot an "interaction", and the bot
   responds (here: by publishing or editing the party message).

## Step-by-step setup

### 1. Create the bot on the Discord portal

1. Go to <https://discord.com/developers/applications> → **New Application**,
   name it "Kisk". Set the avatar (`assets/avatar.png`) and banner
   (`assets/banner.png`) in **General Information** and in the **Bot** tab.
2. **Bot** tab → **Reset Token** → copy the token somewhere safe.
   ⚠️ **Never share this token** (anyone who has it controls your bot). If it
   leaks, come back here and hit "Reset Token".
3. Still in the **Bot** tab, enable **SERVER MEMBERS INTENT** (needed to
   greet new members). The two other privileged intents stay disabled.
4. **Installation** tab (or OAuth2 → URL Generator): tick the `bot` and
   `applications.commands` *scopes*, and the **Send Messages**,
   **Embed Links** and **Read Message History** permissions. Open the
   generated URL in your browser and invite the bot to your server.

### 2. Run the bot on your PC (for testing)

You need Python 3.11 or newer (<https://www.python.org/downloads/>).

```bash
git clone https://github.com/NaxosOne/discord-group-creator.git
cd discord-group-creator

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# Edit .env: paste your DISCORD_TOKEN, and set your GUILD_ID so the
# commands appear on your server immediately.

python -m bot.main
```

Once you see `Logged in as ...`, type `/event` on your server. 🎉

### 3. Host it 24/7

See **[DEPLOYMENT.md](DEPLOYMENT.md)**: the free or nearly-free options
(Oracle Cloud, Railway...), with detailed steps.

## Usage

```
/event title: Fire Temple HM  type: Dungeon       comp: Party of 5   when: tomorrow 21:00
/event title: Evening BG      type: Battleground  comp: Party of 10  when: 9pm
/event title: Abyss farming   type: Abyss         comp: Open         size: 8
/events                   → the upcoming events

/profile set character: Main  name: Kratos  class: Templar  role: Tank
/profile show [member]    → a member's profile
/roster                   → every character in the legion

/away start: 30/08 until: 05/09 reason: holidays
/absences                 → who's away or about to be
/back                     → early return

/announce [ping: @role]   → formatted announcement (moderators)

/vote question: What tonight? option1: Dungeon option2: PvP option3: Nothing
/availability post        → this week's availability board (Mon→Sun buttons)
/availability weekly      → re-post it here every week (moderators)
/welcome                  → greet newcomers in this channel (moderators)
```

The classes suggested by `/profile` are just suggestions (free text): the
list lives in `bot/cogs/profiles.py` (`AION_CLASSES`) — update it there once
the final Aion 2 class names are known.

## Project layout

```
assets/                Avatar and banner (PNG + SVG sources)
bot/
  main.py              Entry point: connection, command sync
  config.py            Reads .env (token, timezone, reminders...)
  db.py                SQLite storage (events, sign-ups, profiles, absences...)
  logic.py             Party / waitlist split (pure, tested)
  embeds.py            Builds the announcement message
  views.py             The buttons and their actions
  cogs/groups.py       /event, /events, reminders and bot status
  cogs/profiles.py     /profile (main + alt) and /roster
  cogs/legion.py       /away, /absences, /back, /announce, /welcome
  cogs/polls.py        /vote and /availability (weekly auto-post)
  utils/time_parse.py  "tomorrow 9pm" -> real date (pure, tested)
tests/                 python -m tests.test_logic ; python -m tests.test_time_parse
```

## Ideas for later

- **Ping a Discord role** on event creation (`@Aion2` to notify members);
- **Automatic thread** per event to chat without flooding the channel;
- **Aion 2 class picker** at sign-up time (dropdown menu);
- **Attendance confirmation**: a "Confirm" button the day before;
- **Recurring events** ("every Tuesday 21:00");
- **Multi-party events** for sieges: one call filling several parties;
- **Temporary voice channel** created when the event starts;
- **Calendar export** (.ics) to see events in your own agenda.

Shelved for now (chill-guild spirit), noted just in case: loot roll
(`/roll`), birthdays, screenshot hall of fame, DKP and attendance stats.
