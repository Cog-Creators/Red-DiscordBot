import asyncio

from . import websocket
from . import player_manager
from . import rest_api

from ..utils import TYPE_CHECKING

if TYPE_CHECKING:
    from ..bot import Red

__all__ = ['initialize', 'close', 'register_event_listener', 'unregister_event_listener']


_event_listeners = []


async def initialize(bot: "Red", host, password, rest_port, ws_port):
    player_manager.user_id = bot.user.id
    player_manager.channel_finder_func = bot.get_channel
    register_event_listener(player_manager.handle_event)

    await websocket.connect(
        bot.loop, dispatch, bot._connection._get_websocket,
        host, password, port=ws_port,
        user_id=player_manager.user_id, num_shards=bot.shard_count
    )

    rest_api.initialize(host=host, port=rest_port, password=password)

    bot.add_listener(player_manager.on_socket_response)


def register_event_listener(coro):
    """
    Registers a coroutine to receive lavalink event information.

    Parameters
    ----------
    coro

    Raises
    ------
    TypeError
        If ``coro`` is not a coroutine.
    """
    if not asyncio.iscoroutinefunction(coro):
        raise TypeError("Function is not a coroutine.")

    if coro not in _event_listeners:
        _event_listeners.append(coro)


def unregister_event_listener(func):
    try:
        _event_listeners.remove(func)
    except ValueError:
        pass


def dispatch(op, data, raw_data):
    for coro in _event_listeners:
        websocket.loop.create_task(coro(op, data, raw_data))


async def close():
    unregister_event_listener(player_manager.handle_event)
    await player_manager.disconnect()
    await websocket.disconnect()
    await rest_api.close()
