<p align="center">
  <img src="assets/banner.png" alt="Kisk — your legion's rally point" width="720">
</p>

<h1 align="center">Kisk</h1>

<p align="center">
  <strong>Your Aion 2 legion's rally point.</strong>
</p>

<p align="center">
  Organise groups, coordinate your legion, and be ready for the fight.
</p>

<p align="center">
  🇫🇷 <a href="README.fr.md">Version française</a>
</p>

---

## 🎯 What is Kisk?

**Kisk** is a Discord bot built to make organising an Aion 2 legion simple.

Create a group, pick a time, choose your role, and let Kisk handle the rest.

Whether you're organising a dungeon, raid, battleground, PvP run, rift, or abyss farming, Kisk gives your legion one place to coordinate:

* 👥 Who is coming?
* 🛡️ Which roles are still needed?
* 📅 When are we playing?
* ⏰ Who needs a reminder?
* 🪑 Who is waiting for a spot?
* 🏖️ Who is away?
* 📊 Who is available this week?

Like the in-game kisk, it's the **rally point you drop before the fight.**

> **Kisk starts with party organisation and aims to become the coordination layer for Aion 2 communities.**

---

## ✨ Features

### 🎯 Group & Event Management

* **`/event`** creates a group call with:

  * title
  * activity type
  * party composition
  * schedule
  * description
* Supported activity types:

  * 🏰 Dungeon
  * 🐉 Raid
  * 🚩 Battleground
  * ⚔️ PvP
  * 🌀 Rift
  * 🌌 Abyss
  * 🎲 Other

### 👥 Party compositions

Three built-in setups are available:

**Party of 5**

`1 Tank / 1 Heal / 3 DPS`

Classic dungeon composition.

**Party of 10**

`2 Tanks / 2 Heals / 6 DPS`

Designed for larger group content such as raids and battlegrounds.

**Open**

First come, first served.

Choose between **2 and 25 slots**, with no role restrictions. Perfect for abyss farming and other activities where composition is flexible.

### 🖱️ One-click sign-up

Players join directly from the event message.

Pick your role:

> 🛡️ Tank · 💚 Heal · 🗡️ DPS

The party updates immediately.

Players can:

* switch roles
* leave the event
* rejoin
* see the current composition

**Which character are you bringing?** Players who registered more than one
character get a private dropdown after picking their role, listing their
characters with their class icons. The party then shows the character by name,
led by its class icon, so the composition reads as a column of classes:

```text
🛡️ Tank (1/1)
• @Naxos — 🛡️ Kratos (Templar)

💚 Heal (1/1)
• @Ael — ✨ Nami (Cleric)

🗡️ DPS (3/3)
• @Kyo — 🗡️ Loki (Assassin)
• @Ryu — 🏹 Zed (Ranger)
• @Mia — 🔥 Ashe (Sorcerer)
```

Clicking the same role again swaps character without losing your place in the
queue. Players with a single character (or none) are signed up straight away,
exactly as before.

### 🪑 Smart waitlist

When an event is full, additional players are automatically placed on the waitlist.

When a spot opens:

1. Kisk finds the first compatible player.
2. Promotes them automatically.
3. Pings them in Discord.

No manual reshuffling required.

### ⏰ Smart schedules

Kisk understands natural time expressions such as:

```text
21:00
9pm
tomorrow 20:30
30/08 21:00
demain 21h
```

Event times are displayed using **Discord's timezone-aware timestamps**, so every player sees the correct local time.

### 🔔 Automatic reminders

Kisk automatically reminds the party before an event starts.

The reminder time is configurable.

Default:

**15 minutes before the event.**

### 🙋 RSVP — "are you coming?"

An hour before a scheduled event (configurable via `RSVP_MINUTES`), Kisk posts a
short **"are you coming?"** prompt that pings the party, with two buttons —
**I'm coming ✅** and **Can't make it ❌**. The prompt updates live with who has
confirmed, who can't make it, and who hasn't replied, so organisers can fill
empty spots before it starts.

Moderators can also trigger it on the spot with `/rsvp event: <message link or
ID>` — handy to ask right away instead of waiting for the automatic window.

Point RSVPs at their own channel with `/channels rsvp: #rsvp` so they don't
clutter the events channel; otherwise they land in the event's own channel.

### 📅 Event overview

Use:

```text
/events
```

to see upcoming activities with clickable links to their Discord messages.

### ❌ Cancellation

The event creator or a moderator can cancel an event.

Everyone who signed up is notified automatically.

### 👤 Player profiles

Players can register their characters with:

```text
/profile set name: Kratos class: Templar role: Tank
```

Each player can register **up to 10 characters** — a main and as many alts as
they actually play. Every character has a name, a class and a preferred role.

The first character registered becomes the **main**: it is the one shown by
default in party lists and on the roster. To change it:

```text
/profile main character: Loki
```

Re-running `/profile set` with a name that already exists updates that
character instead of creating a twin, so fixing a class or a role is one
command.

Use:

```text
/profile show [member]
/roster
```

to browse player information. To remove a character, or a whole profile:

```text
/profile delete character: Loki      → that one character
/profile delete                      → every character
```

Moderators can target another member with `member:`. Kisk also **cleans up
automatically** when someone leaves the server — all of their characters,
sign-ups, absences and availability marks are removed.

### 🏖️ Absences

Tell the legion when you're away:

```text
/away start: 30/08 until: 05/09 reason: holidays
```

Check who is currently away:

```text
/absences
```

Return early with:

```text
/back
```

### 📣 Announcements

Moderators can use:

```text
/announce
```

to create formatted announcements directly from Discord.

Optional role pings are supported.

### 📊 Polls

Create interactive polls with:

```text
/vote
```

Up to five options are supported.

Polls provide:

* Discord buttons
* live results
* controlled closing
* author/moderator management

### 📆 Weekly availability

Post a Monday → Sunday availability board:

```text
/availability post
```

Players can indicate which evenings they are available.

Moderators can configure automatic weekly reposting:

```text
/availability weekly
```

This gives organisers a quick overview of when the legion is most active.

### ✅ Event completion

When the run is finished, press:

**Done ✅**

Kisk sends a GG to the party and archives the event announcement.

### 🧵 Discussion threads

Every event automatically gets its **own discussion thread** attached to its
message, so the party can coordinate without flooding the channel. It works for
both `/event` and the panel. If the bot lacks the **Create Public Threads**
permission, Kisk simply skips it — the event is still created.

### 🎛️ No-command panel

Moderators can use:

```text
/panel
```

to post a pinned message whose buttons walk members through creating an event
or reporting an absence **without typing a single command**.

Creating an event takes two steps: the button opens a private message with two
dropdowns — **event type** (Dungeon, Raid, Battleground, PvP, Rift, Abyss,
Other) and **party setup** (party of 5, party of 10, or an open party of 5, 10
or 25) — then **Continue** opens a short form for the title, the time and the
description. Nothing to spell, nothing to invent: the only free-text type is
the optional name you can give to an **Other** event.

Pair it with `/channels` to keep the panel in its own channel while its results
land elsewhere:

```text
/channels events: #events absences: #absences
```

### 👋 Welcoming newcomers

Moderators can use:

```text
/welcome
```

to introduce new members and explain how to use Kisk.

### 🧭 Profile onboarding

Point Kisk at your "validated member" role once:

```text
/onboard role: @Member
```

From then on, whenever a member receives that role, Kisk DMs them a button that
opens a guided, dropdown-based form to register their main character — **class**
(with Aion 2 class icons), **role** and name — and then to add as many other
characters as they like, all without typing a command. If their DMs are closed, Kisk falls back to the
welcome channel (or the server's system channel). The whole member-facing flow
is bilingual **English / French**.

### 🤖 Bot status

Kisk can display the next upcoming event in its Discord status:

```text
Playing 🏰 Fire Temple — tomorrow 21:00
```

### 💾 Persistence

Kisk stores its state in SQLite.

Events, sign-ups, profiles, absences and other persistent data survive bot restarts.

Buttons continue to work after the bot comes back online.

---

Where is Kisk headed? See the **[roadmap and vision](ROADMAP.md)**.

---

# 🚀 Quick start

## Requirements

* Python **3.11+**
* A Discord application and bot
* A Discord server where you have permission to install the bot

---

## 1. Create the Discord bot

Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.

Name it:

```text
Kisk
```

You can use:

```text
assets/avatar.png
assets/banner.png
```

for the bot's branding.

### Create the bot

Open the **Bot** tab and reset/copy the bot token.

⚠️ **Never share your bot token.**

Anyone with the token can control your bot.

If the token is ever exposed, reset it immediately.

### Enable the required intent

Enable:

**SERVER MEMBERS INTENT**

This is required for Kisk's newcomer-welcoming functionality.

The other privileged intents are not required.

### Install the bot

In the **Installation** tab (or OAuth2 → URL Generator), enable:

**Scopes**

* `bot`
* `applications.commands`

**Permissions**

* Send Messages
* Embed Links
* Read Message History
* Create Public Threads *(for the per-event discussion thread; optional — Kisk works without it)*

Open the generated installation URL and invite Kisk to your server.

---

# 💻 2. Run Kisk locally

Clone the repository:

```bash
git clone https://github.com/NaxosOne/aion2-group-bot.git
cd aion2-group-bot
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

### Linux / macOS

```bash
cp .env.example .env
```

### Windows

```powershell
copy .env.example .env
```

Edit `.env` and configure:

```env
DISCORD_TOKEN=your_token_here
GUILD_ID=your_guild_id_here
```

`GUILD_ID` allows slash commands to appear on your development server immediately.

Start Kisk:

```bash
python -m bot.main
```

Once you see:

```text
Logged in as ...
```

Kisk is online.

Try:

```text
/event
```

🎉

---

# ☁️ 3. Host Kisk 24/7

A Discord bot needs to remain online continuously to respond to interactions and send scheduled reminders.

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for production hosting options, including free or nearly-free solutions such as Oracle Cloud and Railway.

---

# 🎮 Usage

## Groups

```text
/event title: Fire Temple HM
       type: Dungeon
       comp: Party of 5
       when: tomorrow 21:00
       ping: @Aion2

/event title: Evening BG
       type: Battleground
       comp: Party of 10
       when: 9pm

/event title: Abyss farming
       type: Abyss
       comp: Open
       size: 8

/events
```

`ping` is optional: give it a role to notify the legion when the event is
posted. Pinging `@everyone` is reserved to moderators.

## Profiles

```text
/profile set name: Kratos class: Templar role: Tank [main: True]
/profile main character: Loki                        → change your default character

/profile show [member]
/profile delete [character] [member]                 → empty character = all of them
                                                       moderators can target a member
/roster
```

## Absences

```text
/away start: 30/08 until: 05/09 reason: holidays

/absences

/back
```

## Communication

```text
/announce [ping: @role]

/vote question: What tonight? option1: Dungeon option2: PvP option3: Nothing
```

## Availability

```text
/availability post

/availability weekly
```

## New members

```text
/welcome                      → greet newcomers in this channel (moderators)
/onboard role: @Member        → DM new members of that role to set up their profile
```

## Panel & channels

```text
/panel                                          → post the click-only panel
/channels events: #events absences: #absences rsvp: #rsvp   → where results are posted
```

**Tip for a smooth server**: post `/panel` in a channel of its own and pin it,
then run `/channels events: #events absences: #absences` so the panel never
gets buried under its own results. Members who dislike typing commands just
click **Create an event** or **Report an absence** and fill in the pop-up form;
the event appears in the events channel and they get a link to it.

Role, event-type and **Aion 2 class** emojis can be replaced with your own —
upload them as custom emojis in the developer portal (**Emojis** tab), then set
`EMOJI_TANK`, `EMOJI_DUNGEON`, `EMOJI_GLADIATOR`, … in `.env`. A ready-made role
and event-type icon pack ships in [`assets/emoji/`](assets/emoji/README.md).
Custom emojis show up in embeds, buttons and messages; Discord renders
slash-command choice lists as plain text, where only Unicode emojis work.

---

# 🏗️ Project structure

```text
assets/
  avatar.png
  banner.png
  emoji/               Role + event-type icon pack (PNG + SVG)
  ...

bot/
  main.py              Entry point: connection and command sync
  config.py            Environment/configuration
  db.py                SQLite persistence
  logic.py             Party and waitlist logic
  embeds.py            Discord announcement embeds
  views.py             Buttons and interactions
  actions.py           Event/absence logic shared by commands and forms
  errors.py            Always answer the user when something fails

  cogs/
    groups.py           /event, /events, reminders and bot status
    profiles.py         /profile and /roster
    legion.py           /away, /absences, /back, /announce, /welcome
    polls.py            /vote and /availability
    panel.py            /panel: buttons opening fill-in forms
    onboarding.py       /onboard: DM new members to set up their profile

  utils/
    time_parse.py       Natural-language time parsing
    onboarding.py       Pure onboarding helpers (role/profile checks)

tests/
  test_logic.py
  test_time_parse.py
  test_onboarding.py
```

### Architecture

Kisk tries to keep its core logic independent from Discord-specific code.

```text
                 Discord
                    │
                    ▼
             ┌─────────────┐
             │    Kisk     │
             └──────┬──────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Commands    Views    Scheduler
          │         │         │
          └─────────┼─────────┘
                    ▼
               Core Logic
                    │
                    ▼
                  SQLite
```

Party composition, waitlists and time parsing are kept as testable logic rather than being tightly coupled to Discord interactions.

---

# 🧪 Testing

The core logic can be tested independently. Install the dev dependencies and
run the suite with pytest:

```bash
pip install -e ".[dev]"
pytest
```

When adding functionality, prefer adding tests for the underlying logic before wiring it into Discord.

Particular care should be taken with:

* timezones
* daylight-saving transitions
* waitlist promotion
* role switching
* duplicate sign-ups
* bot restarts
* scheduled reminders

---

# 🤝 Contributing

Kisk is a community project and contributions are welcome.

If you want to work on a larger feature, open an issue first so we can discuss the approach before implementing it.

Good areas to contribute include:

* 🐛 Bug fixes
* 🧪 Tests
* 📚 Documentation
* 🌍 Translations
* 🎨 Discord UX
* ⚙️ Core party logic
* 📅 Scheduling
* 👥 Legion management
* 🧠 Group formation

Before opening a PR:

1. Keep changes focused.
2. Add or update tests where appropriate.
3. Make sure existing functionality still works.
4. Update the documentation if behaviour changes.

---

# 🌍 Aion 2 classes

The class list is intentionally configurable, and lives in one place:

```text
bot/config.py       → CLASS_EMOJI
```

Each entry pairs a class with its default emoji, and drives the class menus,
the autocomplete, the roster and the character picker at once.

**Fist Fighter** is already drawn (`assets/emoji/fistfighter.png`) and one
commented-out line away: uncomment it in `CLASS_EMOJI` the day the class
launches and it appears everywhere on its own.

Classes are suggestions rather than strict validation, so custom values remain possible.

---

# 📜 Philosophy

Kisk is built around a simple idea:

> **The bot should organise the boring stuff so players can focus on playing.**

That means:

* simple commands
* minimal configuration
* useful automation
* no unnecessary bureaucracy
* no giant management system forced on casual guilds

Kisk should help a legion coordinate without turning the game into a second job.

---

# 📄 License

See [LICENSE](LICENSE).
