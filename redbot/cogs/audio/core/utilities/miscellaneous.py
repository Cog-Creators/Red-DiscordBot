import asyncio
import contextlib
import datetime
import functools
import logging
import re
from typing import MutableMapping, Union, Any, Final

import discord
import lavalink
from discord.embeds import EmptyEmbed

from redbot.core import bank, commands
from redbot.core.utils.chat_formatting import humanize_number
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, _

log = logging.getLogger("red.cogs.Audio.cog.Utilities.miscellaneous")

_RE_TIME_CONVERTER: Final[re.Pattern] = re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])")


class MiscellaneousUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def _clear_react(
        self, message: discord.Message, emoji: MutableMapping = None
    ) -> asyncio.Task:
        """Non blocking version of clear_react."""
        return self.bot.loop.create_task(self.clear_react(message, emoji))

    async def _currency_check(self, ctx: commands.Context, jukebox_price: int) -> bool:
        jukebox = await self.config.guild(ctx.guild).jukebox()
        if jukebox and not await self._can_instaskip(ctx, ctx.author):
            can_spend = await bank.can_spend(ctx.author, jukebox_price)
            if can_spend:
                await bank.withdraw_credits(ctx.author, jukebox_price)
            else:
                credits_name = await bank.get_currency_name(ctx.guild)
                bal = await bank.get_balance(ctx.author)
                await self._embed_msg(
                    ctx,
                    title=_("Not enough {currency}").format(currency=credits_name),
                    description=_(
                        "{required_credits} {currency} required, but you have {bal}."
                    ).format(
                        currency=credits_name,
                        required_credits=humanize_number(jukebox_price),
                        bal=humanize_number(bal),
                    ),
                )
            return can_spend
        else:
            return True

    async def _embed_msg(self, ctx: commands.Context, **kwargs) -> discord.Message:
        colour = kwargs.get("colour") or kwargs.get("color") or await self.bot.get_embed_color(ctx)
        title = kwargs.get("title", EmptyEmbed) or EmptyEmbed
        _type = kwargs.get("type", "rich") or "rich"
        url = kwargs.get("url", EmptyEmbed) or EmptyEmbed
        description = kwargs.get("description", EmptyEmbed) or EmptyEmbed
        timestamp = kwargs.get("timestamp")
        footer = kwargs.get("footer")
        thumbnail = kwargs.get("thumbnail")
        contents = dict(title=title, type=_type, url=url, description=description)
        if hasattr(kwargs.get("embed"), "to_dict"):
            embed = kwargs.get("embed")
            if embed is not None:
                embed = embed.to_dict()
        else:
            embed = {}
        colour = embed.get("color") if embed.get("color") else colour
        contents.update(embed)
        if timestamp and isinstance(timestamp, datetime.datetime):
            contents["timestamp"] = timestamp
        embed = discord.Embed.from_dict(contents)
        embed.color = colour
        if footer:
            embed.set_footer(text=footer)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return await ctx.send(embed=embed)

    async def _process_db(self, ctx: commands.Context) -> None:
        if self.api_interface is not None:
            await self.api_interface.run_tasks(ctx)

    async def _close_database(self) -> None:
        if self.api_interface is not None:
            await self.api_interface.run_all_pending_tasks()
            self.api_interface.close()

    async def _check_api_tokens(self) -> MutableMapping:
        spotify = await self.bot.get_shared_api_tokens("spotify")
        youtube = await self.bot.get_shared_api_tokens("youtube")
        return {
            "spotify_client_id": spotify.get("client_id", ""),
            "spotify_client_secret": spotify.get("client_secret", ""),
            "youtube_api": youtube.get("api_key", ""),
        }

    async def _check_external(self) -> bool:
        external = await self.config.use_external_lavalink()
        if not external:
            if self.player_manager is not None:
                await self.player_manager.shutdown()
            await self.config.use_external_lavalink.set(True)
            return True
        else:
            return False

    def rsetattr(self, obj, attr, val) -> None:
        pre, _, post = attr.rpartition(".")
        setattr(self.rgetattr(obj, pre) if pre else obj, post, val)

    def rgetattr(self, obj, attr, *args) -> Any:
        def _getattr(obj2, attr2):
            return getattr(obj2, attr2, *args)

        return functools.reduce(_getattr, [obj] + attr.split("."))

    async def remove_react(
        self,
        message: discord.Message,
        react_emoji: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
        react_user: discord.abc.User,
    ) -> None:
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction(react_emoji, react_user)

    async def clear_react(self, message: discord.Message, emoji: MutableMapping = None) -> None:
        try:
            await message.clear_reactions()
        except discord.Forbidden:
            if not emoji:
                return
            with contextlib.suppress(discord.HTTPException):
                for key in emoji.values():
                    await asyncio.sleep(0.2)
                    await message.remove_reaction(key, self.bot.user)
        except discord.HTTPException:
            return

    def track_creator(
        self,
        player: lavalink.Player,
        position: Union[int, str] = None,
        other_track: lavalink.Track = None,
    ) -> MutableMapping:
        if position == "np":
            queued_track = player.current
        elif position is None:
            queued_track = other_track
        else:
            queued_track = player.queue[position]
        return self.track_to_json(queued_track)

    def track_to_json(self, track: lavalink.Track) -> MutableMapping:
        track_keys = track._info.keys()
        track_values = track._info.values()
        track_id = track.track_identifier
        track_info = {}
        for k, v in zip(track_keys, track_values):
            track_info[k] = v
        keys = ["track", "info", "extras"]
        values = [track_id, track_info]
        track_obj = {}
        for key, value in zip(keys, values):
            track_obj[key] = value
        return track_obj

    def time_convert(self, length: Union[int, str]) -> int:
        if isinstance(length, int):
            return length

        match = _RE_TIME_CONVERTER.match(length)
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

    async def queue_duration(self, ctx: commands.Context) -> int:
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

    async def track_remaining_duration(self, ctx: commands.Context) -> int:
        player = lavalink.get_player(ctx.guild.id)
        if not player.current:
            return 0
        try:
            if not player.current.is_stream:
                remain = player.current.length - player.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        return remain

    def dynamic_time(self, seconds: int) -> str:
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
