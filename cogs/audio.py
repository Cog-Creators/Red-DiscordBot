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
log.setLevel(logging.DEBUG)

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


class ConnectTimeout(NotConnected):
    pass


class InvalidURL(Exception):
    pass


class InvalidSong(InvalidURL):
    pass


class InvalidPlaylist(InvalidSong):
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
        self.__dict__ = kwargs
        self.title = kwargs.pop('title', None)
        self.id = kwargs.pop('id', None)
        self.url = kwargs.pop('url', None)
        self.duration = kwargs.pop('duration', "")


class Playlist:
    def __init__(self, server=None, sid=None, name=None, author=None, url=None,
                 playlist=None, **kwargs):
        self.server = server
        self._sid = sid
        self.name = name
        self.author = author
        self.url = url
        if url is None and "link" in kwargs:
            self.url = kwargs.get('link')
        self.playlist = playlist

    @property
    def filename(self):
        f = "data/audio/playlists"
        f = os.path.join(f, self.sid, self.name + ".txt")
        return f

    def to_json(self):
        ret = {"author": self.author, "playlist": self.playlist,
               "link": self.url}
        return ret

    @property
    def sid(self):
        if self._sid:
            return self._sid
        elif self.server:
            return self.server.id
        else:
            return None


class Downloader(threading.Thread):
    def __init__(self, url, max_duration=None, download=False,
                 cache_path="data/audio/cache", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.max_duration = max_duration
        self.done = False
        self.song = None
        self.failed = False
        self._download = download
        self._yt = None

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
        if self.max_duration and self.song.duration > self.max_duration:
            return

        if not os.path.isfile('data/audio/cache' + self.song.id):
            video = self._yt.extract_info(self.url)
            self.song = Song(**video)

    def get_info(self):
        if self._yt is None:
            self._yt = youtube_dl.YoutubeDL(youtube_dl_options)
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
        self.server_specific_setting_keys = ["VOLUME", "QUEUE_MODE",
                                             "VOTE_THRESHOLD"]
        self.cache_path = "data/audio/cache"

    def __del__(self):
        for vc in self.bot.voice_clients:
            self._stop_and_disconnect(vc.server)

    def _add_to_queue(self, server, url):
        if server.id not in self.queue:
            self.queue[server.id] = {"REPEAT": False, "PLAYLIST": False,
                                     "VOICE_CHANNEL_ID": None,
                                     "QUEUE": deque(), "TEMP_QUEUE": deque(),
                                     "NOW_PLAYING": None}
        self.queue[server.id]["QUEUE"].append(url)

    def _add_to_temp_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue(server)
        self.queue[server.id]["TEMP_QUEUE"].append(url)

    def _clear_queue(self, server):
        if server.id not in self.queue:
            return
        self.queue[server.id]["QUEUE"] = deque()
        self.queue[server.id]["TEMP_QUEUE"] = deque()

    def _create_ffmpeg_player(self, server, filename):
        """This function will guarantee we have a valid voice client,
            even if one doesn't exist previously."""
        voice_channel_id = self.queue[server.id]["VOICE_CHANNEL_ID"]
        voice_client = self.voice_client(server)

        if voice_client is None:
            log.debug("not connected when we should be in sid {}".format(
                server.id))
            to_connect = self.bot.get_channel(voice_channel_id)
            if to_connect is None:
                raise VoiceNotConnected("Okay somehow we're not connected and"
                                        " we have no valid channel to"
                                        " reconnect to. In other words...LOL"
                                        " REKT.")
            log.debug("valid reconnect channel for sid"
                      " {}, reconnecting...".format(server.id))
            self.bot.join_voice_channel(to_connect)  # SHIT
        elif voice_client.channel.id != voice_channel_id:
            # This was decided at 3:45 EST in #advanced-testing by 26
            self.queue[server.id]["VOICE_CHANNEL_ID"] = voice_client.channel.id
            log.debug("reconnect chan id for sid {} is wrong, fixing".format(
                server.id))

        # Okay if we reach here we definitively have a working voice_client

        song_filename = os.path.join(self.cache_path, filename)
        use_avconv = self.settings["AVCONV"]
        volume = self.settings["VOLUME"]
        options = '-filter "volume=volume={}"'.format(volume)

        log.debug("making player on sid {}".format(server.id))

        voice_client.audio_player = voice_client.create_ffmpeg_player(
            song_filename, use_avconv=use_avconv, options=options)

        return voice_client  # Just for ease of use, it's modified in-place

    # TODO: _disable_controls()

    def _disconnect_voice_client(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        self.bot.loop.create_task(voice_client.disconnect())

    async def _download_next(self, server, curr_dl, next_dl):
        """Checks to see if we need to download the next, and does.

        Both curr_dl and next_dl should already be started."""
        if curr_dl.song is None:
            # Only happens when the downloader thread hasn't initialized fully
            #   There's no reason to wait if we can't compare
            return

        max_length = self.settings["MAX_LENGTH"]

        while next_dl.is_alive():
            await asyncio.sleep(0.5)

        if curr_dl.song.id != next_dl.song.id:
            log.debug("downloader ID's mismatch on sid {}".format(server.id) +
                      " gonna start dl-ing the next thing on the queue"
                      " id {}".format(next_dl.song.id))
            self.downloaders[server.id] = Downloader(next_dl.url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

    # TODO: _enable_controls()

    async def _join_voice_channel(self, channel):
        server = channel.server
        if server.id in self.queue:
            self.queue[server.id]["VOICE_CHANNEL_ID"] = channel.id
        try:
            await self.bot.join_voice_channel(channel)
        except asyncio.futures.TimeoutError as e:
            log.exception(e)
            raise ConnectTimeout("We timed out connecting to a voice channel")

    def _load_playlist(self, server, name):
        try:
            server = server.id
        except:
            pass

        f = "data/audio/playlists"
        f = os.path.join(f, server, name + ".txt")
        kwargs = fileIO(f, 'load')

        kwargs['name'] = name
        kwargs['sid'] = server

        return Playlist(**kwargs)

    def _make_playlist(self, author, url, songlist):
        try:
            author = author.id
        except:
            pass

        return Playlist(author=author, url=url, songlist=songlist)

    def _match_sc_playlist(self, url):
        return self._match_sc_url(url)

    def _match_yt_playlist(self, url):
        if not self._match_yt_url(url):
            return False
        yt_playlist = re.compile(
            r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)'
            r'(\/playlist\?).*(list=)(.*)(&|$)')
        # Group 6 should be the list ID
        if yt_playlist.match(url):
            return True
        return False

    def _match_sc_url(self, url):
        sc_url = re.compile(
            r'^(https?\:\/\/)?(www\.)?(soundcloud\.com\/)')
        if sc_url.match(url):
            return True
        return False

    def _match_yt_url(self, url):
        yt_link = re.compile(
            r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$')
        if yt_link.match(url):
            return True
        return False

    async def _parse_playlist(self, url):
        if self._match_sc_playlist(url):
            return await self._parse_sc_playlist(url)
        elif self._match_yt_playlist(url):
            return await self._parse_yt_playlist(url)
        raise InvalidPlaylist("The given URL is neither a Soundcloud or"
                              " YouTube playlist.")

    async def _parse_sc_playlist(self, url):
        playlist = []
        d = Downloader(url)
        d.start()

        while d.is_alive():
            await asyncio.sleep(0.5)

        for entry in d.song.entries:
            if entry.url[4] != "s":
                song_url = "https{}".format(entry.url[4:])
                playlist.append(song_url)
            else:
                playlist.append(entry.url)

    async def _parse_yt_playlist(self, url):
        d = Downloader(url)
        d.start()
        playlist = []

        while d.is_alive():
            await asyncio.sleep(0.5)

        for entry in d.song.entries:
            song_url = "https://www.youtube.com/watch?v={}".format(entry['id'])
            playlist.append(song_url)

        log.debug("song list:\n\t{}".format(playlist))

        return playlist

    async def _play(self, sid, url):
        """Returns the song object of what's playing"""
        if type(sid) is not discord.Server:
            server = self.bot.get_server(sid)
        else:
            server = sid

        assert type(server) is discord.Server
        log.debug('starting to play on "{}"'.format(server.name))

        max_length = self.settings["MAX_LENGTH"]
        if server.id not in self.downloaders:  # We don't have a downloader
            log.debug("sid {} not in downloaders, making one".format(
                server.id))
            self.downloaders[server.id] = Downloader(url, max_length)

        if self.downloaders[server.id].url != url:  # Our downloader is old
            # I'm praying to Jeezus that we don't accidentally lose a running
            #   Downloader
            log.debug("sid {} in downloaders but wrong url".format(server.id))
            self.downloaders[server.id] = Downloader(url, max_length)

        try:
            # We're assuming we have the right thing in our downloader object
            self.downloaders[server.id].start()
            log.debug("starting our downloader for sid {}".format(server.id))
        except RuntimeError:
            # Queue manager already started it for us, isn't that nice?
            pass

        while self.downloaders[server.id].is_alive():  # Getting info w/o DL
            await asyncio.sleep(0.5)

        song = self.downloaders[server.id].song
        log.debug("sid {} wants to play songid {}".format(server.id, song.id))

        # Now we check to see if we have a cache hit
        cache_location = os.path.join(self.cache_path, song.id)
        if not os.path.exists(cache_location):
            log.debug("cache miss on song id {}".format(song.id))
            self.downloaders[server.id] = Downloader(url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

            while self.downloaders[server.id].is_alive():
                await asyncio.sleep(0.5)

            song = self.downloaders[server.id].song
        else:
            log.debug("cache hit on song id {}".format(song.id))

        voice_client = self._create_ffmpeg_player(server, song.id)
        # That ^ creates the audio_player property

        voice_client.audio_player.start()
        log.debug("starting player on sid {}".format(server.id))

        return song

    def _play_playlist(self, server, playlist):
        try:
            songlist = playlist.playlist
            name = playlist.name
        except AttributeError:
            songlist = playlist
            name = True

        self._clear_queue(server)
        self._setup_queue(server)
        self._set_queue_playlist(server, name)
        self._set_queue_repeat(server, True)
        self._set_queue(server, songlist)

    def _playlist_exists(self, server, name):
        try:
            server = server.id
        except AttributeError:
            pass

        f = "data/audio/playlists"
        f = os.path.join(f, server, name + ".txt")
        log.debug('checking for {}'.format(f))

        return fileIO(f, 'check')

    def _remove_queue(self, server):
        if server.id in self.queue:
            del self.queue[server.id]

    def _save_playlist(self, server, name, playlist):
        sid = server.id
        try:
            f = playlist.filename
            playlist = playlist.to_json()
            log.debug("got playlist object")
        except AttributeError:
            f = os.path.join("data/audio/playlists", sid, name + ".txt")

        head, _ = os.path.split(f)
        if not os.path.exists(head):
            os.makedirs(head)

        log.debug("saving playlist '{}' to {}:\n\t{}".format(name, f,
                                                             playlist))
        fileIO(f, 'save', playlist)

    def _set_queue(self, server, songlist):
        if server.id in self.queue:
            self._clear_queue(server)
        else:
            self._setup_queue(server)
        self.queue[server.id]["QUEUE"].extend(songlist)

    def _set_queue_playlist(self, server, name=True):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id]["PLAYLIST"] = name

    def _set_queue_repeat(self, server, value):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id]["REPEAT"] = value

    def _setup_queue(self, server):
        self.queue[server.id] = {"REPEAT": False, "PLAYLIST": False,
                                 "VOICE_CHANNEL_ID": None,
                                 "QUEUE": deque(), "TEMP_QUEUE": deque(),
                                 "NOW_PLAYING": None}

    def _stop_and_disconnect(self, server):
        self._clear_queue(server)
        self._stop_downloader(server)
        self._stop_player(server)
        self._disconnect_voice_client(server)

    def _stop_downloader(self, server):
        if server.id not in self.downloaders:
            return

        del self.downloaders[server.id]

    def _stop_player(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        if hasattr(voice_client, 'audio_player'):
            voice_client.audio_player.stop()
            del voice_client.audio_player

    def _valid_playlist_name(self, name):
        for l in name:
            if l.isdigit() or l.isalpha() or l == "_":
                pass
            else:
                return False
        return True

    def _valid_playable_url(self, url):
        yt = self._match_yt_url(url)
        if not yt:  # TODO: Add sc check
            return False
        return True

    @commands.command(hidden=True, pass_context=True)
    @checks.is_owner()
    async def joinvoice(self, ctx):
        """Joins your voice channel"""
        author = ctx.message.author
        server = ctx.message.server
        voice_channel = author.voice_channel

        if voice_channel is not None:
            self._stop_and_disconnect(server)

        await self._join_voice_channel(voice_channel)

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the current song, `!resume` to continue."""
        server = ctx.message.server
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.")
            return

        # We are connected somewhere
        voice_client = self.voice_client(server)

        if not hasattr(voice_client, 'audio_player'):
            await self.bot.say("Nothing playing, nothing to pause.")
        elif voice_client.audio_player.is_playing():
            voice_client.audio_player.pause()
            await self.bot.say("Paused.")
        else:
            await self.bot.say("Nothing playing, nothing to pause.")

    @commands.command(pass_context=True, no_pm=True)
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
                await self._join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                pass  # TODO: Perms

        # Checking if playing in current server

        if self.is_playing(server):
            await self.bot.say("I'm already playing a song on this server!")
            return  # TODO: Possibly execute queue?

        # If not playing, spawn a downloader if it doesn't exist and begin
        #   downloading the next song

        if self.currently_downloading(server):
            await self.bot.say("I'm already downloading a file!")
            return

        # TODO: URL validation
        # TODO: song validity check
        self._clear_queue(server)
        self._stop_player(server)
        self._add_to_queue(server, url)

    @commands.group(pass_context=True, no_pm=True)
    async def playlist(self, ctx):
        """Playlist management/control."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @playlist.command(pass_context=True, no_pm=True, name="add")
    async def playlist_add(self, ctx, name, url):
        """Add a YouTube or Soundcloud playlist."""
        server = ctx.message.server
        author = ctx.message.author
        if not self._valid_playlist_name(name) or len(name) > 25:
            await self.bot.say("That playlist name is invalid. It must only"
                               " contain alpha-numeric characters or _.")
            return

        if self._match_yt_playlist(url) or self._match_sc_playlist(url):
            try:
                await self.bot.say("Enumerating song list...this could take"
                                   " a few moments.")
                songlist = await self._parse_playlist(url)
            except InvalidPlaylist:
                await self.bot.say("That playlist URL is invalid.")
                return

            playlist = self._make_playlist(author, url, songlist)
            # Returns a Playlist object

            playlist.name = name
            playlist.server = server

            self._save_playlist(server, name, playlist)
            await self.bot.say("Playlist '{}' saved.".format(name))
        else:
            await self.bot.say("That URL is not a valid Soundcloud or YouTube"
                               " playlist link. If you think this is in error"
                               " please let us know and we'll get it"
                               " fixed ASAP.")

    @playlist.command(pass_context=True, no_pm=True, name="play")
    async def playlist_play(self, ctx, name):
        """Plays a playlist."""
        server = ctx.message.server
        voice_channel = ctx.message.author.voice_channel
        if voice_channel is None:
            await self.bot.say("You must be in a voice channel to start a"
                               " playlist.")
            return

        if self._playlist_exists(server, name):
            # TODO: permissions checks...
            if not self.voice_connected(server):
                await self._join_voice_channel(voice_channel)
            self._clear_queue(server)
            playlist = self._load_playlist(server, name)
            self._play_playlist(server, playlist)
            await self.bot.say("Playlist queued.")
        else:
            await self.bot.say("That playlist does not exist.")

    @playlist.command(pass_context=True, no_pm=True, name="remove")
    async def playlist_remove(self, ctx, name):
        """Delete's a saved playlist."""
        server = ctx.message.server

        if self._playlist_exists(server, name):
            self._delete_playlist(server, name)
            await self.bot.say("Playlist deleted.")
        else:
            await self.bot.say("Playlist not found.")

    @commands.command(pass_context=True, no_pm=True, name="queue")
    async def _queue(self, ctx, url):
        """Queue's a song to play next. Extended functionality in `!help`

        If you use `queue` when one song is playing, your new song will get
            added to the song loop (if running). If you use `queue` when a
            playlist is running, it will temporarily be played next and will
            NOT stay in the playlist loop."""
        server = ctx.message.server
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.")
            return

        # We are connected somewhere
        if not self.queue[server.id]:
            log.debug("Something went wrong, we're connected but have no"
                      " queue entry.")
            raise VoiceNotConnected("Something went wrong, we have no internal"
                                    " queue to modify. This should never"
                                    " happen.")

        # We have a queue to modify
        if self.queue[server.id]["PLAYLIST"]:
            log.debug("queueing to the temp_queue for sid {}".format(
                server.id))
            self._add_to_temp_queue(server, url)
        else:
            log.debug("queueing to the actual queue for sid {}".format(
                server.id))
            self._add_to_queue(server, url)
        await self.bot.say("Queued.")

    @commands.group(pass_context=True, no_pm=True)
    async def repeat(self, ctx):
        """Toggles REPEAT"""
        server = ctx.message.server
        if ctx.invoked_subcommand is None:
            if self.is_playing(server):
                if self.queue[server.id]["REPEAT"]:
                    msg = "The queue is currently looping."
                else:
                    msg = "The queue is currently not looping."
                await self.bot.say(msg)
                await self.bot.say("Do `!repeat toggle` to change this.")
            else:
                await self.bot.say("Play something to see this setting.")

    @repeat.command(pass_context=True, no_pm=True)
    async def repeat_toggle(self, ctx):
        """Flips repeat setting."""
        server = ctx.message.server
        if not self.is_playing(server):
            await self.bot.say("I don't have a repeat setting to flip."
                               " Try playing something first.")
            return

        self.queue[server.id]["REPEAT"] = not self.queue[server.id]["REPEAT"]
        repeat = self.queue[server.id]["REPEAT"]
        if repeat:
            await self.bot.say("Repeat toggled on.")
        else:
            await self.bot.say("Repeat toggled off.")

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Resumes a paused song or playlist"""
        server = ctx.message.server
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.")
            return

        # We are connected somewhere
        voice_client = self.voice_client(server)

        if not hasattr(voice_client, 'audio_player'):
            await self.bot.say("Nothing paused, nothing to resume.")
        elif not voice_client.audio_player.is_done() and \
                not voice_client.audio_player.is_playing():
            voice_client.audio_player.resume()
            await self.bot.say("Resuming.")
        else:
            await self.bot.say("Nothing paused, nothing to resume.")

    @commands.command(pass_context=True, no_pm=True)
    async def song(self, ctx):
        """Info about the current song."""
        server = ctx.message.server
        if self.is_playing(server):
            song = self.queue[server.id]["NOW_PLAYING"]
            if song:
                await self.bot.say("[{}] {}".format(song.creator,
                                                    song.title))
            else:
                await self.bot.say("I don't know what this song is either.")
        else:
            await self.bot.say("I'm not playing anything on this server.")

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Skips the currently playing song"""
        server = ctx.message.server
        if self.is_playing(server):
            vc = self.voice_client(server)
            vc.audio_player.stop()
            await self.bot.say("Skipping...")
        else:
            await self.bot.say("Can't skip if I'm not playing.")

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        """Stops a currently playing song or playlist. CLEARS QUEUE."""
        # TODO: All those fun checks for permissions
        server = ctx.message.server

        self._stop_and_disconnect(server)
        self._remove_queue(server)

    def is_playing(self, server):
        if not self.voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), 'audio_player'):
            return False
        if not self.voice_client(server).audio_player.is_playing():
            return False
        return True

    async def cache_manager(self):
        # min cache size: max([50, n * log(n)])
        pass

    def currently_downloading(self, server):
        if server.id in self.downloaders:
            if self.downloaders[server.id].is_alive():
                return True
        return False

    def get_server_settings(self, server):
        try:
            sid = server.id
        except:
            sid = server

        if sid in self.settings["SERVERS"]:
            self.settings["SERVERS"][sid] = {}
        ret = self.settings["SERVERS"][sid]

        for setting in self.server_specific_setting_keys:
            if setting not in ret:
                # Add the default
                ret[setting] = self.settings[setting]

        self.save_settings()

        return ret

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
        max_length = self.settings["MAX_LENGTH"]

        # This is a reference, or should be at least
        temp_queue = self.queue[server.id]["TEMP_QUEUE"]
        queue = self.queue[server.id]["QUEUE"]
        repeat = self.queue[server.id]["REPEAT"]

        assert temp_queue is self.queue[server.id]["TEMP_QUEUE"]
        assert queue is self.queue[server.id]["QUEUE"]

        # _play handles creating the voice_client and player for us

        if not self.is_playing(server):
            log.debug("not playing anything on sid {}".format(server.id) +
                      ", attempting to start a new song.")
            if len(temp_queue) > 0:
                # Fake queue for irdumb's temp playlist songs
                log.debug("calling _play because temp_queue is non-empty")
                song = await self._play(sid, temp_queue.popleft())
            elif len(queue) > 0:  # We're in the normal queue
                url = queue.popleft()
                log.debug("calling _play on the normal queue")
                song = await self._play(sid, url)
                if repeat:
                    queue.appendleft(url)
            else:
                song = None
            self.queue[server.id]["NOW_PLAYING"] = song
            log.debug("set now_playing for sid {}".format(server.id))
        else:  # We're playing but we might be able to download a new song
            curr_dl = self.downloaders[server.id]
            if len(temp_queue) > 0:
                next_dl = Downloader(temp_queue.peekleft(),
                                     max_length)
            elif len(queue) > 0:
                next_dl = Downloader(queue.peekleft(), max_length)
            else:
                next_dl = None

            if next_dl is not None:
                # Download next song
                next_dl.start()
                await self._download_next(server, curr_dl, next_dl)

    async def queue_scheduler(self):
        while self == self.bot.get_cog('Audio'):
            tasks = []
            for sid in self.queue:
                if len(self.queue[sid]["QUEUE"]) == 0 and \
                        len(self.queue[sid]["TEMP_QUEUE"]) == 0:
                    continue
                # log.debug("scheduler found a non-empty queue"
                #           " for sid: {}".format(sid))
                tasks.append(
                    self.bot.loop.create_task(self.queue_manager(sid)))
                completed = [t.done() for t in tasks]
                while not all(completed):
                    await asyncio.sleep(0.5)
            await asyncio.sleep(1)

    def save_settings(self):
        fileIO('data/audio/settings.json', 'save', self.settings)

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
        # TODO: Channel changing (by drag n drop)
        # TODO: Muting


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
               "TITLE_STATUS": True, "AVCONV": False,
               "SERVERS": {}}
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
