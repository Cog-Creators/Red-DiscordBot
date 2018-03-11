from collections import namedtuple
from enum import Enum
from typing import Callable, Union
import asyncio
import json

import websockets

from . import log


__all__ = ['loop', 'DiscordVoiceSocketResponses', 'LavalinkEvents',
           'LavalinkOutgoingOp', 'connect', 'join_voice']


loop = None  # type: asyncio.BaseEventLoop
_lavalink_ws = None  # type: websockets.WebSocketClientProtocol
_listener_task = None
_event_handler = lambda op, data, raw_data: None
# type: Callable[LavalinkEvents, Union[LavalinkEvents, PlayerState, Stats], dict]
_voice_ws_func = lambda guild_id: None

_queue = []

SHUTDOWN = asyncio.Event()


class DiscordVoiceSocketResponses(Enum):
    VOICE_STATE_UPDATE = 'VOICE_STATE_UPDATE'
    VOICE_SERVER_UPDATE = 'VOICE_SERVER_UPDATE'


class LavalinkIncomingOp(Enum):
    EVENT = 'event'
    PLAYER_UPDATE = 'playerUpdate'
    STATS = 'stats'


class LavalinkOutgoingOp(Enum):
    VOICE_UPDATE = 'voiceUpdate'
    PLAY = 'play'
    STOP = 'stop'
    PAUSE = 'pause'
    SEEK = 'seek'
    VOLUME = 'volume'


class LavalinkEvents(Enum):
    TRACK_END = 'TrackEndEvent'
    TRACK_EXCEPTION = 'TrackExceptionEvent'
    TRACK_STUCK = 'TrackStuckEvent'


PlayerState = namedtuple('PlayerState', 'position time')
MemoryInfo = namedtuple('MemoryInfo', 'reservable used free allocated')
CPUInfo = namedtuple('CPUInfo', 'cores systemLoad lavalinkLoad')



class Stats:
    def __init__(self, memory, players, active_players, cpu, uptime):
        self.memory = MemoryInfo(**memory)
        self.players = players
        self.active_players = active_players
        self.cpu_info = CPUInfo(**cpu)
        self.uptime = uptime


async def connect(_loop, event_handler, voice_ws_func,
                  host, password, port, user_id, num_shards):
    """
    Connects to the Lavalink player event websocket.

    Parameters
    ----------
    _loop : asyncio.BaseEventLoop
        The event loop of the bot.
    event_handler
        Function to dispatch events to.
    voice_ws_func
        Function that takes one argument, guild ID, and returns a websocket.
    host : str
        Lavalink player host.
    password : str
        Password for the Lavalink player.
    port : int
        Port of the Lavalink player event websocket.
    user_id : int
        User ID of the bot.
    num_shards : int
        Number of shards to which the bot is currently connected.

    Raises
    ------
    OSError
        If the websocket connection failed.
    """
    global loop
    global _lavalink_ws
    global _listener_task
    global _event_handler
    global _voice_ws_func

    SHUTDOWN.clear()

    uri = "ws://{}:{}".format(host, port)
    headers = _get_connect_headers(password, user_id, num_shards)

    log.debug('Lavalink WS connecting to {} with headers {}'.format(
        uri, headers
    ))
    _lavalink_ws = await websockets.connect(uri, extra_headers=headers)

    loop = _loop
    _event_handler = event_handler
    _voice_ws_func = voice_ws_func

    log.debug('Creating Lavalink WS listener.')
    _listener_task = loop.create_task(listener())

    for data in _queue:
        await send(data)


def _get_connect_headers(password, user_id, num_shards):
    return {
        'Authorization': password,
        'User-Id': user_id,
        'Num-Shards': num_shards
    }


async def listener():
    """
    Listener task for receiving ops from Lavalink.
    """
    while _lavalink_ws.open and not SHUTDOWN.is_set():
        try:
            data = json.loads(await _lavalink_ws.recv())
        except websockets.ConnectionClosed:
            break

        raw_op = data.get('op')
        try:
            op = LavalinkIncomingOp(raw_op)
        except ValueError:
            log.debug("Received unknown op: {}".format(data))
        else:
            log.debug("Received known op: {}".format(data))
            loop.create_task(_handle_op(op, data))

    log.debug('Listener exited.')
    loop.create_task(_reconnect())


async def _handle_op(op: LavalinkIncomingOp, data):
    if op == LavalinkIncomingOp.EVENT:
        try:
            event = LavalinkEvents(data.get('type'))
        except ValueError:
            log.debug("Unknown event type: {}".format(data))
        else:
            _event_handler(op, event, data)
    elif op == LavalinkIncomingOp.PLAYER_UPDATE:
        state = PlayerState(**data.get('state'))
        _event_handler(op, state, data)
    elif op == LavalinkIncomingOp.STATS:
        stats = Stats(
            memory=data.get('memory'),
            players=data.get('players'),
            active_players=data.get('playingPlayers'),
            cpu=data.get('cpu'),
            uptime=data.get('uptime')
        )
        _event_handler(op, stats, data)


async def _reconnect():
    if SHUTDOWN.is_set():
        log.debug('Shutting down Lavalink WS.')
        return

    log.debug("Attempting Lavalink WS reconnect.")


async def disconnect():
    """
    Shuts down and disconnects the websocket.
    """
    SHUTDOWN.set()
    await _lavalink_ws.close()
    log.debug("Shutdown Lavalink WS.")


async def join_voice(guild_id: int, channel_id: int):
    """
    Joins a voice channel by ID's.

    Parameters
    ----------
    guild_id : int
    channel_id : int
    """
    ws = _voice_ws_func(guild_id)
    await ws.voice_state(guild_id, channel_id)


async def send(data):
    if _lavalink_ws is None or not _lavalink_ws.open:
        _queue.append(data)
    else:
        log.debug("Sending data to Lavalink: {}".format(data))
        await _lavalink_ws.send(json.dumps(data))


async def send_lavalink_voice_update(guild_id, session_id, event):
    await send({
        'op': LavalinkOutgoingOp.VOICE_UPDATE.value,
        'guildId': str(guild_id),
        'sessionId': session_id,
        'event': event
    })

# Player commands
async def stop(guild_id: int):
    await send({
        'op': LavalinkOutgoingOp.STOP.value,
        'guildId': str(guild_id)
    })


async def play(guild_id: int, track_identifier: str):
    await send({
        'op': LavalinkOutgoingOp.PLAY.value,
        'guildId': str(guild_id),
        'track': track_identifier
    })


async def pause(guild_id, paused):
    await send({
        'op': LavalinkOutgoingOp.PAUSE.value,
        'guildId': str(guild_id),
        'pause': paused
    })


async def volume(guild_id: int, _volume: int):
    await send({
        'op': LavalinkOutgoingOp.VOLUME.value,
        'guildId': str(guild_id),
        'volume': _volume
    })


async def seek(guild_id: int, position: int):
    await send({
        'op': LavalinkOutgoingOp.SEEK.value,
        'guildId': str(guild_id),
        'position': position
    })
