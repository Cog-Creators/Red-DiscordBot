from __future__ import annotations
import inspect
import functools
from typing import (
    TypeVar,
    Callable,
    Awaitable,
    Coroutine,
    Union,
    Type,
    TYPE_CHECKING,
    List,
    Any,
    Generator,
    Protocol,
    overload,
)

import discord
from discord.ext import commands as dpy_commands

# So much of this can be stripped right back out with proper stubs.
if not TYPE_CHECKING:
    from discord.ext.commands import (
        check as check,
        guild_only as guild_only,
        dm_only as dm_only,
        is_nsfw as is_nsfw,
        has_role as has_role,
        has_any_role as has_any_role,
        bot_has_role as bot_has_role,
        bot_has_any_role as bot_has_any_role,
        cooldown as cooldown,
        before_invoke as before_invoke,
        after_invoke as after_invoke,
    )

from ..i18n import Translator
from .context import Context
from .commands import Command


_ = Translator("nah", __file__)


"""
Anything here is either a reimplementation or re-export
of a discord.py function or class with more lies for mypy
"""

__all__ = [
    "check",
    # "check_any",  # discord.py 1.3
    "guild_only",
    "dm_only",
    "is_nsfw",
    "has_role",
    "has_any_role",
    "bot_has_role",
    "bot_has_any_role",
    "when_mentioned_or",
    "cooldown",
    "when_mentioned",
    "before_invoke",
    "after_invoke",
]

_CT = TypeVar("_CT", bound=Context)
_T = TypeVar("_T")
_F = TypeVar("_F")
CheckType = Union[Callable[[_CT], bool], Callable[[_CT], Coroutine[Any, Any, bool]]]
CoroLike = Callable[..., Union[Awaitable[_T], Generator[Any, None, _T]]]
InvokeHook = Callable[[_CT], Coroutine[Any, Any, bool]]


class CheckDecorator(Protocol):
    predicate: Coroutine[Any, Any, bool]

    @overload
    def __call__(self, func: _CT) -> _CT:
        ...

    @overload
    def __call__(self, func: CoroLike) -> CoroLike:
        ...


if TYPE_CHECKING:

    def check(predicate: CheckType) -> CheckDecorator:
        ...

    def guild_only() -> CheckDecorator:
        ...

    def dm_only() -> CheckDecorator:
        ...

    def is_nsfw() -> CheckDecorator:
        ...

    def has_role() -> CheckDecorator:
        ...

    def has_any_role() -> CheckDecorator:
        ...

    def bot_has_role() -> CheckDecorator:
        ...

    def bot_has_any_role() -> CheckDecorator:
        ...

    def cooldown(rate: int, per: float, type: dpy_commands.BucketType = ...) -> Callable[[_F], _F]:
        ...

    def before_invoke(coro: InvokeHook) -> Callable[[_F], _F]:
        ...

    def after_invoke(coro: InvokeHook) -> Callable[[_F], _F]:
        ...


PrefixCallable = Callable[[dpy_commands.bot.BotBase, discord.Message], List[str]]


def when_mentioned(bot: dpy_commands.bot.BotBase, msg: discord.Message) -> List[str]:
    return [f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "]


def when_mentioned_or(*prefixes) -> PrefixCallable:
    def inner(bot: dpy_commands.bot.BotBase, msg: discord.Message) -> List[str]:
        r = list(prefixes)
        r = when_mentioned(bot, msg) + r
        return r

    return inner
