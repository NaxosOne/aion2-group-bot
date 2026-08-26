"""Accès à la base SQLite : sorties (events) et inscriptions (signups).

Chaque sortie est identifiée par l'ID du message Discord qui l'affiche,
ce qui permet aux boutons de retrouver la sortie même après un redémarrage.
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
    activity      TEXT    NOT NULL,               -- Donjon / PvP / Autre
    description   TEXT,
    compo         TEXT    NOT NULL,               -- 'standard' ou 'libre'
    size          INTEGER NOT NULL,
    starts_at     INTEGER,                        -- timestamp UTC, NULL = pas d'horaire
    status        TEXT    NOT NULL DEFAULT 'open',-- 'open' ou 'cancelled'
    reminder_sent INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS signups (
    message_id   INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    display_name TEXT    NOT NULL,
    role         TEXT    NOT NULL,                -- 'tank', 'heal' ou 'dps'
    joined_at    REAL    NOT NULL,
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE IF NOT EXISTS profiles (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    slot       TEXT    NOT NULL,                  -- 'main' ou 'alt'
    char_name  TEXT    NOT NULL,
    char_class TEXT    NOT NULL,
    role       TEXT    NOT NULL,                  -- 'tank', 'heal' ou 'dps'
    PRIMARY KEY (guild_id, user_id, slot)
);

CREATE TABLE IF NOT EXISTS absences (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id  INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    starts_on INTEGER NOT NULL,                   -- timestamp du 1er jour à minuit
    ends_on   INTEGER NOT NULL,                   -- timestamp du dernier jour à 23h59
    reason    TEXT
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        dossier = os.path.dirname(self.path)
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # ----- Sorties -----

    async def create_event(self, **champs) -> None:
        colonnes = ", ".join(champs)
        marqueurs = ", ".join("?" for _ in champs)
        await self.conn.execute(
            f"INSERT INTO events ({colonnes}) VALUES ({marqueurs})",
            tuple(champs.values()),
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
        """Sorties ouvertes du serveur : sans horaire, ou pas encore commencées."""
        async with self.conn.execute(
            """SELECT * FROM events
               WHERE guild_id = ? AND status = 'open'
                 AND (starts_at IS NULL OR starts_at >= ?)
               ORDER BY starts_at IS NULL, starts_at""",
            (guild_id, now_ts),
        ) as cur:
            return await cur.fetchall()

    async def events_to_remind(self, now_ts: int, window_s: int):
        """Sorties ouvertes dont le rappel doit partir (début dans <= window_s)."""
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

    # ----- Inscriptions -----

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
        # REPLACE écrase aussi joined_at : changer de rôle remet en fin de file,
        # ce qui garantit qu'on ne peut jamais éjecter un titulaire du groupe.
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

    # ----- Profils (main / alt) -----

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
        """Les persos d'un membre, main en premier ('main' > 'alt' en tri DESC)."""
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

    async def get_main_classes(self, guild_id: int, user_ids: list) -> dict:
        """{user_id: classe du main} pour afficher la classe dans les groupes."""
        if not user_ids:
            return {}
        marqueurs = ",".join("?" for _ in user_ids)
        async with self.conn.execute(
            f"""SELECT user_id, char_class FROM profiles
                WHERE guild_id = ? AND slot = 'main' AND user_id IN ({marqueurs})""",
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
        """Annule les absences en cours ou à venir d'un membre. Retourne le nombre."""
        cur = await self.conn.execute(
            "DELETE FROM absences WHERE guild_id = ? AND user_id = ? AND ends_on >= ?",
            (guild_id, user_id, now_ts),
        )
        await self.conn.commit()
        return cur.rowcount

    async def list_absences(self, guild_id: int, now_ts: int):
        """Absences en cours ou à venir du serveur, triées par date de début."""
        async with self.conn.execute(
            """SELECT * FROM absences WHERE guild_id = ? AND ends_on >= ?
               ORDER BY starts_on""",
            (guild_id, now_ts),
        ) as cur:
            return await cur.fetchall()
