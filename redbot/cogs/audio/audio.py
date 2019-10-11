# -*- coding: utf-8 -*-
import asyncio
import contextlib
import datetime
import heapq
import json
import logging
import os
import random
import re
import time
import traceback
from collections import namedtuple
from io import StringIO
from typing import List, Optional, Tuple, Union, cast

import aiohttp
import discord
import lavalink
import math
from fuzzywuzzy import process

import redbot.core
from redbot.core import Config, bank, checks, commands
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import bold, box, humanize_number, inline, pagify
from redbot.core.utils.menus import (
    DEFAULT_CONTROLS,
    close_menu,
    menu,
    next_page,
    prev_page,
    start_adding_reactions,
)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from . import dataclasses
from .apis import MusicCache, HAS_SQL
from .checks import can_have_caching
from .converters import ComplexScopeParser, ScopeParser, get_lazy_converter, get_playlist_converter
from .equalizer import Equalizer
from .errors import LavalinkDownloadFailed, MissingGuild, SpotifyFetchError, TooManyMatches
from .manager import ServerManager
from .playlists import (
    FakePlaylist,
    Playlist,
    PlaylistScope,
    create_playlist,
    delete_playlist,
    get_all_playlist,
    get_playlist,
    humanize_scope,
)
from .utils import *


_ = Translator("Audio", __file__)

__version__ = "1.0.0"
__author__ = ["aikaterna", "Draper"]

log = logging.getLogger("red.audio")

_SCHEMA_VERSION = 2
LazyGreedyConverter = get_lazy_converter("--")
PlaylistConverter = get_playlist_converter()


@cog_i18n(_)
class Audio(commands.Cog):
    """Play audio through voice channels."""

    _default_lavalink_settings = {
        "host": "localhost",
        "rest_port": 2333,
        "ws_port": 2333,
        "password": "youshallnotpass",
    }

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 2711759130, force_registration=True)
        self.skip_votes = {}
        self.session = aiohttp.ClientSession()
        self._connect_task = None
        self._disconnect_task = None
        self._cleaned_up = False
        self._connection_aborted = False
        self.play_lock = {}
        self._manager: Optional[ServerManager] = None
        self._cog_name = None
        self._cog_id = None
        default_global = dict(
            schema_version=1,
            cache_level=0,
            cache_age=365,
            status=False,
            use_external_lavalink=False,
            restrict=True,
            current_version=redbot.core.VersionInfo.from_str("3.0.0a0").to_json(),
            localpath=str(cog_data_path(raw_name="Audio")),
            **self._default_lavalink_settings,
        )

        default_guild = dict(
            auto_play=False,
            autoplaylist=dict(enabled=False, id=None, name=None, scope=None),
            disconnect=False,
            dj_enabled=False,
            dj_role=None,
            emptydc_enabled=False,
            emptydc_timer=0,
            emptypause_enabled=False,
            emptypause_timer=0,
            jukebox=False,
            jukebox_price=0,
            maxlength=0,
            notify=False,
            repeat=False,
            shuffle=False,
            thumbnail=False,
            volume=100,
            vote_enabled=False,
            vote_percent=0,
            room_lock=None,
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
        )
        _playlist = dict(id=None, author=None, name=None, playlist_url=None, tracks=[])
        self.config.init_custom("EQUALIZER", 1)
        self.config.register_custom("EQUALIZER", eq_bands=[], eq_presets={})
        self.config.init_custom(PlaylistScope.GLOBAL.value, 1)
        self.config.register_custom(PlaylistScope.GLOBAL.value, **_playlist)
        self.config.init_custom(PlaylistScope.GUILD.value, 2)
        self.config.register_custom(PlaylistScope.GUILD.value, **_playlist)
        self.config.init_custom(PlaylistScope.USER.value, 2)
        self.config.register_custom(PlaylistScope.USER.value, **_playlist)
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.music_cache = MusicCache(bot, self.session, path=str(cog_data_path(raw_name="Audio")))
        self.play_lock = {}

        self._manager: Optional[ServerManager] = None
        self.bot.dispatch("red_audio_initialized", self)

    @property
    def owns_autoplay(self):
        c = self.bot.get_cog(self._cog_name)
        if c and id(c) == self._cog_id:
            return c

    @owns_autoplay.setter
    def owns_autoplay(self, value: commands.Cog):
        if self.owns_autoplay:
            raise RuntimeError(
                f"`{self._cog_name}` already has ownership of autoplay, "
                f"please unload it if you wish to load `{value.qualified_name}`."
            )
        self._cog_name = value.qualified_name
        self._cog_id = id(value)

    @owns_autoplay.deleter
    def owns_autoplay(self):
        self._cog_name = None
        self._cog_id = None

    async def cog_before_invoke(self, ctx: commands.Context):
        if self.llsetup in [ctx.command, ctx.command.root_parent]:
            pass
        elif self._connect_task.cancelled():
            await ctx.send(
                "You have attempted to run Audio's Lavalink server on an unsupported"
                " architecture. Only settings related commands will be available."
            )
            raise RuntimeError(
                "Not running audio command due to invalid machine architecture for Lavalink."
            )
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            dj_role_obj = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
            if not dj_role_obj:
                await self.config.guild(ctx.guild).dj_enabled.set(None)
                await self.config.guild(ctx.guild).dj_role.set(None)
                await self._embed_msg(ctx, _("No DJ role found. Disabling DJ mode."))

    async def initialize(self):
        pass_config_to_dependencies(self.config, self.bot, await self.config.localpath())
        await self.music_cache.initialize(self.config)
        asyncio.ensure_future(
            self._migrate_config(
                from_version=await self.config.schema_version(), to_version=_SCHEMA_VERSION
            )
        )
        self._restart_connect()
        self._disconnect_task = self.bot.loop.create_task(self.disconnect_timer())
        lavalink.register_event_listener(self.event_handler)
        if not HAS_SQL:
            error_message = (
                "Audio version: {version}\nThis version requires SQL to "
                "access the caching features, "
                "your Python install is missing the module sqlite3.\n\n"
                "For instructions on how to fix it Google "
                "`ModuleNotFoundError: No module named '_sqlite3'`\n"
                "You will need to reinstall "
                "Python with SQL dependencies installed.\n\n"
            ).format(version=__version__)
            with contextlib.suppress(discord.HTTPException):
                await self.bot.send_to_owners(error_message)
            log.critical(error_message)

    async def _migrate_config(self, from_version: int, to_version: int):
        database_entries = []
        time_now = str(datetime.datetime.now(datetime.timezone.utc))
        if from_version == to_version:
            return
        elif from_version < to_version:
            all_guild_data = await self.config.all_guilds()
            all_playlist = {}
            for guild_id, guild_data in all_guild_data.items():
                temp_guild_playlist = guild_data.pop("playlists", None)
                if temp_guild_playlist:
                    guild_playlist = {}
                    for count, (name, data) in enumerate(temp_guild_playlist.items(), 1):
                        if not data or not name:
                            continue
                        playlist = {"id": count, "name": name, "guild": int(guild_id)}
                        playlist.update(data)
                        guild_playlist[str(count)] = playlist

                        tracks_in_playlist = data.get("tracks", []) or []
                        for t in tracks_in_playlist:
                            uri = t.get("info", {}).get("uri")
                            if uri:
                                t = {"loadType": "V2_COMPAT", "tracks": [t], "query": uri}
                                database_entries.append(
                                    {
                                        "query": uri,
                                        "data": json.dumps(t),
                                        "last_updated": time_now,
                                        "last_fetched": time_now,
                                    }
                                )
                    if guild_playlist:
                        all_playlist[str(guild_id)] = guild_playlist
            await self.config.custom(PlaylistScope.GUILD.value).set(all_playlist)
            # new schema is now in place
            await self.config.schema_version.set(_SCHEMA_VERSION)

            # migration done, now let's delete all the old stuff
            for guild_id in all_guild_data:
                await self.config.guild(
                    cast(discord.Guild, discord.Object(id=guild_id))
                ).clear_raw("playlists")
        if database_entries and HAS_SQL:
            asyncio.ensure_future(self.music_cache.insert("lavalink", database_entries))

    def _restart_connect(self):
        if self._connect_task:
            self._connect_task.cancel()

        self._connect_task = self.bot.loop.create_task(self.attempt_connect())

    async def attempt_connect(self, timeout: int = 50):
        self._connection_aborted = False
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            external = await self.config.use_external_lavalink()
            if external is False:
                settings = self._default_lavalink_settings
                host = settings["host"]
                password = settings["password"]
                rest_port = settings["rest_port"]
                ws_port = settings["ws_port"]
                if self._manager is not None:
                    await self._manager.shutdown()
                self._manager = ServerManager()
                try:
                    await self._manager.start()
                except LavalinkDownloadFailed as exc:
                    await asyncio.sleep(1)
                    if exc.should_retry:
                        log.exception(
                            "Exception whilst starting internal Lavalink server, retrying...",
                            exc_info=exc,
                        )
                        retry_count += 1
                        continue
                    else:
                        log.exception(
                            "Fatal exception whilst starting internal Lavalink server, "
                            "aborting...",
                            exc_info=exc,
                        )
                        self._connection_aborted = True
                        raise
                except asyncio.CancelledError:
                    log.exception("Invalid machine architecture, cannot run Lavalink.")
                    raise
                except Exception as exc:
                    log.exception(
                        "Unhandled exception whilst starting internal Lavalink server, "
                        "aborting...",
                        exc_info=exc,
                    )
                    self._connection_aborted = True
                    raise
                else:
                    break
            else:
                host = await self.config.host()
                password = await self.config.password()
                rest_port = await self.config.rest_port()
                ws_port = await self.config.ws_port()
                break
        else:
            log.critical(
                "Setting up the Lavalink server failed after multiple attempts. See above "
                "tracebacks for details."
            )
            self._connection_aborted = True
            return

        retry_count = 0
        while retry_count < max_retries:
            try:
                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    rest_port=rest_port,
                    ws_port=ws_port,
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                log.error("Connecting to Lavalink server timed out, retrying...")
                if external is False and self._manager is not None:
                    await self._manager.shutdown()
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink, aborting...", exc_info=exc
                )
                self._connection_aborted = True
                raise
            else:
                break
        else:
            self._connection_aborted = True
            log.critical(
                "Connecting to the Lavalink server failed after multiple attempts. See above "
                "tracebacks for details."
            )

    async def event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
    ):
        disconnect = await self.config.guild(player.channel.guild).disconnect()
        autoplay = await self.config.guild(player.channel.guild).auto_play() or self.owns_autoplay
        notify = await self.config.guild(player.channel.guild).notify()
        status = await self.config.status()
        repeat = await self.config.guild(player.channel.guild).repeat()

        async def _players_check():
            try:
                get_single_title = lavalink.active_players()[0].current.title
                if get_single_title == "Unknown title":
                    get_single_title = lavalink.active_players()[0].current.uri
                    if not get_single_title.startswith("http"):
                        get_single_title = get_single_title.rsplit("/", 1)[-1]
                elif any(
                    x in lavalink.active_players()[0].current.uri
                    for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                ):
                    get_single_title = "{} - {}".format(
                        lavalink.active_players()[0].current.author,
                        lavalink.active_players()[0].current.title,
                    )
                else:
                    get_single_title = lavalink.active_players()[0].current.title
                playing_servers = len(lavalink.active_players())
            except IndexError:
                get_single_title = None
                playing_servers = 0
            return get_single_title, playing_servers

        async def _status_check(playing_servers):
            if playing_servers == 0:
                await self.bot.change_presence(activity=None)
            if playing_servers == 1:
                single_title = await _players_check()
                await self.bot.change_presence(
                    activity=discord.Activity(
                        name=single_title[0], type=discord.ActivityType.listening
                    )
                )
            if playing_servers > 1:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        name=_("music in {} servers").format(playing_servers),
                        type=discord.ActivityType.playing,
                    )
                )

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            self.skip_votes[player.channel.guild] = []
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", player.current)
            player.store(
                "requester", player.current.requester if player.current else player.current
            )
            self.bot.dispatch(
                "red_audio_track_start",
                player.channel.guild,
                player.current,
                player.current.requester,
            )
        if event_type == lavalink.LavalinkEvents.TRACK_END:
            prev_song = player.fetch("prev_song")
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch(
                "red_audio_track_end", player.channel.guild, prev_song, prev_requester
            )

        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            prev_song = player.fetch("prev_song")
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch(
                "red_audio_queue_end", player.channel.guild, prev_song, prev_requester
            )
            if autoplay and not player.queue and player.fetch("playing_song") is not None:
                if self.owns_autoplay is None:
                    await self.music_cache.autoplay(player)
                else:
                    self.bot.dispatch(
                        "red_audio_should_auto_play",
                        player,
                        player.channel.guild,
                        player.channel,
                        self.play_query,
                    )

        if event_type == lavalink.LavalinkEvents.TRACK_START and notify:
            notify_channel = player.fetch("channel")
            prev_song = player.fetch("prev_song")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                if player.fetch("notify_message") is not None:
                    with contextlib.suppress(discord.HTTPException):
                        await player.fetch("notify_message").delete()

                if (
                    autoplay
                    and player.current.extras.get("autoplay")
                    and (prev_song is None or not prev_song.extras.get("autoplay"))
                ):
                    embed = discord.Embed(
                        colour=(await self.bot.get_embed_colour(notify_channel)),
                        title=_("Auto play started."),
                    )
                    await notify_channel.send(embed=embed)

                if (
                    any(
                        x in player.current.uri
                        for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                    )
                    if player.current
                    else False
                ):
                    if player.current.title != "Unknown title":
                        description = "**{} - {}**\n{}".format(
                            player.current.author,
                            player.current.title,
                            dataclasses.LocalPath(player.current.uri).to_string_hidden(),
                        )
                    else:
                        description = "{}".format(
                            dataclasses.LocalPath(player.current.uri).to_string_hidden()
                        )
                else:
                    description = "**[{}]({})**".format(player.current.title, player.current.uri)
                if player.current.is_stream:
                    dur = "LIVE"
                else:
                    dur = lavalink.utils.format_time(player.current.length)
                embed = discord.Embed(
                    colour=(await self.bot.get_embed_color(notify_channel)),
                    title=_("Now Playing"),
                    description=description,
                )
                embed.set_footer(
                    text=_("Track length: {length} | Requested by: {user}").format(
                        length=dur, user=player.current.requester
                    )
                )
                if (
                    await self.config.guild(player.channel.guild).thumbnail()
                    and player.current.thumbnail
                ):
                    embed.set_thumbnail(url=player.current.thumbnail)
                notify_message = await notify_channel.send(embed=embed)
                player.store("notify_message", notify_message)

        if event_type == lavalink.LavalinkEvents.TRACK_START and status:
            player_check = await _players_check()
            await _status_check(player_check[1])

        if event_type == lavalink.LavalinkEvents.TRACK_END and status:
            await asyncio.sleep(1)
            if not player.is_playing:
                player_check = await _players_check()
                await _status_check(player_check[1])

        if event_type == lavalink.LavalinkEvents.QUEUE_END and notify and not autoplay:
            notify_channel = player.fetch("channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                embed = discord.Embed(
                    colour=(await self.bot.get_embed_colour(notify_channel)),
                    title=_("Queue ended."),
                )
                await notify_channel.send(embed=embed)

        elif event_type == lavalink.LavalinkEvents.QUEUE_END and disconnect and not autoplay:
            self.bot.dispatch("red_audio_audio_disconnect", player.channel.guild)
            await player.disconnect()

        if event_type == lavalink.LavalinkEvents.QUEUE_END and status:
            player_check = await _players_check()
            await _status_check(player_check[1])

        if event_type == lavalink.LavalinkEvents.TRACK_EXCEPTION:
            message_channel = player.fetch("channel")
            if message_channel:
                message_channel = self.bot.get_channel(message_channel)
                if player.current and any(
                    x in player.current.uri
                    for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                ):
                    query = dataclasses.Query.process_input(player.current.uri)
                    if player.current.title == "Unknown title":
                        description = "{}".format(query.track.to_string_hidden())
                    else:
                        song = bold("{} - {}").format(player.current.author, player.current.title)
                        description = "{}\n{}".format(song, query.track.to_string_hidden())
                else:
                    description = bold("[{}]({})").format(player.current.title, player.current.uri)

                embed = discord.Embed(
                    colour=(await self.bot.get_embed_color(message_channel)),
                    title=_("Track Error"),
                    description="{}\n{}".format(extra, description),
                )
                embed.set_footer(text=_("Skipping..."))
                await message_channel.send(embed=embed)
            while True:
                if player.current in player.queue:
                    player.queue.remove(player.current)
                else:
                    break
            if repeat:
                player.current = None
            await player.skip()

    async def play_query(
        self,
        query: str,
        guild: discord.Guild,
        channel: discord.VoiceChannel,
        is_autoplay: bool = True,
    ):
        if not self._player_check(guild.me):
            try:
                if (
                    not channel.permissions_for(guild.me).connect
                    or not channel.permissions_for(guild.me).move_members
                    and userlimit(channel)
                ):
                    log.error(f"I don't have permission to connect to {channel} in {guild}.")

                await lavalink.connect(channel)
                player = lavalink.get_player(guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except IndexError:
                log.debug(
                    f"Connection to Lavalink has not yet been established"
                    f" while trying to connect to to {channel} in {guild}."
                )
                return

        player = lavalink.get_player(guild.id)

        player.store("channel", channel.id)
        player.store("guild", guild.id)
        await self._data_check(guild.me)
        query = dataclasses.Query.process_input(query)
        ctx = namedtuple("Context", "message")
        results, called_api = await self.music_cache.lavalink_query(ctx(guild), player, query)

        if not results.tracks:
            log.debug(f"Query returned no tracks.")
            return
        track = results.tracks[0]

        if not await is_allowed(
            guild, f"{track.title} {track.author} {track.uri} {str(query._raw)}"
        ):
            log.debug(f"Query is not allowed in {guild} ({guild.id})")
            return
        track.extras = {"autoplay": is_autoplay}
        player.add(player.channel.guild.me, track)
        self.bot.dispatch(
            "red_audio_track_auto_play", player.channel.guild, track, player.channel.guild.me
        )
        if not player.current:
            await player.play()

    async def delegate_autoplay(self, cog: commands.Cog = None):
        """
        Parameters
        ----------
        cog: Optional[commands.Cog]
            The Cog who is taking ownership of Audio's autoplay.
            If :code:`None` gives ownership back to Audio
        """
        if isinstance(cog, commands.Cog):
            self.owns_autoplay = cog
        else:
            del self.owns_autoplay

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def audioset(self, ctx: commands.Context):
        """Music configuration options."""
        pass

    @audioset.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def dc(self, ctx: commands.Context):
        """Toggle the bot auto-disconnecting when done playing.

        This setting takes precedence over [p]audioset emptydisconnect.
        """

        disconnect = await self.config.guild(ctx.guild).disconnect()
        autoplay = await self.config.guild(ctx.guild).auto_play()
        msg = ""
        msg += _("Auto-disconnection at queue end: {true_or_false}.").format(
            true_or_false=_("Enabled") if not disconnect else _("Disabled")
        )
        await self.config.guild(ctx.guild).repeat.set(not disconnect)
        if disconnect is not True and autoplay is True:
            msg += _("\nAuto-play has been disabled.")
            await self.config.guild(ctx.guild).auto_play.set(False)

        await self.config.guild(ctx.guild).disconnect.set(not disconnect)

        embed = discord.Embed(
            title=_("Auto-disconnection settings changed"),
            description=msg,
            colour=await ctx.embed_colour(),
        )
        await ctx.send(embed=embed)

    @audioset.group(name="restrictions")
    @checks.mod_or_permissions(manage_messages=True)
    async def _perms(self, ctx: commands.Context):
        """Manages the keyword whitelist and blacklist."""
        pass

    @_perms.group(name="whitelist")
    async def _perms_whitelist(self, ctx: commands.Context):
        """Manages the keyword whitelist."""
        pass

    @_perms.group(name="blacklist")
    async def _perms_blacklist(self, ctx: commands.Context):
        """Manages the keyword blacklist."""
        pass

    @_perms_blacklist.command(name="add")
    async def _perms_blacklist_add(self, ctx: commands.Context, *, keyword: str):
        """Adds a keyword to the blacklist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        exists = False
        async with self.config.guild(ctx.guild).url_keyword_blacklist() as blacklist:
            if keyword in blacklist:
                exists = True
            else:
                blacklist.append(keyword)
        if exists:
            return await self._embed_msg(ctx, _("Keyword already in the blacklist."))
        else:
            embed = discord.Embed(title=_("Blacklist modified"), colour=await ctx.embed_colour())
            embed.description = _("Added: `{blacklisted}` to the blacklist.").format(
                blacklisted=keyword
            )
            await ctx.send(embed=embed)

    @_perms_whitelist.command(name="add")
    async def _perms_whitelist_add(self, ctx: commands.Context, *, keyword: str):
        """Adds a keyword to the whitelist.

        If anything is added to whitelist, it will blacklist everything else.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        exists = False
        async with self.config.guild(ctx.guild).url_keyword_whitelist() as whitelist:
            if keyword in whitelist:
                exists = True
            else:
                whitelist.append(keyword)
        if exists:
            return await self._embed_msg(ctx, _("Keyword already in the whitelist."))
        else:
            embed = discord.Embed(title=_("Whitelist modified"), colour=await ctx.embed_colour())
            embed.description = _("Added: `{whitelisted}` to the whitelist.").format(
                whitelisted=keyword
            )
            await ctx.send(embed=embed)

    @_perms_blacklist.command(name="delete", aliases=["del", "remove"])
    async def _perms_blacklist_delete(self, ctx: commands.Context, *, keyword: str):
        """Removes a keyword from the blacklist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        exists = True
        async with self.config.guild(ctx.guild).url_keyword_blacklist() as blacklist:
            if keyword not in blacklist:
                exists = False
            else:
                blacklist.remove(keyword)
        if not exists:
            return await self._embed_msg(ctx, _("Keyword is not in the blacklist."))
        else:
            embed = discord.Embed(title=_("Blacklist modified"), colour=await ctx.embed_colour())
            embed.description = _("Removed: `{blacklisted}` from the blacklist.").format(
                blacklisted=keyword
            )
            await ctx.send(embed=embed)

    @_perms_whitelist.command(name="delete", aliases=["del", "remove"])
    async def _perms_whitelist_delete(self, ctx: commands.Context, *, keyword: str):
        """Removes a keyword from the whitelist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        exists = True
        async with self.config.guild(ctx.guild).url_keyword_whitelist() as whitelist:
            if keyword not in whitelist:
                exists = False
            else:
                whitelist.remove(keyword)
        if not exists:
            return await self._embed_msg(ctx, _("Keyword already in the whitelist."))
        else:
            embed = discord.Embed(title=_("Whitelist modified"), colour=await ctx.embed_colour())
            embed.description = _("Removed: `{whitelisted}` from the whitelist.").format(
                whitelisted=keyword
            )
            await ctx.send(embed=embed)

    @_perms_whitelist.command(name="list")
    async def _perms_whitelist_list(self, ctx: commands.Context):
        """List all keywords added to the whitelist."""
        whitelist = await self.config.guild(ctx.guild).url_keyword_whitelist()
        if not whitelist:
            return await self._embed_msg(ctx, _("Nothing in the whitelist."))
        whitelist.sort()
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
            discord.Embed(title="Whitelist", description=page, colour=embed_colour)
            for page in pages
        )
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @_perms_blacklist.command(name="list")
    async def _perms_blacklist_list(self, ctx: commands.Context):
        """List all keywords added to the blacklist."""
        blacklist = await self.config.guild(ctx.guild).url_keyword_blacklist()
        if not blacklist:
            return await self._embed_msg(ctx, _("Nothing in the blacklist."))
        blacklist.sort()
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
            discord.Embed(title="Whitelist", description=page, colour=embed_colour)
            for page in pages
        )
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @_perms_whitelist.command(name="clear")
    async def _perms_whitelist_clear(self, ctx: commands.Context):
        """Clear all keywords from the whitelist."""
        whitelist = await self.config.guild(ctx.guild).url_keyword_whitelist()
        if not whitelist:
            return await self._embed_msg(ctx, _("Nothing in the whitelist."))
        await self.config.guild(ctx.guild).url_keyword_whitelist.clear()
        return await self._embed_msg(ctx, _("All entries have been removed from the whitelist."))

    @_perms_blacklist.command(name="clear")
    async def _perms_blacklist_clear(self, ctx: commands.Context):
        """Clear all keywords added to the blacklist."""
        blacklist = await self.config.guild(ctx.guild).url_keyword_blacklist()
        if not blacklist:
            return await self._embed_msg(ctx, _("Nothing in the blacklist."))
        await self.config.guild(ctx.guild).url_keyword_blacklist.clear()
        return await self._embed_msg(ctx, _("All entries have been removed from the blacklist."))

    @audioset.group(name="autoplay")
    @checks.mod_or_permissions(manage_messages=True)
    async def _autoplay(self, ctx: commands.Context):
        """Change auto-play setting."""

    @_autoplay.command(name="toggle")
    async def _autoplay_toggle(self, ctx: commands.Context):
        """Toggle auto-play when there no songs in queue."""
        autoplay = await self.config.guild(ctx.guild).auto_play()
        repeat = await self.config.guild(ctx.guild).repeat()
        disconnect = await self.config.guild(ctx.guild).disconnect()
        msg = _("Auto-play when queue ends: {true_or_false}.").format(
            true_or_false=_("Enabled") if not autoplay else _("Disabled")
        )
        await self.config.guild(ctx.guild).auto_play.set(not autoplay)
        if autoplay is not True and repeat is True:
            msg += _("\nRepeat has been disabled.")
            await self.config.guild(ctx.guild).repeat.set(False)
        if autoplay is not True and disconnect is True:
            msg += _("\nAuto-disconnecting at queue end has been disabled.")
            await self.config.guild(ctx.guild).disconnect.set(False)

        embed = discord.Embed(
            title=_("Auto-play settings changed"), description=msg, colour=await ctx.embed_colour()
        )
        await ctx.send(embed=embed)
        if self._player_check(ctx):
            await self._data_check(ctx)

    @_autoplay.command(name="playlist", usage="<playlist_name_OR_id> [args]")
    async def __autoplay_playlist(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Set a playlist to auto-play songs from.

        **Usage**:
        ​ ​ ​ ​ [p]audioset autoplay playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]audioset autoplay MyGuildPlaylist
        ​ ​ ​ ​ [p]audioset autoplay MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]audioset autoplay PersonalPlaylist --scope User --author Draper
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]

        scope, author, guild, specified_user = scope_data
        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist").format(arg=playlist_arg)
            )
        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
            tracks = playlist.tracks
            if not tracks:
                return await self._embed_msg(
                    ctx, _("Playlist {name} has no tracks.").format(name=playlist.name)
                )
            playlist_data = dict(enabled=True, id=playlist.id, name=playlist.name, scope=scope)
            await self.config.guild(ctx.guild).autoplaylist.set(playlist_data)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )
        else:
            return await self._embed_msg(
                ctx,
                _("Playlist {name} (`{id}`) [**{scope}**] will be used for autoplay.").format(
                    name=playlist.name,
                    id=playlist.id,
                    scope=humanize_scope(
                        scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
                    ),
                ),
            )

    @_autoplay.command(name="reset")
    async def _autoplay_reset(self, ctx: commands.Context):
        """Resets auto-play to the default playlist."""
        playlist_data = dict(enabled=False, id=None, name=None, scope=None)
        await self.config.guild(ctx.guild).autoplaylist.set(playlist_data)
        return await self._embed_msg(ctx, _("Set auto-play playlist to default value."))

    @audioset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def dj(self, ctx: commands.Context):
        """Toggle DJ mode.

        DJ mode allows users with the DJ role to use audio commands.
        """
        dj_role = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
        if dj_role is None:
            await self._embed_msg(
                ctx, _("Please set a role to use with DJ mode. Enter the role name or ID now.")
            )

            try:
                pred = MessagePredicate.valid_role(ctx)
                await ctx.bot.wait_for("message", timeout=15.0, check=pred)
                await ctx.invoke(self.role, pred.result)
            except asyncio.TimeoutError:
                return await self._embed_msg(ctx, _("Response timed out, try again later."))

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        await self.config.guild(ctx.guild).dj_enabled.set(not dj_enabled)
        await self._embed_msg(
            ctx,
            _("DJ role: {true_or_false}.").format(
                true_or_false=_("Enabled") if not dj_enabled else _("Disabled")
            ),
        )

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def emptydisconnect(self, ctx: commands.Context, seconds: int):
        """Auto-disconnection after x seconds while stopped. 0 to disable."""
        if seconds < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self._embed_msg(ctx, _("Empty disconnect disabled."))
        else:
            enabled = True
            await self._embed_msg(
                ctx,
                _("Empty disconnect timer set to {num_seconds}.").format(
                    num_seconds=dynamic_time(seconds)
                ),
            )

        await self.config.guild(ctx.guild).emptydc_timer.set(seconds)
        await self.config.guild(ctx.guild).emptydc_enabled.set(enabled)

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def emptypause(self, ctx: commands.Context, seconds: int):
        """Auto-pause after x seconds when room is empty. 0 to disable."""
        if seconds < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self._embed_msg(ctx, _("Empty pause disabled."))
        else:
            enabled = True
            await self._embed_msg(
                ctx,
                _("Empty pause timer set to {num_seconds}.").format(
                    num_seconds=dynamic_time(seconds)
                ),
            )
        await self.config.guild(ctx.guild).emptypause_timer.set(seconds)
        await self.config.guild(ctx.guild).emptypause_enabled.set(enabled)

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def jukebox(self, ctx: commands.Context, price: int):
        """Set a price for queueing tracks for non-mods. 0 to disable."""
        if price < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if price == 0:
            jukebox = False
            await self._embed_msg(ctx, _("Jukebox mode disabled."))
        else:
            jukebox = True
            await self._embed_msg(
                ctx,
                _("Track queueing command price set to {price} {currency}.").format(
                    price=humanize_number(price), currency=await bank.get_currency_name(ctx.guild)
                ),
            )

        await self.config.guild(ctx.guild).jukebox_price.set(price)
        await self.config.guild(ctx.guild).jukebox.set(jukebox)

    @audioset.command()
    @checks.is_owner()
    async def localpath(self, ctx: commands.Context, *, local_path=None):
        """Set the localtracks path if the Lavalink.jar is not run from the Audio data folder.

        Leave the path blank to reset the path to the default, the Audio data directory.
        """

        if not local_path:
            await self.config.localpath.set(str(cog_data_path(raw_name="Audio")))
            pass_config_to_dependencies(
                self.config, self.bot, str(cog_data_path(raw_name="Audio"))
            )
            return await self._embed_msg(
                ctx, _("The localtracks path location has been reset to the default location.")
            )

        info_msg = _(
            "This setting is only for bot owners to set a localtracks folder location "
            "In the example below, the full path for 'ParentDirectory' "
            "must be passed to this command.\n"
            "The path must not contain spaces.\n"
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
        await ctx.bot.wait_for("reaction_add", check=pred)

        if not pred.result:
            with contextlib.suppress(discord.HTTPException):
                await info.delete()
            return
        temp = dataclasses.LocalPath(local_path, forced=True)
        if not temp.exists() or not temp.is_dir():
            return await self._embed_msg(
                ctx,
                _("{local_path} does not seem like a valid path.").format(local_path=local_path),
            )

        if not temp.localtrack_folder.exists():
            warn_msg = _(
                "`{localtracks}` does not exist. "
                "The path will still be saved, but please check the path and "
                "create a localtracks folder in `{localfolder}` before attempting "
                "to play local tracks."
            ).format(localfolder=temp.absolute(), localtracks=temp.localtrack_folder.absolute())
            await ctx.send(
                embed=discord.Embed(
                    title=_("Incorrect environment."),
                    description=warn_msg,
                    colour=await ctx.embed_colour(),
                )
            )
        local_path = str(temp.localtrack_folder.absolute())
        await self.config.localpath.set(local_path)
        pass_config_to_dependencies(self.config, self.bot, local_path)
        await self._embed_msg(
            ctx, _("Localtracks path set to: {local_path}.").format(local_path=local_path)
        )

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def maxlength(self, ctx: commands.Context, seconds: Union[int, str]):
        """Max length of a track to queue in seconds. 0 to disable.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`).
        Invalid input will turn the max length setting off."""
        if not isinstance(seconds, int):
            seconds = time_convert(seconds)
        if seconds < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if seconds == 0:
            await self._embed_msg(ctx, _("Track max length disabled."))
        else:
            await self._embed_msg(
                ctx, _("Track max length set to {seconds}.").format(seconds=dynamic_time(seconds))
            )

        await self.config.guild(ctx.guild).maxlength.set(seconds)

    @audioset.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def notify(self, ctx: commands.Context):
        """Toggle track announcement and other bot messages."""
        notify = await self.config.guild(ctx.guild).notify()
        await self.config.guild(ctx.guild).notify.set(not notify)
        await self._embed_msg(
            ctx,
            _("Verbose mode: {true_or_false}.").format(
                true_or_false=_("Enabled") if not notify else _("Disabled")
            ),
        )

    @audioset.command()
    @checks.is_owner()
    async def restrict(self, ctx: commands.Context):
        """Toggle the domain restriction on Audio.

        When toggled off, users will be able to play songs from non-commercial websites and links.
        When toggled on, users are restricted to YouTube, SoundCloud,
        Mixer, Vimeo, Twitch, and Bandcamp links."""
        restrict = await self.config.restrict()
        await self.config.restrict.set(not restrict)
        await self._embed_msg(
            ctx,
            _("Commercial links only: {true_or_false}.").format(
                true_or_false=_("Enabled") if not restrict else _("Disabled")
            ),
        )

    @audioset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx: commands.Context, role_name: discord.Role):
        """Set the role to use for DJ mode."""
        await self.config.guild(ctx.guild).dj_role.set(role_name.id)
        dj_role_obj = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
        await self._embed_msg(ctx, _("DJ role set to: {role.name}.").format(role=dj_role_obj))

    @audioset.command()
    async def settings(self, ctx: commands.Context):
        """Show the current settings."""
        is_owner = await ctx.bot.is_owner(ctx.author)
        global_data = await self.config.all()
        data = await self.config.guild(ctx.guild).all()
        dj_role_obj = ctx.guild.get_role(data["dj_role"])
        dj_enabled = data["dj_enabled"]
        emptydc_enabled = data["emptydc_enabled"]
        emptydc_timer = data["emptydc_timer"]
        emptypause_enabled = data["emptypause_enabled"]
        emptypause_timer = data["emptypause_timer"]
        jukebox = data["jukebox"]
        jukebox_price = data["jukebox_price"]
        thumbnail = data["thumbnail"]
        dc = data["disconnect"]
        autoplay = data["auto_play"]
        maxlength = data["maxlength"]
        vote_percent = data["vote_percent"]
        current_level = CacheLevel(global_data["cache_level"])
        song_repeat = _("Enabled") if data["repeat"] else _("Disabled")
        song_shuffle = _("Enabled") if data["shuffle"] else _("Disabled")
        song_notify = _("Enabled") if data["notify"] else _("Disabled")
        song_status = _("Enabled") if global_data["status"] else _("Disabled")

        spotify_cache = CacheLevel.set_spotify()
        youtube_cache = CacheLevel.set_youtube()
        lavalink_cache = CacheLevel.set_lavalink()
        has_spotify_cache = current_level.is_superset(spotify_cache)
        has_youtube_cache = current_level.is_superset(youtube_cache)
        has_lavalink_cache = current_level.is_superset(lavalink_cache)
        autoplaylist = data["autoplaylist"]
        vote_enabled = data["vote_enabled"]
        msg = "----" + _("Server Settings") + "----        \n"
        msg += _("Auto-disconnect:  [{dc}]\n").format(dc=_("Enabled") if dc else _("Disabled"))
        msg += _("Auto-play:        [{autoplay}]\n").format(
            autoplay=_("Enabled") if autoplay else _("Disabled")
        )
        if emptydc_enabled:
            msg += _("Disconnect timer: [{num_seconds}]\n").format(
                num_seconds=dynamic_time(emptydc_timer)
            )
        if emptypause_enabled:
            msg += _("Auto Pause timer: [{num_seconds}]\n").format(
                num_seconds=dynamic_time(emptypause_timer)
            )
        if dj_enabled and dj_role_obj:
            msg += _("DJ Role:          [{role.name}]\n").format(role=dj_role_obj)
        if jukebox:
            msg += _("Jukebox:          [{jukebox_name}]\n").format(jukebox_name=jukebox)
            msg += _("Command price:    [{jukebox_price}]\n").format(
                jukebox_price=humanize_number(jukebox_price)
            )
        if maxlength > 0:
            msg += _("Max track length: [{tracklength}]\n").format(
                tracklength=dynamic_time(maxlength)
            )
        msg += _(
            "Repeat:           [{repeat}]\n"
            "Shuffle:          [{shuffle}]\n"
            "Song notify msgs: [{notify}]\n"
            "Songs as status:  [{status}]\n"
        ).format(repeat=song_repeat, shuffle=song_shuffle, notify=song_notify, status=song_status)
        if thumbnail:
            msg += _("Thumbnails:       [{0}]\n").format(
                _("Enabled") if thumbnail else _("Disabled")
            )
        if vote_percent > 0:
            msg += _(
                "Vote skip:        [{vote_enabled}]\nSkip percentage:  [{vote_percent}%]\n"
            ).format(
                vote_percent=vote_percent,
                vote_enabled=_("Enabled") if vote_enabled else _("Disabled"),
            )

        if self.owns_autoplay is not None:
            msg += (
                "\n---"
                + _("Auto-play Settings")
                + "---        \n"
                + _("Owning Cog:       [{name}]\n").format(name=self._cog_name)
            )
        elif autoplay or autoplaylist["enabled"]:
            if autoplaylist["enabled"]:
                pname = autoplaylist["name"]
                pid = autoplaylist["id"]
                pscope = autoplaylist["scope"]
                if pscope == PlaylistScope.GUILD.value:
                    pscope = f"Server"
                elif pscope == PlaylistScope.USER.value:
                    pscope = f"User"
                else:
                    pscope = "Global"
            else:
                pname = _("Cached")
                pid = _("Cached")
                pscope = _("Cached")
            msg += (
                "\n---"
                + _("Auto-play Settings")
                + "---        \n"
                + _("Playlist name:    [{pname}]\n")
                + _("Playlist ID:      [{pid}]\n")
                + _("Playlist scope:   [{pscope}]\n")
            ).format(pname=pname, pid=pid, pscope=pscope)

        if is_owner:
            msg += (
                "\n---"
                + _("Cache Settings")
                + "---        \n"
                + _("Max age:          [{max_age}]\n")
                + _("Spotify cache:    [{spotify_status}]\n")
                + _("Youtube cache:    [{youtube_status}]\n")
                + _("Lavalink cache:   [{lavalink_status}]\n")
            ).format(
                max_age=str(await self.config.cache_age()) + " " + _("days"),
                spotify_status=_("Enabled") if has_spotify_cache else _("Disabled"),
                youtube_status=_("Enabled") if has_youtube_cache else _("Disabled"),
                lavalink_status=_("Enabled") if has_lavalink_cache else _("Disabled"),
            )

        msg += _(
            "\n---" + _("Lavalink Settings") + "---        \n"
            "Cog version:      [{version}]\n"
            "Red-Lavalink:     [{redlava}]\n"
            "External server:  [{use_external_lavalink}]\n"
        ).format(
            version=__version__,
            redlava=lavalink.__version__,
            use_external_lavalink=_("Enabled")
            if global_data["use_external_lavalink"]
            else _("Disabled"),
        )
        if is_owner:
            msg += _("Localtracks path: [{localpath}]\n").format(**global_data)

        embed = discord.Embed(colour=await ctx.embed_colour(), description=box(msg, lang="ini"))
        return await ctx.send(embed=embed)

    @audioset.command()
    @checks.is_owner()
    async def spotifyapi(self, ctx: commands.Context):
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

    @checks.is_owner()
    @audioset.command()
    async def status(self, ctx: commands.Context):
        """Enable/disable tracks' titles as status."""
        status = await self.config.status()
        await self.config.status.set(not status)
        await self._embed_msg(
            ctx,
            _("Song titles as status: {true_or_false}.").format(
                true_or_false=_("Enabled") if not status else _("Disabled")
            ),
        )

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def thumbnail(self, ctx: commands.Context):
        """Toggle displaying a thumbnail on audio messages."""
        thumbnail = await self.config.guild(ctx.guild).thumbnail()
        await self.config.guild(ctx.guild).thumbnail.set(not thumbnail)
        await self._embed_msg(
            ctx,
            _("Thumbnail display: {true_or_false}.").format(
                true_or_false=_("Enabled") if not thumbnail else _("Disabled")
            ),
        )

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def vote(self, ctx: commands.Context, percent: int):
        """Percentage needed for non-mods to skip tracks. 0 to disable."""
        if percent < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        elif percent > 100:
            percent = 100
        if percent == 0:
            enabled = False
            await self._embed_msg(
                ctx, _("Voting disabled. All users can use queue management commands.")
            )
        else:
            enabled = True
            await self._embed_msg(
                ctx, _("Vote percentage set to {percent}%.").format(percent=percent)
            )

        await self.config.guild(ctx.guild).vote_percent.set(percent)
        await self.config.guild(ctx.guild).vote_enabled.set(enabled)

    @audioset.command()
    @checks.is_owner()
    async def youtubeapi(self, ctx: commands.Context):
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

    @audioset.command(name="cache", usage="level=[5, 3, 2, 1, 0, -1, -2, -3]")
    @checks.is_owner()
    @can_have_caching()
    async def _storage(self, ctx: commands.Context, *, level: int = None):
        """Sets the caching level.

        Level can be one of the following:

        0: Disables all caching
        1: Enables Spotify Cache
        2: Enables YouTube Cache
        3: Enables Lavalink Cache
        5: Enables all Caches

        If you wish to disable a specific cache use a negative number.

        """
        current_level = CacheLevel(await self.config.cache_level())
        spotify_cache = CacheLevel.set_spotify()
        youtube_cache = CacheLevel.set_youtube()
        lavalink_cache = CacheLevel.set_lavalink()
        has_spotify_cache = current_level.is_superset(spotify_cache)
        has_youtube_cache = current_level.is_superset(youtube_cache)
        has_lavalink_cache = current_level.is_superset(lavalink_cache)

        if level is None:
            msg = (
                "---"
                + _("Cache Settings")
                + "---        \n"
                + _("Max age:          [{max_age}]\n")
                + _("Spotify cache:    [{spotify_status}]\n")
                + _("Youtube cache:    [{youtube_status}]\n")
                + _("Lavalink cache:   [{lavalink_status}]\n")
            ).format(
                max_age=str(await self.config.cache_age()) + " " + _("days"),
                spotify_status=_("Enabled") if has_spotify_cache else _("Disabled"),
                youtube_status=_("Enabled") if has_youtube_cache else _("Disabled"),
                lavalink_status=_("Enabled") if has_lavalink_cache else _("Disabled"),
            )
            await ctx.send(
                embed=discord.Embed(
                    colour=await ctx.embed_colour(), description=box(msg, lang="ini")
                )
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
            "---"
            + _("Cache Settings")
            + "---        \n"
            + _("Max age:          [{max_age}]\n")
            + _("Spotify cache:    [{spotify_status}]\n")
            + _("Youtube cache:    [{youtube_status}]\n")
            + _("Lavalink cache:   [{lavalink_status}]\n")
        ).format(
            max_age=str(await self.config.cache_age()) + " " + _("days"),
            spotify_status=_("Enabled") if has_spotify_cache else _("Disabled"),
            youtube_status=_("Enabled") if has_youtube_cache else _("Disabled"),
            lavalink_status=_("Enabled") if has_lavalink_cache else _("Disabled"),
        )
        await ctx.send(
            embed=discord.Embed(colour=await ctx.embed_colour(), description=box(msg, lang="ini"))
        )

        await self.config.cache_level.set(newcache.value)

    @audioset.command(name="cacheage")
    @checks.is_owner()
    @can_have_caching()
    async def _cacheage(self, ctx: commands.Context, age: int):
        """Sets the cache max age.

        This commands allows you to set the max number of days
        before an entry in the cache becomes invalid.
        """
        msg = ""
        if age < 7:
            msg = _(
                "Cache age cannot be less than 7 days. If you wish to disable it run "
                "{prefix}audioset cache.\n"
            ).format(prefix=ctx.prefix)
            age = 7
        msg += _("I've set the cache age to {age} days").format(age=age)
        await self.config.cache_age.set(age)
        await self._embed_msg(ctx, msg)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def audiostats(self, ctx: commands.Context):
        """Audio stats."""
        server_num = len(lavalink.active_players())
        total_num = len(lavalink.all_players())
        localtracks = await self.config.localpath()

        msg = ""
        for p in lavalink.all_players():
            connect_start = p.fetch("connect")
            connect_dur = dynamic_time(
                int((datetime.datetime.utcnow() - connect_start).total_seconds())
            )
            try:
                if any(
                    x in p.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                ):
                    if p.current.title == "Unknown title":
                        current_title = localtracks.LocalPath(p.current.uri).to_string_hidden()
                        msg += "{} [`{}`]: **{}**\n".format(
                            p.channel.guild.name, connect_dur, current_title
                        )
                    else:
                        current_title = p.current.title
                        msg += "{} [`{}`]: **{} - {}**\n".format(
                            p.channel.guild.name, connect_dur, p.current.author, current_title
                        )
                else:
                    msg += "{} [`{}`]: **[{}]({})**\n".format(
                        p.channel.guild.name, connect_dur, p.current.title, p.current.uri
                    )
            except AttributeError:
                msg += "{} [`{}`]: **{}**\n".format(
                    p.channel.guild.name, connect_dur, _("Nothing playing.")
                )

        if total_num == 0:
            return await self._embed_msg(ctx, _("Not connected anywhere."))
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
                text="Page {}/{}".format(
                    humanize_number(pages), humanize_number((math.ceil(len(msg) / 1500)))
                )
            )
            pages += 1
            servers_embed.append(em)

        await menu(ctx, servers_embed, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def bump(self, ctx: commands.Context, index: int):
        """Bump a track number to the top of the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to bump a track.")
            )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to bump tracks."))
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(
                ctx, _("Song number must be greater than 1 and within the queue limit.")
            )

        bump_index = index - 1
        bump_song = player.queue[bump_index]
        player.queue.insert(0, bump_song)
        removed = player.queue.pop(index)
        if any(x in removed.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
            localtrack = dataclasses.LocalPath(removed.uri)
            if removed.title != "Unknown title":
                description = "**{} - {}**\n{}".format(
                    removed.author, removed.title, localtrack.to_string_hidden()
                )
            else:
                description = localtrack.to_string_hidden()
        else:
            description = "**[{}]({})**".format(removed.title, removed.uri)
        await ctx.send(
            embed=discord.Embed(
                title=_("Moved track to the top of the queue."),
                colour=await ctx.embed_colour(),
                description=description,
            )
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def disconnect(self, ctx: commands.Context):
        """Disconnect from the voice channel."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        else:
            dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
            player = lavalink.get_player(ctx.guild.id)

            if dj_enabled:
                if not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(ctx, _("You need the DJ role to disconnect."))
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("There are other people listening to music."))
            else:
                await self._embed_msg(ctx, _("Disconnecting..."))
                self.bot.dispatch("red_audio_audio_disconnect", ctx.guild)
                self._play_lock(ctx, False)
                eq = player.fetch("eq")
                player.queue = []
                player.store("playing_song", None)
                if eq:
                    await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
                await player.stop()
                await player.disconnect()

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def eq(self, ctx: commands.Context):
        """Equalizer management."""
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(ctx, _("Nothing playing."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        player = lavalink.get_player(ctx.guild.id)
        eq = player.fetch("eq", Equalizer())
        reactions = ["◀", "⬅", "⏫", "🔼", "🔽", "⏬", "➡", "▶", "⏺", "ℹ"]
        await self._eq_msg_clear(player.fetch("eq_message"))
        eq_message = await ctx.send(box(eq.visualise(), lang="ini"))

        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            try:
                await eq_message.add_reaction("ℹ")
            except discord.errors.NotFound:
                pass
        else:
            start_adding_reactions(eq_message, reactions, self.bot.loop)

        eq_msg_with_reacts = await ctx.fetch_message(eq_message.id)
        player.store("eq_message", eq_msg_with_reacts)
        await self._eq_interact(ctx, player, eq, eq_msg_with_reacts, 0)

    @eq.command(name="delete", aliases=["del", "remove"])
    async def _eq_delete(self, ctx: commands.Context, eq_preset: str):
        """Delete a saved eq preset."""
        async with self.config.custom("EQUALIZER", ctx.guild.id).eq_presets() as eq_presets:
            eq_preset = eq_preset.lower()
            try:
                if eq_presets[eq_preset][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx, _("You are not the author of that preset setting.")
                    )
                del eq_presets[eq_preset]
            except KeyError:
                return await self._embed_msg(
                    ctx,
                    _(
                        "{eq_preset} is not in the eq preset list.".format(
                            eq_preset=eq_preset.capitalize()
                        )
                    ),
                )
            except TypeError:
                if await self._can_instaskip(ctx, ctx.author):
                    del eq_presets[eq_preset]
                else:
                    return await self._embed_msg(
                        ctx, _("You are not the author of that preset setting.")
                    )

        await self._embed_msg(
            ctx, _("The {preset_name} preset was deleted.".format(preset_name=eq_preset))
        )

    @eq.command(name="list")
    async def _eq_list(self, ctx: commands.Context):
        """List saved eq presets."""
        eq_presets = await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets()
        if not eq_presets.keys():
            return await self._embed_msg(ctx, _("No saved equalizer presets."))

        space = "\N{EN SPACE}"
        header_name = _("Preset Name")
        header_author = _("Author")
        header = box(
            "[{header_name}]{space}[{header_author}]\n".format(
                header_name=header_name, space=space * 9, header_author=header_author
            ),
            lang="ini",
        )
        preset_list = ""
        for preset, bands in eq_presets.items():
            try:
                author = self.bot.get_user(bands["author"])
            except TypeError:
                author = "None"
            msg = f"{preset}{space * (22 - len(preset))}{author}\n"
            preset_list += msg

        page_list = []
        for page in pagify(preset_list, delims=[", "], page_length=1000):
            formatted_page = box(page, lang="ini")
            embed = discord.Embed(
                colour=await ctx.embed_colour(), description=f"{header}\n{formatted_page}"
            )
            embed.set_footer(
                text=_("{num} preset(s)").format(num=humanize_number(len(list(eq_presets.keys()))))
            )
            page_list.append(embed)
        if len(page_list) == 1:
            return await ctx.send(embed=page_list[0])
        await menu(ctx, page_list, DEFAULT_CONTROLS)

    @eq.command(name="load")
    async def _eq_load(self, ctx: commands.Context, eq_preset: str):
        """Load a saved eq preset."""
        eq_preset = eq_preset.lower()
        eq_presets = await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets()
        try:
            eq_values = eq_presets[eq_preset]["bands"]
        except KeyError:
            return await self._embed_msg(
                ctx, _("No preset named {eq_preset}.".format(eq_preset=eq_preset))
            )
        except TypeError:
            eq_values = eq_presets[eq_preset]

        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        player = lavalink.get_player(ctx.guild.id)
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You need the DJ role to load equalizer presets.")
                )

        await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq_values)
        await self._eq_check(ctx, player)
        eq = player.fetch("eq", Equalizer())
        await self._eq_msg_clear(player.fetch("eq_message"))
        message = await ctx.send(
            content=box(eq.visualise(), lang="ini"),
            embed=discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("The {eq_preset} preset was loaded.".format(eq_preset=eq_preset)),
            ),
        )
        player.store("eq_message", message)

    @eq.command(name="reset")
    async def _eq_reset(self, ctx: commands.Context):
        """Reset the eq to 0 across all bands."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You need the DJ role to reset the equalizer.")
                )
        player = lavalink.get_player(ctx.guild.id)
        eq = player.fetch("eq", Equalizer())

        for band in range(eq._band_count):
            eq.set_gain(band, 0.0)

        await self._apply_gains(ctx.guild.id, eq.bands)
        await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
        player.store("eq", eq)
        await self._eq_msg_clear(player.fetch("eq_message"))
        message = await ctx.send(
            content=box(eq.visualise(), lang="ini"),
            embed=discord.Embed(
                colour=await ctx.embed_colour(), title=_("Equalizer values have been reset.")
            ),
        )
        player.store("eq_message", message)

    @eq.command(name="save")
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def _eq_save(self, ctx: commands.Context, eq_preset: str = None):
        """Save the current eq settings to a preset."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You need the DJ role to save equalizer presets.")
                )
        if not eq_preset:
            await self._embed_msg(ctx, _("Please enter a name for this equalizer preset."))
            try:
                eq_name_msg = await ctx.bot.wait_for(
                    "message",
                    timeout=15.0,
                    check=MessagePredicate.regex(fr"^(?!{re.escape(ctx.prefix)})", ctx),
                )
                eq_preset = eq_name_msg.content.split(" ")[0].strip('"').lower()
            except asyncio.TimeoutError:
                return await self._embed_msg(
                    ctx, _("No equalizer preset name entered, try the command again later.")
                )

        eq_exists_msg = None
        eq_preset = eq_preset.lower().lstrip(ctx.prefix)
        eq_presets = await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets()
        eq_list = list(eq_presets.keys())

        if len(eq_preset) > 20:
            return await self._embed_msg(ctx, _("Try the command again with a shorter name."))
        if eq_preset in eq_list:
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Preset name already exists, do you want to replace it?"),
            )
            eq_exists_msg = await ctx.send(embed=embed)
            start_adding_reactions(eq_exists_msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(eq_exists_msg, ctx.author)
            await ctx.bot.wait_for("reaction_add", check=pred)
            if not pred.result:
                await self._clear_react(eq_exists_msg)
                embed2 = discord.Embed(
                    colour=await ctx.embed_colour(), title=_("Not saving preset.")
                )
                return await eq_exists_msg.edit(embed=embed2)

        player = lavalink.get_player(ctx.guild.id)
        eq = player.fetch("eq", Equalizer())
        to_append = {eq_preset: {"author": ctx.author.id, "bands": eq.bands}}
        new_eq_presets = {**eq_presets, **to_append}
        await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets.set(new_eq_presets)
        embed3 = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_(
                "Current equalizer saved to the {preset_name} preset.".format(
                    preset_name=eq_preset
                )
            ),
        )
        if eq_exists_msg:
            await self._clear_react(eq_exists_msg)
            await eq_exists_msg.edit(embed=embed3)
        else:
            await ctx.send(embed=embed3)

    @eq.command(name="set")
    async def _eq_set(self, ctx: commands.Context, band_name_or_position, band_value: float):
        """Set an eq band with a band number or name and value.

        Band positions are 1-15 and values have a range of -0.25 to 1.0.
        Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
        6.3k, 10k, and 16k Hz.
        Setting a band value to -0.25 nullifies it while +0.25 is double.
        """
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You need the DJ role to set equalizer presets.")
                )

        player = lavalink.get_player(ctx.guild.id)
        band_names = [
            "25",
            "40",
            "63",
            "100",
            "160",
            "250",
            "400",
            "630",
            "1k",
            "1.6k",
            "2.5k",
            "4k",
            "6.3k",
            "10k",
            "16k",
        ]

        eq = player.fetch("eq", Equalizer())
        bands_num = eq._band_count
        if band_value > 1:
            band_value = 1
        elif band_value <= -0.25:
            band_value = -0.25
        else:
            band_value = round(band_value, 1)

        try:
            band_number = int(band_name_or_position) - 1
        except ValueError:
            band_number = None

        if band_number not in range(0, bands_num) and band_name_or_position not in band_names:
            return await self._embed_msg(
                ctx,
                _(
                    "Valid band numbers are 1-15 or the band names listed in "
                    "the help for this command."
                ),
            )

        if band_name_or_position in band_names:
            band_pos = band_names.index(band_name_or_position)
            band_int = False
            eq.set_gain(int(band_pos), band_value)
            await self._apply_gain(ctx.guild.id, int(band_pos), band_value)
        else:
            band_int = True
            eq.set_gain(band_number, band_value)
            await self._apply_gain(ctx.guild.id, band_number, band_value)

        await self._eq_msg_clear(player.fetch("eq_message"))
        await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
        player.store("eq", eq)
        band_name = band_names[band_number] if band_int else band_name_or_position
        message = await ctx.send(
            content=box(eq.visualise(), lang="ini"),
            embed=discord.Embed(
                colour=await ctx.embed_colour(),
                title=_(
                    "The {band_name}Hz band has been set to {band_value}.".format(
                        band_name=band_name, band_value=band_value
                    )
                ),
            ),
        )
        player.store("eq_message", message)

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def local(self, ctx: commands.Context):
        """Local playback commands."""

    @local.command(name="folder", aliases=["start"])
    async def local_folder(
        self, ctx: commands.Context, play_subfolders: Optional[bool] = True, *, folder: str = None
    ):
        """Play all songs in a localtracks folder."""
        if not await self._localtracks_check(ctx):
            return

        if not folder:
            await ctx.invoke(self.local_play, play_subfolders=play_subfolders)
        else:
            folder = folder.strip()
            _dir = dataclasses.LocalPath.joinpath(folder)
            if not _dir.exists():
                return await self._embed_msg(
                    ctx, _("No localtracks folder named {name}.").format(name=folder)
                )
            query = dataclasses.Query.process_input(_dir, search_subfolders=play_subfolders)
            await self._local_play_all(ctx, query, from_search=False if not folder else True)

    @local.command(name="play")
    async def local_play(self, ctx: commands.Context, play_subfolders: Optional[bool] = True):
        """Play a local track."""
        if not await self._localtracks_check(ctx):
            return
        localtracks_folders = await self._localtracks_folders(
            ctx, search_subfolders=play_subfolders
        )
        if not localtracks_folders:
            return await self._embed_msg(ctx, _("No album folders found."))
        async with ctx.typing():
            len_folder_pages = math.ceil(len(localtracks_folders) / 5)
            folder_page_list = []
            for page_num in range(1, len_folder_pages + 1):
                embed = await self._build_search_page(ctx, localtracks_folders, page_num)
                folder_page_list.append(embed)

        async def _local_folder_menu(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                await self._search_button_action(ctx, localtracks_folders, emoji, page)
                return None

        local_folder_controls = {
            "1⃣": _local_folder_menu,
            "2⃣": _local_folder_menu,
            "3⃣": _local_folder_menu,
            "4⃣": _local_folder_menu,
            "5⃣": _local_folder_menu,
            "⬅": prev_page,
            "❌": close_menu,
            "➡": next_page,
        }

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await menu(ctx, folder_page_list, DEFAULT_CONTROLS)
        else:
            await menu(ctx, folder_page_list, local_folder_controls)

    @local.command(name="search")
    async def local_search(
        self, ctx: commands.Context, play_subfolders: Optional[bool] = True, *, search_words
    ):
        """Search for songs across all localtracks folders."""
        if not await self._localtracks_check(ctx):
            return
        all_tracks = await self._folder_list(
            ctx,
            (
                dataclasses.Query.process_input(
                    dataclasses.LocalPath(
                        await self.config.localpath()
                    ).localtrack_folder.absolute(),
                    search_subfolders=play_subfolders,
                )
            ),
        )
        if not all_tracks:
            return await self._embed_msg(ctx, _("No album folders found."))
        async with ctx.typing():
            search_list = await self._build_local_search_list(all_tracks, search_words)
        if not search_list:
            return await self._embed_msg(ctx, _("No matches."))
        return await ctx.invoke(self.search, query=search_list)

    async def _localtracks_folders(self, ctx: commands.Context, search_subfolders=False):
        audio_data = dataclasses.LocalPath(
            dataclasses.LocalPath(None).localtrack_folder.absolute()
        )
        if not await self._localtracks_check(ctx):
            return

        return audio_data.subfolders_in_tree() if search_subfolders else audio_data.subfolders()

    async def _folder_list(self, ctx: commands.Context, query: dataclasses.Query):
        if not await self._localtracks_check(ctx):
            return
        query = dataclasses.Query.process_input(query)
        if not query.track.exists():
            return
        return (
            query.track.tracks_in_tree()
            if query.search_subfolders
            else query.track.tracks_in_folder()
        )

    async def _folder_tracks(
        self, ctx, player: lavalink.player_manager.Player, query: dataclasses.Query
    ):
        if not await self._localtracks_check(ctx):
            return

        audio_data = dataclasses.LocalPath(None)
        try:
            query.track.path.relative_to(audio_data.to_string())
        except ValueError:
            return
        local_tracks = []
        for local_file in await self._all_folder_tracks(ctx, query):
            trackdata, called_api = await self.music_cache.lavalink_query(ctx, player, local_file)
            with contextlib.suppress(IndexError):
                local_tracks.append(trackdata.tracks[0])
        return local_tracks

    async def _local_play_all(
        self, ctx: commands.Context, query: dataclasses.Query, from_search=False
    ):
        if not await self._localtracks_check(ctx):
            return
        if from_search:
            query = dataclasses.Query.process_input(
                query.track.to_string(), invoked_from="local folder"
            )
        await ctx.invoke(self.search, query=query)

    async def _all_folder_tracks(self, ctx: commands.Context, query: dataclasses.Query):
        if not await self._localtracks_check(ctx):
            return

        return (
            query.track.tracks_in_tree()
            if query.search_subfolders
            else query.track.tracks_in_folder()
        )

    async def _localtracks_check(self, ctx: commands.Context):
        folder = dataclasses.LocalPath(None)
        if folder.localtrack_folder.exists():
            return True
        if ctx.invoked_with != "start":
            await self._embed_msg(ctx, _("No localtracks folder."))
        return False

    @staticmethod
    async def _build_local_search_list(to_search, search_words):
        to_search_string = {i.track.name for i in to_search}
        search_results = process.extract(search_words, to_search_string, limit=50)
        search_list = []
        for track_match, percent_match in search_results:
            if percent_match > 60:
                search_list.extend(
                    [i.track.to_string_hidden() for i in to_search if i.track.name == track_match]
                )
        return search_list

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def now(self, ctx: commands.Context):
        """Now playing."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        expected = ("⏮", "⏹", "⏯", "⏭")
        emoji = {"prev": "⏮", "stop": "⏹", "pause": "⏯", "next": "⏭"}
        player = lavalink.get_player(ctx.guild.id)
        if player.current:
            arrow = await draw_time(ctx)
            pos = lavalink.utils.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
            else:
                dur = lavalink.utils.format_time(player.current.length)
            if any(
                x in player.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
            ):
                if not player.current.title == "Unknown title":
                    song = "**{track.author} - {track.title}**\n{uri}\n"
                else:
                    song = "{uri}\n"
            else:
                song = "**[{track.title}]({track.uri})**\n"
            song += _("Requested by: **{track.requester}**")
            song += "\n\n{arrow}`{pos}`/`{dur}`"
            song = song.format(
                track=player.current,
                uri=dataclasses.LocalPath(player.current.uri).to_string_hidden()
                if any(
                    x in player.current.uri
                    for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                )
                else player.current.uri,
                arrow=arrow,
                pos=pos,
                dur=dur,
            )
        else:
            song = _("Nothing.")

        if player.fetch("np_message") is not None:
            with contextlib.suppress(discord.HTTPException):
                await player.fetch("np_message").delete()

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Now Playing"), description=song
        )
        if await self.config.guild(ctx.guild).thumbnail() and player.current:
            if player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)

        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        autoplay = await self.config.guild(ctx.guild).auto_play() or self.owns_autoplay
        text = ""
        text += (
            _("Auto-Play")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if autoplay else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Shuffle")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if shuffle else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Repeat")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if repeat else "\N{CROSS MARK}")
        )
        embed.set_footer(text=text)

        message = await ctx.send(embed=embed)

        player.store("np_message", message)

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if dj_enabled or vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return

        if player.current:
            task = start_adding_reactions(message, expected[:4], ctx.bot.loop)
        else:
            task = None

        try:
            (r, u) = await self.bot.wait_for(
                "reaction_add",
                check=ReactionPredicate.with_emojis(expected, message, ctx.author),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            return await self._clear_react(message, emoji)
        else:
            if task is not None:
                task.cancel()
        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]
        if react == "prev":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.prev)
        elif react == "stop":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.stop)
        elif react == "pause":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.pause)
        elif react == "next":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.skip)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def pause(self, ctx: commands.Context):
        """Pause or resume a playing track."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel pause or resume.")
            )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(
                    ctx, _("You need the DJ role to pause or resume tracks.")
                )

        if not player.current:
            return await self._embed_msg(ctx, _("Nothing playing."))
        if any(x in player.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
            query = dataclasses.Query.process_input(player.current.uri)
            if player.current.title == "Unknown title":
                description = "{}".format(query.track.to_string_hidden())
            else:
                song = bold("{} - {}").format(player.current.author, player.current.title)
                description = "{}\n{}".format(song, query.track.to_string_hidden())
        else:
            description = bold("[{}]({})").format(player.current.title, player.current.uri)

        if player.current and not player.paused:
            await player.pause()
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Track Paused"), description=description
            )
            return await ctx.send(embed=embed)
        if player.current and player.paused:
            await player.pause(False)
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Track Resumed"), description=description
            )
            return await ctx.send(embed=embed)

        await self._embed_msg(ctx, _("Nothing playing."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def percent(self, ctx: commands.Context):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
        requesters = {"total": 0, "users": {}}

        async def _usercount(req_username):
            if req_username in requesters["users"]:
                requesters["users"][req_username]["songcount"] += 1
                requesters["total"] += 1
            else:
                requesters["users"][req_username] = {}
                requesters["users"][req_username]["songcount"] = 1
                requesters["total"] += 1

        for track in queue_tracks:
            req_username = "{}#{}".format(track.requester.name, track.requester.discriminator)
            await _usercount(req_username)

        try:
            req_username = "{}#{}".format(
                player.current.requester.name, player.current.requester.discriminator
            )
            await _usercount(req_username)
        except AttributeError:
            return await self._embed_msg(ctx, _("There's  nothing in the queue."))

        for req_username in requesters["users"]:
            percentage = float(requesters["users"][req_username]["songcount"]) / float(
                requesters["total"]
            )
            requesters["users"][req_username]["percent"] = round(percentage * 100, 1)

        top_queue_users = heapq.nlargest(
            20,
            [
                (x, requesters["users"][x][y])
                for x in requesters["users"]
                for y in requesters["users"][x]
                if y == "percent"
            ],
            key=lambda x: x[1],
        )
        queue_user = ["{}: {:g}%".format(x[0], x[1]) for x in top_queue_users]
        queue_user_list = "\n".join(queue_user)
        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Queued and playing tracks:"),
            description=queue_user_list,
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def play(self, ctx: commands.Context, *, query: str):
        """Play a URL or search for a track."""
        guild_data = await self.config.guild(ctx.guild).all()
        restrict = await self.config.restrict()
        if restrict and match_url(query):
            valid_url = url_check(query)
            if not valid_url:
                return await self._embed_msg(ctx, _("That URL is not allowed."))
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                if await ctx.bot.is_owner(ctx.author):
                    msg += " " + _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, msg)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, _("Connect to a voice channel first."))
            except IndexError:
                return await self._embed_msg(
                    ctx, _("Connection to Lavalink has not yet been established.")
                )
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to queue tracks."))
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to use the play command.")
            )
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        query = dataclasses.Query.process_input(query)
        if not query.valid:
            return await self._embed_msg(ctx, _("No tracks to play."))
        if query.is_spotify:
            return await self._get_spotify_tracks(ctx, query)
        await self._enqueue_tracks(ctx, query)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def genre(self, ctx: commands.Context):
        """Pick a Spotify playlist from a list of categories to start playing."""

        async def _category_search_menu(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                output = await self._genre_search_button_action(ctx, category_list, emoji, page)
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return output

        async def _playlist_search_menu(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                output = await self._genre_search_button_action(
                    ctx, playlists_list, emoji, page, playlist=True
                )
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return output

        category_search_controls = {
            "1⃣": _category_search_menu,
            "2⃣": _category_search_menu,
            "3⃣": _category_search_menu,
            "4⃣": _category_search_menu,
            "5⃣": _category_search_menu,
            "⬅": prev_page,
            "❌": close_menu,
            "➡": next_page,
        }
        playlist_search_controls = {
            "1⃣": _playlist_search_menu,
            "2⃣": _playlist_search_menu,
            "3⃣": _playlist_search_menu,
            "4⃣": _playlist_search_menu,
            "5⃣": _playlist_search_menu,
            "⬅": prev_page,
            "❌": close_menu,
            "➡": next_page,
        }

        api_data = await self._check_api_tokens()
        if any(
            [
                not api_data["spotify_client_id"],
                not api_data["spotify_client_secret"],
                not api_data["youtube_api"],
            ]
        ):
            return await self._embed_msg(
                ctx,
                _(
                    "The owner needs to set the Spotify client ID, Spotify client secret, "
                    "and YouTube API key before Spotify URLs or codes can be used. "
                    "\nSee `{prefix}audioset youtubeapi` and `{prefix}audioset spotifyapi` "
                    "for instructions."
                ).format(prefix=ctx.prefix),
            )
        guild_data = await self.config.guild(ctx.guild).all()
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                if await ctx.bot.is_owner(ctx.author):
                    msg += " " + _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, msg)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, _("Connect to a voice channel first."))
            except IndexError:
                return await self._embed_msg(
                    ctx, _("Connection to Lavalink has not yet been established.")
                )
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to queue tracks."))
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to use the genre command.")
            )
        try:
            category_list = await self.music_cache.spotify_api.get_categories()
        except SpotifyFetchError as error:
            return await self._embed_msg(ctx, _(error.message).format(prefix=ctx.prefix))
        if not category_list:
            return await self._embed_msg(ctx, _("No categories found, try again later."))
        len_folder_pages = math.ceil(len(category_list) / 5)
        category_search_page_list = []
        for page_num in range(1, len_folder_pages + 1):
            embed = await self._build_genre_search_page(
                ctx, category_list, page_num, _("Categories")
            )
            category_search_page_list.append(embed)
        cat_menu_output = await menu(ctx, category_search_page_list, category_search_controls)
        if not cat_menu_output:
            return await self._embed_msg(ctx, _("No categories selected, try again later."))
        category_name, category_pick = cat_menu_output
        playlists_list = await self.music_cache.spotify_api.get_playlist_from_category(
            category_pick
        )
        if not playlists_list:
            return await self._embed_msg(ctx, _("No categories found, try again later."))
        len_folder_pages = math.ceil(len(playlists_list) / 5)
        playlists_search_page_list = []
        for page_num in range(1, len_folder_pages + 1):
            embed = await self._build_genre_search_page(
                ctx,
                playlists_list,
                page_num,
                _("Playlists for {friendly_name}").format(friendly_name=category_name),
                playlist=True,
            )
            playlists_search_page_list.append(embed)
        playlists_pick = await menu(ctx, playlists_search_page_list, playlist_search_controls)
        query = dataclasses.Query.process_input(playlists_pick)
        if not query.valid:
            return await self._embed_msg(ctx, _("No tracks to play."))
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        if query.is_spotify:
            return await self._get_spotify_tracks(ctx, query)
        return await self._embed_msg(ctx, _("Couldn't find tracks for the selected playlist."))

    @staticmethod
    async def _genre_search_button_action(
        ctx: commands.Context, options, emoji, page, playlist=False
    ):
        try:
            if emoji == "1⃣":
                search_choice = options[0 + (page * 5)]
            elif emoji == "2⃣":
                search_choice = options[1 + (page * 5)]
            elif emoji == "3⃣":
                search_choice = options[2 + (page * 5)]
            elif emoji == "4⃣":
                search_choice = options[3 + (page * 5)]
            elif emoji == "5⃣":
                search_choice = options[4 + (page * 5)]
            else:
                search_choice = options[0 + (page * 5)]
                # TODO: Verify this doesn't break exit and arrows
        except IndexError:
            search_choice = options[-1]
        if not playlist:
            return list(search_choice.items())[0]
        else:
            return search_choice.get("uri")

    @staticmethod
    async def _build_genre_search_page(
        ctx: commands.Context, tracks, page_num, title, playlist=False
    ):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        for i, entry in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            if playlist:
                name = "**[{}]({})** - {}".format(
                    entry.get("name"),
                    entry.get("url"),
                    str(entry.get("tracks")) + " " + _("tracks"),
                )
            else:
                name = f"{list(entry.keys())[0]}"
            search_list += "`{}.` {}\n".format(search_track_num, name)

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages}").format(
                page_num=page_num, total_pages=search_num_pages
            )
        )
        return embed

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def autoplay(self, ctx: commands.Context):
        """Starts auto play."""
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                if await ctx.bot.is_owner(ctx.author):
                    msg += " " + _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, msg)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, _("Connect to a voice channel first."))
            except IndexError:
                return await self._embed_msg(
                    ctx, _("Connection to Lavalink has not yet been established.")
                )
        guild_data = await self.config.guild(ctx.guild).all()
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to queue tracks."))
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to use the autoplay command.")
            )
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        if self.owns_autoplay is None:
            await self.music_cache.autoplay(player)
        else:
            self.bot.dispatch(
                "red_audio_should_auto_play",
                player,
                player.channel.guild,
                player.channel,
                self.play_query,
            )
        if not guild_data["auto_play"]:
            await ctx.invoke(self._autoplay_toggle)
        if not guild_data["notify"] and (
            (player.current and not player.current.extras.get("autoplay")) or not player.current
        ):
            await self._embed_msg(ctx, _("Auto play started."))
        elif player.current:
            await self._embed_msg(ctx, _("Adding a track to queue."))

    async def _get_spotify_tracks(self, ctx: commands.Context, query: dataclasses.Query):
        if ctx.invoked_with in ["play", "genre"]:
            enqueue_tracks = True
        else:
            enqueue_tracks = False
        player = lavalink.get_player(ctx.guild.id)
        api_data = await self._check_api_tokens()

        if (
            not api_data["spotify_client_id"]
            or not api_data["spotify_client_secret"]
            or not api_data["youtube_api"]
        ):
            return await self._embed_msg(
                ctx,
                _(
                    "The owner needs to set the Spotify client ID, Spotify client secret, "
                    "and YouTube API key before Spotify URLs or codes can be used. "
                    "\nSee `{prefix}audioset youtubeapi` and `{prefix}audioset spotifyapi` "
                    "for instructions."
                ).format(prefix=ctx.prefix),
            )
        try:
            if self.play_lock[ctx.message.guild.id]:
                return await self._embed_msg(
                    ctx, _("Wait until the playlist has finished loading.")
                )
        except KeyError:
            pass

        if query.single_track:
            try:
                res = await self.music_cache.spotify_query(
                    ctx, "track", query.id, skip_youtube=True, notifier=None
                )
                if not res:
                    return await self._embed_msg(ctx, _("Nothing found."))
            except SpotifyFetchError as error:
                self._play_lock(ctx, False)
                return await self._embed_msg(ctx, _(error.message).format(prefix=ctx.prefix))
            self._play_lock(ctx, False)
            try:
                if enqueue_tracks:
                    new_query = dataclasses.Query.process_input(res[0])
                    new_query.start_time = query.start_time
                    return await self._enqueue_tracks(ctx, new_query)
                else:
                    result, called_api = await self.music_cache.lavalink_query(
                        ctx, player, dataclasses.Query.process_input(res[0])
                    )
                    tracks = result.tracks
                    if not tracks:
                        return await self._embed_msg(ctx, _("Nothing found."))
                    single_track = tracks[0]
                    single_track.start_timestamp = query.start_time * 1000
                    single_track = [single_track]

                    return single_track

            except KeyError:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx,
                    _(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    ).format(prefix=ctx.prefix),
                )
        elif query.is_album or query.is_playlist:
            self._play_lock(ctx, True)
            track_list = await self._spotify_playlist(
                ctx, "album" if query.is_album else "playlist", query, enqueue_tracks
            )
            self._play_lock(ctx, False)
            return track_list
        else:
            return await self._embed_msg(
                ctx, _("This doesn't seem to be a supported Spotify URL or code.")
            )

    async def _enqueue_tracks(self, ctx: commands.Context, query: Union[dataclasses.Query, list]):
        player = lavalink.get_player(ctx.guild.id)
        try:
            if self.play_lock[ctx.message.guild.id]:
                return await self._embed_msg(
                    ctx, _("Wait until the playlist has finished loading.")
                )
        except KeyError:
            self._play_lock(ctx, True)
        guild_data = await self.config.guild(ctx.guild).all()
        first_track_only = False
        index = None
        playlist_data = None
        seek = 0
        if type(query) is not list:

            if query.single_track:
                first_track_only = True
                index = query.track_index
                if query.start_time:
                    seek = query.start_time
            result, called_api = await self.music_cache.lavalink_query(ctx, player, query)
            tracks = result.tracks
            playlist_data = result.playlist_info
            if not tracks:
                self._play_lock(ctx, False)
                embed = discord.Embed(title=_("Nothing found."), colour=await ctx.embed_colour())
                if await self.config.use_external_lavalink() and query.is_local:
                    embed.description = _(
                        "Local tracks will not work "
                        "if the `Lavalink.jar` cannot see the track.\n"
                        "This may be due to permissions or because Lavalink.jar is being run "
                        "in a different machine than the local tracks."
                    )
                return await ctx.send(embed=embed)
        else:
            tracks = query
        queue_dur = await queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        before_queue_length = len(player.queue)

        if not first_track_only and len(tracks) > 1:
            # a list of Tracks where all should be enqueued
            # this is a Spotify playlist aleady made into a list of Tracks or a
            # url where Lavalink handles providing all Track objects to use, like a
            # YouTube or Soundcloud playlist
            track_len = 0
            empty_queue = not player.queue
            for track in tracks:
                if not await is_allowed(
                    ctx.guild,
                    (
                        f"{track.title} {track.author} {track.uri} "
                        f"{str(dataclasses.Query.process_input(track))}"
                    ),
                ):
                    log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
                    continue
                elif guild_data["maxlength"] > 0:
                    if track_limit(track, guild_data["maxlength"]):
                        track_len += 1
                        player.add(ctx.author, track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                        )

                else:
                    track_len += 1
                    player.add(ctx.author, track)
                    self.bot.dispatch(
                        "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                    )
            player.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                    bad_tracks=(len(tracks) - track_len)
                )
            else:
                maxlength_msg = ""
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                description="{name}".format(
                    name=playlist_data.name if playlist_data else _("No Title")
                ),
                title=_("Playlist Enqueued"),
            )
            embed.set_footer(
                text=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                    num=track_len, maxlength_msg=maxlength_msg
                )
            )
            if not guild_data["shuffle"] and queue_dur > 0:
                embed.set_footer(
                    text=_(
                        "{time} until start of playlist playback: starts at #{position} in queue"
                    ).format(time=queue_total_duration, position=before_queue_length + 1)
                )
            if not player.current:
                await player.play()
        else:
            # a ytsearch: prefixed item where we only need the first Track returned
            # this is in the case of [p]play <query>, a single Spotify url/code
            # or this is a localtrack item
            try:

                single_track = tracks[index] if index else tracks[0]
                if seek and seek > 0:
                    single_track.start_timestamp = seek * 1000
                if not await is_allowed(
                    ctx.guild,
                    (
                        f"{single_track.title} {single_track.author} {single_track.uri} "
                        f"{str(dataclasses.Query.process_input(single_track))}"
                    ),
                ):
                    log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
                    self._play_lock(ctx, False)
                    return await self._embed_msg(
                        ctx, _("This track is not allowed in this server.")
                    )
                elif guild_data["maxlength"] > 0:
                    if track_limit(single_track, guild_data["maxlength"]):
                        player.add(ctx.author, single_track)
                        player.maybe_shuffle()
                        self.bot.dispatch(
                            "red_audio_track_enqueue",
                            player.channel.guild,
                            single_track,
                            ctx.author,
                        )
                    else:
                        self._play_lock(ctx, False)
                        return await self._embed_msg(ctx, _("Track exceeds maximum length."))

                else:
                    player.add(ctx.author, single_track)
                    player.maybe_shuffle()
                    self.bot.dispatch(
                        "red_audio_track_enqueue", player.channel.guild, single_track, ctx.author
                    )
            except IndexError:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx, _("Nothing found. Check your Lavalink logs for details.")
                )
            if any(
                x in single_track.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
            ):
                if single_track.title != "Unknown title":
                    description = "**{} - {}**\n{}".format(
                        single_track.author,
                        single_track.title,
                        dataclasses.LocalPath(single_track.uri).to_string_hidden(),
                    )
                else:
                    description = "{}".format(
                        dataclasses.LocalPath(single_track.uri).to_string_hidden()
                    )
            else:
                description = "**[{}]({})**".format(single_track.title, single_track.uri)
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Track Enqueued"), description=description
            )
            if not guild_data["shuffle"] and queue_dur > 0:
                embed.set_footer(
                    text=_("{time} until track playback: #{position} in queue").format(
                        time=queue_total_duration, position=before_queue_length + 1
                    )
                )

        await ctx.send(embed=embed)
        if not player.current:
            await player.play()

        self._play_lock(ctx, False)

    async def _spotify_playlist(
        self, ctx: commands.Context, stype: str, query: dataclasses.Query, enqueue: bool = False
    ):

        player = lavalink.get_player(ctx.guild.id)
        try:
            embed1 = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Please wait, finding tracks...")
            )
            playlist_msg = await ctx.send(embed=embed1)
            notifier = Notifier(
                ctx,
                playlist_msg,
                {
                    "spotify": _("Getting track {num}/{total}..."),
                    "youtube": _("Matching track {num}/{total}..."),
                    "lavalink": _("Loading track {num}/{total}..."),
                    "lavalink_time": _("Approximate time remaining: {seconds}"),
                },
            )
            track_list = await self.music_cache.spotify_enqueue(
                ctx,
                stype,
                query.id,
                enqueue=enqueue,
                player=player,
                lock=self._play_lock,
                notifier=notifier,
            )
        except SpotifyFetchError as error:
            self._play_lock(ctx, False)
            return await self._embed_msg(ctx, _(error.message).format(prefix=ctx.prefix))
        except (RuntimeError, aiohttp.ServerDisconnectedError):
            self._play_lock(ctx, False)
            error_embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("The connection was reset while loading the playlist."),
            )
            await ctx.send(embed=error_embed)
            return None
        except Exception as e:
            self._play_lock(ctx, False)
            raise e
        self._play_lock(ctx, False)
        return track_list

    async def can_manage_playlist(
        self, scope: str, playlist: Playlist, ctx: commands.Context, user, guild
    ):

        is_owner = await ctx.bot.is_owner(ctx.author)
        has_perms = False
        user_to_query = user
        guild_to_query = guild
        dj_enabled = None
        playlist_author = (
            guild.get_member(playlist.author)
            if guild
            else self.bot.get_user(playlist.author) or user
        )

        is_different_user = len({playlist.author, user_to_query.id, ctx.author.id}) != 1
        is_different_guild = True if guild_to_query is None else ctx.guild.id != guild_to_query.id

        if is_owner:
            has_perms = True
        elif playlist.scope == PlaylistScope.USER.value:
            if not is_different_user:
                has_perms = True
        elif playlist.scope == PlaylistScope.GUILD.value:
            if not is_different_guild:
                dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
                if guild.owner_id == ctx.author.id:
                    has_perms = True
                elif dj_enabled and await self._has_dj_role(ctx, ctx.author):
                    has_perms = True
                elif await ctx.bot.is_mod(ctx.author):
                    has_perms = True
                elif not dj_enabled and not is_different_user:
                    has_perms = True

        if has_perms is False:
            if hasattr(playlist, "name"):
                msg = _(
                    "You do not have the permissions to manage {name} " "(`{id}`) [**{scope}**]."
                ).format(
                    user=playlist_author,
                    name=playlist.name,
                    id=playlist.id,
                    scope=humanize_scope(
                        playlist.scope,
                        ctx=guild_to_query
                        if playlist.scope == PlaylistScope.GUILD.value
                        else playlist_author
                        if playlist.scope == PlaylistScope.USER.value
                        else None,
                    ),
                )
            elif playlist.scope == PlaylistScope.GUILD.value and (
                is_different_guild or dj_enabled
            ):
                msg = _(
                    "You do not have the permissions to manage that playlist in {guild}."
                ).format(guild=guild_to_query)
            elif (
                playlist.scope in [PlaylistScope.GUILD.value, PlaylistScope.USER.value]
                and is_different_user
            ):
                msg = _(
                    "You do not have the permissions to manage playlist owned by {user}."
                ).format(user=playlist_author)
            else:
                msg = _(
                    "You do not have the permissions to manage "
                    "playlists in {scope} scope.".format(scope=humanize_scope(scope, the=True))
                )

            await self._embed_msg(ctx, msg)
            return False
        return True

    async def _get_correct_playlist_id(
        self,
        context: commands.Context,
        matches: dict,
        scope: str,
        author: discord.User,
        guild: discord.Guild,
        specified_user: bool = False,
    ) -> Tuple[Optional[int], str]:
        """
        Parameters
        ----------
        context: commands.Context
            The context in which this is being called.
        matches: dict
            A dict of the matches found where key is scope and value is matches.
        scope:str
            The custom config scope. A value from :code:`PlaylistScope`.
        author: discord.User
            The user.
        guild: discord.Guild
            The guild.
        specified_user: bool
            Whether or not a user ID was specified via argparse.
        Returns
        -------
        Tuple[Optional[int], str]
            Tuple of Playlist ID or None if none found and original user input.
        Raises
        ------
        `TooManyMatches`
            When more than 10 matches are found or
            When multiple matches are found but none is selected.

        """
        original_input = matches.get("arg")
        correct_scope_matches = matches.get(scope)
        guild_to_query = guild.id
        user_to_query = author.id
        if not correct_scope_matches:
            return None, original_input
        if scope == PlaylistScope.USER.value:
            correct_scope_matches = [
                (i[2]["id"], i[2]["name"], len(i[2]["tracks"]), i[2]["author"])
                for i in correct_scope_matches
                if str(user_to_query) == i[0]
            ]
        elif scope == PlaylistScope.GUILD.value:
            if specified_user:
                correct_scope_matches = [
                    (i[2]["id"], i[2]["name"], len(i[2]["tracks"]), i[2]["author"])
                    for i in correct_scope_matches
                    if str(guild_to_query) == i[0] and i[2]["author"] == user_to_query
                ]
            else:
                correct_scope_matches = [
                    (i[2]["id"], i[2]["name"], len(i[2]["tracks"]), i[2]["author"])
                    for i in correct_scope_matches
                    if str(guild_to_query) == i[0]
                ]
        else:
            if specified_user:
                correct_scope_matches = [
                    (i[2]["id"], i[2]["name"], len(i[2]["tracks"]), i[2]["author"])
                    for i in correct_scope_matches
                    if i[2]["author"] == user_to_query
                ]
            else:
                correct_scope_matches = [
                    (i[2]["id"], i[2]["name"], len(i[2]["tracks"]), i[2]["author"])
                    for i in correct_scope_matches
                ]
        match_count = len(correct_scope_matches)
        # We done all the trimming we can with the info available time to ask the user
        if match_count > 10:
            if original_input.isnumeric():
                arg = int(original_input)
                correct_scope_matches = [
                    (i, n, t, a) for i, n, t, a in correct_scope_matches if i == arg
                ]
            if match_count > 10:
                raise TooManyMatches(
                    f"{match_count} playlists match {original_input}: "
                    f"Please try to be more specific, or use the playlist ID."
                )
        elif match_count == 1:
            return correct_scope_matches[0][0], original_input
        elif match_count == 0:
            return None, original_input

        # TODO : Convert this section to a new paged reaction menu when Toby Menus are Merged
        pos_len = 3
        playlists = f"{'#':{pos_len}}\n"

        for number, (pid, pname, ptracks, pauthor) in enumerate(correct_scope_matches, 1):
            author = self.bot.get_user(pauthor) or "Unknown"
            line = (
                f"{number}."
                f"    <{pname}>\n"
                f" - Scope:  < {humanize_scope(scope)} >\n"
                f" - ID:     < {pid} >\n"
                f" - Tracks: < {ptracks} >\n"
                f" - Author: < {author} >\n\n"
            )
            playlists += line

        embed = discord.Embed(
            title="Playlists found, which one would you like?",
            description=box(playlists, lang="md"),
            colour=await context.embed_colour(),
        )
        msg = await context.send(embed=embed)
        avaliable_emojis = ReactionPredicate.NUMBER_EMOJIS[1:]
        avaliable_emojis.append("🔟")
        emojis = avaliable_emojis[: len(correct_scope_matches)]
        emojis.append("❌")
        start_adding_reactions(msg, emojis)
        pred = ReactionPredicate.with_emojis(emojis, msg, user=context.author)
        try:
            await context.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            with contextlib.suppress(discord.HTTPException):
                await msg.delete()
            raise TooManyMatches(
                "Too many matches found and you did not select which one you wanted."
            )
        if emojis[pred.result] == "❌":
            with contextlib.suppress(discord.HTTPException):
                await msg.delete()
            raise TooManyMatches(
                "Too many matches found and you did not select which one you wanted."
            )
        with contextlib.suppress(discord.HTTPException):
            await msg.delete()
        return correct_scope_matches[pred.result][0], original_input

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def playlist(self, ctx: commands.Context):
        """Playlist configuration options.

        Scope info:
        ​ ​ ​ ​ **Global**:
        ​ ​ ​ ​ ​ ​ ​ ​ Visible to all users of this bot.
        ​ ​ ​ ​ ​ ​ ​ ​ Only editable by bot owner.
        ​ ​ ​ ​ **Guild**:
        ​ ​ ​ ​ ​ ​ ​ ​ Visible to all users in this guild.
        ​ ​ ​ ​ ​ ​ ​ ​ Editable by bot owner, guild owner, guild admins,
        ​ ​ ​ ​ ​ ​ ​ ​ guild mods, DJ role and playlist creator.
        ​ ​ ​ ​ **User**:
        ​ ​ ​ ​ ​ ​ ​ ​ Visible to all bot users, if --author is passed.
        ​ ​ ​ ​ ​ ​ ​ ​ Editable by bot owner and creator.

        """
        pass

    @playlist.command(name="append", usage="<playlist_name_OR_id> <track_name_OR_url> [args]")
    async def _playlist_append(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        query: LazyGreedyConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Add a track URL, playlist link, or quick search to a playlist.

        The track(s) will be appended to the end of the playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist append playlist_name_OR_id track_name_OR_url args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist append MyGuildPlaylist Hello by Adele
        ​ ​ ​ ​ [p]playlist append MyGlobalPlaylist Hello by Adele --scope Global
        ​ ​ ​ ​ [p]playlist append MyGlobalPlaylist Hello by Adele --scope Global
        --Author Draper#6666
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        if not await self._playlist_check(ctx):
            return
        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
            return
        player = lavalink.get_player(ctx.guild.id)
        to_append = await self._playlist_tracks(
            ctx, player, dataclasses.Query.process_input(query)
        )
        if not to_append:
            return await self._embed_msg(ctx, _("Could not find a track matching your query."))
        track_list = playlist.tracks
        tracks_obj_list = playlist.tracks_obj
        to_append_count = len(to_append)
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        appended = 0

        if to_append and to_append_count == 1:
            to = lavalink.Track(to_append[0])
            if to in tracks_obj_list:
                return await self._embed_msg(
                    ctx,
                    _("{track} is already in {playlist} (`{id}`) [**{scope}**].").format(
                        track=to.title, playlist=playlist.name, id=playlist.id, scope=scope_name
                    ),
                )
            else:
                appended += 1
        if to_append and to_append_count > 1:
            to_append_temp = []
            for t in to_append:
                to = lavalink.Track(t)
                if to not in tracks_obj_list:
                    appended += 1
                    to_append_temp.append(t)
            to_append = to_append_temp
        if appended > 0:
            track_list.extend(to_append)
            update = {"tracks": track_list, "url": None}
            await playlist.edit(update)

        if to_append_count == 1 and appended == 1:
            track_title = to_append[0]["info"]["title"]
            return await self._embed_msg(
                ctx,
                _("{track} appended to {playlist} (`{id}`) [**{scope}**].").format(
                    track=track_title, playlist=playlist.name, id=playlist.id, scope=scope_name
                ),
            )

        desc = _("{num} tracks appended to {playlist} (`{id}`) [**{scope}**].").format(
            num=appended, playlist=playlist.name, id=playlist.id, scope=scope_name
        )
        if to_append_count > appended:
            diff = to_append_count - appended
            desc += _("\n{existing} {plural} already in the playlist and were skipped.").format(
                existing=diff, plural=_("tracks are") if diff != 1 else _("track is")
            )

        embed = discord.Embed(
            title=_("Playlist Modified"), colour=await ctx.embed_colour(), description=desc
        )
        await ctx.send(embed=embed)

    @playlist.command(name="copy", usage="<id_or_name> [args]")
    async def _playlist_copy(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ComplexScopeParser = None,
    ):

        """Copy a playlist from one scope to another.

        **Usage**:
        ​ ​ ​ ​ [p]playlist copy playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --from-scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --from-author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --from-guild [guild] **Only the bot owner can use this**

        ​ ​ ​ ​ ​ ​ ​ ​ --to-scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --to-author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --to-guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist copy MyGuildPlaylist --from-scope Guild --to-scope Global
        ​ ​ ​ ​ [p]playlist copy MyGlobalPlaylist --from-scope Global --to-author Draper#6666
        --to-scope User
        ​ ​ ​ ​ [p]playlist copy MyPersonalPlaylist --from-scope user --to-author Draper#6666
        --to-scope Guild --to-guild Red - Discord Bot

        """

        if scope_data is None:
            scope_data = [
                PlaylistScope.GUILD.value,
                ctx.author,
                ctx.guild,
                False,
                PlaylistScope.GUILD.value,
                ctx.author,
                ctx.guild,
                False,
            ]
        (
            from_scope,
            from_author,
            from_guild,
            specified_from_user,
            to_scope,
            to_author,
            to_guild,
            specified_to_user,
        ) = scope_data

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, from_scope, from_author, from_guild, specified_from_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))

        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        temp_playlist = FakePlaylist(to_author.id, to_scope)
        if not await self.can_manage_playlist(to_scope, temp_playlist, ctx, to_author, to_guild):
            return

        try:
            from_playlist = await get_playlist(
                playlist_id, from_scope, self.bot, from_guild, from_author.id
            )
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(to_scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        to_playlist = await create_playlist(
            ctx,
            to_scope,
            from_playlist.name,
            from_playlist.url,
            from_playlist.tracks,
            to_author,
            to_guild,
        )
        if to_scope == PlaylistScope.GLOBAL.value:
            to_scope_name = "the Global"
        elif to_scope == PlaylistScope.USER.value:
            to_scope_name = to_author
        else:
            to_scope_name = to_guild

        if from_scope == PlaylistScope.GLOBAL.value:
            from_scope_name = "the Global"
        elif from_scope == PlaylistScope.USER.value:
            from_scope_name = from_author
        else:
            from_scope_name = from_guild

        return await self._embed_msg(
            ctx,
            _(
                "Playlist {name} (`{from_id}`) copied from {from_scope} to {to_scope} (`{to_id}`)."
            ).format(
                name=from_playlist.name,
                from_id=from_playlist.id,
                from_scope=humanize_scope(from_scope, ctx=from_scope_name, the=True),
                to_scope=humanize_scope(to_scope, ctx=to_scope_name, the=True),
                to_id=to_playlist.id,
            ),
        )

    @playlist.command(name="create", usage="<name> [args]")
    async def _playlist_create(
        self, ctx: commands.Context, playlist_name: str, *, scope_data: ScopeParser = None
    ):
        """Create an empty playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist create playlist_name args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist create MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist create MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist create MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data

        temp_playlist = FakePlaylist(author.id, scope)
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
            return
        playlist_name = playlist_name.split(" ")[0].strip('"')[:32]
        if playlist_name.isnumeric():
            return await self._embed_msg(
                ctx,
                _(
                    "Playlist names must be a single word (up to 32 "
                    "characters) and not numbers only."
                ),
            )
        playlist = await create_playlist(ctx, scope, playlist_name, None, None, author, guild)
        return await self._embed_msg(
            ctx,
            _("Empty playlist {name} (`{id}`) [**{scope}**] created.").format(
                name=playlist.name, id=playlist.id, scope=scope_name
            ),
        )

    @playlist.command(name="delete", aliases=["del"], usage="<playlist_name_OR_id> [args]")
    async def _playlist_delete(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Delete a saved playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist delete playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist delete MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist delete MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist delete MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
            return
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        await delete_playlist(scope, playlist.id, guild or ctx.guild, author or ctx.author)

        await self._embed_msg(
            ctx,
            _("{name} (`{id}`) [**{scope}**] playlist deleted.").format(
                name=playlist.name, id=playlist.id, scope=scope_name
            ),
        )

    @playlist.command(name="dedupe", usage="<playlist_name_OR_id> [args]")
    async def _playlist_remdupe(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Remove duplicate tracks from a saved playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist dedupe playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist dedupe MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist dedupe MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist dedupe MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
            return

        track_objects = playlist.tracks_obj
        original_count = len(track_objects)
        unique_tracks = set()
        unique_tracks_add = unique_tracks.add
        track_objects = [
            x for x in track_objects if not (x in unique_tracks or unique_tracks_add(x))
        ]

        tracklist = []
        for track in track_objects:
            track_keys = track._info.keys()
            track_values = track._info.values()
            track_id = track.track_identifier
            track_info = {}
            for k, v in zip(track_keys, track_values):
                track_info[k] = v
            keys = ["track", "info"]
            values = [track_id, track_info]
            track_obj = {}
            for key, value in zip(keys, values):
                track_obj[key] = value
            tracklist.append(track_obj)

        final_count = len(tracklist)
        if original_count - final_count != 0:
            update = {"tracks": tracklist, "url": None}
            await playlist.edit(update)

        if original_count - final_count != 0:
            await self._embed_msg(
                ctx,
                _(
                    "Removed {track_diff} duplicated "
                    "tracks from {name} (`{id}`) [**{scope}**] playlist."
                ).format(
                    name=playlist.name,
                    id=playlist.id,
                    track_diff=original_count - final_count,
                    scope=scope_name,
                ),
            )
        else:
            await self._embed_msg(
                ctx,
                _("{name} (`{id}`) [**{scope}**] playlist has no duplicate tracks.").format(
                    name=playlist.name, id=playlist.id, scope=scope_name
                ),
            )

    @checks.is_owner()
    @playlist.command(name="download", usage="<playlist_name_OR_id> [v2=False] [args]")
    @commands.bot_has_permissions(attach_files=True)
    async def _playlist_download(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        v2: Optional[bool] = False,
        *,
        scope_data: ScopeParser = None,
    ):
        """Download a copy of a playlist.

        These files can be used with the [p]playlist upload command.
        Red v2-compatible playlists can be generated by passing True
        for the v2 variable.

        **Usage**:
        ​ ​ ​ ​ [p]playlist download playlist_name_OR_id [v2=True_OR_False] args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist download MyGuildPlaylist True
        ​ ​ ​ ​ [p]playlist download MyGlobalPlaylist False --scope Global
        ​ ​ ​ ​ [p]playlist download MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        schema = 2
        version = "v3" if v2 is False else "v2"

        if not playlist.tracks:
            return await self._embed_msg(ctx, _("That playlist has no tracks."))
        if version == "v2":
            v2_valid_urls = ["https://www.youtube.com/watch?v=", "https://soundcloud.com/"]
            song_list = []
            for track in playlist.tracks:
                if track["info"]["uri"].startswith(tuple(v2_valid_urls)):
                    song_list.append(track["info"]["uri"])
            playlist_data = {
                "author": playlist.author,
                "link": playlist.url,
                "playlist": song_list,
                "name": playlist.name,
            }
            file_name = playlist.name
        else:
            playlist_data = playlist.to_json()
            playlist_songs_backwards_compatible = [
                track["info"]["uri"] for track in playlist.tracks
            ]
            playlist_data[
                "playlist"
            ] = (
                playlist_songs_backwards_compatible
            )  # TODO: Keep new playlists backwards compatible, Remove me in a few releases
            playlist_data[
                "link"
            ] = (
                playlist.url
            )  # TODO: Keep new playlists backwards compatible, Remove me in a few releases
            file_name = playlist.id
        playlist_data.update({"schema": schema, "version": version})
        playlist_data = json.dumps(playlist_data)
        to_write = StringIO()
        to_write.write(playlist_data)
        to_write.seek(0)
        await ctx.send(file=discord.File(to_write, filename=f"{file_name}.txt"))
        to_write.close()

    @playlist.command(name="info", usage="<playlist_name_OR_id> [args]")
    async def _playlist_info(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Retrieve information from a saved playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist info playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist info MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist info MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist info MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )
        track_len = len(playlist.tracks)

        msg = "​"
        track_idx = 0
        if track_len > 0:
            spaces = "\N{EN SPACE}" * (len(str(len(playlist.tracks))) + 2)
            for track in playlist.tracks:
                track_idx = track_idx + 1
                query = dataclasses.Query.process_input(track["info"]["uri"])
                if any(x in str(query) for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
                    if track["info"]["title"] != "Unknown title":
                        msg += "`{}.` **{} - {}**\n{}{}\n".format(
                            track_idx,
                            track["info"]["author"],
                            track["info"]["title"],
                            spaces,
                            query.to_string_user(),
                        )
                    else:
                        msg += "`{}.` {}\n".format(track_idx, query.to_string_user())
                else:
                    msg += "`{}.` **[{}]({})**\n".format(
                        track_idx, track["info"]["title"], track["info"]["uri"]
                    )

        else:
            msg = "No tracks."

        if not playlist.url:
            embed_title = _("Playlist info for {playlist_name} (`{id}`) [**{scope}**]:\n").format(
                playlist_name=playlist.name, id=playlist.id, scope=scope_name
            )
        else:
            embed_title = _(
                "Playlist info for {playlist_name} (`{id}`) [**{scope}**]:\nURL: {url}"
            ).format(
                playlist_name=playlist.name, url=playlist.url, id=playlist.id, scope=scope_name
            )

        page_list = []
        pages = list(pagify(msg, delims=["\n"], page_length=2000))
        total_pages = len(pages)
        for numb, page in enumerate(pages, start=1):
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=embed_title, description=page
            )
            author_obj = self.bot.get_user(playlist.author)
            embed.set_footer(
                text=_("Page {page}/{pages} | Author: {author_name} | {num} track(s)").format(
                    author_name=author_obj, num=track_len, pages=total_pages, page=numb
                )
            )
            page_list.append(embed)
        await menu(ctx, page_list, DEFAULT_CONTROLS)

    @playlist.command(name="list", usage="[args]")
    @commands.bot_has_permissions(add_reactions=True)
    async def _playlist_list(self, ctx: commands.Context, *, scope_data: ScopeParser = None):
        """List saved playlists.

        **Usage**:
        ​ ​ ​ ​ [p]playlist list args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist list
        ​ ​ ​ ​ [p]playlist list --scope Global
        ​ ​ ​ ​ [p]playlist list --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data

        try:
            playlists = await get_all_playlist(scope, self.bot, guild, author, specified_user)
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        if scope == PlaylistScope.GUILD.value:
            name = f"{guild.name}"
        elif scope == PlaylistScope.USER.value:
            name = f"{author}"
        else:
            name = "the global scope"

        if not playlists and specified_user:
            return await self._embed_msg(
                ctx,
                _("No saved playlists for {scope} created by {author}.").format(
                    scope=name, author=author
                ),
            )
        elif not playlists:
            return await self._embed_msg(
                ctx, _("No saved playlists for {scope}.").format(scope=name)
            )

        playlist_list = []
        space = "\N{EN SPACE}"
        for playlist in playlists:
            playlist_list.append(
                ("\n" + space * 4).join(
                    (
                        bold(playlist.name),
                        _("ID: {id}").format(id=playlist.id),
                        _("Tracks: {num}").format(num=len(playlist.tracks)),
                        _("Author: {name}\n").format(name=self.bot.get_user(playlist.author)),
                    )
                )
            )
        abc_names = sorted(playlist_list, key=str.lower)
        len_playlist_list_pages = math.ceil(len(abc_names) / 5)
        playlist_embeds = []

        for page_num in range(1, len_playlist_list_pages + 1):
            embed = await self._build_playlist_list_page(ctx, page_num, abc_names, name)
            playlist_embeds.append(embed)
        await menu(ctx, playlist_embeds, DEFAULT_CONTROLS)

    @staticmethod
    async def _build_playlist_list_page(ctx: commands.Context, page_num, abc_names, scope):
        plist_num_pages = math.ceil(len(abc_names) / 5)
        plist_idx_start = (page_num - 1) * 5
        plist_idx_end = plist_idx_start + 5
        plist = ""
        for i, playlist_info in enumerate(
            abc_names[plist_idx_start:plist_idx_end], start=plist_idx_start
        ):
            item_idx = i + 1
            plist += "`{}.` {}".format(item_idx, playlist_info)
        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Playlists for {scope}:").format(scope=scope),
            description=plist,
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num} playlists.").format(
                page_num=page_num, total_pages=plist_num_pages, num=len(abc_names)
            )
        )
        return embed

    @commands.cooldown(1, 15, commands.BucketType.guild)
    @playlist.command(name="queue", usage="<name> [args]")
    async def _playlist_queue(
        self, ctx: commands.Context, playlist_name: str, *, scope_data: ScopeParser = None
    ):
        """Save the queue to a playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist queue playlist_name

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist queue MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist queue MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist queue MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        temp_playlist = FakePlaylist(author.id, scope)
        if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
            return
        playlist_name = playlist_name.split(" ")[0].strip('"')[:32]
        if playlist_name.isnumeric():
            return await self._embed_msg(
                ctx,
                _(
                    "Playlist names must be a single word "
                    "(up to 32 characters) and not numbers only."
                ),
            )
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))

        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        tracklist = []
        np_song = track_creator(player, "np")
        tracklist.append(np_song)
        for track in player.queue:
            queue_idx = player.queue.index(track)
            track_obj = track_creator(player, queue_idx)
            tracklist.append(track_obj)

        playlist = await create_playlist(ctx, scope, playlist_name, None, tracklist, author, guild)
        await self._embed_msg(
            ctx,
            _(
                "Playlist {name} (`{id}`) [**{scope}**] saved "
                "from current queue: {num} tracks added."
            ).format(
                name=playlist.name, num=len(playlist.tracks), id=playlist.id, scope=scope_name
            ),
        )

    @playlist.command(name="remove", usage="<playlist_name_OR_id> <url> [args]")
    async def _playlist_remove(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        url: str,
        *,
        scope_data: ScopeParser = None,
    ):
        """Remove a track from a playlist by url.

         **Usage**:
        ​ ​ ​ ​ [p]playlist remove playlist_name_OR_id url args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist remove MyGuildPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU
        ​ ​ ​ ​ [p]playlist remove MyGlobalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU
        --scope Global
        ​ ​ ​ ​ [p]playlist remove MyPersonalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU
        --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
            return

        track_list = playlist.tracks
        clean_list = [track for track in track_list if url != track["info"]["uri"]]
        if len(track_list) == len(clean_list):
            return await self._embed_msg(ctx, _("URL not in playlist."))
        del_count = len(track_list) - len(clean_list)
        if not clean_list:
            await delete_playlist(
                scope=playlist.scope, playlist_id=playlist.id, guild=guild, author=playlist.author
            )
            return await self._embed_msg(ctx, _("No tracks left, removing playlist."))
        update = {"tracks": clean_list, "url": None}
        await playlist.edit(update)
        if del_count > 1:
            await self._embed_msg(
                ctx,
                _(
                    "{num} entries have been removed from the"
                    " playlist {playlist_name} (`{id}`) [**{scope}**]."
                ).format(
                    num=del_count, playlist_name=playlist.name, id=playlist.id, scope=scope_name
                ),
            )
        else:
            await self._embed_msg(
                ctx,
                _(
                    "The track has been removed from the"
                    " playlist: {playlist_name} (`{id}`) [**{scope}**]."
                ).format(playlist_name=playlist.name, id=playlist.id, scope=scope_name),
            )

    @playlist.command(name="save", usage="<name> <url> [args]")
    async def _playlist_save(
        self,
        ctx: commands.Context,
        playlist_name: str,
        playlist_url: str,
        *,
        scope_data: ScopeParser = None,
    ):
        """Save a playlist from a url.

        **Usage**:
        ​ ​ ​ ​ [p]playlist save name url args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist save MyGuildPlaylist
        https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM
        ​ ​ ​ ​ [p]playlist save MyGlobalPlaylist
        https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM --scope Global
        ​ ​ ​ ​ [p]playlist save MyPersonalPlaylist
        https://open.spotify.com/playlist/1RyeIbyFeIJVnNzlGr5KkR --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )

        temp_playlist = FakePlaylist(author.id, scope)
        if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
            return
        playlist_name = playlist_name.split(" ")[0].strip('"')[:32]
        if playlist_name.isnumeric():
            return await self._embed_msg(
                ctx,
                _(
                    "Playlist names must be a single word (up to 32 "
                    "characters) and not numbers only."
                ),
            )
        if not await self._playlist_check(ctx):
            return
        player = lavalink.get_player(ctx.guild.id)
        tracklist = await self._playlist_tracks(
            ctx, player, dataclasses.Query.process_input(playlist_url)
        )
        if tracklist is not None:
            playlist = await create_playlist(
                ctx, scope, playlist_name, playlist_url, tracklist, author, guild
            )
            return await self._embed_msg(
                ctx,
                _("Playlist {name} (`{id}`) [**{scope}**] saved: {num} tracks added.").format(
                    name=playlist.name, num=len(tracklist), id=playlist.id, scope=scope_name
                ),
            )

    @playlist.command(name="start", usage="<playlist_name_OR_id> [args]")
    async def _playlist_start(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Load a playlist into the queue.

        **Usage**:
        ​ ​ ​ ​ [p]playlist start playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist start MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist start MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist start MyPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                await self._embed_msg(ctx, _("You need the DJ role to start playing playlists."))
                return False

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist").format(arg=playlist_arg)
            )

        if not await self._playlist_check(ctx):
            return
        jukebox_price = await self.config.guild(ctx.guild).jukebox_price()
        if not await self._currency_check(ctx, jukebox_price):
            return
        maxlength = await self.config.guild(ctx.guild).maxlength()
        author_obj = self.bot.get_user(ctx.author.id)
        track_len = 0
        playlist = None
        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
            player = lavalink.get_player(ctx.guild.id)
            tracks = playlist.tracks_obj
            empty_queue = not player.queue
            for track in tracks:
                if not await is_allowed(
                    ctx.guild,
                    (
                        f"{track.title} {track.author} {track.uri} "
                        f"{str(dataclasses.Query.process_input(track))}"
                    ),
                ):
                    log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
                    continue
                if any(x in track.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
                    local_path = dataclasses.LocalPath(track.uri)
                    if not await self._localtracks_check(ctx):
                        pass
                    if not local_path.exists() and not local_path.is_file():
                        continue
                if maxlength > 0:
                    if not track_limit(track.length, maxlength):
                        continue

                player.add(author_obj, track)
                self.bot.dispatch(
                    "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                )
                track_len += 1
            player.maybe_shuffle(0 if empty_queue else 1)
            if len(tracks) > track_len:
                maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                    bad_tracks=(len(tracks) - track_len)
                )
            else:
                maxlength_msg = ""
            if scope == PlaylistScope.GUILD.value:
                scope_name = f"{guild.name}"
            elif scope == PlaylistScope.USER.value:
                scope_name = f"{author}"
            else:
                scope_name = "the global scope"

            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playlist Enqueued"),
                description=_(
                    "{name} - (`{id}`) [**{scope}**]\nAdded {num} "
                    "tracks to the queue.{maxlength_msg}"
                ).format(
                    num=track_len,
                    maxlength_msg=maxlength_msg,
                    name=playlist.name,
                    id=playlist.id,
                    scope=scope_name,
                ),
            )
            await ctx.send(embed=embed)
            if not player.current:
                await player.play()
            return
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )
        except TypeError:
            if playlist:
                return await ctx.invoke(self.play, query=playlist.url)

    @playlist.command(name="update", usage="<playlist_name_OR_id> [args]")
    async def _playlist_update(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Updates all tracks in a playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist update playlist_name_OR_id args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist update MyGuildPlaylist
        ​ ​ ​ ​ [p]playlist update MyGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist update MyPersonalPlaylist --scope User
        """

        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))

        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        if not await self._playlist_check(ctx):
            return
        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
            if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
                return
            if playlist.url:
                player = lavalink.get_player(ctx.guild.id)
                added, removed, playlist = await self._maybe_update_playlist(ctx, player, playlist)
            else:
                return await self._embed_msg(ctx, _("Custom playlists cannot be updated."))
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )
        else:
            scope_name = humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            if added or removed:
                _colour = await ctx.embed_colour()
                embeds = []
                total_added = len(added)
                total_removed = len(removed)
                total_pages = math.ceil(total_removed / 10) + math.ceil(total_added / 10)
                page_count = 0
                if removed:
                    removed_text = ""
                    for i, track in enumerate(removed, 1):
                        if len(track.title) > 40:
                            track_title = str(track.title).replace("[", "")
                            track_title = "{}...".format((track_title[:40]).rstrip(" "))
                        else:
                            track_title = track.title
                        removed_text += f"`{i}.` **[{track_title}]({track.uri})**\n"
                        if i % 10 == 0 or i == total_removed:
                            page_count += 1
                            embed = discord.Embed(
                                title=_("Tracks removed"), colour=_colour, description=removed_text
                            )
                            text = _("Page {page_num}/{total_pages}").format(
                                page_num=page_count, total_pages=total_pages
                            )
                            embed.set_footer(text=text)
                            embeds.append(embed)
                            removed_text = ""
                if added:
                    added_text = ""
                    for i, track in enumerate(added, 1):
                        if len(track.title) > 40:
                            track_title = str(track.title).replace("[", "")
                            track_title = "{}...".format((track_title[:40]).rstrip(" "))
                        else:
                            track_title = track.title
                        added_text += f"`{i}.` **[{track_title}]({track.uri})**\n"
                        if i % 10 == 0 or i == total_added:
                            page_count += 1
                            embed = discord.Embed(
                                title=_("Tracks added"), colour=_colour, description=added_text
                            )
                            text = _("Page {page_num}/{total_pages}").format(
                                page_num=page_count, total_pages=total_pages
                            )
                            embed.set_footer(text=text)
                            embeds.append(embed)
                            added_text = ""
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                return await self._embed_msg(
                    ctx,
                    _("No changes for {name} (`{id}`) [**{scope}**].").format(
                        id=playlist.id, name=playlist.name, scope=scope_name
                    ),
                )

    @checks.is_owner()
    @playlist.command(name="upload", usage="[args]")
    async def _playlist_upload(self, ctx: commands.Context, *, scope_data: ScopeParser = None):
        """Uploads a playlist file as a playlist for the bot.

        V2 and old V3 playlist will be slow.
        V3 Playlist made with [p]playlist download will load a lot faster.

        **Usage**:
        ​ ​ ​ ​ [p]playlist upload args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist upload
        ​ ​ ​ ​ [p]playlist upload --scope Global
        ​ ​ ​ ​ [p]playlist upload --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        temp_playlist = FakePlaylist(author.id, scope)
        if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
            return

        if not await self._playlist_check(ctx):
            return
        player = lavalink.get_player(ctx.guild.id)

        await self._embed_msg(
            ctx,
            _("Please upload the playlist file. Any other message will cancel this operation."),
        )

        try:
            file_message = await ctx.bot.wait_for(
                "message", timeout=30.0, check=MessagePredicate.same_context(ctx)
            )
        except asyncio.TimeoutError:
            return await self._embed_msg(ctx, _("No file detected, try again later."))
        try:
            file_url = file_message.attachments[0].url
        except IndexError:
            return await self._embed_msg(ctx, _("Upload cancelled."))
        file_suffix = file_url.rsplit(".", 1)[1]
        if file_suffix != "txt":
            return await self._embed_msg(ctx, _("Only playlist files can be uploaded."))
        try:
            async with self.session.request("GET", file_url) as r:
                uploaded_playlist = await r.json(content_type="text/plain")
        except UnicodeDecodeError:
            return await self._embed_msg(ctx, _("Not a valid playlist file."))

        new_schema = uploaded_playlist.get("schema", 1) >= 2
        version = uploaded_playlist.get("version", "v2")

        if new_schema and version == "v3":
            uploaded_playlist_url = uploaded_playlist.get("playlist_url", None)
            track_list = uploaded_playlist.get("tracks", [])
        else:
            uploaded_playlist_url = uploaded_playlist.get("link", None)
            track_list = uploaded_playlist.get("playlist", [])

        uploaded_playlist_name = uploaded_playlist.get(
            "name", (file_url.split("/")[6]).split(".")[0]
        )
        if (
            not uploaded_playlist_url
            or not match_yt_playlist(uploaded_playlist_url)
            or not (
                await self.music_cache.lavalink_query(
                    ctx, player, dataclasses.Query.process_input(uploaded_playlist_url)
                )
            )[0].tracks
        ):
            if version == "v3":
                return await self._load_v3_playlist(
                    ctx,
                    scope,
                    uploaded_playlist_name,
                    uploaded_playlist_url,
                    track_list,
                    author,
                    guild,
                )
            return await self._load_v2_playlist(
                ctx,
                track_list,
                player,
                uploaded_playlist_url,
                uploaded_playlist_name,
                scope,
                author,
                guild,
            )
        return await ctx.invoke(
            self._playlist_save,
            playlist_name=uploaded_playlist_name,
            playlist_url=uploaded_playlist_url,
            scope_data=(scope, author, guild, specified_user),
        )

    @playlist.command(name="rename", usage="<playlist_name_OR_id> <new_name> [args]")
    async def _playlist_rename(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        new_name: str,
        *,
        scope_data: ScopeParser = None,
    ):
        """Rename an existing playlist.

        **Usage**:
        ​ ​ ​ ​ [p]playlist rename playlist_name_OR_id new_name args

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        Scope is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        Author can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        Guild can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ [p]playlist rename MyGuildPlaylist RenamedGuildPlaylist
        ​ ​ ​ ​ [p]playlist rename MyGlobalPlaylist RenamedGlobalPlaylist --scope Global
        ​ ​ ​ ​ [p]playlist rename MyPersonalPlaylist RenamedPersonalPlaylist --scope User
        """
        if scope_data is None:
            scope_data = [PlaylistScope.GUILD.value, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data

        new_name = new_name.split(" ")[0].strip('"')[:32]
        if new_name.isnumeric():
            return await self._embed_msg(
                ctx,
                _(
                    "Playlist names must be a single word (up to 32 "
                    "characters) and not numbers only."
                ),
            )

        try:
            playlist_id, playlist_arg = await self._get_correct_playlist_id(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self._embed_msg(ctx, str(e))
        if playlist_id is None:
            return await self._embed_msg(
                ctx, _("Could not match '{arg}' to a playlist.").format(arg=playlist_arg)
            )

        try:
            playlist = await get_playlist(playlist_id, scope, self.bot, guild, author)
        except RuntimeError:
            return await self._embed_msg(
                ctx,
                _("Playlist {id} does not exist in {scope} scope.").format(
                    id=playlist_id, scope=humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self._embed_msg(
                ctx, _("You need to specify the Guild ID for the guild to lookup.")
            )

        if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
            return
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        old_name = playlist.name
        update = {"name": new_name}
        await playlist.edit(update)
        msg = _("'{old}' playlist has been renamed to '{new}' (`{id}`) [**{scope}**]").format(
            old=bold(old_name), new=bold(playlist.name), id=playlist.id, scope=scope_name
        )
        await self._embed_msg(ctx, msg)

    async def _load_v3_playlist(
        self,
        ctx: commands.Context,
        scope: str,
        uploaded_playlist_name: str,
        uploaded_playlist_url: str,
        track_list,
        author: Union[discord.User, discord.Member],
        guild: Union[discord.Guild],
    ):
        embed1 = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Please wait, adding tracks...")
        )
        playlist_msg = await ctx.send(embed=embed1)
        track_count = len(track_list)
        uploaded_track_count = len(track_list)
        await asyncio.sleep(1)
        embed2 = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Loading track {num}/{total}...").format(
                num=track_count, total=uploaded_track_count
            ),
        )
        await playlist_msg.edit(embed=embed2)
        playlist = await create_playlist(
            ctx, scope, uploaded_playlist_name, uploaded_playlist_url, track_list, author, guild
        )
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        if not track_count:
            msg = _("Empty playlist {name} (`{id}`) [**{scope}**] created.").format(
                name=playlist.name, id=playlist.id, scope=scope_name
            )
        elif uploaded_track_count != track_count:
            bad_tracks = uploaded_track_count - track_count
            msg = _(
                "Added {num} tracks from the {playlist_name} playlist. {num_bad} track(s) "
                "could not be loaded."
            ).format(num=track_count, playlist_name=playlist.name, num_bad=bad_tracks)
        else:
            msg = _("Added {num} tracks from the {playlist_name} playlist.").format(
                num=track_count, playlist_name=playlist.name
            )
        embed3 = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Playlist Saved"), description=msg
        )
        await playlist_msg.edit(embed=embed3)
        database_entries = []
        time_now = str(datetime.datetime.now(datetime.timezone.utc))
        for t in track_list:
            uri = t.get("info", {}).get("uri")
            if uri:
                t = {"loadType": "V2_COMPAT", "tracks": [t], "query": uri}
                database_entries.append(
                    {
                        "query": uri,
                        "data": json.dumps(t),
                        "last_updated": time_now,
                        "last_fetched": time_now,
                    }
                )
        if database_entries and HAS_SQL:
            asyncio.ensure_future(self.music_cache.insert("lavalink", database_entries))

    async def _load_v2_playlist(
        self,
        ctx: commands.Context,
        uploaded_track_list,
        player: lavalink.player_manager.Player,
        playlist_url: str,
        uploaded_playlist_name: str,
        scope: str,
        author: Union[discord.User, discord.Member],
        guild: Union[discord.Guild],
    ):
        track_list = []
        track_count = 0
        successfull_count = 0
        uploaded_track_count = len(uploaded_track_list)

        embed1 = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Please wait, adding tracks...")
        )
        playlist_msg = await ctx.send(embed=embed1)
        notifier = Notifier(ctx, playlist_msg, {"playlist": _("Loading track {num}/{total}...")})
        for song_url in uploaded_track_list:
            track_count += 1
            try:
                result, called_api = await self.music_cache.lavalink_query(
                    ctx, player, dataclasses.Query.process_input(song_url)
                )
                track = result.tracks
            except Exception:
                continue
            try:
                track_obj = track_creator(player, other_track=track[0])
                track_list.append(track_obj)
                successfull_count += 1
            except Exception:
                continue
            if (track_count % 2 == 0) or (track_count == len(uploaded_track_list)):
                await notifier.notify_user(
                    current=track_count, total=len(uploaded_track_list), key="playlist"
                )

        playlist = await create_playlist(
            ctx, scope, uploaded_playlist_name, playlist_url, track_list, author, guild
        )
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        if not successfull_count:
            msg = _("Empty playlist {name} (`{id}`) [**{scope}**] created.").format(
                name=playlist.name, id=playlist.id, scope=scope_name
            )
        elif uploaded_track_count != successfull_count:
            bad_tracks = uploaded_track_count - successfull_count
            msg = _(
                "Added {num} tracks from the {playlist_name} playlist. {num_bad} track(s) "
                "could not be loaded."
            ).format(num=successfull_count, playlist_name=playlist.name, num_bad=bad_tracks)
        else:
            msg = _("Added {num} tracks from the {playlist_name} playlist.").format(
                num=successfull_count, playlist_name=playlist.name
            )
        embed3 = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Playlist Saved"), description=msg
        )
        await playlist_msg.edit(embed=embed3)

    async def _maybe_update_playlist(
        self, ctx: commands.Context, player: lavalink.player_manager.Player, playlist: Playlist
    ) -> Tuple[List[lavalink.Track], List[lavalink.Track], Playlist]:
        if playlist.url is None:
            return [], [], playlist
        results = {}
        updated_tracks = await self._playlist_tracks(
            ctx, player, dataclasses.Query.process_input(playlist.url)
        )
        if not updated_tracks:
            # No Tracks available on url Lets set it to none to avoid repeated calls here
            results["url"] = None
        if updated_tracks:  # Tracks have been updated
            results["tracks"] = updated_tracks

        old_tracks = playlist.tracks_obj
        new_tracks = [lavalink.Track(data=track) for track in updated_tracks]
        removed = list(set(old_tracks) - set(new_tracks))
        added = list(set(new_tracks) - set(old_tracks))
        if removed or added:
            await playlist.edit(results)

        return added, removed, playlist

    async def _playlist_check(self, ctx: commands.Context):
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                if await ctx.bot.is_owner(ctx.author):
                    msg += " " + _("Please check your console or logs for details.")
                await self._embed_msg(ctx, msg)
                return False
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
                    return False
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except IndexError:
                await self._embed_msg(
                    ctx, _("Connection to Lavalink has not yet been established.")
                )
                return False
            except AttributeError:
                await self._embed_msg(ctx, _("Connect to a voice channel first."))
                return False

        player = lavalink.get_player(ctx.guild.id)
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            await self._embed_msg(
                ctx, _("You must be in the voice channel to use the playlist command.")
            )
            return False
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        return True

    async def _playlist_tracks(
        self,
        ctx: commands.Context,
        player: lavalink.player_manager.Player,
        query: dataclasses.Query,
    ):
        search = query.is_search
        tracklist = []

        if query.is_spotify:
            try:
                if self.play_lock[ctx.message.guild.id]:
                    return await self._embed_msg(
                        ctx, _("Wait until the playlist has finished loading.")
                    )
            except KeyError:
                pass
            tracks = await self._get_spotify_tracks(ctx, query)
            if not tracks:
                return await self._embed_msg(ctx, _("Nothing found."))
            for track in tracks:
                track_obj = track_creator(player, other_track=track)
                tracklist.append(track_obj)
            self._play_lock(ctx, False)
        elif query.is_search:
            result, called_api = await self.music_cache.lavalink_query(ctx, player, query)
            tracks = result.tracks
            if not tracks:
                return await self._embed_msg(ctx, _("Nothing found."))
        else:
            result, called_api = await self.music_cache.lavalink_query(ctx, player, query)
            tracks = result.tracks

        if not search and len(tracklist) == 0:
            for track in tracks:
                track_obj = track_creator(player, other_track=track)
                tracklist.append(track_obj)
        elif len(tracklist) == 0:
            track_obj = track_creator(player, other_track=tracks[0])
            tracklist.append(track_obj)
        return tracklist

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def prev(self, ctx: commands.Context):
        """Skip to the start of the previously played track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        player = lavalink.get_player(ctx.guild.id)
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to skip tracks."))
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to skip the music.")
            )
        if player.fetch("prev_song") is None:
            return await self._embed_msg(ctx, _("No previous track."))
        else:
            track = player.fetch("prev_song")
            player.add(player.fetch("prev_requester"), track)
            self.bot.dispatch("red_audio_track_enqueue", player.channel.guild, track, ctx.author)
            queue_len = len(player.queue)
            bump_song = player.queue[-1]
            player.queue.insert(0, bump_song)
            player.queue.pop(queue_len)
            await player.skip()
            if any(
                x in player.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
            ):
                query = dataclasses.Query.process_input(player.current.uri)
                if player.current.title == "Unknown title":
                    description = "{}".format(query.track.to_string_hidden())
                else:
                    song = bold("{} - {}").format(player.current.author, player.current.title)
                    description = "{}\n{}".format(song, query.track.to_string_hidden())
            else:
                description = f"**[{player.current.title}]({player.current.uri})**"
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Replaying Track"),
                description=description,
            )
            await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def queue(self, ctx: commands.Context, *, page: int = 1):
        """List the songs in the queue."""

        async def _queue_menu(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                await ctx.send_help(self.queue)
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return None

        queue_controls = {"⬅": prev_page, "❌": close_menu, "➡": next_page, "ℹ": _queue_menu}

        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            if player.current:
                arrow = await draw_time(ctx)
                pos = lavalink.utils.format_time(player.position)
                if player.current.is_stream:
                    dur = "LIVE"
                else:
                    dur = lavalink.utils.format_time(player.current.length)
                if any(
                    x in player.current.uri
                    for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                ):
                    if player.current.title != "Unknown title":
                        song = "**{track.author} - {track.title}**\n{uri}\n"
                    else:
                        song = "{uri}\n"
                else:
                    song = "**[{track.title}]({track.uri})**\n"
                song += _("Requested by: **{track.requester}**")
                song += "\n\n{arrow}`{pos}`/`{dur}`"
                song = song.format(
                    track=player.current,
                    uri=dataclasses.LocalPath(player.current.uri).to_string_hidden()
                    if any(
                        x in player.current.uri
                        for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
                    )
                    else player.current.uri,
                    arrow=arrow,
                    pos=pos,
                    dur=dur,
                )

                embed = discord.Embed(
                    colour=await ctx.embed_colour(), title=_("Now Playing"), description=song
                )
                if await self.config.guild(ctx.guild).thumbnail() and player.current:
                    if player.current.thumbnail:
                        embed.set_thumbnail(url=player.current.thumbnail)

                shuffle = await self.config.guild(ctx.guild).shuffle()
                repeat = await self.config.guild(ctx.guild).repeat()
                autoplay = await self.config.guild(ctx.guild).auto_play() or self.owns_autoplay
                text = ""
                text += (
                    _("Auto-Play")
                    + ": "
                    + ("\N{WHITE HEAVY CHECK MARK}" if autoplay else "\N{CROSS MARK}")
                )
                text += (
                    (" | " if text else "")
                    + _("Shuffle")
                    + ": "
                    + ("\N{WHITE HEAVY CHECK MARK}" if shuffle else "\N{CROSS MARK}")
                )
                text += (
                    (" | " if text else "")
                    + _("Repeat")
                    + ": "
                    + ("\N{WHITE HEAVY CHECK MARK}" if repeat else "\N{CROSS MARK}")
                )
                embed.set_footer(text=text)

                return await ctx.send(embed=embed)
            return await self._embed_msg(ctx, _("There's nothing in the queue."))

        async with ctx.typing():
            len_queue_pages = math.ceil(len(player.queue) / 10)
            queue_page_list = []
            for page_num in range(1, len_queue_pages + 1):
                embed = await self._build_queue_page(ctx, player, page_num)
                queue_page_list.append(embed)
            if page > len_queue_pages:
                page = len_queue_pages
        return await menu(ctx, queue_page_list, queue_controls, page=(page - 1))

    async def _build_queue_page(
        self, ctx: commands.Context, player: lavalink.player_manager.Player, page_num
    ):
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        autoplay = await self.config.guild(ctx.guild).auto_play() or self.owns_autoplay

        queue_num_pages = math.ceil(len(player.queue) / 10)
        queue_idx_start = (page_num - 1) * 10
        queue_idx_end = queue_idx_start + 10
        queue_list = ""
        try:
            arrow = await draw_time(ctx)
        except AttributeError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        pos = lavalink.utils.format_time(player.position)

        if player.current.is_stream:
            dur = "LIVE"
        else:
            dur = lavalink.utils.format_time(player.current.length)

        if player.current.is_stream:
            queue_list += _("**Currently livestreaming:**\n")
            queue_list += "**[{current.title}]({current.uri})**\n".format(current=player.current)
            queue_list += _("Requested by: **{user}**").format(user=player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        elif any(
            x in player.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
        ):
            if player.current.title != "Unknown title":
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + "**{current.author} - {current.title}**".format(current=player.current),
                        dataclasses.LocalPath(player.current.uri).to_string_hidden(),
                        _("Requested by: **{user}**\n").format(user=player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
            else:
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + dataclasses.LocalPath(player.current.uri).to_string_hidden(),
                        _("Requested by: **{user}**\n").format(user=player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
        else:
            queue_list += _("Playing: ")
            queue_list += "**[{current.title}]({current.uri})**\n".format(current=player.current)
            queue_list += _("Requested by: **{user}**").format(user=player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        for i, track in enumerate(
            player.queue[queue_idx_start:queue_idx_end], start=queue_idx_start
        ):
            if len(track.title) > 40:
                track_title = str(track.title).replace("[", "")
                track_title = "{}...".format((track_title[:40]).rstrip(" "))
            else:
                track_title = track.title
            req_user = track.requester
            track_idx = i + 1
            if any(x in track.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
                if track.title == "Unknown title":
                    queue_list += f"`{track_idx}.` " + ", ".join(
                        (
                            bold(dataclasses.LocalPath(track.uri).to_string_hidden()),
                            _("requested by **{user}**\n").format(user=req_user),
                        )
                    )
                else:
                    queue_list += f"`{track_idx}.` **{track.author} - {track_title}**, " + _(
                        "requested by **{user}**\n"
                    ).format(user=req_user)
            else:
                queue_list += f"`{track_idx}.` **[{track_title}]({track.uri})**, "
                queue_list += _("requested by **{user}**\n").format(user=req_user)

        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title="Queue for " + ctx.guild.name,
            description=queue_list,
        )
        if await self.config.guild(ctx.guild).thumbnail() and player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
        queue_dur = await queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        text = _(
            "Page {page_num}/{total_pages} | {num_tracks} "
            "tracks, {num_remaining} remaining  |  \n\n"
        ).format(
            page_num=page_num,
            total_pages=queue_num_pages,
            num_tracks=len(player.queue) + 1,
            num_remaining=queue_total_duration,
        )
        text += (
            _("Auto-Play")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if autoplay else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Shuffle")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if shuffle else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Repeat")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if repeat else "\N{CROSS MARK}")
        )
        embed.set_footer(text=text)
        return embed

    @staticmethod
    async def _build_queue_search_list(queue_list, search_words):
        track_list = []
        queue_idx = 0
        for track in queue_list:
            queue_idx = queue_idx + 1
            if not match_url(track.uri):
                query = dataclasses.Query.process_input(track)
                if track.title == "Unknown title":
                    track_title = query.track.to_string_hidden()
                else:
                    track_title = "{} - {}".format(track.author, track.title)
            else:
                track_title = track.title

            song_info = {str(queue_idx): track_title}
            track_list.append(song_info)
        search_results = process.extract(search_words, track_list, limit=50)
        search_list = []
        for search, percent_match in search_results:
            for queue_position, title in search.items():
                if percent_match > 89:
                    search_list.append([queue_position, title])
        return search_list

    @staticmethod
    async def _build_queue_search_page(ctx: commands.Context, page_num, search_list):
        search_num_pages = math.ceil(len(search_list) / 10)
        search_idx_start = (page_num - 1) * 10
        search_idx_end = search_idx_start + 10
        track_match = ""
        for i, track in enumerate(
            search_list[search_idx_start:search_idx_end], start=search_idx_start
        ):
            track_idx = i + 1
            if type(track) is str:
                track_location = dataclasses.LocalPath(track).to_string_hidden()
                track_match += "`{}.` **{}**\n".format(track_idx, track_location)
            else:
                track_match += "`{}.` **{}**\n".format(track[0], track[1])
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Matching Tracks:"), description=track_match
        )
        embed.set_footer(
            text=(_("Page {page_num}/{total_pages}") + " | {num_tracks} tracks").format(
                page_num=page_num, total_pages=search_num_pages, num_tracks=len(search_list)
            )
        )
        return embed

    @queue.command(name="clear")
    @commands.guild_only()
    async def _queue_clear(self, ctx: commands.Context):
        """Clears the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to clear the queue."))
        player.queue.clear()
        await self._embed_msg(ctx, _("The queue has been cleared."))

    @queue.command(name="clean")
    @commands.guild_only()
    async def _queue_clean(self, ctx: commands.Context):
        """Removes songs from the queue if the requester is not in the voice channel."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to clean the queue."))
        clean_tracks = []
        removed_tracks = 0
        listeners = player.channel.members
        for track in player.queue:
            if track.requester in listeners:
                clean_tracks.append(track)
            else:
                removed_tracks += 1
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self._embed_msg(ctx, _("Removed 0 tracks."))
        else:
            await self._embed_msg(
                ctx,
                _(
                    "Removed {removed_tracks} tracks queued by members o"
                    "utside of the voice channel."
                ).format(removed_tracks=removed_tracks),
            )

    @queue.command(name="cleanself")
    @commands.guild_only()
    async def _queue_cleanself(self, ctx: commands.Context):
        """Removes all tracks you requested from the queue."""

        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))

        clean_tracks = []
        removed_tracks = 0
        for track in player.queue:
            if track.requester != ctx.author:
                clean_tracks.append(track)
            else:
                removed_tracks += 1
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self._embed_msg(ctx, _("Removed 0 tracks."))
        else:
            await self._embed_msg(
                ctx,
                _("Removed {removed_tracks} tracks queued by {member.display_name}.").format(
                    removed_tracks=removed_tracks, member=ctx.author
                ),
            )

    @queue.command(name="search")
    @commands.guild_only()
    async def _queue_search(self, ctx: commands.Context, *, search_words: str):
        """Search the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))

        search_list = await self._build_queue_search_list(player.queue, search_words)
        if not search_list:
            return await self._embed_msg(ctx, _("No matches."))

        len_search_pages = math.ceil(len(search_list) / 10)
        search_page_list = []
        for page_num in range(1, len_search_pages + 1):
            embed = await self._build_queue_search_page(ctx, page_num, search_list)
            search_page_list.append(embed)
        await menu(ctx, search_page_list, DEFAULT_CONTROLS)

    @queue.command(name="shuffle")
    @commands.guild_only()
    async def _queue_shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to clean the queue."))
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        try:
            if (
                not ctx.author.voice.channel.permissions_for(ctx.me).connect
                or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                and userlimit(ctx.author.voice.channel)
            ):
                return await self._embed_msg(
                    ctx, _("I don't have permission to connect to your channel.")
                )
            await lavalink.connect(ctx.author.voice.channel)
            player = lavalink.get_player(ctx.guild.id)
            player.store("connect", datetime.datetime.utcnow())
        except AttributeError:
            return await self._embed_msg(ctx, _("Connect to a voice channel first."))
        except IndexError:
            return await self._embed_msg(
                ctx, _("Connection to Lavalink has not yet been established.")
            )
        except KeyError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))

        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))

        player.force_shuffle(0)
        return await self._embed_msg(ctx, _("Queue has been shuffled."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def repeat(self, ctx: commands.Context):
        """Toggle repeat."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to toggle repeat."))
        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You must be in the voice channel to toggle repeat.")
                )

        autoplay = await self.config.guild(ctx.guild).auto_play()
        repeat = await self.config.guild(ctx.guild).repeat()
        msg = ""
        msg += _("Repeat tracks: {true_or_false}.").format(
            true_or_false=_("Enabled") if not repeat else _("Disabled")
        )
        await self.config.guild(ctx.guild).repeat.set(not repeat)
        if repeat is not True and autoplay is True:
            msg += _("\nAuto-play has been disabled.")
            await self.config.guild(ctx.guild).auto_play.set(False)

        embed = discord.Embed(
            title=_("Repeat settings changed"), description=msg, colour=await ctx.embed_colour()
        )
        await ctx.send(embed=embed)
        if self._player_check(ctx):
            await self._data_check(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def remove(self, ctx: commands.Context, index: int):
        """Remove a specific track number from the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, _("Nothing queued."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to remove tracks."))
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to manage the queue.")
            )
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(
                ctx, _("Song number must be greater than 1 and within the queue limit.")
            )
        index -= 1
        removed = player.queue.pop(index)
        if any(x in removed.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
            local_path = dataclasses.LocalPath(removed.uri).to_string_hidden()
            if removed.title == "Unknown title":
                removed_title = local_path
            else:
                removed_title = "{} - {}\n{}".format(removed.author, removed.title, local_path)
        else:
            removed_title = removed.title
        await self._embed_msg(
            ctx, _("Removed {track} from the queue.").format(track=removed_title)
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def search(self, ctx: commands.Context, *, query: str):
        """Pick a track with a search.

        Use `[p]search list <search term>` to queue all tracks found
        on YouTube. `[p]search sc <search term>` will search SoundCloud
        instead of YouTube.
        """

        async def _search_menu(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                await self._search_button_action(ctx, tracks, emoji, page)
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return None

        search_controls = {
            "1⃣": _search_menu,
            "2⃣": _search_menu,
            "3⃣": _search_menu,
            "4⃣": _search_menu,
            "5⃣": _search_menu,
            "⬅": prev_page,
            "❌": close_menu,
            "➡": next_page,
        }

        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                if await ctx.bot.is_owner(ctx.author):
                    msg += " " + _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, msg)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, _("Connect to a voice channel first."))
            except IndexError:
                return await self._embed_msg(
                    ctx, _("Connection to Lavalink has not yet been established.")
                )
        player = lavalink.get_player(ctx.guild.id)
        guild_data = await self.config.guild(ctx.guild).all()
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to enqueue tracks.")
            )
        await self._eq_check(ctx, player)
        await self._data_check(ctx)

        if not isinstance(query, list):
            query = dataclasses.Query.process_input(query)
            if query.invoked_from == "search list" or query.invoked_from == "local folder":
                if query.invoked_from == "search list":
                    result, called_api = await self.music_cache.lavalink_query(ctx, player, query)
                    tracks = result.tracks
                else:
                    tracks = await self._folder_tracks(ctx, player, query)
                if not tracks:
                    embed = discord.Embed(
                        title=_("Nothing found."), colour=await ctx.embed_colour()
                    )
                    if await self.config.use_external_lavalink() and query.is_local:
                        embed.description = _(
                            "Local tracks will not work "
                            "if the `Lavalink.jar` cannot see the track.\n"
                            "This may be due to permissions or because Lavalink.jar is being run "
                            "in a different machine than the local tracks."
                        )
                    return await ctx.send(embed=embed)
                queue_dur = await queue_duration(ctx)
                queue_total_duration = lavalink.utils.format_time(queue_dur)

                track_len = 0
                empty_queue = not player.queue
                for track in tracks:
                    if not await is_allowed(
                        ctx.guild,
                        (
                            f"{track.title} {track.author} {track.uri} "
                            f"{str(dataclasses.Query.process_input(track))}"
                        ),
                    ):
                        log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
                        continue
                    elif guild_data["maxlength"] > 0:
                        if track_limit(track, guild_data["maxlength"]):
                            track_len += 1
                            player.add(ctx.author, track)
                            self.bot.dispatch(
                                "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                            )
                    else:
                        track_len += 1
                        player.add(ctx.author, track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                        )
                    if not player.current:
                        await player.play()
                player.maybe_shuffle(0 if empty_queue else 1)
                if len(tracks) > track_len:
                    maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                        bad_tracks=(len(tracks) - track_len)
                    )
                else:
                    maxlength_msg = ""
                songembed = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_("Queued {num} track(s).{maxlength_msg}").format(
                        num=track_len, maxlength_msg=maxlength_msg
                    ),
                )
                if not guild_data["shuffle"] and queue_dur > 0:
                    songembed.set_footer(
                        text=_(
                            "{time} until start of search playback: starts at #{position} in queue"
                        ).format(time=queue_total_duration, position=len(player.queue) + 1)
                    )
                return await ctx.send(embed=songembed)
            elif query.is_local and query.single_track:
                tracks = await self._folder_list(ctx, query)
            elif query.is_local and query.is_album:
                if ctx.invoked_with == "folder":
                    return await self._local_play_all(ctx, query, from_search=True)
                else:
                    tracks = await self._folder_list(ctx, query)
            else:
                result, called_api = await self.music_cache.lavalink_query(ctx, player, query)
                tracks = result.tracks
            if not tracks:
                embed = discord.Embed(title=_("Nothing found."), colour=await ctx.embed_colour())
                if await self.config.use_external_lavalink() and query.is_local:
                    embed.description = _(
                        "Local tracks will not work "
                        "if the `Lavalink.jar` cannot see the track.\n"
                        "This may be due to permissions or because Lavalink.jar is being run "
                        "in a different machine than the local tracks."
                    )
                return await ctx.send(embed=embed)
        else:
            tracks = query

        len_search_pages = math.ceil(len(tracks) / 5)
        search_page_list = []
        for page_num in range(1, len_search_pages + 1):
            embed = await self._build_search_page(ctx, tracks, page_num)
            search_page_list.append(embed)

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await menu(ctx, search_page_list, DEFAULT_CONTROLS)

        await menu(ctx, search_page_list, search_controls)

    async def _search_button_action(self, ctx: commands.Context, tracks, emoji, page):
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                if await ctx.bot.is_owner(ctx.author):
                    msg += " " + _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, msg)
            try:
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, _("Connect to a voice channel first."))
            except IndexError:
                return await self._embed_msg(
                    ctx, _("Connection to Lavalink has not yet been established.")
                )
        player = lavalink.get_player(ctx.guild.id)
        guild_data = await self.config.guild(ctx.guild).all()
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        try:
            if emoji == "1⃣":
                search_choice = tracks[0 + (page * 5)]
            elif emoji == "2⃣":
                search_choice = tracks[1 + (page * 5)]
            elif emoji == "3⃣":
                search_choice = tracks[2 + (page * 5)]
            elif emoji == "4⃣":
                search_choice = tracks[3 + (page * 5)]
            elif emoji == "5⃣":
                search_choice = tracks[4 + (page * 5)]
            else:
                search_choice = tracks[0 + (page * 5)]
                # TODO: verify this does not break exit and arrows
        except IndexError:
            search_choice = tracks[-1]
        try:
            if any(
                x in search_choice.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
            ):

                localtrack = dataclasses.LocalPath(search_choice.uri)
                if search_choice.title != "Unknown title":
                    description = "**{} - {}**\n{}".format(
                        search_choice.author, search_choice.title, localtrack.to_string_hidden()
                    )
                else:
                    description = localtrack.to_string_hidden()
            else:
                description = "**[{}]({})**".format(search_choice.title, search_choice.uri)

        except AttributeError:
            search_choice = dataclasses.Query.process_input(search_choice)
            if search_choice.track.exists() and search_choice.track.is_dir():
                return await ctx.invoke(self.search, query=search_choice)
            elif search_choice.track.exists() and search_choice.track.is_file():
                search_choice.invoked_from = "localtrack"
            return await ctx.invoke(self.play, query=search_choice)

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Track Enqueued"), description=description
        )
        queue_dur = await queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        if not await is_allowed(
            ctx.guild,
            (
                f"{search_choice.title} {search_choice.author} {search_choice.uri} "
                f"{str(dataclasses.Query.process_input(search_choice))}"
            ),
        ):
            log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
            self._play_lock(ctx, False)
            return await self._embed_msg(ctx, _("This track is not allowed in this server."))
        elif guild_data["maxlength"] > 0:

            if track_limit(search_choice.length, guild_data["maxlength"]):
                player.add(ctx.author, search_choice)
                player.maybe_shuffle()
                self.bot.dispatch(
                    "red_audio_track_enqueue", player.channel.guild, search_choice, ctx.author
                )
            else:
                return await self._embed_msg(ctx, _("Track exceeds maximum length."))
        else:
            player.add(ctx.author, search_choice)
            player.maybe_shuffle()
            self.bot.dispatch(
                "red_audio_track_enqueue", player.channel.guild, search_choice, ctx.author
            )

        if not guild_data["shuffle"] and queue_dur > 0:
            embed.set_footer(
                text=_("{time} until track playback: #{position} in queue").format(
                    time=queue_total_duration, position=len(player.queue) + 1
                )
            )

        if not player.current:
            await player.play()
        await ctx.send(embed=embed)

    @staticmethod
    async def _build_search_page(ctx: commands.Context, tracks, page_num):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        command = ctx.invoked_with
        folder = False
        for i, track in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            try:
                if any(x in track.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
                    search_list += "`{0}.` **{1}**\n[{2}]\n".format(
                        search_track_num,
                        track.title,
                        dataclasses.LocalPath(track.uri).to_string_hidden(),
                    )
                else:
                    search_list += "`{0}.` **[{1}]({2})**\n".format(
                        search_track_num, track.title, track.uri
                    )
            except AttributeError:
                # query = Query.process_input(track)
                track = dataclasses.Query.process_input(track)
                if (
                    any(x in str(track) for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"])
                    and command != "search"
                ):
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
                    folder = True
                elif command == "search":
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
                else:
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
        if hasattr(tracks[0], "uri"):
            title = _("Tracks Found:")
            footer = _("search results")
        elif folder:
            title = _("Folders Found:")
            footer = _("local folders")
        else:
            title = _("Files Found:")
            footer = _("local tracks")
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=(_("Page {page_num}/{total_pages}") + " | {num_results} {footer}").format(
                page_num=page_num,
                total_pages=search_num_pages,
                num_results=len(tracks),
                footer=footer,
            )
        )
        return embed

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def seek(self, ctx: commands.Context, seconds: Union[int, str]):
        """Seek ahead or behind on a track by seconds or a to a specific time.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`)."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        is_alone = await self._is_alone(ctx, ctx.author)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)

        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self._embed_msg(ctx, _("You must be in the voice channel to use seek."))

        if vote_enabled and not can_skip and not is_alone:
            return await self._embed_msg(
                ctx, _("There are other people listening - vote to skip instead.")
            )

        if dj_enabled and not (can_skip or is_requester) and not is_alone:
            return await self._embed_msg(
                ctx, _("You need the DJ role or be the track requester to use seek.")
            )

        if player.current:
            if player.current.is_stream:
                return await self._embed_msg(ctx, _("Can't seek on a stream."))
            else:
                try:
                    int(seconds)
                    abs_position = False
                except ValueError:
                    abs_position = True
                    seconds = time_convert(seconds)
                if seconds == 0:
                    return await self._embed_msg(ctx, _("Invalid input for the time to seek."))
                if not abs_position:
                    time_sec = int(seconds) * 1000
                    seek = player.position + time_sec
                    if seek <= 0:
                        await self._embed_msg(
                            ctx, _("Moved {num_seconds}s to 00:00:00").format(num_seconds=seconds)
                        )
                    else:
                        await self._embed_msg(
                            ctx,
                            _("Moved {num_seconds}s to {time}").format(
                                num_seconds=seconds, time=lavalink.utils.format_time(seek)
                            ),
                        )
                    await player.seek(seek)
                else:
                    await self._embed_msg(
                        ctx,
                        _("Moved to {time}").format(
                            time=lavalink.utils.format_time(seconds * 1000)
                        ),
                    )
                    await player.seek(seconds * 1000)
        else:
            await self._embed_msg(ctx, _("Nothing playing."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def shuffle(self, ctx: commands.Context):
        """Toggle shuffle."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to toggle shuffle."))
        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You must be in the voice channel to toggle shuffle.")
                )

        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self.config.guild(ctx.guild).shuffle.set(not shuffle)
        await self._embed_msg(
            ctx,
            _("Shuffle tracks: {true_or_false}.").format(
                true_or_false=_("Enabled") if not shuffle else _("Disabled")
            ),
        )
        if self._player_check(ctx):
            await self._data_check(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def sing(self, ctx: commands.Context):
        """Make Red sing one of her songs."""
        ids = (
            "zGTkAVsrfg8",
            "cGMWL8cOeAU",
            "vFrjMq4aL-g",
            "WROI5WYBU_A",
            "41tIUr_ex3g",
            "f9O2Rjn1azc",
        )
        url = f"https://www.youtube.com/watch?v={random.choice(ids)}"
        await ctx.invoke(self.play, query=url)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def skip(self, ctx: commands.Context, skip_to_track: int = None):
        """Skip to the next track, or to a given track number."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to skip the music.")
            )
        if not player.current:
            return await self._embed_msg(ctx, _("Nothing playing."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        is_alone = await self._is_alone(ctx, ctx.author)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)

        if dj_enabled and not vote_enabled:
            if not (can_skip or is_requester) and not is_alone:
                return await self._embed_msg(
                    ctx, _("You need the DJ role or be the track requester to skip tracks.")
                )
            if (
                is_requester
                and not can_skip
                and isinstance(skip_to_track, int)
                and skip_to_track > 1
            ):
                return await self._embed_msg(ctx, _("You can only skip the current track."))

        if vote_enabled:
            if not can_skip:
                if skip_to_track is not None:
                    return await self._embed_msg(
                        ctx, _("Can't skip to a specific track in vote mode without the DJ role.")
                    )
                if ctx.author.id in self.skip_votes[ctx.message.guild]:
                    self.skip_votes[ctx.message.guild].remove(ctx.author.id)
                    reply = _("I removed your vote to skip.")
                else:
                    self.skip_votes[ctx.message.guild].append(ctx.author.id)
                    reply = _("You voted to skip.")

                num_votes = len(self.skip_votes[ctx.message.guild])
                vote_mods = []
                for member in player.channel.members:
                    can_skip = await self._can_instaskip(ctx, member)
                    if can_skip:
                        vote_mods.append(member)
                num_members = len(player.channel.members) - len(vote_mods)
                vote = int(100 * num_votes / num_members)
                percent = await self.config.guild(ctx.guild).vote_percent()
                if vote >= percent:
                    self.skip_votes[ctx.message.guild] = []
                    await self._embed_msg(ctx, _("Vote threshold met."))
                    return await self._skip_action(ctx)
                else:
                    reply += _(
                        " Votes: {num_votes}/{num_members}"
                        " ({cur_percent}% out of {required_percent}% needed)"
                    ).format(
                        num_votes=humanize_number(num_votes),
                        num_members=humanize_number(num_members),
                        cur_percent=vote,
                        required_percent=percent,
                    )
                    return await self._embed_msg(ctx, reply)
            else:
                return await self._skip_action(ctx, skip_to_track)
        else:
            return await self._skip_action(ctx, skip_to_track)

    async def _can_instaskip(self, ctx: commands.Context, member: discord.Member):

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()

        if member.bot:
            return True

        if member.id == ctx.guild.owner_id:
            return True

        if dj_enabled:
            if await self._has_dj_role(ctx, member):
                return True

        if await ctx.bot.is_owner(member):
            return True

        if await ctx.bot.is_mod(member):
            return True

        if await self._channel_check(ctx):
            return True

        return False

    async def _is_alone(self, ctx: commands.Context, member: discord.Member):
        try:
            user_voice = ctx.guild.get_member(member.id).voice
            bot_voice = ctx.guild.get_member(self.bot.user.id).voice
            nonbots = sum(not m.bot for m in user_voice.channel.members)
            if user_voice.channel != bot_voice.channel:
                nonbots = nonbots + 1
        except AttributeError:
            if ctx.guild.get_member(self.bot.user.id).voice is not None:
                nonbots = sum(
                    not m.bot for m in ctx.guild.get_member(self.bot.user.id).voice.channel.members
                )
                if nonbots == 1:
                    nonbots = 2
            elif ctx.guild.get_member(member.id).voice.channel.members == 1:
                nonbots = 1
            else:
                nonbots = 0
        return nonbots <= 1

    async def _has_dj_role(self, ctx: commands.Context, member: discord.Member):
        dj_role_obj = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
        if dj_role_obj in ctx.guild.get_member(member.id).roles:
            return True
        return False

    @staticmethod
    async def is_requester(ctx: commands.Context, member: discord.Member):
        try:
            player = lavalink.get_player(ctx.guild.id)
            log.debug(f"Current requester is {player.current}")
            if player.current.requester.id == member.id:
                return True
            return False
        except Exception as e:
            log.error(e)
        return False

    async def _skip_action(self, ctx: commands.Context, skip_to_track: int = None):
        player = lavalink.get_player(ctx.guild.id)
        autoplay = await self.config.guild(player.channel.guild).auto_play() or self.owns_autoplay
        if not player.current or (not player.queue and not autoplay):
            try:
                pos, dur = player.position, player.current.length
            except AttributeError:
                return await self._embed_msg(ctx, _("There's nothing in the queue."))
            time_remain = lavalink.utils.format_time(dur - pos)
            if player.current.is_stream:
                embed = discord.Embed(
                    colour=await ctx.embed_colour(), title=_("There's nothing in the queue.")
                )
                embed.set_footer(
                    text=_("Currently livestreaming {track}").format(track=player.current.title)
                )
            else:
                embed = discord.Embed(
                    colour=await ctx.embed_colour(), title=_("There's nothing in the queue.")
                )
                embed.set_footer(
                    text=_("{time} left on {track}").format(
                        time=time_remain, track=player.current.title
                    )
                )
            return await ctx.send(embed=embed)
        elif autoplay and not player.queue:
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Track Skipped"),
                description=await get_description(player.current),
            )
            await ctx.send(embed=embed)
            return await player.skip()

        queue_to_append = []
        if skip_to_track is not None and skip_to_track != 1:
            if skip_to_track < 1:
                return await self._embed_msg(
                    ctx, _("Track number must be equal to or greater than 1.")
                )
            elif skip_to_track > len(player.queue):
                return await self._embed_msg(
                    ctx,
                    _(
                        "There are only {queuelen} songs currently queued.".format(
                            queuelen=len(player.queue)
                        )
                    ),
                )
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("{skip_to_track} Tracks Skipped".format(skip_to_track=skip_to_track)),
            )
            await ctx.send(embed=embed)
            if player.repeat:
                queue_to_append = player.queue[0 : min(skip_to_track - 1, len(player.queue) - 1)]
            player.queue = player.queue[
                min(skip_to_track - 1, len(player.queue) - 1) : len(player.queue)
            ]
        else:
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Track Skipped"),
                description=await get_description(player.current),
            )
            await ctx.send(embed=embed)
        self.bot.dispatch("red_audio_skip_track", player.channel.guild, player.current, ctx.author)
        await player.play()
        player.queue += queue_to_append

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def stop(self, ctx: commands.Context):
        """Stop playback and clear the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to stop the music.")
            )
        if vote_enabled or vote_enabled and dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(
                    ctx, _("There are other people listening - vote to skip instead.")
                )
        if dj_enabled and not vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to stop the music."))
        if (
            player.is_playing
            or (not player.is_playing and player.paused)
            or player.queue
            or getattr(player.current, "extras", {}).get("autoplay")
        ):
            eq = player.fetch("eq")
            if eq:
                await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
            player.queue = []
            player.store("playing_song", None)
            player.store("prev_requester", None)
            player.store("prev_song", None)
            player.store("requester", None)
            await player.stop()
            await self._embed_msg(ctx, _("Stopping..."))

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True)
    async def summon(self, ctx: commands.Context):
        """Summon the bot to a voice channel."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to summon the bot."))
        try:
            if (
                not ctx.author.voice.channel.permissions_for(ctx.me).connect
                or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                and userlimit(ctx.author.voice.channel)
            ):
                return await self._embed_msg(
                    ctx, _("I don't have permission to connect to your channel.")
                )
            if not self._player_check(ctx):
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            else:
                player = lavalink.get_player(ctx.guild.id)
                if ctx.author.voice.channel == player.channel:
                    return
                await player.move_to(ctx.author.voice.channel)
        except AttributeError:
            return await self._embed_msg(ctx, _("Connect to a voice channel first."))
        except IndexError:
            return await self._embed_msg(
                ctx, _("Connection to Lavalink has not yet been established.")
            )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def volume(self, ctx: commands.Context, vol: int = None):
        """Set the volume, 1% - 150%."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not vol:
            vol = await self.config.guild(ctx.guild).volume()
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Current Volume:"),
                description=str(vol) + "%",
            )
            if not self._player_check(ctx):
                embed.set_footer(text=_("Nothing playing."))
            return await ctx.send(embed=embed)
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You must be in the voice channel to change the volume.")
                )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to change the volume."))
        if vol < 0:
            vol = 0
        if vol > 150:
            vol = 150
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check(ctx):
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        else:
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check(ctx):
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Volume:"), description=str(vol) + "%"
        )
        if not self._player_check(ctx):
            embed.set_footer(text=_("Nothing playing."))
        await ctx.send(embed=embed)

    @commands.group(aliases=["llset"])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @checks.is_owner()
    async def llsetup(self, ctx: commands.Context):
        """Lavalink server configuration options."""
        pass

    @llsetup.command()
    async def external(self, ctx: commands.Context):
        """Toggle using external lavalink servers."""
        external = await self.config.use_external_lavalink()
        await self.config.use_external_lavalink.set(not external)

        if external:
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("External lavalink server: {true_or_false}.").format(
                    true_or_false=_("Enabled") if not external else _("Disabled")
                ),
            )
            await ctx.send(embed=embed)
        else:
            if self._manager is not None:
                await self._manager.shutdown()
            await self._embed_msg(
                ctx,
                _("External lavalink server: {true_or_false}.").format(
                    true_or_false=_("Enabled") if not external else _("Disabled")
                ),
            )

        self._restart_connect()

    @llsetup.command()
    async def host(self, ctx: commands.Context, host: str):
        """Set the lavalink server host."""
        await self.config.host.set(host)
        if await self._check_external():
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Host set to {host}.").format(host=host)
            )
            embed.set_footer(text=_("External lavalink server set to True."))
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, _("Host set to {host}.").format(host=host))

        self._restart_connect()

    @llsetup.command()
    async def password(self, ctx: commands.Context, password: str):
        """Set the lavalink server password."""
        await self.config.password.set(str(password))
        if await self._check_external():
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Server password set to {password}.").format(password=password),
            )
            embed.set_footer(text=_("External lavalink server set to True."))
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(
                ctx, _("Server password set to {password}.").format(password=password)
            )

        self._restart_connect()

    @llsetup.command()
    async def restport(self, ctx: commands.Context, rest_port: int):
        """Set the lavalink REST server port."""
        await self.config.rest_port.set(rest_port)
        if await self._check_external():
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("REST port set to {port}.").format(port=rest_port),
            )
            embed.set_footer(text=_("External lavalink server set to True."))
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, _("REST port set to {port}.").format(port=rest_port))

        self._restart_connect()

    @llsetup.command()
    async def wsport(self, ctx: commands.Context, ws_port: int):
        """Set the lavalink websocket server port."""
        await self.config.ws_port.set(ws_port)
        if await self._check_external():
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Websocket port set to {port}.").format(port=ws_port),
            )
            embed.set_footer(text=_("External lavalink server set to True."))
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, _("Websocket port set to {port}.").format(port=ws_port))

        self._restart_connect()

    @staticmethod
    async def _apply_gain(guild_id: int, band, gain):
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": band, "gain": gain}],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    @staticmethod
    async def _apply_gains(guild_id: int, gains):
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": x, "gain": y} for x, y in enumerate(gains)],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    async def _channel_check(self, ctx: commands.Context):
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return False
        try:
            in_channel = sum(
                not m.bot for m in ctx.guild.get_member(self.bot.user.id).voice.channel.members
            )
        except AttributeError:
            return False

        if not ctx.author.voice:
            user_channel = None
        else:
            user_channel = ctx.author.voice.channel

        if in_channel == 0 and user_channel:
            if (
                (player.channel != user_channel)
                and not player.current
                and player.position == 0
                and len(player.queue) == 0
            ):
                await player.move_to(user_channel)
                return True
        else:
            return False

    async def _check_api_tokens(self):
        spotify = await self.bot.get_shared_api_tokens("spotify")
        youtube = await self.bot.get_shared_api_tokens("youtube")
        return {
            "spotify_client_id": spotify.get("client_id", ""),
            "spotify_client_secret": spotify.get("client_secret", ""),
            "youtube_api": youtube.get("api_key", ""),
        }

    async def _check_external(self):
        external = await self.config.use_external_lavalink()
        if not external:
            if self._manager is not None:
                await self._manager.shutdown()
            await self.config.use_external_lavalink.set(True)
            return True
        else:
            return False

    async def _clear_react(self, message: discord.Message, emoji: dict = None):
        """Non blocking version of clear_react"""
        return self.bot.loop.create_task(clear_react(self.bot, message, emoji))

    async def _currency_check(self, ctx: commands.Context, jukebox_price: int):
        jukebox = await self.config.guild(ctx.guild).jukebox()
        if jukebox and not await self._can_instaskip(ctx, ctx.author):
            try:
                await bank.withdraw_credits(ctx.author, jukebox_price)
                return True
            except ValueError:
                credits_name = await bank.get_currency_name(ctx.guild)
                await self._embed_msg(
                    ctx,
                    _("Not enough {currency} ({required_credits} required).").format(
                        currency=credits_name, required_credits=humanize_number(jukebox_price)
                    ),
                )
                return False
        else:
            return True

    async def _data_check(self, ctx: commands.Context):
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        volume = await self.config.guild(ctx.guild).volume()
        player.repeat = repeat
        player.shuffle = shuffle
        if player.volume != volume:
            await player.set_volume(volume)

    async def disconnect_timer(self):
        stop_times = {}
        pause_times = {}
        while True:
            for p in lavalink.all_players():
                server = p.channel.guild

                if [self.bot.user] == p.channel.members:
                    stop_times.setdefault(server.id, time.time())
                    pause_times.setdefault(server.id, time.time())
                else:
                    stop_times.pop(server.id, None)
                    if p.paused and server.id in pause_times:
                        try:
                            await p.pause(False)
                        except Exception:
                            log.error(
                                "Exception raised in Audio's emptypause_timer.", exc_info=True
                            )
                        finally:
                            pause_times.pop(server.id, None)
                    else:
                        pause_times.pop(server.id, None)
            servers = stop_times.copy()
            servers.update(pause_times)
            for sid in servers:
                server_obj = self.bot.get_guild(sid)
                if sid in stop_times and await self.config.guild(server_obj).emptydc_enabled():
                    emptydc_timer = await self.config.guild(server_obj).emptydc_timer()
                    if (time.time() - stop_times[sid]) >= emptydc_timer:
                        stop_times.pop(sid)
                        try:
                            await lavalink.get_player(sid).disconnect()
                        except Exception:
                            log.error("Exception raised in Audio's emptydc_timer.", exc_info=True)
                            pass
                elif (
                    sid in pause_times and await self.config.guild(server_obj).emptypause_enabled()
                ):
                    emptypause_timer = await self.config.guild(server_obj).emptypause_timer()
                    if (time.time() - pause_times.get(sid)) >= emptypause_timer:
                        try:
                            await lavalink.get_player(sid).pause()
                        except Exception:
                            log.error(
                                "Exception raised in Audio's emptypause_timer.", exc_info=True
                            )
            await asyncio.sleep(5)

    @staticmethod
    async def _embed_msg(ctx: commands.Context, title: str):
        embed = discord.Embed(colour=await ctx.embed_colour(), title=title)
        await ctx.send(embed=embed)

    async def _eq_check(self, ctx: commands.Context, player: lavalink.Player):
        eq = player.fetch("eq", Equalizer())

        config_bands = await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands()
        if not config_bands:
            config_bands = eq.bands
            await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)

        if eq.bands != config_bands:
            band_num = list(range(0, eq._band_count))
            band_value = config_bands
            eq_dict = {}
            for k, v in zip(band_num, band_value):
                eq_dict[k] = v
            for band, value in eq_dict.items():
                eq.set_gain(band, value)
            player.store("eq", eq)
            await self._apply_gains(ctx.guild.id, config_bands)

    async def _eq_interact(
        self, ctx: commands.Context, player: lavalink.Player, eq, message, selected
    ):
        player.store("eq", eq)
        emoji = {
            "far_left": "◀",
            "one_left": "⬅",
            "max_output": "⏫",
            "output_up": "🔼",
            "output_down": "🔽",
            "min_output": "⏬",
            "one_right": "➡",
            "far_right": "▶",
            "reset": "⏺",
            "info": "ℹ",
        }
        selector = f'{" " * 8}{"   " * selected}^^'
        try:
            await message.edit(content=box(f"{eq.visualise()}\n{selector}", lang="ini"))
        except discord.errors.NotFound:
            return
        try:
            react_emoji, react_user = await self._get_eq_reaction(ctx, message, emoji)
        except TypeError:
            return

        if not react_emoji:
            await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
            await self._clear_react(message, emoji)

        if react_emoji == "⬅":
            await remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, eq, message, max(selected - 1, 0))

        if react_emoji == "➡":
            await remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, eq, message, min(selected + 1, 14))

        if react_emoji == "🔼":
            await remove_react(message, react_emoji, react_user)
            _max = "{:.2f}".format(min(eq.get_gain(selected) + 0.1, 1.0))
            eq.set_gain(selected, float(_max))
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "🔽":
            await remove_react(message, react_emoji, react_user)
            _min = "{:.2f}".format(max(eq.get_gain(selected) - 0.1, -0.25))
            eq.set_gain(selected, float(_min))
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "⏫":
            await remove_react(message, react_emoji, react_user)
            _max = 1.0
            eq.set_gain(selected, _max)
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "⏬":
            await remove_react(message, react_emoji, react_user)
            _min = -0.25
            eq.set_gain(selected, _min)
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "◀":
            await remove_react(message, react_emoji, react_user)
            selected = 0
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "▶":
            await remove_react(message, react_emoji, react_user)
            selected = 14
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "⏺":
            await remove_react(message, react_emoji, react_user)
            for band in range(eq._band_count):
                eq.set_gain(band, 0.0)
            await self._apply_gains(ctx.guild.id, eq.bands)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "ℹ":
            await remove_react(message, react_emoji, react_user)
            await ctx.send_help(self.eq)
            await self._eq_interact(ctx, player, eq, message, selected)

    @staticmethod
    async def _eq_msg_clear(eq_message: discord.Message):
        if eq_message is not None:
            with contextlib.suppress(discord.HTTPException):
                await eq_message.delete()

    async def _get_eq_reaction(self, ctx: commands.Context, message: discord.Message, emoji):
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == message.id
                and u.id == ctx.author.id
                and r.emoji in emoji.values(),
                timeout=30,
            )
        except asyncio.TimeoutError:
            await self._clear_react(message, emoji)
            return None
        else:
            return reaction.emoji, user

    def _play_lock(self, ctx: commands.Context, tf):
        if tf:
            self.play_lock[ctx.message.guild.id] = True
        else:
            self.play_lock[ctx.message.guild.id] = False

    def _player_check(self, ctx: commands.Context):
        if self._connection_aborted:
            return False
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except IndexError:
            return False
        except KeyError:
            return False

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

    def cog_unload(self):
        if not self._cleaned_up:
            self.bot.dispatch("red_audio_unload", self)
            self.session.detach()
            self.bot.loop.create_task(self._close_database())
            if self._disconnect_task:
                self._disconnect_task.cancel()

            if self._connect_task:
                self._connect_task.cancel()

            lavalink.unregister_event_listener(self.event_handler)
            self.bot.loop.create_task(lavalink.close())
            if self._manager is not None:
                self.bot.loop.create_task(self._manager.shutdown())

            self._cleaned_up = True

    @bump.error
    @disconnect.error
    @genre.error
    @local_folder.error
    @local_play.error
    @local_search.error
    @play.error
    @prev.error
    @search.error
    @_playlist_append.error
    @_playlist_save.error
    @_playlist_update.error
    @_playlist_upload.error
    async def _clear_lock_on_error(self, ctx: commands.Context, error):
        # TODO: Change this in a future PR
        # FIXME: This seems to be consuming tracebacks and not adding them to last traceback
        # which is handled by on_command_error
        # Make it so that this can be used to show user friendly errors
        if not isinstance(
            getattr(error, "original", error),
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandOnCooldown,
            ),
        ):
            self._play_lock(ctx, False)
            await self.music_cache.run_tasks(ctx)
            message = "Error in command '{}'. Check your console or logs for details.".format(
                ctx.command.qualified_name
            )
            await ctx.send(inline(message))
            exception_log = "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            self.bot._last_exception = exception_log

        await ctx.bot.on_command_error(
            ctx, getattr(error, "original", error), unhandled_by_cog=True
        )

    async def cog_after_invoke(self, ctx: commands.Context):
        await self._process_db(ctx)

    async def _process_db(self, ctx: commands.Context):
        await self.music_cache.run_tasks(ctx)

    async def _close_database(self):
        await self.music_cache.run_all_pending_tasks()
        await self.music_cache.close()

    __del__ = cog_unload
