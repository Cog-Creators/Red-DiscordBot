import warnings
from typing import TYPE_CHECKING, Awaitable, Dict

from .commands import (
    admin,
    admin_or_permissions,
    bot_has_permissions,
    bot_in_a_guild,
    guildowner,
    guildowner_or_permissions,
    has_permissions,
    is_owner,
    mod,
    mod_or_permissions,
)
from .utils.mod import (
    check_permissions as _check_permissions,
    is_admin_or_superior as _is_admin_or_superior,
    is_mod_or_superior as _is_mod_or_superior,
)

if TYPE_CHECKING:
    from .commands import Context

__all__ = [
    "bot_has_permissions",
    "bot_in_a_guild",
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
    "check_permissions",
]


def is_mod_or_superior(ctx: "Context") -> Awaitable[bool]:
    warnings.warn(
        "`redbot.core.checks.is_mod_or_superior` is deprecated and will be removed in a future "
        "release, please use `redbot.core.utils.mod.is_mod_or_superior` instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return _is_mod_or_superior(ctx.bot, ctx.author)


def is_admin_or_superior(ctx: "Context") -> Awaitable[bool]:
    warnings.warn(
        "`redbot.core.checks.is_admin_or_superior` is deprecated and will be removed in a future "
        "release, please use `redbot.core.utils.mod.is_admin_or_superior` instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return _is_admin_or_superior(ctx.bot, ctx.author)


def check_permissions(ctx: "Context", perms: Dict[str, bool]) -> Awaitable[bool]:
    warnings.warn(
        "`redbot.core.checks.check_permissions` is deprecated and will be removed in a future "
        "release, please use `redbot.core.utils.mod.check_permissions`.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _check_permissions(ctx, perms)
