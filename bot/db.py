"""SQLite storage: events, sign-ups, profiles, absences, polls, availability.

Each event is keyed by the ID of the Discord message that displays it, so
the buttons can find their event again even after a restart.

Note: a few table/column names are in French (dispos, dispo_marks,
dispo_channel_id...) — they are kept as-is for compatibility with databases
created by earlier versions.
"""

import os

import aiosqlite

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
    reminder_sent INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS signups (
    message_id   INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    display_name TEXT    NOT NULL,
    role         TEXT    NOT NULL,                -- 'tank', 'heal' or 'dps'
    joined_at    REAL    NOT NULL,
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE IF NOT EXISTS profiles (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    slot       TEXT    NOT NULL,                  -- 'main' or 'alt'
    char_name  TEXT    NOT NULL,
    char_class TEXT    NOT NULL,
    role       TEXT    NOT NULL,                  -- 'tank', 'heal' or 'dps'
    PRIMARY KEY (guild_id, user_id, slot)
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
    absence_channel_id INTEGER                    -- where absences are posted
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
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self._add_missing_columns()
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
                "member_role_id": "INTEGER",    # role that means "validated member"
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

    async def set_status(self, message_id: int, status: str) -> None:
        await self.conn.execute(
            "UPDATE events SET status = ? WHERE message_id = ?", (status, message_id)
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

    async def mark_reminded(self, message_id: int) -> None:
        await self.conn.execute(
            "UPDATE events SET reminder_sent = 1 WHERE message_id = ?", (message_id,)
        )
        await self.conn.commit()

    # ----- Sign-ups -----

    async def get_signups(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM signups WHERE message_id = ? ORDER BY joined_at",
            (message_id,),
        ) as cur:
            return await cur.fetchall()

    async def get_signup(self, message_id: int, user_id: int):
        async with self.conn.execute(
            "SELECT * FROM signups WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        ) as cur:
            return await cur.fetchone()

    async def upsert_signup(
        self, message_id: int, user_id: int, display_name: str, role: str, joined_at: float
    ) -> None:
        # REPLACE also overwrites joined_at: switching roles sends you to the
        # back of the queue, so you can never bump someone out of the party.
        await self.conn.execute(
            """INSERT OR REPLACE INTO signups
               (message_id, user_id, display_name, role, joined_at)
               VALUES (?, ?, ?, ?, ?)""",
            (message_id, user_id, display_name, role, joined_at),
        )
        await self.conn.commit()

    async def remove_signup(self, message_id: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM signups WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # ----- Profiles (main / alt) -----

    async def set_profile(
        self, guild_id: int, user_id: int, slot: str,
        char_name: str, char_class: str, role: str,
    ) -> None:
        await self.conn.execute(
            """INSERT OR REPLACE INTO profiles
               (guild_id, user_id, slot, char_name, char_class, role)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (guild_id, user_id, slot, char_name, char_class, role),
        )
        await self.conn.commit()

    async def get_profiles(self, guild_id: int, user_id: int):
        """A member's characters, main first ('main' > 'alt' in DESC order)."""
        async with self.conn.execute(
            """SELECT * FROM profiles WHERE guild_id = ? AND user_id = ?
               ORDER BY slot DESC""",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchall()

    async def all_profiles(self, guild_id: int):
        async with self.conn.execute(
            "SELECT * FROM profiles WHERE guild_id = ? ORDER BY user_id, slot DESC",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()

    async def has_main_profile(self, guild_id: int, user_id: int) -> bool:
        """Whether the member has registered their main character (onboarded)."""
        async with self.conn.execute(
            """SELECT 1 FROM profiles
               WHERE guild_id = ? AND user_id = ? AND slot = 'main' LIMIT 1""",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchone() is not None

    async def get_main_classes(self, guild_id: int, user_ids: list) -> dict:
        """{user_id: main character's class} to display classes in parties."""
        if not user_ids:
            return {}
        placeholders = ",".join("?" for _ in user_ids)
        async with self.conn.execute(
            f"""SELECT user_id, char_class FROM profiles
                WHERE guild_id = ? AND slot = 'main' AND user_id IN ({placeholders})""",
            (guild_id, *user_ids),
        ) as cur:
            return {row["user_id"]: row["char_class"] for row in await cur.fetchall()}

    # ----- Absences -----

    async def add_absence(
        self, guild_id: int, user_id: int, starts_on: int, ends_on: int, reason: str | None
    ) -> None:
        await self.conn.execute(
            """INSERT INTO absences (guild_id, user_id, starts_on, ends_on, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, starts_on, ends_on, reason),
        )
        await self.conn.commit()

    async def clear_absences(self, guild_id: int, user_id: int, now_ts: int) -> int:
        """Cancels a member's current or upcoming absences. Returns the count."""
        cur = await self.conn.execute(
            "DELETE FROM absences WHERE guild_id = ? AND user_id = ? AND ends_on >= ?",
            (guild_id, user_id, now_ts),
        )
        await self.conn.commit()
        return cur.rowcount

    async def list_absences(self, guild_id: int, now_ts: int):
        """Current or upcoming absences of the guild, sorted by start date."""
        async with self.conn.execute(
            """SELECT * FROM absences WHERE guild_id = ? AND ends_on >= ?
               ORDER BY starts_on""",
            (guild_id, now_ts),
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

    async def guilds_with_availability(self):
        """Guilds where the weekly availability board is enabled."""
        async with self.conn.execute(
            "SELECT * FROM guild_settings WHERE dispo_channel_id IS NOT NULL"
        ) as cur:
            return await cur.fetchall()

    # ----- Polls (/vote) -----

    async def create_poll(
        self, message_id: int, guild_id: int, channel_id: int,
        creator_id: int, question: str, options_json: str,
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

    async def toggle_availability(self, message_id: int, user_id: int, day: int) -> bool:
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

    async def get_availability_marks(self, message_id: int):
        async with self.conn.execute(
            "SELECT * FROM dispo_marks WHERE message_id = ? ORDER BY rowid",
            (message_id,),
        ) as cur:
            return await cur.fetchall()
