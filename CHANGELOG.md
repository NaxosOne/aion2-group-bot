# Changelog

All notable changes to Kisk are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/) (pre-1.0, so the API may still move).

## [Unreleased]

## [0.3.0] - 2026-08-30

### Added

- **Branded embeds** — a consistent Kisk author line across embeds, the banner
  on the `/panel`, and an original per-event-type banner (Dungeon, Raid, PvP, …)
  on event embeds. Artwork is served by URL (`ASSET_BASE_URL`); SVG sources plus
  `scripts/render_banners.py` produce the PNGs.
- **Siege events (multiple groups)** — add `groups:` to an Open `/event` to
  split one roster across several equal groups (Group 1 / 2 / 3); sign-up and
  waitlist are unchanged.
- **Weekly availability upgrades** — the board now shows a "Most available:
  Saturday (8), Friday (6)" summary, and a Clear-mine button wipes your week in
  one click.
- **Recurring events** — `/event … repeat: Weekly` (moderators) makes an event
  repeat every week; Kisk posts each instance a day ahead. Manage them with
  `/recurring list` and `/recurring stop`.
- **Calendar export** — a Calendar button on any event returns an `.ics` file of
  the server's upcoming scheduled events, to import into a personal calendar.
- **Temporary voice channels** — opt in with `/channels voice: <category>` and
  each scheduled event gets a "🔊 <title>" voice channel around its reminder
  window, cleaned up when the event is done/cancelled (or a few hours after it
  starts). Needs Manage Channels. First step of the Phase 2 *Legion scheduling*
  work.
- **Configurable Kisk admin role** — `/admin-role` lets a server appoint a role
  that Kisk treats as an admin (and therefore moderator), so trusted members get
  admin powers without Discord's Manage Server. Setting it still requires Manage
  Server. Button actions honour it immediately.
- **Edit a posted event** — an **Edit** button (creator or moderator) changes an
  event's title, time or description from a prefilled form. Rescheduling
  re-arms the reminder and the "are you coming?" prompt against the new time and
  pings the party; clearing the time drops the schedule. ([#21])
- **Admin queue reordering** — a **Manage queue** button (admins) opens a
  private panel to move sign-ups up or down the queue and promote waitlisted
  players. Per-role slots are still respected and anyone pushed into the party
  is pinged. ([#20])
- **Open-seat visibility** — while a standard event is live and not yet full,
  the embed shows its empty seats per role and a "Needs: 1 Tank, 2 DPS" summary.
  ([#22])
- **`/redeploy`** — an admin command that re-renders every open event with the
  latest buttons and embed and refreshes the panel. **`/panel`** now edits its
  existing message in place instead of posting a duplicate. ([#23])

### Fixed

- Embed fields and descriptions are now trimmed to Discord's limits, so a long
  waitlist (or a big siege / RSVP / availability board) no longer makes the API
  reject the update and freeze the message. ([#35])
- Cancelled or deleted events no longer fire their last-minute reminder or RSVP
  prompt. ([#18], [#19])

[#18]: https://github.com/NaxosOne/aion2-group-bot/issues/18
[#19]: https://github.com/NaxosOne/aion2-group-bot/pull/19
[#20]: https://github.com/NaxosOne/aion2-group-bot/pull/20
[#21]: https://github.com/NaxosOne/aion2-group-bot/pull/21
[#22]: https://github.com/NaxosOne/aion2-group-bot/pull/22
[#23]: https://github.com/NaxosOne/aion2-group-bot/pull/23
[#35]: https://github.com/NaxosOne/aion2-group-bot/issues/35

[Unreleased]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/NaxosOne/aion2-group-bot/releases/tag/v0.3.0
