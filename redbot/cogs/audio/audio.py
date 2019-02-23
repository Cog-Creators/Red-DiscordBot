import aiohttp
import asyncio
import datetime
import discord
from fuzzywuzzy import process
import heapq
import lavalink
import math
import os
import random
import re
import time
import redbot.core
from redbot.core import Config, commands, checks, bank
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import bold, box
from redbot.core.utils.menus import (
    menu,
    DEFAULT_CONTROLS,
    prev_page,
    next_page,
    close_menu,
    start_adding_reactions,
)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from urllib.parse import urlparse
from .manager import shutdown_lavalink_server, start_lavalink_server, maybe_download_lavalink

_ = Translator("Audio", __file__)

__version__ = "0.0.8"
__author__ = ["aikaterna", "billy/bollo/ati"]


@cog_i18n(_)
class Audio(commands.Cog):
    """Play audio through voice channels."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 2711759130, force_registration=True)

        default_global = {
            "host": "localhost",
            "rest_port": "2333",
            "ws_port": "2332",
            "password": "youshallnotpass",
            "status": False,
            "current_version": redbot.core.VersionInfo.from_str("3.0.0a0").to_json(),
            "use_external_lavalink": False,
            "restrict": True,
        }

        default_guild = {
            "dj_enabled": False,
            "dj_role": None,
            "emptydc_enabled": False,
            "emptydc_timer": 0,
            "jukebox": False,
            "jukebox_price": 0,
            "maxlength": 0,
            "playlists": {},
            "notify": False,
            "repeat": False,
            "shuffle": False,
            "thumbnail": False,
            "volume": 100,
            "vote_enabled": False,
            "vote_percent": 0,
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.skip_votes = {}
        self.session = aiohttp.ClientSession()
        self._connect_task = None
        self._disconnect_task = None
        self._cleaned_up = False

    async def initialize(self):
        self._restart_connect()
        self._disconnect_task = self.bot.loop.create_task(self.disconnect_timer())
        lavalink.register_event_listener(self.event_handler)

    def _restart_connect(self):
        if self._connect_task:
            self._connect_task.cancel()

        self._connect_task = self.bot.loop.create_task(self.attempt_connect())

    async def attempt_connect(self, timeout: int = 30):
        while True:  # run until success
            external = await self.config.use_external_lavalink()
            if not external:
                shutdown_lavalink_server()
                await maybe_download_lavalink(self.bot.loop, self)
                await start_lavalink_server(self.bot.loop)
            try:
                host = await self.config.host()
                password = await self.config.password()
                rest_port = await self.config.rest_port()
                ws_port = await self.config.ws_port()

                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    rest_port=rest_port,
                    ws_port=ws_port,
                    timeout=timeout,
                )
                return  # break infinite loop
            except Exception:
                if not external:
                    shutdown_lavalink_server()
                await asyncio.sleep(1)  # prevent busylooping

    async def event_handler(self, player, event_type, extra):
        notify = await self.config.guild(player.channel.guild).notify()
        status = await self.config.status()
        try:
            get_players = [p for p in lavalink.players if p.current is not None]
            get_single_title = get_players[0].current.title
            if get_single_title == "Unknown title":
                get_single_title = get_players[0].current.uri
                if not get_single_title.startswith("http"):
                    get_single_title = get_single_title.rsplit("/", 1)[-1]
            elif "localtracks/" in get_players[0].current.uri:
                get_single_title = "{} - {}".format(
                    get_players[0].current.author, get_players[0].current.title
                )
            else:
                get_single_title = get_players[0].current.title
            playing_servers = len(get_players)
        except IndexError:
            playing_servers = 0

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", player.current.uri)
            player.store("requester", player.current.requester)
            self.skip_votes[player.channel.guild] = []

        if event_type == lavalink.LavalinkEvents.TRACK_START and notify:
            notify_channel = player.fetch("channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                if player.fetch("notify_message") is not None:
                    try:
                        await player.fetch("notify_message").delete()
                    except discord.errors.NotFound:
                        pass
                if "localtracks/" in player.current.uri:
                    if not player.current.title == "Unknown title":
                        description = "**{} - {}**\n{}".format(
                            player.current.author,
                            player.current.title,
                            player.current.uri.replace("localtracks/", ""),
                        )
                    else:
                        description = "{}".format(player.current.uri.replace("localtracks/", ""))
                else:
                    description = "**[{}]({})**".format(player.current.title, player.current.uri)
                if player.current.is_stream:
                    dur = "LIVE"
                else:
                    dur = lavalink.utils.format_time(player.current.length)
                embed = discord.Embed(
                    colour=(await self._get_embed_colour(notify_channel)),
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
            if playing_servers == 0:
                await self.bot.change_presence(activity=None)
            if playing_servers == 1:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        name=get_single_title, type=discord.ActivityType.listening
                    )
                )
            if playing_servers > 1:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        name=_("music in {} servers").format(playing_servers),
                        type=discord.ActivityType.playing,
                    )
                )

        if event_type == lavalink.LavalinkEvents.QUEUE_END and notify:
            notify_channel = player.fetch("channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                embed = discord.Embed(
                    colour=(await self._get_embed_colour(notify_channel)), title=_("Queue ended.")
                )
                await notify_channel.send(embed=embed)

        if event_type == lavalink.LavalinkEvents.QUEUE_END and status:
            if playing_servers == 0:
                await self.bot.change_presence(activity=None)
            if playing_servers == 1:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        name=get_single_title, type=discord.ActivityType.listening
                    )
                )
            if playing_servers > 1:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        name=_("music in {} servers").format(playing_servers),
                        type=discord.ActivityType.playing,
                    )
                )

        if event_type == lavalink.LavalinkEvents.TRACK_EXCEPTION:
            if "localtracks/" in player.current.uri:
                return
            message_channel = player.fetch("channel")
            if message_channel:
                message_channel = self.bot.get_channel(message_channel)
                embed = discord.Embed(
                    colour=(await self._get_embed_colour(message_channel)),
                    title=_("Track Error"),
                    description="{}\n**[{}]({})**".format(
                        extra, player.current.title, player.current.uri
                    ),
                )
                embed.set_footer(text=_("Skipping..."))
                await message_channel.send(embed=embed)
                await player.skip()

    @commands.group()
    @commands.guild_only()
    async def audioset(self, ctx):
        """Music configuration options."""
        pass

    @audioset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def dj(self, ctx):
        """Toggle DJ mode.

        DJ mode allows users with the DJ role to use audio commands.
        """
        dj_role_id = await self.config.guild(ctx.guild).dj_role()
        if dj_role_id is None and ctx.guild.get_role(dj_role_id):
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
            ctx, _("DJ role enabled: {true_or_false}.".format(true_or_false=not dj_enabled))
        )

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def emptydisconnect(self, ctx, seconds: int):
        """Auto-disconnection after x seconds while stopped. 0 to disable."""
        if seconds < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if seconds < 10 and seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self._embed_msg(ctx, _("Empty disconnect disabled."))
        else:
            enabled = True
            await self._embed_msg(
                ctx,
                _("Empty disconnect timer set to {num_seconds}.").format(
                    num_seconds=self._dynamic_time(seconds)
                ),
            )

        await self.config.guild(ctx.guild).emptydc_timer.set(seconds)
        await self.config.guild(ctx.guild).emptydc_enabled.set(enabled)

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def maxlength(self, ctx, seconds):
        """Max length of a track to queue in seconds. 0 to disable.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`).
        Invalid input will turn the max length setting off."""
        if not isinstance(seconds, int):
            seconds = int(await self._time_convert(seconds) / 1000)
        if seconds < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if seconds == 0:
            await self._embed_msg(ctx, _("Track max length disabled."))
        else:
            await self._embed_msg(
                ctx,
                _("Track max length set to {seconds}.").format(
                    seconds=self._dynamic_time(seconds)
                ),
            )

        await self.config.guild(ctx.guild).maxlength.set(seconds)

    @audioset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx, role_name: discord.Role):
        """Set the role to use for DJ mode."""
        await self.config.guild(ctx.guild).dj_role.set(role_name.id)
        dj_role_obj = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
        await self._embed_msg(ctx, _("DJ role set to: {role.name}.").format(role=dj_role_obj))

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def jukebox(self, ctx, price: int):
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
                    price=price, currency=await bank.get_currency_name(ctx.guild)
                ),
            )

        await self.config.guild(ctx.guild).jukebox_price.set(price)
        await self.config.guild(ctx.guild).jukebox.set(jukebox)

    @audioset.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def notify(self, ctx):
        """Toggle track announcement and other bot messages."""
        notify = await self.config.guild(ctx.guild).notify()
        await self.config.guild(ctx.guild).notify.set(not notify)
        await self._embed_msg(
            ctx, _("Verbose mode on: {true_or_false}.").format(true_or_false=not notify)
        )

    @audioset.command()
    @checks.is_owner()
    async def restrict(self, ctx):
        """Toggle the domain restriction on Audio.

        When toggled off, users will be able to play songs from non-commercial websites and links.
        When toggled on, users are restricted to YouTube, SoundCloud, Mixer, Vimeo, Twitch, and Bandcamp links."""
        restrict = await self.config.restrict()
        await self.config.restrict.set(not restrict)
        await self._embed_msg(
            ctx, _("Commercial links only: {true_or_false}.").format(true_or_false=not restrict)
        )

    @audioset.command()
    async def settings(self, ctx):
        """Show the current settings."""
        data = await self.config.guild(ctx.guild).all()
        global_data = await self.config.all()
        dj_role_obj = ctx.guild.get_role(data["dj_role"])
        dj_enabled = data["dj_enabled"]
        emptydc_enabled = data["emptydc_enabled"]
        emptydc_timer = data["emptydc_timer"]
        jukebox = data["jukebox"]
        jukebox_price = data["jukebox_price"]
        thumbnail = data["thumbnail"]
        jarbuild = redbot.core.__version__
        maxlength = data["maxlength"]
        vote_percent = data["vote_percent"]
        msg = "----" + _("Server Settings") + "----        \n"
        if emptydc_enabled:
            msg += _("Disconnect timer: [{num_seconds}]\n").format(
                num_seconds=self._dynamic_time(emptydc_timer)
            )
        if dj_enabled:
            msg += _("DJ Role:          [{role.name}]\n").format(role=dj_role_obj)
        if jukebox:
            msg += _("Jukebox:          [{jukebox_name}]\n").format(jukebox_name=jukebox)
            msg += _("Command price:    [{jukebox_price}]\n").format(jukebox_price=jukebox_price)
        if maxlength > 0:
            msg += _("Max track length: [{tracklength}]\n").format(
                tracklength=self._dynamic_time(maxlength)
            )
        msg += _(
            "Repeat:           [{repeat}]\n"
            "Shuffle:          [{shuffle}]\n"
            "Song notify msgs: [{notify}]\n"
            "Songs as status:  [{status}]\n"
        ).format(**global_data, **data)
        if thumbnail:
            msg += _("Thumbnails:       [{0}]\n").format(thumbnail)
        if vote_percent > 0:
            msg += _(
                "Vote skip:        [{vote_enabled}]\nSkip percentage:  [{vote_percent}%]\n"
            ).format(**data)
        msg += _(
            "---Lavalink Settings---        \n"
            "Cog version:      [{version}]\n"
            "Jar build:        [{jarbuild}]\n"
            "External server:  [{use_external_lavalink}]"
        ).format(version=__version__, jarbuild=jarbuild, **global_data)

        embed = discord.Embed(colour=await ctx.embed_colour(), description=box(msg, lang="ini"))
        return await ctx.send(embed=embed)

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def thumbnail(self, ctx):
        """Toggle displaying a thumbnail on audio messages."""
        thumbnail = await self.config.guild(ctx.guild).thumbnail()
        await self.config.guild(ctx.guild).thumbnail.set(not thumbnail)
        await self._embed_msg(
            ctx, _("Thumbnail display: {true_or_false}.").format(true_or_false=not thumbnail)
        )

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def vote(self, ctx, percent: int):
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

    @checks.is_owner()
    @audioset.command()
    async def status(self, ctx):
        """Enable/disable tracks' titles as status."""
        status = await self.config.status()
        await self.config.status.set(not status)
        await self._embed_msg(
            ctx, _("Song titles as status: {true_or_false}.").format(true_or_false=not status)
        )

    @commands.command()
    @commands.guild_only()
    async def audiostats(self, ctx):
        """Audio stats."""
        server_num = len([p for p in lavalink.players if p.current is not None])
        server_list = []

        for p in lavalink.players:
            connect_start = p.fetch("connect")
            connect_dur = self._dynamic_time(
                int((datetime.datetime.utcnow() - connect_start).total_seconds())
            )
            try:
                if "localtracks/" in p.current.uri:
                    if p.current.title == "Unknown title":
                        current_title = p.current.uri.replace("localtracks/", "")
                        server_list.append(
                            "{} [`{}`]: **{}**".format(
                                p.channel.guild.name, connect_dur, current_title
                            )
                        )
                    else:
                        current_title = p.current.title
                        server_list.append(
                            "{} [`{}`]: **{} - {}**".format(
                                p.channel.guild.name, connect_dur, p.current.author, current_title
                            )
                        )
                else:
                    server_list.append(
                        "{} [`{}`]: **[{}]({})**".format(
                            p.channel.guild.name, connect_dur, p.current.title, p.current.uri
                        )
                    )
            except AttributeError:
                server_list.append(
                    "{} [`{}`]: **{}**".format(
                        p.channel.guild.name, connect_dur, _("Nothing playing.")
                    )
                )
        if server_num == 0:
            servers = _("Not connected anywhere.")
        else:
            servers = "\n".join(server_list)
        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Connected in {num} servers:").format(num=server_num),
            description=servers,
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def bump(self, ctx, index: int):
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
        if "localtracks/" in removed.uri:
            if removed.title == "Unknown title":
                removed_title = removed.uri.replace("localtracks/", "")
            else:
                removed_title = "{} - {}".format(removed.author, removed.title)
        else:
            removed_title = removed.title
        await self._embed_msg(
            ctx, _("Moved {track} to the top of the queue.").format(track=removed_title)
        )

    @commands.command(aliases=["dc"])
    @commands.guild_only()
    async def disconnect(self, ctx):
        """Disconnect from the voice channel."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if self._player_check(ctx):
            if dj_enabled:
                if not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(ctx, _("You need the DJ role to disconnect."))
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("There are other people listening to music."))
            else:
                await lavalink.get_player(ctx.guild.id).stop()
                return await lavalink.get_player(ctx.guild.id).disconnect()

    @commands.group()
    @commands.guild_only()
    async def local(self, ctx):
        """Local playback commands."""
        pass

    @local.command(name="folder")
    async def local_folder(self, ctx):
        """Play all songs in a localtracks folder."""
        if not await self._localtracks_check(ctx):
            return
        await ctx.invoke(self.local_play)

    @local.command(name="play")
    async def local_play(self, ctx):
        """Play a local track."""
        if not await self._localtracks_check(ctx):
            return
        localtracks_folders = await self._localtracks_folders(ctx)
        if not localtracks_folders:
            return await self._embed_msg(ctx, _("No local track folders found."))
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
                await message.delete()
                await self._search_button_action(ctx, localtracks_folders, emoji, page)
                return None

        LOCAL_FOLDER_CONTROLS = {
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
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await menu(ctx, folder_page_list, DEFAULT_CONTROLS)
            else:
                await menu(ctx, folder_page_list, LOCAL_FOLDER_CONTROLS)
        else:
            await menu(ctx, folder_page_list, LOCAL_FOLDER_CONTROLS)

    @local.command(name="search")
    async def local_search(self, ctx, *, search_words):
        """Search for songs across all localtracks folders."""
        if not await self._localtracks_check(ctx):
            return
        localtracks_folders = await self._localtracks_folders(ctx)
        if not localtracks_folders:
            return await self._embed_msg(ctx, _("No album folders found."))
        all_tracks = []
        for local_folder in localtracks_folders:
            folder_tracks = await self._folder_list(ctx, local_folder)
            all_tracks = all_tracks + folder_tracks
        search_list = await self._build_local_search_list(all_tracks, search_words)
        if not search_list:
            return await self._embed_msg(ctx, _("No matches."))
        await ctx.invoke(self.search, query=search_list)

    async def _all_folder_tracks(self, ctx, folder):
        if not await self._localtracks_check(ctx):
            return
        allowed_files = (".mp3", ".flac", ".ogg")
        current_folder = os.getcwd() + "/localtracks/{}/".format(folder)
        folder_list = [
            f
            for f in os.listdir(current_folder)
            if (f.lower().endswith(allowed_files)) and (os.path.isfile(current_folder + f))
        ]
        track_listing = []
        for localtrack_location in folder_list:
            track_listing.append(localtrack_location)
        return track_listing

    @staticmethod
    async def _build_local_search_list(to_search, search_words):
        search_results = process.extract(search_words, to_search, limit=50)
        search_list = []
        for track_match, percent_match in search_results:
            if percent_match > 75:
                search_list.append(track_match)
        return search_list

    async def _folder_list(self, ctx, folder):
        if not await self._localtracks_check(ctx):
            return
        allowed_files = (".mp3", ".flac", ".ogg")
        folder_list = [
            os.getcwd() + "/localtracks/{}/{}".format(folder, f)
            for f in os.listdir(os.getcwd() + "/localtracks/{}/".format(folder))
            if (f.lower().endswith(allowed_files))
            and (os.path.isfile(os.getcwd() + "/localtracks/{}/{}".format(folder, f)))
        ]
        track_listing = []
        if ctx.invoked_with == "search":
            for localtrack_location in folder_list:
                track_listing.append(
                    localtrack_location.replace(
                        "{}/localtracks/".format(cog_data_path(raw_name="Audio")), ""
                    )
                )
        else:
            for localtrack_location in folder_list:
                localtrack_location = "localtrack:{}".format(localtrack_location)
                track_listing.append(localtrack_location)
        return track_listing

    async def _folder_tracks(self, ctx, player, folder):
        if not await self._localtracks_check(ctx):
            return
        local_tracks = []
        for local_file in await self._all_folder_tracks(ctx, folder):
            track = await player.get_tracks("localtracks/{}/{}".format(folder, local_file))
            try:
                local_tracks.append(track[0])
            except IndexError:
                pass
        return local_tracks

    async def _local_play_all(self, ctx, folder):
        if not await self._localtracks_check(ctx):
            return
        await ctx.invoke(self.search, query=("folder:" + folder))

    async def _localtracks_check(self, ctx):
        audio_data = cog_data_path(raw_name="Audio")
        if os.getcwd() != audio_data:
            os.chdir(audio_data)
        localtracks_folder = any(
            f for f in os.listdir(os.getcwd()) if not os.path.isfile(f) if f == "localtracks"
        )
        if not localtracks_folder:
            await self._embed_msg(ctx, _("No localtracks folder."))
            return False
        else:
            return True

    @commands.command(aliases=["np", "n", "song", "track"])
    @commands.guild_only()
    async def now(self, ctx):
        """Now playing."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        expected = ("⏮", "⏹", "⏸", "⏭")
        emoji = {"prev": "⏮", "stop": "⏹", "pause": "⏸", "next": "⏭"}
        player = lavalink.get_player(ctx.guild.id)
        if player.current:
            arrow = await self._draw_time(ctx)
            pos = lavalink.utils.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
            else:
                dur = lavalink.utils.format_time(player.current.length)
            if "localtracks" in player.current.uri:
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
                uri=player.current.uri.replace("localtracks/", ""),
                arrow=arrow,
                pos=pos,
                dur=dur,
            )
        else:
            song = _("Nothing.")

        if player.fetch("np_message") is not None:
            try:
                await player.fetch("np_message").delete()
            except discord.errors.NotFound:
                pass

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Now Playing"), description=song
        )
        if await self.config.guild(ctx.guild).thumbnail() and player.current:
            if player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)
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
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            return await self._clear_react(message)
        else:
            if task is not None:
                task.cancel()
        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]
        if react == "prev":
            await self._clear_react(message)
            await ctx.invoke(self.prev)
        elif react == "stop":
            await self._clear_react(message)
            await ctx.invoke(self.stop)
        elif react == "pause":
            await self._clear_react(message)
            await ctx.invoke(self.pause)
        elif react == "next":
            await self._clear_react(message)
            await ctx.invoke(self.skip)

    @commands.command(aliases=["resume"])
    @commands.guild_only()
    async def pause(self, ctx):
        """Pause and resume."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to pause the music.")
            )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to pause tracks."))

        command = ctx.invoked_with
        if not player.current:
            return await self._embed_msg(ctx, _("Nothing playing."))
        if "localtracks/" in player.current.uri:
            description = "**{}**\n{}".format(
                player.current.title, player.current.uri.replace("localtracks/", "")
            )
        else:
            description = "**[{}]({})**".format(player.current.title, player.current.uri)
        if player.current and not player.paused and command != "resume":
            await player.pause()
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Track Paused"), description=description
            )
            return await ctx.send(embed=embed)

        if player.paused and command != "pause":
            await player.pause(False)
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Track Resumed"), description=description
            )
            return await ctx.send(embed=embed)

        if player.paused and command == "pause":
            return await self._embed_msg(ctx, _("Track is paused."))
        if player.current and command == "resume":
            return await self._embed_msg(ctx, _("Track is playing."))
        await self._embed_msg(ctx, _("Nothing playing."))

    @commands.command()
    @commands.guild_only()
    async def percent(self, ctx):
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
            return await self._embed_msg(ctx, _("Nothing in the queue."))

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
    async def play(self, ctx, *, query):
        """Play a URL or search for a track."""
        guild_data = await self.config.guild(ctx.guild).all()
        restrict = await self.config.restrict()
        if restrict:
            if self._match_url(query):
                url_check = self._url_check(query)
                if not url_check:
                    return await self._embed_msg(ctx, _("That URL is not allowed."))
        if not self._player_check(ctx):
            try:
                if not ctx.author.voice.channel.permissions_for(ctx.me).connect or self._userlimit(
                    ctx.author.voice.channel
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
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to use the play command.")
            )
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return

        if not query:
            return await self._embed_msg(ctx, _("No tracks to play."))
        query = query.strip("<>")

        if query.startswith("localtrack:"):
            await self._localtracks_check(ctx)
            query = query.replace("localtrack:", "").replace(
                (str(cog_data_path(raw_name="Audio")) + "/"), ""
            )
        allowed_files = (".mp3", ".flac", ".ogg")
        if not self._match_url(query) and not (query.lower().endswith(allowed_files)):
            query = "ytsearch:{}".format(query)

        tracks = await player.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, _("Nothing found."))

        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        before_queue_length = len(player.queue)

        if ("ytsearch:" or "localtrack") not in query and len(tracks) > 1:
            track_len = 0
            for track in tracks:
                if guild_data["maxlength"] > 0:
                    if self._track_limit(ctx, track, guild_data["maxlength"]):
                        track_len += 1
                        player.add(ctx.author, track)
                else:
                    track_len += 1
                    player.add(ctx.author, track)

            if len(tracks) > track_len:
                maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                    bad_tracks=(len(tracks) - track_len)
                )
            else:
                maxlength_msg = ""
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playlist Enqueued"),
                description=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                    num=track_len, maxlength_msg=maxlength_msg
                ),
            )
            if not guild_data["shuffle"] and queue_duration > 0:
                embed.set_footer(
                    text=_(
                        "{time} until start of playlist playback: starts at #{position} in queue"
                    ).format(time=queue_total_duration, position=before_queue_length + 1)
                )
            if not player.current:
                await player.play()
        else:
            single_track = tracks[0]
            if guild_data["maxlength"] > 0:
                if self._track_limit(ctx, single_track, guild_data["maxlength"]):
                    player.add(ctx.author, single_track)
                else:
                    return await self._embed_msg(ctx, _("Track exceeds maximum length."))
            else:
                player.add(ctx.author, single_track)

            if "localtracks" in single_track.uri:
                if not single_track.title == "Unknown title":
                    description = "**{} - {}**\n{}".format(
                        single_track.author,
                        single_track.title,
                        single_track.uri.replace("localtracks/", ""),
                    )
                else:
                    description = "{}".format(single_track.uri.replace("localtracks/", ""))
            else:
                description = "**[{}]({})**".format(single_track.title, single_track.uri)
            embed = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Track Enqueued"), description=description
            )
            if not guild_data["shuffle"] and queue_duration > 0:
                embed.set_footer(
                    text=_("{time} until track playback: #{position} in queue").format(
                        time=queue_total_duration, position=before_queue_length + 1
                    )
                )
            elif queue_duration > 0:
                embed.set_footer(text=_("#{position} in queue").format(position=len(player.queue)))
            if not player.current:
                await player.play()
        await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    async def playlist(self, ctx):
        """Playlist configuration options."""
        pass

    @playlist.command(name="append")
    async def _playlist_append(self, ctx, playlist_name, *url):
        """Add a track URL, playlist link, or quick search to a playlist.

        The track(s) will be appended to the end of the playlist.
        """
        if not await self._playlist_check(ctx):
            return
        async with self.config.guild(ctx.guild).playlists() as playlists:
            try:
                if playlists[playlist_name][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx, _("You are not the author of that playlist.")
                    )
                player = lavalink.get_player(ctx.guild.id)
                to_append = await self._playlist_tracks(ctx, player, url)
                if not to_append:
                    return
                track_list = playlists[playlist_name]["tracks"]
                if track_list and len(to_append) == 1 and to_append[0] in track_list:
                    return await self._embed_msg(
                        ctx,
                        _("{track} is already in {playlist}.").format(
                            track=to_append[0]["info"]["title"], playlist=playlist_name
                        ),
                    )
                if track_list:
                    playlists[playlist_name]["tracks"] = track_list + to_append
                else:
                    playlists[playlist_name]["tracks"] = to_append
            except KeyError:
                return await self._embed_msg(ctx, _("No playlist with that name."))
        if playlists[playlist_name]["playlist_url"] is not None:
            playlists[playlist_name]["playlist_url"] = None
        if len(to_append) == 1:
            track_title = to_append[0]["info"]["title"]
            return await self._embed_msg(
                ctx,
                _("{track} appended to {playlist}.").format(
                    track=track_title, playlist=playlist_name
                ),
            )
        await self._embed_msg(
            ctx,
            _("{num} tracks appended to {playlist}.").format(
                num=len(to_append), playlist=playlist_name
            ),
        )

    @playlist.command(name="create")
    async def _playlist_create(self, ctx, playlist_name):
        """Create an empty playlist."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to save playlists."))
        async with self.config.guild(ctx.guild).playlists() as playlists:
            if playlist_name in playlists:
                return await self._embed_msg(
                    ctx, _("Playlist name already exists, try again with a different name.")
                )
        playlist_name = playlist_name.split(" ")[0].strip('"')
        playlist_list = self._to_json(ctx, None, None)
        async with self.config.guild(ctx.guild).playlists() as playlists:
            playlists[playlist_name] = playlist_list
        await self._embed_msg(ctx, _("Empty playlist {name} created.").format(name=playlist_name))

    @playlist.command(name="delete")
    async def _playlist_delete(self, ctx, playlist_name):
        """Delete a saved playlist."""
        async with self.config.guild(ctx.guild).playlists() as playlists:
            try:
                if playlists[playlist_name][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx, _("You are not the author of that playlist.")
                    )
                del playlists[playlist_name]
            except KeyError:
                return await self._embed_msg(ctx, _("No playlist with that name."))
        await self._embed_msg(ctx, _("{name} playlist deleted.").format(name=playlist_name))

    @playlist.command(name="info")
    async def _playlist_info(self, ctx, playlist_name):
        """Retrieve information from a saved playlist."""
        playlists = await self.config.guild(ctx.guild).playlists.get_raw()
        try:
            author_id = playlists[playlist_name]["author"]
        except KeyError:
            return await self._embed_msg(ctx, _("No playlist with that name."))
        author_obj = self.bot.get_user(author_id)
        playlist_url = playlists[playlist_name]["playlist_url"]
        try:
            track_len = len(playlists[playlist_name]["tracks"])
        except TypeError:
            track_len = 0
        if playlist_url is None:
            playlist_url = _("**Custom playlist.**")
        else:
            playlist_url = _("URL: <{url}>").format(url=playlist_url)
        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Playlist info for {playlist_name}:").format(playlist_name=playlist_name),
            description=_("Author: **{author_name}**\n{url}").format(
                author_name=author_obj, url=playlist_url
            ),
        )
        embed.set_footer(text=_("{num} track(s)").format(num=track_len))
        await ctx.send(embed=embed)

    @playlist.command(name="list")
    async def _playlist_list(self, ctx):
        """List saved playlists."""
        playlists = await self.config.guild(ctx.guild).playlists.get_raw()
        if not playlists:
            return await self._embed_msg(ctx, _("No saved playlists."))
        playlist_list = []
        space = "\N{EN SPACE}"
        for playlist_name in playlists:
            tracks = playlists[playlist_name]["tracks"]
            if not tracks:
                tracks = []
            author = playlists[playlist_name]["author"]
            playlist_list.append(
                ("\n" + space * 4).join(
                    (
                        bold(playlist_name),
                        _("Tracks: {num}").format(num=len(tracks)),
                        _("Author: {name}\n").format(name=self.bot.get_user(author)),
                    )
                )
            )
        abc_names = sorted(playlist_list, key=str.lower)
        len_playlist_list_pages = math.ceil(len(abc_names) / 5)
        playlist_embeds = []
        for page_num in range(1, len_playlist_list_pages + 1):
            embed = await self._build_playlist_list_page(ctx, page_num, abc_names)
            playlist_embeds.append(embed)
        await menu(ctx, playlist_embeds, DEFAULT_CONTROLS)

    async def _build_playlist_list_page(self, ctx, page_num, abc_names):
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
            title=_("Playlists for {server_name}:").format(server_name=ctx.guild.name),
            description=plist,
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num} playlists").format(
                page_num=page_num, total_pages=plist_num_pages, num=len(abc_names)
            )
        )
        return embed

    @commands.cooldown(1, 15, discord.ext.commands.BucketType.guild)
    @playlist.command(name="queue")
    async def _playlist_queue(self, ctx, playlist_name=None):
        """Save the queue to a playlist."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to save playlists."))
        async with self.config.guild(ctx.guild).playlists() as playlists:
            if playlist_name in playlists:
                return await self._embed_msg(
                    ctx, _("Playlist name already exists, try again with a different name.")
                )
            if not self._player_check(ctx):
                return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        tracklist = []
        np_song = self._track_creator(player, "np")
        tracklist.append(np_song)
        for track in player.queue:
            queue_idx = player.queue.index(track)
            track_obj = self._track_creator(player, queue_idx)
            tracklist.append(track_obj)
        if not playlist_name:
            await self._embed_msg(ctx, _("Please enter a name for this playlist."))

            try:
                playlist_name_msg = await ctx.bot.wait_for(
                    "message",
                    timeout=15.0,
                    check=MessagePredicate.regex(fr"^(?!{ctx.prefix})", ctx),
                )
                playlist_name = playlist_name_msg.content.split(" ")[0].strip('"')
                if len(playlist_name) > 20:
                    return await self._embed_msg(
                        ctx, _("Try the command again with a shorter name.")
                    )
                if playlist_name in playlists:
                    return await self._embed_msg(
                        ctx, _("Playlist name already exists, try again with a different name.")
                    )
            except asyncio.TimeoutError:
                return await self._embed_msg(ctx, _("No playlist name entered, try again later."))
        playlist_list = self._to_json(ctx, None, tracklist)
        async with self.config.guild(ctx.guild).playlists() as playlists:
            playlist_name = playlist_name.split(" ")[0].strip('"')
            playlists[playlist_name] = playlist_list
        await self._embed_msg(
            ctx,
            _("Playlist {name} saved from current queue: {num} tracks added.").format(
                name=playlist_name.split(" ")[0].strip('"'), num=len(tracklist)
            ),
        )

    @playlist.command(name="remove")
    async def _playlist_remove(self, ctx, playlist_name, url):
        """Remove a track from a playlist by url."""
        async with self.config.guild(ctx.guild).playlists() as playlists:
            try:
                if playlists[playlist_name][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx, _("You are not the author of that playlist.")
                    )
            except KeyError:
                return await self._embed_msg(ctx, _("No playlist with that name."))
            track_list = playlists[playlist_name]["tracks"]
            clean_list = [track for track in track_list if not url == track["info"]["uri"]]
            if len(playlists[playlist_name]["tracks"]) == len(clean_list):
                return await self._embed_msg(ctx, _("URL not in playlist."))
            del_count = len(playlists[playlist_name]["tracks"]) - len(clean_list)
            if not clean_list:
                del playlists[playlist_name]
                return await self._embed_msg(ctx, _("No tracks left, removing playlist."))
            playlists[playlist_name]["tracks"] = clean_list
        if playlists[playlist_name]["playlist_url"] is not None:
            playlists[playlist_name]["playlist_url"] = None
        if del_count > 1:
            await self._embed_msg(
                ctx,
                _("{num} entries have been removed from the {playlist_name} playlist.").format(
                    num=del_count, playlist_name=playlist_name
                ),
            )
        else:
            await self._embed_msg(
                ctx,
                _("The track has been removed from the {playlist_name} playlist.").format(
                    playlist_name=playlist_name
                ),
            )

    @playlist.command(name="save")
    async def _playlist_save(self, ctx, playlist_name, playlist_url):
        """Save a playlist from a url."""
        if not await self._playlist_check(ctx):
            return
        player = lavalink.get_player(ctx.guild.id)
        tracklist = await self._playlist_tracks(ctx, player, playlist_url)
        playlist_list = self._to_json(ctx, playlist_url, tracklist)
        if tracklist is not None:
            async with self.config.guild(ctx.guild).playlists() as playlists:
                playlist_name = playlist_name.split(" ")[0].strip('"')
                playlists[playlist_name] = playlist_list
                return await self._embed_msg(
                    ctx,
                    _("Playlist {name} saved: {num} tracks added.").format(
                        name=playlist_name, num=len(tracklist)
                    ),
                )

    @playlist.command(name="start")
    async def _playlist_start(self, ctx, playlist_name=None):
        """Load a playlist into the queue."""
        if not await self._playlist_check(ctx):
            return
        maxlength = await self.config.guild(ctx.guild).maxlength()
        playlists = await self.config.guild(ctx.guild).playlists.get_raw()
        author_obj = self.bot.get_user(ctx.author.id)
        track_len = 0
        try:
            player = lavalink.get_player(ctx.guild.id)
            for track in playlists[playlist_name]["tracks"]:
                if track["info"]["uri"].startswith("localtracks/"):
                    if not os.path.isfile(track["info"]["uri"]):
                        continue
                if maxlength > 0:
                    if not self._track_limit(ctx, track["info"]["length"], maxlength):
                        continue
                player.add(author_obj, lavalink.rest_api.Track(data=track))
                track_len += 1
            if len(playlists[playlist_name]["tracks"]) > track_len:
                maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                    bad_tracks=(len(playlists[playlist_name]["tracks"]) - track_len)
                )
            else:
                maxlength_msg = ""
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playlist Enqueued"),
                description=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                    num=track_len, maxlength_msg=maxlength_msg
                ),
            )
            await ctx.send(embed=embed)
            if not player.current:
                await player.play()
        except TypeError:
            await ctx.invoke(self.play, query=playlists[playlist_name]["playlist_url"])
        except KeyError:
            await self._embed_msg(ctx, _("That playlist doesn't exist."))

    @checks.is_owner()
    @playlist.command(name="upload")
    async def _playlist_upload(self, ctx):
        """Convert a Red v2 playlist file to a playlist."""
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
        v2_playlist_name = (file_url.split("/")[6]).split(".")[0]
        file_suffix = file_url.rsplit(".", 1)[1]
        if file_suffix != "txt":
            return await self._embed_msg(ctx, _("Only playlist files can be uploaded."))
        try:
            async with self.session.request("GET", file_url) as r:
                v2_playlist = await r.json(content_type="text/plain")
        except UnicodeDecodeError:
            return await self._embed_msg(ctx, _("Not a valid playlist file."))
        try:
            v2_playlist_url = v2_playlist["link"]
        except KeyError:
            v2_playlist_url = None
        if (
            not v2_playlist_url
            or not self._match_yt_playlist(v2_playlist_url)
            or not await player.get_tracks(v2_playlist_url)
        ):
            track_list = []
            track_count = 0
            async with self.config.guild(ctx.guild).playlists() as v3_playlists:
                try:
                    if v3_playlists[v2_playlist_name]:
                        return await self._embed_msg(
                            ctx, _("A playlist already exists with this name.")
                        )
                except KeyError:
                    pass
            embed1 = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Please wait, adding tracks...")
            )
            playlist_msg = await ctx.send(embed=embed1)
            for song_url in v2_playlist["playlist"]:
                track = await player.get_tracks(song_url)
                try:
                    track_obj = self._track_creator(player, other_track=track[0])
                    track_list.append(track_obj)
                    track_count = track_count + 1
                except IndexError:
                    pass
                if track_count % 5 == 0:
                    embed2 = discord.Embed(
                        colour=await ctx.embed_colour(),
                        title=_("Loading track {num}/{total}...").format(
                            num=track_count, total=len(v2_playlist["playlist"])
                        ),
                    )
                    await playlist_msg.edit(embed=embed2)
            if not track_list:
                return await self._embed_msg(ctx, _("No tracks found."))
            playlist_list = self._to_json(ctx, v2_playlist_url, track_list)
            async with self.config.guild(ctx.guild).playlists() as v3_playlists:
                v3_playlists[v2_playlist_name] = playlist_list
            if len(v2_playlist["playlist"]) != track_count:
                bad_tracks = len(v2_playlist["playlist"]) - track_count
                msg = _(
                    "Added {num} tracks from the {playlist_name} playlist. {num_bad} track(s) "
                    "could not be loaded."
                ).format(num=track_count, playlist_name=v2_playlist_name, num_bad=bad_tracks)
            else:
                msg = _("Added {num} tracks from the {playlist_name} playlist.").format(
                    num=track_count, playlist_name=v2_playlist_name
                )
            embed3 = discord.Embed(
                colour=await ctx.embed_colour(), title=_("Playlist Saved"), description=msg
            )
            await playlist_msg.edit(embed=embed3)
        else:
            await ctx.invoke(self._playlist_save, v2_playlist_name, v2_playlist_url)

    async def _playlist_check(self, ctx):
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        jukebox_price = await self.config.guild(ctx.guild).jukebox_price()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                await self._embed_msg(ctx, _("You need the DJ role to use playlists."))
                return False
        if not self._player_check(ctx):
            try:
                if not ctx.author.voice.channel.permissions_for(ctx.me).connect or self._userlimit(
                    ctx.author.voice.channel
                ):
                    return await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
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
        if not await self._currency_check(ctx, jukebox_price):
            return False
        await self._data_check(ctx)
        return True

    async def _playlist_tracks(self, ctx, player, query):
        search = False
        if type(query) is tuple:
            query = " ".join(query)
        if not query.startswith("http"):
            query = " ".join(query)
            query = "ytsearch:{}".format(query)
            search = True
        tracks = await player.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, _("Nothing found."))
        tracklist = []
        if not search:
            for track in tracks:
                track_obj = self._track_creator(player, other_track=track)
                tracklist.append(track_obj)
        else:
            track_obj = self._track_creator(player, other_track=tracks[0])
            tracklist.append(track_obj)
        return tracklist

    @commands.command()
    @commands.guild_only()
    async def prev(self, ctx):
        """Skip to the start of the previously played track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
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
        if shuffle:
            return await self._embed_msg(ctx, _("Turn shuffle off to use this command."))
        if player.fetch("prev_song") is None:
            return await self._embed_msg(ctx, _("No previous track."))
        else:
            last_track = await player.get_tracks(player.fetch("prev_song"))
            player.add(player.fetch("prev_requester"), last_track[0])
            queue_len = len(player.queue)
            bump_song = player.queue[-1]
            player.queue.insert(0, bump_song)
            player.queue.pop(queue_len)
            await player.skip()
            if "localtracks/" in player.current.uri:
                description = "**{}**\n{}".format(
                    player.current.title, player.current.uri.replace("localtracks/", "")
                )
            else:
                description = f"**[{player.current.title}]({player.current.title})**"
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Replaying Track"),
                description=description,
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx, *, page="1"):
        """List the queue.

        Use [p]queue search <search terms> to search the queue.
        """
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        if not page.isdigit():
            if page.startswith("search "):
                return await self._queue_search(ctx=ctx, search_words=page.replace("search ", ""))
            else:
                return
        else:
            page = int(page)
        len_queue_pages = math.ceil(len(player.queue) / 10)
        queue_page_list = []
        for page_num in range(1, len_queue_pages + 1):
            embed = await self._build_queue_page(ctx, player, page_num)
            queue_page_list.append(embed)
        if page > len_queue_pages:
            page = len_queue_pages
        await menu(ctx, queue_page_list, DEFAULT_CONTROLS, page=(page - 1))

    async def _build_queue_page(self, ctx, player, page_num):
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        queue_num_pages = math.ceil(len(player.queue) / 10)
        queue_idx_start = (page_num - 1) * 10
        queue_idx_end = queue_idx_start + 10
        queue_list = ""
        try:
            arrow = await self._draw_time(ctx)
        except AttributeError:
            return await self._embed_msg(ctx, _("There's nothing in the queue."))
        pos = lavalink.utils.format_time(player.position)

        if player.current.is_stream:
            dur = "LIVE"
        else:
            dur = lavalink.utils.format_time(player.current.length)

        if player.current.is_stream:
            queue_list += _("**Currently livestreaming:**")

        elif "localtracks" in player.current.uri:
            if not player.current.title == "Unknown title":
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + "**{current.author} - {current.title}**".format(current=player.current),
                        player.current.uri.replace("localtracks/", ""),
                        _("Requested by: **{user}**\n").format(user=player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
            else:
                queue_list += "\n".join(
                    (
                        _("Playing: ") + player.current.uri.replace("localtracks/", ""),
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
            if "localtracks" in track.uri:
                if track.title == "Unknown title":
                    queue_list += f"`{track_idx}.` " + ", ".join(
                        (
                            bold(track.uri.replace("localtracks/", "")),
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
        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        text = _(
            "Page {page_num}/{total_pages} | {num_tracks} tracks, {num_remaining} remaining"
        ).format(
            page_num=page_num,
            total_pages=queue_num_pages,
            num_tracks=len(player.queue) + 1,
            num_remaining=queue_total_duration,
        )
        if repeat:
            text += " | " + _("Repeat") + ": \N{WHITE HEAVY CHECK MARK}"
        if shuffle:
            text += " | " + _("Shuffle") + ": \N{WHITE HEAVY CHECK MARK}"
        embed.set_footer(text=text)
        return embed

    async def _queue_search(self, ctx, *, search_words):
        player = lavalink.get_player(ctx.guild.id)
        search_list = await self._build_queue_search_list(player.queue, search_words)
        if not search_list:
            return await self._embed_msg(ctx, _("No matches."))
        len_search_pages = math.ceil(len(search_list) / 10)
        search_page_list = []
        for page_num in range(1, len_search_pages + 1):
            embed = await self._build_queue_search_page(ctx, page_num, search_list)
            search_page_list.append(embed)
        await menu(ctx, search_page_list, DEFAULT_CONTROLS)

    async def _build_queue_search_list(self, queue_list, search_words):
        track_list = []
        queue_idx = 0
        for track in queue_list:
            queue_idx = queue_idx + 1
            if not self._match_url(track.uri):
                if track.title == "Unknown title":
                    track_title = track.uri.split("/")[2]
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

    async def _build_queue_search_page(self, ctx, page_num, search_list):
        search_num_pages = math.ceil(len(search_list) / 10)
        search_idx_start = (page_num - 1) * 10
        search_idx_end = search_idx_start + 10
        track_match = ""
        command = ctx.invoked_with
        for i, track in enumerate(
            search_list[search_idx_start:search_idx_end], start=search_idx_start
        ):
            track_idx = i + 1
            if command == "search":
                track_location = track.replace(
                    "localtrack:{}/localtracks/".format(cog_data_path(raw_name="Audio")), ""
                )
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

    @commands.command()
    @commands.guild_only()
    async def repeat(self, ctx):
        """Toggle repeat."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to toggle repeat."))
        repeat = await self.config.guild(ctx.guild).repeat()
        await self.config.guild(ctx.guild).repeat.set(not repeat)
        repeat = await self.config.guild(ctx.guild).repeat()
        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You must be in the voice channel to toggle repeat.")
                )
        await self._embed_msg(
            ctx, _("Repeat tracks: {true_or_false}.").format(true_or_false=repeat)
        )

    @commands.command()
    @commands.guild_only()
    async def remove(self, ctx, index: int):
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
        if "localtracks/" in removed.uri:
            if removed.title == "Unknown title":
                removed_title = removed.uri.replace("localtracks/", "")
            else:
                removed_title = "{} - {}".format(removed.author, removed.title)
        else:
            removed_title = removed.title
        await self._embed_msg(
            ctx, _("Removed {track} from the queue.").format(track=removed_title)
        )

    @commands.command()
    @commands.guild_only()
    async def search(self, ctx, *, query):
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
                await message.delete()
                return None

        SEARCH_CONTROLS = {
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
            try:
                if not ctx.author.voice.channel.permissions_for(ctx.me).connect or self._userlimit(
                    ctx.author.voice.channel
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
        await self._data_check(ctx)

        if not isinstance(query, list):
            query = query.strip("<>")
            if query.startswith("list ") or query.startswith("folder:"):
                if query.startswith("list "):
                    query = "ytsearch:{}".format(query.replace("list ", ""))
                    tracks = await player.get_tracks(query)
                else:
                    query = query.replace("folder:", "")
                    tracks = await self._folder_tracks(ctx, player, query)
                if not tracks:
                    return await self._embed_msg(ctx, _("Nothing found."))

                queue_duration = await self._queue_duration(ctx)
                queue_total_duration = lavalink.utils.format_time(queue_duration)

                track_len = 0
                for track in tracks:
                    if guild_data["maxlength"] > 0:
                        if self._track_limit(ctx, track, guild_data["maxlength"]):
                            track_len += 1
                            player.add(ctx.author, track)
                    else:
                        track_len += 1
                        player.add(ctx.author, track)
                    if not player.current:
                        await player.play()
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
                if not guild_data["shuffle"] and queue_duration > 0:
                    songembed.set_footer(
                        text=_(
                            "{time} until start of search playback: starts at #{position} in queue"
                        ).format(time=queue_total_duration, position=len(player.queue) + 1)
                    )
                return await ctx.send(embed=songembed)
            elif query.startswith("sc "):
                query = "scsearch:{}".format(query.replace("sc ", ""))
                tracks = await player.get_tracks(query)
            elif ":localtrack:" in query:
                track_location = query.split(":")[2]
                tracks = await self._folder_list(ctx, track_location)
            elif query.startswith("localfolder:") and ":localtrack:" not in query:
                folder = query.split(":")[1]
                if ctx.invoked_with == "folder":
                    localfolder = query.replace("localfolder:", "")
                    return await self._local_play_all(ctx, localfolder)
                else:
                    tracks = await self._folder_list(ctx, folder)
            elif not self._match_url(query):
                query = "ytsearch:{}".format(query)
                tracks = await player.get_tracks(query)
            else:
                tracks = await player.get_tracks(query)
            if not tracks:
                return await self._embed_msg(ctx, _("Nothing found."))
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

        await menu(ctx, search_page_list, SEARCH_CONTROLS)

    async def _search_button_action(self, ctx, tracks, emoji, page):
        if not self._player_check(ctx):
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
        command = ctx.invoked_with
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        try:
            if emoji == "1⃣":
                search_choice = tracks[0 + (page * 5)]
            if emoji == "2⃣":
                search_choice = tracks[1 + (page * 5)]
            if emoji == "3⃣":
                search_choice = tracks[2 + (page * 5)]
            if emoji == "4⃣":
                search_choice = tracks[3 + (page * 5)]
            if emoji == "5⃣":
                search_choice = tracks[4 + (page * 5)]
        except IndexError:
            search_choice = tracks[-1]
        try:
            if "localtracks" in search_choice.uri:
                if search_choice.title == "Unknown title":
                    description = "**{} - {}**\n{}".format(
                        search_choice.author,
                        search_choice.title,
                        search_choice.uri.replace("localtracks/", ""),
                    )
                else:
                    description = "{}".format(search_choice.uri.replace("localtracks/", ""))
            else:
                description = "**[{}]({})**".format(search_choice.title, search_choice.uri)

        except AttributeError:
            if command == "search":
                return await ctx.invoke(self.play, query=("localtracks/{}".format(search_choice)))
            search_choice = search_choice.replace("localtrack:", "")
            if not search_choice.startswith(str(cog_data_path(raw_name="Audio"))):
                return await ctx.invoke(
                    self.search, query=("localfolder:{}".format(search_choice))
                )
            else:
                return await ctx.invoke(self.play, query=("localtrack:{}".format(search_choice)))

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Track Enqueued"), description=description
        )
        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        if not guild_data["shuffle"] and queue_duration > 0:
            embed.set_footer(
                text=_("{time} until track playback: #{position} in queue").format(
                    time=queue_total_duration, position=len(player.queue) + 1
                )
            )
        elif queue_duration > 0:
            embed.set_footer(text=_("#{position} in queue").format(position=len(player.queue) + 1))

        if guild_data["maxlength"] > 0:
            if self._track_limit(ctx, search_choice.length, guild_data["maxlength"]):
                player.add(ctx.author, search_choice)
            else:
                return await self._embed_msg(ctx, _("Track exceeds maximum length."))
        if not player.current:
            await player.play()
        await ctx.send(embed=embed)

    async def _build_search_page(self, ctx, tracks, page_num):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        command = ctx.invoked_with
        for i, track in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            try:
                if "localtracks" in track.uri:
                    search_list += "`{0}.` **{1}**\n[{2}]\n".format(
                        search_track_num, track.title, track.uri.replace("localtracks/", "")
                    )
                else:
                    search_list += "`{0}.` **[{1}]({2})**\n".format(
                        search_track_num, track.title, track.uri
                    )
            except AttributeError:
                if "localtrack:" not in track and command != "search":
                    search_list += "`{}.` **{}**\n".format(search_track_num, track)
                    folder = True
                elif command == "search":
                    search_list += "`{}.` **{}**\n".format(search_track_num, track)
                    folder = False
                else:
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num,
                        track.replace(
                            "localtrack:{}/localtracks/".format(
                                str(cog_data_path(raw_name="Audio"))
                            ),
                            "",
                        ),
                    )
                    folder = False
        try:
            title_check = tracks[0].uri
            title = _("Tracks Found:")
            footer = _("search results")
        except AttributeError:
            if folder:
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
    async def seek(self, ctx, seconds: int = 30):
        """Seek ahead or behind on a track by seconds."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(ctx, _("You must be in the voice channel to use seek."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("You need the DJ role to use seek."))
        if vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(
                    ctx, _("There are other people listening - vote to skip instead.")
                )
        if player.current:
            if player.current.is_stream:
                return await self._embed_msg(ctx, _("Can't seek on a stream."))
            else:
                time_sec = seconds * 1000
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
                return await player.seek(seek)
        else:
            await self._embed_msg(ctx, _("Nothing playing."))

    @commands.command()
    @commands.guild_only()
    async def shuffle(self, ctx):
        """Toggle shuffle."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to toggle shuffle."))
        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self.config.guild(ctx.guild).shuffle.set(not shuffle)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, _("You must be in the voice channel to toggle shuffle.")
                )
        await self._embed_msg(
            ctx, _("Shuffle tracks: {true_or_false}.").format(true_or_false=shuffle)
        )

    @commands.command()
    @commands.guild_only()
    async def sing(self, ctx):
        """Make Red sing one of her songs"""
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

    @commands.command(aliases=["forceskip", "fs"])
    @commands.guild_only()
    async def skip(self, ctx):
        """Skip to the next track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, _("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to skip the music.")
            )
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if dj_enabled and not vote_enabled and not await self._can_instaskip(ctx, ctx.author):
            if not await self._is_alone(ctx, ctx.author):
                return await self._embed_msg(ctx, _("You need the DJ role to skip tracks."))
        if vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
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
                        num_votes=num_votes,
                        num_members=num_members,
                        cur_percent=vote,
                        required_percent=percent,
                    )
                    return await self._embed_msg(ctx, reply)
            else:
                return await self._skip_action(ctx)
        else:
            return await self._skip_action(ctx)

    async def _can_instaskip(self, ctx, member):
        mod_role = await ctx.bot.db.guild(ctx.guild).mod_role()
        admin_role = await ctx.bot.db.guild(ctx.guild).admin_role()
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()

        if dj_enabled:
            is_active_dj = await self._has_dj_role(ctx, member)
        else:
            is_active_dj = False
        is_owner = member.id == self.bot.owner_id
        is_server_owner = member.id == ctx.guild.owner_id
        is_coowner = any(x == member.id for x in self.bot._co_owners)
        is_admin = (
            discord.utils.get(ctx.guild.get_member(member.id).roles, id=admin_role) is not None
        )
        is_mod = discord.utils.get(ctx.guild.get_member(member.id).roles, id=mod_role) is not None
        is_bot = member.bot is True

        return (
            is_active_dj
            or is_owner
            or is_server_owner
            or is_coowner
            or is_admin
            or is_mod
            or is_bot
        )

    async def _is_alone(self, ctx, member):
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

    async def _has_dj_role(self, ctx, member):
        dj_role_obj = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
        if dj_role_obj in ctx.guild.get_member(member.id).roles:
            return True
        else:
            return False

    async def _skip_action(self, ctx):
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
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

        if "localtracks" in player.current.uri:
            if not player.current.title == "Unknown title":
                description = "**{} - {}**\n{}".format(
                    player.current.author,
                    player.current.title,
                    player.current.uri.replace("localtracks/", ""),
                )
            else:
                description = "{}".format(player.current.uri.replace("localtracks/", ""))
        else:
            description = "**[{}]({})**".format(player.current.title, player.current.uri)
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Track Skipped"), description=description
        )
        await ctx.send(embed=embed)
        await player.skip()

    @commands.command(aliases=["s"])
    @commands.guild_only()
    async def stop(self, ctx):
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
        if player.is_playing:
            await self._embed_msg(ctx, _("Stopping..."))
            await player.stop()
            player.store("prev_requester", None)
            player.store("prev_song", None)
            player.store("playing_song", None)
            player.store("requester", None)

    @commands.command()
    @commands.guild_only()
    async def volume(self, ctx, vol: int = None):
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
    @checks.is_owner()
    async def llsetup(self, ctx):
        """Lavalink server configuration options."""
        pass

    @llsetup.command()
    async def external(self, ctx):
        """Toggle using external lavalink servers."""
        external = await self.config.use_external_lavalink()
        await self.config.use_external_lavalink.set(not external)

        if external:
            await self.config.host.set("localhost")
            await self.config.password.set("youshallnotpass")
            await self.config.rest_port.set(2333)
            await self.config.ws_port.set(2332)
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("External lavalink server: {true_or_false}.").format(
                    true_or_false=not external
                ),
            )
            embed.set_footer(text=_("Defaults reset."))
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(
                ctx,
                _("External lavalink server: {true_or_false}.").format(true_or_false=not external),
            )

        self._restart_connect()

    @llsetup.command()
    async def host(self, ctx, host):
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
    async def password(self, ctx, password):
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
    async def restport(self, ctx, rest_port: int):
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
    async def wsport(self, ctx, ws_port: int):
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

    async def _check_external(self):
        external = await self.config.use_external_lavalink()
        if not external:
            await self.config.use_external_lavalink.set(True)
            return True
        else:
            return False

    @staticmethod
    async def _clear_react(message):
        try:
            await message.clear_reactions()
        except (discord.Forbidden, discord.HTTPException):
            return

    async def _currency_check(self, ctx, jukebox_price: int):
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
                        currency=credits_name, required_credits=jukebox_price
                    ),
                )
                return False
        else:
            return True

    async def _data_check(self, ctx):
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        volume = await self.config.guild(ctx.guild).volume()
        if player.repeat != repeat:
            player.repeat = repeat
        if player.shuffle != shuffle:
            player.shuffle = shuffle
        if player.volume != volume:
            await player.set_volume(volume)

    async def disconnect_timer(self):
        stop_times = {}

        while True:
            for p in lavalink.players:
                server = p.channel.guild

                if server.id not in stop_times:
                    stop_times[server.id] = None

                if [self.bot.user] == p.channel.members:
                    if stop_times[server.id] is None:
                        stop_times[server.id] = int(time.time())

            for sid in stop_times:
                server_obj = self.bot.get_guild(sid)
                emptydc_enabled = await self.config.guild(server_obj).emptydc_enabled()
                if emptydc_enabled:
                    if stop_times[sid] is not None and [self.bot.user] == p.channel.members:
                        emptydc_timer = await self.config.guild(server_obj).emptydc_timer()
                        if stop_times[sid] and (
                            int(time.time()) - stop_times[sid] > emptydc_timer
                        ):
                            stop_times[sid] = None
                            await lavalink.get_player(sid).disconnect()

            await asyncio.sleep(5)

    @staticmethod
    async def _draw_time(ctx):
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

    @staticmethod
    def _dynamic_time(time):
        m, s = divmod(time, 60)
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

    @staticmethod
    async def _embed_msg(ctx, title):
        embed = discord.Embed(colour=await ctx.embed_colour(), title=title)
        await ctx.send(embed=embed)

    async def _get_embed_colour(self, channel: discord.abc.GuildChannel):
        # Unfortunately we need this for when context is unavailable.
        if await self.bot.db.guild(channel.guild).use_bot_color():
            return channel.guild.me.color
        else:
            return self.bot.color

    async def _get_playing(self, ctx):
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            return len([player for p in lavalink.players if p.is_playing])
        else:
            return 0

    async def _localtracks_folders(self, ctx):
        if not await self._localtracks_check(ctx):
            return
        localtracks_folders = [
            f
            for f in os.listdir(os.getcwd() + "/localtracks/")
            if not os.path.isfile(os.getcwd() + "/localtracks/" + f)
        ]
        return localtracks_folders

    @staticmethod
    def _match_url(url):
        try:
            query_url = urlparse(url)
            return all([query_url.scheme, query_url.netloc, query_url.path])
        except Exception:
            return False

    @staticmethod
    def _match_yt_playlist(url):
        yt_list_playlist = re.compile(
            r"^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)"
            r"(\/playlist\?).*(list=)(.*)(&|$)"
        )
        if yt_list_playlist.match(url):
            return True
        return False

    @staticmethod
    def _player_check(ctx):
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except KeyError:
            return False

    @staticmethod
    async def _queue_duration(ctx):
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

    @staticmethod
    def _to_json(ctx, playlist_url, tracklist):
        playlist = {"author": ctx.author.id, "playlist_url": playlist_url, "tracks": tracklist}
        return playlist

    @staticmethod
    def _track_creator(player, position=None, other_track=None):
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

    @staticmethod
    def _track_limit(ctx, track, maxlength):
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

    async def _time_convert(self, length):
        match = re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])").match(length)
        if match is not None:
            hr = int(match.group(1)) if match.group(1) else 0
            mn = int(match.group(2)) if match.group(2) else 0
            sec = int(match.group(3)) if match.group(3) else 0
            pos = sec + (mn * 60) + (hr * 3600)
            return pos * 1000
        else:
            try:
                return int(length) * 1000
            except ValueError:
                return 0

    @staticmethod
    def _url_check(url):
        valid_tld = [
            "youtube.com",
            "youtu.be",
            "soundcloud.com",
            "bandcamp.com",
            "vimeo.com",
            "mixer.com",
            "twitch.tv",
            "localtracks",
        ]
        query_url = urlparse(url)
        url_domain = ".".join(query_url.netloc.split(".")[-2:])
        if not query_url.netloc:
            url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
        return True if url_domain in valid_tld else False

    @staticmethod
    def _userlimit(channel):
        if channel.user_limit == 0:
            return False
        if channel.user_limit < len(channel.members) + 1:
            return True
        else:
            return False

    async def on_voice_state_update(self, member, before, after):
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

    def __unload(self):
        if not self._cleaned_up:
            self.session.detach()

            if self._disconnect_task:
                self._disconnect_task.cancel()

            if self._connect_task:
                self._connect_task.cancel()

            lavalink.unregister_event_listener(self.event_handler)
            self.bot.loop.create_task(lavalink.close())
            shutdown_lavalink_server()
            self._cleaned_up = True

    __del__ = __unload

    async def on_guild_remove(self, guild: discord.Guild):
        """
        This is to clean up players when
        the bot either leaves or is removed from a guild
        """
        channels = {
            x  # x is a voice_channel
            for y in [g.voice_channels for g in self.bot.guilds]
            for x in y  # y is a list of voice channels
        }  # Yes, this is ugly. It's also the most performant and commented.

        zombie_players = {p for p in lavalink.player_manager.players if p.channel not in channels}
        # Do not unroll to combine with next line.
        # Can result in iterator changing size during context switching.
        for zombie in zombie_players:
            await zombie.destroy()
