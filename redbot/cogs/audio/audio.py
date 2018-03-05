# Lavalink.py cog for Red v3 beta 7+
# Cog base thanks to Kromatic's example cog.
import asyncio
import datetime
import discord
import heapq
import lavalink
import math
from discord.ext import commands
from redbot.core import Config, checks

__version__ = "2.0.2.9.b"
__author__ = ["aikaterna", "billy/bollo/ati"]


LAVALINK_BUILD = 3065


class Audio:
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2711759128, force_registration=True)

        default_global = {
            "host": 'localhost',
            "port": '2332',
            "passw": 'youshallnotpass',
            "status": False
        }

        default_guild = {
            "notify": False,
            "repeat": False,
            "shuffle": False,
            "volume": 100
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self._lavalink = None
        self._lavalink_build_url = (
            "https://ci.fredboat.com/repository/download/"
            "Lavalink_Build/{}:id/Lavalink.jar"
        ).format(LAVALINK_BUILD)

    async def init_config(self):
        host = await self.config.host()
        passw = await self.config.passw()
        port = await self.config.port()

        try:
            self._lavalink = lavalink.Client(
                bot=self.bot, password=passw, host=host, port=port, loop=self.bot.loop
            )
        except RuntimeError:
            pass

        self.bot.lavalink.client.register_hook(self.track_hook)

    @property
    def lavalink(self):
        return self._lavalink

    async def track_hook(self, player, event):
        notify = await self.config.guild(self.bot.get_guild(player.fetch('guild'))).notify()
        status = await self.config.status()
        playing_servers = await self._get_playing()
        get_players = [p for p in self.bot.lavalink.players._players.values() if p.is_playing]
        try:
            get_single_title = get_players[0].current.title
        except IndexError:
            pass

        if event == 'TrackStartEvent' and notify:
            c = player.fetch('channel')
            if c:
                c = self.bot.get_channel(c)
                if player.fetch('notify_message') is not None:
                    try:
                        await player.fetch('notify_message').delete()
                    except discord.errors.NotFound:
                        pass
                embed = discord.Embed(colour=c.guild.me.top_role.colour, title='Now Playing',
                                      description='**[{}]({})**'.format(player.current.title, player.current.uri))
                notify_message = await c.send(embed=embed)
                player.store('notify_message', notify_message)

        if event == 'TrackStartEvent' and status:
            if playing_servers > 1:
                await self.bot.change_presence(game=discord.Game(name='music in {} servers'.format(playing_servers)))
            else:
                await self.bot.change_presence(game=discord.Game(name=get_single_title, type=2))

        if event == 'QueueEndEvent' and notify:
            c = player.fetch('channel')
            if c:
                c = self.bot.get_channel(c)
                if c:
                    embed = discord.Embed(colour=c.guild.me.top_role.colour, title='Queue ended.')
                    await c.send(embed=embed)

        if event == 'QueueEndEvent' and status:
            await asyncio.sleep(1)
            if playing_servers == 0:
                await self.bot.change_presence(game=None)
            if playing_servers == 1:
                await self.bot.change_presence(game=discord.Game(name=get_single_title, type=2))
            if playing_servers > 1:
                await self.bot.change_presence(game=discord.Game(name='music in {} servers'.format(playing_servers)))

    @commands.group()
    @checks.is_owner()
    async def audioset(self, ctx):
        """Music configuration options."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @audioset.command()
    async def notify(self, ctx):
        """Toggle song announcement and other bot messages."""
        notify = await self.config.guild(ctx.guild).notify()
        await self.config.guild(ctx.guild).notify.set(not notify)
        get_notify = await self.config.guild(ctx.guild).notify()
        await self._embed_msg(ctx, 'Verbose mode on: {}.'.format(get_notify))

    @audioset.command()
    async def settings(self, ctx):
        """Show the current settings."""
        notify = await self.config.guild(ctx.guild).notify()
        status = await self.config.status()
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()

        msg = '```ini\n'
        msg += '----Guild Settings----\n'
        msg += 'audioset notify: [{}]\n'.format(notify)
        msg += 'audioset status: [{}]\n'.format(status)
        msg += 'Repeat:          [{}]\n'.format(repeat)
        msg += 'Shuffle:         [{}]\n'.format(shuffle)
        msg += '---Lavalink Settings---\n'
        msg += 'Cog version: {}\n'.format(__version__)
        msg += 'Pip version: {}\n```'.format(lavalink.__version__)

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, description=msg)
        return await ctx.send(embed=embed)

    @audioset.command()
    @checks.is_owner()
    async def status(self, ctx):
        """Enables/disables songs' titles as status."""
        status = await self.config.status()
        await self.config.status.set(not status)
        get_status = await self.config.status()
        await self._embed_msg(ctx, 'Song titles as status: {}'.format(get_status))

    @commands.command()
    async def audiostats(self, ctx):
        """Audio stats."""
        server_num = await self._get_playing()
        server_ids = self.bot.lavalink.players._players
        server_list = []

        for k, v in server_ids.items():
            guild_id = k
            player = v
            connect_start = v.fetch('connect')
            try:
                connect_dur = self._dynamic_time((datetime.datetime.utcnow() - connect_start).seconds)
            except TypeError:
                connect_dur = 0
            try:
                server_list.append('{} [`{}`]: **[{}]({})**'.format(self.bot.get_guild(guild_id).name, connect_dur, 
                                   v.current.title, v.current.uri))
            except AttributeError:
                pass
            servers = '\n'.join(server_list)
        if server_list == []:
            servers = 'Not connected anywhere.'
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Playing in {} servers:'.format(server_num),
                              description=servers)
        await ctx.send(embed=embed)

    @commands.command()
    async def bump(self, ctx, index: int):
        """Bump a song number to the top of the queue."""
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.queue:
            return await self._embed_msg(ctx, 'Nothing queued.')

        if index > len(player.queue) or index < 1:
            return await self._embed_msg(ctx, 'Song number must be greater than 1 and within the queue limit.')

        bump_index = index - 1
        bump_song = self.bot.lavalink.players.get(ctx.guild.id).queue[bump_index]
        player.queue.insert(0, bump_song)
        removed = player.queue.pop(index)
        await self._embed_msg(ctx, 'Moved **' + removed.title + '** to the top of the queue.')

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        """Disconnect from the voice channel."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        await player.disconnect()
        player.queue.clear()
        player.store('song', None)
        player.store('requester', None)
        await self.bot.lavalink.client._trigger_event("QueueEndEvent", ctx.guild.id)

    @commands.command(aliases=['np', 'n', 'song'])
    async def now(self, ctx):
        """Now playing."""
        expected = ['⏹', '⏸', '⏭']
        emoji = {
            'stop': '⏹',
            'pause': '⏸',
            'next': '⏭'
        }
        player = self.bot.lavalink.players.get(ctx.guild.id)
        song = 'Nothing'
        if player.current:
            arrow = await self._draw_time(ctx)
            pos = lavalink.Utils.format_time(player.position)
            if player.current.stream:
                dur = 'LIVE'
            else:
                dur = lavalink.Utils.format_time(player.current.duration)
        if not player.current:
            song = 'Nothing.'
        else:
            req_user = self.bot.get_user(player.current.requester)
            song = '**[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`'.format(player.current.title, player.current.uri,
                                                                              req_user, arrow, pos, dur)
        if player.fetch('np_message') is not None:
            try:
                await player.fetch('np_message').delete()
            except discord.errors.NotFound:
                pass

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Now Playing', description=song)
        message = await ctx.send(embed=embed)
        player.store('np_message', message)

        def check(r, u):
            return r.message.id == message.id and u == ctx.message.author

        if player.current:
            for i in range(3):
                await message.add_reaction(expected[i])
        try:
            (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=10.0)
        except asyncio.TimeoutError:
            return await self._clear_react(message)

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]

        if react == 'stop':
            await self._clear_react(message)
            await ctx.invoke(self.stop)
        elif react == 'pause':
            await self._clear_react(message)
            await ctx.invoke(self.pause)
        elif react == 'next':
            await self._clear_react(message)
            await ctx.invoke(self.skip)

    @commands.command(aliases=['resume'])
    async def pause(self, ctx):
        """Pause and resume."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to pause the music.')

        if not player.is_playing:
            return

        if player.paused:
            await player.set_pause(False)
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Resumed',
                                  description='**[{}]({})**'.format(player.current.title, player.current.uri))
            message = await ctx.send(embed=embed)
        else:
            await player.set_pause(True)
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Paused',
                                  description='**[{}]({})**'.format(player.current.title, player.current.uri))
            message = await ctx.send(embed=embed)

    @commands.command()
    async def percent(self, ctx):
        """Queue percentage."""
        queue_tracks = self.bot.lavalink.players.get(ctx.guild.id).queue
        queue_len = len(queue_tracks)
        requesters = {'total': 0, 'users': {}}

        async def _usercount(req_username):
            if req_username in requesters['users']:
                requesters['users'][req_username]['songcount'] += 1
                requesters['total'] += 1
            else:
                requesters['users'][req_username] = {}
                requesters['users'][req_username]['songcount'] = 1
                requesters['total'] += 1

        for i in range(queue_len):
            req_username = self.bot.get_user(queue_tracks[i].requester).name
            await _usercount(req_username)
        try:
            req_username = self.bot.get_user(self.bot.lavalink.players.get(ctx.guild.id).current.requester).name
            await _usercount(req_username)
        except AttributeError:
            return await self._embed_msg(ctx, 'Nothing in the queue.')

        for req_username in requesters['users']:
            percentage = float(requesters['users'][req_username]['songcount']) / float(requesters['total'])
            requesters['users'][req_username]['percent'] = round(percentage * 100, 1)

        top_queue_users = heapq.nlargest(20, [(x, requesters['users'][x][y]) for x in requesters['users'] for y in
                                              requesters['users'][x] if y == 'percent'], key=lambda x: x[1])
        queue_user = ["{}: {:g}%".format(x[0], x[1]) for x in top_queue_users]
        queue_user_list = '\n'.join(queue_user)
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Queued and playing songs:',
                              description=queue_user_list)
        await ctx.send(embed=embed)

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query):
        """Play a URL or search for a song."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to use the play command.')

        player.store('channel', ctx.channel.id)
        player.store('guild', ctx.guild.id)
        await self._data_check(ctx)

        if not player.is_connected:
            player.store('connect', datetime.datetime.utcnow())
            await player.connect(ctx.author.voice.channel.id)

        query = query.strip('<>')
        if not query.startswith('http'):
            query = 'ytsearch:{}'.format(query)

        tracks = await self.bot.lavalink.client.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, 'Nothing found 👀')

        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.Utils.format_time(queue_duration)

        if 'list' in query and 'ytsearch:' not in query:
            for track in tracks:
                player.add(requester=ctx.author.id, track=track)
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Playlist Enqueued',
                                  description='Added {} tracks to the queue.'.format(len(tracks)))
            if not shuffle and queue_duration > 0:
                embed.set_footer(text='{} until start of playlist playback'.format(queue_total_duration))
        else:
            player.add(requester=ctx.author.id, track=tracks[0])
            track_title = tracks[0]["info"]["title"]
            track_url = tracks[0]["info"]["uri"]
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Enqueued',
                                  description='[**{}**]({})'.format(track_title, track_url))
            if not shuffle and queue_duration > 0:
                embed.set_footer(text='{} until track playback'.format(queue_total_duration))
        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.play()

    @commands.command(aliases=['q'])
    async def queue(self, ctx, page: int = 1):
        """Lists the queue."""
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, 'There\'s nothing in the queue.')

        if player.current is None:
            return await self._embed_msg(ctx, 'The player is stopped.')

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)
        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue_list = ''
        arrow = await self._draw_time(ctx)
        pos = lavalink.Utils.format_time(player.position)

        if player.current.stream:
            dur = 'LIVE'
        else:
            dur = lavalink.Utils.format_time(player.current.duration)

        if player.current.stream:
            queue_list += '**Currently livestreaming:** [**{}**]({})\nRequested by: **{}**\n\n{}`{}`/`{}`\n\n'.format(
                player.current.title, player.current.uri, self.bot.get_user(player.current.requester), arrow, pos, dur)
        else:
            queue_list += 'Playing: [**{}**]({})\nRequested by: **{}**\n\n{}`{}`/`{}`\n\n'.format(player.current.title,
                                                                                                  player.current.uri,
                                                                                                  self.bot.get_user(
                                                                                                      player.current.requester),
                                                                                                  arrow, pos, dur)

        for i, track in enumerate(player.queue[start:end], start=start):
            req_user = self.bot.get_user(track.requester)
            next = i + 1
            queue_list += '`{}.` [**{}**]({}), requested by **{}**\n'.format(next, track.title, track.uri, req_user)

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Queue for ' + ctx.guild.name,
                              description=queue_list)

        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.Utils.format_time(queue_duration)
        text = 'Page {}/{} | {} tracks, {} remaining'.format(page, pages, len(player.queue), queue_total_duration)
        if repeat:
            text += ' | Repeat: \N{WHITE HEAVY CHECK MARK}'
        if shuffle:
            text += ' | Shuffle: \N{WHITE HEAVY CHECK MARK}'
        embed.set_footer(text=text)
        await ctx.send(embed=embed)

    @commands.command()
    async def repeat(self, ctx):
        """Toggles repeat."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to toggle repeat.')

        repeat = await self.config.guild(ctx.guild).repeat()
        await self.config.guild(ctx.guild).repeat.set(not repeat)
        repeat = await self.config.guild(ctx.guild).repeat()
        if player.repeat != repeat:
            player.repeat = repeat
        await self._embed_msg(ctx, 'Repeat songs: {}.'.format(repeat))

    @commands.command()
    async def remove(self, ctx, index: int):
        """Remove a specific song number from the queue."""
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.queue:
            return await self._embed_msg(ctx, 'Nothing queued.')

        if index > len(player.queue) or index < 1:
            return await self._embed_msg(ctx, 'Song number must be greater than 1 and within the queue limit.')

        index = index - 1
        removed = player.queue.pop(index)

        await self._embed_msg(ctx, 'Removed **' + removed.title + '** from the queue.')

    @commands.command()
    async def search(self, ctx, *, query):
        """Pick a song with a search.
        Use [p]search list <search term> to queue all songs.
        """
        expected = ["1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "⏪", "⏩"]
        emoji = {
            "one": "1⃣",
            "two": "2⃣",
            "three": "3⃣",
            "four": "4⃣",
            "five": "5⃣",
            "back": "⏪",
            "next": "⏩"
        }
        player = self.bot.lavalink.players.get(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        player.store('channel', ctx.channel.id)
        player.store('guild', ctx.guild.id)

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to enqueue songs.')
        if not player.is_connected:
            player.store('connect', datetime.datetime.utcnow())
            await player.connect(ctx.author.voice.channel.id)

        query = query.strip('<>')
        if query.startswith('sc '):
            query = 'scsearch:{}'.format(query.strip('sc '))
        elif not query.startswith('http') or query.startswith('sc '):
            query = 'ytsearch:{}'.format(query)

        tracks = await self.bot.lavalink.client.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, 'Nothing found 👀')
        if 'list' not in query and 'ytsearch:' or 'scsearch:' in query:
            page = 1
            items_per_page = 5
            pages = math.ceil(len(tracks) / items_per_page)
            start = (page - 1) * items_per_page
            end = start + items_per_page

            search_list = ''

            for i, track in enumerate(tracks[start:end], start=start):
                next = i + 1
                search_list += '`{0}.` [**{1}**]({2})\n'.format(next, tracks[i]["info"]["title"],
                                                                tracks[i]["info"]["uri"])

            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Tracks Found:', description=search_list)
            embed.set_footer(text='Page {}/{} | {} search results'.format(page, pages, len(tracks)))
            message = await ctx.send(embed=embed)

            def check(r, u):
                return r.message.id == message.id and u == ctx.message.author

            for i in range(7):
                await message.add_reaction(expected[i])
            try:
                (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await self._clear_react(message)
                return
            reacts = {v: k for k, v in emoji.items()}
            react = reacts[r.emoji]
            if react == 'one':
                await self._search_button(ctx, message, tracks, entry=0)
            elif react == 'two':
                await self._search_button(ctx, message, tracks, entry=1)
            elif react == 'three':
                await self._search_button(ctx, message, tracks, entry=2)
            elif react == 'four':
                await self._search_button(ctx, message, tracks, entry=3)
            elif react == 'five':
                await self._search_button(ctx, message, tracks, entry=4)

            elif react == 'back':
                await self._clear_react(message)
                return
            elif react == 'next':
                await self._clear_react(message)
                return
        else:
            await self._data_check(ctx)
            songembed = discord.Embed(colour=ctx.guild.me.top_role.colour,
                                      title='Queued {} track(s).'.format(len(tracks)))
            queue_duration = await self._queue_duration(ctx)
            queue_total_duration = lavalink.Utils.format_time(queue_duration)
            if not shuffle and queue_duration > 0:
                songembed.set_footer(text='{} until start of search playback'.format(queue_total_duration))
            for track in tracks:
                player.add(requester=ctx.author.id, track=track)
                if not player.is_playing:
                    await player.play()
            message = await ctx.send(embed=songembed)

    async def _search_button(self, ctx, message, tracks, entry: int):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self._clear_react(message)
        player.add(requester=ctx.author.id, track=tracks[entry])
        track_title = tracks[entry]["info"]["title"]
        track_url = tracks[entry]["info"]["uri"]
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Enqueued',
                              description='[**{}**]({})'.format(track_title, track_url))
        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.Utils.format_time(queue_duration)
        if not shuffle:
            embed.set_footer(text='{} until track playback'.format(queue_total_duration))
        return await ctx.send(embed=embed)

    @commands.command()
    async def seek(self, ctx, seconds: int = 5):
        """Seeks ahead or behind on a track by seconds."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to use seek.')
        if player.is_playing:
            if player.current.stream:
                return await self._embed_msg(ctx, 'Can\'t seek on a stream.')
            else:
                time_sec = seconds * 1000
                seek = player.position + time_sec
                if abs(time_sec) > player.position:
                    await self._embed_msg(ctx, 'Moved {}s to 00:00:00'.format(seconds))
                else:
                    await self._embed_msg(ctx, 'Moved {}s to {}'.format(seconds, lavalink.Utils.format_time(seek)))
                return await player.seek(seek)

    @commands.command()
    async def shuffle(self, ctx):
        """Toggles shuffle."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to toggle shuffle.')

        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self.config.guild(ctx.guild).shuffle.set(not shuffle)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        if player.shuffle != shuffle:
            player.shuffle = shuffle
        await self._embed_msg(ctx, 'Shuffle songs: {}.'.format(shuffle))

    @commands.command(aliases=['forceskip', 'fs'])
    async def skip(self, ctx):
        """Skips to the next track."""
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if player.current is None:
            return await self._embed_msg(ctx, 'The player is stopped.')

        if not player.queue:
            pos = player.position
            dur = player.current.duration
            remain = dur - pos
            time_remain = lavalink.Utils.format_time(remain)
            if player.current.stream:
                embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='There\'s nothing in the queue.')
                embed.set_footer(text='Currently livestreaming {}'.format(player.current.title))
                return await ctx.send(embed=embed)
            elif player.current.track:
                embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='There\'s nothing in the queue.')
                embed.set_footer(text='{} left on {}'.format(time_remain, player.current.title))
                return await ctx.send(embed=embed)
            else:
                return await self._embed_msg(ctx, 'There\'s nothing in the queue.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to skip the music.')

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Skipped',
                              description='**[{}]({})**'.format(player.current.title, player.current.uri))
        message = await ctx.send(embed=embed)

        await player.skip()

    @commands.command(aliases=['s'])
    async def stop(self, ctx):
        """Stops playback and clears the queue."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to stop the music.')
        if player.is_playing:
            await self._embed_msg(ctx, 'Stopping...')
            player.queue.clear()
            await player.stop()
            player.store('song', None)
            player.store('requester', None)
            await self.bot.lavalink.client._trigger_event("QueueEndEvent", ctx.guild.id)

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, vol: int = None):
        """Sets the volume, 1% - 150%."""
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await self._embed_msg(ctx, 'You must be in the voice channel to change the volume.')
        if not vol:
            vol = await self.config.guild(ctx.guild).volume()
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Current Volume:',
                                  description=str(vol) + '%')
            if not player.is_playing:
                embed.set_footer(text='Nothing playing.')
            return await ctx.send(embed=embed)
        if int(vol) > 150:
            vol = 150
            await self.config.guild(ctx.guild).volume.set(vol)
            await player.set_volume(vol)
        else:
            await self.config.guild(ctx.guild).volume.set(vol)
            await player.set_volume(vol)
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Volume:', description=str(vol) + '%')
        if not player.is_playing:
            embed.set_footer(text='Nothing playing.')
        await ctx.send(embed=embed)

    @commands.group(aliases=['llset'])
    @checks.is_owner()
    async def llsetup(self, ctx):
        """Lavalink server configuration options."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @llsetup.command()
    async def host(self, ctx, host):
        """Set the lavalink server host."""
        await self.config.host.set(host)
        get_host = await self.config.host()
        await self._embed_msg(ctx, 'Host set to {}.'.format(get_host))

    @llsetup.command()
    async def password(self, ctx, passw):
        """Set the lavalink server password."""
        await self.config.passw.set(str(passw))
        get_passw = await self.config.passw()
        await self._embed_msg(ctx, 'Server password set to {}.'.format(get_passw))

    @llsetup.command()
    async def port(self, ctx, port):
        """Set the lavalink server port."""
        await self.config.port.set(str(port))
        get_port = await self.config.port()
        await self._embed_msg(ctx, 'Port set to {}.'.format(get_port))

    async def _clear_react(self, message):
        try:
            await message.clear_reactions()
        except:
            return

    async def _data_check(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        volume = await self.config.guild(ctx.guild).volume()
        if player.repeat != repeat:
            player.repeat = repeat
        if player.shuffle != shuffle:
            player.shuffle = shuffle
        if player.volume != volume:
            player.volume = volume

    async def _draw_time(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        paused = player.paused
        pos = player.position
        dur = player.current.duration
        sections = 12
        loc_time = round((pos / dur) * sections)
        bar = '\N{BOX DRAWINGS HEAVY HORIZONTAL}'
        seek = '\N{RADIO BUTTON}'
        if paused:
            msg = '\N{DOUBLE VERTICAL BAR}'
        else:
            msg = '\N{BLACK RIGHT-POINTING TRIANGLE}'
        for i in range(sections):
            if i == loc_time:
                msg += seek
            else:
                msg += bar
        return msg

    def _dynamic_time(self, time):
        m, s = divmod(time, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d > 0:
            msg = "{0}d"
            if h > 0 and m > 0 and s > 0:
                msg += " {1}h"
            elif m > 0 and d == 0 and h == 0 and s == 0:
                pass
            elif s > 0 and d == 0 and h == 0 and m == 0:
                pass
            elif d == 0 and m == 0 and h == 0 and s == 0:
                pass
            else:
                msg += " {1}h"
        elif d == 0 and h > 0:
            msg = "{1}h 0m" if m == 0 else "{1}h {2}m"
        elif d == 0 and h == 0 and m > 0:
            msg = "{2}m 0s" if s == 0 else "{2}m {3}s"
        elif d == 0 and h == 0 and m == 0 and s > 0:
            msg = "{3}s"
        return msg.format(d, h, m, s)

    async def _embed_msg(self, ctx, title):
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title=title)
        await ctx.send(embed=embed)

    async def _get_playing(self):
        return len([p for p in self.bot.lavalink.players._players.values() if p.is_playing])

    async def _queue_duration(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        duration = []
        for i in range(len(player.queue)):
            if not player.queue[i].stream:
                duration.append(player.queue[i].duration)
            queue_duration = sum(duration)
        if player.queue == []:
            queue_duration = 0
        try:
            if not player.current.stream:
                remain = player.current.duration - player.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        queue_total_duration = remain + queue_duration
        return queue_total_duration

    def __unload(self):
        self.bot.lavalink.client.destroy()
