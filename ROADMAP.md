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
* Guided profile onboarding (`/onboard`) — validated members are DMed to register their main (and alt), bilingual EN/FR, with a channel fallback
* Profile management — `/profile delete` (yours, or a member's for moderators) and automatic cleanup when a member leaves the server
* Automatic discussion thread on every event message (best-effort; skipped if the bot lacks Create Public Threads)

## 🟢 Phase 1 — Better group organisation

Make creating and managing groups as frictionless as possible.

* [ ] Aion 2 class picker during sign-up
* [ ] Sign-up confirmation before an event (a quick "are you coming?" RSVP)
* [ ] Improved event and party UX
* [ ] Better waitlist management (manual reordering, role-aware slots)
* [ ] More flexible party compositions (custom ratios)

## 🔵 Phase 2 — Legion scheduling

Make recurring legion activities easier to organise.

* [ ] Recurring events
* [ ] Multi-party events for sieges
* [ ] Temporary voice channels
* [ ] Calendar export (`.ics`)
* [ ] Improved weekly availability
* [ ] Event series management

## 🟣 Phase 3 — Smart group formation

Move from manually organising parties toward helping players find the right group automatically.

* [ ] LFG system
* [ ] "Available now" status
* [ ] Automatic party suggestions
* [ ] Role/class balancing
* [ ] Smart, role-aware waitlist promotion
* [ ] Replacement suggestions
* [ ] Better player preferences

## 🟠 Phase 4 — Legion tools

Give organisers a clearer view of what's happening.

* [ ] Legion dashboard
* [ ] Web interface

## 💡 Exploring

Some ideas are interesting, but aren't currently priorities:

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
