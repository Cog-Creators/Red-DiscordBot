import asyncio
import audioop
import glob
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import discord
import youtube_dl
from core import Config
from core.data_manager import cog_data_path
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands

log = logging.getLogger("red.audio")


class Audio:
    """Audio commands"""

    default_global_settings = {

    }

    default_guild_settings = {

    }

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=8675309)
        self.conf.register_global(
            **self.default_global_settings
        )
        self.conf.register_guild(
            **self.default_guild_settings
        )
        self.data_path = cog_data_path(self)
        self.local_path = os.path.join(self.data_path, 'local')
        self.downloader_path = os.path.join(self.data_path, 'cache')
        self.downloader = Downloader(self.downloader_path)
        if not os.path.exists(self.local_path):
            os.makedirs(self.local_path)
        self.queues = {}
        self.queue_task = asyncio.get_event_loop().create_task(self._queue_manager())

    async def enqueue(self, vchan: discord.VoiceChannel, source: discord.AudioSource):

        guild = vchan.guild

        # Check for existence of voice client
        if guild.voice_client is None:
            voice_client = await vchan.connect()
        else:
            voice_client = guild.voice_client

        # Check if a queue exists for the guild
        if guild.id in self.queues:
            self.queues[guild.id].append(source)
        else:
            self.queues[guild.id] = [source]

    async def mix(self, vchan: discord.VoiceChannel, source: discord.AudioSource):

        guild = vchan.guild

        # Check for existence of voice client
        if guild.voice_client is None:
            voice_client = await vchan.connect()
        else:
            voice_client = guild.voice_client

        # Check that voice client is in correct channel
        if voice_client.channel != vchan:
            if not voice_client.is_playing():
                await voice_client.move_to(ctx.author.voice)
            else:
                # Voice client is busy in different channel,
                # add error handling
                return

        # Check if voice client is already playing
        if voice_client.is_playing():
            voice_client.source.mix(source)
        else:
            voice_client.play(MixedSource(source))

    async def _queue_manager(self):
        await self.bot.wait_until_ready()
        while True:
            for guild in self.queues:
                vc = discord.utils.get(self.bot.guilds, id=guild).voice_client
                if not self.queues[guild]:
                    continue
                if self.queues[guild][0].done:
                    # current song is done
                    self.queues[guild].pop(0)
                if vc is None:
                    # can put some reconnect logic here later
                    # or at least an error message
                    continue
                if self.queues[guild] and not vc.is_playing():
                    # ok to play new song
                    vc.play(MixedSource(self.queues[guild][0]))
                    # How do we determine which text channel to post an alert to?
            await asyncio.sleep(1)   

    @commands.command()
    async def local(self, ctx, *, filename: str):
        """Play a local file"""
        if ctx.author.voice is None:
            await ctx.send("Join a voice channel first!")
            return

        path = self.search_local(filename)
        if path is None:
            await ctx.send("Couldn't find a unique file by that name.")
            return

        await self.mix(ctx.author.voice.channel, FFmpegPCMAudio(path))
        await ctx.send("{} is playing local file `{}`.".format(ctx.author, filename))

    @commands.command()
    async def play(self, ctx, url: str):
        """Play from url"""
        if ctx.author.voice is None:
            await ctx.send("Join a voice channel first!")
            return

        source = await YTDLSource.from_url(url, self.downloader)
        await self.enqueue(ctx.author.voice.channel, source)
        await ctx.send("{} is queueing a downloaded file...".format(ctx.author))

    @commands.command()
    async def stop(self, ctx):
        """Stops the music and disconnects"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Stopped audio.")
        else:
            await ctx.send("I'm not even connected to a voice channel!")

    @commands.command()
    async def pause(self, ctx):
        """Pauses the music"""
        if ctx.voice_client:
            ctx.voice_client.pause()
            await ctx.send("Paused audio.")
        else:
            await ctx.send("I'm not even connected to a voice channel!")

    @commands.command()
    async def resume(self, ctx):
        """Resumes the music"""
        if ctx.voice_client:
            ctx.voice_client.resume()
            await ctx.send("Resumed audio.")
        else:
            await ctx.send("I'm not even connected to a voice channel!")

    @commands.group(name='cache')
    async def cache(self, ctx):
        """Audio cache management"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @cache.command(name='dump')
    async def cache_dump(self, ctx):
        """Dump the audio cache"""
        count = 0
        files = glob.glob(os.path.join(self.downloader_path, "*"))
        for f in files:
            try:
                os.remove(f)
                count += 1
            except PermissionError:
                print("Could not delete file '{}'. "
                      "Check your file permissions.".format(f))

        await ctx.send("Dumped {} file(s).".format(count))

    def __unload(self):
        for vc in self.bot.voice_clients:
            if vc.source:
                vc.source.cleanup()
            self.bot.loop.create_task(vc.disconnect())
        self.queue_task.cancel()

    def search_local(self, filename: str):
        f = glob.glob(os.path.join(
            self.local_path, filename + ".*"))

        if len(f) == 1:
            return f[0]
        else:
            return None


class MixedSource(discord.AudioSource):
    """
    A class that allows for overlaying of an unbounded number of audio sources.
    Create a MixedSource by passing the first source in the constructor.
    Mix in additional sources by passing them in the mix method.
    """

    def __init__(self, source):
        self.sources = [source]

    def read(self):
        frames = []
        for source in self.sources:
            frame = source.read()
            if frame:
                frames.append(frame)
            else:
                source.cleanup()

        if not frames:
            return None
        elif len(frames) == 1:
            return frames[0]
        # There may be a cleaner way to do this logic
        elif len(frames) == 2:
            return audioop.add(frames[0], frames[1], 2)
        else:
            mix = audioop.add(frames[0], frames[1], 2)
            for frame in frames[2:]:
                mix = audioop.add(mix, frame, 2)
            return mix

    def mix(self, source):
        self.sources.append(source)

    def cleanup(self):
        for source in self.sources:
            source.cleanup()


class Downloader:
    # Thanks to imayhaveborkedit for offering this downloader code
    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
    }

    def __init__(self, dl_folder=None, loop=None):
        self.dl_folder = dl_folder
        self.loop = loop or asyncio.get_event_loop()

        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self.ytdl = youtube_dl.YoutubeDL(self.ytdl_format_options)

        if dl_folder:
            otmpl = self.ytdl.params['outtmpl']
            self.ytdl.params['outtmpl'] = os.path.join(dl_folder, otmpl)

    async def extract_info(self, *args, **kwargs):
        return await self.loop.run_in_executor(
            self.thread_pool, lambda: self.ytdl.extract_info(*args, **kwargs))


class YTDLSource(discord.PCMVolumeTransformer):
    # Thanks to imayhaveborkedit for starter code again
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.done = False
        self.data = data

        self.title = data.get('title', '[no title]')
        self.url = data.get('url', '[no url]')
        # TODO: extract properties from data (title, duration, etc)

    def cleanup(self):
        super().cleanup()
        self.done = True

    @classmethod
    async def from_url(cls, url, downloader):
        data = await downloader.extract_info(url)
        if 'entries' in data:
            # playlist stuff
            data = data['entries'][0]

        filename = downloader.ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(
            filename, before_options='-nostdin', options='-vn'), data=data)
