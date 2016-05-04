import discord
from discord.ext import commands
import threading
import os
from random import choice as rndchoice
from random import shuffle
from cogs.utils.dataIO import fileIO
from cogs.utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
import glob
import re
import aiohttp
import json
import time
import logging
import collections
import copy
import asyncio

log = logging.getLogger("red.audio")

try:
    import youtube_dl
except:
    youtube_dl = None

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except OSError:  # Incorrect bitness
    opus = False
except:  # Missing opus
    opus = None
else:
    opus = True

youtube_dl_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'outtmpl': '%(id)s',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'outtmpl': "data/audio/cache/%(id)s",
    'default_search': 'auto'
}


class MaximumLength(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class NotConnected(Exception):
    pass


class AuthorNotConnected(NotConnected):
    pass


class VoiceNotConnected(NotConnected):
    pass


class EmptyPlayer:  # dummy player
    def __init__(self):
        self.paused = False

    def stop(self):
        pass

    def is_playing(self):
        return False

    def is_done(self):
        return True


class deque(collections.deque):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def peek(self):
        ret = self.pop()
        self.append(ret)
        return copy.deepcopy(ret)

    def peekleft(self):
        ret = self.popleft()
        self.appendleft(ret)
        return copy.deepcopy(ret)


class Song:
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.id = kwargs.get('title')
        self.url = kwargs.get('url')
        self.duration = kwargs.get('duration')


class Downloader(threading.Thread):
    def __init__(self, url, max_duration, download=False,
                 cache_path="data/audio/cache"):
        self.url = url
        self.max_duration = max_duration
        self.done = False
        self.song = None
        self.failed = False
        self._download = download
        self._yt = youtube_dl.YoutubeDL(youtube_dl_options)

    def run(self):
        try:
            self.get_info()
            if self._download:
                self.download()
        except:
            self.done = True
            self.failed = True
        else:
            self.done = True

    def download(self):
        if self.song.duration > self.max_duration:
            return

        if not os.path.isfile('data/audio/cache' + self.song.id):
            video = self._yt.extract_info(self.url)
            self.song = Song(**video)

    def get_info(self):
        if "[SEARCH:]" not in self.url:
            video = self._yt.extract_info(self.url, download=False)
        else:
            self.url = "https://youtube.com/watch?v={}".format(
                self._yt.extract_info(self.url,
                                      download=False)["entries"][0]["id"])
            video = self._yt.extract_info(self.url, download=False)

        self.song = Song(**video)


class Audio:
    """Music Streaming."""

    def __init__(self, bot):
        self.bot = bot
        self.queue = {}  # add deque's, repeat
        self.downloaders = {}  # sid: object
        self.settings = fileIO("data/audio/settings.json", 'load')
        self.cache_path = "data/audio/cache"

    async def _add_to_queue(self, server, url):
        if server.id not in self.queue:
            self.queue[server.id] = {"REPEAT": False, "VOICE_CHANNEL_ID": None,
                                     "QUEUE": deque(), "TEMP_QUEUE": deque()}
        self.queue[server.id]["QUEUE"].append(url)

    def _create_ffmpeg_player(self, server, filename):
        """This function will guarantee we have a valid voice client,
            even if one doesn't exist previously."""
        voice_client_id = self.queue[server.id]["VOICE_CHANNEL_ID"]
        voice_client = self.bot.voice_client_in(server)

        if voice_client is None:
            to_connect = self.bot.get_channel(voice_client_id)
            if to_connect is None:
                raise VoiceNotConnected("Okay somehow we're not connected and"
                                        " we have no valid channel to"
                                        " reconnect to. In other words...LOL"
                                        " REKT.")
            self.bot.join_voice_channel(to_connect)  # SHIT
        elif voice_client.channel.id != voice_client_id:
            # This was decided at 3:45 EST in #advanced-testing by 26
            self.queue[server.id]["VOICE_CHANNEL_ID"] = voice_client.channel.id

        # Okay if we reach here we definitively have a working voice_client

        song_filename = os.path.join(self.cache_path, filename)
        use_avconv = self.settings["AVCONV"]
        volume = self.settings["VOLUME"]
        options = '-filter "volume=volume={}"'.format(volume)

        voice_client.audio_player = voice_client.create_ffmpeg_player(
            song_filename, use_avconv=use_avconv, options=options)

        return voice_client  # Just for ease of use, it's modified in-place

    async def _play(self, sid, url):
        if type(sid) is not discord.Server:
            server = self.bot.get_server(sid)
        else:
            server = sid
        # We can assume by this point that there is definitely a player
        max_length = self.settings["MAX_LENGTH"]
        if server.id not in self.downloaders:  # We don't have a downloader
            self.downloaders[server.id] = Downloader(url, max_length)

        if self.downloaders[server.id].url != url:  # Our downloader is old
            # I'm praying to Jeezus that we don't accidentally lose a running
            #   Downloader
            self.downloaders[server.id] = Downloader(url, max_length)

        while not self.downloaders[server.id].done:  # Getting info w/o DL
            await asyncio.sleep(0.5)

        song = self.downloaders[server.id].song

        # Now we check to see if we have a cache hit
        cache_location = os.path.join(self.cache_path, song.id)
        if not os.path.exists(cache_location):
            self.downloaders[server.id] = Downloader(url, download=True)
            self.downloaders[server.id].start()

            while not self.downloaders[server.id].done:
                await asyncio.sleep(0.5)

            song = self.downloaders[server.id].song

        voice_client = self._create_ffmpeg_player(server, song.id)
        # That ^ creates the audio_player property

        voice_client.audio_player.start()

    @commands.command(pass_context=True)
    async def play(self, ctx, url):
        """Plays a song"""
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel

        # Checking already connected, will join if not

        if not self.voice_connected(server):
            try:
                can_connect = self.has_connect_perm(author, server)
            except AuthorNotConnected:
                await self.bot.say("You must join a voice channel before I can"
                                   " play anything.")
                return
            if not can_connect:
                await self.bot.say("I don't have permissions to join your"
                                   " voice channel.")
            else:
                await self.bot.join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                pass  # TODO

        # Checking if playing in current server

        if self.already_playing(server):
            await self.bot.say("I'm already playing a song on this server!")
            return  # TODO Possibly execute queue?

        # If not playing, spawn a downloader if it doesn't exist and begin
        #   downloading the next song

        if self.currently_downloading(server):
            await self.bot.say("I'm already downloading a file!")
            return

        self._add_to_queue(server, url)

    def already_playing(self, server):
        if not self.check_voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), 'audio_player'):
            return False
        if not self.voice_client(server).player.is_playing():
            return False
        return True

    async def cache_manager(self):
        # cache size: max([50, n * log(n)])
        pass

    def currently_downloading(self, server):
        if server.id in self.downloaders:
            if not self.downloaders[server.id].done:
                return True
        return False

    def has_connect_perm(self, author, server):
        channel = author.voice_channel
        if channel is None:
            raise AuthorNotConnected
        if channel.permissions_for(server.me):
            return True
        return False

    async def queue_manager(self, sid):
        """This function assumes that there's something in the queue for us to
            play"""
        server = self.bot.get_server(sid)
        voice_client = self.bot.voice_client_in(server)

        if voice_client is None or not hasattr(voice_client, 'audio_player'):
            # Preface player property with cog name
            self._create_ffmpeg_player(server)

        # Can assume we have a valid player at voice_client.audio_player

        # This is a reference, or should be at least
        temp_queue = self.queue[server.id]["TEMP_QUEUE"]
        queue = self.queue[server.id]["QUEUE"]
        repeat = self.queue[server.id]["REPEAT"]

        assert temp_queue is self.queue[server.id]["TEMP_QUEUE"]
        assert queue is self.queue[server.id]["QUEUE"]
        assert repeat is self.queue[server.id]["REPEAT"]

        if len(temp_queue) > 0:  # Fake queue for irdumb's temp playlist songs
            await self._play(temp_queue.popleft())
        else:  # We're in the normal queue
            url = self.queue.popleft()
            await self._play(sid, url)
            if repeat:
                self.queue.appendleft(url)

    async def queue_scheduler(self):
        for sid in self.queue:
            if len(self.queue[sid]["QUEUE"]) == 0 and \
                    len(self.queue[sid]["TEMP_QUEUE"]) == 0:
                continue
            self.bot.loop.create_task(self.queue_manager(sid))

    def voice_client(self, server):
        return self.bot.voice_client_in(server)

    def voice_connected(self, server):
        if self.bot.is_voice_connected(server):
            return True
        return False

    async def voice_state_update(self, before, after):
        # Member objects
        server = after.server
        if server.id not in self.queue:
            return
        # TODO
        #   Channel changing (by drag n drop)
        #   Muting


def check_folders():
    folders = ("data/audio", "data/audio/cache", "data/audio/playlists",
               "data/audio/localtracks", "data/audio/sfx")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    default = {"VOLUME": 0.5, "MAX_LENGTH": 3700, "QUEUE_MODE": True,
               "MAX_CACHE": 0, "SOUNDCLOUD_CLIENT_ID": None,
               "TITLE_STATUS": True, "AVCONV": False, "SERVER_SFX_ON": {}}
    settings_path = "data/audio/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default audio settings.json...")
        fileIO(settings_path, "save", default)
    else:  # consistency check
        current = fileIO(settings_path, "load")
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print(
                        "Adding " + str(key) + " field to audio settings.json")
            fileIO(settings_path, "save", current)

    allowed = ["^(https:\/\/www\\.youtube\\.com\/watch\\?v=...........*)",
               "^(https:\/\/youtu.be\/...........*)",
               "^(https:\/\/youtube\\.com\/watch\\?v=...........*)",
               "^(https:\/\/soundcloud\\.com\/.*)"]

    if not os.path.isfile("data/audio/accepted_links.json"):
        print("Creating accepted_links.json...")
        fileIO("data/audio/accepted_links.json", "save", allowed)


def setup(bot):
    check_folders()
    check_files()
    if youtube_dl is None:
        raise RuntimeError("You need to run `pip3 install youtube_dl`")
        return
    if opus is False:
        raise RuntimeError(
            "Your opus library's bitness must match your python installation's"
            " bitness. They both must be either 32bit or 64bit.")
        return
    elif opus is None:
        raise RuntimeError(
            "You need to install ffmpeg and opus. See \"https://github.com/"
            "Twentysix26/Red-DiscordBot/wiki/Requirements\"")
        return
    n = Audio(bot)  # Praise 26
    bot.add_cog(n)
    bot.add_listener(n.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(n.queue_scheduler())
    bot.loop.create_task(n.cache_manager())
