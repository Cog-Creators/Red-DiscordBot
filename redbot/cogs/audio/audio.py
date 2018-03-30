import asyncio
import datetime
import discord
import heapq
import lavalink
import math
from discord.ext import commands
from redbot.core import Config, checks

from .manager import shutdown_lavalink_server

__version__ = "0.0.3a"
__author__ = ["aikaterna", "billy/bollo/ati"]


class Audio:
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2711759128, force_registration=True)

        default_global = {
            "host": 'localhost',
            "rest_port": '2333',
            "ws_port": '2332',
            "password": 'youshallnotpass',
            "status": False,
            "current_build": 0
        }

        default_guild = {
            "notify": False,
            "repeat": False,
            "shuffle": False,
            "volume": 100
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

    async def init_config(self):
        host = await self.config.host()
        password = await self.config.password()
        rest_port = await self.config.rest_port()
        ws_port = await self.config.ws_port()

        await lavalink.initialize(
            bot=self.bot, host=host, password=password, rest_port=rest_port, ws_port=ws_port
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
            playing_song = player.fetch('playing_song')
            requester = player.fetch('requester')
            player.store('prev_song', playing_song)
            player.store('prev_requester', requester)
            player.store('playing_song', player.current.uri)
            player.store('requester', player.current.requester)

        if event_type == lavalink.LavalinkEvents.TRACK_START and notify:
            notify_channel = player.fetch('channel')
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                if player.fetch('notify_message') is not None:
                    try:
                        await player.fetch('notify_message').delete()
                    except discord.errors.NotFound:
                        pass
                embed = discord.Embed(colour=notify_channel.guild.me.top_role.colour, title='Now Playing',
                                      description='**[{}]({})**'.format(player.current.title, player.current.uri))
                notify_message = await notify_channel.send(embed=embed)
                player.store('notify_message', notify_message)

        if event_type == lavalink.LavalinkEvents.TRACK_START and status:
            if playing_servers == 0:
                await self.bot.change_presence(activity=None)
            if playing_servers == 1:
                await self.bot.change_presence(activity=discord.Activity(name=get_single_title,
                                               type=discord.ActivityType.listening))
            if playing_servers > 1:
                await self.bot.change_presence(activity=discord.Activity(name='music in {} servers'.format(playing_servers),
                                               type=discord.ActivityType.playing))

        if event_type == lavalink.LavalinkEvents.QUEUE_END and notify:
            notify_channel = player.fetch('channel')
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                embed = discord.Embed(colour=notify_channel.guild.me.top_role.colour, title='Queue ended.')
                await notify_channel.send(embed=embed)

        if event_type == lavalink.LavalinkEvents.QUEUE_END and status:
            if playing_servers == 0:
                await self.bot.change_presence(activity=None)
            if playing_servers == 1:
                await self.bot.change_presence(activity=discord.Activity(name=get_single_title,
                                               type=discord.ActivityType.listening))
            if playing_servers > 1:
                await self.bot.change_presence(activity=discord.Activity(name='music in {} servers'.format(playing_servers),
                                               type=discord.ActivityType.playing))

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
        msg += 'Cog version: {}\n```'.format(__version__)

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, description=msg)
        return await ctx.send(embed=embed)

    @audioset.command()
    @checks.is_owner()
    async def status(self, ctx):
        """Enables/disables songs' titles as status."""
        status = await self.config.status()
        await self.config.status.set(not status)
        get_status = await self.config.status()
        await self._embed_msg(ctx, 'Song titles as status: {}.'.format(get_status))

    @commands.command()
    async def audiostats(self, ctx):
        """Audio stats."""
        server_num = len([p for p in lavalink.players if p.current is not None])
        server_list = []

        for p in lavalink.players:
            connect_start = p.fetch('connect')
            connect_dur = self._dynamic_time(int((datetime.datetime.utcnow() - connect_start).total_seconds()))
            try:
                server_list.append('{} [`{}`]: **[{}]({})**'.format(p.channel.guild.name, connect_dur,
                                   p.current.title, p.current.uri))
            except AttributeError:
                server_list.append('{} [`{}`]: **{}**'.format(p.channel.guild.name, connect_dur,
                                   'Nothing playing.'))
        if server_num == 0:
            servers = 'Not connected anywhere.'
        else:
            servers = '\n'.join(server_list)
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Connected in {} servers:'.format(server_num),
                              description=servers)
        await ctx.send(embed=embed)

    @commands.command()
    async def bump(self, ctx, index: int):
        """Bump a song number to the top of the queue."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')

        player = lavalink.get_player(ctx.guild.id)
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(ctx, 'Song number must be greater than 1 and within the queue limit.')

        bump_index = index - 1
        bump_song = player.queue[bump_index]
        player.queue.insert(0, bump_song)
        removed = player.queue.pop(index)
        await self._embed_msg(ctx, 'Moved **' + removed.title + '** to the top of the queue.')

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        """Disconnect from the voice channel."""
        if self._player_check(ctx):
            await lavalink.get_player(ctx.guild.id).stop()
            await lavalink.get_player(ctx.guild.id).disconnect()

    @commands.command(aliases=['np', 'n', 'song'])
    async def now(self, ctx):
        """Now playing."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        expected = ['⏮', '⏹', '⏸', '⏭']
        emoji = {
            'prev': '⏮',
            'stop': '⏹',
            'pause': '⏸',
            'next': '⏭'
        }
        player = lavalink.get_player(ctx.guild.id)
        song = 'Nothing'
        if player.current:
            arrow = await self._draw_time(ctx)
            pos = lavalink.utils.format_time(player.position)
            if player.current.is_stream:
                dur = 'LIVE'
            else:
                dur = lavalink.utils.format_time(player.current.length)
            song = '**[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`'.format(
                player.current.title, player.current.uri,
                player.current.requester, arrow, pos, dur
            )
        else:
            song = 'Nothing.'

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
            for i in range(4):
                await message.add_reaction(expected[i])
        try:
            (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=10.0)
        except asyncio.TimeoutError:
            return await self._clear_react(message)

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]

        if react == 'prev':
            await self._clear_react(message)
            await ctx.invoke(self.prev)
        elif react == 'stop':
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
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        player = lavalink.get_player(ctx.guild.id)
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await self._embed_msg(ctx, 'You must be in the voice channel to pause the music.')

        if player.current and not player.paused:
            await player.pause()
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour, title='Track Paused',
                description='**[{}]({})**'.format(
                    player.current.title,
                    player.current.uri
                )
            )
            return await ctx.send(embed=embed)

        if player.paused:
            await player.pause(False)
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title='Track Resumed',
                description='**[{}]({})**'.format(
                    player.current.title,
                    player.current.uri
                )
            )
            return await ctx.send(embed=embed)

        await self._embed_msg(ctx, 'Nothing playing.')

    @commands.command()
    async def percent(self, ctx):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
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

        for track in queue_tracks:
            req_username = '{}#{}'.format(track.requester.name, track.requester.discriminator)
            await _usercount(req_username)

        try:
            req_username = '{}#{}'.format(player.current.requester.name, player.current.requester.discriminator)
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
        if not ctx.author.voice:
            return await self._embed_msg(ctx, 'You must be in the voice channel to use the play command.')
        if not self._player_check(ctx):
            await lavalink.connect(ctx.author.voice.channel)
            player = lavalink.get_player(ctx.guild.id)
            player.store('connect', datetime.datetime.utcnow())
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        player.store('channel', ctx.channel.id)
        player.store('guild', ctx.guild.id)
        await self._data_check(ctx)

        query = query.strip('<>')
        if not query.startswith('http'):
            query = 'ytsearch:{}'.format(query)

        tracks = await player.get_tracks(query)
        if not tracks:
            return await self._embed_msg(ctx, 'Nothing found.')

        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)

        if 'list' in query and 'ytsearch:' not in query:
            for track in tracks:
                player.add(ctx.author, track)
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Playlist Enqueued',
                                  description='Added {} tracks to the queue.'.format(len(tracks)))
            if not shuffle and queue_duration > 0:
                embed.set_footer(text='{} until start of playlist playback'.format(queue_total_duration))
            if not player.current:
                await player.play()
        else:
            single_track = tracks[0]
            player.add(ctx.author, single_track)
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Enqueued',
                                  description='**[{}]({})**'.format(single_track.title, single_track.uri))
            if not shuffle and queue_duration > 0:
                embed.set_footer(text='{} until track playback'.format(queue_total_duration))
            if not player.current:
                await player.play()
        await ctx.send(embed=embed)

    @commands.command()
    async def prev(self, ctx):
        """Skips to the start of the previously played track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await self._embed_msg(ctx, 'You must be in the voice channel to skip the music.')
        if shuffle:
            return await self._embed_msg(ctx, 'Turn shuffle off to use this command.')
        if player.fetch('prev_song') is None:
            return await self._embed_msg(ctx, 'No previous track.')
        else:
            last_track = await player.get_tracks(player.fetch('prev_song'))
            player.add(player.fetch('prev_requester').id, last_track[0])
            queue_len = len(player.queue)
            bump_song = player.queue[-1]
            player.queue.insert(0, bump_song)
            player.queue.pop(queue_len)
            await player.skip()
            embed = discord.Embed(
                colour=ctx.guild.me.top_role.colour,
                title='Replaying Track', description='**[{}]({})**'.format(
                    player.current.title, player.current.uri
                )
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=['q'])
    async def queue(self, ctx, page: int=1):
        """Lists the queue."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'There\'s nothing in the queue.')
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, 'There\'s nothing in the queue.')

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)
        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue_list = ''
        arrow = await self._draw_time(ctx)
        pos = lavalink.utils.format_time(player.position)

        if player.current.is_stream:
            dur = 'LIVE'
        else:
            dur = lavalink.utils.format_time(player.current.length)

        if player.current.is_stream:
            queue_list += '**Currently livestreaming:** **[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`\n\n'.format(
                player.current.title,
                player.current.uri,
                player.current.requester,
                arrow, pos, dur
            )
        else:
            queue_list += 'Playing: **[{}]({})**\nRequested by: **{}**\n\n{}`{}`/`{}`\n\n'.format(
                player.current.title,
                player.current.uri,
                player.current.requester,
                arrow, pos, dur
            )

        for i, track in enumerate(player.queue[start:end], start=start):
            req_user = track.requester
            next = i + 1
            queue_list += '`{}.` **[{}]({})**, requested by **{}**\n'.format(next, track.title, track.uri, req_user)

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Queue for ' + ctx.guild.name,
                              description=queue_list)

        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        text = 'Page {}/{} | {} tracks, {} remaining'.format(page, pages, len(player.queue) + 1, queue_total_duration)
        if repeat:
            text += ' | Repeat: \N{WHITE HEAVY CHECK MARK}'
        if shuffle:
            text += ' | Shuffle: \N{WHITE HEAVY CHECK MARK}'
        embed.set_footer(text=text)
        await ctx.send(embed=embed)

    @commands.command()
    async def repeat(self, ctx):
        """Toggles repeat."""
        repeat_msg = 'You must be in the voice channel to toggle repeat.'
        if not ctx.author.voice:
            return await self._embed_msg(ctx, repeat_msg)

        repeat = await self.config.guild(ctx.guild).repeat()
        await self.config.guild(ctx.guild).repeat.set(not repeat)
        repeat = await self.config.guild(ctx.guild).repeat()
        await self._embed_msg(ctx, 'Repeat songs: {}.'.format(repeat))

        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if ctx.author.voice.channel != player.channel:
                return await self._embed_msg(ctx, repeat_msg)

    @commands.command()
    async def remove(self, ctx, index: int):
        """Remove a specific song number from the queue."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, 'Nothing queued.')
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(ctx, 'Song number must be greater than 1 and within the queue limit.')
        index -= 1
        removed = player.queue.pop(index)
        await self._embed_msg(ctx, 'Removed **' + removed.title + '** from the queue.')

    @commands.command()
    async def search(self, ctx, *, query):
        """Pick a song with a search.
        Use [p]search list <search term> to queue all songs.
        """
        expected = ["1⃣", "2⃣", "3⃣", "4⃣", "5⃣"]
        emoji = {
            "one": "1⃣",
            "two": "2⃣",
            "three": "3⃣",
            "four": "4⃣",
            "five": "5⃣"
        }
        if not ctx.author.voice:
            return await self._embed_msg(ctx, 'You must be in the voice channel to enqueue songs.')
        if not self._player_check(ctx):
            await lavalink.connect(ctx.author.voice.channel)
            player = lavalink.get_player(ctx.guild.id)
            player.store('connect', datetime.datetime.utcnow())
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        player.store('channel', ctx.channel.id)
        player.store('guild', ctx.guild.id)
        if ctx.author.voice.channel != player.channel:
            return await self._embed_msg(ctx, 'You must be in the voice channel to enqueue songs.')

        query = query.strip('<>')
        if query.startswith('sc '):
            query = 'scsearch:{}'.format(query.strip('sc '))
        elif not query.startswith('http') or query.startswith('sc '):
            query = 'ytsearch:{}'.format(query)

        tracks = await player.get_tracks(query)
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
                search_list += '`{0}.` [**{1}**]({2})\n'.format(next, track.title,
                                                                track.uri)

            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Tracks Found:', description=search_list)
            embed.set_footer(text='Page {}/{} | {} search results'.format(page, pages, len(tracks)))
            message = await ctx.send(embed=embed)

            def check(r, u):
                return r.message.id == message.id and u == ctx.message.author

            for i in range(5):
                await message.add_reaction(expected[i])
            try:
                (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await self._clear_react(message)
                return
            reacts = {v: k for k, v in emoji.items()}
            react = reacts[r.emoji]
            choice = {'one': 0, 'two': 1, 'three': 2, 'four': 3, 'five': 4}
            await self._search_button(ctx, message, tracks, entry=choice[react])

        else:
            await self._data_check(ctx)
            songembed = discord.Embed(colour=ctx.guild.me.top_role.colour,
                                      title='Queued {} track(s).'.format(len(tracks)))
            queue_duration = await self._queue_duration(ctx)
            queue_total_duration = lavalink.utils.format_time(queue_duration)
            if not shuffle and queue_duration > 0:
                songembed.set_footer(text='{} until start of search playback'.format(queue_total_duration))
            for track in tracks:
                player.add(ctx.author, track)
                if not player.current:
                    await player.play()
            message = await ctx.send(embed=songembed)

    async def _search_button(self, ctx, message, tracks, entry: int):
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self._clear_react(message)
        search_choice = tracks[entry]
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Track Enqueued',
                              description='**[{}]({})**'.format(search_choice.title, search_choice.uri))
        queue_duration = await self._queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_duration)
        if not shuffle and queue_duration > 0:
            embed.set_footer(text='{} until track playback'.format(queue_total_duration))
        player.add(ctx.author, search_choice)
        if not player.current:
            await player.play()
        return await ctx.send(embed=embed)

    @commands.command()
    async def seek(self, ctx, seconds: int=30):
        """Seeks ahead or behind on a track by seconds."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        player = lavalink.get_player(ctx.guild.id)
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await self._embed_msg(ctx, 'You must be in the voice channel to use seek.')
        if player.current:
            if player.current.is_stream:
                return await self._embed_msg(ctx, 'Can\'t seek on a stream.')
            else:
                time_sec = seconds * 1000
                seek = player.position + time_sec
                if seek <= 0:
                    await self._embed_msg(ctx, 'Moved {}s to 00:00:00'.format(seconds))
                else:
                    await self._embed_msg(ctx, 'Moved {}s to {}'.format(seconds, lavalink.utils.format_time(seek)))
                return await player.seek(seek)
        else:
             await self._embed_msg(ctx, 'Nothing playing.')

    @commands.command()
    async def shuffle(self, ctx):
        """Toggles shuffle."""
        shuffle_msg = 'You must be in the voice channel to toggle shuffle.'
        if not ctx.author.voice:
            return await self._embed_msg(ctx, shuffle_msg)

        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self.config.guild(ctx.guild).shuffle.set(not shuffle)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        await self._embed_msg(ctx, 'Shuffle songs: {}.'.format(shuffle))

        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if ctx.author.voice.channel != player.channel:
                return await self._embed_msg(ctx, shuffle_msg)

    @commands.command(aliases=['forceskip', 'fs'])
    async def skip(self, ctx):
        """Skips to the next track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        else:
            player = lavalink.get_player(ctx.guild.id)

        if not player.current:
            return await self._embed_msg(ctx, 'There\'s nothing in the queue.')

        if not player.queue:
            pos, dur = player.position, player.current.length
            time_remain = lavalink.utils.format_time(dur - pos)
            if player.current.is_stream:
                embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='There\'s nothing in the queue.')
                embed.set_footer(text='Currently livestreaming {}'.format(player.current.title))
            else:
                embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='There\'s nothing in the queue.')
                embed.set_footer(text='{} left on {}'.format(time_remain, player.current.title))
            return await ctx.send(embed=embed)

        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await self._embed_msg(ctx, 'You must be in the voice channel to skip the music.')

        embed = discord.Embed(
            colour=ctx.guild.me.top_role.colour, title='Track Skipped',
            description='**[{}]({})**'.format(
                player.current.title, player.current.uri
            )
        )
        await ctx.send(embed=embed)

        await player.skip()

    @commands.command(aliases=['s'])
    async def stop(self, ctx):
        """Stops playback and clears the queue."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, 'Nothing playing.')
        player = lavalink.get_player(ctx.guild.id)
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await self._embed_msg(ctx, 'You must be in the voice channel to stop the music.')
        if player.is_playing:
            await self._embed_msg(ctx, 'Stopping...')
            await player.stop()
            player.store('prev_requester', None)
            player.store('prev_song', None)
            player.store('playing_song', None)
            player.store('requester', None)

    @commands.command()
    async def volume(self, ctx, vol: int=None):
        """Sets the volume, 1% - 150%."""
        if not vol:
            vol = await self.config.guild(ctx.guild).volume()
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Current Volume:',
                                  description=str(vol) + '%')
            if not self._player_check(ctx):
                embed.set_footer(text='Nothing playing.')
            return await ctx.send(embed=embed)
        if vol > 150:
            vol = 150
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check:
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        else:
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check:
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Volume:',
                              description=str(vol) + '%')
        if not self._player_check(ctx):
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
    async def restport(self, ctx, rest_port):
        """Set the lavalink REST server port."""
        await self.config.rest_port.set(str(rest_port))
        get_rest_port = await self.config.rest_port()
        await self._embed_msg(ctx, 'REST port set to {}.'.format(get_rest_port))

    @llsetup.command()
    async def wsport(self, ctx, rest_port):
        """Set the lavalink websocket server port."""
        await self.config.ws_port.set(str(ws_port))
        get_rest_port = await self.config.ws_port()
        await self._embed_msg(ctx, 'Websocket port set to {}.'.format(get_ws_port))

    async def _clear_react(self, message):
        try:
            await message.clear_reactions()
        except:
            return

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

    async def _draw_time(self, ctx):
        player = lavalink.get_player(ctx.guild.id)
        paused = player.paused
        pos = player.position
        dur = player.current.length
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
            msg = "{0}d {1}h"
        elif d == 0 and h > 0:
            msg = "{1}h {2}m"
        elif d == 0 and h == 0 and m > 0:
            msg = "{2}m {3}s"
        elif d == 0 and h == 0 and m == 0 and s > 0:
            msg = "{3}s"
        return msg.format(d, h, m, s)

    async def _embed_msg(self, ctx, title):
        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title=title)
        await ctx.send(embed=embed)

    async def _get_playing(self, ctx):
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            return len([player for p in lavalink.players if p.is_playing])
        else:
            return 0

    async def _queue_duration(self, ctx):
        player = lavalink.get_player(ctx.guild.id)
        duration = []
        for i in range(len(player.queue)):
            if not player.queue[i].is_stream:
                duration.append(player.queue[i].length)
            queue_duration = sum(duration)
        if player.queue == []:
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

    def _player_check(self, ctx):
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except KeyError:
            return False

    def __unload(self):
        lavalink.unregister_event_listener(self.event_handler)
        self.bot.loop.create_task(lavalink.close())
        shutdown_lavalink_server()
