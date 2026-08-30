# Changelog

All notable changes to Kisk are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/) (pre-1.0, so the API may still move).

## [Unreleased]

## [0.5.2] - 2026-08-30

### Security

- **An event title could smuggle an `@everyone` ping.** Notification messages
  (reminders, completion, cancellation, reschedule and waitlist-promotion
  notices, and the discussion-thread intro) put the member-supplied event title
  into the message body without restricting mentions, so an event titled
  `@everyone` made Kisk mass-ping the server — bypassing the moderator-only
  `@everyone` gate. Every such send now allows user mentions only.

### Fixed

- `SignupView` leaked one lock per event for the bot's lifetime; the lock is now
  dropped when an event is completed or cancelled (its buttons are gone, so no
  interaction reaches it again).
- Party/pool pings no longer silently fail on large sieges. A ping built from a
  whole party or pool (reminders, RSVP prompts, completion/cancellation notices,
  LFG invites, waitlist promotions) could exceed Discord's 2000-character
  message limit for a maxed siege (up to 200 members) and fail to send at all —
  so nobody was pinged. Mentions are now trimmed to fit (`join_mentions`), and
  the ping goes out.

## [0.5.1] - 2026-08-30

### Fixed

- A member who left a server kept lingering in the LFG pool and the "available
  now" list until their entry expired; leaving now clears both immediately
  (`purge_member`).
- A **recurring siege** lost its group split: `/event comp:Open groups:N
  repeat:Weekly` stored the total size but not the group count, so each posted
  instance rendered as one flat party instead of N groups. The group count is
  now stored on the recurrence and reproduced on every instance.

### Changed

- **Every background loop is now crash-resilient.** discord.py stops a task loop
  the first time its coroutine raises, which would silently freeze a background
  job (reminders, RSVP prompts, voice channels, recurring events, bot status,
  the weekly availability post, the LFG prune and the dashboard refresh). A
  `resilient_tick` wrapper now logs the failure and lets the next tick run. This
  supersedes the narrower LFG/dashboard guard added earlier in this cycle.
- Removed an unused helper (`logic.role_capacity`).

## [0.5.0] - 2026-08-30

### Added

- **Legion dashboard** — the first Phase 4 feature. `/dashboard` (moderators)
  posts one auto-refreshing overview per server (updates every couple of
  minutes) that gathers, in one embed: upcoming events with fill and the roles
  still short, the LFG pool and "available now" counts, current absences, active
  recurring series, and roster health (members + tank/heal/DPS split among
  mains). Read-only; a dedicated refresh loop keeps it current. ([#46])

## [0.4.0] - 2026-08-30

### Added

- **"Available now" status** — a lighter, activity-agnostic companion to LFG.
  Mark yourself available to play right now (default 2h) with the LFG board's
  **✋ I'm around now** button or `/lfg available on`; the board shows an
  **Available now** section at the top. Shares the LFG expiry/prune loop.
- **Looking for group (LFG)** — the first Phase 3 feature. `/lfg looking`
  (activity, role, optional note, auto-expiry) adds a member to the server's
  live pool; `/lfg stop` removes them. Moderators post a persistent **LFG
  board** with `/lfg board` (one per server, like `/panel`) that shows the pool
  grouped by activity, with **🔎 I'm looking** / **🛑 Stop looking** buttons; a
  background loop prunes expired entries and refreshes the board. Open events
  gain an **Invite LFG** button (creator or moderator) that pings the pool
  members who fit a still-open role. ([#43])

## [0.3.1] - 2026-08-30

### Fixed

- A maxed-out siege (8 groups × 25) with a long waitlist could exceed Discord's
  6000-char embed ceiling — even with every field under the 1024 per-field
  limit — and fail to render. The composition and waitlist fields now share a
  total budget so the embed always stays valid. ([#40])

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
[#40]: https://github.com/NaxosOne/aion2-group-bot/issues/40
[#43]: https://github.com/NaxosOne/aion2-group-bot/pull/43
[#46]: https://github.com/NaxosOne/aion2-group-bot/pull/46

[Unreleased]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.5.2...HEAD
[0.5.2]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/NaxosOne/aion2-group-bot/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/NaxosOne/aion2-group-bot/releases/tag/v0.3.0
