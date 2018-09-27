import warnings
from typing import Awaitable, TYPE_CHECKING, Dict

import discord

from .commands import (
    bot_has_permissions,
    has_permissions,
    is_owner,
    guildowner,
    guildowner_or_permissions,
    admin,
    admin_or_permissions,
    mod,
    mod_or_permissions,
    check as _check_decorator,
)
from .utils.mod import (
    is_mod_or_superior as _is_mod_or_superior,
    is_admin_or_superior as _is_admin_or_superior,
    check_permissions as _check_permissions,
)

if TYPE_CHECKING:
    from .bot import Red
    from .commands import Context

__all__ = [
    "bot_has_permissions",
    "has_permissions",
    "is_owner",
    "guildowner",
    "guildowner_or_permissions",
    "admin",
    "admin_or_permissions",
    "mod",
    "mod_or_permissions",
    "is_mod_or_superior",
    "is_admin_or_superior",
    "bot_in_a_guild",
    "check_permissions",
]


def bot_in_a_guild():
    """Deny the command if the bot is not in a guild."""

    async def predicate(ctx):
        return len(ctx.bot.guilds) > 0

    return _check_decorator(predicate)


def is_mod_or_superior(bot: "Red", member: discord.Member) -> Awaitable[bool]:
    warnings.warn(
        "`redbot.core.checks.is_mod_or_superior` is deprecated and will be removed in a future "
        "release, please use `redbot.core.utils.mod.is_mod_or_superior` instead.",
        category=DeprecationWarning,
    )
    return _is_mod_or_superior(bot, member)


def is_admin_or_superior(bot: "Red", member: discord.Member) -> Awaitable[bool]:
    warnings.warn(
        "`redbot.core.checks.is_admin_or_superior` is deprecated and will be removed in a future "
        "release, please use `redbot.core.utils.mod.is_admin_or_superior` instead.",
        category=DeprecationWarning,
    )
    return _is_admin_or_superior(bot, member)


def check_permissions(ctx: "Context", perms: Dict[str, bool]) -> Awaitable[bool]:
    warnings.warn(
        "`redbot.core.checks.check_permissions` is deprecated and will be removed in a future "
        "release, please use `redbot.core.utils.mod.check_permissions`."
    )
    return _check_permissions(ctx, perms)
