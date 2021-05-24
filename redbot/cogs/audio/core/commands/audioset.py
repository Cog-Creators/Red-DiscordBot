import asyncio
import contextlib
import datetime
import logging
import math
import os
import tarfile
from operator import attrgetter
from pathlib import Path
from typing import Union

import discord
import lavalink

from redbot.core import bank, commands
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils._dpy_menus_utils import dpymenu
from redbot.core.utils.chat_formatting import box, humanize_number, pagify
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from ...audio_dataclasses import LocalPath
from ...converters import ScopeParser
from ...errors import MissingGuild, TooManyMatches
from ...utils import CacheLevel, PlaylistScope, has_internal_server
from ..abc import MixinMeta
from ..cog_utils import (
    CompositeMetaClass,
    ENABLED_TITLE,
    PlaylistConverter,
    __version__,
    DISABLED_TITLE,
    ENABLED,
    DISABLED,
)

log = logging.getLogger("red.cogs.Audio.cog.Commands.audioset")

_ = Translator("Audio", Path(__file__))


class AudioSetCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="audioset")
    @commands.bot_has_permissions(embed_links=True)
    async def command_audioset(self, ctx: commands.Context):
        """Music configuration options."""

    # --------------------------- GLOBAL COMMANDS ----------------------------

    @command_audioset.group(name="global")
    @commands.is_owner()
    async def command_audioset_global(self, ctx: commands.Context):
        """Bot owner controlled configuration options."""

    @command_audioset_global.command(name="volume", aliases=["vol"])
    async def command_audioset_global_volume(self, ctx: commands.Context, volume: int):
        """Set the maximum allowed volume to be set by servers."""
        if not 10 < volume < 500:
            await self.send_embed_msg(
                ctx,
                title=_("Invalid Setting"),
                description=_("Maximum allowed volume has to be between 10% and 500%.").format(
                    volume=volume
                ),
            )
            return
        await self.config_cache.volume.set_global(volume)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Maximum allowed volume set to: {volume}%.").format(volume=volume),
        )

    @command_audioset_global.command(name="dailyqueue")
    async def command_audioset_global_dailyqueue_override(self, ctx: commands.Context):
        """Toggle daily queues, if set to disable, it will disable in all servers

        Daily queues creates a playlist for all tracks played today.

        If disabled, servers will not be able to overwrite it.
        """
        daily_playlists = await self.config_cache.daily_playlist.get_global()
        await self.config_cache.daily_playlist.set_global(not daily_playlists)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Global Daily queues: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not daily_playlists else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="notify")
    async def command_audioset_global_dailyqueue_notify(self, ctx: commands.Context):
        """Toggle track announcement and other bot messages.


        If disabled, servers will not be able to overwrite it.
        """
        daily_playlists = await self.config_cache.daily_playlist.get_global()
        await self.config_cache.daily_playlist.set_global(not daily_playlists)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Global track announcement: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not daily_playlists else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="autodeafen")
    async def command_audioset_global_auto_deafen(self, ctx: commands.Context):
        """Toggle whether the bot will be auto deafened upon joining the voice channel.

        If enabled, servers will not be able to override it.
        """
        auto_deafen = await self.config_cache.auto_deafen.get_global()
        await self.config_cache.auto_deafen.set_global(not auto_deafen)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Auto Deafen: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not auto_deafen else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="emptydisconnect", aliases=["emptydc"])
    async def command_audioset_global_emptydisconnect(self, ctx: commands.Context, seconds: int):
        """Auto-disconnect from channel when bot is alone in it for x seconds, 0 to disable.

        `[p]audioset global dc` takes precedence over this setting.

        If enabled, servers cannot override / set a lower time in seconds.
        """
        if seconds < 0:
            return await self.send_embed_msg(
                ctx, title=_("Invalid Time"), description=_("Seconds can't be less than zero.")
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Global empty disconnect disabled.")
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Global empty disconnect timer set to {num_seconds}.").format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_dc_timer.set_global(seconds)
        await self.config_cache.empty_dc.set_global(enabled)

    @command_audioset_global.command(name="emptypause")
    async def command_audioset_global_emptypause(self, ctx: commands.Context, seconds: int):
        """Auto-pause after x seconds when room is empty, 0 to disable.

        If enabled, servers cannot override / set a lower time in seconds.
        """
        if seconds < 0:
            return await self.send_embed_msg(
                ctx, title=_("Invalid Time"), description=_("Seconds can't be less than zero.")
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Global empty pause disabled.")
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Global empty pause timer set to {num_seconds}.").format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_pause_timer.set_global(seconds)
        await self.config_cache.empty_pause.set_global(enabled)

    @command_audioset_global.command(name="lyrics")
    async def command_audioset_global_lyrics(self, ctx: commands.Context):
        """Prioritise tracks with lyrics globally.

        If enabled, servers cannot override.
        """
        prefer_lyrics = await self.config_cache.prefer_lyrics.get_global()
        await self.config_cache.prefer_lyrics.set_global(not prefer_lyrics)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Prefer tracks with lyrics globally: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not prefer_lyrics else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="disconnect", aliases=["dc"])
    async def command_audioset_global_dc(self, ctx: commands.Context):
        """Toggle the bot auto-disconnecting when done playing.

        This setting takes precedence over `[p]audioset global emptydisconnect`.

        If enabled, servers cannot override.
        """
        disconnect = await self.config_cache.disconnect.get_global()
        msg = ""
        msg += _("Global auto-disconnection at queue end: {true_or_false}.").format(
            true_or_false=ENABLED_TITLE if not disconnect else DISABLED_TITLE
        )
        await self.config_cache.disconnect.set_global(not disconnect)

        await self.send_embed_msg(ctx, title=_("Setting Changed"), description=msg)

    @command_audioset_global.command(name="jukebox")
    async def command_audioset_global_jukebox(self, ctx: commands.Context, price: int):
        """Set a price for queueing tracks for non-mods, 0 to disable.

        If set servers can never go below this value and the jukebox will be enabled globally.
        """

        if not await bank.is_global():
            await self.config_cache.jukebox.set_global(False)
            await self.config_cache.jukebox_price.set_global(0)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Jukebox Mode: {true_or_false}\n"
                    "Price per command: {cost} {currency}\n"
                    "\n\n**Reason**: You cannot enable this feature if the bank isn't global\n"
                    "Use `[p]bankset toggleglobal` from the "
                    "`Bank` cog to enable a global bank first."
                ).format(
                    true_or_false=ENABLED_TITLE,
                    cost=0,
                    currency=await bank.get_currency_name(ctx.guild),
                ),
            )

        if price < 0:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Price"),
                description=_("Price can't be less than zero."),
            )
        elif price > 2 ** 63 - 1:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Price"),
                description=_("Price can't be greater or equal to than 2^63."),
            )
        elif price == 0:
            jukebox = False
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Global jukebox mode disabled.")
            )
        else:
            jukebox = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Global track queueing command price set to {price} {currency}."
                ).format(
                    price=humanize_number(price), currency=await bank.get_currency_name(ctx.guild)
                ),
            )
        await self.config_cache.jukebox_price.set_global(price)
        await self.config_cache.jukebox.set_global(jukebox)

    @command_audioset_global.command(name="maxlength")
    async def command_audioset_global_maxlength(
        self, ctx: commands.Context, seconds: Union[int, str]
    ):
        """Max length of a track to queue in seconds, 0 to disable.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`). Invalid input will turn the max length setting off.

        Setting this value means that servers will never be able to bypass it, however they will be allowed to set short lengths.
        """
        if not isinstance(seconds, int):
            seconds = self.time_convert(seconds)
        if seconds < 0:
            return await self.send_embed_msg(
                ctx, title=_("Invalid length"), description=_("Length can't be less than zero.")
            )
        if seconds == 0:
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Global track max length disabled.")
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Global track max length set to {seconds}.").format(
                    seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.max_track_length.set_global(seconds)

    @command_audioset_global.command(name="maxqueue")
    async def command_audioset_global_maxqueue(self, ctx: commands.Context, size: int):
        """Set the maximum size a queue is allowed to be.

        Default is 10,000, servers cannot go over this value, but they can set smaller values.
        """
        if not 10 < size < 20_000:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Queue Size"),
                description=_("Queue size must bet between 10 and {cap}.").format(
                    cap=humanize_number(20_000)
                ),
            )
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Maximum queue size allowed is now {size}.").format(
                size=humanize_number(size)
            ),
        )
        await self.config_cache.max_queue_size.set_global(size)

    @command_audioset_global.command(name="thumbnail")
    async def command_audioset_global_thumbnail(self, ctx: commands.Context):
        """Toggle displaying a thumbnail on audio messages.

        If enabled servers will not be able to override this setting.
        """
        thumbnail = await self.config_cache.thumbnail.get_global()
        await self.config_cache.thumbnail.set_global(not thumbnail)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Global thumbnail display: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not thumbnail else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="countrycode")
    async def command_audioset_global_countrycode(self, ctx: commands.Context, country: str):
        """Set the country code for Spotify searches.

        This can be override by servers, however it will set the default value for the bot.
        """
        if len(country) != 2:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Country Code"),
                description=_(
                    "Please use an official [ISO 3166-1 alpha-2]"
                    "(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code."
                ),
            )
        country = country.upper()
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Global country Code set to {country}.").format(country=country),
        )

        await self.config_cache.country_code.set_global(country)

    @command_audioset_global.command(name="persistqueue")
    async def command_audioset_global_persist_queue(self, ctx: commands.Context):
        """Toggle persistent queues.

        Persistent queues allows the current queue to be restored when the queue closes.

        If set servers will be able to overwrite this value.
        """
        persist_cache = await self.config_cache.persistent_queue.get_global()
        await self.config_cache.persistent_queue.set_global(not persist_cache)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Global queue persistence: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not persist_cache else DISABLED_TITLE
            ),
        )

    @command_audioset_global.group(name="allowlist", aliases=["whitelist"])
    async def command_audioset_global_whitelist(self, ctx: commands.Context):
        """Manages the global keyword allowlist."""

    @command_audioset_global_whitelist.command(name="add")
    async def command_audioset_global_whitelist_add(self, ctx: commands.Context, *, keyword: str):
        """Adds a keyword to the allowlist.

        If anything is added to allowlist, it will reject everything else.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_whitelist(None, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Allowlist Modified"),
            description=_("Added `{whitelisted}` to the allowlist.").format(whitelisted=keyword),
        )

    @command_audioset_global_whitelist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_global_whitelist_list(self, ctx: commands.Context):
        """List all keywords added to the allowlist."""
        whitelist = await self.config_cache.blacklist_whitelist.get_context_whitelist(None)

        if not whitelist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the allowlist."))
        whitelist = sorted(whitelist)
        text = ""
        total = len(whitelist)
        pages = []
        for i, entry in enumerate(whitelist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = list(
            discord.Embed(title=_("Global Allowlist"), description=page, colour=embed_colour)
            for page in pages
        )
        await dpymenu(ctx, pages)

    @command_audioset_global_whitelist.command(name="clear", aliases=["reset"])
    async def command_audioset_global_whitelist_clear(self, ctx: commands.Context):
        """Clear all keywords from the allowlist."""
        whitelist = await self.config_cache.blacklist_whitelist.get_whitelist(None)
        if not whitelist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the allowlist."))
        await self.config_cache.blacklist_whitelist.clear_whitelist()
        return await self.send_embed_msg(
            ctx,
            title=_("Allowlist Modified"),
            description=_("All entries have been removed from the allowlist."),
        )

    @command_audioset_global_whitelist.command(name="delete", aliases=["del", "remove"])
    async def command_audioset_global_whitelist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the allowlist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_whitelist(None, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Allowlist Modified"),
            description=_("Removed `{whitelisted}` from the allowlist.").format(
                whitelisted=keyword
            ),
        )

    @command_audioset_global.group(
        name="denylist", aliases=["blacklist", "disallowlist", "blocklist"]
    )
    async def command_audioset_global_blacklist(self, ctx: commands.Context):
        """Manages the global keyword denylist."""

    @command_audioset_global_blacklist.command(name="add")
    async def command_audioset_global_blacklist_add(self, ctx: commands.Context, *, keyword: str):
        """Adds a keyword to the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_blacklist(None, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Denylist Modified"),
            description=_("Added `{blacklisted}` to the denylist.").format(blacklisted=keyword),
        )

    @command_audioset_global_blacklist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_global_blacklist_list(self, ctx: commands.Context):
        """List all keywords added to the denylist."""
        blacklist = await self.config_cache.blacklist_whitelist.get_context_blacklist(None)
        if not blacklist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the denylist."))
        blacklist = sorted(blacklist)
        text = ""
        total = len(blacklist)
        pages = []
        for i, entry in enumerate(blacklist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = list(
            discord.Embed(title=_("Global Denylist"), description=page, colour=embed_colour)
            for page in pages
        )
        await dpymenu(ctx, pages)

    @command_audioset_global_blacklist.command(name="clear", aliases=["reset"])
    async def command_audioset_global_blacklist_clear(self, ctx: commands.Context):
        """Clear all keywords added to the denylist."""
        blacklist = await self.config_cache.blacklist_whitelist.get_blacklist(None)
        if not blacklist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the denylist."))
        await self.config_cache.blacklist_whitelist.clear_blacklist(None)
        return await self.send_embed_msg(
            ctx,
            title=_("Denylist Modified"),
            description=_("All entries have been removed from the denylist."),
        )

    @command_audioset_global_blacklist.command(name="delete", aliases=["del", "remove"])
    async def command_audioset_global_blacklist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_blacklist(None, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Denylist Modified"),
            description=_("Removed `{blacklisted}` from the denylist.").format(
                blacklisted=keyword
            ),
        )

    @command_audioset_global.command(name="restrict")
    async def command_audioset_global_restrict(self, ctx: commands.Context):
        """Toggle the domain restriction on Audio.

        When toggled off, users will be able to play songs from non-commercial websites and links.
        When toggled on, users are restricted to YouTube, SoundCloud, Vimeo, Twitch, and Bandcamp links.
        """
        restrict = await self.config_cache.url_restrict.get_global()
        await self.config_cache.url_restrict.set_global(not restrict)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Commercial links only globally: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not restrict else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="status")
    async def command_audioset_global_status(self, ctx: commands.Context):
        """Enable/disable tracks' titles as status."""
        status = await self.config_cache.status.get_global()
        await self.config_cache.status.set_global(not status)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Song titles as status: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not status else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="cache")
    async def command_audioset_global_cache(self, ctx: commands.Context, *, level: int = None):
        """Sets the caching level.

        Level can be one of the following:

        0: Disables all caching
        1: Enables Spotify Cache
        2: Enables YouTube Cache
        3: Enables Lavalink Cache
        5: Enables all Caches

        If you wish to disable a specific cache use a negative number.
        """
        current_level = await self.config_cache.local_cache_level.get_global()
        spotify_cache = CacheLevel.set_spotify()
        youtube_cache = CacheLevel.set_youtube()
        lavalink_cache = CacheLevel.set_lavalink()
        has_spotify_cache = current_level.is_superset(spotify_cache)
        has_youtube_cache = current_level.is_superset(youtube_cache)
        has_lavalink_cache = current_level.is_superset(lavalink_cache)

        if level is None:
            msg = (
                _("Max age:          [{max_age}]\n")
                + _("Spotify cache:    [{spotify_status}]\n")
                + _("Youtube cache:    [{youtube_status}]\n")
                + _("Lavalink cache:   [{lavalink_status}]\n")
            ).format(
                max_age=str(await self.config_cache.local_cache_age.get_global())
                + " "
                + _("days"),
                spotify_status=ENABLED_TITLE if has_spotify_cache else DISABLED_TITLE,
                youtube_status=ENABLED_TITLE if has_youtube_cache else DISABLED_TITLE,
                lavalink_status=ENABLED_TITLE if has_lavalink_cache else DISABLED_TITLE,
            )
            await self.send_embed_msg(
                ctx, title=_("Cache Settings"), description=box(msg, lang="ini")
            )
            return await ctx.send_help()
        if level not in [5, 3, 2, 1, 0, -1, -2, -3]:
            return await ctx.send_help()

        removing = level < 0

        if level == 5:
            newcache = CacheLevel.all()
        elif level == 0:
            newcache = CacheLevel.none()
        elif level in [-3, 3]:
            if removing:
                newcache = current_level - lavalink_cache
            else:
                newcache = current_level + lavalink_cache
        elif level in [-2, 2]:
            if removing:
                newcache = current_level - youtube_cache
            else:
                newcache = current_level + youtube_cache
        elif level in [-1, 1]:
            if removing:
                newcache = current_level - spotify_cache
            else:
                newcache = current_level + spotify_cache
        else:
            return await ctx.send_help()

        has_spotify_cache = newcache.is_superset(spotify_cache)
        has_youtube_cache = newcache.is_superset(youtube_cache)
        has_lavalink_cache = newcache.is_superset(lavalink_cache)
        msg = (
            _("Max age:          [{max_age}]\n")
            + _("Spotify cache:    [{spotify_status}]\n")
            + _("Youtube cache:    [{youtube_status}]\n")
            + _("Lavalink cache:   [{lavalink_status}]\n")
        ).format(
            max_age=str(await self.config_cache.local_cache_age.get_global()) + " " + _("days"),
            spotify_status=ENABLED_TITLE if has_spotify_cache else DISABLED_TITLE,
            youtube_status=ENABLED_TITLE if has_youtube_cache else DISABLED_TITLE,
            lavalink_status=ENABLED_TITLE if has_lavalink_cache else DISABLED_TITLE,
        )

        await self.send_embed_msg(ctx, title=_("Cache Settings"), description=box(msg, lang="ini"))
        await self.config_cache.local_cache_level.set_global(newcache.value)

    @command_audioset_global.command(name="cacheage")
    async def command_audioset_cacheage(self, ctx: commands.Context, age: int):
        """Sets the cache max age.

        This commands allows you to set the max number of days before an entry in the cache becomes
        invalid.
        """
        msg = ""
        if age < 7:
            msg = _(
                "Cache age cannot be less than 7 days. If you wish to disable it run "
                "{prefix}audioset cache.\n"
            ).format(prefix=ctx.prefix)
            age = 7
        msg += _("I've set the cache age to {age} days").format(age=age)
        await self.config_cache.local_cache_age.set_global(age)
        await self.send_embed_msg(ctx, title=_("Setting Changed"), description=msg)

    @command_audioset_global.group(name="globalapi")
    async def command_audioset_global_globalapi(self, ctx: commands.Context):
        """Change globalapi settings."""

    @command_audioset_global_globalapi.command(name="toggle")
    async def command_audioset_global_globalapi_toggle(self, ctx: commands.Context):
        """Toggle the server settings.

        Default is ON
        """
        state = await self.config_cache.global_api.get_context_value(ctx.guild)
        await self.config_cache.global_api.set_global(not state)
        if not state:  # Ensure a call is made if the API is enabled to update user perms
            self.global_api_user = await self.api_interface.global_cache_api.get_perms()

        msg = _("Global DB is {status}").format(status=ENABLED if not state else DISABLED)
        await self.send_embed_msg(ctx, title=_("Setting Changed"), description=msg)

    @command_audioset_global_globalapi.command(name="timeout")
    async def command_audioset_global_globalapi_timeout(
        self, ctx: commands.Context, timeout: Union[float, int]
    ):
        """Set GET request timeout.

        Example: 0.1 = 100ms 1 = 1 second
        """

        await self.config_cache.global_api_timeout.set_global(timeout)
        await ctx.send(_("Request timeout set to {time} second(s)").format(time=timeout))

    @command_audioset_global.command(name="historicalqueue")
    async def command_audioset_global_historical_queue(self, ctx: commands.Context):
        """Toggle global daily queues.

        Global daily queues creates a playlist for all tracks played today across all servers.
        """
        daily_playlists = await self.config_cache.daily_global_playlist.get_global()
        await self.config_cache.daily_global_playlist.set_global(not daily_playlists)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Global historical queues: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not daily_playlists else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="info", aliases=["settings"])
    async def command_audioset_global_info(self, ctx: commands.Context):
        """Display global settings."""
        current_level = await self.config_cache.local_cache_level.get_global()
        spotify_cache = CacheLevel.set_spotify()
        youtube_cache = CacheLevel.set_youtube()
        lavalink_cache = CacheLevel.set_lavalink()
        has_spotify_cache = current_level.is_superset(spotify_cache)
        has_youtube_cache = current_level.is_superset(youtube_cache)
        has_lavalink_cache = current_level.is_superset(lavalink_cache)
        global_api_enabled = await self.config_cache.global_api.get_global()
        global_api_get_timeout = await self.config_cache.global_api_timeout.get_global()
        empty_dc_enabled = await self.config_cache.empty_dc.get_global()
        empty_dc_timer = await self.config_cache.empty_dc_timer.get_global()
        empty_pause_enabled = await self.config_cache.empty_pause.get_global()
        empty_pause_timer = await self.config_cache.empty_pause_timer.get_global()
        jukebox = await self.config_cache.jukebox.get_global()
        jukebox_price = await self.config_cache.jukebox_price.get_global()
        disconnect = await self.config_cache.disconnect.get_global()
        maxlength = await self.config_cache.max_track_length.get_global()
        song_status = await self.config_cache.status.get_global()
        persist_queue = await self.config_cache.persistent_queue.get_global()
        auto_deafen = await self.config_cache.auto_deafen.get_global()
        lyrics = await self.config_cache.prefer_lyrics.get_global()
        restrict = await self.config_cache.url_restrict.get_global()
        volume = await self.config_cache.volume.get_global()
        thumbnail = await self.config_cache.thumbnail.get_global()
        max_queue = await self.config_cache.max_queue_size.get_global()
        country_code = await self.config_cache.country_code.get_global()
        historical_playlist = await self.config_cache.daily_global_playlist.get_global()
        disabled = DISABLED_TITLE
        enabled = ENABLED_TITLE

        msg = "----" + _("Global Settings") + "----        \n"

        msg += _(
            "Songs as status:              [{status}]\n"
            "Historical playlist:          [{historical_playlist}]\n"
            "Default persist queue:        [{persist_queue}]\n"
            "Default Spotify search:       [{countrycode}]\n"
        ).format(
            status=enabled if song_status else disabled,
            countrycode=country_code,
            historical_playlist=enabled if historical_playlist else disabled,
            persist_queue=enabled if persist_queue else disabled,
        )

        over_notify = await self.config_cache.notify.get_global()
        over_daily_playlist = await self.config_cache.daily_playlist.get_global()
        msg += (
            "\n---"
            + _("Global Rules")
            + "---        \n"
            + _(
                "Allow notify messages:        [{notify}]\n"
                "Allow daily playlist:         [{daily_playlist}]\n"
                "Enforced auto-disconnect:     [{dc}]\n"
                "Enforced empty dc:            [{empty_dc_enabled}]\n"
                "Empty dc timer:               [{dc_num_seconds}]\n"
                "Enforced empty pause:         [{empty_pause_enabled}]\n"
                "Empty pause timer:            [{pause_num_seconds}]\n"
                "Enforced jukebox:             [{jukebox}]\n"
                "Command price:                [{jukebox_price}]\n"
                "Enforced max queue length:    [{max_queue}]\n"
                "Enforced max track length:    [{tracklength}]\n"
                "Enforced auto-deafen:         [{auto_deafen}]\n"
                "Enforced thumbnails:          [{thumbnail}]\n"
                "Enforced maximum volume:      [{volume}%]\n"
                "Enforced URL restrict:        [{restrict}]\n"
                "Enforced prefer lyrics:       [{lyrics}]\n"
            )
        ).format(
            notify=over_notify,
            daily_playlist=over_daily_playlist,
            dc=enabled if disconnect else disabled,
            dc_num_seconds=self.get_time_string(empty_dc_timer),
            empty_pause_enabled=enabled if empty_pause_enabled else disabled,
            empty_dc_enabled=enabled if empty_dc_enabled else disabled,
            pause_num_seconds=self.get_time_string(empty_pause_timer),
            jukebox=enabled if jukebox else disabled,
            jukebox_price=humanize_number(jukebox_price),
            tracklength=self.get_time_string(maxlength),
            volume=volume,
            restrict=enabled if restrict else disabled,
            auto_deafen=enabled if auto_deafen else disabled,
            thumbnail=enabled if thumbnail else disabled,
            max_queue=humanize_number(max_queue),
            lyrics=enabled if lyrics else disabled,
        )

        msg += (
            "\n---"
            + _("Cache Settings")
            + "---        \n"
            + _("Max age:                [{max_age}]\n")
            + _("Local Spotify cache:    [{spotify_status}]\n")
            + _("Local Youtube cache:    [{youtube_status}]\n")
            + _("Local Lavalink cache:   [{lavalink_status}]\n")
            + _("Global cache status:    [{global_cache}]\n")
            + _("Global timeout:         [{num_seconds}]\n")
        ).format(
            max_age=str(await self.config_cache.local_cache_age.get_global()) + " " + _("days"),
            spotify_status=ENABLED_TITLE if has_spotify_cache else DISABLED_TITLE,
            youtube_status=ENABLED_TITLE if has_youtube_cache else DISABLED_TITLE,
            lavalink_status=ENABLED_TITLE if has_lavalink_cache else DISABLED_TITLE,
            global_cache=ENABLED_TITLE if global_api_enabled else DISABLED_TITLE,
            num_seconds=self.get_time_string(global_api_get_timeout),
        )

        await self.send_embed_msg(ctx, description=box(msg, lang="ini"))

    # --------------------------- CHANNEL COMMANDS ----------------------------

    @command_audioset.group(name="channel")
    @commands.guild_only()
    async def command_audioset_channel(self, ctx: commands.Context):
        """Channel configuration options."""

    @command_audioset_channel.command(name="volume")
    async def command_audioset_channel_volume(
        self, ctx: commands.Context, channel: discord.VoiceChannel, volume: int
    ):
        """Set the maximum allowed volume to be set on the specified channel."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if dj_enabled and not can_skip and not await self._has_dj_role(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Change Volume"),
                description=_("You need the DJ role to change the volume."),
            )
        global_value, guild_value, __ = await self.config_cache.volume.get_context_max(ctx.guild)
        max_value = min(global_value, guild_value)
        if not 10 < volume <= max_value:
            await self.send_embed_msg(
                ctx,
                title=_("Invalid Setting"),
                description=_("Maximum allowed volume has to be between 10% and {cap}%.").format(
                    cap=max_value
                ),
            )
            return
        await self.config_cache.volume.set_channel(channel, volume)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Maximum allowed volume set to: {volume}%.").format(volume=volume),
        )

    @command_audioset_channel.command(name="info", aliases=["settings", "config"])
    async def command_audioset_channel_settings(
        self, ctx: commands.Context, channel: discord.VoiceChannel
    ):
        """Show the settings for the specified channel."""

        volume = await self.config_cache.volume.get_channel(channel)
        msg = (
            "----"
            + _("Channel Settings")
            + "----        \nVolume:   [{vol}%]\n".format(
                vol=volume,
            )
        )
        await self.send_embed_msg(ctx, description=box(msg, lang="ini"))

    # --------------------------- SERVER COMMANDS ----------------------------

    @command_audioset.group(name="server", aliases=["guild"])
    @commands.guild_only()
    async def command_audioset_guild(self, ctx: commands.Context):
        """Server configuration options."""

    @command_audioset_guild.group(name="allowlist", aliases=["whitelist"])
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_whitelist(self, ctx: commands.Context):
        """Manages the keyword allowlist."""

    @command_audioset_guild_whitelist.command(name="add")
    async def command_audioset_guild_whitelist_add(self, ctx: commands.Context, *, keyword: str):
        """Adds a keyword to the allowlist.

        If anything is added to allowlist, it will reject everything else.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_whitelist(ctx.guild, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Allowlist Modified"),
            description=_("Added `{whitelisted}` to the allowlist.").format(whitelisted=keyword),
        )

    @command_audioset_guild_whitelist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_guild_whitelist_list(self, ctx: commands.Context):
        """List all keywords added to the allowlist."""
        whitelist = await self.config_cache.blacklist_whitelist.get_context_whitelist(
            ctx.guild, printable=True
        )
        if not whitelist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the allowlist."))
        whitelist = sorted(whitelist)
        text = ""
        total = len(whitelist)
        pages = []
        for i, entry in enumerate(whitelist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = list(
            discord.Embed(title=_("Allowlist"), description=page, colour=embed_colour)
            for page in pages
        )
        await dpymenu(ctx, pages)

    @command_audioset_guild_whitelist.command(name="clear", aliases=["reset"])
    async def command_audioset_guild_whitelist_clear(self, ctx: commands.Context):
        """Clear all keywords from the allowlist."""
        whitelist = await self.config_cache.blacklist_whitelist.get_whitelist(ctx.guild)
        if not whitelist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the allowlist."))
        await self.config_cache.blacklist_whitelist.clear_whitelist(ctx.guild)
        return await self.send_embed_msg(
            ctx,
            title=_("Allowlist Modified"),
            description=_("All entries have been removed from the allowlist."),
        )

    @command_audioset_guild_whitelist.command(name="delete", aliases=["del", "remove"])
    async def command_audioset_guild_whitelist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the allowlist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_whitelist(ctx.guild, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Allowlist Modified"),
            description=_("Removed `{whitelisted}` from the allowlist.").format(
                whitelisted=keyword
            ),
        )

    @command_audioset_guild.group(
        name="denylist", aliases=["blacklist", "disallowlist", "blocklist"]
    )
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_blacklist(self, ctx: commands.Context):
        """Manages the keyword denylist."""

    @command_audioset_guild_blacklist.command(name="add")
    async def command_audioset_guild_blacklist_add(self, ctx: commands.Context, *, keyword: str):
        """Adds a keyword to the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_blacklist(ctx.guild, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Denylist Modified"),
            description=_("Added `{blacklisted}` to the denylist.").format(blacklisted=keyword),
        )

    @command_audioset_guild_blacklist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_guild_blacklist_list(self, ctx: commands.Context):
        """List all keywords added to the denylist."""
        blacklist = await self.config_cache.blacklist_whitelist.get_context_blacklist(
            ctx.guild, printable=True
        )
        if not blacklist:
            return await self.send_embed_msg(ctx, title=_("Nothing in the denylist."))
        blacklist = sorted(blacklist)
        text = ""
        total = len(blacklist)
        pages = []
        for i, entry in enumerate(blacklist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = list(
            discord.Embed(title=_("Denylist"), description=page, colour=embed_colour)
            for page in pages
        )
        await dpymenu(ctx, pages)

    @command_audioset_guild_blacklist.command(name="clear", aliases=["reset"])
    async def command_audioset_guild_blacklist_clear(self, ctx: commands.Context):
        """Clear all keywords added to the denylist."""
        await self.config_cache.blacklist_whitelist.clear_blacklist(ctx.guild)
        return await self.send_embed_msg(
            ctx,
            title=_("Denylist Modified"),
            description=_("All entries have been removed from the denylist."),
        )

    @command_audioset_guild_blacklist.command(name="delete", aliases=["del", "remove"])
    async def command_audioset_guild_blacklist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_blacklist(ctx.guild, {keyword})
        return await self.send_embed_msg(
            ctx,
            title=_("Denylist Modified"),
            description=_("Removed `{blacklisted}` from the denylist.").format(
                blacklisted=keyword
            ),
        )

    @command_audioset_guild.command(name="volume")
    async def command_audioset_guild_volume(self, ctx: commands.Context, volume: int):
        """Set the maximum allowed volume to be set."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if dj_enabled and not can_skip and not await self._has_dj_role(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Change Volume"),
                description=_("You need the DJ role to change the volume."),
            )

        global_value, __, __ = await self.config_cache.volume.get_context_max(ctx.guild)
        if not 10 < volume <= global_value:
            await self.send_embed_msg(
                ctx,
                title=_("Invalid Setting"),
                description=_("Maximum allowed volume has to be between 10% and {cap}%.").format(
                    cap=global_value
                ),
            )
            return
        await self.config_cache.volume.set_guild(ctx.guild, volume)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Maximum allowed volume set to: {volume}%.").format(volume=volume),
        )

    @command_audioset_guild.command(name="maxqueue")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_maxqueue(self, ctx: commands.Context, size: int):
        """Set the maximum size a queue is allowed to be.

        Set to -1 to use the maximum value allowed by the bot.
        """
        global_value = await self.config_cache.max_queue_size.get_global()

        if not 10 < size < global_value:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Queue Size"),
                description=_("Queue size must bet between 10 and {cap}.").format(
                    cap=humanize_number(global_value)
                ),
            )
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Maximum queue size allowed is now {size}.").format(
                size=humanize_number(size)
            ),
        )
        if size < 0:
            size = None
        await self.config_cache.max_queue_size.set_guild(ctx.guild, size)

    @command_audioset_guild.command(name="dailyqueue")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_daily_queue(self, ctx: commands.Context):
        """Toggle daily queues.

        Daily queues creates a playlist for all tracks played today.
        """

        if await self.config_cache.daily_playlist.get_global() is False:
            await self.config_cache.daily_playlist.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Daily queues: {true_or_false}, "
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=DISABLED_TITLE),
            )

        daily_playlists = await self.config_cache.daily_playlist.get_guild(ctx.guild)
        await self.config_cache.daily_playlist.set_guild(ctx.guild, not daily_playlists)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Daily queues: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not daily_playlists else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="disconnect", aliases=["dc"])
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_dc(self, ctx: commands.Context):
        """Toggle the bot auto-disconnecting when done playing.

        This setting takes precedence over `[p]audioset emptydisconnect`.
        """

        if await self.config_cache.disconnect.get_global() is True:
            await self.config_cache.disconnect.set_guild(ctx.guild, True)
            await self.config_cache.autoplay.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Auto-disconnection at queue end: {true_or_false}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )

        disconnect = await self.config_cache.disconnect.get_guild(ctx.guild)
        autoplay = await self.config_cache.autoplay.get_guild(ctx.guild)
        msg = ""
        msg += _("Auto-disconnection at queue end: {true_or_false}.").format(
            true_or_false=ENABLED_TITLE if not disconnect else DISABLED_TITLE
        )
        if disconnect is not True and autoplay is True:
            msg += _("\nAuto-play has been disabled.")
            await self.config_cache.autoplay.set_guild(ctx.guild, False)

        await self.config_cache.disconnect.set_guild(ctx.guild, not disconnect)

        await self.send_embed_msg(ctx, title=_("Setting Changed"), description=msg)

    @command_audioset_guild.command(name="dj")
    @commands.admin_or_permissions(manage_roles=True)
    async def command_audioset_guild_dj(self, ctx: commands.Context):
        """Toggle DJ mode.

        DJ mode allows users with the DJ role to use audio commands.
        """
        dj_role = await self.config_cache.dj_roles.get_guild(ctx.guild)
        if not dj_role:
            await self.send_embed_msg(
                ctx,
                title=_("Missing DJ Role"),
                description=_(
                    "Please set a role to use with DJ mode. Enter the role name or ID now."
                ),
            )

            try:
                pred = MessagePredicate.valid_role(ctx)
                await self.bot.wait_for("message", timeout=15.0, check=pred)
                await ctx.invoke(self.command_audioset_guild_role_create, role_name=pred.result)
            except asyncio.TimeoutError:
                return await self.send_embed_msg(
                    ctx, title=_("Response timed out, try again later.")
                )
        dj_enabled = await self.config_cache.dj_status.get_guild(ctx.guild)
        await self.config_cache.dj_status.set_guild(ctx.guild, not dj_enabled)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("DJ role: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not dj_enabled else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="emptydisconnect", aliases=["emptydc"])
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_emptydisconnect(self, ctx: commands.Context, seconds: int):
        """Auto-disconnect from channel when bot is alone in it for x seconds, 0 to disable.

        `[p]audioset dc` takes precedence over this setting.
        """

        if await self.config_cache.empty_dc.get_global() is True:
            await self.config_cache.empty_dc.set_guild(ctx.guild, True)
            seconds = await self.config_cache.empty_dc_timer.get_global()
            await self.config_cache.empty_dc_timer.set_guild(ctx.guild, seconds)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Empty disconnect: {true_or_false}\n"
                    "Empty disconnect timer set to: {time_to_auto_dc}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(
                    true_or_false=ENABLED_TITLE, time_to_auto_dc=self.get_time_string(seconds)
                ),
            )

        if seconds < 0:
            return await self.send_embed_msg(
                ctx, title=_("Invalid Time"), description=_("Seconds can't be less than zero.")
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Empty disconnect disabled.")
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Empty disconnect timer set to {num_seconds}.").format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_dc_timer.set_guild(ctx.guild, seconds)
        await self.config_cache.empty_dc.set_guild(ctx.guild, enabled)

    @command_audioset_guild.command(name="emptypause")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_emptypause(self, ctx: commands.Context, seconds: int):
        """Auto-pause after x seconds when room is empty, 0 to disable."""
        if await self.config_cache.empty_pause.get_global() is True:
            await self.config_cache.empty_pause.set_guild(ctx.guild, True)
            seconds = await self.config_cache.empty_pause_timer.get_global()
            await self.config_cache.empty_pause_timer.set_guild(ctx.guild, seconds)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Empty pause: {true_or_false}\n"
                    "Empty pause timer set to: {time_to_auto_dc}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(
                    true_or_false=ENABLED_TITLE, time_to_auto_dc=self.get_time_string(seconds)
                ),
            )

        if seconds < 0:
            return await self.send_embed_msg(
                ctx, title=_("Invalid Time"), description=_("Seconds can't be less than zero.")
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Empty pause disabled.")
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Empty pause timer set to {num_seconds}.").format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_pause_timer.set_guild(ctx.guild, seconds)
        await self.config_cache.empty_pause.set_guild(ctx.guild, enabled)

    @command_audioset_guild.command(name="lyrics")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_lyrics(self, ctx: commands.Context):
        """Prioritise tracks with lyrics."""

        if await self.config_cache.prefer_lyrics.get_global() is True:
            await self.config_cache.prefer_lyrics.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Prefer tracks with lyrics: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )

        prefer_lyrics = await self.config_cache.prefer_lyrics.get_guild(ctx.guild)
        await self.config_cache.prefer_lyrics.set_guild(ctx.guild, not prefer_lyrics)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Prefer tracks with lyrics: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not prefer_lyrics else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="jukebox")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_jukebox(self, ctx: commands.Context, price: int):
        """Set a price for queueing tracks for non-mods, 0 to disable."""
        if await self.config_cache.jukebox.get_global() is True and await bank.is_global():
            await self.config_cache.jukebox.set_guild(ctx.guild, True)
            jukebox_price = await self.config_cache.jukebox_price.get_global()
            await self.config_cache.jukebox_price.set_guild(ctx.guild, jukebox_price)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Jukebox Mode: {true_or_false}\n"
                    "Price per command: {cost} {currency}\n"
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(
                    true_or_false=ENABLED_TITLE,
                    cost=humanize_number(jukebox_price),
                    currency=await bank.get_currency_name(ctx.guild),
                ),
            )
        if price < 0:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Price"),
                description=_("Price can't be less than zero."),
            )
        elif price > 2 ** 63 - 1:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Price"),
                description=_("Price can't be greater or equal to than 2^63."),
            )
        elif price == 0:
            jukebox = False
            await self.send_embed_msg(
                ctx, title=_("Setting Changed"), description=_("Jukebox mode disabled.")
            )
        else:
            jukebox = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Jukebox mode enabled, command price set to {price} {currency}."
                ).format(
                    price=humanize_number(price), currency=await bank.get_currency_name(ctx.guild)
                ),
            )

        await self.config_cache.jukebox_price.set_guild(ctx.guild, price)
        await self.config_cache.jukebox.set_guild(ctx.guild, jukebox)

    @command_audioset_guild.group(name="djrole", aliases=["role"])
    @commands.admin_or_permissions(manage_roles=True)
    async def command_audioset_guild_role(self, ctx: commands.Context):
        """Add/Remove/Show DJ Role and members."""

    @command_audioset_guild_role.command(name="create", aliases=["add"])
    async def command_audioset_guild_role_create(
        self, ctx: commands.Context, *, role_name: discord.Role
    ):
        """Add a role from DJ mode allowlist.

        See roles with `[p]audioset role list`
        Remove roles with `[p]audioset role remove`
        See DJs with `[p]audioset role members`
        """
        await self.config_cache.dj_roles.add_guild(ctx.guild, {role_name})
        await self.send_embed_msg(
            ctx,
            title=_("Settings Changed"),
            description=_("Role added to DJ list: {role.name}.").format(role=role_name),
        )

    @command_audioset_guild_role.command(name="delete", aliases=["remove", "del"])
    async def command_audioset_guild_role_delete(
        self, ctx: commands.Context, *, role_name: discord.Role
    ):
        """Remove a role from DJ mode allowlist.

        Add roles with `[p]audioset role add`
        See roles with `[p]audioset role list`
        See DJs with `[p]audioset role members`
        """
        await self.config_cache.dj_roles.remove_guild(ctx.guild, {role_name})
        await self.send_embed_msg(
            ctx,
            title=_("Settings Changed"),
            description=_("Role removed from DJ list: {role.name}.").format(role=role_name),
        )

    @command_audioset_guild_role.command(name="list", aliases=["show"])
    async def command_audioset_guild_role_list(self, ctx: commands.Context):
        """Show all roles from DJ mode allowlist.

        Add roles with `[p]audioset role add`
        Remove roles with `[p]audioset role remove`
        See DJs with `[p]audioset role members`
        """
        roles = await self.config_cache.dj_roles.get_context_value(ctx.guild)
        roles = sorted(roles, key=attrgetter("position"), reverse=True)
        rolestring = "\n".join([r.name for r in roles])
        pages = pagify(rolestring, page_length=500)
        await ctx.send_interactive(pages, timeout=30)

    @command_audioset_guild_role.command(name="members")
    async def command_audioset_guild_role_members(self, ctx: commands.Context):
        """Show all users with DJ permission.

        Add roles with `[p]audioset role add`
        Remove roles with `[p]audioset role remove`
        See roles with `[p]audioset role list`
        """
        djs = await self.config_cache.dj_roles.get_allowed_members(ctx.guild)
        djs = sorted(djs, key=attrgetter("top_role.position", "display_name"), reverse=True)
        memberstring = "\n".join([r.display_name for r in djs])
        pages = pagify(memberstring, page_length=500)
        await ctx.send_interactive(pages, timeout=30)

    @command_audioset_guild.command(name="maxlength")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_maxlength(
        self, ctx: commands.Context, seconds: Union[int, str]
    ):
        """Max length of a track to queue in seconds, 0 to disable.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`). Invalid input will turn the max length setting off.
        """
        global_value = await self.config_cache.max_queue_size.get_global()
        if not isinstance(seconds, int):
            seconds = self.time_convert(seconds)
        if not 0 <= seconds <= global_value:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid length"),
                description=_("Length can't be less than zero or greater than {cap}.").format(
                    cap=self.get_time_string(global_value)
                ),
            )
        if seconds == 0:
            if global_value != 0:
                await self.send_embed_msg(
                    ctx, title=_("Setting Changed"), description=_("Track max length disabled.")
                )
            else:
                await self.send_embed_msg(
                    ctx,
                    title=_("Setting Not Changed"),
                    description=_(
                        "Track max length cannot be disabled as it is restricted by the bot owner."
                    ),
                )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Track max length set to {seconds}.").format(
                    seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.max_track_length.set_guild(ctx.guild, seconds)

    @command_audioset_guild.command(name="notify")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_notify(self, ctx: commands.Context):
        """Toggle track announcement and other bot messages."""
        if await self.config_cache.notify.get_global() is False:
            await self.config_cache.notify.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Notify mode: {true_or_false}, "
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=DISABLED_TITLE),
            )
        notify = await self.config_cache.notify.get_guild(ctx.guild)
        await self.config_cache.notify.set_guild(ctx.guild, not notify)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Notify mode: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not notify else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="autodeafen")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_auto_deafen(self, ctx: commands.Context):
        """Toggle whether the bot will be auto deafened upon joining the voice channel."""
        if await self.config_cache.auto_deafen.get_global() is True:
            await self.config_cache.auto_deafen.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Auto-deafen: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        auto_deafen = await self.config_cache.auto_deafen.get_guild(ctx.guild)
        await self.config_cache.auto_deafen.set_guild(ctx.guild, not auto_deafen)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Auto-deafen: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not auto_deafen else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="restrict")
    @commands.admin_or_permissions(manage_guild=True)
    async def command_audioset_guild_restrict(self, ctx: commands.Context):
        """Toggle the domain restriction on Audio.

        When toggled off, users will be able to play songs from non-commercial websites and links.
        When toggled on, users are restricted to YouTube, SoundCloud, Twitch, and Bandcamp links.
        """
        if await self.config_cache.url_restrict.get_global() is True:
            await self.config_cache.url_restrict.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Commercial links only: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        restrict = await self.config_cache.url_restrict.get_guild(ctx.guild)
        await self.config_cache.url_restrict.set_guild(ctx.guild, not restrict)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Commercial links only: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not restrict else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="thumbnail")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_thumbnail(self, ctx: commands.Context):
        """Toggle displaying a thumbnail on audio messages."""
        if await self.config_cache.thumbnail.get_global() is True:
            await self.config_cache.thumbnail.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Thumbnail display: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        thumbnail = await self.config_cache.thumbnail.get_guild(ctx.guild)
        await self.config_cache.thumbnail.set_guild(ctx.guild, not thumbnail)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Thumbnail display: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not thumbnail else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="vote")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_vote(self, ctx: commands.Context, percent: int):
        """Percentage needed for non-mods to skip tracks, 0 to disable."""
        if percent < 0:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid percentage"),
                description=_("Percentage can't be less than zero."),
            )
        elif percent > 100:
            percent = 100
        if percent == 0:
            enabled = False
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Voting disabled. All users can use queue management commands."),
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Vote percentage set to {percent}%.").format(percent=percent),
            )

        await self.config_cache.votes.set_guild(ctx.guild, enabled)
        await self.config_cache.votes_percentage.set_guild(ctx.guild, percent)

    @command_audioset_guild.command(name="countrycode")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_countrycode(self, ctx: commands.Context, country: str):
        """Set the country code for Spotify searches."""
        if len(country) != 2:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Country Code"),
                description=_(
                    "Please use an official [ISO 3166-1 alpha-2]"
                    "(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code."
                ),
            )
        country = country.upper()
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Country Code set to {country}.").format(country=country),
        )

        await self.config_cache.country_code.set_guild(ctx.guild, country)

    @command_audioset_guild.command(name="persistqueue")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_persist_queue(self, ctx: commands.Context):
        """Toggle persistent queues.

        Persistent queues allows the current queue to be restored when the queue closes.
        """
        persist_cache = await self.config_cache.persistent_queue.get_guild(ctx.guild)
        await self.config_cache.persistent_queue.set_guild(ctx.guild, not persist_cache)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Persisting queues: {true_or_false}.").format(
                true_or_false=ENABLED_TITLE if not persist_cache else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.group(name="autoplay")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_autoplay(self, ctx: commands.Context):
        """Change auto-play setting."""

    @command_audioset_guild_autoplay.command(name="toggle")
    async def command_audioset_guild_autoplay_toggle(self, ctx: commands.Context):
        """Toggle auto-play when there no songs in queue."""
        if await self.config_cache.disconnect.get_global() is True:
            await self.config_cache.disconnect.set_guild(ctx.guild, True)
            await self.config_cache.autoplay.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Auto-disconnection at queue end: {true_or_false}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )

        autoplay = await self.config_cache.autoplay.get_guild(ctx.guild)
        repeat = await self.config_cache.repeat.get_guild(ctx.guild)
        disconnect = await self.config_cache.disconnect.get_guild(ctx.guild)
        msg = _("Auto-play when queue ends: {true_or_false}.").format(
            true_or_false=ENABLED_TITLE if not autoplay else DISABLED_TITLE
        )
        await self.config_cache.autoplay.set_guild(ctx.guild, not autoplay)
        if autoplay is not True and repeat is True:
            msg += _("\nRepeat has been disabled.")
            await self.config_cache.repeat.set_guild(ctx.guild, False)
        if autoplay is not True and disconnect is True:
            msg += _("\nAuto-disconnecting at queue end has been disabled.")
            await self.config_cache.disconnect.set_guild(ctx.guild, False)

        await self.send_embed_msg(ctx, title=_("Setting Changed"), description=msg)
        if self._player_check(ctx):
            await self.set_player_settings(ctx)

    @command_audioset_guild_autoplay.command(name="playlist", usage="<playlist_name_OR_id> [args]")
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_guild_autoplay_playlist(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Set a playlist to auto-play songs from.

        **Usage**:
        ​ ​ ​ ​ `[p]audioset autoplay playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
            ​Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]audioset autoplay MyGuildPlaylist`
        ​ ​ ​ ​ `[p]audioset autoplay MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]audioset autoplay PersonalPlaylist --scope User --author Draper`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=discord.Embed.Empty
                if not await self.bot.is_owner(ctx.author)
                else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]

        scope, author, guild, specified_user = scope_data
        try:
            playlist, playlist_arg, scope = await self.get_playlist_match(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self.send_embed_msg(ctx, title=str(e))
        if playlist is None:
            return await self.send_embed_msg(
                ctx,
                title=_("No Playlist Found"),
                description=_("Could not match '{arg}' to a playlist").format(arg=playlist_arg),
            )
        try:
            tracks = playlist.tracks
            if not tracks:
                return await self.send_embed_msg(
                    ctx,
                    title=_("No Tracks Found"),
                    description=_("Playlist {name} has no tracks.").format(name=playlist.name),
                )
            playlist_data = dict(enabled=True, id=playlist.id, name=playlist.name, scope=scope)
            await self.config.guild(ctx.guild).autoplaylist.set(playlist_data)
        except RuntimeError:
            return await self.send_embed_msg(
                ctx,
                title=_("No Playlist Found"),
                description=_("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_arg, scope=self.humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self.send_embed_msg(
                ctx,
                title=_("Missing Arguments"),
                description=_("You need to specify the Guild ID for the guild to lookup."),
            )
        else:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Playlist {name} (`{id}`) [**{scope}**] will be used for autoplay."
                ).format(
                    name=playlist.name,
                    id=playlist.id,
                    scope=self.humanize_scope(
                        scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
                    ),
                ),
            )

    @command_audioset_guild_autoplay.command(name="reset")
    async def command_audioset_guild_autoplay_reset(self, ctx: commands.Context):
        """Resets auto-play to the default playlist."""
        playlist_data = dict(
            enabled=True,
            id=42069,
            name="Aikaterna's curated tracks",
            scope=PlaylistScope.GLOBAL.value,
        )

        await self.config.guild(ctx.guild).autoplaylist.set(playlist_data)
        return await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Set auto-play playlist to play recently played tracks."),
        )

    @command_audioset_guild.command(name="info", aliases=["settings"])
    async def command_audioset_guild_info(self, ctx: commands.Context):
        """Display server settings."""
        empty_dc_enabled = await self.config_cache.empty_dc.get_guild(ctx.guild)
        empty_dc_timer = await self.config_cache.empty_dc_timer.get_guild(ctx.guild)
        empty_pause_enabled = await self.config_cache.empty_pause.get_guild(ctx.guild)
        empty_pause_timer = await self.config_cache.empty_pause_timer.get_guild(ctx.guild)
        jukebox = await self.config_cache.jukebox.get_guild(ctx.guild)
        jukebox_price = await self.config_cache.jukebox_price.get_guild(ctx.guild)
        disconnect = await self.config_cache.disconnect.get_guild(ctx.guild)
        maxlength = await self.config_cache.max_track_length.get_guild(ctx.guild)
        persist_queue = await self.config_cache.persistent_queue.get_guild(ctx.guild)
        auto_deafen = await self.config_cache.auto_deafen.get_guild(ctx.guild)
        lyrics = await self.config_cache.prefer_lyrics.get_guild(ctx.guild)
        restrict = await self.config_cache.url_restrict.get_guild(ctx.guild)
        volume = await self.config_cache.volume.get_guild(ctx.guild)
        thumbnail = await self.config_cache.thumbnail.get_guild(ctx.guild)
        max_queue = await self.config_cache.max_queue_size.get_guild(ctx.guild)
        country_code = await self.config_cache.country_code.get_guild(ctx.guild)
        daily_playlist = await self.config_cache.daily_playlist.get_guild(ctx.guild)
        autoplay = await self.config_cache.autoplay.get_guild(ctx.guild)
        dj_roles = await self.config_cache.dj_roles.get_guild(ctx.guild)
        dj_enabled = await self.config_cache.dj_status.get_guild(ctx.guild)
        vote_mode = await self.config_cache.votes.get_guild(ctx.guild)
        vote_percentage = await self.config_cache.votes_percentage.get_guild(ctx.guild)
        notify = await self.config_cache.notify.get_guild(ctx.guild)
        bumpped_shuffle = await self.config_cache.shuffle_bumped.get_guild(ctx.guild)
        repeat = await self.config_cache.repeat.get_guild(ctx.guild)
        shuffle = await self.config_cache.shuffle.get_guild(ctx.guild)

        autoplaylist = await self.config.guild(ctx.guild).autoplaylist()

        disabled = DISABLED_TITLE
        enabled = ENABLED_TITLE

        msg = "----" + _("Server Settings") + "----        \n"
        msg += _(
            "DJ mode:             [{dj_mode}]\n"
            "DJ roles:            [{dj_roles}]\n"
            "Vote mode:           [{vote_enabled}]\n"
            "Vote percentage:     [{vote_percent}%]\n"
            "Auto-play:           [{autoplay}]\n"
            "Auto-disconnect:     [{dc}]\n"
            "Empty dc:            [{empty_dc_enabled}]\n"
            "Empty dc timer:      [{dc_num_seconds}]\n"
            "Empty pause:         [{empty_pause_enabled}]\n"
            "Empty pause timer:   [{pause_num_seconds}]\n"
            "Jukebox:             [{jukebox}]\n"
            "Command price:       [{jukebox_price}]\n"
            "Max track length:    [{tracklength}]\n"
            "Volume:              [{volume}%]\n"
            "URL restrict:        [{restrict}]\n"
            "Prefer lyrics:       [{lyrics}]\n"
            "Song notify msgs:    [{notify}]\n"
            "Persist queue:       [{persist_queue}]\n"
            "Spotify search:      [{countrycode}]\n"
            "Auto-deafen:         [{auto_deafen}]\n"
            "Thumbnails:          [{thumbnail}]\n"
            "Max queue length:    [{max_queue}]\n"
            "Historical playlist: [{historical_playlist}]\n"
            "Repeat:              [{repeat}]\n"
            "Shuffle:             [{shuffle}]\n"
            "Shuffle bumped:      [{bumpped_shuffle}]\n"
        ).format(
            dj_mode=enabled if dj_enabled else disabled,
            dj_roles=len(dj_roles),
            vote_percent=vote_percentage,
            vote_enabled=enabled if vote_mode else disabled,
            autoplay=enabled if autoplay else disabled,
            dc=enabled if disconnect else disabled,
            dc_num_seconds=self.get_time_string(empty_dc_timer),
            empty_pause_enabled=enabled if empty_pause_enabled else disabled,
            empty_dc_enabled=enabled if empty_dc_enabled else disabled,
            pause_num_seconds=self.get_time_string(empty_pause_timer),
            jukebox=jukebox,
            jukebox_price=humanize_number(jukebox_price),
            tracklength=self.get_time_string(maxlength),
            volume=volume,
            restrict=restrict,
            countrycode=country_code,
            persist_queue=persist_queue,
            auto_deafen=auto_deafen,
            thumbnail=enabled if thumbnail else disabled,
            notify=enabled if notify else disabled,
            max_queue=humanize_number(max_queue),
            historical_playlist=enabled if daily_playlist else disabled,
            lyrics=enabled if lyrics else disabled,
            repeat=enabled if repeat else disabled,
            shuffle=enabled if shuffle else disabled,
            bumpped_shuffle=enabled if bumpped_shuffle else disabled,
        )

        if autoplaylist["enabled"]:
            pname = autoplaylist["name"]
            pid = autoplaylist["id"]
            pscope = autoplaylist["scope"]
            if pscope == PlaylistScope.GUILD.value:
                pscope = _("Server")
            elif pscope == PlaylistScope.USER.value:
                pscope = _("User")
            else:
                pscope = _("Global")
            msg += (
                "\n---"
                + _("Auto-play Settings")
                + "---        \n"
                + _("Playlist name:    [{pname}]\n")
                + _("Playlist ID:      [{pid}]\n")
                + _("Playlist scope:   [{pscope}]\n")
            ).format(pname=pname, pid=pid, pscope=pscope)

        await self.send_embed_msg(ctx, description=box(msg, lang="ini"))

    # --------------------------- Lavalink COMMANDS ----------------------------

    @command_audioset.group(name="lavalink", aliases=["ll", "llset", "llsetup"])
    @commands.is_owner()
    async def command_audioset_lavalink(self, ctx: commands.Context):
        """Lavalink configuration options."""

    @command_audioset_lavalink.command(name="localpath")
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_lavalink_localpath(self, ctx: commands.Context, *, local_path=None):
        """Set the localtracks path if the Lavalink.jar is not run from the Audio data folder.

        Leave the path blank to reset the path to the default, the Audio data directory.
        """

        if not local_path:
            await self.config_cache.localpath.set_global(cog_data_path(raw_name="Audio"))
            self.local_folder_current_path = cog_data_path(raw_name="Audio")
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "The localtracks path location has been reset to {localpath}"
                ).format(localpath=str(cog_data_path(raw_name="Audio").absolute())),
            )

        info_msg = _(
            "This setting is only for bot owners to set a localtracks folder location "
            "In the example below, the full path for 'ParentDirectory' "
            "must be passed to this command.\n"
            "```\n"
            "ParentDirectory\n"
            "  |__ localtracks  (folder)\n"
            "  |     |__ Awesome Album Name  (folder)\n"
            "  |           |__01 Cool Song.mp3\n"
            "  |           |__02 Groovy Song.mp3\n"
            "```\n"
            "The folder path given to this command must contain the localtracks folder.\n"
            "**This folder and files need to be visible to the user where `"
            "Lavalink.jar` is being run from.**\n"
            "Use this command with no path given to reset it to the default, "
            "the Audio data directory for this bot.\n"
            "Do you want to continue to set the provided path for local tracks?"
        )
        info = await ctx.maybe_send_embed(info_msg)

        start_adding_reactions(info, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(info, ctx.author)
        await self.bot.wait_for("reaction_add", check=pred)

        if not pred.result:
            with contextlib.suppress(discord.HTTPException):
                await info.delete()
            return
        temp = LocalPath(local_path, self.local_folder_current_path, forced=True)
        if not temp.exists() or not temp.is_dir():
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Path"),
                description=_("{local_path} does not seem like a valid path.").format(
                    local_path=local_path
                ),
            )

        if not temp.localtrack_folder.exists():
            warn_msg = _(
                "`{localtracks}` does not exist. "
                "The path will still be saved, but please check the path and "
                "create a localtracks folder in `{localfolder}` before attempting "
                "to play local tracks."
            ).format(localfolder=temp.absolute(), localtracks=temp.localtrack_folder.absolute())
            await self.send_embed_msg(ctx, title=_("Invalid Environment"), description=warn_msg)
        local_path = str(temp.localtrack_folder.absolute())
        await self.config_cache.localpath.set_global(cog_data_path(raw_name="Audio"))
        self.local_folder_current_path = temp.localtrack_folder.absolute()
        return await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("The localtracks path location has been set to {localpath}").format(
                localpath=local_path
            ),
        )

    @command_audioset_lavalink.command(name="logs")
    @has_internal_server()
    async def command_audioset_lavalink_logs(self, ctx: commands.Context):
        """Sends the Lavalink server logs to your DMs."""
        datapath = cog_data_path(raw_name="Audio")
        logs = datapath / "logs" / "spring.log"
        zip_name = None
        try:
            try:
                if not (logs.exists() and logs.is_file()):
                    return await ctx.send(_("No logs found in your data folder."))
            except OSError:
                return await ctx.send(_("No logs found in your data folder."))

            def check(path):
                return os.path.getsize(str(path)) > (8388608 - 1000)

            if check(logs):
                zip_name = logs.with_suffix(".tar.gz")
                zip_name.unlink(missing_ok=True)
                with tarfile.open(zip_name, "w:gz") as tar:
                    tar.add(str(logs), arcname="spring.log", recursive=False)
                if check(zip_name):
                    await ctx.send(
                        _("Logs are too large, you can find them in {path}").format(
                            path=zip_name.absolute()
                        )
                    )
                    zip_name = None
                else:
                    await ctx.author.send(file=discord.File(str(zip_name)))
            else:
                await ctx.author.send(file=discord.File(str(logs)))
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you the logs."))
        finally:
            if zip_name is not None:
                zip_name.unlink(missing_ok=True)

    @command_audioset_lavalink.command(name="restart")
    async def command_audioset_lavalink_restart(self, ctx: commands.Context):
        """Restarts the lavalink connection."""
        async with ctx.typing():
            await lavalink.close(self.bot)
            if self.player_manager is not None:
                await self.player_manager.shutdown()

            self.lavalink_restart_connect()

            await self.send_embed_msg(
                ctx,
                title=_("Restarting Lavalink"),
                description=_("It can take a couple of minutes for Lavalink to fully start up."),
            )

    @command_audioset_lavalink.command(name="java")
    async def command_audioset_lavalink_java(
        self, ctx: commands.Context, *, java_path: str = None
    ):
        """Change your Java executable path

        Enter nothing to reset to default.
        """
        external = await self.config_cache.external_lavalink_server.get_context_value(ctx.guild)
        if external:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "You cannot changed the Java executable path of "
                    "external Lavalink instances from the Audio Cog."
                ),
            )
        if java_path is None:
            await self.config.java_exc_path.clear()
            await self.send_embed_msg(
                ctx,
                title=_("Java Executable Reset"),
                description=_("Audio will now use `java` to run your Lavalink.jar"),
            )
        else:
            exc = Path(java_path)
            exc_absolute = exc.absolute()
            if not exc.exists() or not exc.is_file():
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Environment"),
                    description=_("`{java_path}` is not a valid executable").format(
                        java_path=exc_absolute
                    ),
                )
            await self.config.java_exc_path.set(str(exc_absolute))
            await self.send_embed_msg(
                ctx,
                title=_("Java Executable Changed"),
                description=_("Audio will now use `{exc}` to run your Lavalink.jar").format(
                    exc=exc_absolute
                ),
            )
        try:
            if self.player_manager is not None:
                await self.player_manager.shutdown()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_(
                    "For it to take effect please reload Audio (`{prefix}reload audio`)."
                ).format(
                    prefix=ctx.prefix,
                ),
            )
        else:
            try:
                self.lavalink_restart_connect()
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title=_("Failed To Shutdown Lavalink"),
                    description=_("Please reload Audio (`{prefix}reload audio`).").format(
                        prefix=ctx.prefix
                    ),
                )

    @command_audioset_lavalink.command(name="external", aliases=["managed"])
    async def command_audioset_lavalink_external(self, ctx: commands.Context):
        """Toggle using external Lavalink servers."""
        external = await self.config_cache.external_lavalink_server.get_context_value(ctx.guild)
        await self.config_cache.external_lavalink_server.set_global(not external)

        if external:
            embed = discord.Embed(
                title=_("Setting Changed"),
                description=_("External Lavalink server: {true_or_false}.").format(
                    true_or_false=ENABLED_TITLE if not external else DISABLED_TITLE
                ),
            )
            await self.send_embed_msg(ctx, embed=embed)
        else:
            try:
                if self.player_manager is not None:
                    await self.player_manager.shutdown()
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title=_("Failed To Shutdown Lavalink"),
                    description=_(
                        "External Lavalink server: {true_or_false}\n"
                        "For it to take effect please reload "
                        "Audio (`{prefix}reload audio`)."
                    ).format(
                        true_or_false=ENABLED_TITLE if not external else DISABLED_TITLE,
                        prefix=ctx.prefix,
                    ),
                )
            else:
                await self.send_embed_msg(
                    ctx,
                    title=_("Setting Changed"),
                    description=_("External Lavalink server: {true_or_false}.").format(
                        true_or_false=ENABLED_TITLE if not external else DISABLED_TITLE
                    ),
                )
        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink.command(name="host")
    async def command_audioset_lavalink_host(self, ctx: commands.Context, host: str):
        """Set the Lavalink server host."""
        await self.config.host.set(host)
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Host set to {host}.").format(host=host),
            footer=footer,
        )
        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink.command(name="password")
    async def command_audioset_lavalink_password(self, ctx: commands.Context, password: str):
        """Set the Lavalink server password."""
        await self.config.password.set(str(password))
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Server password set to {password}.").format(password=password),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink.command(name="port")
    async def command_audioset_lavalink_port(self, ctx: commands.Context, ws_port: int):
        """Set the Lavalink websocket server port."""
        await self.config.ws_port.set(ws_port)
        footer = None
        if await self.update_external_status():
            footer = _("External Lavalink server set to True.")
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Websocket port set to {port}.").format(port=ws_port),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title=_("Failed To Shutdown Lavalink"),
                description=_("Please reload Audio (`{prefix}reload audio`).").format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink.command(name="info", aliases=["settings"])
    async def command_audioset_lavalink_info(self, ctx: commands.Context):
        """Display Lavalink settings."""
        configs = await self.config.all()
        use_external_lavalink_server = (
            await self.config_cache.external_lavalink_server.get_global()
        )
        local_path = await self.config_cache.localpath.get_global()
        host = configs["host"]
        password = configs["password"]
        rest_port = configs["rest_port"]
        ws_port = configs["ws_port"]
        msg = "----" + _("Connection Settings") + "----        \n"
        msg += _("Host:             [{host}]\n").format(host=host)
        msg += _("Port:          [{port}]\n").format(port=ws_port)
        if ws_port != rest_port and rest_port != 2333:
            msg += _("Rest Port:        [{port}]\n").format(port=rest_port)
        msg += _("Password:         [{password}]\n").format(password=password)

        msg += (
            "\n---"
            + _("Lavalink Settings")
            + "---        \n"
            + _("Cog version:            [{version}]\n")
            + _("Red-Lavalink:           [{lavalink_version}]\n")
            + _("External server:        [{use_external_lavalink}]\n")
        ).format(
            version=__version__,
            lavalink_version=lavalink.__version__,
            use_external_lavalink=ENABLED_TITLE
            if use_external_lavalink_server
            else DISABLED_TITLE,
        )
        if (
            not use_external_lavalink_server
            and self.player_manager
            and self.player_manager.ll_build
        ):
            msg += _(
                "Lavalink build:         [{llbuild}]\n"
                "Lavalink branch:        [{llbranch}]\n"
                "Release date:           [{build_time}]\n"
                "Lavaplayer version:     [{lavaplayer}]\n"
                "Java version:           [{jvm}]\n"
                "Java Executable:        [{jv_exec}]\n"
            ).format(
                build_time=self.player_manager.build_time,
                llbuild=self.player_manager.ll_build,
                llbranch=self.player_manager.ll_branch,
                lavaplayer=self.player_manager.lavaplayer,
                jvm=self.player_manager.jvm,
                jv_exec=self.player_manager.path,
            )
        msg += _("Localtracks path:       [{localpath}]\n").format(localpath=local_path)

        try:
            await self.send_embed_msg(ctx.author, description=box(msg, lang="ini"))
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you this info."))

    @command_audioset_lavalink.command(name="stats")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_audioset_lavalink_stats(self, ctx: commands.Context):
        """Show audio stats."""
        server_num = len(lavalink.active_players())
        total_num = len(lavalink.all_connected_players())

        msg = ""
        async for p in AsyncIter(lavalink.all_connected_players()):
            connect_dur = (
                self.get_time_string(
                    int(
                        (
                            datetime.datetime.now(datetime.timezone.utc) - p.connected_at
                        ).total_seconds()
                    )
                )
                or "0s"
            )
            try:
                if not p.current:
                    raise AttributeError
                current_title = await self.get_track_description(
                    p.current, self.local_folder_current_path
                )
                msg += f"{p.guild.name} [`{connect_dur}`]: {current_title}\n"
            except AttributeError:
                msg += "{} [`{}`]: **{}**\n".format(
                    p.guild.name, connect_dur, _("Nothing playing.")
                )

        if total_num == 0:
            return await self.send_embed_msg(ctx, title=_("Not connected anywhere."))
        servers_embed = []
        pages = 1
        for page in pagify(msg, delims=["\n"], page_length=1500):
            em = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playing in {num}/{total} servers:").format(
                    num=humanize_number(server_num), total=humanize_number(total_num)
                ),
                description=page,
            )
            em.set_footer(
                text=_("Page {}/{}").format(
                    humanize_number(pages), humanize_number((math.ceil(len(msg) / 1500)))
                )
            )
            pages += 1
            servers_embed.append(em)

        await dpymenu(ctx, servers_embed)

    @command_audioset_lavalink.group(name="disconnect", aliases=["dc", "kill"])
    async def command_audioset_lavalink_disconnect(self, ctx: commands.Context):
        """Disconnect players."""

    @command_audioset_lavalink_disconnect.command(name="all")
    async def command_audioset_lavalink_disconnect_all(self, ctx: commands.Context):
        """Disconnect all players."""
        for player in lavalink.all_players():
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(player.guild)
            await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title=_("Admin Action."),
            description=_("Successfully disconnected from all voice channels."),
        )

    @command_audioset_lavalink_disconnect.command(name="active")
    async def command_audioset_lavalink_disconnect_active(self, ctx: commands.Context):
        """Disconnect all active players."""
        active_players = [p for p in lavalink.all_connected_players() if p.current]

        for player in active_players:
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(player.guild)
            await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title=_("Admin Action."),
            description=_("Successfully disconnected from all active voice channels."),
        )

    @command_audioset_lavalink_disconnect.command(name="idle")
    async def command_audioset_lavalink_disconnect_idle(self, ctx: commands.Context):
        """Disconnect all idle players."""
        idle_players = [
            p for p in lavalink.all_connected_players() if not (p.is_playing or p.is_auto_playing)
        ]
        for player in idle_players:
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(player.guild)
            await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title=_("Admin Action."),
            description=_("Successfully disconnected from all idle voice channels."),
        )

    @command_audioset_lavalink_disconnect.command(name="specific", aliases=["this"])
    async def command_audioset_lavalink_disconnect_specific(
        self, ctx: commands.Context, guild: Union[discord.Guild, int]
    ):
        """Disconnect the specified player."""
        try:
            player = lavalink.get_player(guild if type(guild) == int else guild.id)
        except (KeyError, IndexError, AttributeError):
            return await self.send_embed_msg(
                ctx,
                title=_("Player Not Found."),
                description=_(
                    "The specified player was not found ensure to provide the correct server ID.."
                ),
            )
        await player.disconnect()
        await self.config_cache.autoplay.set_currently_in_guild(player.guild)
        await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title=_("Admin Action."),
            description=_("Successfully disconnected from the specified server."),
        )

    # --------------------------- USER COMMANDS ----------------------------
    @command_audioset.group(name="user", aliases=["self", "my", "mine"])
    async def command_audioset_user(self, ctx: commands.Context):
        """User configuration options."""

    @command_audioset_user.command(name="countrycode")
    async def command_audioset_user_countrycode(self, ctx: commands.Context, country: str):
        """Set the country code for Spotify searches."""
        if len(country) != 2:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Country Code"),
                description=_(
                    "Please use an official [ISO 3166-1 alpha-2]"
                    "(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code."
                ),
            )
        country = country.upper()
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Country Code set to {country}.").format(country=country),
        )

        await self.config_cache.country_code.set_user(ctx.author, country)

    @command_audioset_user.command(name="info", aliases=["settings", "config"])
    async def command_audioset_user_settings(self, ctx: commands.Context):
        """Show the settings for the user who runs it."""

        country_code = await self.config_cache.country_code.get_user(ctx.author)
        msg = (
            "----"
            + _("User Settings")
            + "----        \nSpotify search:   [{country_code}]\n".format(
                country_code=country_code if country_code else _("Not set"),
            )
        )
        await self.send_embed_msg(ctx, description=box(msg, lang="ini"))

    # --------------------------- GENERIC COMMANDS ----------------------------
    @command_audioset.command(name="info", aliases=["settings"])
    @commands.guild_only()
    async def command_audioset_settings(self, ctx: commands.Context):
        """Show the settings for the current context.

        This takes into consideration where the command is ran, if the music is playing on the current server and the user who run it.
        """
        dj_roles = await self.config_cache.dj_roles.get_context_value(ctx.guild)
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        emptydc_enabled = await self.config_cache.empty_dc.get_context_value(ctx.guild)
        emptydc_timer = await self.config_cache.empty_dc_timer.get_context_value(ctx.guild)
        emptypause_enabled = await self.config_cache.empty_pause.get_context_value(ctx.guild)
        emptypause_timer = await self.config_cache.empty_dc_timer.get_context_value(ctx.guild)
        jukebox = await self.config_cache.jukebox.get_context_value(ctx.guild)
        jukebox_price = await self.config_cache.jukebox_price.get_context_value(ctx.guild)
        thumbnail = await self.config_cache.thumbnail.get_context_value(ctx.guild)
        dc = await self.config_cache.disconnect.get_context_value(ctx.guild)
        autoplay = await self.config_cache.autoplay.get_context_value(
            ctx.guild, cache=self.config_cache
        )
        maxlength = await self.config_cache.max_track_length.get_context_value(ctx.guild)
        maxqueue = await self.config_cache.max_queue_size.get_context_value(ctx.guild)
        vote_percent = await self.config_cache.votes_percentage.get_context_value(ctx.guild)
        current_level = await self.config_cache.local_cache_level.get_context_value(ctx.guild)
        song_repeat = await self.config_cache.repeat.get_context_value(ctx.guild)
        song_shuffle = await self.config_cache.shuffle.get_context_value(ctx.guild)
        bumpped_shuffle = await self.config_cache.shuffle_bumped.get_context_value(ctx.guild)
        song_notify = await self.config_cache.notify.get_context_value(ctx.guild)
        persist_queue = await self.config_cache.persistent_queue.get_context_value(ctx.guild)
        auto_deafen = await self.config_cache.auto_deafen.get_context_value(ctx.guild)
        volume = await self.config_cache.volume.get_context_value(
            ctx.guild, channel=self.rgetattr(ctx, "guild.me.voice.channel", None)
        )
        countrycode = await self.config_cache.country_code.get_context_value(
            ctx.guild, user=ctx.author
        )
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_level)
        vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
        msg = "----" + _("Context Settings") + "----        \n"
        msg += _("Auto-disconnect:  [{dc}]\n").format(dc=ENABLED_TITLE if dc else DISABLED_TITLE)
        msg += _("Auto-play:        [{autoplay}]\n").format(
            autoplay=ENABLED_TITLE if autoplay else DISABLED_TITLE
        )
        if emptydc_enabled:
            msg += _("Disconnect timer: [{num_seconds}]\n").format(
                num_seconds=self.get_time_string(emptydc_timer)
            )
        if emptypause_enabled:
            msg += _("Auto Pause timer: [{num_seconds}]\n").format(
                num_seconds=self.get_time_string(emptypause_timer)
            )
        if dj_enabled and dj_roles:
            msg += _("DJ Roles:         [{number}]\n").format(number=len(dj_roles))
        if jukebox:
            msg += _("Jukebox:          [{jukebox_name}]\n").format(jukebox_name=jukebox)
            msg += _("Command price:    [{jukebox_price}]\n").format(
                jukebox_price=humanize_number(jukebox_price)
            )
        if maxlength > 0:
            msg += _("Max track length: [{length}]\n").format(
                length=self.get_time_string(maxlength)
            )
        if maxqueue > 0:
            msg += _("Max queue length: [{length}]\n").format(length=humanize_number(maxqueue))

        msg += _(
            "Repeat:           [{repeat}]\n"
            "Shuffle:          [{shuffle}]\n"
            "Shuffle bumped:   [{bumpped_shuffle}]\n"
            "Song notify msgs: [{notify}]\n"
            "Persist queue:    [{persist_queue}]\n"
            "Spotify search:   [{countrycode}]\n"
            "Auto-deafen:      [{auto_deafen}]\n"
            "Volume:           [{volume}%]\n"
        ).format(
            countrycode=countrycode,
            repeat=song_repeat,
            shuffle=song_shuffle,
            notify=song_notify,
            bumpped_shuffle=bumpped_shuffle,
            persist_queue=persist_queue,
            auto_deafen=auto_deafen,
            volume=volume,
        )
        if thumbnail:
            msg += _("Thumbnails:       [{0}]\n").format(
                ENABLED_TITLE if thumbnail else DISABLED_TITLE
            )
        if vote_percent > 0:
            msg += _(
                "Vote skip:        [{vote_enabled}]\n" "Vote percentage:  [{vote_percent}%]\n"
            ).format(
                vote_percent=vote_percent,
                vote_enabled=ENABLED_TITLE if vote_enabled else DISABLED_TITLE,
            )

        autoplaylist = await self.config.guild(ctx.guild).autoplaylist()
        if autoplay or autoplaylist["enabled"]:
            if autoplaylist["enabled"]:
                pname = autoplaylist["name"]
                pid = autoplaylist["id"]
                pscope = autoplaylist["scope"]
                if pscope == PlaylistScope.GUILD.value:
                    pscope = _("Server")
                elif pscope == PlaylistScope.USER.value:
                    pscope = _("User")
                else:
                    pscope = _("Global")
            elif cache_enabled:
                pname = _("Cached")
                pid = _("Cached")
                pscope = _("Cached")
            else:
                pname = _("US Top 100")
                pid = _("US Top 100")
                pscope = _("US Top 100")
            msg += (
                "\n---"
                + _("Auto-play Settings")
                + "---        \n"
                + _("Playlist name:    [{pname}]\n")
                + _("Playlist ID:      [{pid}]\n")
                + _("Playlist scope:   [{pscope}]\n")
            ).format(pname=pname, pid=pid, pscope=pscope)

        await self.send_embed_msg(ctx, description=box(msg, lang="ini"))

    # --------------------------- GENERIC COMMANDS ----------------------------

    @command_audioset.command(name="youtubeapi")
    @commands.is_owner()
    async def command_audioset_youtubeapi(self, ctx: commands.Context):
        """Instructions to set the YouTube API key."""
        message = _(
            f"1. Go to Google Developers Console and log in with your Google account.\n"
            "(https://console.developers.google.com/)\n"
            "2. You should be prompted to create a new project (name does not matter).\n"
            "3. Click on Enable APIs and Services at the top.\n"
            "4. In the list of APIs choose or search for YouTube Data API v3 and "
            "click on it. Choose Enable.\n"
            "5. Click on Credentials on the left navigation bar.\n"
            "6. Click on Create Credential at the top.\n"
            '7. At the top click the link for "API key".\n'
            "8. No application restrictions are needed. Click Create at the bottom.\n"
            "9. You now have a key to add to `{prefix}set api youtube api_key <your_api_key_here>`"
        ).format(prefix=ctx.prefix)
        await ctx.maybe_send_embed(message)

    @command_audioset.command(name="spotifyapi")
    @commands.is_owner()
    async def command_audioset_spotifyapi(self, ctx: commands.Context):
        """Instructions to set the Spotify API tokens."""
        message = _(
            "1. Go to Spotify developers and log in with your Spotify account.\n"
            "(https://developer.spotify.com/dashboard/applications)\n"
            '2. Click "Create An App".\n'
            "3. Fill out the form provided with your app name, etc.\n"
            '4. When asked if you\'re developing commercial integration select "No".\n'
            "5. Accept the terms and conditions.\n"
            "6. Copy your client ID and your client secret into:\n"
            "`{prefix}set api spotify client_id <your_client_id_here> "
            "client_secret <your_client_secret_here>`"
        ).format(prefix=ctx.prefix)
        await ctx.maybe_send_embed(message)
