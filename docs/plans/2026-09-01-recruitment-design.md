# Recruitment / application flow — design

**Date:** 2026-09-01
**Status:** approved (design), pending implementation plan
**Branch:** `feat/recruitment`

## Problem

Kisk covers everything *after* a player is in the guild (profiles, events, RSVP,
availability, LFG, onboarding), but there is **no way to bring a newcomer in**.
Today an officer has to manually hand out the "validated member" role; the join
itself is untracked. This feature adds a proper **application → review → decision**
flow so recruiting a member is a first-class, in-Discord process.

## Decisions (locked)

| Question | Decision |
|----------|----------|
| Entry point | **Auto on join**: Kisk DMs the newcomer a persistent "Postuler" button (channel fallback if DMs are closed). |
| Form fields | Core: **character name + class + role**; plus **level/CP, PvP·PvE experience, availability/timezone, motivation** (all four). |
| Reject | **DM with optional reason**: Reject opens a small modal for a reason (may be blank); the applicant gets a polite DM (+ reason if given). Can re-apply later. |
| Discussion space | **Dedicated private channel per candidate** (candidate + officers). |
| On applicant leaving | **Delete everything**: dedicated channel + officer card + DB row. |
| Officer card after decision | **Kept as a trace** (edited to show outcome, buttons removed). |

Officers are identified with the existing `member_is_admin(db, member)` helper
(`admin_role_id` **or** Manage Server).

## Lifecycle

```
Member joins ─▶ DM "Postuler" (fallback to welcome/system channel if DMs closed)
       │ click
       ▼
Class + Role view ─▶ Modal (name, level/CP, experience, availability, motivation)
       │ submit
       ▼
Kisk creates the dedicated candidate channel, posts a welcome message there,
then posts the FICHE (embed + ✅ Accept / ❌ Reject) in the officers' channel.
       │
   ┌───┴─────────────────────────┐
   ▼ Accept (officer)            ▼ Reject (officer)
grants member_role               reason modal ─▶ DM the applicant (+ reason)
   │ (triggers existing              │
   │  onboarding: welcome DM         │
   │  + guided profile setup)        │
   ▼                                 ▼
delete dedicated channel         delete dedicated channel
edit fiche → "✅ Accepté par …"  edit fiche → "❌ Refusé par …"
(buttons removed, kept)          (buttons removed, kept)
```

The pivotal reuse: **Accept only adds the configured `member_role`**. The
existing `Onboarding.on_member_update` listener already reacts to that role being
added and DMs the profile-setup flow — so acceptance needs no new welcome/profile
code, and there is no duplicate notification.

## Two surfaces

With a dedicated channel we separate **deciding** from **talking**:

- **Officers' channel** (`recruit_channel_id`, officers only) → the **fiche** with
  **Accept / Reject**. The candidate is *not* in this channel, so they never see a
  "Reject" button.
- **Dedicated candidate channel** (created per application) → **candidate + officers**,
  for Q&A. The fiche carries a "💬 Ouvrir la discussion" link to it.

```
📁 (category of the officers' channel)
 ├─ #recrutement            (officers)     ← fiche + Accept/Reject
 └─ 🔒 cand-sorcerer-pseudo  (candidate + officers) ← discussion
```

## Configuration

- New setting **`recruit_channel_id`** (officers' channel), set with
  **`/recruit channel`** (on in current channel / off), gated `manage_guild`,
  mirroring `/…welcome` in `legion.py`.
- Dedicated candidate channels are created **in the category of the officers'
  channel** (no extra setting; if it has no category, at guild root).
- **Guard rail:** the on-join "Postuler" DM is sent **only if `recruit_channel_id`
  is configured** → zero impact on servers that don't use recruitment.
- **New bot permission required: `Manage Channels`** (create/delete the dedicated
  channels + set their overwrites). Documented in the README; a missing permission
  is handled gracefully (the officer is told, the application is not created — no
  crash).
- Candidate-channel overwrites: `@everyone` view denied; the candidate and
  `admin_role_id` allowed; the bot allowed. (Officers with Administrator / Manage
  Channels see it regardless.)

## Components (new)

- **`bot/cogs/recruitment.py`** — the cog:
  - `on_member_join` (independent of `legion`'s; the public greeting and the
    private "Postuler" DM coexist), guarded on `recruit_channel_id`.
  - `on_member_remove` — deletes a pending applicant's channel + card + row.
  - `/recruit channel` command.
  - `ApplyButton` (persistent `DynamicItem`, guild_id in the custom_id) — reused in
    the DM and the channel fallback.
  - `ApplicationSetupView` (reuses `ClassSelect` / `RoleSelect` from `onboarding`)
    → Continue → `ApplicationModal` (5 text inputs).
  - `ReviewView` — persistent Accept/Reject buttons on the fiche, gated by
    `member_is_admin`. Reject opens `RejectReasonModal`.
- **`bot/utils/recruitment.py`** — pure helpers (channel-name slug, permission
  overwrite builder, state-transition guards) so the logic is unit-testable off
  Discord.
- Registration of the persistent items in `main.py` (as `OnboardButton` is today).

## Data

New table **`applications`**:

| column | notes |
|--------|-------|
| `guild_id`, `user_id` | applicant |
| `char_name`, `char_class`, `role` | core |
| `level_cp`, `experience`, `availability`, `motivation` | form text |
| `status` | `pending` / `accepted` / `rejected` |
| `reviewer_id`, `reason` | decision |
| `channel_id` | dedicated discussion channel |
| `card_message_id` | fiche message (in the officers' channel) |
| `created_at`, `decided_at` | timestamps |

- **One `pending` per (guild_id, user_id)**; re-applying after a reject is allowed.
- New settings column `recruit_channel_id` added to the `settings` table via the
  established `CREATE TABLE` + migration-dict pattern (same as `admin_role_id`).
- DB methods: `create_application`, `get_pending_application`,
  `get_application(card_message_id)`, `set_application_status`, `delete_application`.

## Edge cases

- **Applicant already has a pending application** → the button/flow says "tu as déjà
  une candidature en cours" (no duplicate channel).
- **`member_role` not configured** → Accept tells the officer to run `/onboard role`
  first (can't validate without a target role).
- **Applicant left before decision** → `on_member_remove` deletes channel + fiche +
  row (the "auto-delete" requirement).
- **Concurrent Accept/Reject** (two officers) → the same atomic conditional-update
  pattern already used for the notification race: the second click sees the row is
  no longer `pending` and gets "déjà traitée".
- **DMs closed on join** → fallback to the welcome channel / system channel (reusing
  `onboarding`'s fallback approach); the "Postuler" button still works there.
- **`Manage Channels` missing** → officer is warned, application not created.
- **Dedicated channel manually deleted** before a decision → delete/edit is
  best-effort and ignores a missing channel/message.
- Everything is **i18n FR/EN** via `i18n.t` + `resolve_lang`, per the per-guild
  language convention.

## Testing

Pure-logic unit tests (repo conventions — `asyncio.run`, cogs via
`Cog.__new__`, no live Discord):

- DB: `create_application` → `get_pending_application` returns it; second create
  while pending is rejected; `set_application_status` transitions; `delete_application`
  removes the row.
- Guard: "DM on join only if `recruit_channel_id` set".
- State transitions: `pending → accepted` / `pending → rejected`; a decision on a
  non-pending row is refused.
- Permission gate on Accept/Reject (`member_is_admin`).
- Channel-name slug / overwrite-builder helpers.

Discord-coupled parts (channel creation, DMs, button wiring) → CI import/format +
manual smoke, exactly as `polls.py` is treated.

## Docs (per the feature-docs habit)

Update in the same PR: `README.md` (+ `README.fr.md`), `ROADMAP.md`
(+ `ROADMAP.fr.md`), `CHANGELOG.md`, and the in-bot command help. Call out the new
**Manage Channels** permission requirement prominently.

## Out of scope (YAGNI)

- Public "we're recruiting" showcase embed / roster-gap display.
- Multi-stage queues, trials, or automated interviews.
- Periodic purge of *decided* applications (kept as a trace by decision; the
  transient channels are already deleted at every outcome, so nothing unbounded
  accumulates).
