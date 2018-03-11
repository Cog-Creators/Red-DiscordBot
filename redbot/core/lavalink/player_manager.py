from collections import namedtuple
from random import randrange
from typing import Union
from enum import Enum

import discord

from . import log
from . import websocket

__all__ = ['players', 'user_id', 'channel_finder_func', 'connect',
           'get_player', 'handle_event', 'TrackEndReason']

players = []
user_id = None
channel_finder_func = lambda channel_id: None

_voice_states = {}


TrackInfo = namedtuple(
    'TrackInfo', 'identifier isSeekable author length isStream position title uri'
)


class Track:
    def __init__(self, requester, data):
        self.requester = requester
        self.track_identifier = data.get('track')
        self.info = TrackInfo(**data.get('info'))


class TrackEndReason(Enum):
    FINISHED = 'FINISHED'
    LOAD_FAILED = 'LOAD_FAILED'
    STOPPED = 'STOPPED'
    REPLACED = 'REPLACED'
    CLEANUP = 'CLEANUP'


class Player:
    def __init__(self, websocket: websocket.WebSocket, channel: discord.VoiceChannel):
        self.channel = channel

        self.queue = []
        self.position = 0
        self.current = None  # type: Track
        self.paused = False
        self.repeat = False
        self.shuffle = False

        self.volume = 100

        self._metadata = {}
        self._ws = websocket

    async def connect(self):
        """
        Connects to the voice channel.
        """
        await websocket.join_voice(self.channel.guild.id, self.channel.id)

    async def move_to(self, channel: discord.VoiceChannel):
        """
        Moves this player to a voice channel.

        Parameters
        ----------
        channel : discord.VoiceChannel
        """
        if channel.guild != self.channel.guild:
            raise TypeError("Cannot move to a different guild.")

        self.channel = channel
        await self.connect()

    async def disconnect(self):
        """
        Disconnects this player from it's voice channel.
        """
        await websocket.join_voice(self.channel.guild.id, None)

    def store(self, key, value):
        self._metadata[key] = value

    def fetch(self, key, default=None):
        return self._metadata.get(key, default)

    async def handle_event(self, event: websocket.LavalinkEvents, extra):
        """
        Handles various Lavalink Events.

        If the event is TRACK END, extra will be TrackEndReason.

        If the event is TRACK EXCEPTION, extra will be the string reason.

        If the event is TRACK STUCK, extra will be the threshold ms.

        Parameters
        ----------
        event : websocket.LavalinkEvents
        extra
        """
        if event == websocket.LavalinkEvents.TRACK_END:
            if extra == TrackEndReason.FINISHED:
                await self.play()

    async def handle_player_update(self, state: websocket.PlayerState):
        """
        Handles player updates from lavalink.

        Parameters
        ----------
        state : websocket.PlayerState
        """
        self.position = state.position

    # Play commands
    def add(self, requester: discord.User, track_info: dict):
        """
        Adds a track to the queue.

        Parameters
        ----------
        requester : discord.User
            User who requested the track.
        track_info : dict
            Result from any of the lavalink track search methods.
        """
        self.queue.append(Track(requester, track_info))

    async def play(self):
        """
        Starts playback from lavalink.
        """
        if self.repeat and self.current is not None:
            self.queue.append(self.current)

        self.current = None
        self.position = 0
        self.paused = False

        if not self.queue:
            await self.stop()
        else:
            if self.shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(0)

            self.current = track
            await self._ws.play(self.channel.guild.id, track.track_identifier)

    async def stop(self):
        """
        Stops playback from lavalink.

        .. important::

            This method will clear the queue.
        """
        await self._ws.stop(self.channel.guild.id)
        self.queue = []
        self.current = None
        self.position = 0
        self.paused = False

    async def skip(self):
        """
        Skips to the next song.
        """
        await self.play()

    async def pause(self, pause: bool=True):
        """
        Pauses the current song.

        Parameters
        ----------
        pause : bool
            Set to ``False`` to resume.
        """
        await self._ws.pause(self.channel.guild.id, pause)
        self.paused = pause

    async def volume(self, volume: int):
        """
        Sets the volume of Lavalink.

        Parameters
        ----------
        volume : int
            Between 0 and 150
        """
        self.volume = max(min(volume, 150), 0)
        await self._ws.volume(self.channel.guild.id, self.volume)

    async def seek(self, position: int):
        """
        If the track allows it, seeks to a position.

        Parameters
        ----------
        position : int
            Between 0 and track length.
        """
        if self.current.info.isSeekable:
            position = max(min(position, self.current.info.length), 0)
            await self._ws.seek(self.channel.guild.id, position)


async def connect(channel: discord.VoiceChannel) -> Player:
    """
    Connects to a discord voice channel.

    Parameters
    ----------
    channel

    Returns
    -------
    Player
        The created Player object.
    """
    if _already_in_guild(channel):
        p = get_player(channel.guild.id)
        await p.move_to(channel)
    else:
        ws = websocket.get_websocket(channel.guild.id)
        p = Player(ws, channel)
        await p.connect()
        players.append(p)
    return p


def _already_in_guild(channel: discord.VoiceChannel) -> bool:
    for p in players:
        if p.channel.guild == channel.guild:
            return True
    return False


def get_player(guild_id: int) -> Player:
    """
    Gets a Player object from a guild ID.

    Parameters
    ----------
    guild_id : int
        Discord guild ID.

    Returns
    -------
    Player
    """
    for p in players:
        if p.channel.guild.id == guild_id:
            return p
    raise KeyError("No such player for that guild.")


async def handle_event(op: websocket.LavalinkIncomingOp,
                       data: Union[websocket.LavalinkEvents, websocket.PlayerState, websocket.Stats],
                       raw_data: dict):
    if op == websocket.LavalinkIncomingOp.STATS:
        return

    guild_id = int(raw_data.get('guildId'))

    try:
        player = get_player(guild_id)
    except KeyError:
        log.debug("Got an event for a guild that we have no player for.")
        return

    if op == websocket.LavalinkIncomingOp.EVENT:
        extra = None
        if data == websocket.LavalinkEvents.TRACK_END:
            extra = TrackEndReason(raw_data.get('reason'))
        elif data == websocket.LavalinkEvents.TRACK_EXCEPTION:
            extra = raw_data.get('error')
        elif data == websocket.LavalinkEvents.TRACK_STUCK:
            extra = raw_data.get('thresholdMs')
        await player.handle_event(data, extra)
    elif op == websocket.LavalinkIncomingOp.PLAYER_UPDATE:
        await player.handle_player_update(data)


def _ensure_player(channel_id: int):
    channel = channel_finder_func(channel_id)
    if channel is not None:
        try:
            get_player(channel.guild.id)
        except KeyError:
            log.debug("Received voice channel connection without a player.")
            ws = websocket.get_websocket(channel.guild.id)
            players.append(Player(ws, channel))


def _remove_player(guild_id: int):
    try:
        p = get_player(guild_id)
    except KeyError:
        pass
    else:
        players.remove(p)


async def on_socket_response(data):
    raw_event = data.get('t')
    try:
        event = websocket.DiscordVoiceSocketResponses(raw_event)
    except ValueError:
        return

    log.debug('Received Discord WS voice response: {}'.format(data))

    guild_id = data['d']['guild_id']
    if guild_id not in _voice_states:
        _voice_states[guild_id] = {}

    if event == websocket.DiscordVoiceSocketResponses.VOICE_SERVER_UPDATE:
        # Connected for the first time
        socket_event_data = data['d']

        _voice_states[guild_id].update({
            'guild_id': guild_id,
            'event': socket_event_data
        })
    elif event == websocket.DiscordVoiceSocketResponses.VOICE_STATE_UPDATE:
        channel_id = data['d']['channel_id']

        if channel_id is None:
            # We disconnected
            _voice_states[guild_id] = {}
            _remove_player(int(guild_id))
        else:
            # After initial connection, get session ID
            event_user_id = int(data['d'].get('user_id'))
            if event_user_id != user_id:
                return

            _ensure_player(int(channel_id))

            session_id = data['d']['session_id']
            _voice_states[guild_id]['session_id'] = session_id

    if len(_voice_states[guild_id]) == 3:
        ws = websocket.get_websocket(int(guild_id))
        await ws.send_lavalink_voice_update(**_voice_states[guild_id])


async def disconnect():
    """
    Disconnects all players.
    """
    for p in players:
        await p.disconnect()
    log.debug("Disconnected players.")
