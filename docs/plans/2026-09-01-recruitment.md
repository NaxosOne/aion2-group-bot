# Recruitment / Application Flow — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an in-Discord application flow — a newcomer is DM'd a "Postuler" button on join, fills a form, and officers review it (with a dedicated per-candidate discussion channel) and Accept (grants the member role, which triggers the existing onboarding) or Reject (with an optional reason DM'd to the candidate).

**Architecture:** A new self-contained cog `bot/cogs/recruitment.py` with pure helpers in `bot/utils/recruitment.py` and an `applications` table. It reuses existing rails: `ClassSelect`/`RoleSelect` from `onboarding`, `member_is_admin` from `utils/permissions`, the persistent-`DynamicItem` pattern, the `guild_settings` migration dict, and the `i18n.t` / `resolve_lang` translation layer. **Accept simply adds the configured `member_role`**, so `Onboarding.on_member_update` handles the welcome + profile setup with no new code.

**Tech Stack:** discord.py 2.x (cogs, `DynamicItem`, modals, `PermissionOverwrite`), aiosqlite, JSON i18n catalogs. Tests: `pytest` with `asyncio.run` (no pytest-asyncio), cogs via `Cog.__new__`.

**Design doc:** `docs/plans/2026-09-01-recruitment-design.md`

**Branch:** `feat/recruitment` (already created off `upstream/claude/discord-bot-aion-groups-3bnutq`).

**Conventions to respect (verify as you go):**
- ruff: `select=["F"]` **plus E501 (lines ≤ 88 chars)**, and `ruff format --check` (magic trailing comma, 2-space inline comments). Run both before every commit.
- Conventional Commits; **no attribution footer in commits** (repo convention).
- Every user-facing string goes through `i18n.t(key, lang)`; `lang = await i18n.resolve_lang(db, guild)`.
- Full local check before each commit:
  ```bash
  python -m pytest -q && ruff check bot tests && ruff format --check bot tests
  ```
  (If Python isn't available locally, push and verify via CI — see the repo's CI-check loop.)

---

## Task 1: Database — `applications` table, settings column, methods

**Files:**
- Modify: `bot/db.py` (SCHEMA block ~line 158; `_add_missing_columns` dict ~line 185; add methods near the other sections)
- Test: `tests/test_recruitment_db.py` (create)

**Step 1: Write the failing test**

```python
"""The applications table: create, find-pending, decide, delete."""

import asyncio

from bot.db import Database


def _make_db():
    db = Database(":memory:")
    asyncio.get_event_loop().run_until_complete(db.connect())
    return db


APP = dict(
    guild_id=1,
    user_id=42,
    char_name="Kratos",
    char_class="Sorcerer",
    role="dps",
    level_cp="55 / 4.2k CP",
    experience="cleared everything",
    availability="weeknights, CET",
    motivation="wanna raid",
)


def test_create_returns_id_and_pending_is_findable():
    async def go():
        db = Database(":memory:")
        await db.connect()
        app_id = await db.create_application(**APP)
        assert isinstance(app_id, int)
        pending = await db.get_pending_application(1, 42)
        assert pending is not None
        assert pending["char_name"] == "Kratos"
        assert pending["status"] == "pending"

    asyncio.run(go())


def test_second_pending_is_blocked_but_reapply_after_decision_is_allowed():
    async def go():
        db = Database(":memory:")
        await db.connect()
        first = await db.create_application(**APP)
        assert await db.get_pending_application(1, 42) is not None
        # A decision frees the applicant to reapply.
        await db.set_application_status(first, "rejected", reviewer_id=7, reason="low")
        assert await db.get_pending_application(1, 42) is None
        second = await db.create_application(**APP)
        assert second != first
        assert await db.get_pending_application(1, 42) is not None

    asyncio.run(go())


def test_set_status_records_decision_and_delete_removes_row():
    async def go():
        db = Database(":memory:")
        await db.connect()
        app_id = await db.create_application(**APP)
        await db.set_application_status(app_id, "accepted", reviewer_id=7, reason=None)
        row = await db.get_application(app_id)
        assert row["status"] == "accepted"
        assert row["reviewer_id"] == 7
        assert row["decided_at"] is not None
        await db.delete_application(app_id)
        assert await db.get_application(app_id) is None

    asyncio.run(go())


def test_recruit_channel_id_setting_roundtrips():
    async def go():
        db = Database(":memory:")
        await db.connect()
        await db.set_setting(1, "recruit_channel_id", 999)
        row = await db.get_settings(1)
        assert row["recruit_channel_id"] == 999

    asyncio.run(go())
```

**Step 2: Run it, expect failure**

Run: `python -m pytest tests/test_recruitment_db.py -q`
Expected: FAIL (`create_application` missing / `recruit_channel_id` no such column).

**Step 3: Add the table to `SCHEMA`** (insert before the closing `"""` at ~line 158, after the `recurrences` table):

```sql
CREATE TABLE IF NOT EXISTS applications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    char_name      TEXT    NOT NULL,
    char_class     TEXT    NOT NULL,
    role           TEXT    NOT NULL,
    level_cp       TEXT,
    experience     TEXT,
    availability   TEXT,
    motivation     TEXT,
    status         TEXT    NOT NULL DEFAULT 'pending',   -- pending/accepted/rejected
    reviewer_id    INTEGER,
    reason         TEXT,
    channel_id     INTEGER,                              -- dedicated discussion channel
    card_message_id INTEGER,                             -- the fiche in the officers' channel
    created_at     INTEGER NOT NULL,
    decided_at     INTEGER
);
```

**Step 4: Add the settings column** to the `"guild_settings"` dict in `_add_missing_columns` (after `dashboard_message_id`):

```python
                "recruit_channel_id": "INTEGER",  # officers' recruitment review channel
```

**Step 5: Add the DB methods** (new section, e.g. after the events section):

```python
    # ----- Recruitment -----

    async def create_application(self, **fields) -> int:
        fields.setdefault("created_at", int(time.time()))
        columns = ", ".join(fields)
        placeholders = ", ".join("?" for _ in fields)
        async with self.conn.execute(
            f"INSERT INTO applications ({columns}) VALUES ({placeholders})",
            tuple(fields.values()),
        ) as cur:
            app_id = cur.lastrowid
        await self.conn.commit()
        return app_id

    async def get_application(self, app_id: int):
        async with self.conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ) as cur:
            return await cur.fetchone()

    async def get_pending_application(self, guild_id: int, user_id: int):
        async with self.conn.execute(
            """SELECT * FROM applications
               WHERE guild_id = ? AND user_id = ? AND status = 'pending'""",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchone()

    async def set_application_card(
        self, app_id: int, channel_id: int, card_message_id: int
    ) -> None:
        await self.conn.execute(
            "UPDATE applications SET channel_id = ?, card_message_id = ? WHERE id = ?",
            (channel_id, card_message_id, app_id),
        )
        await self.conn.commit()

    async def set_application_status(
        self, app_id: int, status: str, *, reviewer_id: int | None, reason: str | None
    ) -> bool:
        """Decide a still-pending application. Returns False if it was already
        decided (a second officer clicked) — the same guard used for the
        notification race."""
        async with self.conn.execute(
            """UPDATE applications
               SET status = ?, reviewer_id = ?, reason = ?, decided_at = ?
               WHERE id = ? AND status = 'pending'""",
            (status, reviewer_id, reason, int(time.time()), app_id),
        ) as cur:
            changed = cur.rowcount > 0
        await self.conn.commit()
        return changed

    async def delete_application(self, app_id: int) -> None:
        await self.conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        await self.conn.commit()
```

> `time` is already imported in `db.py` (used by other methods). Confirm with `grep -n "^import time" bot/db.py`; add it if missing.

**Step 6: Run tests, expect PASS**

Run: `python -m pytest tests/test_recruitment_db.py -q`
Expected: PASS (4 tests).

**Step 7: Commit**

```bash
git add bot/db.py tests/test_recruitment_db.py
git commit -m "feat(recruitment): applications table and settings column"
```

---

## Task 2: Pure helpers — `bot/utils/recruitment.py`

Off-Discord logic so it is unit-testable: the join-DM guard, the dedicated-channel name slug, and the permission-overwrite recipe (returned as plain data, asserted without a live guild).

**Files:**
- Create: `bot/utils/recruitment.py`
- Test: `tests/test_recruitment_utils.py`

**Step 1: Write the failing test**

```python
from bot.utils.recruitment import channel_slug, overwrite_spec, recruitment_enabled


def test_recruitment_enabled_needs_a_configured_channel():
    assert recruitment_enabled({"recruit_channel_id": 123}) is True
    assert recruitment_enabled({"recruit_channel_id": None}) is False
    assert recruitment_enabled(None) is False


def test_channel_slug_is_discord_safe():
    # lowercased, spaces/punctuation -> hyphens, deduped, trimmed, capped.
    assert channel_slug("Sorcerer", "Kro Nos!!") == "cand-sorcerer-kro-nos"
    assert channel_slug("Cleric", "") == "cand-cleric"
    long = channel_slug("Ranger", "x" * 200)
    assert len(long) <= 90 and long.startswith("cand-ranger-")


def test_overwrite_spec_lists_who_may_see_the_channel():
    spec = overwrite_spec(candidate_id=42, admin_role_id=7, bot_id=99)
    assert spec["everyone"] is False        # @everyone denied view
    assert set(spec["allow_view"]) == {42, 7, 99}
    # No admin role configured -> only candidate + bot are explicitly allowed.
    spec2 = overwrite_spec(candidate_id=42, admin_role_id=None, bot_id=99)
    assert set(spec2["allow_view"]) == {42, 99}
```

**Step 2: Run it, expect failure** — `python -m pytest tests/test_recruitment_utils.py -q` → FAIL (module missing).

**Step 3: Implement**

```python
"""Pure helpers for the recruitment flow — no Discord dependency, so the
logic is unit-testable without a live guild."""

import re

_CHANNEL_MAX = 90  # Discord caps channel names at 100; leave margin.


def recruitment_enabled(settings) -> bool:
    """True when this guild has an officers' recruitment channel configured."""
    return bool(settings and settings["recruit_channel_id"])


def channel_slug(char_class: str, char_name: str) -> str:
    """A Discord-safe channel name for a candidate's dedicated channel."""
    raw = f"cand-{char_class}-{char_name}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug[:_CHANNEL_MAX].rstrip("-")


def overwrite_spec(*, candidate_id: int, admin_role_id: int | None, bot_id: int):
    """Who may see the dedicated channel, as plain data the cog turns into
    discord.PermissionOverwrite objects: @everyone denied, candidate + admin
    role (if any) + the bot allowed."""
    allow_view = [candidate_id, bot_id]
    if admin_role_id:
        allow_view.insert(1, admin_role_id)
    return {"everyone": False, "allow_view": allow_view}
```

**Step 4: Run tests, expect PASS.**

**Step 5: Commit**

```bash
git add bot/utils/recruitment.py tests/test_recruitment_utils.py
git commit -m "feat(recruitment): pure helpers (guard, channel slug, overwrites)"
```

---

## Task 3: i18n strings

Add every recruitment string to both catalogs, then lock them with a keys test (mirrors `tests/test_polls_i18n_keys.py`).

**Files:**
- Modify: `bot/locales/en.json`, `bot/locales/fr.json`
- Test: `tests/test_recruitment_i18n_keys.py` (create)

**Step 1: Add the keys** to `en.json` (and the French equivalents to `fr.json`). Keep them grouped. English values:

```json
  "recruit.dm_title": "Join {guild}? 🛡️",
  "recruit.dm_body": "Interested in playing with us? Tap the button to send your application to the officers.",
  "recruit.dm_fallback_prefix": "I couldn't DM you (your DMs are closed), so here it is.",
  "recruit.apply_button": "Apply",
  "recruit.already_pending": "You already have an application in progress — the officers are on it. ⏳",
  "recruit.setup_title": "📝 Apply to {guild}",
  "recruit.summary_body": "**Class:** {class_line}\n**Role:** {role_line}\n\nPick from the menus, then hit **Continue** to fill in the rest.",
  "recruit.continue": "Continue",
  "recruit.pick_first": "Pick your class and role from the menus first.",
  "recruit.modal_title": "Your application",
  "recruit.name_label": "Character name",
  "recruit.level_label": "Level / Combat Power",
  "recruit.exp_label": "PvP / PvE experience",
  "recruit.avail_label": "Availability / timezone",
  "recruit.motivation_label": "Why do you want to join?",
  "recruit.submitted": "✅ Application sent! The officers will get back to you. A private channel was opened so you can chat with them.",
  "recruit.no_channel": "Recruitment isn't set up on this server yet.",
  "recruit.missing_perm": "I need the **Manage Channels** permission to open a candidate channel — ask an admin to grant it.",
  "recruit.channel_welcome": "👋 {mention}, welcome! Your application is with the officers. Ask anything here while you wait.",
  "recruit.fiche_title": "📄 Application — {name}",
  "recruit.fiche_class_role": "{emoji} **{cls}** · {role}",
  "recruit.fiche_level": "Level / CP",
  "recruit.fiche_exp": "Experience",
  "recruit.fiche_avail": "Availability",
  "recruit.fiche_motivation": "Motivation",
  "recruit.fiche_pending": "⏳ Pending — {mention}",
  "recruit.btn_accept": "Accept",
  "recruit.btn_reject": "Reject",
  "recruit.btn_discuss": "💬 Open discussion",
  "recruit.not_officer": "Only officers can decide on applications.",
  "recruit.already_decided": "This application has already been handled.",
  "recruit.no_member_role": "Set the validated-member role first with `/onboard role`, then accept.",
  "recruit.applicant_gone": "This candidate has left the server.",
  "recruit.accepted_fiche": "✅ Accepted by {who}",
  "recruit.rejected_fiche": "❌ Rejected by {who}",
  "recruit.reject_modal_title": "Reject — optional reason",
  "recruit.reject_reason_label": "Reason (optional, sent to the candidate)",
  "recruit.dm_accepted": "🎉 Your application to {guild} was accepted — welcome aboard!",
  "recruit.dm_rejected": "❌ Your application to {guild} wasn't retained. Thanks for your interest!",
  "recruit.dm_rejected_reason": "❌ Your application to {guild} wasn't retained.\n**Reason:** {reason}",
  "recruit.cmd_on": "✅ Applications will be reviewed in this channel.",
  "recruit.cmd_off": "Recruitment review disabled.",
```

French values (`fr.json`) — same keys, e.g. `"recruit.apply_button": "Postuler"`, `"recruit.btn_accept": "Accepter"`, `"recruit.btn_reject": "Refuser"`, `"recruit.submitted": "✅ Candidature envoyée ! Les officiers reviendront vers toi. Un salon privé a été ouvert pour échanger avec eux."`, etc. Translate every value.

**Step 2: Write the keys test**

```python
"""Every recruitment string resolves in both catalogs with the params the cog
passes — a renamed or half-translated key fails here, not in front of players."""

import pytest

from bot import i18n

RECRUIT_KEYS = {
    "recruit.dm_title": {"guild": "Kisk"},
    "recruit.dm_body": {},
    "recruit.dm_fallback_prefix": {},
    "recruit.apply_button": {},
    "recruit.already_pending": {},
    "recruit.setup_title": {"guild": "Kisk"},
    "recruit.summary_body": {"class_line": "x", "role_line": "y"},
    "recruit.continue": {},
    "recruit.pick_first": {},
    "recruit.modal_title": {},
    "recruit.name_label": {},
    "recruit.level_label": {},
    "recruit.exp_label": {},
    "recruit.avail_label": {},
    "recruit.motivation_label": {},
    "recruit.submitted": {},
    "recruit.no_channel": {},
    "recruit.missing_perm": {},
    "recruit.channel_welcome": {"mention": "@x"},
    "recruit.fiche_title": {"name": "Kratos"},
    "recruit.fiche_class_role": {"emoji": "🔥", "cls": "Sorcerer", "role": "DPS"},
    "recruit.fiche_level": {},
    "recruit.fiche_exp": {},
    "recruit.fiche_avail": {},
    "recruit.fiche_motivation": {},
    "recruit.fiche_pending": {"mention": "@x"},
    "recruit.btn_accept": {},
    "recruit.btn_reject": {},
    "recruit.btn_discuss": {},
    "recruit.not_officer": {},
    "recruit.already_decided": {},
    "recruit.no_member_role": {},
    "recruit.applicant_gone": {},
    "recruit.accepted_fiche": {"who": "@x"},
    "recruit.rejected_fiche": {"who": "@x"},
    "recruit.reject_modal_title": {},
    "recruit.reject_reason_label": {},
    "recruit.dm_accepted": {"guild": "Kisk"},
    "recruit.dm_rejected": {"guild": "Kisk"},
    "recruit.dm_rejected_reason": {"guild": "Kisk", "reason": "low"},
    "recruit.cmd_on": {},
    "recruit.cmd_off": {},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key,params", list(RECRUIT_KEYS.items()))
def test_recruit_key_resolves_and_formats(key, params, lang):
    out = i18n.t(key, lang, **params)
    assert out != key          # missing key degrades to the raw key
    assert "{" not in out      # a formatting miss leaves {markers}
```

**Step 3: Run** — `python -m pytest tests/test_recruitment_i18n_keys.py -q` → PASS (both langs). Fix any missing/renamed key until green.

**Step 4: Commit**

```bash
git add bot/locales/en.json bot/locales/fr.json tests/test_recruitment_i18n_keys.py
git commit -m "feat(recruitment): FR/EN strings for the application flow"
```

---

## Task 4: The recruitment cog — form + channel creation

This task is Discord-coupled; follow `bot/cogs/onboarding.py` closely. Unit tests cover the pure decomposition (Task 1/2 already do the testable logic); the wiring is verified by CI import/format + manual smoke, as `polls.py` is.

**Files:**
- Create: `bot/cogs/recruitment.py`

**Step 1: Write the module** — imports, the persistent apply button, the class/role view (reusing `ClassSelect`/`RoleSelect`), and the modal that creates the channel + fiche.

```python
"""Recruitment: newcomers are DM'd a "Postuler" button on join; they fill a
form; officers review each application in a dedicated per-candidate channel and
Accept (grants the member role -> onboarding fires) or Reject (optional reason,
DM'd to the candidate). See docs/plans/2026-09-01-recruitment-design.md."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .. import config, i18n
from ..branding import brand
from ..errors import ModalErrorMixin, ViewErrorMixin
from ..utils.onboarding import onboard_custom_id  # reuse the guild-id codec? see note
from ..utils.permissions import member_is_admin
from ..utils.recruitment import channel_slug, overwrite_spec, recruitment_enabled
from .onboarding import ClassSelect, ROLE_LABELS, RoleSelect

log = logging.getLogger(__name__)
```

> **Note on the apply-button custom_id:** `onboard_custom_id` builds the string for
> the onboarding template. Do **not** reuse it — define a distinct template so the
> two dynamic items never collide. Add helpers in `bot/utils/recruitment.py`
> (`apply_custom_id(guild_id)` returning `f"kisk:apply:{guild_id}"`) with a matching
> unit test, or inline the template on the `DynamicItem` subclass as `OnboardButton`
> does. Keep templates disjoint: `kisk:apply:(?P<guild_id>\d+)` and
> `kisk:recruit:(?P<app_id>\d+):(?P<action>accept|reject)`.

```python
class ApplyButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"kisk:apply:(?P<guild_id>\d+)",
):
    """Persistent DM button that opens the application form for a guild."""

    def __init__(self, guild_id: int, lang: str = i18n.DEFAULT):
        self.guild_id = guild_id
        super().__init__(
            discord.ui.Button(
                label=i18n.t("recruit.apply_button", lang),
                emoji="📝",
                style=discord.ButtonStyle.primary,
                custom_id=f"kisk:apply:{guild_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match["guild_id"]))

    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.db
        guild = interaction.client.get_guild(self.guild_id)
        lang = await i18n.resolve_lang(db, guild)
        ephemeral = interaction.guild is not None
        settings = await db.get_settings(self.guild_id)
        if not recruitment_enabled(settings):
            await interaction.response.send_message(
                i18n.t("recruit.no_channel", lang), ephemeral=ephemeral
            )
            return
        if await db.get_pending_application(self.guild_id, interaction.user.id):
            await interaction.response.send_message(
                i18n.t("recruit.already_pending", lang), ephemeral=ephemeral
            )
            return
        guild_name = guild.name if guild else i18n.t("onboard.your_legion", lang)
        view = ApplicationSetupView(self.guild_id, guild_name, ephemeral, lang)
        await interaction.response.send_message(
            embed=view.summary(), view=view, ephemeral=ephemeral
        )


class ApplicationSetupView(ViewErrorMixin, discord.ui.View):
    """Pick class + role (reused selects), then Continue -> the text modal."""

    def __init__(self, guild_id, guild_name, ephemeral, lang):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.ephemeral = ephemeral
        self.lang = lang
        self.char_class = None
        self.role = None
        self.add_item(ClassSelect(None, lang))
        self.add_item(RoleSelect(None, lang))
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.label = i18n.t("recruit.continue", lang)

    def summary(self) -> discord.Embed:
        not_set = i18n.t("onboard.not_set", self.lang)
        cls = (
            f"{config.CLASS_EMOJI[self.char_class]} **{self.char_class}**"
            if self.char_class
            else not_set
        )
        role = f"**{ROLE_LABELS[self.role]}**" if self.role else not_set
        return brand(
            discord.Embed(
                title=i18n.t("recruit.setup_title", self.lang, guild=self.guild_name),
                description=i18n.t(
                    "recruit.summary_body", self.lang, class_line=cls, role_line=role
                ),
                colour=discord.Colour.blurple(),
            )
        )

    @discord.ui.button(label="Continue", emoji="➡️", style=discord.ButtonStyle.success)
    async def proceed(self, interaction: discord.Interaction, _):
        if self.char_class is None or self.role is None:
            await interaction.response.send_message(
                i18n.t("recruit.pick_first", self.lang), ephemeral=self.ephemeral
            )
            return
        await interaction.response.send_modal(
            ApplicationModal(
                self.guild_id, self.char_class, self.role, self.ephemeral, self.lang
            )
        )
```

> **Reuse check:** `ClassSelect`/`RoleSelect` set `self.view.char_class` /
> `self.view.role` in their callbacks — the attribute names above match
> `onboarding.py`, so the reused selects drive this view unchanged. Confirm by
> reading `bot/cogs/onboarding.py:34-85`.

```python
class ApplicationModal(ModalErrorMixin, discord.ui.Modal):
    """The five free-text fields, then create the channel + fiche."""

    def __init__(self, guild_id, char_class, role, ephemeral, lang):
        super().__init__(title=i18n.t("recruit.modal_title", lang))
        self.guild_id = guild_id
        self.char_class = char_class
        self.role = role
        self.ephemeral = ephemeral
        self.lang = lang
        self.f_name = discord.ui.TextInput(
            label=i18n.t("recruit.name_label", lang), max_length=32
        )
        self.f_level = discord.ui.TextInput(
            label=i18n.t("recruit.level_label", lang), max_length=100, required=False
        )
        self.f_exp = discord.ui.TextInput(
            label=i18n.t("recruit.exp_label", lang),
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=False,
        )
        self.f_avail = discord.ui.TextInput(
            label=i18n.t("recruit.avail_label", lang), max_length=100, required=False
        )
        self.f_motivation = discord.ui.TextInput(
            label=i18n.t("recruit.motivation_label", lang),
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=False,
        )
        for item in (
            self.f_name,
            self.f_level,
            self.f_exp,
            self.f_avail,
            self.f_motivation,
        ):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruitment")
        await cog.submit_application(interaction, self)
```

**Step 2: Run the import smoke** — `python -c "import bot.cogs.recruitment"` (after Task 6 finishes the cog class; if run now it fails on the missing `Recruitment` cog — that's fine, it lands in Task 6). Commit with Task 6.

*(No standalone commit here — Task 4 and Task 6 form one importable module. Commit at the end of Task 6.)*

---

## Task 5: The review flow — accept / reject buttons + reason modal

**Files:**
- Modify: `bot/cogs/recruitment.py` (append)

**Step 1: The persistent decision buttons and the reject modal**

```python
class ReviewView(ViewErrorMixin, discord.ui.View):
    """Accept / Reject on a fiche. Persistent: each button carries the app id."""

    def __init__(self, app_id: int, lang: str = i18n.DEFAULT):
        super().__init__(timeout=None)
        self.add_item(DecisionButton(app_id, "accept", lang))
        self.add_item(DecisionButton(app_id, "reject", lang))


class DecisionButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"kisk:recruit:(?P<app_id>\d+):(?P<action>accept|reject)",
):
    def __init__(self, app_id: int, action: str, lang: str = i18n.DEFAULT):
        self.app_id = app_id
        self.action = action
        accept = action == "accept"
        super().__init__(
            discord.ui.Button(
                label=i18n.t(f"recruit.btn_{action}", lang),
                emoji="✅" if accept else "❌",
                style=discord.ButtonStyle.success if accept else discord.ButtonStyle.danger,
                custom_id=f"kisk:recruit:{app_id}:{action}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match["app_id"]), match["action"])

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruitment")
        await cog.decide(interaction, self.app_id, self.action)


class RejectReasonModal(ModalErrorMixin, discord.ui.Modal):
    def __init__(self, app_id: int, lang: str):
        super().__init__(title=i18n.t("recruit.reject_modal_title", lang))
        self.app_id = app_id
        self.lang = lang
        self.reason = discord.ui.TextInput(
            label=i18n.t("recruit.reject_reason_label", lang),
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=False,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruitment")
        await cog.finalize_reject(
            interaction, self.app_id, self.reason.value.strip() or None
        )
```

*(Wiring — `decide`, `finalize_reject`, `submit_application` — is implemented on the cog in Task 6.)*

---

## Task 6: The cog — join/leave listeners, `/recruit channel`, and the action methods

**Files:**
- Modify: `bot/cogs/recruitment.py` (append the cog class + `setup`)

**Step 1: The cog**

```python
@app_commands.guild_only()
class Recruitment(commands.Cog):
    """Applications: on-join DM, per-candidate channel, officer review."""

    recruit = app_commands.Group(
        name="recruit", description="Recruitment settings", guild_only=True
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- Config -----

    @recruit.command(name="channel", description="Review applications in this channel")
    @app_commands.describe(action="Enable in this channel, or disable")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Enable in this channel", value="on"),
            app_commands.Choice(name="Disable", value="off"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction, action: app_commands.Choice[str]):
        lang = await i18n.resolve_lang(self.bot.db, interaction.guild)
        value = interaction.channel_id if action.value == "on" else None
        await self.bot.db.set_setting(interaction.guild_id, "recruit_channel_id", value)
        key = "recruit.cmd_on" if action.value == "on" else "recruit.cmd_off"
        await interaction.response.send_message(i18n.t(key, lang), ephemeral=True)

    # ----- Join / leave -----

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = await self.bot.db.get_settings(member.guild.id)
        if not recruitment_enabled(settings):
            return  # feature off on this server -> no DM at all
        lang = await i18n.resolve_lang(self.bot.db, member.guild)
        try:
            await member.send(
                embed=self._invite_embed(member.guild, lang),
                view=self._apply_view(member.guild.id, lang),
            )
        except discord.Forbidden:
            await self._invite_in_channel(member, settings, lang)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        app = await self.bot.db.get_pending_application(member.guild.id, member.id)
        if app is None:
            return
        await self._teardown_channel(member.guild, app)
        await self._delete_fiche(member.guild, app)
        await self.bot.db.delete_application(app["id"])

    # ----- Application intake (called by ApplicationModal) -----

    async def submit_application(self, interaction, modal):
        db = self.bot.db
        guild = interaction.client.get_guild(modal.guild_id)
        lang = modal.lang
        settings = await db.get_settings(modal.guild_id)
        officers_channel = guild.get_channel(settings["recruit_channel_id"])
        # 1) create the row (returns id used in the fiche buttons + channel name)
        app_id = await db.create_application(
            guild_id=modal.guild_id,
            user_id=interaction.user.id,
            char_name=modal.f_name.value.strip(),
            char_class=modal.char_class,
            role=modal.role,
            level_cp=modal.f_level.value.strip() or None,
            experience=modal.f_exp.value.strip() or None,
            availability=modal.f_avail.value.strip() or None,
            motivation=modal.f_motivation.value.strip() or None,
        )
        # 2) create the dedicated candidate channel
        try:
            channel = await self._create_candidate_channel(
                guild, officers_channel, interaction.user, modal, settings
            )
        except discord.Forbidden:
            await db.delete_application(app_id)
            await interaction.response.send_message(
                i18n.t("recruit.missing_perm", lang), ephemeral=modal.ephemeral
            )
            return
        await channel.send(
            i18n.t("recruit.channel_welcome", lang, mention=interaction.user.mention),
            allowed_mentions=discord.AllowedMentions(users=[interaction.user]),
        )
        # 3) post the fiche in the officers' channel
        app = await db.get_application(app_id)
        fiche = await officers_channel.send(
            embed=self._fiche_embed(app, interaction.user, channel, lang),
            view=ReviewView(app_id, lang),
        )
        await db.set_application_card(app_id, channel.id, fiche.id)
        await interaction.response.send_message(
            i18n.t("recruit.submitted", lang), ephemeral=modal.ephemeral
        )

    # ----- Decision (called by DecisionButton / RejectReasonModal) -----

    async def decide(self, interaction, app_id, action):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        if not await member_is_admin(db, interaction.user):
            await interaction.response.send_message(
                i18n.t("recruit.not_officer", lang), ephemeral=True
            )
            return
        app = await db.get_application(app_id)
        if app is None or app["status"] != "pending":
            await interaction.response.send_message(
                i18n.t("recruit.already_decided", lang), ephemeral=True
            )
            return
        if action == "reject":
            await interaction.response.send_modal(RejectReasonModal(app_id, lang))
            return
        await self._accept(interaction, app, lang)

    async def _accept(self, interaction, app, lang):
        db = self.bot.db
        guild = interaction.guild
        settings = await db.get_settings(guild.id)
        role_id = settings["member_role_id"] if settings else None
        if not role_id:
            await interaction.response.send_message(
                i18n.t("recruit.no_member_role", lang), ephemeral=True
            )
            return
        member = guild.get_member(app["user_id"])
        if member is None:
            await interaction.response.send_message(
                i18n.t("recruit.applicant_gone", lang), ephemeral=True
            )
            return
        if not await db.set_application_status(
            app["id"], "accepted", reviewer_id=interaction.user.id, reason=None
        ):
            await interaction.response.send_message(
                i18n.t("recruit.already_decided", lang), ephemeral=True
            )
            return
        # Grant the role -> Onboarding.on_member_update DMs the profile setup.
        role = guild.get_role(role_id)
        await member.add_roles(role, reason="Recruitment: application accepted")
        try:
            await member.send(i18n.t("recruit.dm_accepted", lang, guild=guild.name))
        except discord.HTTPException:
            pass
        await self._teardown_channel(guild, app)
        await self._mark_fiche(
            interaction, app, "recruit.accepted_fiche", lang
        )

    async def finalize_reject(self, interaction, app_id, reason):
        db = self.bot.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        app = await db.get_application(app_id)
        if app is None or not await db.set_application_status(
            app_id, "rejected", reviewer_id=interaction.user.id, reason=reason
        ):
            await interaction.response.send_message(
                i18n.t("recruit.already_decided", lang), ephemeral=True
            )
            return
        member = interaction.guild.get_member(app["user_id"])
        if member is not None:
            key = "recruit.dm_rejected_reason" if reason else "recruit.dm_rejected"
            try:
                await member.send(
                    i18n.t(key, lang, guild=interaction.guild.name, reason=reason or "")
                )
            except discord.HTTPException:
                pass
        await self._teardown_channel(interaction.guild, app)
        await self._mark_fiche(interaction, app, "recruit.rejected_fiche", lang)
```

**Step 2: The Discord glue helpers** (embeds, channel create/teardown, fiche edit). Append:

```python
    # ----- Helpers -----

    def _apply_view(self, guild_id, lang):
        view = discord.ui.View(timeout=None)
        view.add_item(ApplyButton(guild_id, lang))
        return view

    def _invite_embed(self, guild, lang):
        return brand(
            discord.Embed(
                title=i18n.t("recruit.dm_title", lang, guild=guild.name),
                description=i18n.t("recruit.dm_body", lang),
                colour=discord.Colour.blurple(),
            )
        )

    async def _invite_in_channel(self, member, settings, lang):
        channel_id = settings["welcome_channel_id"] if settings else None
        channel = member.guild.get_channel(channel_id) if channel_id else None
        channel = channel or member.guild.system_channel
        if channel is None:
            return
        embed = self._invite_embed(member.guild, lang)
        embed.description = (
            i18n.t("recruit.dm_fallback_prefix", lang) + "\n\n" + (embed.description or "")
        )
        try:
            await channel.send(
                content=member.mention,
                embed=embed,
                view=self._apply_view(member.guild.id, lang),
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )
        except discord.HTTPException:
            pass

    async def _create_candidate_channel(
        self, guild, officers_channel, user, modal, settings
    ):
        spec = overwrite_spec(
            candidate_id=user.id,
            admin_role_id=settings["admin_role_id"] if settings else None,
            bot_id=guild.me.id,
        )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for object_id in spec["allow_view"]:
            target = guild.get_role(object_id) or guild.get_member(object_id) or guild.me
            overwrites[target] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True
            )
        return await guild.create_text_channel(
            name=channel_slug(modal.char_class, modal.f_name.value),
            category=officers_channel.category,
            overwrites=overwrites,
            reason=f"Recruitment: application from {user}",
        )

    async def _teardown_channel(self, guild, app):
        if not app["channel_id"]:
            return
        channel = guild.get_channel(app["channel_id"])
        if channel is not None:
            try:
                await channel.delete(reason="Recruitment: application closed")
            except discord.HTTPException:
                pass

    def _fiche_embed(self, app, user, channel, lang):
        emoji = config.CLASS_EMOJI.get(app["char_class"], "")
        embed = brand(
            discord.Embed(
                title=i18n.t("recruit.fiche_title", lang, name=app["char_name"]),
                description=i18n.t(
                    "recruit.fiche_class_role",
                    lang,
                    emoji=emoji,
                    cls=app["char_class"],
                    role=ROLE_LABELS.get(app["role"], app["role"]),
                ),
                colour=discord.Colour.blurple(),
            )
        )
        for key, field in (
            ("recruit.fiche_level", app["level_cp"]),
            ("recruit.fiche_exp", app["experience"]),
            ("recruit.fiche_avail", app["availability"]),
            ("recruit.fiche_motivation", app["motivation"]),
        ):
            if field:
                embed.add_field(name=i18n.t(key, lang), value=field, inline=False)
        embed.add_field(
            name="​",
            value=i18n.t("recruit.fiche_pending", lang, mention=user.mention),
            inline=False,
        )
        return embed

    async def _delete_fiche(self, guild, app):
        settings = await self.bot.db.get_settings(guild.id)
        channel_id = settings["recruit_channel_id"] if settings else None
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None or not app["card_message_id"]:
            return
        try:
            await channel.get_partial_message(app["card_message_id"]).delete()
        except discord.HTTPException:
            pass

    async def _mark_fiche(self, interaction, app, outcome_key, lang):
        """Edit the fiche in place: outcome banner, buttons removed (kept as a trace)."""
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        who = interaction.user.mention
        if embed is not None:
            embed.set_footer(text=i18n.t(outcome_key, lang, who=who))
        # The Accept path responds via edit; the Reject path came from a modal
        # (interaction.message is the modal's origin message = the fiche).
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Recruitment(bot))
```

> **Verify while implementing:**
> - `interaction.response.edit_message` in `_mark_fiche` must target the fiche.
>   For the Accept button the interaction *is* the fiche message → fine. For the
>   Reject modal, `interaction.message` is `None` on modal submit — instead capture
>   the fiche via `app["card_message_id"]` and edit it with
>   `channel.get_partial_message(...).edit(...)`, and use
>   `interaction.response.send_message(..., ephemeral=True)` (or `defer`) to ack the
>   modal. **Split `_mark_fiche` into a button variant (edit_message) and a modal
>   variant (fetch fiche by id + edit + ephemeral ack).** Adjust `finalize_reject`
>   accordingly.
> - `guild.me` requires the member cache; it is available in listeners/interactions.

**Step 3: Import smoke**

Run: `python -c "import bot.cogs.recruitment"`
Expected: no ImportError.

**Step 4: Commit** (Tasks 4–6 together — one importable module)

```bash
git add bot/cogs/recruitment.py
git commit -m "feat(recruitment): application form, per-candidate channel and officer review"
```

---

## Task 7: Register persistent items + load the cog

**Files:**
- Modify: `bot/main.py` (imports ~line 10; `setup_hook` ~lines 57 and 67)

**Step 1: Import and register** — add to imports:

```python
from .cogs.recruitment import ApplyButton, DecisionButton
```

After `self.add_dynamic_items(OnboardButton)`:

```python
        self.add_dynamic_items(ApplyButton)
        self.add_dynamic_items(DecisionButton)
```

And add to the extension list (after onboarding, before/after settings):

```python
        await self.load_extension("bot.cogs.recruitment")
```

**Step 2: Full import smoke**

Run: `python -c "import bot.main"`
Expected: no ImportError.

**Step 3: Run the whole suite + lint**

```bash
python -m pytest -q && ruff check bot tests && ruff format --check bot tests
```
Expected: all green. Fix E501 / format issues (wrap long lines to ≤88, honour magic trailing commas) until clean.

**Step 4: Commit**

```bash
git add bot/main.py
git commit -m "feat(recruitment): register persistent items and load the cog"
```

---

## Task 8: Docs (per the feature-docs habit)

**Files:**
- Modify: `README.md`, `README.fr.md`, `ROADMAP.md`, `ROADMAP.fr.md`, `CHANGELOG.md`
- Modify: the in-bot command help (grep for where `/availability` or `/onboard` is documented, e.g. a help cog / panel text, and add `/recruit`).

**Step 1:** Document the flow in both READMEs: what it does, the `/recruit channel` setup, that Accept grants the member role (so `/onboard role` must be set), and — prominently — the **new `Manage Channels` permission requirement**.

**Step 2:** ROADMAP (both languages): move recruitment into "done". CHANGELOG: an entry under the current version, e.g. `- Recruitment: on-join application flow with per-candidate channels and officer review (#PR).`

**Step 3:** In-bot help: add `/recruit channel` next to the other admin/setup commands.

**Step 4: Commit**

```bash
git add README.md README.fr.md ROADMAP.md ROADMAP.fr.md CHANGELOG.md
git commit -m "docs(recruitment): document the application flow and Manage Channels requirement"
```

---

## Task 9: Push + open PR + verify CI

**Step 1:** Push and open the PR against `claude/discord-bot-aion-groups-3bnutq` (use the repo's git-credential + GitHub API method; never print the token). PR body: what/why, the six locked decisions, the Manage Channels requirement, and the test plan. End with the Claude Code footer.

**Step 2:** Verify CI green (test 3.11 + 3.12, ruff, format) via the API check-runs loop before reporting to the user.

---

## Manual smoke checklist (post-merge, in a test guild)

1. `/recruit channel` (enable) in an officers-only channel; `/onboard role` set.
2. Join with an alt → receive the "Postuler" DM (or channel fallback with DMs closed).
3. Apply → dedicated channel appears (candidate + officers see it; others don't); fiche posts in the officers' channel.
4. Second apply while pending → "already in progress".
5. Reject with a reason → candidate DM'd, channel deleted, fiche shows "❌ Rejected by …".
6. Re-apply → allowed; Accept → member role granted, onboarding DM fires, channel deleted, fiche shows "✅ Accepted by …".
7. Apply then leave the server → channel + fiche + row all gone.
8. Remove the bot's Manage Channels perm → applying tells the candidate cleanly; no crash.
