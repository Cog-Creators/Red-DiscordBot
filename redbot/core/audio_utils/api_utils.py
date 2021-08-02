import asyncio
import contextlib
import logging
import lavalink
import functools

from abc import ABC
from typing import Any, AsyncContextManager, Awaitable, TypeVar, List

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

class _ValueCtxManager(Awaitable[TypeVar("_T")], AsyncContextManager[TypeVar("_T")]):  # pylint: disable=duplicate-bases
    """Context manager implementation for audio immutables

    totally not stolen from redbot.core.config"""
    def __init__(self, player: lavalink.Player, *, acquire_lock: bool = False):
        self.player = player
        self._queue = player.queue
        #self.__acquire_lock = acquire_lock
        #self.__lock = self.value_obj.get_lock()

    def __await__(self):
        return self.__aenter__().__await__()

    async def __aenter__(self):
        return self._queue

    async def __aexit__(self, exc_type, exc, tb):
        self.player.queue = self._queue