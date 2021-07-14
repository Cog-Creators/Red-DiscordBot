from abc import ABC
import asyncio
import contextlib
import logging
import lavalink

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
