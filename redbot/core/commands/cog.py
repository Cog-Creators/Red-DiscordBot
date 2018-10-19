import inspect
from typing import Callable, TYPE_CHECKING, Dict, List, Union, Awaitable

import discord
import discord.ext.commands

from .commands import (
    CogCommandMixin,
    CogGroupMixin,
    Command,
    ScheduledMethod,
    LoopedMethod,
    ShutdownMethod,
)
from .errors import OverrideNotAllowed
from ..i18n import Translator

if TYPE_CHECKING:
    from ..bot import Red
    from .context import Context


__all__ = ["CogMeta", "Cog"]

_ = Translator("commands.cog", __file__)


class CogMeta(CogCommandMixin, CogGroupMixin, type):
    """Metaclass for cog base class."""

    __checks: List[Callable[["Context"], Union[bool, Awaitable[bool]]]]

    def __init__(cls, *args, **kwargs) -> None:
        try:
            cls.__checks = getattr(cls, "__commands_checks__")
        except AttributeError:
            cls.__checks = []
        else:
            delattr(cls, "__commands_checks__")
        super().__init__(*args, **kwargs)

    @property
    def all_commands(cls) -> Dict[str, Command]:
        return {cmd.name: cmd for _, cmd in inspect.getmembers(cls) if isinstance(cmd, Command)}

    @property
    def qualified_name(cls) -> str:
        return cls.__name__

    @property
    def checks(cls) -> List[Callable[["Context"], Union[bool, Awaitable[bool]]]]:
        return cls.__checks

    async def can_run(cls, ctx: "Context") -> bool:
        """Check if the given context passes this cog class's requirements.

        Raises
        ------
        CommandError
            Any exception which are raised from underlying checks.

        """
        ret = await discord.utils.async_all((pred(ctx) for pred in cls.checks))
        if ret is False:
            return ret
        return await cls.requires.verify(ctx)

    @classmethod
    async def convert(mcs, ctx: "Context", argument: str) -> "Cog":
        cog_instance = ctx.bot.get_cog(argument)
        if cog_instance is None:
            raise discord.ext.commands.BadArgument(_('Cog "argument" not found.'))
        return type(cog_instance)


class Cog(metaclass=CogMeta):
    """Base class for a cog."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__scheduled_methods = []
        self.__scheduled_shutdown_methods = []

    def _add_scheduled_methods(self, bot: "Red"):
        members = inspect.getmembers(self)

        for name, member in members:
            scheduled_name = None
            full_name = None
            if isinstance(member, ShutdownMethod):
                full_name = f"{self.__class__.__name__}.{name}"
                args = [self] + member.args
                scheduled_name = bot.scheduler.call_at_shutdown(
                    member.callback, name=full_name, args=args, kwargs=member.kwargs
                )
            elif isinstance(member, LoopedMethod):
                full_name = f"{self.__class__.__name__}.{name}"
                args = [self] + member.args
                scheduled_name = bot.scheduler.loop(
                    member.callback,
                    period=member.period,
                    name=full_name,
                    args=args,
                    kwargs=member.kwargs,
                    now=member.call_now,
                    call_at_shutdown=member.call_at_shutdown,
                )
            elif isinstance(member, ScheduledMethod):
                full_name = f"{self.__class__.__name__}.{name}"
                args = [self] + member.args
                scheduled_name = bot.scheduler.call_once(
                    member.callback,
                    delay=member.delay,
                    name=full_name,
                    args=args,
                    kwargs=member.kwargs,
                    call_at_shutdown=member.call_at_shutdown,
                )

            if scheduled_name is not None:
                assert full_name == scheduled_name, "This shouldn't happen...report it now."
                self.__scheduled_methods.append(scheduled_name)
                if member.call_at_shutdown:
                    self.__scheduled_shutdown_methods.append(scheduled_name)

    def _remove_scheduled_methods(self, bot):
        for name in self.__scheduled_methods:
            bot.scheduler.remove(name)

        for name in self.__scheduled_shutdown_methods:
            bot.scheduler.remove(name)

    @classmethod
    async def convert(cls, ctx: "Context", argument: str) -> "Cog":
        cog_instance = ctx.bot.get_cog(argument)
        if cog_instance is None:
            raise discord.ext.commands.BadArgument(_('Cog "argument" not found.'))
        return cog_instance
