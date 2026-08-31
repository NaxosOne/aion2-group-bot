"""Storage for member characters, sign-ups and absences.

Mixed into Database (see db.py).
"""


class ProfilesMixin:
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
        self,
        message_id: int,
        user_id: int,
        display_name: str,
        role: str,
        joined_at: float,
        character_id: int | None = None,
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
        self,
        guild_id: int,
        user_id: int,
        char_name: str,
        char_class: str,
        role: str,
        make_main: bool = False,
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

        if make_main or (
            is_first and await self.count_characters(guild_id, user_id) == 1
        ):
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

        Profiles, absences, LFG entries and the "available now" status are keyed
        by guild_id; sign-ups, poll votes and availability marks are keyed by
        message_id, so they are filtered through their parent table's guild_id.
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
        await self.conn.execute(
            "DELETE FROM lfg_entries WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.execute(
            "DELETE FROM available_now WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
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
        self,
        guild_id: int,
        user_id: int,
        starts_on: int,
        ends_on: int,
        reason: str | None,
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
