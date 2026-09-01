"""Storage for the LFG pool, available-now status and the legion dashboard.

Mixed into Database (see db.py).
"""


class BoardsMixin:
    # ----- Looking for group (/lfg) -----

    async def set_lfg_looking(
        self,
        guild_id: int,
        user_id: int,
        activity: str,
        role: str,
        note: str | None,
        expires_at: int,
    ) -> None:
        """Adds a member to the pool for an activity, or refreshes their entry.

        One entry per (guild, member, activity): re-signalling the same activity
        updates the role, note and expiry rather than piling up duplicates.
        """
        await self.conn.execute(
            """INSERT INTO lfg_entries
                   (guild_id, user_id, activity, role, note, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(guild_id, user_id, activity) DO UPDATE SET
                   role = excluded.role,
                   note = excluded.note,
                   expires_at = excluded.expires_at""",
            (guild_id, user_id, activity, role, note, expires_at),
        )
        await self.conn.commit()

    async def remove_lfg(
        self, guild_id: int, user_id: int, activity: str | None = None
    ) -> int:
        """Drops a member's entries — one activity, or all of them. Returns the
        number of rows removed."""
        if activity is None:
            cur = await self.conn.execute(
                "DELETE FROM lfg_entries WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
        else:
            cur = await self.conn.execute(
                "DELETE FROM lfg_entries "
                "WHERE guild_id = ? AND user_id = ? AND activity = ?",
                (guild_id, user_id, activity),
            )
        await self.conn.commit()
        return cur.rowcount

    async def get_lfg_pool(self, guild_id: int, now_ts: int):
        """The guild's live pool (expired entries excluded), soonest expiry first
        within each activity."""
        async with self.conn.execute(
            """SELECT * FROM lfg_entries
               WHERE guild_id = ? AND expires_at > ?
               ORDER BY activity, expires_at, rowid""",
            (guild_id, now_ts),
        ) as cur:
            return await cur.fetchall()

    async def prune_lfg(self, now_ts: int) -> int:
        """Deletes every expired entry across all guilds. Returns the row count,
        so the scheduler only refreshes the boards when something changed."""
        cur = await self.conn.execute(
            "DELETE FROM lfg_entries WHERE expires_at <= ?", (now_ts,)
        )
        await self.conn.commit()
        return cur.rowcount

    async def get_lfg_board(self, guild_id: int) -> "tuple[int, int] | None":
        """The (channel_id, message_id) of the guild's LFG board, or None."""
        async with self.conn.execute(
            "SELECT lfg_channel_id, lfg_message_id FROM guild_settings "
            "WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None or row["lfg_channel_id"] is None:
            return None
        return row["lfg_channel_id"], row["lfg_message_id"]

    async def set_lfg_board(
        self, guild_id: int, channel_id: int | None, message_id: int | None
    ) -> None:
        """Remembers where the LFG board lives so /lfg board can edit it."""
        await self.conn.execute(
            """INSERT INTO guild_settings
                   (guild_id, lfg_channel_id, lfg_message_id)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET
                   lfg_channel_id = excluded.lfg_channel_id,
                   lfg_message_id = excluded.lfg_message_id""",
            (guild_id, channel_id, message_id),
        )
        await self.conn.commit()

    async def guilds_with_lfg_board(self):
        """Guilds that have posted an LFG board (for the pruning refresh loop)."""
        async with self.conn.execute(
            "SELECT guild_id, lfg_channel_id, lfg_message_id FROM guild_settings "
            "WHERE lfg_message_id IS NOT NULL"
        ) as cur:
            return await cur.fetchall()

    # ----- Available now (shown on the LFG board) -----

    async def set_available(self, guild_id: int, user_id: int, expires_at: int) -> None:
        """Marks a member available (or refreshes their window)."""
        await self.conn.execute(
            """INSERT INTO available_now (guild_id, user_id, expires_at)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id, user_id) DO UPDATE SET
                   expires_at = excluded.expires_at""",
            (guild_id, user_id, expires_at),
        )
        await self.conn.commit()

    async def remove_available(self, guild_id: int, user_id: int) -> int:
        """Clears a member's available status. Returns the number of rows removed."""
        cur = await self.conn.execute(
            "DELETE FROM available_now WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.commit()
        return cur.rowcount

    async def toggle_available(
        self, guild_id: int, user_id: int, now_ts: int, expires_at: int
    ) -> bool:
        """Flips a member's available status. Returns True if now available.

        A row whose window already lapsed counts as off, so toggling re-arms it.
        """
        async with self.conn.execute(
            "SELECT expires_at FROM available_now WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cur:
            row = await cur.fetchone()
        if row is not None and row["expires_at"] > now_ts:
            await self.remove_available(guild_id, user_id)
            return False
        await self.set_available(guild_id, user_id, expires_at)
        return True

    async def get_available(self, guild_id: int, now_ts: int):
        """The guild's live "available now" members, soonest expiry first."""
        async with self.conn.execute(
            """SELECT * FROM available_now
               WHERE guild_id = ? AND expires_at > ?
               ORDER BY expires_at, rowid""",
            (guild_id, now_ts),
        ) as cur:
            return await cur.fetchall()

    async def prune_available(self, now_ts: int) -> int:
        """Deletes every lapsed available status. Returns the row count."""
        cur = await self.conn.execute(
            "DELETE FROM available_now WHERE expires_at <= ?", (now_ts,)
        )
        await self.conn.commit()
        return cur.rowcount

    # ----- Legion dashboard (/dashboard) -----

    async def get_dashboard(self, guild_id: int) -> "tuple[int, int] | None":
        """The (channel_id, message_id) of the guild's dashboard, or None."""
        async with self.conn.execute(
            "SELECT dashboard_channel_id, dashboard_message_id FROM guild_settings "
            "WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None or row["dashboard_channel_id"] is None:
            return None
        return row["dashboard_channel_id"], row["dashboard_message_id"]

    async def set_dashboard(
        self, guild_id: int, channel_id: int | None, message_id: int | None
    ) -> None:
        """Remembers where the dashboard lives so it can be refreshed in place."""
        await self.conn.execute(
            """INSERT INTO guild_settings
                   (guild_id, dashboard_channel_id, dashboard_message_id)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET
                   dashboard_channel_id = excluded.dashboard_channel_id,
                   dashboard_message_id = excluded.dashboard_message_id""",
            (guild_id, channel_id, message_id),
        )
        await self.conn.commit()

    async def guilds_with_dashboard(self):
        """Guilds that have posted a dashboard (for the auto-refresh loop)."""
        async with self.conn.execute(
            "SELECT guild_id, dashboard_channel_id, dashboard_message_id "
            "FROM guild_settings WHERE dashboard_message_id IS NOT NULL"
        ) as cur:
            return await cur.fetchall()
