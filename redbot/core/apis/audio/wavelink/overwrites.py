from __future__ import annotations

import asyncio
import collections
import contextlib
import enum
import inspect
import itertools
import logging
import random
import re
import time
import typing
from operator import attrgetter
from urllib.parse import quote, urlparse

import aiohttp
import async_timeout
import discord
import wavelink
from discord.http import Route

from redbot.core import commands

from .. import regex
from . import constants
from .events import QueueEnd

__all__ = [
    "ExceptionSeverity",
    "LoadType",
    "PlayerStatus",
    "RedClient",
    "RedEqualizer",
    "RedNode",
    "RedPlayer",
    "RedTrack",
    "RedTrackPlaylist",
    "Votes",
    "get_tracks",
    "parse_timestamps",
]

log = logging.getLogger("red.core.apis.audio.wavelink")

_PlaylistInfo = collections.namedtuple("PlaylistInfo", "name selectedTrack")


class ExceptionSeverity(enum.Enum):
    COMMON = "COMMON"
    SUSPICIOUS = "SUSPICIOUS"
    FATAL = "FATAL"


class LoadType(enum.Enum):
    """
    The result type of a loadtracks request
    Attributes
    ----------
    TRACK_LOADED
    TRACK_LOADED
    PLAYLIST_LOADED
    SEARCH_RESULT
    NO_MATCHES
    LOAD_FAILED
    """

    TRACK_LOADED = "TRACK_LOADED"
    PLAYLIST_LOADED = "PLAYLIST_LOADED"
    SEARCH_RESULT = "SEARCH_RESULT"
    NO_MATCHES = "NO_MATCHES"
    LOAD_FAILED = "LOAD_FAILED"
    V2_COMPAT = "V2_COMPAT"
    V2_COMPACT = "V2_COMPACT"


class PlayerStatus(enum.Enum):
    READY = "Ready"
    DISCONNECTED = "Disconnected"
    PLAYING = "Playing"
    CONNECTED = "Connected"
    PAUSED = "Paused"


class RedClient(wavelink.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.valid_regions: typing.Set[str] = set()

    async def set_valid_regions(self) -> None:
        data = await self.bot.http.request(Route("GET", "/voice/regions"))
        self.valid_regions = {i["id"] for i in data if not i.get("deprecated")}
        if self.valid_regions and "south-korea" not in self.valid_regions:
            self.valid_regions.add("south-korea")

    def get_valid_region(self, region: str) -> typing.Optional[str]:
        if region in self.valid_regions:
            return region
        if region in constants.REGION_AGGREGATION:
            return constants.REGION_AGGREGATION.get(region)
        return None

    async def initiate_node(
        self,
        host: str,
        port: int,
        *,
        rest_uri: str,
        password: str,
        region: str,
        identifier: str,
        shard_id: int = None,
        secure: bool = False,
        search_only: bool = False,
    ) -> RedNode:
        """|coro|

        Initiate a Node and connect to the provided server.

        Parameters
        ------------
        host: str
            The host address to connect to.
        port: int
            The port to connect to.
        rest_uri: str
            The URI to use to connect to the REST server.
        password: str
            The password to authenticate on the server.
        region: str
            The region as a valid discord.py guild.region to associate the :class:`RedNode` with.
        identifier: str
            A unique identifier for the :class:`RedNode`
        shard_id: Optional[int]
            An optional Shard ID to associate with the :class:`RedNode`. Could be None.
        secure: bool
            Whether the websocket should be started with the secure wss protocol.
        search_only: bool
            Whether the node should only be used for searches.

        Returns
        ---------
        :class:`RedNode`
            Returns the initiated Node in a connected state.

        Raises
        --------
        NodeOccupied
            A node with provided identifier already exists.
        """
        await self.bot.wait_until_ready()

        if identifier in self.nodes:
            node = self.nodes[identifier]
            raise wavelink.NodeOccupied(
                f"Node with identifier ({identifier}) already exists >> {node.__repr__()}"
            )

        node = RedNode(
            host,
            port,
            self.shard_count,
            self.user_id,
            rest_uri=rest_uri,
            password=password,
            region=region,
            identifier=identifier,
            shard_id=shard_id,
            session=self.session,
            client=self,
            secure=secure,
            search_only=search_only,
        )

        await node.connect(bot=self.bot)

        node.available = True
        self.nodes[identifier] = node

        log.debug(f"CLIENT | New node initiated:: {node.__repr__()} ")
        await self.set_valid_regions()
        return node

    def get_player(
        self,
        guild_id: int,
        *,
        cls: typing.Optional[RedPlayer] = None,
        node_id: typing.Optional[str] = None,
        **kwargs: typing.Any,
    ) -> RedPlayer:
        """Retrieve a player for the given guild ID. If None, a player will be created and
        returned.

        .. versionchanged:: 0.3.0
            cls is now a keyword only argument.

        .. versionadded:: 0.5.01
            Added support for passing kwarg parameters to the cls.

        Parameters
        ------------
        guild_id: int
            The guild ID to retrieve a player for.
        cls: Optional[:class:`RedPlayer`]
            An optional class to pass to build from, overriding the default :class:`Player` class.
            This must be similar to :class:`Player`. E.g a subclass.
        node_id: Optional[str]
            An optional Node identifier to create a player under. If the player already exists this will be ignored.
            Otherwise an attempt to find the node and assign a new player will be made.

        Returns
        ---------
        Player
            The :class:`RedPlayer.Player` associated with the given guild ID.

        Raises
        --------
        InvalidIDProvided
            The given ID does not yield a valid guild or Node.
        ZeroConnectedNodes
            There are no :class:`RedNode`'s currently connected.
        """
        players = self.players

        try:
            player = players[guild_id]
        except KeyError:
            pass
        else:
            return player

        guild = self.bot.get_guild(guild_id)
        if not guild:
            raise wavelink.InvalidIDProvided(
                f"A guild with the id <{guild_id}> can not be located."
            )

        if not self.nodes:
            raise wavelink.ZeroConnectedNodes("There are not any currently connected nodes.")

        if not cls:
            cls = RedPlayer

        if node_id:
            node = self.get_node(identifier=node_id)

            if not node:
                raise wavelink.InvalidIDProvided(
                    f"A Node with the identifier <{node_id}> does not exist."
                )

            player = cls(bot=self.bot, guild_id=guild_id, node=node, **kwargs)
            node.players[guild_id] = player

            return player
        region = self.get_valid_region(guild.region)
        node = self.get_best_node(region=region, shard_id=guild.shard_id, search_only=False)
        player = cls(bot=self.bot, guild_id=guild_id, node=node, **kwargs)
        node.players[guild_id] = player

        return player

    async def build_track(
        self, identifier: str, guild: discord.Guild = None, search_only: bool = None
    ) -> RedTrack:
        """|coro|

        Build a track object with a valid track identifier.

        Parameters
        ------------
        identifier: str
            The tracks unique Base64 encoded identifier. This is usually retrieved from various lavalink events.
        guild: discord.Guild
            Guild making the query.
        search_only: Optional[:class:`bool`]
            Whether the node should be dedicated for search only.

        Returns
        ---------
        :class:`RedTrack`
            The track built from a Base64 identifier.

        Raises
        --------
        ZeroConnectedNodes
            There are no :class:`RedNode`s currently connected.
        BuildTrackError
            Decoding and building the track failed.
        """
        if guild:
            region = self.get_valid_region(guild.region)
        else:
            region = None
        node = self.get_best_node(
            region=region, shard_id=guild.shard_id if guild else None, search_only=search_only
        )

        if node is None:
            raise wavelink.ZeroConnectedNodes

        return await node.build_track(identifier)

    def get_best_node(
        self, region: str = None, shard_id: int = None, search_only: bool = None
    ) -> typing.Optional[RedNode]:
        """Return the best available :class:`RedNode` across the :class:`.RedClient`.
        Parameters
        ----------
        region: Optional[:class:`str`]
            The region to find a node in. Defaults to `None`.

        shard_id: Optional[:class:`int`]
            The shard ID to search for.

        search_only: Optional[:class:`bool`]
            Whether the node should be dedicated for search only.

        Returns
        ---------
        Optional[:class:`Node`]
            The best available :class:`RedNode` available to the :class:`RedClient`.
        """
        nodes = [n for n in self.nodes.values() if n.is_available]
        region_available = []
        shard_id_available = []
        if search_only is not None:
            nodes = [n for n in nodes if n.search_only == search_only and n.is_available]
        if region:
            region_available = [
                n for n in nodes if str(n.region).lower() == str(region).lower() and n.is_available
            ]
        if shard_id:
            shard_id_available = [
                n for n in (region_available or nodes) if n.shard_id == shard_id and n.is_available
            ]
        if not (shard_id_available or region_available or nodes):
            return None
        return min(shard_id_available or region_available or nodes, key=attrgetter("penalty"))

    def get_node_by_region(self, region: str) -> typing.Optional[RedNode]:
        """Retrieve the best available Node with the given region.

        Parameters
        ------------
        region: str
            The region to search for.

        Returns
        ---------
        Optional[:class:`RedNode`]
            The best available Node matching the given region.
            This could be None if no :class:`RedNode` could be found.
        """
        return self.get_best_node(region=region)

    def get_node_by_shard(self, shard_id: int) -> typing.Optional[RedNode]:
        """Retrieve the best available Node with the given shard ID.

        Parameters
        ------------
        shard_id: int
            The shard ID to search for.

        Returns
        ---------
        Optional[:class:`RedNode`]
            The best available Node matching the given Shard ID.
            This could be None if no :class:`RedNode` could be found.
        """
        return self.get_best_node(shard_id=shard_id)

    @property
    def active_players(self) -> typing.Dict[int, RedPlayer]:
        """Return the WaveLink client's current players across all nodes.

        Returns
        ---------
        dict:
            A dict of the current WaveLink players.
        """
        return {
            guild_id: player
            for guild_id, player in self._get_players().items()
            if player.is_connected and (player.is_playing or player.is_paused)
        }

    @property
    def idle_players(self) -> typing.Dict[int, RedPlayer]:
        """Return the WaveLink client's current idle players across all nodes.

        Returns
        ---------
        dict:
            A dict of the current WaveLink players.
        """
        return {
            guild_id: player
            for guild_id, player in self._get_players().items()
            if player.is_connected and not (player.is_playing or player.is_paused)
        }

    @property
    def connected_players(self) -> typing.Dict[int, RedPlayer]:
        """Return the WaveLink client's current connected players across all nodes.

        Returns
        ---------
        dict:
            A dict of the current WaveLink players.
        """
        return {
            guild_id: player
            for guild_id, player in self._get_players().items()
            if player.is_connected
        }

    async def get_tracks(
        self,
        query: str,
        guild: discord.Guild = None,
        search_only: bool = None,
        ctx: commands.Context = None,
    ) -> typing.Optional[RedTrackPlaylist]:
        """|coro|

        Search for and return a list of Tracks for the given query.

        Parameters
        ------------
        query: str
            The query to use to search for tracks. If a valid URL is not provided, it's best to default to
            "ytsearch:query", which allows the REST server to search YouTube for Tracks.

        guild: discord.Guild
            The guild making the request
        search_only: bool
            Whether the node should be a search only node.

        Returns
        ---------
        Union[list, TrackPlaylist, None]:
            A list of or :class:`TrackPlaylist` instance of :class:`Track` objects.
            This could be None if no tracks were found.

        Raises
        --------
        ZeroConnectedNodes
            There are no :class:`RedNode`s currently connected.
            :param search_only:
            :param guild:
        """

        if guild:
            region = self.get_valid_region(guild.region)
            shard_id = guild.shard_id
        else:
            region = None
            shard_id = None
        node = self.get_best_node(region=region, shard_id=shard_id, search_only=search_only)

        if node is None:
            raise wavelink.ZeroConnectedNodes

        if ctx:
            async with ctx.typing():
                return await get_tracks(node, query)
        return await get_tracks(node, query)

    def __repr__(self) -> str:
        return (
            f"Red.Client("
            f"RedNodes={len(self.nodes)}, "
            f"RedPlayers={len(self.players)}, "
            f"SupportedRegions={len(self.valid_regions)}, "
            ")"
        )


class RedEqualizer(wavelink.Equalizer):
    def __init__(self, levels: typing.Iterable[typing.Tuple[int, float]]) -> None:
        _dict = collections.defaultdict(float)
        _dict.update(levels)
        _dict = {i: {"band": i, "gain": _dict[i]} for i in range(15)}
        _dict_eq = [{"band": i, "gain": _dict[i]} for i in range(15)]
        self.eq: typing.Dict[int, typing.Dict[str, typing.Union[int, float]]] = _dict
        self.get: typing.List[typing.Dict[str, typing.Union[int, float]]] = _dict_eq
        self.raw = levels

    def set_gain(self, band: int, gain: float) -> None:
        if band < 0 or band >= (len(list(self.raw)) - 1):
            raise IndexError(f"Band {band} does not exist!")

        gain = min(max(gain, -0.25), 1.0)

        self.eq[band]["gain"] = gain
        self.get[band]["gain"] = gain

    def get_gain(self, band: int) -> float:
        if band < 0 or band >= (len(list(self.raw)) - 1):
            raise IndexError(f"Band {band} does not exist!")
        return self.eq[band]["gain"]

    def visualise(self) -> str:
        block = ""
        _bands = [str(b.get("band")).zfill(2) for b in self.eq.values()]
        _gain = [g.get("gain") for g in self.eq.values()]
        bottom = (" " * 8) + " ".join(_bands)
        gains = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.25]

        for gain in gains:
            prefix = ""
            if gain > 0:
                prefix = "+"
            elif gain == 0:
                prefix = " "

            block += f"{prefix}{gain:.2f} | "

            for value in _gain:
                if value >= gain:
                    block += "[] "
                else:
                    block += "   "

            block += "\n"

        block += bottom
        return block

    @classmethod
    def build(cls, *, levels: list) -> RedEqualizer:
        """Build an Equalizer class with the provided levels.

        Parameters
        ------------
        levels: List[Tuple[int, float]]
            A list of tuple pairs containing a band int and gain float.
        """
        return cls(levels)

    @classmethod
    def flat(cls) -> RedEqualizer:
        """Flat Equalizer.

        Resets your EQ to Flat.
        """
        return cls(
            [
                (0, 0.0),
                (1, 0.0),
                (2, 0.0),
                (3, 0.0),
                (4, 0.0),
                (5, 0.0),
                (6, 0.0),
                (7, 0.0),
                (8, 0.0),
                (9, 0.0),
                (10, 0.0),
                (11, 0.0),
                (12, 0.0),
                (13, 0.0),
                (14, 0.0),
            ]
        )

    @classmethod
    def boost(cls) -> RedEqualizer:
        """Boost Equalizer.

        This equalizer emphasizes Punchy Bass and Crisp Mid-High tones.
        Not suitable for tracks with Deep/Low Bass.
        """
        return cls(
            [
                (0, -0.075),
                (1, 0.125),
                (2, 0.125),
                (3, 0.1),
                (4, 0.1),
                (5, 0.05),
                (6, 0.075),
                (7, 0.0),
                (8, 0.0),
                (9, 0.0),
                (10, 0.0),
                (11, 0.0),
                (12, 0.125),
                (13, 0.15),
                (14, 0.05),
            ]
        )

    @classmethod
    def metal(cls) -> RedEqualizer:
        """Experimental Metal/Rock Equalizer.

        Expect clipping on Bassy songs.
        """
        return cls(
            [
                (0, 0.0),
                (1, 0.1),
                (2, 0.1),
                (3, 0.15),
                (4, 0.13),
                (5, 0.1),
                (6, 0.0),
                (7, 0.125),
                (8, 0.175),
                (9, 0.175),
                (10, 0.125),
                (11, 0.125),
                (12, 0.1),
                (13, 0.075),
                (14, 0.0),
            ]
        )

    @classmethod
    def piano(cls) -> RedEqualizer:
        """Piano Equalizer.

        Suitable for Piano tracks, or tacks with an emphasis on Female Vocals.
        Could also be used as a Bass Cutoff.
        """
        return cls(
            [
                (0, -0.25),
                (1, -0.25),
                (2, -0.125),
                (3, 0.0),
                (4, 0.25),
                (5, 0.25),
                (6, 0.0),
                (7, -0.25),
                (8, -0.25),
                (9, 0.0),
                (10, 0.0),
                (11, 0.5),
                (12, 0.25),
                (13, -0.025),
            ]
        )

    def to_json(self) -> typing.Iterable[typing.Tuple[int, float]]:
        return self.raw


class RedNode(wavelink.node.Node):
    def __init__(
        self,
        host: str,
        port: int,
        shards: int,
        user_id: int,
        *,
        client: RedClient,
        session: aiohttp.ClientSession,
        rest_uri: str,
        password: str,
        region: str,
        identifier: str,
        shard_id: int = None,
        secure: bool = False,
        search_only: bool = False,
    ):
        super().__init__(
            host=host,
            port=port,
            shards=shards,
            user_id=user_id,
            client=client,
            session=session,
            rest_uri=rest_uri,
            password=password,
            region=region,
            identifier=identifier,
            shard_id=shard_id,
            secure=secure,
        )
        self.search_only = search_only

    async def migrate_destroy(self) -> None:
        players = self.players.copy()

        for player in players.values():
            await player.change_node()

        with contextlib.suppress(Exception):
            self._websocket._task.cancel()

        del self._client.nodes[self.identifier]

    def __repr__(self) -> str:
        return (
            "Red.Node("
            f"identifier='{self.identifier}', "
            f"region='{self.region}', "
            f"shard={self.shard_id}, "
            f"search_only={self.search_only}, "
            f"penalty={round(self.penalty, ndigits=3)}, "
            f"players={len(self.players)}, "
            f"stats.players={self.stats.players if self.stats else 0}, "
            f"stats.playing_players={self.stats.playing_players if self.stats else 0}"
            ")"
        )

    async def on_event(self, event) -> None:
        """Function which dispatches events when triggered on the Node."""
        log.debug(f"NODE | Event dispatched:: <{str(event)}> ({self.__repr__()})")
        if str(event) == "TrackEnd" and event.player.queue.empty():
            event = QueueEnd({"player": event.player, "track": event.track})
        await event.player.hook(event)

        if not self.hook:
            return

        if inspect.iscoroutinefunction(self.hook):
            await self.hook(event)
        else:
            self.hook(event)

    @property
    def active_players(self) -> typing.Dict[int, RedPlayer]:
        """Return the WaveLink clients current players across all nodes.

        Returns
        ---------
        dict:
            A dict of the current WaveLink players.
        """
        return {
            guild_id: player
            for guild_id, player in self.players.items()
            if player.is_connected and (player.is_playing or player.is_paused)
        }

    @property
    def idle_players(self) -> typing.Dict[int, RedPlayer]:
        """Return the WaveLink clients current idle players across all nodes.

        Returns
        ---------
        dict:
            A dict of the current WaveLink players.
        """
        return {
            guild_id: player
            for guild_id, player in self.players.items()
            if player.is_connected and not (player.is_playing or player.is_paused)
        }

    @property
    def connected_players(self) -> typing.Dict[int, RedPlayer]:
        """Return the WaveLink clients current connected players across all nodes.

        Returns
        ---------
        dict:
            A dict of the current WaveLink players.
        """
        return {
            guild_id: player for guild_id, player in self.players.items() if player.is_connected
        }


class RedPlayer(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(
        self,
        *args: typing.Any,
        vc: typing.Optional[discord.VoiceChannel] = None,
        notify: typing.Optional[discord.TextChannel] = None,
        guild: typing.Optional[discord.Guild] = None,
        context: typing.Optional[commands.Context] = None,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._metadata: typing.MutableMapping[typing.Any, typing.Any] = {}
        self.context: typing.Optional[commands.Context] = context
        self.vc: typing.Optional[discord.VoiceChannel] = None
        self.notification_channel: typing.Optional[discord.TextChannel] = None
        self.guild: typing.Optional[discord.Guild] = None
        self.current: typing.Optional[RedTrack]
        self.paused: bool
        self.node: wavelink.Node

        if self.context:
            self.dj: discord.Member = self.context.author
            self.guild = self.context.guild
            self.notification_channel = self.context.channel
            self.vc = self.context.author.voice.channel if self.context.author.voice else None

        self.vc = vc or getattr(self, "vc", None) or self.bot.get_channel(self.channel_id)
        self.notification_channel = notify or getattr(self, "notification_channel", None)
        self.guild = guild or getattr(self, "guild", None) or self.bot.get_guild(self.guild_id)

        self.queue: asyncio.Queue = asyncio.Queue()
        self.recent_queue: asyncio.Queue = asyncio.Queue()

        self._shuffle: bool = False
        self._shuffle_bumped: bool = True
        self._repeat: bool = False

        self.waiting: bool = False
        self.updating: bool = False

        self.equalizer: typing.Optional[RedEqualizer] = None

        self.votes: Votes = Votes()

    @property
    def members_in_vc(self) -> int:
        if self.vc and self.vc.members:
            return sum(1 for m in self.vc.members if not m.bot)
        return 1

    @property
    def pause_votes(self) -> int:
        return len(self.votes.pause)

    @property
    def resume_votes(self) -> int:
        return len(self.votes.resume)

    @property
    def skip_votes(self) -> int:
        return len(self.votes.skip)

    @property
    def shuffle_votes(self) -> int:
        return len(self.votes.shuffle)

    @property
    def stop_votes(self) -> int:
        return len(self.votes.stop)

    @property
    def status(self) -> PlayerStatus:
        if self.is_playing:
            return PlayerStatus.PLAYING
        elif self.is_paused:
            return PlayerStatus.PAUSED
        elif self.is_connected:
            return PlayerStatus.CONNECTED
        else:
            return PlayerStatus.DISCONNECTED

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @shuffle.setter
    def shuffle(self, value: bool) -> None:
        self._shuffle = value

    @property
    def shuffle_bumped(self) -> bool:
        return self._shuffle_bumped

    @shuffle_bumped.setter
    def shuffle_bumped(self, value: bool) -> None:
        self._shuffle_bumped = value

    @property
    def repeat(self) -> bool:
        return self._repeat

    @repeat.setter
    def repeat(self, value: bool) -> None:
        self._repeat = value

    def store(self, key: typing.Any, value: typing.Any) -> typing.Any:
        """Stores a metadata value by key."""
        self._metadata[key] = value

    def fetch(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        """
        Returns a stored metadata value.
        Parameters
        ----------
        key
            Key used to store metadata.
        default
            Optional, used if the key doesn't exist.
        """
        return self._metadata.get(key, default)

    def member_listening(self, member: discord.Member) -> bool:
        if self.vc:
            return member in self.vc.members
        return False

    def __repr__(self) -> str:
        return (
            "Red.Player("
            f"status={self.status}, "
            f"queue={self.queue.qsize()}, "
            f"recent_queue={self.recent_queue.qsize()}, "
            f"guild={self.guild.id if self.guild else None}, "
            f"channel={self.vc.id if self.vc else None}, "
            f"notification_channel={self.notification_channel.id if self.notification_channel else None}, "
            f"current='{self.current}', "
            f"volume={self.volume}, "
            f"votes={str(self.votes)}"
            ")"
        )

    async def play_next(self) -> None:
        # Clear the votes for a new song...
        self.votes.pause.clear()
        self.votes.resume.clear()
        self.votes.skip.clear()
        self.votes.shuffle.clear()
        self.votes.stop.clear()

        self.waiting = True
        track = await self.queue.get()

        await self.play(track=track)
        self.waiting = False

        # Invoke our players controller...
        await self.invoke_controller()

    def maybe_shuffle(self, sticky_songs: int = 1) -> None:
        if (
            self.shuffle and not self.queue.empty()
        ):  # Keeps queue order consistent unless adding new tracks
            self.force_shuffle(sticky_songs)

    def force_shuffle(self, sticky_songs: int = 1) -> None:
        if self.queue.empty():
            return
        sticky = max(0, sticky_songs)  # Songs to  bypass shuffle
        # Keeps queue order consistent unless adding new tracks
        if sticky > 0:
            to_keep = list(itertools.islice(self.queue._queue, 0, sticky))
            to_shuffle = list(itertools.islice(self.queue._queue, sticky))
        else:
            to_shuffle = self.queue._queue
            to_keep = []
        if not self.shuffle_bumped:
            to_keep_bumped = [t for t in to_shuffle if t.extras.get("bumped", None)]
            to_shuffle = [t for t in to_shuffle if not t.extras.get("bumped", None)]
            to_keep.extend(to_keep_bumped)
            # Shuffles whole queue
        random.shuffle(to_shuffle)
        to_keep.extend(to_shuffle)
        # Keep next track in queue consistent while adding new tracks
        self.queue._queue = wavelink.collections.deque(to_keep)

    async def move_to(self, channel: discord.VoiceChannel) -> None:
        """
        Moves this player to a voice channel.
        Parameters
        ----------
        channel : discord.VoiceChannel
        """
        if channel.guild != self.guild:
            raise TypeError("Cannot move to a different guild.")

        self.vc = channel
        await self.connect(channel.id)

    async def add(self, requester: discord.abc.User, track: RedTrack) -> None:
        """
        Adds a track to the queue.
        Parameters
        ----------
        requester : discord.User
            User who requested the track.
        track : Track
            Result from any of the lavalink track search methods.
        """
        track.requester = requester
        await self.queue.put(track)

    async def pause(self, pause: bool = None) -> None:
        """
        Pauses the current song.
        Parameters
        ----------
        pause : bool
            Set to ``False`` to resume.
        """
        if pause is None:
            pause = not self.paused
        self.paused = pause
        await self.set_pause(pause)

    async def unpause(self) -> None:
        """Unpause the current song."""
        self.paused = False
        await self.set_pause(False)

    async def play(
        self, track: RedTrack = None, replace: bool = True, start: int = 0, end: int = 0
    ) -> None:
        """|coro|

        Play a WaveLink Track.

        Parameters
        ------------
        track: :class:`Track`
            The :class:`Track` to initiate playing.
        replace: bool
            Whether or not the current track, if there is one, should be replaced or not. Defaults to True.
        start: int
            The position to start the player from in milliseconds. Defaults to 0.
        end: int
            The position to end the track on in milliseconds. By default this always allows the current
            song to finish playing.
        """
        self.vc = self.bot.get_channel(self.channel_id)
        if replace or not self.is_playing:
            self.last_update = 0
            self.last_position = 0
            self.position_timestamp = 0
            self.paused = False
        else:
            return

        if self.guild:
            region = self.node._client.get_valid_region(self.guild.region)
            await self.change_node(shard_id=self.guild.shard_id, region=region)

        if self.current is not None:
            await self.recent_queue.put(self.current)
            if self.repeat:
                await self.queue.put(self.current)

        if not track:
            try:
                with async_timeout.timeout(20):
                    track = await self.queue.get()
            except asyncio.TimeoutError:
                return
        assert isinstance(track, RedTrack)
        no_replace = not replace

        self.current = track
        payload = {
            "op": "play",
            "guildId": str(self.guild_id),
            "track": track.id,
            "noReplace": no_replace,
            "startTime": str(start or track.start_timestamp),
        }
        if end > 0:
            payload["endTime"] = str(end)
        await self.node._send(**payload)

    async def skip(self) -> None:
        await self.play_next()

    async def change_node(
        self, identifier: str = None, shard_id: int = None, region: str = None
    ) -> None:
        """|coro|

        Change the players current :class:`wavelink.node.Node`. Useful when a Node fails or when changing regions.
        The change Node behaviour allows for near seamless fallbacks and changeovers to occur.

        Parameters
        ------------
        Optional[identifier: str]
            An optional Node identifier to change to. If None, the next best available Node will be found.
        """
        client = self.node._client

        if identifier:
            node = client.get_node(identifier)

            if not node:
                raise wavelink.WavelinkException(f"No Nodes matching identifier:: {identifier}")
            elif node == self.node:
                raise wavelink.WavelinkException(
                    "Node identifiers must not be the same while changing."
                )
        else:
            self.node.close()
            node = client.get_best_node(shard_id=shard_id, region=region)
            if node and self.node.identifier == node.identifier:
                self.node.open()
                return
            elif not node:
                self.node.open()
                raise wavelink.WavelinkException("No Nodes available for changeover.")

        self.node.open()

        old = self.node
        del old.players[self.guild_id]
        await old._send(op="destroy", guildId=str(self.guild_id))

        self.node = node
        self.node.players[int(self.guild_id)] = self

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            await self.node._send(
                op="play",
                guildId=str(self.guild_id),
                track=self.current.id,
                startTime=int(self.position),
            )
            self.last_update = time.time() * 1000

            if self.paused:
                await self.node._send(op="pause", guildId=str(self.guild_id), pause=self.paused)

        if self.volume != 100:
            await self.node._send(op="volume", guildId=str(self.guild_id), volume=self.volume)
        if self.equalizer:  # If any bands of the equalizer was modified
            payload = [{"band": b, "gain": g} for b, g in enumerate(self.equalizer.eq)]
            await self.node._send(op="equalizer", guildId=self.guild_id, bands=payload)

    async def teardown(self) -> None:
        """Clear internal states, remove player controller and disconnect."""
        with contextlib.suppress(KeyError):
            await self.destroy()

    async def set_gain(self, band: int, gain: float = 0.0) -> None:
        """
        Sets the equalizer band gain to the given amount.
        Parameters
        ----------
        band: :class:`int`
            Band number (0-14).
        gain: Optional[:class:`float`]
            A float representing gain of a band (-0.25 to 1.00). Defaults to 0.0.
        """
        await self.set_gains((band, gain))

    async def set_gains(self, *gain_list) -> None:
        """
        Modifies the player's equalizer settings.
        Parameters
        ----------
        gain_list: :class:`any`
            A list of tuples denoting (`band`, `gain`).
        """
        update_package = []
        for value in gain_list:
            if not isinstance(value, tuple):
                raise TypeError("gain_list must be a list of tuples")

            band = value[0]
            gain = value[1]

            if not -1 < value[0] < 15:
                raise IndexError("{} is an invalid band, must be 0-14".format(band))

            gain = max(min(float(gain), 1.0), -0.25)
            update_package.append({"band": band, "gain": gain})
            self.equalizer.set_gain(band, gain)

        await self.node._send(op="equalizer", guildId=self.guild_id, bands=update_package)

    async def reset_equalizer(self):
        """Resets equalizer to default values."""
        await self.set_gains(*[(x, 0.0) for x in range(15)])

    async def reset_equalizer(self):
        """Resets equalizer to default values."""
        await self.set_gains(*[(x, 0.0) for x in range(15)])


class RedTrack(wavelink.Track):
    """Wavelink Track object with a extra attributes."""

    __slots__ = (
        "requesting_user",
        "position",
        "seekable",
        "start_timestamp",
        "extras",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requesting_user = kwargs.get("requester")
        self.start_timestamp = kwargs.get("timestamp", 0)
        self.seekable = self.info.get("isSeekable", False)
        self.position = kwargs.get("position", 0)
        self.extras = kwargs.get("extras", {})

    @property
    def is_dead(self) -> bool:
        return self.dead

    @property
    def thumbnail(self) -> typing.Optional[str]:
        return self.thumb

    @property
    def requester(self) -> typing.Optional[discord.Member]:
        return self.requesting_user

    @requester.setter
    def requester(self, requester: discord.Member) -> None:
        self.requesting_user = requester

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, wavelink.Track):
            return self.id == other.id
        return NotImplemented

    def __ne__(self, other: typing.Any) -> bool:
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> hash:
        return hash(self.id) ^ hash(self.uri)


class RedTrackPlaylist(wavelink.TrackPlaylist):
    """Wavelink TrackPlaylist object containing RedTrack objects."""

    def __init__(self, data: dict) -> None:
        _fallback = {
            "loadType": LoadType.LOAD_FAILED,
            "exception": {
                "message": "Lavalink API returned an unsupported response, Please report it.",
                "severity": ExceptionSeverity.SUSPICIOUS,
            },
            "playlistInfo": {},
            "tracks": [],
        }
        self.data = data
        for (k, v) in _fallback.items():
            if k not in data:
                if (
                    k == "exception"
                    and data.get("loadType", LoadType.LOAD_FAILED) != LoadType.LOAD_FAILED
                ):
                    continue
                elif k == "exception":
                    v["message"] = (
                        f"Timestamp: {self.data.get('timestamp', 'Unknown')}\n"
                        f"Status Code: {self.data.get('status', 'Unknown')}\n"
                        f"Error: {self.data.get('error', 'Unknown')}\n"
                        f"Query: {self.data.get('query', 'Unknown')}\n"
                        f"Load Type: {self.data['loadType']}\n"
                        f"Message: {self.data.get('message', v['message'])}"
                    )
                self.data.update({k: v})
        self.load_type = LoadType(self.data["loadType"])
        is_playlist = self.data.get("isPlaylist") or self.load_type == LoadType.PLAYLIST_LOADED
        if is_playlist is True:
            self.is_playlist = True
            self.playlist_info = PlaylistInfo(**self.data["playlistInfo"])
        elif is_playlist is False:
            self.is_playlist = False
            self.playlist_info = None
        else:
            self.is_playlist = None
            self.playlist_info = None
        _tracks = parse_timestamps(data) if data.get("query") else data["tracks"]

        self.tracks = collections.deque(
            RedTrack(id_=track["track"], info=track["info"], extras=track.get("extras", {}))
            for track in _tracks
            if track
        )

    @property
    def has_error(self) -> bool:
        return self.load_type == LoadType.LOAD_FAILED

    @property
    def exception_message(self) -> typing.Union[str, None]:
        """On Lavalink V3, if there was an exception during a load or get tracks call this property
        will be populated with the error message.

        If there was no error this property will be ``None``.
        """
        if self.has_error:
            exception_data = self._raw.get("exception", {})
            return exception_data.get("message")
        return None

    @property
    def exception_severity(self) -> typing.Union[ExceptionSeverity, None]:
        if self.has_error:
            exception_data = self._raw.get("exception", {})
            severity = exception_data.get("severity")
            if severity is not None:
                return ExceptionSeverity(severity)
        return None


class Votes:
    def __init__(self) -> None:
        self._pause = set()
        self._resume = set()
        self._skip = set()
        self._shuffle = set()
        self._stop = set()

    @property
    def pause(self) -> typing.Set[int]:
        return self._pause

    @property
    def resume(self) -> typing.Set[int]:
        return self._resume

    @property
    def skip(self) -> typing.Set[int]:
        return self._skip

    @property
    def shuffle(self) -> typing.Set[int]:
        return self._shuffle

    @property
    def stop(self) -> typing.Set[int]:
        return self._stop

    def __rep__(self):
        return (
            f"Votes(pause={len(self.pause)}, "
            f"resume={len(self.resume)}, "
            f"skip={len(self.skip)}, "
            f"shuffle={len(self.shuffle)}, "
            f"stop={len(self.stop)})"
        )


def PlaylistInfo(
    name: typing.Optional[str] = None, selectedTrack: typing.Optional[int] = None
) -> _PlaylistInfo:
    return _PlaylistInfo(
        name if name is not None else "Unknown",
        selectedTrack if selectedTrack is not None else -1,
    )


async def get_tracks(node: wavelink.Node, query: str) -> typing.Optional[RedTrackPlaylist]:
    """|coro|

    Search for and return a list of Tracks for the given query.

    Parameters
    ------------
    node: wavelink.Node
        The Note to submit query to.
    query: str
        The query to use to search for tracks. If a valid URL is not provided, it's best to default to
        "ytsearch:query", which allows the REST server to search YouTube for Tracks.

    Returns
    ---------
    Union[RedTrackPlaylist, None]:
        A list of or TrackPlaylist instance of :class:`RedTrack` objects.
        This could be None if no tracks were found.
    """
    _raw_url = str(query)
    parsed_url = reformat_query(_raw_url)
    url = quote(parsed_url)
    try:
        async with node.session.get(
            f"{node.rest_uri}/loadtracks?identifier={url}",
            headers={"Authorization": node.password},
        ) as resp:
            data = await resp.json()
    except aiohttp.ServerDisconnectedError:
        if not node.is_available:
            data = {
                "loadType": LoadType.LOAD_FAILED,
                "exception": {
                    "message": "Load tracks interrupted by player disconnect.",
                    "severity": ExceptionSeverity.COMMON,
                },
                "tracks": [],
            }
            return RedTrackPlaylist(data)
        raise
    if data is not None:
        if isinstance(data, dict):
            data["query"] = _raw_url
            data["encodedquery"] = url
            return RedTrackPlaylist(data)
        elif isinstance(data, list):
            modified_data = {
                "loadType": LoadType.V2_COMPAT,
                "tracks": data,
                "query": _raw_url,
                "encodedquery": url,
            }
            return RedTrackPlaylist(modified_data)
    return data


def parse_timestamps(data: typing.Dict) -> typing.List[typing.Dict]:
    if data["loadType"] == LoadType.PLAYLIST_LOADED:
        return data["tracks"]

    new_tracks = []
    query = data["query"]
    try:
        query_url = urlparse(query)
    except:
        query_url = None
    if not query_url:
        return data["tracks"]

    for track in data["tracks"]:
        start_time = 0
        with contextlib.suppress(Exception):
            if all([query_url.scheme, query_url.netloc, query_url.path]) or any(
                x in query for x in ["ytsearch:", "scsearch:"]
            ):
                url_domain = ".".join(query_url.netloc.split(".")[-2:])
                if not query_url.netloc:
                    url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
                if (
                    (url_domain in ["youtube.com", "youtu.be"] or "ytsearch:" in query)
                    and any(x in query for x in ["&t=", "?t="])
                    and not all(k in query for k in ["playlist?", "&list="])
                ):
                    match = re.search(regex.YOUTUBE_TIMESTAMP, query)
                    if match:
                        start_time = int(match.group(1))
                elif (url_domain == "soundcloud.com" or "scsearch:" in query) and "#t=" in query:
                    if "/sets/" not in query or ("/sets/" in query and "?in=" in query):
                        match = re.search(regex.SOUNDCLOUD_TIMESTAMP, query)
                        if match:
                            start_time = (int(match.group(1)) * 60) + int(match.group(2))
                elif url_domain == "twitch.tv" and "?t=" in query:
                    match = re.search(regex.TWITCH_TIMESTAMP, query)
                    if match:
                        start_time = (
                            (int(match.group(1)) * 60 * 60)
                            + (int(match.group(2)) * 60)
                            + int(match.group(3))
                        )
        track["info"]["timestamp"] = start_time * 1000
        new_tracks.append(track)
    return new_tracks


def reformat_query(query: str) -> str:
    with contextlib.suppress(Exception):
        query_url = urlparse(query)
        if all([query_url.scheme, query_url.netloc, query_url.path]) or any(
            x in query for x in ["ytsearch:", "scsearch:"]
        ):
            url_domain = ".".join(query_url.netloc.split(".")[-2:])
            if not query_url.netloc:
                url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
            if (
                (url_domain in ["youtube.com", "youtu.be"] or "ytsearch:" in query)
                and any(x in query for x in ["&t=", "?t="])
                and not all(k in query for k in ["playlist?", "&list="])
            ):
                match = re.search(regex.YOUTUBE_TIMESTAMP, query)
                if match:
                    query = query.split("&t=")[0].split("?t=")[0]
            elif (url_domain == "soundcloud.com" or "scsearch:" in query) and "#t=" in query:
                if "/sets/" not in query or ("/sets/" in query and "?in=" in query):
                    match = re.search(regex.SOUNDCLOUD_TIMESTAMP, query)
                    if match:
                        query = query.split("#t=")[0]
            elif url_domain == "twitch.tv" and "?t=" in query:
                match = re.search(regex.TWITCH_TIMESTAMP, query)
                if match:
                    query = query.split("?t=")[0]
    return query
