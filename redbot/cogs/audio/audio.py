import aiohttp
import asyncio
import datetime
import discord
import heapq
import lavalink
import math
import re
import redbot.core
from redbot.core import Config, commands, checks, bank
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, prev_page, next_page, close_menu
from redbot.core.i18n import Translator, cog_i18n
from .manager import shutdown_lavalink_server

_ = Translator("Audio", __file__)

__version__ = "0.0.6a"
__author__ = ["aikaterna", "billy/bollo/ati"]


@cog_i18n(_)
class Audio:
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2711759130, force_registration=True)

        default_global = {
            "host": "localhost",
            "rest_port": "2333",
            "ws_port": "2332",
            "password": "youshallnotpass",
            "status": False,
            "current_build": [3, 0, 0, "alpha", 0],
            "use_external_lavalink": False,
        }

        default_guild = {
            "dj_enabled": False,
            "dj_role": None,
            "jukebox": False,
            "jukebox_price": 0,
            "playlists": {},
            "notify": False,
            "repeat": False,
            "shuffle": False,
            "volume": 100,
            "vote_enabled": False,
            "vote_percent": 0,
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.skip_votes = {}
        self.session = aiohttp.ClientSession()

    async def init_config(self):
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
            timeout=60,
        )
        lavalink.register_event_listener(self.event_handler)

    async def event_handler(self, player, event_type, extra):
        notify = await self.config.guild(player.channel.guild).notify()
        status = await self.config.status()
        try:
            get_players = [p for p in lavalink.players if p.current is not None]
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
                embed = discord.Embed(
                    colour=notify_channel.guild.me.top_role.colour,
                    title="Now Playing",
                    description="**[{}]({})**".format(player.current.title, player.current.uri),
                )
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
                        name="music in {} servers".format(playing_servers),
                        type=discord.ActivityType.playing,
                    )
                )

        if event_type == lavalink.LavalinkEvents.QUEUE_END and notify:
            notify_channel = player.fetch("channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                embed = discord.Embed(
                    colour=notify_channel.guild.me.top_role.colour, title="Queue ended."
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
                        name="music in {} servers".format(playing_servers),
                        type=discord.ActivityType.playing,
                    )
                )

        if event_type == lavalink.LavalinkEvents.TRACK_EXCEPTION:
            message_channel = player.fetch("channel")
            if message_channel:
                message_channel = self.bot.get_channel(message_channel)
                embed = discord.Embed(
                    colour=message_channel.guild.me.top_role.colour,
                    title="Track Error",
                    description="{}\n**[{}]({})**".format(
                        extra, player.current.title, player.current.uri
                    ),
                )
                embed.set_footer(text="Skipping...")
                await message_channel.send(embed=embed)
                await player.skip()

    @commands.group()
    @commands.guild_only()
    async def audioset(self, ctx):
        """Music configuration options."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @audioset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def dj(self, ctx):
        """Toggle DJ mode (users need a role to use audio commands)."""
        dj_role_id = await self.config.guild(ctx.guild).dj_role()
        if dj_role_id is None:
            await self._embed_msg(
                ctx, "Please set a role to use with DJ mode. Enter the role name now."
            )

            def check(m):
                return m.author == ctx.author

            try:
                dj_role = await ctx.bot.wait_for("message", timeout=15.0, check=check)
                dj_role_obj = discord.utils.get(ctx.guild.roles, name=dj_role.content)
                if dj_role_obj is None:
                    return await self._embed_msg(ctx, "No role with that name.")
                await ctx.invoke(self.role, dj_role_obj)
            except asyncio.TimeoutError:
                return await self._embed_msg(ctx, "No role entered, try again later.")

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        await self.config.guild(ctx.guild).dj_enabled.set(not dj_enabled)
        await self._embed_msg(ctx, "DJ role enabled: {}.".format(not dj_enabled))

    @audioset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx, role_name: discord.Role):
        """Sets the role to use for DJ mode."""
        await self.config.guild(ctx.guild).dj_role.set(role_name.id)
        dj_role_id = await self.config.guild(ctx.guild).dj_role()
        dj_role_obj = discord.utils.get(ctx.guild.roles, id=dj_role_id)
        await self._embed_msg(ctx, "DJ role set to: {}.".format(dj_role_obj.name))

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def jukebox(self, ctx, price: int):
        """Set a price for queueing songs for non-mods. 0 to disable."""
        if price < 0:
            return await self._embed_msg(ctx, "Can't be less than zero.")
        if price == 0:
            jukebox = False
            await self._embed_msg(ctx, "Jukebox mode disabled.")
        else:
            jukebox = True
            await self._embed_msg(
                ctx,
                "Track queueing command price set to {} {}.".format(
                    price, await bank.get_currency_name(ctx.guild)
                ),
            )

        await self.config.guild(ctx.guild).jukebox_price.set(price)
        await self.config.guild(ctx.guild).jukebox.set(jukebox)

    @audioset.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def notify(self, ctx):
        """Toggle song announcement and other bot messages."""
        notify = await self.config.guild(ctx.guild).notify()
        await self.config.guild(ctx.guild).notify.set(not notify)
        await self._embed_msg(ctx, "Verbose mode on: {}.".format(not notify))

    @audioset.command()
    async def settings(self, ctx):
        """Show the current settings."""
        data = await self.config.guild(ctx.guild).all()
        global_data = await self.config.all()
        dj_role_obj = discord.utils.get(ctx.guild.roles, id=data["dj_role"])
        dj_enabled = data["dj_enabled"]
        jukebox = data["jukebox"]
        jukebox_price = data["jukebox_price"]
        jarbuild = redbot.core.__version__

        vote_percent = data["vote_percent"]
        msg = "```ini\n" "----Server Settings----\n"
        if dj_enabled:
            msg += "DJ Role:          [{}]\n".format(dj_role_obj.name)
        if jukebox:
            msg += "Jukebox:          [{0}]\n".format(jukebox)
            msg += "Command price:    [{0}]\n".format(jukebox_price)
        msg += (
            "Repeat:           [{repeat}]\n"
            "Shuffle:          [{shuffle}]\n"
            "Song notify msgs: [{notify}]\n"
            "Songs as status:  [{status}]\n".format(**global_data, **data)
        )
        if vote_percent > 0:
            msg += (
                "Vote skip:        [{vote_enabled}]\n" "Skip percentage:  [{vote_percent}%]\n"
            ).format(**data)
        msg += (
            "---Lavalink Settings---\n"
            "Cog version:      [{}]\n"
            "Jar build:        [{}]\n"
            "External server:  [{use_external_lavalink}]```"
        ).format(__version__, jarbuild, **global_data)

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, description=msg)
        return await ctx.send(embed=embed)

    @audioset.command()
    @checks.mod_or_permissions(administrator=True)
    async def vote(self, ctx, percent: int):
        """Percentage needed for non-mods to skip songs. 0 to disable."""
        if percent < 0:
            return await self._embed_msg(ctx, "Can't be less than zero.")
        elif percent > 100:
            percent = 100
        if percent == 0:
            enabled = False
            await self._embed_msg(
                ctx, "Voting disabled. All users can use queue management commands."
            )
        else:
            enabled = True
            await self._embed_msg(ctx, "Vote percentage set to {}%.".format(percent))

        await self.config.guild(ctx.guild).vote_percent.set(percent)
        await self.config.guild(ctx.guild).vote_enabled.set(enabled)

    @checks.is_owner()
    @audioset.command()
    async def status(self, ctx):
        """Enables/disables songs' titles as status."""
        status = await self.config.status()
        await self.config.status.set(not status)
        await self._embed_msg(ctx, "Song titles as status: {}.".format(not status))

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
                server_list.append(
                    "{} [`{}`]: **[{}]({})**".format(
                        p.channel.guild.name, connect_dur, p.current.title, p.current.uri
                    )
                )
            except AttributeError:
                server_list.append(
                    "{} [`{}`]: **{}**".format(
                        p.channel.guild.name, connect_dur, "Nothing playing."
                    )
                )
        if server_num == 0:
            servers = "Not connected anywhere."
        else:
            servers = "\n".join(server_list)
        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour,
            title="Connected in {} servers:".format(server_num),
            description=servers,
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def bump(self, ctx, index: int):
        """Bump a song number to the top of the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(ctx, "You must be in the voice channel to bump a song.")
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to bump songs.")
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(
                ctx, "Song number must be greater than 1 and within the queue limit."
            )

        bump_index = index - 1
        bump_song = player.queue[bump_index]
        player.queue.insert(0, bump_song)
        removed = player.queue.pop(index)
        await self._embed_msg(ctx, "Moved {} to the top of the queue.".format(removed.title))

    @commands.command(aliases=["dc"])
    @commands.guild_only()
    async def disconnect(self, ctx):
        """Disconnect from the voice channel."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if self._player_check(ctx):
            if dj_enabled:
                if not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(ctx, "You need the DJ role to disconnect.")
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, "There are other people listening to music.")
            else:
                await lavalink.get_player(ctx.guild.id).stop()
                return await lavalink.get_player(ctx.guild.id).disconnect()

    @commands.command(aliases=["np", "n", "song"])
    @commands.guild_only()
    async def now(self, ctx):
        """Now playing."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
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
            song = "**[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`".format(
                player.current.title, player.current.uri, player.current.requester, arrow, pos, dur
            )
        else:
            song = "Nothing."

        if player.fetch("np_message") is not None:
            try:
                await player.fetch("np_message").delete()
            except discord.errors.NotFound:
                pass

        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour, title="Now Playing", description=song
        )
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
            for i in range(4):
                await message.add_reaction(expected[i])

        def check(r, u):
            return (
                r.message.id == message.id
                and u == ctx.message.author
                and any(e in str(r.emoji) for e in expected)
            )

        try:
            (r, u) = await self.bot.wait_for("reaction_add", check=check, timeout=10.0)
        except asyncio.TimeoutError:
            return await self._clear_react(message)
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
            return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, "You must be in the voice channel to pause the music."
            )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, "You need the DJ role to pause songs.")

        command = ctx.invoked_with
        if player.current and not player.paused and command != "resume":
            await player.pause()
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Track Paused",
                description="**[{}]({})**".format(player.current.title, player.current.uri),
            )
            return await ctx.send(embed=embed)

        if player.paused and command != "pause":
            await player.pause(False)
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Track Resumed",
                description="**[{}]({})**".format(player.current.title, player.current.uri),
            )
            return await ctx.send(embed=embed)

        if player.paused and command == "pause":
            return await self._embed_msg(ctx, "Track is paused.")
        if player.current and command == "resume":
            return await self._embed_msg(ctx, "Track is playing.")
        await self._embed_msg(ctx, "Nothing playing.")

    @commands.command()
    @commands.guild_only()
    async def percent(self, ctx):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
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
            return await self._embed_msg(ctx, "Nothing in the queue.")

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
            colour=ctx.guild.me.top_role.colour,
            title="Queued and playing songs:",
            description=queue_user_list,
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def play(self, ctx, *, query):
        """Play a URL or search for a song."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        jukebox_price = await self.config.guild(ctx.guild).jukebox_price()
        shuffle = await self.config.guild(ctx.guild).shuffle()
        if not self._player_check(ctx):
            try:
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, "Connect to a voice channel first.")
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to queue songs.")
        player = lavalink.get_player(ctx.guild.id)
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, "You must be in the voice channel to use the play command."
            )
        if not await self._currency_check(ctx, jukebox_price):
            return

        if not query:
            return await self._embed_msg(ctx, "No songs to play.")
        query = query.strip("<>")
        if not query.startswith("http"):
            query = "ytsearch:{}".format(query)

        tracks = await player.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, "Nothing found.")

        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        before_queue_length = len(player.queue) + 1

        if "list" in query and "ytsearch:" not in query:
            for track in tracks:
                player.add(ctx.author, track)
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Playlist Enqueued",
                description="Added {} tracks to the queue.".format(len(tracks)),
            )
            if not shuffle and queue_duration > 0:
                embed.set_footer(
                    text="{} until start of playlist playback: starts at #{} in queue".format(
                        queue_total_duration, before_queue_length
                    )
                )
            if not player.current:
                await player.play()
        else:
            single_track = tracks[0]
            player.add(ctx.author, single_track)
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Track Enqueued",
                description="**[{}]({})**".format(single_track.title, single_track.uri),
            )
            if not shuffle and queue_duration > 0:
                embed.set_footer(
                    text="{} until track playback: #{} in queue".format(
                        queue_total_duration, before_queue_length
                    )
                )
            elif queue_duration > 0:
                embed.set_footer(text="#{} in queue".format(len(player.queue) + 1))
            if not player.current:
                await player.play()
        await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    async def playlist(self, ctx):
        """Playlist configuration options."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @playlist.command(name="append")
    async def _playlist_append(self, ctx, playlist_name, *url):
        """Add a song URL, playlist link, or quick search to the end of a saved playlist."""
        if not await self._playlist_check(ctx):
            return
        async with self.config.guild(ctx.guild).playlists() as playlists:
            try:
                if playlists[playlist_name][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(ctx, "You are not the author of that playlist.")
                player = lavalink.get_player(ctx.guild.id)
                to_append = await self._playlist_tracks(ctx, player, url)
                if not to_append:
                    return
                track_list = playlists[playlist_name]["tracks"]
                if track_list:
                    playlists[playlist_name]["tracks"] = track_list + to_append
                else:
                    playlists[playlist_name]["tracks"] = to_append
            except KeyError:
                return await self._embed_msg(ctx, "No playlist with that name.")
        if playlists[playlist_name]["playlist_url"] is not None:
            playlists[playlist_name]["playlist_url"] = None
        if len(to_append) == 1:
            track_title = to_append[0]["info"]["title"]
            return await self._embed_msg(
                ctx, "{} appended to {}.".format(track_title, playlist_name)
            )
        await self._embed_msg(
            ctx, "{} tracks appended to {}.".format(len(to_append), playlist_name)
        )

    @playlist.command(name="create")
    async def _playlist_create(self, ctx, playlist_name):
        """Create an empty playlist."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to save playlists.")
        async with self.config.guild(ctx.guild).playlists() as playlists:
            if playlist_name in playlists:
                return await self._embed_msg(
                    ctx, "Playlist name already exists, try again with a different name."
                )
        playlist_list = self._to_json(ctx, None, None)
        playlists[playlist_name] = playlist_list
        await self._embed_msg(ctx, "Empty playlist {} created.".format(playlist_name))

    @playlist.command(name="delete")
    async def _playlist_delete(self, ctx, playlist_name):
        """Delete a saved playlist."""
        async with self.config.guild(ctx.guild).playlists() as playlists:
            try:
                if playlists[playlist_name][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(ctx, "You are not the author of that playlist.")
                del playlists[playlist_name]
            except KeyError:
                return await self._embed_msg(ctx, "No playlist with that name.")
        await self._embed_msg(ctx, "{} playlist deleted.".format(playlist_name))

    @playlist.command(name="info")
    async def _playlist_info(self, ctx, playlist_name):
        """Retrieve information from a saved playlist."""
        playlists = await self.config.guild(ctx.guild).playlists.get_raw()
        try:
            author_id = playlists[playlist_name]["author"]
        except KeyError:
            return await self._embed_msg(ctx, "No playlist with that name.")
        author_obj = self.bot.get_user(author_id)
        playlist_url = playlists[playlist_name]["playlist_url"]
        try:
            track_len = len(playlists[playlist_name]["tracks"])
        except TypeError:
            track_len = 0
        if playlist_url is None:
            playlist_url = "**Custom playlist.**"
        else:
            playlist_url = "URL: <{}>".format(playlist_url)
        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour,
            title="Playlist info for {}:".format(playlist_name),
            description="Author: **{}**\n{}".format(author_obj, playlist_url),
        )
        embed.set_footer(text="{} track(s)".format(track_len))
        await ctx.send(embed=embed)

    @playlist.command(name="list")
    async def _playlist_list(self, ctx):
        """List saved playlists."""
        playlists = await self.config.guild(ctx.guild).playlists.get_raw()
        playlist_list = []
        for playlist_name in playlists:
            playlist_list.append(playlist_name)
        abc_names = sorted(playlist_list, key=str.lower)
        all_playlists = ", ".join(abc_names)
        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour,
            title="Playlists for {}:".format(ctx.guild.name),
            description=all_playlists,
        )
        await ctx.send(embed=embed)

    @playlist.command(name="queue")
    async def _playlist_queue(self, ctx, playlist_name=None):
        """Save the queue to a playlist."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to save playlists.")
        async with self.config.guild(ctx.guild).playlists() as playlists:
            if playlist_name in playlists:
                return await self._embed_msg(
                    ctx, "Playlist name already exists, try again with a different name."
                )
            if not self._player_check(ctx):
                return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        tracklist = []
        np_song = self._track_creator(player, "np")
        tracklist.append(np_song)
        for track in player.queue:
            queue_idx = player.queue.index(track)
            track_obj = self._track_creator(player, queue_idx)
            tracklist.append(track_obj)
        if not playlist_name:
            await self._embed_msg(ctx, "Please enter a name for this playlist.")

            def check(m):
                return m.author == ctx.author

            try:
                playlist_name_msg = await ctx.bot.wait_for("message", timeout=15.0, check=check)
                playlist_name = str(playlist_name_msg.content)
                if len(playlist_name) > 20:
                    return await self._embed_msg(ctx, "Try the command again with a shorter name.")
                if playlist_name in playlists:
                    return await self._embed_msg(
                        ctx, "Playlist name already exists, try again with a different name."
                    )
            except asyncio.TimeoutError:
                return await self._embed_msg(ctx, "No playlist name entered, try again later.")
        playlist_list = self._to_json(ctx, None, tracklist)
        async with self.config.guild(ctx.guild).playlists() as playlists:
            playlists[playlist_name] = playlist_list
        await self._embed_msg(
            ctx,
            "Playlist {} saved from current queue: {} tracks added.".format(
                playlist_name, len(tracklist)
            ),
        )

    @playlist.command(name="remove")
    async def _playlist_remove(self, ctx, playlist_name, url):
        """Remove a song from a playlist by url."""
        async with self.config.guild(ctx.guild).playlists() as playlists:
            try:
                if playlists[playlist_name][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(ctx, "You are not the author of that playlist.")
            except KeyError:
                return await self._embed_msg(ctx, "No playlist with that name.")
            track_list = playlists[playlist_name]["tracks"]
            clean_list = [track for track in track_list if not url == track["info"]["uri"]]
            if len(playlists[playlist_name]["tracks"]) == len(clean_list):
                return await self._embed_msg(ctx, "URL not in playlist.")
            del_count = len(playlists[playlist_name]["tracks"]) - len(clean_list)
            if not clean_list:
                del playlists[playlist_name]
                return await self._embed_msg(ctx, "No songs left, removing playlist.")
            playlists[playlist_name]["tracks"] = clean_list
        if playlists[playlist_name]["playlist_url"] is not None:
            playlists[playlist_name]["playlist_url"] = None
        if del_count > 1:
            await self._embed_msg(
                ctx,
                "{} entries have been removed from the {} playlist.".format(
                    del_count, playlist_name
                ),
            )
        else:
            await self._embed_msg(
                ctx, "The track has been removed from the {} playlist.".format(playlist_name)
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
                playlists[playlist_name] = playlist_list
                return await self._embed_msg(
                    ctx,
                    "Playlist {} saved: {} tracks added.".format(playlist_name, len(tracklist)),
                )

    @playlist.command(name="start")
    async def _playlist_start(self, ctx, playlist_name=None):
        """Load a playlist into the queue."""
        if not await self._playlist_check(ctx):
            return
        playlists = await self.config.guild(ctx.guild).playlists.get_raw()
        author_obj = self.bot.get_user(ctx.author.id)
        track_count = 0
        try:
            player = lavalink.get_player(ctx.guild.id)
            for track in playlists[playlist_name]["tracks"]:
                player.add(author_obj, lavalink.rest_api.Track(data=track))
                track_count = track_count + 1
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Playlist Enqueued",
                description="Added {} tracks to the queue.".format(track_count),
            )
            await ctx.send(embed=embed)
            if not player.current:
                await player.play()
        except TypeError:
            await ctx.invoke(self.play, query=playlists[playlist_name]["playlist_url"])
        except KeyError:
            await self._embed_msg(ctx, "That playlist doesn't exist.")

    @checks.is_owner()
    @playlist.command(name="upload")
    async def _playlist_upload(self, ctx):
        """Convert a Red v2 playlist file to a playlist."""
        if not await self._playlist_check(ctx):
            return
        player = lavalink.get_player(ctx.guild.id)
        await self._embed_msg(
            ctx, "Please upload the playlist file. Any other message will cancel this operation."
        )

        def check(m):
            return m.author == ctx.author

        try:
            file_message = await ctx.bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await self._embed_msg(ctx, "No file detected, try again later.")
        try:
            file_url = file_message.attachments[0].url
        except IndexError:
            return await self._embed_msg(ctx, "Upload canceled.")
        v2_playlist_name = (file_url.split("/")[6]).split(".")[0]
        file_suffix = file_url.rsplit(".", 1)[1]
        if file_suffix != "txt":
            return await self._embed_msg(ctx, "Only playlist files can be uploaded.")
        async with self.session.request("GET", file_url) as r:
            v2_playlist = await r.json(content_type="text/plain")
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
                            ctx, "A playlist already exists with this name."
                        )
                except KeyError:
                    pass
            embed1 = discord.Embed(
                colour=ctx.guild.me.top_role.colour, title="Please wait, adding tracks..."
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
                        colour=ctx.guild.me.top_role.colour,
                        title="Loading track {}/{}...".format(
                            track_count, len(v2_playlist["playlist"])
                        ),
                    )
                    await playlist_msg.edit(embed=embed2)
            if not track_list:
                return await self._embed_msg(ctx, "No tracks found.")
            playlist_list = self._to_json(ctx, v2_playlist_url, track_list)
            async with self.config.guild(ctx.guild).playlists() as v3_playlists:
                v3_playlists[v2_playlist_name] = playlist_list
            if len(v2_playlist["playlist"]) != track_count:
                bad_tracks = len(v2_playlist["playlist"]) - track_count
                msg = (
                    "Added {} tracks from the {} playlist. {} track(s) could not "
                    "be loaded.".format(track_count, v2_playlist_name, bad_tracks)
                )
            else:
                msg = "Added {} tracks from the {} playlist.".format(track_count, v2_playlist_name)
            embed3 = discord.Embed(
                colour=ctx.guild.me.top_role.colour, title="Playlist Saved", description=msg
            )
            await playlist_msg.edit(embed=embed3)
        else:
            await ctx.invoke(self._playlist_save, v2_playlist_name, v2_playlist_url)

    async def _playlist_check(self, ctx):
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        jukebox_price = await self.config.guild(ctx.guild).jukebox_price()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                await self._embed_msg(ctx, "You need the DJ role to use playlists.")
                return False
        if not self._player_check(ctx):
            try:
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                await self._embed_msg(ctx, "Connect to a voice channel first.")
                return False
        player = lavalink.get_player(ctx.guild.id)
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            await self._embed_msg(
                ctx, "You must be in the voice channel to use the playlist command."
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
            return await self._embed_msg(ctx, "Nothing found.")
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
        """Skips to the start of the previously played track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, "You need the DJ role to skip songs.")
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, "You must be in the voice channel to skip the music."
            )
        if shuffle:
            return await self._embed_msg(ctx, "Turn shuffle off to use this command.")
        if player.fetch("prev_song") is None:
            return await self._embed_msg(ctx, "No previous track.")
        else:
            last_track = await player.get_tracks(player.fetch("prev_song"))
            player.add(player.fetch("prev_requester"), last_track[0])
            queue_len = len(player.queue)
            bump_song = player.queue[-1]
            player.queue.insert(0, bump_song)
            player.queue.pop(queue_len)
            await player.skip()
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Replaying Track",
                description="**[{}]({})**".format(player.current.title, player.current.uri),
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx, page: int = 1):
        """Lists the queue."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "There's nothing in the queue.")
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, "There's nothing in the queue.")
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
            return await self._embed_msg(ctx, "There's nothing in the queue.")
        pos = lavalink.utils.format_time(player.position)

        if player.current.is_stream:
            dur = "LIVE"
        else:
            dur = lavalink.utils.format_time(player.current.length)

        if player.current.is_stream:
            queue_list += "**Currently livestreaming:** **[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`\n\n".format(
                player.current.title, player.current.uri, player.current.requester, arrow, pos, dur
            )
        else:
            queue_list += "Playing: **[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`\n\n".format(
                player.current.title, player.current.uri, player.current.requester, arrow, pos, dur
            )

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
            queue_list += "`{}.` **[{}]({})**, requested by **{}**\n".format(
                track_idx, track_title, track.uri, req_user
            )

        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour,
            title="Queue for " + ctx.guild.name,
            description=queue_list,
        )
        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        text = "Page {}/{} | {} tracks, {} remaining".format(
            page_num, queue_num_pages, len(player.queue) + 1, queue_total_duration
        )
        if repeat:
            text += " | Repeat: \N{WHITE HEAVY CHECK MARK}"
        if shuffle:
            text += " | Shuffle: \N{WHITE HEAVY CHECK MARK}"
        embed.set_footer(text=text)
        return embed

    @commands.command()
    @commands.guild_only()
    async def repeat(self, ctx):
        """Toggles repeat."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, "You need the DJ role to toggle repeat.")
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
                    ctx, "You must be in the voice channel to toggle repeat."
                )
        await self._embed_msg(ctx, "Repeat songs: {}.".format(repeat))

    @commands.command()
    @commands.guild_only()
    async def remove(self, ctx, index: int):
        """Remove a specific song number from the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, "Nothing queued.")
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to remove songs.")
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, "You must be in the voice channel to manage the queue."
            )
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(
                ctx, "Song number must be greater than 1 and within the queue limit."
            )
        index -= 1
        removed = player.queue.pop(index)
        await self._embed_msg(ctx, "Removed {} from the queue.".format(removed.title))

    @commands.command()
    @commands.guild_only()
    async def search(self, ctx, *, query):
        """Pick a song with a search.
        Use [p]search list <search term> to queue all songs found on YouTube.
        [p]search sc <search term> will search SoundCloud instead of YouTube.
        """
        if not self._player_check(ctx):
            try:
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, "Connect to a voice channel first.")
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(ctx, "You must be in the voice channel to enqueue songs.")
        await self._data_check(ctx)

        query = query.strip("<>")
        if query.startswith("list "):
            query = "ytsearch:{}".format(query.lstrip("list "))
            tracks = await player.get_tracks(query)
            if not tracks:
                return await self._embed_msg(ctx, "Nothing found 👀")
            songembed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Queued {} track(s).".format(len(tracks)),
            )
            queue_duration = await self._queue_duration(ctx)
            queue_total_duration = lavalink.utils.format_time(queue_duration)
            if not shuffle and queue_duration > 0:
                songembed.set_footer(
                    text="{} until start of search playback: starts at #{} in queue".format(
                        queue_total_duration, (len(player.queue) + 1)
                    )
                )
            for track in tracks:
                player.add(ctx.author, track)
                if not player.current:
                    await player.play()
            return await ctx.send(embed=songembed)
        if query.startswith("sc "):
            query = "scsearch:{}".format(query.lstrip("sc "))
        elif not query.startswith("http"):
            query = "ytsearch:{}".format(query)
        tracks = await player.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, "Nothing found 👀")

        len_search_pages = math.ceil(len(tracks) / 5)
        search_page_list = []
        for page_num in range(1, len_search_pages + 1):
            embed = await self._build_search_page(ctx, tracks, page_num)
            search_page_list.append(embed)

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await menu(ctx, search_page_list, DEFAULT_CONTROLS)

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
                await _search_button_action(ctx, tracks, emoji, page)
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

        async def _search_button_action(ctx, tracks, emoji, page):
            player = lavalink.get_player(ctx.guild.id)
            jukebox_price = await self.config.guild(ctx.guild).jukebox_price()
            shuffle = await self.config.guild(ctx.guild).shuffle()
            if not await self._currency_check(ctx, jukebox_price):
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

            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Track Enqueued",
                description="**[{}]({})**".format(search_choice.title, search_choice.uri),
            )
            queue_duration = await self._queue_duration(ctx)
            queue_total_duration = lavalink.utils.format_time(queue_duration)
            if not shuffle and queue_duration > 0:
                embed.set_footer(
                    text="{} until track playback: #{} in queue".format(
                        queue_total_duration, (len(player.queue) + 1)
                    )
                )
            elif queue_duration > 0:
                embed.set_footer(text="#{} in queue".format(len(player.queue) + 1))

            player.add(ctx.author, search_choice)
            if not player.current:
                await player.play()
            await ctx.send(embed=embed)

        await menu(ctx, search_page_list, SEARCH_CONTROLS)

    async def _build_search_page(self, ctx, tracks, page_num):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        for i, track in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            search_list += "`{0}.` **[{1}]({2})**\n".format(
                search_track_num, track.title, track.uri
            )
        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour, title="Tracks Found:", description=search_list
        )
        embed.set_footer(
            text="Page {}/{} | {} search results".format(page_num, search_num_pages, len(tracks))
        )
        return embed

    @commands.command()
    @commands.guild_only()
    async def seek(self, ctx, seconds: int = 30):
        """Seeks ahead or behind on a track by seconds."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(ctx, "You must be in the voice channel to use seek.")
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, "You need the DJ role to use seek.")
        if player.current:
            if player.current.is_stream:
                return await self._embed_msg(ctx, "Can't seek on a stream.")
            else:
                time_sec = seconds * 1000
                seek = player.position + time_sec
                if seek <= 0:
                    await self._embed_msg(ctx, "Moved {}s to 00:00:00".format(seconds))
                else:
                    await self._embed_msg(
                        ctx, "Moved {}s to {}".format(seconds, lavalink.utils.format_time(seek))
                    )
                return await player.seek(seek)
        else:
            await self._embed_msg(ctx, "Nothing playing.")

    @commands.command()
    @commands.guild_only()
    async def shuffle(self, ctx):
        """Toggles shuffle."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to toggle shuffle.")
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
                    ctx, "You must be in the voice channel to toggle shuffle."
                )
        await self._embed_msg(ctx, "Shuffle songs: {}.".format(shuffle))

    @commands.command(aliases=["forceskip", "fs"])
    @commands.guild_only()
    async def skip(self, ctx):
        """Skips to the next track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, "You must be in the voice channel to skip the music."
            )
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if dj_enabled and not vote_enabled and not await self._can_instaskip(ctx, ctx.author):
            if not await self._is_alone(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to skip songs.")
        if vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                if ctx.author.id in self.skip_votes[ctx.message.guild]:
                    self.skip_votes[ctx.message.guild].remove(ctx.author.id)
                    reply = "I removed your vote to skip."
                else:
                    self.skip_votes[ctx.message.guild].append(ctx.author.id)
                    reply = "You voted to skip."

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
                    await self._embed_msg(ctx, "Vote threshold met.")
                    return await self._skip_action(ctx)
                else:
                    reply += " Votes: %d/%d" % (num_votes, num_members)
                    reply += " (%d%% out of %d%% needed)" % (vote, percent)
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
        dj_role_id = await self.config.guild(ctx.guild).dj_role()
        dj_role_obj = discord.utils.get(ctx.guild.roles, id=dj_role_id)
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
                return await self._embed_msg(ctx, "There's nothing in the queue.")
            time_remain = lavalink.utils.format_time(dur - pos)
            if player.current.is_stream:
                embed = discord.Embed(
                    colour=ctx.guild.me.top_role.colour, title="There's nothing in the queue."
                )
                embed.set_footer(text="Currently livestreaming {}".format(player.current.title))
            else:
                embed = discord.Embed(
                    colour=ctx.guild.me.top_role.colour, title="There's nothing in the queue."
                )
                embed.set_footer(text="{} left on {}".format(time_remain, player.current.title))
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour,
            title="Track Skipped",
            description="**[{}]({})**".format(player.current.title, player.current.uri),
        )
        await ctx.send(embed=embed)
        await player.skip()

    @commands.command(aliases=["s"])
    @commands.guild_only()
    async def stop(self, ctx):
        """Stops playback and clears the queue."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, "Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx, "You must be in the voice channel to stop the music."
            )
        if vote_enabled or vote_enabled and dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(
                    ctx, "There are other people listening - vote to skip instead."
                )
        if dj_enabled and not vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(ctx, "You need the DJ role to stop the music.")
        if player.is_playing:
            await self._embed_msg(ctx, "Stopping...")
            await player.stop()
            player.store("prev_requester", None)
            player.store("prev_song", None)
            player.store("playing_song", None)
            player.store("requester", None)

    @commands.command()
    @commands.guild_only()
    async def volume(self, ctx, vol: int = None):
        """Sets the volume, 1% - 150%."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if not vol:
            vol = await self.config.guild(ctx.guild).volume()
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Current Volume:",
                description=str(vol) + "%",
            )
            if not self._player_check(ctx):
                embed.set_footer(text="Nothing playing.")
            return await ctx.send(embed=embed)
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx, "You must be in the voice channel to change the volume."
                )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, "You need the DJ role to change the volume.")
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
            colour=ctx.guild.me.top_role.colour, title="Volume:", description=str(vol) + "%"
        )
        if not self._player_check(ctx):
            embed.set_footer(text="Nothing playing.")
        await ctx.send(embed=embed)

    @commands.group(aliases=["llset"])
    @commands.guild_only()
    @checks.is_owner()
    async def llsetup(self, ctx):
        """Lavalink server configuration options."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @llsetup.command()
    async def external(self, ctx):
        """Toggles using external lavalink servers."""
        external = await self.config.use_external_lavalink()
        await self.config.use_external_lavalink.set(not external)
        if external:
            await self.config.host.set("localhost")
            await self.config.password.set("youshallnotpass")
            await self.config.rest_port.set(2333)
            await self.config.ws_port.set(2332)
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="External lavalink server: {}.".format(not external),
            )
            embed.set_footer(text="Defaults reset.")
            return await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, "External lavalink server: {}.".format(not external))

    @llsetup.command()
    async def host(self, ctx, host):
        """Set the lavalink server host."""
        await self.config.host.set(host)
        if await self._check_external():
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour, title="Host set to {}.".format(host)
            )
            embed.set_footer(text="External lavalink server set to True.")
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, "Host set to {}.".format(host))

    @llsetup.command()
    async def password(self, ctx, password):
        """Set the lavalink server password."""
        await self.config.password.set(str(password))
        if await self._check_external():
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Server password set to {}.".format(password),
            )
            embed.set_footer(text="External lavalink server set to True.")
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, "Server password set to {}.".format(password))

    @llsetup.command()
    async def restport(self, ctx, rest_port: int):
        """Set the lavalink REST server port."""
        await self.config.rest_port.set(rest_port)
        if await self._check_external():
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour, title="REST port set to {}.".format(rest_port)
            )
            embed.set_footer(text="External lavalink server set to True.")
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, "REST port set to {}.".format(rest_port))

    @llsetup.command()
    async def wsport(self, ctx, ws_port: int):
        """Set the lavalink websocket server port."""
        await self.config.ws_port.set(ws_port)
        if await self._check_external():
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title="Websocket port set to {}.".format(ws_port),
            )
            embed.set_footer(text="External lavalink server set to True.")
            await ctx.send(embed=embed)
        else:
            await self._embed_msg(ctx, "Websocket port set to {}.".format(ws_port))

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
                    ctx, "Not enough {} ({} required).".format(credits_name, jukebox_price)
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
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title=title)
        await ctx.send(embed=embed)

    async def _get_playing(self, ctx):
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            return len([player for p in lavalink.players if p.is_playing])
        else:
            return 0

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
    def _player_check(ctx):
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except KeyError:
            return False

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

    async def on_voice_state_update(self, member, before, after):
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

    def __unload(self):
        self.session.close()
        lavalink.unregister_event_listener(self.event_handler)
        self.bot.loop.create_task(lavalink.close())
        shutdown_lavalink_server()
