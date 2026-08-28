# Design — Per-server language (`/language`) and i18n

Date: 2026-08-28
Branch: `feat/rsvp-channel` (feature branch for this work: `feat/language`)
Status: Approved

## Problem

KISK's user-facing strings are currently hardcoded **inline bilingual**
(e.g. `"Continue / Continuer"`, `"Welcome … / Bienvenue …"`) across ~180 string
sites in 8 cogs plus `embeds.py`, `views.py` and onboarding. This is verbose and
shows both languages to everyone.

Goal: a `/language` command that sets a server's language (FR or EN). Once set,
**everything the user sees** — event/RSVP embeds, command responses, onboarding
DMs, buttons, error messages — is shown **exclusively** in that language.

## Decisions (from brainstorming)

1. **Scope**: migrate everything *user-visible*. Do not touch internal code —
   table/column names, logs, comments, `custom_id`s, technical `SystemExit`
   startup messages stay as-is.
2. **Discord `/` menu** (command names + descriptions): Discord can only localize
   these per *user client locale*, not per guild. We accept this and use
   Discord-native localization so each member sees the picker in their own
   Discord language. All runtime content follows the per-guild `/language`.
3. **Default** (no `/language` set yet): auto-detect from `guild.preferred_locale`
   (`fr*` → French, else English). `/language` can override.
4. **Catalog storage**: JSON files per language (`bot/locales/{en,fr}.json`), with
   a CI test enforcing key + placeholder parity.

## Architecture

### 1. Language resolution

- New column `guild_settings.language TEXT` (`'fr'` | `'en'` | `NULL` = auto),
  added through the existing `Database._add_missing_columns` migration path.
- New dependency-free module `bot/i18n.py` with **pure, unit-testable** helpers:
  - `normalize_locale(discord_locale) -> 'fr' | 'en'`: `"fr"`, `"fr-*"` → `fr`,
    everything else → `en`.
  - `pick_lang(setting, guild_locale) -> 'fr' | 'en'`: if the stored server
    override is set, use it; otherwise derive from `guild.preferred_locale`;
    fallback `en`. Pure — no DB.
  - `t(key, lang, **params) -> str`: catalog lookup + `str.format(**params)`.
    Missing key/lang → fallback to the other language, then the raw key; logs a
    warning. Never raises inside a handler.
  - `resolve_lang(db, guild) -> str`: async wrapper that reads the setting then
    calls `pick_lang`.

### 2. Slash-command metadata (`/` menu) — per client locale

- Command names/descriptions/param descriptions become `app_commands.locale_str`.
- A `Translator(app_commands.Translator)` subclass is registered via
  `tree.set_translator(...)` in `setup_hook`; it reads the same JSON catalogs
  under a `commands.*` namespace, keyed by the `locale_str` message and target
  `discord.Locale`.
- Effect: the picker follows each user's Discord client language, independent of
  the per-guild runtime setting. This is the one surface Discord cannot vary per
  guild — accepted by design.

### 3. Runtime content — follows `/language`

- Each handler resolves `lang = await resolve_lang(db, interaction.guild)`; for
  onboarding DMs (no guild context on the message) the `guild_id` already travels
  in the button `custom_id`, so lang is resolved from that.
- `build_event_embed` / `build_rsvp_embed` and message helpers take a `lang` param
  and call `t(...)`.
- **Persistent-view button labels**: Discord stores the rendered label at *send*
  time; on restart `add_view(...)` only re-routes clicks by `custom_id` (the
  registered instance's labels are never re-displayed). So views are built in the
  server's language *at send time*; the startup registration keeps neutral labels.
  `custom_id`s stay static → persistence intact.

### 4. Catalog + parity test

- `bot/locales/en.json` + `bot/locales/fr.json`, flat dotted keys grouped by
  surface: `rsvp.title`, `onboard.welcome_title`, `commands.language.description`, …
- `tests/test_i18n.py`: strict key parity between both files, identical
  `{placeholder}` sets per key, `t()` formatting, missing-key fallback,
  `pick_lang()`, `normalize_locale()`. CI guard against a forgotten translation.

### 5. The `/language` command

- Small cog `bot/cogs/settings.py`, `@app_commands.guild_only()`,
  `@app_commands.default_permissions(manage_guild=True)`.
- Shape: `/language choice:<Français | English | Auto (Discord server language)>`.
  `Auto` resets the column to `NULL`. The confirmation reply is rendered in the
  resulting language.

### 6. Migration scope

- **Translate** every user-visible surface: events/RSVP/embeds/views, onboarding
  + DM, profiles, polls, panel, groups, legion, user-facing error messages.
- **Leave untouched**: table/column names, logs, comments, `custom_id`s,
  technical startup `SystemExit` messages.
- Delivery in **atomic-commit waves** on the feature branch:
  - A. infra: `i18n.py`, `language` column, `/language` cog, translator,
    parity test.
  - B. events / RSVP / embeds / signup + RSVP views.
  - C. onboarding + DM.
  - D. profiles / polls / panel / groups / legion / errors.
- Docs updated in the same PR (feature-docs habit): `README.md`, `README.fr.md`,
  `ROADMAP.md`, `ROADMAP.fr.md`, and any in-bot command help.

### 7. Error handling

- Missing key/lang → `t` falls back (other lang → raw key) and logs; no crash.
- Unknown stored `language` value → treated as auto.
- `guild is None` and no resolvable `guild_id` → `en` default.

### 8. Verification (no local Python → CI)

- All new i18n logic covered by unit tests; parity test enforces completeness.
- Existing tests updated where embed/message signatures gain `lang`.
- Final validation on the PR's CI.

## Out of scope

- Languages beyond FR/EN (catalog is structured to extend later).
- Translating logs, comments, or internal identifiers.
- Per-user runtime language inside a guild (setting is per-server).
