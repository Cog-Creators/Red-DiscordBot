from collections import namedtuple
from enum import Enum
import asyncio
import json
from typing import Dict, List

import websockets
from discord.backoff import ExponentialBackoff

from . import log


__all__ = ['DiscordVoiceSocketResponses', 'LavalinkEvents',
           'LavalinkOutgoingOp', 'get_websocket', 'join_voice']

SHUTDOWN = asyncio.Event()
_websockets = {}  # type: Dict[WebSocket, List[int]]


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


class WebSocket:
    def __init__(self, _loop, event_handler, voice_ws_func,
                 host, password, port, user_id, num_shards):
        """

        Parameters
        ----------
        _loop : asyncio.BaseEventLoop
            The event loop of the bot.
        event_handler
            Function to dispatch events to.
        voice_ws_func : typing.Callable
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
        """
        self.loop = _loop
        self.event_handler = event_handler
        self.voice_ws_func = voice_ws_func
        self.host = host
        self.port = port
        self.headers = self._get_connect_headers(password, user_id, num_shards)

        self._ws = None
        self._listener_task = None

        self._queue = []

        _websockets[self] = []

    async def connect(self):
        """
        Connects to the Lavalink player event websocket.

        Parameters
        ----------

        Raises
        ------
        OSError
            If the websocket connection failed.
        """
        SHUTDOWN.clear()

        uri = "ws://{}:{}".format(self.host, self.port)

        log.debug('Lavalink WS connecting to {} with headers {}'.format(
            uri, self.headers
        ))
        self._ws = await websockets.connect(uri, extra_headers=self.headers)

        log.debug('Creating Lavalink WS listener.')
        self._listener_task = self.loop.create_task(self.listener())

        for data in self._queue:
            await self.send(data)

    @staticmethod
    def _get_connect_headers(password, user_id, num_shards):
        return {
            'Authorization': password,
            'User-Id': user_id,
            'Num-Shards': num_shards
        }

    async def listener(self):
        """
        Listener task for receiving ops from Lavalink.
        """
        while self._ws.open and not SHUTDOWN.is_set():
            try:
                data = json.loads(await self._ws.recv())
            except websockets.ConnectionClosed:
                break

            raw_op = data.get('op')
            try:
                op = LavalinkIncomingOp(raw_op)
            except ValueError:
                log.debug("Received unknown op: {}".format(data))
            else:
                log.debug("Received known op: {}".format(data))
                self.loop.create_task(self._handle_op(op, data))

        log.debug('Listener exited.')
        self.loop.create_task(self._reconnect())

    async def _handle_op(self, op: LavalinkIncomingOp, data):
        if op == LavalinkIncomingOp.EVENT:
            try:
                event = LavalinkEvents(data.get('type'))
            except ValueError:
                log.debug("Unknown event type: {}".format(data))
            else:
                self.event_handler(op, event, data)
        elif op == LavalinkIncomingOp.PLAYER_UPDATE:
            state = PlayerState(**data.get('state'))
            self.event_handler(op, state, data)
        elif op == LavalinkIncomingOp.STATS:
            stats = Stats(
                memory=data.get('memory'),
                players=data.get('players'),
                active_players=data.get('playingPlayers'),
                cpu=data.get('cpu'),
                uptime=data.get('uptime')
            )
            self.event_handler(op, stats, data)

    async def _reconnect(self):
        if SHUTDOWN.is_set():
            log.debug('Shutting down Lavalink WS.')
            return

        log.debug("Attempting Lavalink WS reconnect.")
        backoff = ExponentialBackoff()

        for x in range(5):
            delay = backoff.delay()
            log.debug("Reconnecting in {} seconds".format(delay))
            await asyncio.sleep(delay)

            try:
                await self.connect()
            except OSError:
                log.debug("Could not reconnect.")
            else:
                log.debug("Reconnect successful.")
                break
        else:
            log.debug("Failed to reconnect, please reinitialize lavalink when ready.")

    async def disconnect(self):
        """
        Shuts down and disconnects the websocket.
        """
        SHUTDOWN.set()
        await self._ws.close()
        del _websockets[self]
        log.debug("Shutdown Lavalink WS.")

    async def send(self, data):
        if self._ws is None or not self._ws.open:
            self._queue.append(data)
        else:
            log.debug("Sending data to Lavalink: {}".format(data))
            await self._ws.send(json.dumps(data))

    async def send_lavalink_voice_update(self, guild_id, session_id, event):
        await self.send({
            'op': LavalinkOutgoingOp.VOICE_UPDATE.value,
            'guildId': str(guild_id),
            'sessionId': session_id,
            'event': event
        })

    # Player commands
    async def stop(self, guild_id: int):
        await self.send({
            'op': LavalinkOutgoingOp.STOP.value,
            'guildId': str(guild_id)
        })

    async def play(self, guild_id: int, track_identifier: str):
        await self.send({
            'op': LavalinkOutgoingOp.PLAY.value,
            'guildId': str(guild_id),
            'track': track_identifier
        })

    async def pause(self, guild_id, paused):
        await self.send({
            'op': LavalinkOutgoingOp.PAUSE.value,
            'guildId': str(guild_id),
            'pause': paused
        })

    async def volume(self, guild_id: int, _volume: int):
        await self.send({
            'op': LavalinkOutgoingOp.VOLUME.value,
            'guildId': str(guild_id),
            'volume': _volume
        })

    async def seek(self, guild_id: int, position: int):
        await self.send({
            'op': LavalinkOutgoingOp.SEEK.value,
            'guildId': str(guild_id),
            'position': position
        })


def get_websocket(guild_id: int) -> WebSocket:
    """
    Gets a websocket based on a guild ID, useful for noding separation. If the
    guild ID does not already have a websocket association, the least used
    websocket is returned.

    Parameters
    ----------
    guild_id : int

    Returns
    -------
    WebSocket
    """
    guild_count = 1e10
    least_used = None
    for ws, guild_ids in _websockets.items():
        if len(guild_ids) < guild_count:
            guild_count = len(guild_ids)
            least_used = ws

        if guild_id in guild_ids:
            return ws

    _websockets[least_used].append(guild_id)
    return least_used


async def join_voice(guild_id: int, channel_id: int):
    """
    Joins a voice channel by ID's.

    Parameters
    ----------
    guild_id : int
    channel_id : int
    """
    ws = get_websocket(guild_id)
    voice_ws = ws.voice_ws_func(guild_id)
    await voice_ws.voice_state(guild_id, channel_id)


async def disconnect():
    ws_list = list(_websockets.keys())
    for ws in ws_list:
        await ws.disconnect()
