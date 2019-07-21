import time
from typing import NoReturn

import discord
import lavalink

from redbot.core import commands


def track_limit(track, maxlength):
    try:
        length = round(track.length / 1000)
    except AttributeError:
        length = round(track / 1000)
    if length > 900000000000000:  # livestreams return 9223372036854775807ms
        return True
    elif length >= maxlength:
        return False
    else:
        return True


async def queue_duration(ctx):
    player = lavalink.get_player(ctx.guild.id)
    duration = []
    for i in range(len(player.queue)):
        if not player.queue[i].is_stream:
            duration.append(player.queue[i].length)
    queue_duration = sum(duration)
    if not player.queue:
        queue_duration = 0
    try:
        if not player.current.is_stream:
            remain = player.current.length - player.position
        else:
            remain = 0
    except AttributeError:
        remain = 0
    queue_total_duration = remain + queue_duration
    return queue_total_duration


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
        if isinstance(other, CacheLevel):
            return CacheLevel(self.value + other.value)
        else:
            raise TypeError(
                "cannot add {} with {}".format(self.__class__.__name__, other.__class__.__name__)
            )

    def __radd__(self, other):
        if isinstance(other, CacheLevel):
            val = other.value + self.value
            return CacheLevel(val)
        else:
            raise TypeError(
                "cannot add {} with {}".format(self.__class__.__name__, other.__class__.__name__)
            )

    def __sub__(self, other):
        if isinstance(other, CacheLevel):
            val = self.value - other.value
            return CacheLevel(val)
        else:
            raise TypeError(
                "cannot add {} with {}".format(self.__class__.__name__, other.__class__.__name__)
            )

    def __rsub__(self, other):
        if isinstance(other, CacheLevel):
            val = other.value - self.value
            return CacheLevel(val)
        else:
            raise TypeError(
                "cannot add {} with {}".format(self.__class__.__name__, other.__class__.__name__)
            )

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
        """Returns ``True`` if the caching level on other are a strict superset of those on self."""
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
    ) -> NoReturn:
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
        if seconds:
            embed2.set_footer(text=self.updates.get(seconds_key).format(seconds=seconds))
        try:
            await self.message.edit(embed=embed2)
            self.last_msg_time = time.time()
        except discord.errors.NotFound:
            pass

    async def update_text(self, text: str) -> NoReturn:
        embed2 = discord.Embed(colour=self.color, title=text)
        try:
            await self.message.edit(embed=embed2)
        except discord.errors.NotFound:
            pass
