import asyncio
import contextlib
import logging
import lavalink
import functools

from abc import ABC
from typing import Any

from redbot.core import commands
from redbot.core.utils import AsyncIter

log = logging.getLogger("red.core.audio_api.server_manager.callback")

class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass

def task_callback(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError, asyncio.InvalidStateError):
        if exc := task.exception():
            log.exception("%s raised an Exception", task.get_name(), exc_info=exc)

def has_internal_server():
    async def pred(ctx: commands.Context):
        external = await ctx.cog.config.use_external_lavalink()
        return not external

    return commands.check(pred)

async def get_queue_duration(player: lavalink.Player) -> int:
    dur = [
        i.length
        async for i in AsyncIter(player.queue, steps=50).filter(lambda x: not x.is_stream)
    ]
    queue_dur = sum(dur)
    if not player.queue:
        queue_dur = 0
    try:
        if not player.current.is_stream:
            remain = player.current.length - player.position
        else:
            remain = 0
    except AttributeError:
        remain = 0
    queue_total_duration = remain + queue_dur
    return queue_total_duration

def rgetattr(obj, attr, *args) -> Any:
    def _getattr(obj2, attr2):
        return getattr(obj2, attr2, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))

class classproperty:
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if doc is None and fget:
            doc = fget.__doc__
        self.__doc__ = doc

    def __get__(self, obj, objtype):
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget(objtype)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)

    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__doc__)