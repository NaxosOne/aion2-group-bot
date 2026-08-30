<p align="center">
  🇫🇷 <a href="ROADMAP.fr.md">Version française</a> · ⬅️ <a href="README.md">Back to the README</a>
</p>

# 🗺️ Kisk roadmap

Kisk is intentionally starting small.

The long-term goal is to evolve from a simple party bot into a **complete coordination tool for Aion 2 legions**.

The roadmap is flexible and will evolve with the game and community.

## ✅ Already shipped

The foundations are in place:

* Timezone-aware schedules — every player sees the event time in their own timezone
* Automatic waitlist promotion — the first compatible player is promoted and pinged when a spot opens
* No-command panel (`/panel`) with dedicated result channels (`/channels`)
* Custom emoji pack — roles, event types and every Aion 2 class
* Automatic reminders, event completion and cancellation
* Multi-guild — Kisk runs independently on any number of servers
* Guided profile onboarding (`/onboard`) — validated members are DMed to register their main (and alt), in the server's language, with a channel fallback
* Per-server language (`/language`) — choose English or French (or Auto to follow the server's Discord language); every embed, button, onboarding DM and message then appears only in that language
* Profile management — `/profile delete` (yours, or a member's for moderators) and automatic cleanup when a member leaves the server
* Automatic discussion thread on every event message (best-effort; skipped if the bot lacks Create Public Threads)
* RSVP prompt before an event — an "are you coming?" message with confirm/decline buttons and a live tally (configurable timing)
* Character picker at sign-up — players with several registered characters pick which one they bring after choosing a role, each shown with its Aion 2 class icon; `/profile set` restricts characters to the known class list
* Admin queue reordering — a "Manage queue" button (admins only) lets an admin move sign-ups up or down the queue to promote waitlisted players; per-role slots are still respected and anyone pushed into the party is pinged
* Edit a posted event — an "Edit" button (creator or moderator) changes the title, time or description; rescheduling re-arms the reminder and RSVP prompt and pings the party
* Open-seat visibility — a live standard event shows its empty seats per role and a "Needs: 1 Tank, 2 DPS" summary until it fills up

## ✅ Phase 1 — Better group organisation *(complete)*

Creating and managing groups is now frictionless: timezone-aware schedules,
role-aware parties, character sign-up, automatic waitlist promotion, admin
queue reordering, open-seat visibility and event editing are all in place. See
**Already shipped** above for the details.

## ✅ Phase 2 — Legion scheduling *(complete)*

Organising recurring legion activities is now covered: recurring events, siege
events split into groups, temporary voice channels, calendar export and an
upgraded weekly availability board are all in place.

* [x] Recurring events
* [x] Multi-party events for sieges *(light: one shared roster shown in groups)*
* [x] Temporary voice channels
* [x] Calendar export (`.ics`)
* [x] Improved weekly availability
* [x] Event series management *(covered by recurring events)*

## ✅ Phase 3 — Smart group formation *(complete)*

The visibility layer a legion actually needs is in place: players signal what
they're looking for and who's free to play right now, and organisers pull groups
together from that live picture.

* [x] LFG system *(per-server pool + board, with an "Invite LFG" button on open events)*
* [x] "Available now" status *(activity-agnostic presence, shown atop the LFG board)*

Heavier matchmaking automation was considered and **deliberately dropped**: a
legion is a close-knit group that forms its parties socially, not a pool of
strangers to match algorithmically. Those ideas moved to **Exploring** below.

## ✅ Phase 4 — Legion tools *(complete)*

Organisers have a clear, live view of what's happening: the auto-refreshing
`/dashboard` overview inside Discord.

* [x] Legion dashboard *(an auto-refreshing `/dashboard` overview inside Discord)*

A separate web interface was considered and **deferred**: a legion lives in
Discord, and the in-Discord dashboard covers the need without a second surface to
host and secure. Moved to **Exploring**, to revisit only if a concrete
out-of-Discord need appears.

## 💡 Exploring

Some ideas are interesting, but aren't currently priorities:

* Web interface *(Discord covers the need today; revisit for an out-of-Discord use case)*
* Automatic party suggestions *(a legion forms parties socially, not by matchmaking)*
* Role/class balancing
* Replacement suggestions *(the "Invite LFG" button already covers a freed spot)*
* Better player preferences
* More flexible party compositions (custom role ratios)
* Loot rolls
* Birthdays
* Screenshot hall of fame
* More Aion 2 integrations
* Additional community tools

Kisk should remain **useful rather than bloated**.

If a feature doesn't help a legion organise, communicate, or play together, it probably doesn't belong in Kisk.

---

# 🧭 The vision

Aion 2 communities shouldn't need spreadsheets, external calendars, and dozens of Discord messages just to organise a group.

Kisk aims to make the process simple:

```text
Player
   │
   ├── Profile
   ├── Availability
   └── Preferences
          │
          ▼
       Kisk
          │
   ┌──────┼──────┐
   ▼      ▼      ▼
 Events  LFG   Legion
   │      │      │
   └──────┼──────┘
          ▼
    Group formation
          │
          ▼
       The fight
```

The long-term goal is simple:

> **Kisk should know what your legion is doing, who is available, which groups need players, and help get everyone ready to fight.**
