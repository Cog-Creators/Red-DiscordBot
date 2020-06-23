from __future__ import annotations

import copy
import typing

from .managed import managed_lavalink_connect_task_event
from ... import constants, config

if typing.TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["start_nodes"]


async def start_nodes(bot: Red, identifier: typing.Optional[str] = None) -> None:
    """Connect and initiate nodes."""
    await bot.wait_until_ready()
    if identifier:
        if bot.wavelink.nodes:
            previous = bot.wavelink.nodes.copy()
            if node := previous.get(identifier):
                await node.destroy()
        async with config._config.nodes.all() as node_data:
            if identifier in node_data:
                node_copy = copy.copy(node_data[identifier])
            elif identifier in constants.DEFAULT_COG_LAVALINK_SETTINGS:
                node_copy = copy.copy(constants.DEFAULT_COG_LAVALINK_SETTINGS[identifier])
            else:
                return
        node_copy["region"] = bot.wavelink.get_valid_region(node_copy["region"])
        await bot.wavelink.initiate_node(**node_copy)
    else:
        if bot.wavelink.nodes:
            previous = bot.wavelink.nodes.copy()
            for node in previous.values():
                await node.destroy()
        use_managed_lavalink = await config.config_cache.managed_lavalink_server.get_global()
        if use_managed_lavalink:
            await managed_lavalink_attempt_connect(timeout=120)
            await managed_lavalink_connect_task_event.wait()
        nodes = await config._config.nodes()
        for n in nodes.values():
            n["region"] = bot.wavelink.get_valid_region(n["region"])
            await bot.wavelink.initiate_node(**n)
