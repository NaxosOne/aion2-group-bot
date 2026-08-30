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
    reminder_sent INTEGER NOT NULL DEFAULT 0,
    rsvp_sent     INTEGER NOT NULL DEFAULT 0,      -- 'are you coming?' prompt posted
    rsvp_prompt_id INTEGER,                        -- message id of that prompt
    voice_created INTEGER NOT NULL DEFAULT 0,      -- temp voice channel claimed
    voice_channel_id INTEGER,                      -- its channel, NULL once cleaned up
    groups        INTEGER NOT NULL DEFAULT 1       -- display groups (sieges); 1 = single party
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
    panel_message_id   INTEGER,                   -- its message, so /panel can refresh it
    admin_role_id      INTEGER,                   -- role treated as a Kisk admin
    voice_category_id  INTEGER                    -- category for temp event voice channels
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
    active        INTEGER NOT NULL DEFAULT 1
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
                "member_role_id": "INTEGER",    # role that means "validated member"
                "rsvp_channel_id": "INTEGER",   # where RSVP prompts are posted
                "language": "TEXT",             # 'fr' | 'en' | NULL = auto
                "panel_channel_id": "INTEGER",  # quick-actions panel location
                "panel_message_id": "INTEGER",  # so /panel refreshes it in place
                "admin_role_id": "INTEGER",     # role treated as a Kisk admin
                "voice_category_id": "INTEGER", # category for temp voice channels
            },
            "signups": {
                "character_id": "INTEGER",      # which character the member brings
                "priority": "INTEGER NOT NULL DEFAULT 0",  # admin waitlist reorder
            },
            "events": {
                "rsvp_sent": "INTEGER NOT NULL DEFAULT 0",
                "rsvp_prompt_id": "INTEGER",
                "voice_created": "INTEGER NOT NULL DEFAULT 0",
                "voice_channel_id": "INTEGER",
                "groups": "INTEGER NOT NULL DEFAULT 1",
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
        self, message_id: int, *, title: str, starts_at: int | None,
        description: str | None, rearm_notifications: bool = False,
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

    # ----- Sign-ups -----

    async def get_signups(self, message_id: int):
        """Sign-ups, oldest first, each carrying its character when one is set.

        The join is outer: members who never registered a profile — and
        sign-ups whose character has since been deleted — keep their spot with
        char_name / char_class left NULL.
        """
        async with self.conn.execute(
            """SELECT s.*, p.char_name, p.char_class
               FROM signups s LEFT JOIN profiles p ON p.id = s.character_id
               WHERE s.message_id = ? ORDER BY s.joined_at""",
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
        self, message_id: int, user_id: int, display_name: str, role: str,
        joined_at: float, character_id: int | None = None,
    ) -> None:
        # REPLACE also overwrites joined_at: switching roles sends you to the
        # back of the queue, so you can never bump someone out of the party.
        await self.conn.execute(
            """INSERT OR REPLACE INTO signups
               (message_id, user_id, display_name, role, joined_at, character_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, user_id, display_name, role, joined_at, character_id),
        )
        await self.conn.commit()

    async def set_signup_character(
        self, message_id: int, user_id: int, character_id: int | None
    ) -> bool:
        """Swaps the character brought to an event, keeping the queue position.

        Unlike upsert_signup this leaves joined_at alone: bringing another
        character is not a re-sign-up, so it must not cost the member their
        spot in the party.
        """
        cur = await self.conn.execute(
            "UPDATE signups SET character_id = ? WHERE message_id = ? AND user_id = ?",
            (character_id, message_id, user_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def set_signup_priorities(
        self, message_id: int, priorities: dict[int, int]
    ) -> None:
        """Persist an admin waitlist reorder as per-sign-up priority values.

        `priorities` maps user_id -> priority; higher floats towards the front.
        Only the given members are touched, so absent sign-ups keep their value.
        """
        await self.conn.executemany(
            "UPDATE signups SET priority = ? WHERE message_id = ? AND user_id = ?",
            [(prio, message_id, uid) for uid, prio in priorities.items()],
        )
        await self.conn.commit()

    async def remove_signup(self, message_id: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM signups WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # ----- Profiles (the members' characters) -----

    async def add_character(
        self, guild_id: int, user_id: int, char_name: str, char_class: str,
        role: str, make_main: bool = False,
    ) -> int:
        """Registers a character, or updates the one already under that name.

        Names are matched case-insensitively, so re-running the command on
        "kratos" edits Kratos rather than creating a twin. A member's first
        character always becomes their main, whatever `make_main` says: the
        party lists and the roster need one to fall back on.
        """
        async with self.conn.execute(
            """SELECT id FROM profiles
               WHERE guild_id = ? AND user_id = ? AND char_name = ?""",
            (guild_id, user_id, char_name),
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            cur = await self.conn.execute(
                """INSERT INTO profiles
                       (guild_id, user_id, char_name, char_class, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (guild_id, user_id, char_name, char_class, role),
            )
            character_id, is_first = cur.lastrowid, True
        else:
            character_id, is_first = row["id"], False
            await self.conn.execute(
                """UPDATE profiles SET char_name = ?, char_class = ?, role = ?
                   WHERE id = ?""",
                (char_name, char_class, role, character_id),
            )

        if make_main or (is_first and await self.count_characters(guild_id, user_id) == 1):
            await self._seat_main(guild_id, user_id, character_id)
        await self.conn.commit()
        return character_id

    async def _seat_main(self, guild_id: int, user_id: int, character_id: int) -> None:
        """Makes `character_id` the one row of that member carrying is_main."""
        await self.conn.execute(
            "UPDATE profiles SET is_main = (id = ?) WHERE guild_id = ? AND user_id = ?",
            (character_id, guild_id, user_id),
        )

    async def _reseat_main(self, guild_id: int, user_id: int) -> None:
        """Keeps a main seated after a deletion.

        Ordering by is_main first leaves an untouched main in place and
        otherwise promotes the member's oldest remaining character.
        """
        async with self.conn.execute(
            """SELECT id FROM profiles WHERE guild_id = ? AND user_id = ?
               ORDER BY is_main DESC, id LIMIT 1""",
            (guild_id, user_id),
        ) as cur:
            row = await cur.fetchone()
        if row is not None:
            await self._seat_main(guild_id, user_id, row["id"])

    async def set_main_character(
        self, guild_id: int, user_id: int, character_id: int
    ) -> bool:
        """Promotes one of the member's own characters to main."""
        if await self.get_character(guild_id, user_id, character_id) is None:
            return False
        await self._seat_main(guild_id, user_id, character_id)
        await self.conn.commit()
        return True

    async def count_characters(self, guild_id: int, user_id: int) -> int:
        async with self.conn.execute(
            "SELECT COUNT(*) AS n FROM profiles WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cur:
            return (await cur.fetchone())["n"]

    async def get_profiles(self, guild_id: int, user_id: int):
        """A member's characters: main first, then by class, then by name."""
        async with self.conn.execute(
            """SELECT * FROM profiles WHERE guild_id = ? AND user_id = ?
               ORDER BY is_main DESC, char_class, char_name""",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchall()

    async def get_character(self, guild_id: int, user_id: int, character_id: int):
        """One character, scoped to its owner so ids can't be borrowed."""
        async with self.conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND guild_id = ? AND user_id = ?",
            (character_id, guild_id, user_id),
        ) as cur:
            return await cur.fetchone()

    async def profile_user_ids(self, guild_id: int) -> list:
        """Every member with at least one character on this server."""
        async with self.conn.execute(
            "SELECT DISTINCT user_id FROM profiles WHERE guild_id = ?", (guild_id,)
        ) as cur:
            return [row["user_id"] for row in await cur.fetchall()]

    async def all_profiles(self, guild_id: int):
        async with self.conn.execute(
            """SELECT * FROM profiles WHERE guild_id = ?
               ORDER BY user_id, is_main DESC, char_class, char_name""",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()

    async def has_main_profile(self, guild_id: int, user_id: int) -> bool:
        """Whether the member has registered a character at all (onboarded)."""
        async with self.conn.execute(
            """SELECT 1 FROM profiles
               WHERE guild_id = ? AND user_id = ? AND is_main = 1 LIMIT 1""",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchone() is not None

    async def delete_profile(
        self, guild_id: int, user_id: int, character_id: int | None = None
    ) -> int:
        """Deletes one character, or every one of them. Returns the row count."""
        if character_id is None:
            cur = await self.conn.execute(
                "DELETE FROM profiles WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
        else:
            cur = await self.conn.execute(
                "DELETE FROM profiles WHERE guild_id = ? AND user_id = ? AND id = ?",
                (guild_id, user_id, character_id),
            )
        await self._reseat_main(guild_id, user_id)
        await self.conn.commit()
        return cur.rowcount

    async def purge_member(self, guild_id: int, user_id: int) -> None:
        """Removes every trace of a member from a guild (they left/were removed).

        Profiles and absences are keyed by guild_id; sign-ups, poll votes and
        availability marks are keyed by message_id, so they are filtered through
        their parent table's guild_id.
        """
        await self.conn.execute(
            "DELETE FROM profiles WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.execute(
            "DELETE FROM absences WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.execute(
            """DELETE FROM signups WHERE user_id = ? AND message_id IN
               (SELECT message_id FROM events WHERE guild_id = ?)""",
            (user_id, guild_id),
        )
        await self.conn.execute(
            """DELETE FROM poll_votes WHERE user_id = ? AND message_id IN
               (SELECT message_id FROM polls WHERE guild_id = ?)""",
            (user_id, guild_id),
        )
        await self.conn.execute(
            """DELETE FROM dispo_marks WHERE user_id = ? AND message_id IN
               (SELECT message_id FROM dispos WHERE guild_id = ?)""",
            (user_id, guild_id),
        )
        await self.conn.execute(
            """DELETE FROM rsvp WHERE user_id = ? AND message_id IN
               (SELECT message_id FROM events WHERE guild_id = ?)""",
            (user_id, guild_id),
        )
        await self.conn.commit()


    async def get_main_classes(self, guild_id: int, user_ids: list) -> dict:
        """{user_id: main character's class}, for members who signed up
        without naming a character."""
        if not user_ids:
            return {}
        placeholders = ",".join("?" for _ in user_ids)
        async with self.conn.execute(
            f"""SELECT user_id, char_class FROM profiles
                WHERE guild_id = ? AND is_main = 1 AND user_id IN ({placeholders})""",
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
