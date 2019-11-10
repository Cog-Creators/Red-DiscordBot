import asyncio
import contextlib
import os
import re
import time
from urllib.parse import urlparse

import discord
import lavalink

from redbot.core import Config, commands
from redbot.core.bot import Red
from . import audio_dataclasses

from .converters import _pass_config_to_converters

from .playlists import _pass_config_to_playlist

__all__ = [
    "pass_config_to_dependencies",
    "track_limit",
    "queue_duration",
    "draw_time",
    "dynamic_time",
    "match_url",
    "clear_react",
    "match_yt_playlist",
    "remove_react",
    "get_description",
    "track_creator",
    "time_convert",
    "url_check",
    "userlimit",
    "is_allowed",
    "CacheLevel",
    "Notifier",
]
_re_time_converter = re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])")
re_yt_list_playlist = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.?be)(/playlist\?).*(list=)(.*)(&|$)"
)

_config = None
_bot = None


def pass_config_to_dependencies(config: Config, bot: Red, localtracks_folder: str):
    global _bot, _config
    _bot = bot
    _config = config
    _pass_config_to_playlist(config, bot)
    _pass_config_to_converters(config, bot)
    audio_dataclasses._pass_config_to_dataclasses(config, bot, localtracks_folder)


def track_limit(track, maxlength):
    try:
        length = round(track.length / 1000)
    except AttributeError:
        length = round(track / 1000)

    if maxlength < length <= 900000000000000:  # livestreams return 9223372036854775807ms
        return False
    return True


async def is_allowed(guild: discord.Guild, query: str):
    query = query.lower().strip()
    whitelist = set(await _config.guild(guild).url_keyword_whitelist())
    if whitelist:
        return any(i in query for i in whitelist)
    blacklist = set(await _config.guild(guild).url_keyword_blacklist())
    return not any(i in query for i in blacklist)


async def queue_duration(ctx):
    player = lavalink.get_player(ctx.guild.id)
    duration = []
    for i in range(len(player.queue)):
        if not player.queue[i].is_stream:
            duration.append(player.queue[i].length)
    queue_dur = sum(duration)
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


async def draw_time(ctx):
    player = lavalink.get_player(ctx.guild.id)
    paused = player.paused
    pos = player.position
    dur = player.current.length
    sections = 12
    loc_time = round((pos / dur) * sections)
    bar = "\N{BOX DRAWINGS HEAVY HORIZONTAL}"
    seek = "\N{RADIO BUTTON}"
    if paused:
        msg = "\N{DOUBLE VERTICAL BAR}"
    else:
        msg = "\N{BLACK RIGHT-POINTING TRIANGLE}"
    for i in range(sections):
        if i == loc_time:
            msg += seek
        else:
            msg += bar
    return msg


def dynamic_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    if d > 0:
        msg = "{0}d {1}h"
    elif d == 0 and h > 0:
        msg = "{1}h {2}m"
    elif d == 0 and h == 0 and m > 0:
        msg = "{2}m {3}s"
    elif d == 0 and h == 0 and m == 0 and s > 0:
        msg = "{3}s"
    else:
        msg = ""
    return msg.format(d, h, m, s)


def match_url(url):
    try:
        query_url = urlparse(url)
        return all([query_url.scheme, query_url.netloc, query_url.path])
    except Exception:
        return False


def match_yt_playlist(url):
    if re_yt_list_playlist.match(url):
        return True
    return False


async def remove_react(message, react_emoji, react_user):
    with contextlib.suppress(discord.HTTPException):
        await message.remove_reaction(react_emoji, react_user)


async def clear_react(bot: Red, message: discord.Message, emoji: dict = None):
    try:
        await message.clear_reactions()
    except discord.Forbidden:
        if not emoji:
            return
        with contextlib.suppress(discord.HTTPException):
            for key in emoji.values():
                await asyncio.sleep(0.2)
                await message.remove_reaction(key, bot.user)
    except discord.HTTPException:
        return


async def get_description(track):
    if any(x in track.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
        local_track = audio_dataclasses.LocalPath(track.uri)
        if track.title != "Unknown title":
            return "**{} - {}**\n{}".format(
                track.author, track.title, local_track.to_string_hidden()
            )
        else:
            return local_track.to_string_hidden()
    else:
        return "**[{}]({})**".format(track.title, track.uri)


def track_creator(player, position=None, other_track=None):
    if position == "np":
        queued_track = player.current
    elif position is None:
        queued_track = other_track
    else:
        queued_track = player.queue[position]
    track_keys = queued_track._info.keys()
    track_values = queued_track._info.values()
    track_id = queued_track.track_identifier
    track_info = {}
    for k, v in zip(track_keys, track_values):
        track_info[k] = v
    keys = ["track", "info"]
    values = [track_id, track_info]
    track_obj = {}
    for key, value in zip(keys, values):
        track_obj[key] = value
    return track_obj


def time_convert(length):
    match = re.compile(_re_time_converter).match(length)
    if match is not None:
        hr = int(match.group(1)) if match.group(1) else 0
        mn = int(match.group(2)) if match.group(2) else 0
        sec = int(match.group(3)) if match.group(3) else 0
        pos = sec + (mn * 60) + (hr * 3600)
        return pos
    else:
        try:
            return int(length)
        except ValueError:
            return 0


def url_check(url):
    valid_tld = [
        "youtube.com",
        "youtu.be",
        "soundcloud.com",
        "bandcamp.com",
        "vimeo.com",
        "beam.pro",
        "mixer.com",
        "twitch.tv",
        "spotify.com",
        "localtracks",
    ]
    query_url = urlparse(url)
    url_domain = ".".join(query_url.netloc.split(".")[-2:])
    if not query_url.netloc:
        url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
    return True if url_domain in valid_tld else False


def userlimit(channel):
    if channel.user_limit == 0 or channel.user_limit > len(channel.members) + 1:
        return False
    return True


class CacheLevel:
    __slots__ = ("value",)

    def __init__(self, level=0):
        if not isinstance(level, int):
            raise TypeError(
                f"Expected int parameter, received {level.__class__.__name__} instead."
            )
        elif level < 0:
            level = 0
        elif level > 0b11111:
            level = 0b11111

        self.value = level

    def __eq__(self, other):
        return isinstance(other, CacheLevel) and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)

    def __add__(self, other):
        return CacheLevel(self.value + other.value)

    def __radd__(self, other):
        return CacheLevel(other.value + self.value)

    def __sub__(self, other):
        return CacheLevel(self.value - other.value)

    def __rsub__(self, other):
        return CacheLevel(other.value - self.value)

    def __str__(self):
        return "{0:b}".format(self.value)

    def __format__(self, format_spec):
        return "{r:{f}}".format(r=self.value, f=format_spec)

    def __repr__(self):
        return f"<CacheLevel value={self.value}>"

    def is_subset(self, other):
        """Returns ``True`` if self has the same or fewer caching levels as other."""
        return (self.value & other.value) == self.value

    def is_superset(self, other):
        """Returns ``True`` if self has the same or more caching levels as other."""
        return (self.value | other.value) == self.value

    def is_strict_subset(self, other):
        """Returns ``True`` if the caching level on other are a strict subset of those on self."""
        return self.is_subset(other) and self != other

    def is_strict_superset(self, other):
        """Returns ``True`` if the caching level on
        other are a strict superset of those on self."""
        return self.is_superset(other) and self != other

    __le__ = is_subset
    __ge__ = is_superset
    __lt__ = is_strict_subset
    __gt__ = is_strict_superset

    @classmethod
    def all(cls):
        """A factory method that creates a :class:`CacheLevel` with max caching level."""
        return cls(0b11111)

    @classmethod
    def none(cls):
        """A factory method that creates a :class:`CacheLevel` with no caching."""
        return cls(0)

    @classmethod
    def set_spotify(cls):
        """A factory method that creates a :class:`CacheLevel` with Spotify caching level."""
        return cls(0b00011)

    @classmethod
    def set_youtube(cls):
        """A factory method that creates a :class:`CacheLevel` with YouTube caching level."""
        return cls(0b00100)

    @classmethod
    def set_lavalink(cls):
        """A factory method that creates a :class:`CacheLevel` with lavalink caching level."""
        return cls(0b11000)

    def _bit(self, index):
        return bool((self.value >> index) & 1)

    def _set(self, index, value):
        if value is True:
            self.value |= 1 << index
        elif value is False:
            self.value &= ~(1 << index)
        else:
            raise TypeError("Value to set for CacheLevel must be a bool.")

    @property
    def lavalink(self):
        """:class:`bool`: Returns ``True`` if a user can deafen other users."""
        return self._bit(4)

    @lavalink.setter
    def lavalink(self, value):
        self._set(4, value)

    @property
    def youtube(self):
        """:class:`bool`: Returns ``True`` if a user can move users between other voice
        channels."""
        return self._bit(2)

    @youtube.setter
    def youtube(self, value):
        self._set(2, value)

    @property
    def spotify(self):
        """:class:`bool`: Returns ``True`` if a user can use voice activation in voice channels."""
        return self._bit(1)

    @spotify.setter
    def spotify(self, value):
        self._set(1, value)


class Notifier:
    def __init__(self, ctx: commands.Context, message: discord.Message, updates: dict, **kwargs):
        self.context = ctx
        self.message = message
        self.updates = updates
        self.color = None
        self.last_msg_time = 0
        self.cooldown = 5

    async def notify_user(
        self,
        current: int = None,
        total: int = None,
        key: str = None,
        seconds_key: str = None,
        seconds: str = None,
    ):
        """
        This updates an existing message.
        Based on the message found in :variable:`Notifier.updates` as per the `key` param
        """
        if self.last_msg_time + self.cooldown > time.time() and not current == total:
            return
        if self.color is None:
            self.color = await self.context.embed_colour()
        embed2 = discord.Embed(
            colour=self.color,
            title=self.updates.get(key).format(num=current, total=total, seconds=seconds),
        )
        if seconds and seconds_key:
            embed2.set_footer(text=self.updates.get(seconds_key).format(seconds=seconds))
        try:
            await self.message.edit(embed=embed2)
            self.last_msg_time = time.time()
        except discord.errors.NotFound:
            pass

    async def update_text(self, text: str):
        embed2 = discord.Embed(colour=self.color, title=text)
        try:
            await self.message.edit(embed=embed2)
        except discord.errors.NotFound:
            pass

    async def update_embed(self, embed: discord.Embed):
        try:
            await self.message.edit(embed=embed)
            self.last_msg_time = time.time()
        except discord.errors.NotFound:
            pass
