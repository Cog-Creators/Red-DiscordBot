import asyncio
import audioop
import glob
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import discord
import youtube_dl
from core import Config, checks
from core.data_manager import cog_data_path
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands

log = logging.getLogger("red.audio")


class AudioError(Exception):
    pass


class AuthorNotInVoice(AudioError):
    pass


class NoVoiceClient(AudioError):
    pass


class VoiceClientBusy(AudioError):
    pass


class QueueError(AudioError):
    pass


class DownloadError(AudioError):
    pass


class AudioManager:

    def __init__(self, ctx):
        self.guild = ctx.guild
        self.text_channel = ctx.message.channel
        self.voice_client = None
        self.disc_timer = 0
        self.timeout = 10
        self.queue = []
        self.current = None
        self.loop = asyncio.get_event_loop()
        self.task = self.loop.create_task(self.queue_manager())

    def enqueue(self, song):
        self.queue.append(song)

    def mix(self, source: discord.AudioSource):
        # Check if voice client is already playing
        if self.is_busy(self.voice_client):
            self.voice_client.source.mix(source)
        else:
            self.voice_client.play(MixedSource(source))

    def skip(self):
        try:
            if isinstance(self.voice_client.source.sources[0], YTDLSource):
                self.voice_client.source.sources[0].cleanup()
                self.voice_client.source.sources.pop(0)
            else:
                raise QueueError("I'm not playing any music.")
        except (AttributeError, IndexError):
            raise QueueError("I'm not playing anything.")

    def restart(self):
        if self.task.done():
            self.disc_timer = 0
            self.task = self.loop.create_task(self.queue_manager())

    def set_voice_client(self, voice_client: discord.VoiceClient):
        self.voice_client = voice_client

    async def queue_manager(self):
        log.debug('Queue manager started on guild ' + str(self.guild.id))
        while True:
            await asyncio.sleep(1)
            self.disc_timer += 1
            if self.voice_client is None:
                # can put some reconnect logic here later
                # or at least an error message
                break
            try:
                if not self.queue[0].is_downloaded():
                    # It's ok to block the loop here and wait for download
                    await self.queue[0].download()
                    log.debug('Downloading song ' + self.queue[0].data.get('title', '[no title]'))
                else:
                    if (self.current is None or self.current.source.done) and not self.is_busy(self.voice_client):
                        log.debug('Playing song ' + self.queue[0].data.get('title', '[no title]'))
                        self.current = self.queue.pop(0)
                        self.voice_client.play(MixedSource(self.current.source))

            except IndexError:
                # Queue is empty
                pass

            if self.is_busy(self.voice_client):
                self.disc_timer = 0
            if self.disc_timer > self.timeout:
                await self.voice_client.disconnect()
                # This kills the task
                break
        self.queue.clear()
        log.debug('Queue manager stopped on guild ' + str(self.guild.id))

    def is_busy(self, voice_client: discord.VoiceClient):
        return voice_client.is_playing() or voice_client.is_paused()


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
        self.data_path = Path(cog_data_path(self))
        self.local_path = self.data_path / 'local'
        self.downloader_path = self.data_path / 'cache'
        self.downloader = Downloader(self.downloader_path)
        self.managers = {}

        self.local_path.mkdir(exist_ok=True)
        self.downloader_path.mkdir(exist_ok=True)

    async def get_manager(self, ctx, connect: bool=False):
        # Returns a reference to the audio manager
        # and ensures a connection if required
        manager = self.managers.get(ctx.guild.id, None)
        voice_client = manager.voice_client if manager else ctx.guild.voice_client

        if connect:
            if ctx.author.voice is None:
                raise AuthorNotInVoice("You are not in a voice channel.")            
            if voice_client is None or not voice_client.is_connected():
                try:
                    voice_client = await ctx.author.voice.channel.connect()
                except asyncio.TimeoutError:
                    raise NoVoiceClient("Timed out trying to connect to voice channel.")
                except:
                    raise NoVoiceClient("Could not connect to voice channel.")
            elif voice_client.channel != ctx.author.voice.channel:
                # Check if it's ok to try to move channels
                if not voice_client.is_playing() and not voice_client.is_paused():
                    await voice_client.move_to(ctx.author.voice.channel)
                    await ctx.send('Moving voice channels.')
                else:
                    raise VoiceClientBusy("Voice client is busy in another channel.")

            if manager is None:
                manager = AudioManager(ctx)
                self.managers[ctx.guild.id] = manager
            manager.set_voice_client(voice_client)
            if manager.task.done():
                manager.restart()

        return manager

    @commands.command()
    async def local(self, ctx, *, filename: str):
        """Play a local file"""

        path = self.search_local(filename)
        if path is None:
            await ctx.send("Couldn't find a unique file by that name.")
            return

        try:
            manager = await self.get_manager(ctx, connect=True)
        except AudioError as e:
            await ctx.send(e)
            return

        source = FFmpegPCMAudio(str(path))
        manager.mix(source)
        log.debug('Playing file ' + str(path))
        await ctx.send("{} is playing local file `{}`.".format(ctx.author, filename))

    @commands.command()
    async def play(self, ctx, url: str):
        """Play from url"""

        try:
            manager = await self.get_manager(ctx, connect=True)
        except AudioError as e:
            await ctx.send(e)
            return

        song = YTDLSong(url, self.downloader)
        await song.extract()
        manager.enqueue(song)
        title = song.data.get('title', '[no title]')
        await ctx.send("{} is queueing {}...".format(ctx.author.display_name, title))

    @commands.command()
    async def stop(self, ctx):
        """Stops the music and disconnects"""

        manager = await self.get_manager(ctx)

        if manager is None or manager.voice_client is None:
            await ctx.send("I'm not playing anything!")
            return

        await manager.voice_client.disconnect()
        await ctx.send("Stopping audio.")

    @commands.command()
    async def pause(self, ctx):
        """Pauses the music"""

        manager = await self.get_manager(ctx)

        if manager is None or manager.voice_client is None:
            await ctx.send("I'm not playing anything!")
            return

        manager.voice_client.pause()
        await ctx.send("Pausing audio.")

    @commands.command()
    async def resume(self, ctx):
        """Resumes the music"""

        manager = await self.get_manager(ctx)

        if manager is None or manager.voice_client is None:
            await ctx.send("Nothing to play!")
            return

        if manager.voice_client.is_paused():
            manager.voice_client.resume()
            await ctx.send("Resuming audio.")
        else:
            await ctx.send("I wasn't paused!")

    @commands.command()
    async def skip(self, ctx):
        """Skips the current song"""

        manager = await self.get_manager(ctx)

        if manager is None:
            await ctx.send("I'm not playing anything!")
            return
        try:
            manager.skip()
            await ctx.send("Skipping song...")
        except AudioError as e:
            await ctx.send(e)

    @commands.group(name='cache')
    async def cache(self, ctx):
        """Audio cache management"""

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @cache.command(name='dump')
    @checks.is_owner()
    async def cache_dump(self, ctx):
        """Dump the audio cache"""

        for child in self.downloader_path.iterdir():
            if child_isdir():
                child.rmdir()
            else:
                child.unlink()

        await ctx.send("Dumped audio cache.")

    def __unload(self):        
        for vc in self.bot.voice_clients:
            if vc.source:
                vc.source.cleanup()
            self.bot.loop.create_task(vc.disconnect())
        for manager in self.managers:
            self.managers[manager].task.cancel()

    def search_local(self, filename: str):
        f = sorted(self.local_path.glob(filename + ".*"))

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
    # Thanks to imayhaveborkedit for this downloader code
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

    def __init__(self, download_path, loop=None):
        self.download_path = download_path
        self.loop = loop or asyncio.get_event_loop()

        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self.ytdl = youtube_dl.YoutubeDL(self.ytdl_format_options)

        otmpl = self.ytdl.params['outtmpl']
        self.ytdl.params['outtmpl'] = str(self.download_path / otmpl)

    async def extract_info(self, *args, **kwargs):
        return await self.loop.run_in_executor(
            self.thread_pool, lambda: self.ytdl.extract_info(*args, **kwargs))


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, volume=0.5):
        super().__init__(source, volume)
        self.done = False

    def cleanup(self):
        super().cleanup()
        self.done = True


class YTDLSong:
    def __init__(self, url, downloader):
        self.url = url
        self.downloader = downloader
        self.data = None
        self.source = None

    async def extract(self):
        # Only extracts data, doesn't download yet
        self.data = await self.downloader.extract_info(self.url, download=False)
        if 'entries' in self.data:
            # For now, just grab the first song of a playlist.
            self.data = data['entries'][0]

    async def download(self):
        # After skimming the youtube_dl source a bit, it seems like calling
        # extract_info again might be the best way to download. Could lead to
        # some odd behavior if the source has changed since the initial data
        # extraction. Will look into this.
        self.data = await self.downloader.extract_info(self.url)
        if 'entries' in self.data:
            # Tried to download a whole playlist. We should handle this in the
            # extract method first so this doesn't happen.
            raise DownloadError('Tried to download a playlist.')

        filename = self.downloader.ytdl.prepare_filename(self.data)
        self.source = YTDLSource(discord.FFmpegPCMAudio(
            filename, before_options='-nostdin', options='-vn'))

    def is_downloaded(self):
        return True if self.source else False
