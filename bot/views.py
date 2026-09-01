"""The buttons under an event message (Tank / Heal / DPS / Leave / Done / Cancel).

The view is "persistent": thanks to fixed custom_ids, the buttons keep
working even after a bot restart (it is re-registered at startup in main.py).
The custom_ids themselves are kept from earlier versions so already
published messages stay clickable.
"""

import asyncio
import io
import time
from collections import defaultdict

import discord

from . import config, i18n
from .embeds import ROLE_EMOJI, ROLE_LABEL, build_event_embed
from .errors import ViewErrorMixin
from .logic import (
    COMPO_STANDARD,
    MOVE_DOWN,
    MOVE_UP,
    assign,
    missing_slots,
    reorder_priorities,
    signup_priority,
)
from .utils.ics import build_calendar
from .utils.lfg import matching_pool
from .utils.mentions import join_mentions
from .utils.permissions import member_is_admin, member_is_moderator
from .views_common import character_option, refresh_event_message
from .views_edit import EventEditModal
from .views_rsvp import RSVPView as RSVPView


class CharacterSelect(discord.ui.Select):
    """Which character the member is bringing to this event."""

    def __init__(self, characters: list, current_id: int | None, lang: str = "en"):
        super().__init__(
            placeholder=i18n.t("signup.pick_placeholder", lang),
            options=[
                character_option(row, default=row["id"] == current_id)
                for row in characters
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.chosen(interaction, int(self.values[0]))


class CharacterPicker(ViewErrorMixin, discord.ui.View):
    """The ephemeral menu shown to members who registered several characters.

    Short-lived and private to one member, so it needs no persistence: the
    event it belongs to is captured on the instance.
    """

    def __init__(
        self,
        signups: "SignupView",
        event,
        role: str,
        characters: list,
        current_id: int | None,
        switching: bool,
        lang: str = "en",
    ):
        super().__init__(timeout=180)
        self.signups = signups
        self.event = event
        self.role = role
        # A member already in the party is only swapping characters; anyone
        # else is joining (or changing role), which re-queues them.
        self.switching = switching
        self.add_item(CharacterSelect(characters, current_id, lang))

    async def chosen(self, interaction: discord.Interaction, character_id: int):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        character = await db.get_character(
            self.event["guild_id"], interaction.user.id, character_id
        )
        if character is None:  # deleted between opening the menu and picking
            await interaction.response.edit_message(
                content=i18n.t("signup.char_gone", lang), view=None
            )
            return

        async with self.signups._locks[self.event["message_id"]]:
            if self.switching:
                await db.set_signup_character(
                    self.event["message_id"], interaction.user.id, character_id
                )
                await interaction.response.edit_message(
                    content=i18n.t(
                        "signup.bringing",
                        lang,
                        name=character["char_name"],
                        title=self.event["title"],
                    ),
                    view=None,
                )
                await refresh_event_message(interaction.client, self.event)
                return

            message, party_before = await self.signups.perform_join(
                interaction, self.event, self.role, character, lang
            )
            await interaction.response.edit_message(content=message, view=None)
            await refresh_event_message(interaction.client, self.event)
            await self.signups.announce_promoted(interaction, self.event, party_before)


class SignupView(ViewErrorMixin, discord.ui.View):
    # One lock per event message, shared across every SignupView instance (a
    # message may be created by one instance and, after a restart, served by
    # the one re-registered in main.py). Joining, leaving and switching roles
    # each read the party, mutate the DB and diff the result across several
    # awaits; serialising per message keeps that read-modify-diff atomic so
    # concurrent clicks can't double-promote or emit phantom promotions.
    _locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    # Which buttons carry a translatable label; role buttons (tank/heal/dps)
    # keep their emoji-driven tokens untouched.
    _LABELS = {
        "aion2:leave": "signup.btn_leave",
        "aion2:done": "signup.btn_done",
        "aion2:cancel": "signup.btn_cancel",
        "aion2:edit": "signup.btn_edit",
        "aion2:queue": "signup.btn_manage",
        "aion2:ics": "signup.btn_calendar",
        "aion2:lfg": "signup.btn_invite_lfg",
    }

    def __init__(self, lang: str = "en"):
        super().__init__(timeout=None)
        for child in self.children:
            key = self._LABELS.get(getattr(child, "custom_id", None))
            if key is not None:
                child.label = i18n.t(key, lang)

    # ----- Sign-up buttons -----

    @discord.ui.button(
        label="Tank",
        emoji=config.EMOJI_TANK,
        style=discord.ButtonStyle.primary,
        custom_id="aion2:tank",
    )
    async def tank_button(self, interaction: discord.Interaction, _):
        await self._join(interaction, "tank")

    @discord.ui.button(
        label="Heal",
        emoji=config.EMOJI_HEAL,
        style=discord.ButtonStyle.success,
        custom_id="aion2:heal",
    )
    async def heal_button(self, interaction: discord.Interaction, _):
        await self._join(interaction, "heal")

    @discord.ui.button(
        label="DPS",
        emoji=config.EMOJI_DPS,
        style=discord.ButtonStyle.danger,
        custom_id="aion2:dps",
    )
    async def dps_button(self, interaction: discord.Interaction, _):
        await self._join(interaction, "dps")

    @discord.ui.button(
        label="Leave",
        emoji="🚪",
        style=discord.ButtonStyle.secondary,
        custom_id="aion2:leave",
        row=1,
    )
    async def leave_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        async with self._locks[event["message_id"]]:
            party_before, _ = assign(
                event["compo"],
                event["size"],
                await db.get_signups(event["message_id"]),
            )
            removed = await db.remove_signup(event["message_id"], interaction.user.id)
            if not removed:
                await interaction.response.send_message(
                    i18n.t("signup.not_signed_up", lang), ephemeral=True
                )
                return

            await self._update_message(interaction, event)
            await interaction.followup.send(i18n.t("signup.left", lang), ephemeral=True)
            await self.announce_promoted(interaction, event, party_before)

    @discord.ui.button(
        label="Done",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="aion2:done",
        row=1,
    )
    async def done_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        is_creator = interaction.user.id == event["creator_id"]
        is_mod = await member_is_moderator(db, interaction.user)
        if not (is_creator or is_mod):
            await interaction.response.send_message(
                i18n.t("signup.only_creator_close", lang),
                ephemeral=True,
            )
            return

        await db.set_status(event["message_id"], "done")
        event = await db.get_event(event["message_id"])
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes, lang)
        await interaction.response.edit_message(embed=embed, view=None)
        # Closing removes the buttons, so no interaction reaches this event's
        # lock again: drop it rather than leak one lock per event forever.
        self._locks.pop(event["message_id"], None)

        party, _ = assign(event["compo"], event["size"], signups)
        mentions = join_mentions(s["user_id"] for s in party)
        await interaction.followup.send(
            i18n.t("signup.completed", lang, title=event["title"])
            + (f" GG {mentions}" if mentions else ""),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        await self._delete_event_voice(interaction, event)

    @discord.ui.button(
        label="Cancel event",
        emoji="🗑️",
        style=discord.ButtonStyle.secondary,
        custom_id="aion2:cancel",
        row=1,
    )
    async def cancel_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        is_creator = interaction.user.id == event["creator_id"]
        is_mod = await member_is_moderator(db, interaction.user)
        if not (is_creator or is_mod):
            await interaction.response.send_message(
                i18n.t("signup.only_creator_cancel", lang),
                ephemeral=True,
            )
            return

        await db.set_status(event["message_id"], "cancelled")
        event = await db.get_event(event["message_id"])
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes, lang)
        await interaction.response.edit_message(embed=embed, view=None)
        self._locks.pop(event["message_id"], None)  # see done_button

        party, waitlist = assign(event["compo"], event["size"], signups)
        mentions = join_mentions(s["user_id"] for s in party + waitlist)
        await interaction.followup.send(
            i18n.t(
                "signup.cancelled",
                lang,
                title=event["title"],
                who=interaction.user.mention,
            )
            + (f"\n{mentions}" if mentions else ""),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        await self._delete_event_voice(interaction, event)

    async def _delete_event_voice(self, interaction, event):
        """Removes the event's temporary voice channel, if it has one."""
        channel_id = event["voice_channel_id"]
        if not channel_id:
            return
        channel = interaction.client.get_channel(channel_id)
        if channel is not None:
            try:
                await channel.delete()
            except discord.HTTPException:
                pass  # already gone or no permission
        await interaction.client.db.clear_voice_channel(event["message_id"])

    @discord.ui.button(
        label="Edit",
        emoji="✏️",
        style=discord.ButtonStyle.secondary,
        custom_id="aion2:edit",
        row=2,
    )
    async def edit_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        is_creator = interaction.user.id == event["creator_id"]
        is_mod = await member_is_moderator(db, interaction.user)
        if not (is_creator or is_mod):
            await interaction.response.send_message(
                i18n.t("signup.only_creator_edit", lang), ephemeral=True
            )
            return

        await interaction.response.send_modal(EventEditModal(event, lang))

    @discord.ui.button(
        label="Manage queue",
        emoji="🧮",
        style=discord.ButtonStyle.secondary,
        custom_id="aion2:queue",
        row=2,
    )
    async def queue_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        # Reordering the queue is a Kisk-admin action.
        if not await member_is_admin(db, interaction.user):
            await interaction.response.send_message(
                i18n.t("signup.only_admin_manage", lang), ephemeral=True
            )
            return

        signups = await db.get_signups(event["message_id"])
        if len(signups) < 2:
            await interaction.response.send_message(
                i18n.t("signup.manage_empty", lang), ephemeral=True
            )
            return

        await interaction.response.send_message(
            i18n.t("signup.manage_intro", lang),
            view=QueueManageView(event, signups, lang),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Calendar",
        emoji="📅",
        style=discord.ButtonStyle.secondary,
        custom_id="aion2:ics",
        row=2,
    )
    async def ics_button(self, interaction: discord.Interaction, _):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        events = await db.upcoming_events(interaction.guild_id, int(time.time()))
        if not any(e["starts_at"] is not None for e in events):
            await interaction.response.send_message(
                i18n.t("ics.none", lang), ephemeral=True
            )
            return
        data = build_calendar(events).encode("utf-8")
        file = discord.File(io.BytesIO(data), filename="kisk-events.ics")
        await interaction.response.send_message(
            i18n.t("ics.here", lang), file=file, ephemeral=True
        )

    @discord.ui.button(
        label="Invite LFG",
        emoji="🔎",
        style=discord.ButtonStyle.secondary,
        custom_id="aion2:lfg",
        row=2,
    )
    async def invite_lfg_button(self, interaction: discord.Interaction, _):
        """Pings the LFG pool members who fit an open seat on this event."""
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        is_creator = interaction.user.id == event["creator_id"]
        if not (is_creator or await member_is_moderator(db, interaction.user)):
            await interaction.response.send_message(
                i18n.t("lfg.invite_forbidden", lang), ephemeral=True
            )
            return

        signups = await db.get_signups(event["message_id"])
        party, _waitlist = assign(event["compo"], event["size"], signups)
        if len(party) >= event["size"]:
            await interaction.response.send_message(
                i18n.t("lfg.invite_full", lang), ephemeral=True
            )
            return

        # Standard events only want the roles still short; open events take any.
        if event["compo"] == COMPO_STANDARD:
            needed = set(missing_slots(event["compo"], event["size"], signups))
        else:
            needed = None
        signed_ids = {s["user_id"] for s in signups}
        matches = [
            entry
            for entry in matching_pool(
                await db.get_lfg_pool(event["guild_id"], int(time.time())),
                event["activity"],
                needed,
                int(time.time()),
            )
            if entry["user_id"] not in signed_ids
        ]
        if not matches:
            await interaction.response.send_message(
                i18n.t("lfg.invite_none", lang), ephemeral=True
            )
            return

        emoji = config.EMOJI_ACTIVITY.get(
            event["activity"], config.EMOJI_ACTIVITY["Other"]
        )
        mentions = join_mentions(entry["user_id"] for entry in matches)
        await interaction.response.send_message(
            i18n.t(
                "lfg.invite_ping",
                lang,
                mentions=mentions,
                emoji=emoji,
                activity=event["activity"],
                link=interaction.message.jump_url,
            ),
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    # ----- Shared machinery -----

    async def _join(self, interaction: discord.Interaction, role: str):
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        event = await self._open_event(interaction)
        if event is None:
            return

        characters = await db.get_profiles(event["guild_id"], interaction.user.id)
        existing = await db.get_signup(event["message_id"], interaction.user.id)
        already_in_this_role = existing is not None and existing["role"] == role

        if already_in_this_role and len(characters) < 2:
            await interaction.response.send_message(
                i18n.t(
                    "signup.already_role",
                    lang,
                    emoji=ROLE_EMOJI[role],
                    label=ROLE_LABEL[role],
                ),
                ephemeral=True,
            )
            return

        # Members with several characters say which one they're bringing;
        # everyone else is signed up straight away, as before.
        if len(characters) > 1:
            picker = CharacterPicker(
                self,
                event,
                role,
                characters,
                current_id=existing["character_id"] if existing else None,
                switching=already_in_this_role,
                lang=lang,
            )
            intro = (
                i18n.t(
                    "signup.pick_switch",
                    lang,
                    emoji=ROLE_EMOJI[role],
                    label=ROLE_LABEL[role],
                )
                if already_in_this_role
                else i18n.t(
                    "signup.pick_join",
                    lang,
                    emoji=ROLE_EMOJI[role],
                    label=ROLE_LABEL[role],
                )
            )
            await interaction.response.send_message(intro, view=picker, ephemeral=True)
            return

        async with self._locks[event["message_id"]]:
            message, party_before = await self.perform_join(
                interaction, event, role, characters[0] if characters else None, lang
            )
            await interaction.response.send_message(message, ephemeral=True)
            await refresh_event_message(interaction.client, event)
            await self.announce_promoted(interaction, event, party_before)

    async def perform_join(
        self,
        interaction: discord.Interaction,
        event,
        role: str,
        character,
        lang: str = "en",
    ) -> tuple[str, list]:
        """Signs the member up and redraws the event.

        Returns the reply to show them and the party as it stood beforehand,
        which the caller passes to announce_promoted. Callers hold the event's
        lock around this, answer the interaction with the returned message and
        only then redraw the event: an interaction left unanswered for three
        seconds is dropped by Discord, so the HTTP edit must come after.
        """
        db = interaction.client.db
        party_before, _ = assign(
            event["compo"],
            event["size"],
            await db.get_signups(event["message_id"]),
        )
        await db.upsert_signup(
            event["message_id"],
            interaction.user.id,
            interaction.user.display_name,
            role,
            time.time(),
            character["id"] if character else None,
        )

        signups = await db.get_signups(event["message_id"])
        party, waitlist = assign(event["compo"], event["size"], signups)
        who = (
            i18n.t("signup.with_character", lang, name=character["char_name"])
            if character
            else ""
        )
        if any(s["user_id"] == interaction.user.id for s in party):
            message = i18n.t(
                "signup.joined",
                lang,
                emoji=ROLE_EMOJI[role],
                label=ROLE_LABEL[role],
                who=who,
            )
        else:
            position = next(
                i
                for i, s in enumerate(waitlist, start=1)
                if s["user_id"] == interaction.user.id
            )
            message = i18n.t(
                "signup.waitlisted",
                lang,
                position=position,
                emoji=ROLE_EMOJI[role],
                label=ROLE_LABEL[role],
                who=who,
            )
        return message, party_before

    async def _open_event(self, interaction: discord.Interaction):
        """Finds the event tied to the clicked message, if it's still open."""
        lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
        event = await interaction.client.db.get_event(interaction.message.id)
        if event is None:
            await interaction.response.send_message(
                i18n.t("signup.event_gone", lang),
                ephemeral=True,
            )
            return None
        if event["status"] != "open":
            message = (
                i18n.t("signup.event_done", lang)
                if event["status"] == "done"
                else i18n.t("signup.event_cancelled", lang)
            )
            await interaction.response.send_message(message, ephemeral=True)
            return None
        return event

    async def _update_message(self, interaction: discord.Interaction, event) -> list:
        """Updates the message's embed and returns the fresh sign-ups.

        Named `_update_message` on purpose: `_refresh` is an internal discord.py
        View method (`View._refresh(components)`), and shadowing it crashes the
        gateway when Discord refreshes the view on a message update.
        """
        db = interaction.client.db
        lang = await i18n.resolve_lang(db, interaction.guild)
        signups = await db.get_signups(event["message_id"])
        classes = await db.get_main_classes(
            event["guild_id"], [s["user_id"] for s in signups]
        )
        embed = build_event_embed(event, signups, classes, lang)
        await interaction.response.edit_message(embed=embed, view=self)
        return signups

    async def announce_promoted(self, interaction, event, party_before: list):
        """Publicly notifies players promoted from the waitlist to the party."""
        signups = await interaction.client.db.get_signups(event["message_id"])
        party, _ = assign(event["compo"], event["size"], signups)
        ids_before = {s["user_id"] for s in party_before}
        promoted = [
            s
            for s in party
            if s["user_id"] not in ids_before and s["user_id"] != interaction.user.id
        ]
        if promoted:
            lang = await i18n.resolve_lang(interaction.client.db, interaction.guild)
            mentions = join_mentions(s["user_id"] for s in promoted)
            await interaction.followup.send(
                i18n.t(
                    "signup.promoted", lang, mentions=mentions, title=event["title"]
                ),
                allowed_mentions=discord.AllowedMentions(users=True),
            )


def _ranked_signups(signups: list) -> list:
    """Sign-ups in queue order: highest admin priority first, then join order."""
    return sorted(signups, key=signup_priority, reverse=True)


class QueueSelect(discord.ui.Select):
    """Picks which sign-up the admin is about to move up or down."""

    def __init__(
        self, ranked: list, party_ids: set, selected: int | None, lang: str = "en"
    ):
        options = []
        for position, s in enumerate(ranked[:25], start=1):
            in_party = s["user_id"] in party_ids
            tag = i18n.t(
                "signup.in_party" if in_party else "signup.waitlisted_tag", lang
            )
            description = f"{tag} · {ROLE_LABEL[s['role']]}"
            if s["char_name"]:
                description += f" · {s['char_name']}"
            options.append(
                discord.SelectOption(
                    label=f"{position}. {s['display_name']}"[:100],
                    value=str(s["user_id"]),
                    description=description[:100],
                    default=s["user_id"] == selected,
                )
            )
        super().__init__(
            placeholder=i18n.t("signup.queue_placeholder", lang), options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected = int(self.values[0])
        signups = await interaction.client.db.get_signups(self.view.event["message_id"])
        await interaction.response.edit_message(
            view=QueueManageView(
                self.view.event, signups, self.view.lang, selected=self.view.selected
            )
        )


class QueueManageView(ViewErrorMixin, discord.ui.View):
    """Admin-only ephemeral controls to reorder an event's sign-up queue.

    Short-lived and private to one admin, so no persistence is needed. Moving a
    sign-up up or down rewrites the stored priorities (see logic.reorder_priorities)
    and redraws the public event message; anyone this pushes into the party is
    pinged, exactly like an automatic promotion.
    """

    _BUTTONS = {"queue:up": "signup.btn_up", "queue:down": "signup.btn_down"}

    def __init__(
        self, event, signups: list, lang: str = "en", selected: int | None = None
    ):
        super().__init__(timeout=180)
        self.event = event
        self.lang = lang
        ranked = _ranked_signups(signups)
        party, _waitlist = assign(event["compo"], event["size"], signups)
        party_ids = {s["user_id"] for s in party}
        if selected is None or all(s["user_id"] != selected for s in ranked):
            selected = ranked[0]["user_id"] if ranked else None
        self.selected = selected
        for child in self.children:
            key = self._BUTTONS.get(getattr(child, "custom_id", None))
            if key is not None:
                child.label = i18n.t(key, lang)
        self.add_item(QueueSelect(ranked, party_ids, selected, lang))

    @discord.ui.button(
        emoji="⬆️", style=discord.ButtonStyle.primary, custom_id="queue:up", row=1
    )
    async def up_button(self, interaction: discord.Interaction, _):
        await self._move(interaction, MOVE_UP)

    @discord.ui.button(
        emoji="⬇️", style=discord.ButtonStyle.primary, custom_id="queue:down", row=1
    )
    async def down_button(self, interaction: discord.Interaction, _):
        await self._move(interaction, MOVE_DOWN)

    async def _move(self, interaction: discord.Interaction, direction: str):
        db = interaction.client.db
        async with SignupView._locks[self.event["message_id"]]:
            signups = await db.get_signups(self.event["message_id"])
            ordered_ids = [s["user_id"] for s in _ranked_signups(signups)]
            if self.selected not in ordered_ids:
                # The picked member left the event meanwhile: just redraw.
                await interaction.response.edit_message(
                    view=QueueManageView(self.event, signups, self.lang)
                )
                return

            party_before, _ = assign(self.event["compo"], self.event["size"], signups)
            priorities = reorder_priorities(ordered_ids, self.selected, direction)
            await db.set_signup_priorities(self.event["message_id"], priorities)
            signups = await db.get_signups(self.event["message_id"])

            # Answer the interaction (redraw the ephemeral panel) before the
            # slower HTTP edit of the public event message.
            await interaction.response.edit_message(
                view=QueueManageView(
                    self.event, signups, self.lang, selected=self.selected
                )
            )
            await refresh_event_message(interaction.client, self.event)
            await self._announce_promoted(interaction, party_before, signups)

    async def _announce_promoted(self, interaction, party_before: list, signups: list):
        party, _ = assign(self.event["compo"], self.event["size"], signups)
        ids_before = {s["user_id"] for s in party_before}
        promoted = [s for s in party if s["user_id"] not in ids_before]
        if not promoted:
            return
        channel = interaction.client.get_channel(self.event["channel_id"])
        if channel is None:
            channel = await interaction.client.fetch_channel(self.event["channel_id"])
        mentions = join_mentions(s["user_id"] for s in promoted)
        await channel.send(
            i18n.t(
                "signup.promoted",
                self.lang,
                mentions=mentions,
                title=self.event["title"],
            ),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
