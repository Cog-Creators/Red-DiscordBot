import discord
from discord.ext import commands
import asyncio
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


class EmptyPlayer:  # dummy player
    def __init__(self):
        self.paused = False

    def stop(self):
        pass

    def is_playing(self):
        return False

    def is_done(self):
        return True


class Song:
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.id = kwargs.get('title')
        self.url = kwargs.get('url')
        self.duration = kwargs.get('duration')


class Downloader(threading.Thread):
    def __init__(self, url, max_duration):
        self.url = url
        self.max_duration = max_duration
        self.done = False
        self.song = None
        self.failed = False

    def run(self):
        try:
            self.download()
        except:
            self.done = True
            self.failed = True
        else:
            self.done = True

    def download(self):
        yt = youtube_dl.YoutubeDL(youtube_dl_options)
        if "[SEARCH:]" not in self.url:
            video = yt.extract_info(self.url, download=False)
        else:
            self.url = "https://youtube.com/watch?v={}".format(
                yt.extract_info(self.url, download=False)["entries"][0]["id"])
            video = yt.extract_info(self.url, download=False)

        self.song = Song(**video)

        if video['duration'] > self.max_duration:
            return

        if not os.path.isfile('data/audio/cache' + self.song.id):
            video = yt.extract_info(self.url)
            self.song = Song(**video)


class Audio:
    """Music Streaming."""

    def __init__(self, bot):
        self.bot = bot
        self.downloaders = {}  # sid: object

    @commands.command(pass_context=True)
    async def play(self, ctx, url):
        """Plays a song"""
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel

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

        if self.already_playing(server):
            await self.bot.say("I'm already playing a song on this server!")

        if server.id in self.downloaders:
            if not self.downloaders[server.id].done:
                await self.bot.say("I'm already downloading a song!")
                return
            else:
                pass

    def already_playing(self, server):
        if not self.check_voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), 'player'):
            return False
        if not self.voice_client(server).player.is_playing():
            return False
        return True

    def has_connect_perm(self, author, server):
        channel = author.voice_channel
        if channel is None:
            raise AuthorNotConnected
        if channel.permissions_for(server.me):
            return True
        return False

    def voice_client(self, server):
        return self.bot.voice_client_in(server)

    def voice_connected(self, server):
        if self.bot.is_voice_connected(server):
            return True
        return False


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
    n = Audio(bot)
    bot.add_cog(n)
