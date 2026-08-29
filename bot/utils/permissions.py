"""Kisk's permission model: a configurable admin role on top of Discord's
native Manage Server / Manage Messages.

Two tiers: a Kisk *admin* (the configured role, or Manage Server) and a Kisk
*moderator* (any Kisk admin, or Manage Messages) — admin implies moderator.

The predicates are pure so they can be unit-tested; the async wrappers adapt a
discord.Member and the guild's stored settings to them.
"""


def is_admin(admin_role_id, role_ids, *, manage_guild: bool) -> bool:
    """A Kisk admin: holds the configured admin role, or has Manage Server."""
    if manage_guild:
        return True
    return admin_role_id is not None and admin_role_id in role_ids


def is_moderator(
    admin_role_id, role_ids, *, manage_guild: bool, manage_messages: bool
) -> bool:
    """A Kisk moderator: any Kisk admin, or a member with Manage Messages."""
    return manage_messages or is_admin(
        admin_role_id, role_ids, manage_guild=manage_guild
    )


async def member_is_admin(db, member) -> bool:
    """Resolve is_admin() for a live member against the guild's stored role."""
    settings = await db.get_settings(member.guild.id)
    admin_role_id = settings["admin_role_id"] if settings else None
    return is_admin(
        admin_role_id,
        {role.id for role in member.roles},
        manage_guild=member.guild_permissions.manage_guild,
    )


async def member_is_moderator(db, member) -> bool:
    """Resolve is_moderator() for a live member against the stored role."""
    settings = await db.get_settings(member.guild.id)
    admin_role_id = settings["admin_role_id"] if settings else None
    perms = member.guild_permissions
    return is_moderator(
        admin_role_id,
        {role.id for role in member.roles},
        manage_guild=perms.manage_guild,
        manage_messages=perms.manage_messages,
    )
