########## SENSITIVE SECTION WARNING ###########
################################################
# Any edits of any of the exported names       #
# may result in a breaking change.             #
# Ensure no names are removed without warning. #
################################################

### DEP-WARN: Check this *every* discord.py update
from discord.app_commands.checks import (
    bot_has_permissions,
    cooldown,
    dynamic_cooldown,
    has_any_role,
    has_role,
    has_permissions,
)

from typing import Dict, Optional

import discord

from . import BotMissingPermissions, check
from redbot.core.commands.requires import PrivilegeLevel, _validate_perms_dict

__all__ = (
    "bot_has_permissions",
    "cooldown",
    "dynamic_cooldown",
    "has_any_role",
    "has_role",
    "has_permissions",
    "is_owner",
    "guildowner",
    "admin",
    "mod",
    "guildowner_or_permissions",
    "admin_or_permissions",
    "mod_or_permissions",
    "can_manage_channel",
    "admin_or_can_manage_channel",
    "mod_or_can_manage_channel",
    "bot_can_manage_channel",
    "bot_can_react",
    "bot_in_a_guild",
)


def _permissions_deco(
    *,
    privilege_level: Optional[PrivilegeLevel] = None,
    user_perms: Optional[Dict[str, bool]] = None,
):
    if user_perms is not None:
        _validate_perms_dict(user_perms)

    async def predicate(interaction: discord.Interaction) -> bool:
        if privilege_level is not None:
            if await PrivilegeLevel.from_interaction(interaction) >= privilege_level:
                return True

        if user_perms is not None:
            permissions = interaction.permissions
            missing = [
                perm for perm, value in user_perms.items() if getattr(permissions, perm) != value
            ]

            if not missing:
                return True

        return False

    return check(predicate)


def is_owner():
    """
    Restrict the command to bot owners.

    You probably should not use this check, since slash commands are not designed to be owner only.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.BOT_OWNER)


def guildowner():
    """
    Restrict the command to the guild owner.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.GUILD_OWNER)


def admin():
    """
    Restrict the command to users with the admin role.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.ADMIN)


def mod():
    """
    Restrict the command to users with the mod role.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.MOD)


def guildowner_or_permissions(**perms: bool):
    """
    Restrict the command to the guild owner or users with these permissions.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.GUILD_OWNER, user_perms=perms)


def admin_or_permissions(**perms: bool):
    """
    Restrict the command to users with the admin role or these permissions.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.ADMIN, user_perms=perms)


def mod_or_permissions(**perms: bool):
    """
    Restrict the command to users with the mod role or these permissions.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.MOD, user_perms=perms)


def _can_manage_channel_deco(
    *, privilege_level: Optional[PrivilegeLevel] = None, allow_thread_owner: bool = False
):
    async def predicate(interaction: discord.Interaction) -> bool:
        perms = interaction.permissions
        if isinstance(interaction.channel, discord.Thread):
            if perms.manage_threads or (
                allow_thread_owner and interaction.channel.owner_id == interaction.user.id
            ):
                return True
        else:
            if perms.manage_channels:
                return True

        if privilege_level is not None:
            if await PrivilegeLevel.from_interaction(interaction) >= privilege_level:
                return True

        return False

    return check(predicate)


def can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Restrict the command to users with permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the author is a thread owner.
        This can, for example, be useful to check if the author can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """
    return _can_manage_channel_deco(allow_thread_owner=allow_thread_owner)


def admin_or_can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Restrict the command to users with the admin role or permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the author is a thread owner.
        This can, for example, be useful to check if the author can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """
    return _can_manage_channel_deco(
        privilege_level=PrivilegeLevel.ADMIN, allow_thread_owner=allow_thread_owner
    )


def mod_or_can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Restrict the command to users with the mod role or permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the author is a thread owner.
        This can, for example, be useful to check if the author can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """
    return _can_manage_channel_deco(
        privilege_level=PrivilegeLevel.MOD, allow_thread_owner=allow_thread_owner
    )


def bot_can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Complain if the bot is missing permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the bot is a thread owner.
        This can, for example, be useful to check if the bot can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """

    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False

        perms = interaction.app_permissions
        if isinstance(interaction.channel, discord.Thread):
            if not (
                perms.manage_threads
                or (
                    allow_thread_owner
                    and interaction.channel.owner_id == interaction.client.user.id
                )
            ):
                # This is a slight lie - thread owner *might* also be allowed
                # but we just say that bot is missing the Manage Threads permission.
                raise BotMissingPermissions(["manage_threads"])
        else:
            if not perms.manage_channels:
                raise BotMissingPermissions(["manage_channels"])

        return True

    return check(predicate)


def bot_can_react():
    """
    Complain if the bot is missing permissions to react.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        return not (
            isinstance(interaction.channel, discord.Thread) and interaction.channel.archived
        )

    def decorator(func):
        func = bot_has_permissions(read_message_history=True, add_reactions=True)(func)
        func = check(predicate)(func)
        return func

    return decorator


def bot_in_a_guild():
    """
    Deny the command if the bot is not in a guild.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        return len(interaction.client.guilds) > 0

    return check(predicate)
