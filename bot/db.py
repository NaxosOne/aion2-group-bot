"""SQLite storage: events, sign-ups, profiles, absences, polls, availability.

Each event is keyed by the ID of the Discord message that displays it, so
the buttons can find their event again even after a restart.

Note: a few table/column names are in French (dispos, dispo_marks,
dispo_channel_id...) — they are kept as-is for compatibility with databases
created by earlier versions.
"""

import os

import aiosqlite

from .db_boards import BoardsMixin
from .db_profiles import ProfilesMixin

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    message_id    INTEGER PRIMARY KEY,
    channel_id    INTEGER NOT NULL,
    guild_id      INTEGER NOT NULL,
    creator_id    INTEGER NOT NULL,
    creator_name  TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    activity      TEXT    NOT NULL,               -- Dungeon / PvP / ...
    description   TEXT,
    compo         TEXT    NOT NULL,               -- 'standard' or 'open'
    size          INTEGER NOT NULL,
    starts_at     INTEGER,                        -- UTC timestamp, NULL = no schedule
    status        TEXT    NOT NULL DEFAULT 'open',-- 'open', 'cancelled' or 'done'
    reminder_sent INTEGER NOT NULL DEFAULT 0,
    rsvp_sent     INTEGER NOT NULL DEFAULT 0,      -- 'are you coming?' prompt posted
    rsvp_prompt_id INTEGER,                        -- message id of that prompt
    voice_created INTEGER NOT NULL DEFAULT 0,      -- temp voice channel claimed
    voice_channel_id INTEGER,                      -- its channel, NULL once cleaned up
    groups        INTEGER NOT NULL DEFAULT 1       -- display groups; 1 = single party
);

CREATE TABLE IF NOT EXISTS signups (
    message_id   INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    display_name TEXT    NOT NULL,
    role         TEXT    NOT NULL,                -- 'tank', 'heal' or 'dps'
    joined_at    REAL    NOT NULL,
    character_id INTEGER,                         -- profiles.id, NULL = unspecified
    priority     INTEGER NOT NULL DEFAULT 0,      -- admin reorder; 0 = first-come order
    PRIMARY KEY (message_id, user_id)
);

-- One row per character: a member registers a main and as many alts as
-- they like. Exactly one of their rows carries is_main = 1.
CREATE TABLE IF NOT EXISTS profiles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    char_name  TEXT    NOT NULL COLLATE NOCASE,
    char_class TEXT    NOT NULL,
    role       TEXT    NOT NULL,                  -- 'tank', 'heal' or 'dps'
    is_main    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (guild_id, user_id, char_name)
);

CREATE TABLE IF NOT EXISTS absences (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id  INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    starts_on INTEGER NOT NULL,                   -- timestamp of first day at 00:00
    ends_on   INTEGER NOT NULL,                   -- timestamp of last day at 23:59
    reason    TEXT
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id           INTEGER PRIMARY KEY,
    welcome_channel_id INTEGER,                   -- channel greeting newcomers
    dispo_channel_id   INTEGER,                   -- weekly availability channel
    dispo_last_posted  INTEGER NOT NULL DEFAULT 0,
    event_channel_id   INTEGER,                   -- where events are posted
    absence_channel_id INTEGER,                   -- where absences are posted
    panel_channel_id   INTEGER,                   -- channel of the quick-actions panel
    panel_message_id   INTEGER,                   -- its message; /panel refreshes it
    admin_role_id      INTEGER,                   -- role treated as a Kisk admin
    voice_category_id  INTEGER,                   -- category for temp voice channels
    lfg_channel_id     INTEGER,                   -- channel of the LFG board
    lfg_message_id     INTEGER,                   -- its message; /lfg board edits it
    dashboard_channel_id INTEGER,                 -- channel of the legion dashboard
    dashboard_message_id INTEGER                  -- its message; auto-refreshed
);

CREATE TABLE IF NOT EXISTS polls (
    message_id INTEGER PRIMARY KEY,
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL,
    question   TEXT    NOT NULL,
    options    TEXT    NOT NULL,                  -- JSON list of choices
    status     TEXT    NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS poll_votes (
    message_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    choice     INTEGER NOT NULL,
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE IF NOT EXISTS dispos (
    message_id INTEGER PRIMARY KEY,
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    week_label TEXT    NOT NULL                   -- e.g. "week of 31/08"
);

CREATE TABLE IF NOT EXISTS dispo_marks (
    message_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    day        INTEGER NOT NULL,                  -- 0 = Monday ... 6 = Sunday
    PRIMARY KEY (message_id, user_id, day)
);

CREATE TABLE IF NOT EXISTS rsvp (
    message_id INTEGER NOT NULL,                  -- the event's message id
    user_id    INTEGER NOT NULL,
    status     TEXT    NOT NULL,                  -- 'yes' or 'no'
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE IF NOT EXISTS lfg_entries (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    activity   TEXT    NOT NULL,                  -- Dungeon / Raid / PvP / ...
    role       TEXT    NOT NULL,                  -- 'tank', 'heal' or 'dps'
    note       TEXT,                              -- optional free text
    expires_at INTEGER NOT NULL,                  -- UTC timestamp; pruned past this
    PRIMARY KEY (guild_id, user_id, activity)
);

CREATE TABLE IF NOT EXISTS available_now (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,                  -- UTC timestamp; pruned past this
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS recurrences (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    channel_id    INTEGER NOT NULL,
    creator_id    INTEGER NOT NULL,
    creator_name  TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    activity      TEXT    NOT NULL,
    description   TEXT,
    compo         TEXT    NOT NULL,
    size          INTEGER NOT NULL,
    ping_role_id  INTEGER,
    next_at       INTEGER NOT NULL,               -- next occurrence (UTC)
    active        INTEGER NOT NULL DEFAULT 1,
    groups        INTEGER NOT NULL DEFAULT 1       -- siege display groups; 1 = single
);
"""


class Database(ProfilesMixin, BoardsMixin):
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self._retire_slot_profiles()
        await self.conn.executescript(SCHEMA)
        await self._add_missing_columns()
        await self._import_slot_profiles()
        await self.conn.commit()

    async def _add_missing_columns(self) -> None:
        """Brings a database created by an earlier version up to date.

        CREATE TABLE IF NOT EXISTS leaves existing tables untouched, so
        columns added later have to be applied by hand.
        """
        added = {
            "guild_settings": {
                "event_channel_id": "INTEGER",
                "absence_channel_id": "INTEGER",
                "member_role_id": "INTEGER",  # role that means "validated member"
                "rsvp_channel_id": "INTEGER",  # where RSVP prompts are posted
                "language": "TEXT",  # 'fr' | 'en' | NULL = auto
                "panel_channel_id": "INTEGER",  # quick-actions panel location
                "panel_message_id": "INTEGER",  # so /panel refreshes it in place
                "admin_role_id": "INTEGER",  # role treated as a Kisk admin
                "voice_category_id": "INTEGER",  # category for temp voice channels
                "lfg_channel_id": "INTEGER",  # LFG board location
                "lfg_message_id": "INTEGER",  # so /lfg board refreshes it in place
                "dashboard_channel_id": "INTEGER",  # legion dashboard location
                "dashboard_message_id": "INTEGER",  # auto-refreshed in place
            },
            "signups": {
                "character_id": "INTEGER",  # which character the member brings
                "priority": "INTEGER NOT NULL DEFAULT 0",  # admin waitlist reorder
            },
            "events": {
                "rsvp_sent": "INTEGER NOT NULL DEFAULT 0",
                "rsvp_prompt_id": "INTEGER",
                "voice_created": "INTEGER NOT NULL DEFAULT 0",
                "voice_channel_id": "INTEGER",
                "groups": "INTEGER NOT NULL DEFAULT 1",
            },
            "recurrences": {
                "groups": "INTEGER NOT NULL DEFAULT 1",  # siege split, threaded
            },
        }
        for table, columns in added.items():
            async with self.conn.execute(f"PRAGMA table_info({table})") as cur:
                existing = {row["name"] for row in await cur.fetchall()}
            for name, kind in columns.items():
                if name not in existing:
                    await self.conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {kind}"
                    )

    async def _retire_slot_profiles(self) -> None:
        """Step 1 of the main/alt -> many-characters migration.

        Older databases key `profiles` on a 'main'/'alt' slot, which caps a
        member at two characters. Move that table aside so the schema above
        can create the new one; `_import_slot_profiles` refills it.
        """
        async with self.conn.execute("PRAGMA table_info(profiles)") as cur:
            columns = {row["name"] for row in await cur.fetchall()}
        if "slot" in columns:  # empty on a fresh database: nothing to migrate
            await self.conn.execute("ALTER TABLE profiles RENAME TO profiles_slots")

    async def _import_slot_profiles(self) -> None:
        """Step 2: copy the retired rows into the new table, then drop it.

        Mains are copied first so that if a member somehow gave their main and
        their alt the same name, the main is the one that survives the
        (guild_id, user_id, char_name) uniqueness constraint.
        """
        async with self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("profiles_slots",),
        ) as cur:
            if await cur.fetchone() is None:
                return
        await self.conn.execute(
            """INSERT OR IGNORE INTO profiles
                   (guild_id, user_id, char_name, char_class, role, is_main)
               SELECT guild_id, user_id, char_name, char_class, role, slot = 'main'
               FROM profiles_slots ORDER BY slot DESC"""
        )
        # A member who only ever registered an alt now has no main at all;
        # seat their oldest character so the roster and party lists still
        # have a class to show for them.
        await self.conn.execute(
            """UPDATE profiles SET is_main = 1 WHERE id IN (
                   SELECT MIN(id) FROM profiles
                   GROUP BY guild_id, user_id HAVING MAX(is_main) = 0)"""
        )
        await self.conn.execute("DROP TABLE profiles_slots")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # ----- Events -----

    async def create_event(self, **fields) -> None:
        columns = ", ".join(fields)
        placeholders = ", ".join("?" for _ in fields)
        await self.conn.execute(
            f"INSERT INTO events ({columns}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        await self.conn.commit()

    async def get_event(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM events WHERE message_id = ?", (message_id,)
        ) as cur:
            return await cur.fetchone()

    async def update_event_details(
        self,
        message_id: int,
        *,
        title: str,
        starts_at: int | None,
        description: str | None,
        rearm_notifications: bool = False,
    ) -> None:
        """Edits a posted event's text fields (title, schedule, description).

        When the schedule moved to a future time the caller sets
        `rearm_notifications`, which clears the reminder / RSVP "sent" flags so
        the loop fires them again against the new time.
        """
        if rearm_notifications:
            await self.conn.execute(
                """UPDATE events
                   SET title = ?, starts_at = ?, description = ?,
                       reminder_sent = 0, rsvp_sent = 0
                   WHERE message_id = ?""",
                (title, starts_at, description, message_id),
            )
        else:
            await self.conn.execute(
                """UPDATE events SET title = ?, starts_at = ?, description = ?
                   WHERE message_id = ?""",
                (title, starts_at, description, message_id),
            )
        await self.conn.commit()

    async def set_status(self, message_id: int, status: str) -> None:
        await self.conn.execute(
            "UPDATE events SET status = ? WHERE message_id = ?", (status, message_id)
        )
        await self.conn.commit()

    async def get_open_events(self, guild_id: int):
        """Every still-open event of the guild, for redeploying their messages."""
        async with self.conn.execute(
            "SELECT * FROM events WHERE guild_id = ? AND status = 'open'",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()

    async def get_panel(self, guild_id: int) -> "tuple[int, int] | None":
        """The (channel_id, message_id) of the guild's panel, or None if unset."""
        async with self.conn.execute(
            "SELECT panel_channel_id, panel_message_id FROM guild_settings "
            "WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None or row["panel_channel_id"] is None:
            return None
        return row["panel_channel_id"], row["panel_message_id"]

    async def set_panel(
        self, guild_id: int, channel_id: int | None, message_id: int | None
    ) -> None:
        """Remembers where the quick-actions panel lives so /panel can edit it."""
        await self.conn.execute(
            """INSERT INTO guild_settings
                   (guild_id, panel_channel_id, panel_message_id)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET
                   panel_channel_id = excluded.panel_channel_id,
                   panel_message_id = excluded.panel_message_id""",
            (guild_id, channel_id, message_id),
        )
        await self.conn.commit()

    async def upcoming_events(self, guild_id: int, now_ts: int):
        """Open events of the guild: unscheduled, or not started yet."""
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE guild_id = ? AND status = 'open'
                 AND (starts_at IS NULL OR starts_at >= ?)
               ORDER BY starts_at IS NULL, starts_at""",
            (guild_id, now_ts),
        ) as cur:
            return await cur.fetchall()

    async def next_upcoming_event(self, now_ts: int):
        """The next scheduled event across all guilds (for the bot status)."""
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE status = 'open' AND starts_at IS NOT NULL AND starts_at >= ?
               ORDER BY starts_at LIMIT 1""",
            (now_ts,),
        ) as cur:
            return await cur.fetchone()

    async def events_to_remind(self, now_ts: int, window_s: int):
        """Open events whose reminder is due (start within window_s seconds)."""
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE status = 'open' AND reminder_sent = 0
                 AND starts_at IS NOT NULL AND starts_at <= ?""",
            (now_ts + window_s,),
        ) as cur:
            return await cur.fetchall()

    async def mark_reminded(self, message_id: int) -> bool:
        """Atomically claims the reminder for a still-open event.

        Returns True only if this call is the one that claimed it (the event was
        open and not yet reminded). A cancelled/completed event — or one already
        claimed — returns False, so the loop skips it rather than pinging the
        party for an event that was cancelled between the due-query and the send.
        """
        cur = await self.conn.execute(
            "UPDATE events SET reminder_sent = 1 "
            "WHERE message_id = ? AND status = 'open' AND reminder_sent = 0",
            (message_id,),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # ----- Temporary voice channels -----

    async def events_due_for_voice(self, now_ts: int, lead_s: int, grace_s: int):
        """Open scheduled events whose temp voice channel should be created now.

        Within the lead window before the start, not yet claimed, and not so far
        past the start that they are certainly over.
        """
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE status = 'open' AND starts_at IS NOT NULL
                 AND voice_created = 0
                 AND starts_at <= ? AND starts_at > ?""",
            (now_ts + lead_s, now_ts - grace_s),
        ) as cur:
            return await cur.fetchall()

    async def mark_voice_created(self, message_id: int) -> bool:
        """Atomically claims the voice-channel creation for an open event."""
        cur = await self.conn.execute(
            "UPDATE events SET voice_created = 1 "
            "WHERE message_id = ? AND status = 'open' AND voice_created = 0",
            (message_id,),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def set_voice_channel(self, message_id: int, channel_id: int) -> None:
        await self.conn.execute(
            "UPDATE events SET voice_channel_id = ? WHERE message_id = ?",
            (channel_id, message_id),
        )
        await self.conn.commit()

    async def clear_voice_channel(self, message_id: int) -> None:
        """Forgets the channel (kept voice_created = 1 so it isn't recreated)."""
        await self.conn.execute(
            "UPDATE events SET voice_channel_id = NULL WHERE message_id = ?",
            (message_id,),
        )
        await self.conn.commit()

    async def events_with_stale_voice(self, now_ts: int, grace_s: int):
        """Events whose temp voice channel should be cleaned up."""
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE voice_channel_id IS NOT NULL
                 AND (status IN ('done', 'cancelled') OR starts_at < ?)""",
            (now_ts - grace_s,),
        ) as cur:
            return await cur.fetchall()

    # ----- Recurring events -----

    async def create_recurrence(self, **fields) -> int:
        columns = ", ".join(fields)
        placeholders = ", ".join("?" for _ in fields)
        cur = await self.conn.execute(
            f"INSERT INTO recurrences ({columns}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def recurrences_due(self, now_ts: int, lead_s: int):
        """Active recurrences whose next occurrence is within the lead window."""
        async with self.conn.execute(
            "SELECT * FROM recurrences WHERE active = 1 AND next_at <= ?",
            (now_ts + lead_s,),
        ) as cur:
            return await cur.fetchall()

    async def advance_recurrence(
        self, recurrence_id: int, old_next_at: int, new_next_at: int
    ) -> bool:
        """Atomically moves a recurrence to its next occurrence.

        Returns True only for the caller that claimed this occurrence, so two
        ticks can't post the same instance twice.
        """
        cur = await self.conn.execute(
            "UPDATE recurrences SET next_at = ? "
            "WHERE id = ? AND next_at = ? AND active = 1",
            (new_next_at, recurrence_id, old_next_at),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def list_recurrences(self, guild_id: int):
        async with self.conn.execute(
            "SELECT * FROM recurrences WHERE guild_id = ? AND active = 1 "
            "ORDER BY next_at",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()

    async def deactivate_recurrence(self, recurrence_id: int, guild_id: int) -> bool:
        cur = await self.conn.execute(
            "UPDATE recurrences SET active = 0 WHERE id = ? AND guild_id = ?",
            (recurrence_id, guild_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # ----- RSVP ("are you coming?" before the event) -----

    async def events_to_rsvp(self, now_ts: int, window_s: int):
        """Scheduled open events whose RSVP prompt is due and not yet sent."""
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE status = 'open' AND rsvp_sent = 0
                 AND starts_at IS NOT NULL AND starts_at <= ?""",
            (now_ts + window_s,),
        ) as cur:
            return await cur.fetchall()

    async def mark_rsvp_sent(self, message_id: int) -> bool:
        """Atomically claims the RSVP prompt for a still-open event.

        Returns True only if this call claimed it (open and not yet sent); a
        cancelled/completed or already-claimed event returns False, so the loop
        posts the 'are you coming?' prompt at most once and never for an event
        that was cancelled between the due-query and the send.
        """
        cur = await self.conn.execute(
            "UPDATE events SET rsvp_sent = 1 "
            "WHERE message_id = ? AND status = 'open' AND rsvp_sent = 0",
            (message_id,),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def set_rsvp_prompt_id(self, message_id: int, prompt_id: int) -> None:
        await self.conn.execute(
            "UPDATE events SET rsvp_prompt_id = ? WHERE message_id = ?",
            (prompt_id, message_id),
        )
        await self.conn.commit()

    async def get_event_by_rsvp_prompt(self, prompt_id: int):
        """The event a given RSVP prompt message belongs to (for its buttons)."""
        async with self.conn.execute(
            "SELECT * FROM events WHERE rsvp_prompt_id = ?", (prompt_id,)
        ) as cur:
            return await cur.fetchone()

    async def set_rsvp(self, message_id: int, user_id: int, status: str) -> None:
        await self.conn.execute(
            """INSERT OR REPLACE INTO rsvp (message_id, user_id, status)
               VALUES (?, ?, ?)""",
            (message_id, user_id, status),
        )
        await self.conn.commit()

    async def get_rsvps(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM rsvp WHERE message_id = ?", (message_id,)
        ) as cur:
            return await cur.fetchall()

    # ----- Per-guild settings -----

    async def get_settings(self, guild_id: int):
        async with self.conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ) as cur:
            return await cur.fetchone()

    async def set_setting(self, guild_id: int, column: str, value) -> None:
        # `column` always comes from the code (never from user input).
        await self.conn.execute(
            f"""INSERT INTO guild_settings (guild_id, {column}) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET {column} = excluded.{column}""",
            (guild_id, value),
        )
        await self.conn.commit()

    async def get_language(self, guild_id: int) -> str | None:
        row = await self.get_settings(guild_id)
        return row["language"] if row else None

    async def set_language(self, guild_id: int, lang: str | None) -> None:
        await self.set_setting(guild_id, "language", lang)

    async def guilds_with_availability(self):
        """Guilds where the weekly availability board is enabled."""
        async with self.conn.execute(
            "SELECT * FROM guild_settings WHERE dispo_channel_id IS NOT NULL"
        ) as cur:
            return await cur.fetchall()

    # ----- Polls (/vote) -----

    async def create_poll(
        self,
        message_id: int,
        guild_id: int,
        channel_id: int,
        creator_id: int,
        question: str,
        options_json: str,
    ) -> None:
        await self.conn.execute(
            """INSERT INTO polls
               (message_id, guild_id, channel_id, creator_id, question, options)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, guild_id, channel_id, creator_id, question, options_json),
        )
        await self.conn.commit()

    async def get_poll(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM polls WHERE message_id = ?", (message_id,)
        ) as cur:
            return await cur.fetchone()

    async def set_poll_status(self, message_id: int, status: str) -> None:
        await self.conn.execute(
            "UPDATE polls SET status = ? WHERE message_id = ?", (status, message_id)
        )
        await self.conn.commit()

    async def set_vote(self, message_id: int, user_id: int, choice: int) -> None:
        await self.conn.execute(
            """INSERT OR REPLACE INTO poll_votes (message_id, user_id, choice)
               VALUES (?, ?, ?)""",
            (message_id, user_id, choice),
        )
        await self.conn.commit()

    async def get_votes(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM poll_votes WHERE message_id = ? ORDER BY rowid",
            (message_id,),
        ) as cur:
            return await cur.fetchall()

    # ----- Weekly availability (/availability) -----

    async def create_availability(
        self, message_id: int, guild_id: int, channel_id: int, week_label: str
    ) -> None:
        await self.conn.execute(
            """INSERT INTO dispos (message_id, guild_id, channel_id, week_label)
               VALUES (?, ?, ?, ?)""",
            (message_id, guild_id, channel_id, week_label),
        )
        await self.conn.commit()

    async def get_availability(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM dispos WHERE message_id = ?", (message_id,)
        ) as cur:
            return await cur.fetchone()

    async def toggle_availability(
        self, message_id: int, user_id: int, day: int
    ) -> bool:
        """Ticks/unticks a day. Returns True if the day was just ticked."""
        cur = await self.conn.execute(
            "DELETE FROM dispo_marks WHERE message_id = ? AND user_id = ? AND day = ?",
            (message_id, user_id, day),
        )
        if cur.rowcount:
            await self.conn.commit()
            return False
        await self.conn.execute(
            "INSERT INTO dispo_marks (message_id, user_id, day) VALUES (?, ?, ?)",
            (message_id, user_id, day),
        )
        await self.conn.commit()
        return True

    async def clear_availability(self, message_id: int, user_id: int) -> None:
        """Removes every day a member ticked on a board."""
        await self.conn.execute(
            "DELETE FROM dispo_marks WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        )
        await self.conn.commit()

    async def get_availability_marks(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM dispo_marks WHERE message_id = ? ORDER BY rowid",
            (message_id,),
        ) as cur:
            return await cur.fetchall()
