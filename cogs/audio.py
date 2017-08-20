import discord
from discord.ext import commands
import threading
import os
from random import shuffle, choice
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils.chat_formatting import pagify, escape
from urllib.parse import urlparse
from __main__ import send_cmd_help, settings
from json import JSONDecodeError
import re
import logging
import collections
import copy
import asyncio
import math
import time
import inspect
import subprocess
import urllib.parse
from enum import Enum

__author__ = "tekulvw"
__version__ = "0.1.1"

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
    'source_address': '0.0.0.0',
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'outtmpl': "data/audio/cache/%(id)s",
    'default_search': 'auto',
    'encoding': 'utf-8'
}


class MaximumLength(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message
    

class YouTubeDlError(Exception):
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


class UnauthorizedConnect(Exception):
    pass


class UnauthorizedSpeak(Exception):
    pass


class ChannelUserLimit(Exception):
    pass


class UnauthorizedSave(Exception):
    pass


class ConnectTimeout(NotConnected):
    pass


class InvalidURL(Exception):
    pass


class InvalidSong(InvalidURL):
    pass


class InvalidPlaylist(InvalidSong):
    pass

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

class QueueKey(Enum):
	REPEAT = 1
	PLAYLIST = 2
	VOICE_CHANNEL_ID = 3
	QUEUE = 4
	TEMP_QUEUE = 5
	NOW_PLAYING = 6
	NOW_PLAYING_CHANNEL = 7

class Song:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.title = kwargs.pop('title', None)
        self.id = kwargs.pop('id', None)
        self.url = kwargs.pop('url', None)
        self.webpage_url = kwargs.pop('webpage_url', "")
        self.duration = kwargs.pop('duration', 60)
        self.start_time = kwargs.pop('start_time', None)
        self.end_time = kwargs.pop('end_time', None)

class QueuedSong:
    def __init__(self, url, channel):
        self.url = url
        self.channel = channel

class Playlist:
    def __init__(self, server=None, sid=None, name=None, author=None, url=None,
                 playlist=None, path=None, main_class=None, **kwargs):
        # when is this used? idk
        # what is server when it's global? None? idk
        self.server = server
        self._sid = sid
        self.name = name
        # this is an id......
        self.author = author
        self.url = url
        self.main_class = main_class  # reference to Audio
        self.path = path

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

    def is_author(self, user):
        """checks if the user is the author of this playlist
        Returns True/False"""
        return user.id == self.author

    def can_edit(self, user):
        """right now checks if user is mod or higher including server owner
        global playlists are uneditable atm

        dev notes:
        should probably be defined elsewhere later or be dynamic"""

        # I don't know how global playlists are handled.
        # Not sure if the framework is there for them to be editable.
        # Don't know how they are handled by Playlist
        # Don't know how they are handled by Audio
        # so let's make sure it's not global at all.
        if self.main_class._playlist_exists_global(self.name):
            return False

        admin_role = settings.get_server_admin(self.server)
        mod_role = settings.get_server_mod(self.server)

        is_playlist_author = self.is_author(user)
        is_bot_owner = user.id == settings.owner
        is_server_owner = self.server.owner.id == self.author
        is_admin = discord.utils.get(user.roles, name=admin_role) is not None
        is_mod = discord.utils.get(user.roles, name=mod_role) is not None

        return any((is_playlist_author,
                    is_bot_owner,
                    is_server_owner,
                    is_admin,
                    is_mod))

    # def __del__() ?

    def append_song(self, author, url):
        if not self.can_edit(author):
            raise UnauthorizedSave
        elif not self.main_class._valid_playable_url(url):
            raise InvalidURL
        else:
            self.playlist.append(url)
            self.save()

    def save(self):
        dataIO.save_json(self.path, self.to_json())

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
        self.done = threading.Event()
        self.song = None
        self._download = download
        self.hit_max_length = threading.Event()
        self._yt = None
        self.error = None

    def run(self):
        try:
            self.get_info()
            if self._download:
                self.download()
        except youtube_dl.utils.DownloadError as e:
            self.error = str(e)
        except MaximumLength:
            self.hit_max_length.set()
        except OSError as e:
            log.warning("An operating system error occurred while downloading URL '{}':\n'{}'".format(self.url, str(e)))
        self.done.set()

    def download(self):
        self.duration_check()

        if not os.path.isfile('data/audio/cache' + self.song.id):
            video = self._yt.extract_info(self.url)
            self.song = Song(**video)

    def duration_check(self):
        log.debug("duration {} for songid {}".format(self.song.duration,
                                                     self.song.id))
        if self.max_duration and self.song.duration > self.max_duration:
            log.debug("songid {} too long".format(self.song.id))
            raise MaximumLength("songid {} has duration {} > {}".format(
                self.song.id, self.song.duration, self.max_duration))

    def get_info(self):
        if self._yt is None:
            self._yt = youtube_dl.YoutubeDL(youtube_dl_options)
        if "[SEARCH:]" not in self.url:
            video = self._yt.extract_info(self.url, download=False,
                                          process=False)
        else:
            self.url = self.url[9:]
            yt_id = self._yt.extract_info(
                self.url, download=False)["entries"][0]["id"]
            # Should handle errors here ^
            self.url = "https://youtube.com/watch?v={}".format(yt_id)
            video = self._yt.extract_info(self.url, download=False,
                                          process=False)

        if(video is not None):
            self.song = Song(**video)


class Audio:
    """Music Streaming."""

    def __init__(self, bot, player):
        self.bot = bot
        self.queue = {}  # add deque's, repeat
        self.downloaders = {}  # sid: object
        self.settings = dataIO.load_json("data/audio/settings.json")
        self.server_specific_setting_keys = ["VOLUME", "VOTE_ENABLED",
                                             "VOTE_THRESHOLD", "NOPPL_DISCONNECT"]
        self.cache_path = "data/audio/cache"
        self.local_playlist_path = "data/audio/localtracks"
        self._old_game = False

        self.skip_votes = {}

        self.connect_timers = {}

        if player == "ffmpeg":
            self.settings["AVCONV"] = False
        elif player == "avconv":
            self.settings["AVCONV"] = True
        self.save_settings()

    async def _add_song_status(self, song):
        if self._old_game is False:
            self._old_game = list(self.bot.servers)[0].me.game
        status = list(self.bot.servers)[0].me.status
        game = discord.Game(name=song.title)
        await self.bot.change_presence(status=status, game=game)
        log.debug('Bot status changed to song title: ' + song.title)

    def _add_to_queue(self, server, url, channel):
        if server.id not in self.queue:
            self._setup_queue(server)
        queued_song = QueuedSong(url, channel)
        self.queue[server.id][QueueKey.QUEUE].append(queued_song)

    def _add_to_temp_queue(self, server, url, channel):
        if server.id not in self.queue:
            self._setup_queue(server)
        queued_song = QueuedSong(url, channel)
        self.queue[server.id][QueueKey.TEMP_QUEUE].append(queued_song)

    def _addleft_to_queue(self, server, url, channel):
        if server.id not in self.queue:
            self._setup_queue()
        queued_song = QueuedSong(url, channel)
        self.queue[server.id][QueueKey.QUEUE].appendleft(queued_song)

    def _cache_desired_files(self):
        filelist = []
        for server in self.downloaders:
            song = self.downloaders[server].song
            try:
                filelist.append(song.id)
            except AttributeError:
                pass
        shuffle(filelist)
        return filelist

    def _cache_max(self):
        setting_max = self.settings["MAX_CACHE"]
        return max([setting_max, self._cache_min()])  # enforcing hard limit

    def _cache_min(self):
        x = self._server_count()
        return max([60, 48 * math.log(x) * x**0.3])  # log is not log10

    def _cache_required_files(self):
        queue = copy.deepcopy(self.queue)
        filelist = []
        for server in queue:
            now_playing = queue[server].get(QueueKey.NOW_PLAYING)
            try:
                filelist.append(now_playing.id)
            except AttributeError:
                pass
        return filelist

    def _cache_size(self):
        songs = os.listdir(self.cache_path)
        size = sum(map(lambda s: os.path.getsize(
            os.path.join(self.cache_path, s)) / 10**6, songs))
        return size

    def _cache_too_large(self):
        if self._cache_size() > self._cache_max():
            return True
        return False

    def _clear_queue(self, server):
        if server.id not in self.queue:
            return
        self.queue[server.id][QueueKey.QUEUE] = deque()
        self.queue[server.id][QueueKey.TEMP_QUEUE] = deque()

    async def _create_ffmpeg_player(self, server, filename, local=False, start_time=None, end_time=None):
        """This function will guarantee we have a valid voice client,
            even if one doesn't exist previously."""
        voice_channel_id = self.queue[server.id][QueueKey.VOICE_CHANNEL_ID]
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
            await self._join_voice_channel(to_connect)  # SHIT
        elif voice_client.channel.id != voice_channel_id:
            # This was decided at 3:45 EST in #advanced-testing by 26
            self.queue[server.id][QueueKey.VOICE_CHANNEL_ID] = voice_client.channel.id
            log.debug("reconnect chan id for sid {} is wrong, fixing".format(
                server.id))

        # Okay if we reach here we definitively have a working voice_client

        if local:
            song_filename = os.path.join(self.local_playlist_path, filename)
        else:
            song_filename = os.path.join(self.cache_path, filename)

        use_avconv = self.settings["AVCONV"]
        options = '-b:a 64k -bufsize 64k'
        before_options = ''

        if start_time:
            before_options += '-ss {}'.format(start_time)
        if end_time:
            options += ' -to {} -copyts'.format(end_time)

        try:
            voice_client.audio_player.process.kill()
            log.debug("killed old player")
        except AttributeError:
            pass
        except ProcessLookupError:
            pass

        log.debug("making player on sid {}".format(server.id))

        voice_client.audio_player = voice_client.create_ffmpeg_player(
            song_filename, use_avconv=use_avconv, options=options, before_options=before_options)

        # Set initial volume
        vol = self.get_server_settings(server)['VOLUME'] / 100
        voice_client.audio_player.volume = vol

        return voice_client  # Just for ease of use, it's modified in-place

    # TODO: _current_playlist

    # TODO: _current_song

    def _delete_playlist(self, server, name):
        if not name.endswith('.txt'):
            name = name + ".txt"
        try:
            os.remove(os.path.join('data/audio/playlists', server.id, name))
        except OSError:
            pass
        except WindowsError:
            pass

    # TODO: _disable_controls()

    async def _disconnect_voice_client(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        await voice_client.disconnect()

    async def _download_all(self, queued_song_list, channel):
        """
        Doesn't actually download, just get's info for uses like queue_list
        """
        downloaders = []
        for queued_song in queued_song_list:
            d = Downloader(queued_song.url)
            d.start()
            downloaders.append(d)

        while any([d.is_alive() for d in downloaders]):
            await asyncio.sleep(0.1)
            
        songs = [d.song for d in downloaders if d.song is not None and d.error is None]
           
        invalid_downloads = [d for d in downloaders if d.error is not None]
        invalid_number = len(invalid_downloads)
        if(invalid_number > 0):
            await self.bot.send_message(channel, "The queue contains {} item(s)"
                                            " that can not be played.".format(invalid_number))

        return songs

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
            
        error = next_dl.error
        if(error is not None):
            raise YouTubeDlError(error)

        if curr_dl.song.id != next_dl.song.id:
            log.debug("downloader ID's mismatch on sid {}".format(server.id) +
                      " gonna start dl-ing the next thing on the queue"
                      " id {}".format(next_dl.song.id))
            try:
                next_dl.duration_check()
            except MaximumLength:
                return
            self.downloaders[server.id] = Downloader(next_dl.url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

    def _dump_cache(self, ignore_desired=False):
        reqd = self._cache_required_files()
        log.debug("required cache files:\n\t{}".format(reqd))

        opt = self._cache_desired_files()
        log.debug("desired cache files:\n\t{}".format(opt))

        prev_size = self._cache_size()

        for file in os.listdir(self.cache_path):
            if file not in reqd:
                if ignore_desired or file not in opt:
                    try:
                        os.remove(os.path.join(self.cache_path, file))
                    except OSError:
                        # A directory got in the cache?
                        pass
                    except WindowsError:
                        # Removing a file in use, reqd failed
                        pass

        post_size = self._cache_size()
        dumped = prev_size - post_size

        if not ignore_desired and self._cache_too_large():
            log.debug("must dump desired files")
            return dumped + self._dump_cache(ignore_desired=True)

        log.debug("dumped {} MB of audio files".format(dumped))

        return dumped

    # TODO: _enable_controls()

    # returns list of active voice channels
    # assuming list does not change during the execution of this function
    # if that happens, blame asyncio.
    def _get_active_voice_clients(self):
        avcs = []
        for vc in self.bot.voice_clients:
            if hasattr(vc, 'audio_player') and not vc.audio_player.is_done():
                avcs.append(vc)
        return avcs

    def _get_queue(self, server, limit):
        if server.id not in self.queue:
            return []

        ret = []
        for i in range(limit):
            try:
                ret.append(self.queue[server.id][QueueKey.QUEUE][i])
            except IndexError:
                pass

        return ret

    def _get_queue_nowplaying(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.NOW_PLAYING]
		
    def _get_queue_nowplaying_channel(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.NOW_PLAYING_CHANNEL]

    def _get_queue_playlist(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.PLAYLIST]

    def _get_queue_repeat(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.REPEAT]

    def _get_queue_tempqueue(self, server, limit):
        if server.id not in self.queue:
            return []

        ret = []
        for i in range(limit):
            try:
                ret.append(self.queue[server.id][QueueKey.TEMP_QUEUE][i])
            except IndexError:
                pass
        return ret

    async def _guarantee_downloaded(self, server, url):
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

        # Getting info w/o download
        self.downloaders[server.id].done.wait()
        
        # Youtube-DL threw an exception.
        error = self.downloaders[server.id].error
        if(error is not None):
            raise YouTubeDlError(error)

        # This will throw a maxlength exception if required
        self.downloaders[server.id].duration_check()
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

        return song

    def _is_queue_playlist(self, server):
        if server.id not in self.queue:
            return False

        return self.queue[server.id][QueueKey.PLAYLIST]

    async def _join_voice_channel(self, channel):
        server = channel.server
        connect_time = self.connect_timers.get(server.id, 0)
        if time.time() < connect_time:
            diff = int(connect_time - time.time())
            raise ConnectTimeout("You are on connect cooldown for another {}"
                                 " seconds.".format(diff))
        if server.id in self.queue:
            self.queue[server.id][QueueKey.VOICE_CHANNEL_ID] = channel.id
        try:
            await asyncio.wait_for(self.bot.join_voice_channel(channel),
                                   timeout=5, loop=self.bot.loop)
        except asyncio.futures.TimeoutError as e:
            log.exception(e)
            self.connect_timers[server.id] = time.time() + 300
            raise ConnectTimeout("We timed out connecting to a voice channel,"
                                 " please try again in 10 minutes.")

    def _list_local_playlists(self):
        ret = []
        for thing in os.listdir(self.local_playlist_path):
            if os.path.isdir(os.path.join(self.local_playlist_path, thing)):
                ret.append(thing)
        log.debug("local playlists:\n\t{}".format(ret))
        return ret

    def _list_playlists(self, server):
        try:
            server = server.id
        except:
            pass
        path = "data/audio/playlists"
        old_playlists = [f[:-4] for f in os.listdir(path)
                         if f.endswith(".txt")]
        path = os.path.join(path, server)
        if os.path.exists(path):
            new_playlists = [f[:-4] for f in os.listdir(path)
                             if f.endswith(".txt")]
        else:
            new_playlists = []
        return list(set(old_playlists + new_playlists))

    def _load_playlist(self, server, name, local=True):
        try:
            server = server.id
        except:
            pass

        f = "data/audio/playlists"
        if local:
            f = os.path.join(f, server, name + ".txt")
        else:
            f = os.path.join(f, name + ".txt")
        kwargs = dataIO.load_json(f)

        kwargs['path'] = f
        kwargs['main_class'] = self
        kwargs['name'] = name
        kwargs['sid'] = server
        kwargs['server'] = self.bot.get_server(server)

        return Playlist(**kwargs)

    def _local_playlist_songlist(self, name):
        dirpath = os.path.join(self.local_playlist_path, name)
        return sorted(os.listdir(dirpath))

    def _make_local_song(self, filename):
        # filename should be playlist_folder/file_name
        folder, song = os.path.split(filename)
        return Song(name=song, id=filename, title=song, url=filename,
                    webpage_url=filename)

    def _make_playlist(self, author, url, songlist):
        try:
            author = author.id
        except:
            pass

        return Playlist(author=author, url=url, playlist=songlist)

    def _match_sc_playlist(self, url):
        return self._match_sc_url(url)

    def _match_yt_playlist(self, url):
        if not self._match_yt_url(url):
            return False
        yt_playlist = re.compile(
            r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)'
            r'((\/playlist\?)|\/watch\?).*(list=)(.*)(&|$)')
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
            r'^(https?\:\/\/)?(www\.|m\.)?(youtube\.com|youtu\.?be)\/.+$')
        if yt_link.match(url):
            return True
        return False

    def _match_any_url(self, url):
        url = urlparse(url)
        if url.scheme and url.netloc and url.path:
            return True
        return False

    # TODO: _next_songs_in_queue

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

        error = d.error
        if(error is not None):
            raise YouTubeDlError(error)

        for entry in d.song.entries:
            if entry["url"][4] != "s":
                song_url = "https{}".format(entry["url"][4:])
                playlist.append(song_url)
            else:
                playlist.append(entry.url)

        return playlist

    async def _parse_yt_playlist(self, url):
        d = Downloader(url)
        d.start()
        playlist = []

        while d.is_alive():
            await asyncio.sleep(0.5)

        error = d.error
        if(error is not None):
            raise YouTubeDlError(error)

        for entry in d.song.entries:
            try:
                song_url = "https://www.youtube.com/watch?v={}".format(
                    entry['id'])
                playlist.append(song_url)
            except AttributeError:
                pass
            except TypeError:
                pass

        log.debug("song list:\n\t{}".format(playlist))

        return playlist

    async def _play(self, sid, url, channel):
        """Returns the song object of what's playing"""
        if type(sid) is not discord.Server:
            server = self.bot.get_server(sid)
        else:
            server = sid

        assert type(server) is discord.Server
        log.debug('starting to play on "{}"'.format(server.name))

        if self._valid_playable_url(url) or "[SEARCH:]" in url:
            clean_url = self._clean_url(url)
            try:
                song = await self._guarantee_downloaded(server, url)
            except YouTubeDlError as e:
                message = ("I'm unable to play '{}' because of an error:\n"
                          "'{}'".format(clean_url, str(e)))
                message = escape(message, mass_mentions=True)
                await self.bot.send_message(channel, message)
                return
            except MaximumLength:
                message = ("I'm unable to play '{}' because it exceeds the "
                          "maximum audio length.".format(clean_url))
                message = escape(message, mass_mentions=True)
                await self.bot.send_message(channel, message)
                return
            local = False
        else:  # Assume local
            try:
                song = self._make_local_song(url)
                local = True
            except FileNotFoundError:
                raise

        voice_client = await self._create_ffmpeg_player(server, song.id,
                                                        local=local,
                                                        start_time=song.start_time,
                                                        end_time=song.end_time)
        # That ^ creates the audio_player property

        voice_client.audio_player.start()
        log.debug("starting player on sid {}".format(server.id))

        return song

    def _play_playlist(self, server, playlist, channel):
        try:
            songlist = playlist.playlist
            name = playlist.name
        except AttributeError:
            songlist = playlist
            name = True
            
        songlist = self._songlist_change_url_to_queued_song(songlist, channel)

        log.debug("setting up playlist {} on sid {}".format(name, server.id))

        self._stop_player(server)
        self._stop_downloader(server)
        self._clear_queue(server)

        log.debug("finished resetting state on sid {}".format(server.id))

        self._setup_queue(server)
        self._set_queue_playlist(server, name)
        self._set_queue_repeat(server, True)
        self._set_queue(server, songlist)

    def _play_local_playlist(self, server, name, channel):
        songlist = self._local_playlist_songlist(name)

        ret = []
        for song in songlist:
            ret.append(os.path.join(name, song))

        ret_playlist = Playlist(server=server, name=name, playlist=ret)
        self._play_playlist(server, ret_playlist, channel)
        
    def _songlist_change_url_to_queued_song(self, songlist, channel):
        queued_songlist = []
        for song in songlist:
            queued_song = QueuedSong(song, channel)
            queued_songlist.append(queued_song)
            
        return queued_songlist

    def _player_count(self):
        count = 0
        queue = copy.deepcopy(self.queue)
        for sid in queue:
            server = self.bot.get_server(sid)
            try:
                vc = self.voice_client(server)
                if vc.audio_player.is_playing():
                    count += 1
            except:
                pass
        return count

    def _playlist_exists(self, server, name):
        return self._playlist_exists_local(server, name) or \
            self._playlist_exists_global(name)

    def _playlist_exists_global(self, name):
        f = "data/audio/playlists"
        f = os.path.join(f, name + ".txt")
        log.debug('checking for {}'.format(f))

        return dataIO.is_valid_json(f)

    def _playlist_exists_local(self, server, name):
        try:
            server = server.id
        except AttributeError:
            pass

        f = "data/audio/playlists"
        f = os.path.join(f, server, name + ".txt")
        log.debug('checking for {}'.format(f))

        return dataIO.is_valid_json(f)

    def _remove_queue(self, server):
        if server.id in self.queue:
            del self.queue[server.id]

    async def _remove_song_status(self):
        if self._old_game is not False:
            status = list(self.bot.servers)[0].me.status
            await self.bot.change_presence(game=self._old_game,
                                           status=status)
            log.debug('Bot status returned to ' + str(self._old_game))
            self._old_game = False

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
        dataIO.save_json(f, playlist)

    def _shuffle_queue(self, server):
        shuffle(self.queue[server.id][QueueKey.QUEUE])

    def _shuffle_temp_queue(self, server):
        shuffle(self.queue[server.id][QueueKey.TEMP_QUEUE])

    def _server_count(self):
        return max([1, len(self.bot.servers)])

    def _set_queue(self, server, songlist):
        if server.id in self.queue:
            self._clear_queue(server)
        else:
            self._setup_queue(server)
        self.queue[server.id][QueueKey.QUEUE].extend(songlist)

    def _set_queue_channel(self, server, channel):
        if server.id not in self.queue:
            return

        try:
            channel = channel.id
        except AttributeError:
            pass

        self.queue[server.id][QueueKey.VOICE_CHANNEL_ID] = channel

    def _set_queue_nowplaying(self, server, song, channel):
        if server.id not in self.queue:
            return

        self.queue[server.id][QueueKey.NOW_PLAYING] = song
        self.queue[server.id][QueueKey.NOW_PLAYING_CHANNEL] = channel

    def _set_queue_playlist(self, server, name=True):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id][QueueKey.PLAYLIST] = name

    def _set_queue_repeat(self, server, value):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id][QueueKey.REPEAT] = value

    def _setup_queue(self, server):
        self.queue[server.id] = {QueueKey.REPEAT: False, QueueKey.PLAYLIST: False,
                                 QueueKey.VOICE_CHANNEL_ID: None,
                                 QueueKey.QUEUE: deque(), QueueKey.TEMP_QUEUE: deque(),
                                 QueueKey.NOW_PLAYING: None, QueueKey.NOW_PLAYING_CHANNEL: None}

    def _stop(self, server):
        self._setup_queue(server)
        self._stop_player(server)
        self._stop_downloader(server)
        self.bot.loop.create_task(self._update_bot_status())

    async def _stop_and_disconnect(self, server):
        self._stop(server)
        await self._disconnect_voice_client(server)

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

    # no return. they can check themselves.
    async def _update_bot_status(self):
        if self.settings["TITLE_STATUS"]:
            song = None
            try:
                active_servers = self._get_active_voice_clients()
            except:
                log.debug("Voice client changed while trying to update bot's"
                          " song status")
                return
            if len(active_servers) == 1:
                server = active_servers[0].server
                song = self._get_queue_nowplaying(server)
            if song:
                await self._add_song_status(song)
            else:
                await self._remove_song_status()

    def _valid_playlist_name(self, name):
        for char in name:
            if char.isdigit() or char.isalpha() or char == "_":
                pass
            else:
                return False
        return True

    def _valid_playable_url(self, url):
        yt = self._match_yt_url(url)
        sc = self._match_sc_url(url)
        if yt or sc:  # TODO: Add sc check
            return True
        return False
    
    def _clean_url(self, url):
        if(self._valid_playable_url(url)):
            return "<{}>".format(url)
        
        return url.replace("[SEARCH:]", "")

    @commands.group(pass_context=True)
    async def audioset(self, ctx):
        """Audio settings."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @audioset.command(name="cachemax")
    @checks.is_owner()
    async def audioset_cachemax(self, size: int):
        """Set the max cache size in MB"""
        if size < self._cache_min():
            await self.bot.say("Sorry, but because of the number of servers"
                               " that your bot is in I cannot safely allow"
                               " you to have less than {} MB of cache.".format(
                                   self._cache_min()))
            return

        self.settings["MAX_CACHE"] = size
        await self.bot.say("Max cache size set to {} MB.".format(size))
        self.save_settings()

    @audioset.command(name="emptydisconnect", pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def audioset_emptydisconnect(self, ctx):
        """Toggles auto disconnection when everyone leaves the channel"""
        server = ctx.message.server
        settings = self.get_server_settings(server.id)
        noppl_disconnect = settings.get("NOPPL_DISCONNECT", True)
        self.set_server_setting(server, "NOPPL_DISCONNECT",
                                not noppl_disconnect)
        if not noppl_disconnect:
            await self.bot.say("If there is no one left in the voice channel"
                               " the bot will automatically disconnect after"
                               " five minutes.")
        else:
            await self.bot.say("The bot will no longer auto disconnect"
                               " if the voice channel is empty.")
        self.save_settings()

    @audioset.command(name="maxlength")
    @checks.is_owner()
    async def audioset_maxlength(self, length: int):
        """Maximum track length (seconds) for requested links"""
        if length <= 0:
            await self.bot.say("Wow, a non-positive length value...aren't"
                               " you smart.")
            return
        self.settings["MAX_LENGTH"] = length
        await self.bot.say("Maximum length is now {} seconds.".format(length))
        self.save_settings()

    @audioset.command(name="player")
    @checks.is_owner()
    async def audioset_player(self):
        """Toggles between Ffmpeg and Avconv"""
        self.settings["AVCONV"] = not self.settings["AVCONV"]
        if self.settings["AVCONV"]:
            await self.bot.say("Player toggled. You're now using avconv.")
        else:
            await self.bot.say("Player toggled. You're now using ffmpeg.")
        self.save_settings()

    @audioset.command(name="status")
    @checks.is_owner()  # cause effect is cross-server
    async def audioset_status(self):
        """Enables/disables songs' titles as status"""
        self.settings["TITLE_STATUS"] = not self.settings["TITLE_STATUS"]
        if self.settings["TITLE_STATUS"]:
            await self.bot.say("If only one server is playing music, songs'"
                               " titles will now show up as status")
            # not updating on disable if we say disable
            #   means don't mess with it.
            await self._update_bot_status()
        else:
            await self.bot.say("Songs' titles will no longer show up as"
                               " status")
        self.save_settings()

    @audioset.command(pass_context=True, name="volume", no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def audioset_volume(self, ctx, percent: int=None):
        """Sets the volume (0 - 100)
        Note: volume may be set up to 200 but you may experience clipping."""
        server = ctx.message.server
        if percent is None:
            vol = self.get_server_settings(server)['VOLUME']
            msg = "Volume is currently set to %d%%" % vol
        elif percent >= 0 and percent <= 200:
            self.set_server_setting(server, "VOLUME", percent)
            msg = "Volume is now set to %d." % percent
            if percent > 100:
                msg += ("\nWarning: volume levels above 100 may result in"
                        " clipping")

            # Set volume of playing audio
            vc = self.voice_client(server)
            if vc:
                vc.audio_player.volume = percent / 100

            self.save_settings()
        else:
            msg = "Volume must be between 0 and 100."
        await self.bot.say(msg)

    @audioset.command(pass_context=True, name="vote", no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def audioset_vote(self, ctx, percent: int):
        """Percentage needed for the masses to skip songs. 0 to disable."""
        server = ctx.message.server

        if percent < 0:
            await self.bot.say("Can't be less than zero.")
            return
        elif percent > 100:
            percent = 100

        if percent == 0:
            enabled = False
            await self.bot.say("Voting disabled. All users can stop or skip.")
        else:
            enabled = True
            await self.bot.say("Vote percentage set to {}%".format(percent))

        self.set_server_setting(server, "VOTE_THRESHOLD", percent)
        self.set_server_setting(server, "VOTE_ENABLED", enabled)
        self.save_settings()

    @commands.group(pass_context=True)
    async def audiostat(self, ctx):
        """General stats on audio stuff."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @audiostat.command(name="servers")
    async def audiostat_servers(self):
        """Number of servers currently playing."""

        count = self._player_count()

        await self.bot.say("Currently playing music in {} servers.".format(
            count))

    @commands.group(pass_context=True)
    async def cache(self, ctx):
        """Cache management tools."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @cache.command(name="dump")
    @checks.is_owner()
    async def cache_dump(self):
        """Dumps the cache."""
        dumped = self._dump_cache()
        await self.bot.say("Dumped {:.3f} MB of audio files.".format(dumped))

    @cache.command(name='stats')
    async def cache_stats(self):
        """Reports info about the cache.
            - Current size of the cache.
            - Maximum cache size. User setting or minimum, whichever is higher.
            - Minimum cache size. Automatically determined by number of servers Red is running on.
        """
        await self.bot.say("Cache stats:\n"
                           "Current size: {:.2f} MB\n"
                           "Maximum: {:.1f} MB\n"
                           "Minimum: {:.1f} MB".format(self._cache_size(),
                                                       self._cache_max(),
                                                       self._cache_min()))

    @commands.group(pass_context=True, hidden=True, no_pm=True)
    @checks.is_owner()
    async def disconnect(self, ctx):
        """Disconnects from voice channel in current server."""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            await self._stop_and_disconnect(server)

    @disconnect.command(name="all", hidden=True, no_pm=True)
    async def disconnect_all(self):
        """Disconnects from all voice channels."""
        while len(list(self.bot.voice_clients)) != 0:
            vc = list(self.bot.voice_clients)[0]
            await self._stop_and_disconnect(vc.server)
        await self.bot.say("done.")

    @commands.command(hidden=True, pass_context=True, no_pm=True)
    @checks.is_owner()
    async def joinvoice(self, ctx):
        """Joins your voice channel"""
        author = ctx.message.author
        server = ctx.message.server
        voice_channel = author.voice_channel

        if voice_channel is not None:
            self._stop(server)

        await self._join_voice_channel(voice_channel)

    @commands.group(pass_context=True, no_pm=True)
    async def local(self, ctx):
        """Local playlists commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @local.command(name="start", pass_context=True, no_pm=True)
    async def play_local(self, ctx, *, name):
        """Plays a local playlist"""
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel
        channel = ctx.message.channel

        # Checking already connected, will join if not

        if not self.voice_connected(server):
            try:
                self.has_connect_perm(author, server)
            except AuthorNotConnected:
                await self.bot.say("You must join a voice channel before I can"
                                   " play anything.")
                return
            except UnauthorizedConnect:
                await self.bot.say("I don't have permissions to join your"
                                   " voice channel.")
                return
            except UnauthorizedSpeak:
                await self.bot.say("I don't have permissions to speak in your"
                                   " voice channel.")
                return
            except ChannelUserLimit:
                await self.bot.say("Your voice channel is full.")
                return
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

        lists = self._list_local_playlists()

        if not any(map(lambda l: os.path.split(l)[1] == name, lists)):
            await self.bot.say("Local playlist not found.")
            return

        self._play_local_playlist(server, name, channel)

    @local.command(name="list", no_pm=True)
    async def list_local(self):
        """Lists local playlists"""
        playlists = ", ".join(self._list_local_playlists())
        if playlists:
            playlists = "Available local playlists:\n\n" + playlists
            for page in pagify(playlists, delims=[" "]):
                await self.bot.say(page)
        else:
            await self.bot.say("There are no playlists.")

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the current song, `[p]resume` to continue."""
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
    async def play(self, ctx, *, url_or_search_terms):
        """Plays a link / searches and play"""
        url = url_or_search_terms
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel
        channel = ctx.message.channel

        # Checking if playing in current server

        if self.is_playing(server):
            await ctx.invoke(self._queue, url=url)
            return  # Default to queue

        # Checking already connected, will join if not

        try:
            self.has_connect_perm(author, server)
        except AuthorNotConnected:
            await self.bot.say("You must join a voice channel before I can"
                               " play anything.")
            return
        except UnauthorizedConnect:
            await self.bot.say("I don't have permissions to join your"
                               " voice channel.")
            return
        except UnauthorizedSpeak:
            await self.bot.say("I don't have permissions to speak in your"
                               " voice channel.")
            return
        except ChannelUserLimit:
            await self.bot.say("Your voice channel is full.")
            return

        if not self.voice_connected(server):
            await self._join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                await self._stop_and_disconnect(server)
                await self._join_voice_channel(voice_channel)

        # If not playing, spawn a downloader if it doesn't exist and begin
        #   downloading the next song

        if self.currently_downloading(server):
            await self.bot.say("I'm already downloading a file!")
            return

        url = url.strip("<>")

        if self._match_any_url(url):
            if not self._valid_playable_url(url):
                await self.bot.say("That's not a valid URL.")
                return
        else:
            url = url.replace("/", "&#47")
            url = "[SEARCH:]" + url

        if "[SEARCH:]" not in url and "youtube" in url:
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            query.pop("list", None)
            parsed_url = parsed_url._replace(query=urllib.parse.urlencode(query, True))
            url = urllib.parse.urlunparse(parsed_url)

        self._stop_player(server)
        self._clear_queue(server)
        self._add_to_queue(server, url, channel)

    @commands.command(pass_context=True, no_pm=True)
    async def prev(self, ctx):
        """Goes back to the last song."""
        # Current song is in NOW_PLAYING
        server = ctx.message.server
        channel = ctx.message.channel

        if self.is_playing(server):
            curr_url = self._get_queue_nowplaying(server).webpage_url
            last_url = None
            if self._is_queue_playlist(server):
                # need to reorder queue
                try:
                    last_url = self.queue[server.id][QueueKey.QUEUE].pop()
                except IndexError:
                    pass

            log.debug("prev on sid {}, curr_url {}".format(server.id,
                                                           curr_url))

            self._addleft_to_queue(server, curr_url, channel)
            if last_url:
                self._addleft_to_queue(server, last_url, channel)
            self._set_queue_nowplaying(server, None, None)

            self.voice_client(server).audio_player.stop()

            await self.bot.say("Going back 1 song.")
        else:
            await self.bot.say("Not playing anything on this server.")

    @commands.group(pass_context=True, no_pm=True)
    async def playlist(self, ctx):
        """Playlist management/control."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @playlist.command(pass_context=True, no_pm=True, name="create")
    async def playlist_create(self, ctx, name):
        """Creates an empty playlist"""
        server = ctx.message.server
        author = ctx.message.author
        if not self._valid_playlist_name(name) or len(name) > 25:
            await self.bot.say("That playlist name is invalid. It must only"
                               " contain alpha-numeric characters or _.")
            return

        # Returns a Playlist object
        url = None
        songlist = []
        playlist = self._make_playlist(author, url, songlist)

        playlist.name = name
        playlist.server = server

        self._save_playlist(server, name, playlist)
        await self.bot.say("Empty playlist '{}' saved.".format(name))

    @playlist.command(pass_context=True, no_pm=True, name="add")
    async def playlist_add(self, ctx, name, url):
        """Add a YouTube or Soundcloud playlist."""
        server = ctx.message.server
        author = ctx.message.author
        if not self._valid_playlist_name(name) or len(name) > 25:
            await self.bot.say("That playlist name is invalid. It must only"
                               " contain alpha-numeric characters or _.")
            return

        if self._valid_playable_url(url):
            try:
                await self.bot.say("Enumerating song list... This could take"
                                   " a few moments.")
                songlist = await self._parse_playlist(url)
            except InvalidPlaylist:
                await self.bot.say("That playlist URL is invalid.")
                return
            except YouTubeDlError as e:
                await self.bot.say("An error occurred while enumerating the playlist:\n"
                                   "'{}'".format(str(e)))
                return
				
            playlist = self._make_playlist(author, url, songlist)
            # Returns a Playlist object

            playlist.name = name
            playlist.server = server

            self._save_playlist(server, name, playlist)
            await self.bot.say("Playlist '{}' saved. Tracks: {}".format(
                name, len(songlist)))
        else:
            await self.bot.say("That URL is not a valid Soundcloud or YouTube"
                               " playlist link. If you think this is in error"
                               " please let us know and we'll get it"
                               " fixed ASAP.")

    @playlist.command(pass_context=True, no_pm=True, name="append")
    async def playlist_append(self, ctx, name, url):
        """Appends to a playlist."""
        author = ctx.message.author
        server = ctx.message.server
        if name not in self._list_playlists(server):
            await self.bot.say("There is no playlist with that name.")
            return
        playlist = self._load_playlist(
            server, name, local=self._playlist_exists_local(server, name))
        try:
            playlist.append_song(author, url)
        except UnauthorizedSave:
            await self.bot.say("You're not the author of that playlist.")
        except InvalidURL:
            await self.bot.say("Invalid link.")
        else:
            await self.bot.say("Done.")

    @playlist.command(pass_context=True, no_pm=True, name="extend")
    async def playlist_extend(self, ctx, playlist_url_or_name):
        """Extends a playlist with a playlist link"""
        # Need better wording ^
        await self.bot.say("Not implemented yet.")

    @playlist.command(pass_context=True, no_pm=True, name="list")
    async def playlist_list(self, ctx):
        """Lists all available playlists"""
        server = ctx.message.server
        playlists = ", ".join(self._list_playlists(server))
        if playlists:
            playlists = "Available playlists:\n\n" + playlists
            for page in pagify(playlists, delims=[" "]):
                await self.bot.say(page)
        else:
            await self.bot.say("There are no playlists.")

    @playlist.command(pass_context=True, no_pm=True, name="queue")
    async def playlist_queue(self, ctx, url):
        """Adds a song to the playlist loop.

        Does NOT write to disk."""
        server = ctx.message.server
        channel = ctx.message.channel
        if not self.voice_connected(server):
            await self.bot.say("Not voice connected in this server.")
            return

        # We are connected somewhere
        if server.id not in self.queue:
            log.debug("Something went wrong, we're connected but have no"
                      " queue entry.")
            raise VoiceNotConnected("Something went wrong, we have no internal"
                                    " queue to modify. This should never"
                                    " happen.")

        # We have a queue to modify
        self._add_to_queue(server, url, channel)

        await self.bot.say("Queued.")

    @playlist.command(pass_context=True, no_pm=True, name="remove")
    async def playlist_remove(self, ctx, name):
        """Deletes a saved playlist."""
        author = ctx.message.author
        server = ctx.message.server

        if not self._valid_playlist_name(name):
            await self.bot.say("The playlist's name contains invalid "
                               "characters.")
            return

        if not self._playlist_exists(server, name):
            await self.bot.say("Playlist not found.")
            return

        playlist = self._load_playlist(
            server, name, local=self._playlist_exists_local(server, name))

        if not playlist.can_edit(author):
            await self.bot.say("You do not have permissions to delete that playlist.")
            return

        self._delete_playlist(server, name)
        await self.bot.say("Playlist deleted.")

    @playlist.command(pass_context=True, no_pm=True, name="start")
    async def playlist_start(self, ctx, name):
        """Plays a playlist."""
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = ctx.message.author.voice_channel
        channel = ctx.message.channel

        caller = inspect.currentframe().f_back.f_code.co_name

        if voice_channel is None:
            await self.bot.say("You must be in a voice channel to start a"
                               " playlist.")
            return

        if self._playlist_exists(server, name):
            if not self.voice_connected(server):
                try:
                    self.has_connect_perm(author, server)
                except AuthorNotConnected:
                    await self.bot.say("You must join a voice channel before"
                                       " I can play anything.")
                    return
                except UnauthorizedConnect:
                    await self.bot.say("I don't have permissions to join your"
                                       " voice channel.")
                    return
                except UnauthorizedSpeak:
                    await self.bot.say("I don't have permissions to speak in"
                                       " your voice channel.")
                    return
                except ChannelUserLimit:
                    await self.bot.say("Your voice channel is full.")
                    return
                else:
                    await self._join_voice_channel(voice_channel)
            self._clear_queue(server)
            playlist = self._load_playlist(server, name,
                                           local=self._playlist_exists_local(
                                               server, name))
            if caller == "playlist_start_mix":
                shuffle(playlist.playlist)

            self._play_playlist(server, playlist, channel)
            await self.bot.say("Playlist queued.")
        else:
            await self.bot.say("That playlist does not exist.")

    @playlist.command(pass_context=True, no_pm=True, name="mix")
    async def playlist_start_mix(self, ctx, name):
        """Plays and mixes a playlist."""
        await self.playlist_start.callback(self, ctx, name)

    @commands.command(pass_context=True, no_pm=True, name="queue")
    async def _queue(self, ctx, *, url=None):
        """Queues a song to play next. Extended functionality in `[p]help`

        If you use `queue` when one song is playing, your new song will get
            added to the song loop (if running). If you use `queue` when a
            playlist is running, it will temporarily be played next and will
            NOT stay in the playlist loop."""
        if url is None:
            return await self._queue_list(ctx)
        server = ctx.message.server
        channel = ctx.message.channel
        if not self.voice_connected(server):
            await ctx.invoke(self.play, url_or_search_terms=url)
            return

        # We are connected somewhere
        if server.id not in self.queue:
            log.debug("Something went wrong, we're connected but have no"
                      " queue entry.")
            raise VoiceNotConnected("Something went wrong, we have no internal"
                                    " queue to modify. This should never"
                                    " happen.")

        url = url.strip("<>")

        if self._match_any_url(url):
            if not self._valid_playable_url(url):
                await self.bot.say("That's not a valid URL.")
                return
        else:
            url = "[SEARCH:]" + url

        if "[SEARCH:]" not in url and "youtube" in url:
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            query.pop("list", None)
            parsed_url = parsed_url._replace(query=urllib.parse.urlencode(query, True))
            url = urllib.parse.urlunparse(parsed_url)

        # We have a queue to modify
        if self.queue[server.id][QueueKey.PLAYLIST]:
            log.debug("queueing to the temp_queue for sid {}".format(
                server.id))
            self._add_to_temp_queue(server, url, channel)
        else:
            log.debug("queueing to the actual queue for sid {}".format(
                server.id))
            self._add_to_queue(server, url, channel)
        await self.bot.say("Queued.")

    async def _queue_list(self, ctx):
        """Not a command, use `queue` with no args to call this."""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id not in self.queue:
            await self.bot.say("Nothing playing on this server!")
            return
        elif len(self.queue[server.id][QueueKey.QUEUE]) == 0:
            await self.bot.say("Nothing queued on this server.")
            return

        msg = ""

        now_playing = self._get_queue_nowplaying(server)

        if now_playing is not None:
            msg += "\n***Now playing:***\n{}\n".format(now_playing.title)

        queued_song_list = self._get_queue(server, 5)
        tempqueued_song_list = self._get_queue_tempqueue(server, 5)

        await self.bot.say("Gathering information...")

        queue_song_list = await self._download_all(queued_song_list, channel)
        tempqueue_song_list = await self._download_all(tempqueued_song_list, channel)

        song_info = []
        for num, song in enumerate(tempqueue_song_list, 1):
            try:
                song_info.append("{}. {.title}".format(num, song))
            except AttributeError:
                song_info.append("{}. {.webpage_url}".format(num, song))

        for num, song in enumerate(queue_song_list, len(song_info) + 1):
            if num > 5:
                break
            try:
                song_info.append("{}. {.title}".format(num, song))
            except AttributeError:
                song_info.append("{}. {.webpage_url}".format(num, song))
        msg += "\n***Next up:***\n" + "\n".join(song_info)

        await self.bot.say(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def repeat(self, ctx):
        """Toggles REPEAT"""
        server = ctx.message.server
        if ctx.invoked_subcommand is None:
            if self.is_playing(server):
                if self.queue[server.id][QueueKey.REPEAT]:
                    msg = "The queue is currently looping."
                else:
                    msg = "The queue is currently not looping."
                await self.bot.say(msg)
                await self.bot.say(
                    "Do `{}repeat toggle` to change this.".format(ctx.prefix))
            else:
                await self.bot.say("Play something to see this setting.")

    @repeat.command(pass_context=True, no_pm=True, name="toggle")
    async def repeat_toggle(self, ctx):
        """Flips repeat setting."""
        server = ctx.message.server
        if not self.is_playing(server):
            await self.bot.say("I don't have a repeat setting to flip."
                               " Try playing something first.")
            return

        self._set_queue_repeat(server, not self.queue[server.id][QueueKey.REPEAT])
        repeat = self.queue[server.id][QueueKey.REPEAT]
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

    @commands.command(pass_context=True, no_pm=True, name="shuffle")
    async def _shuffle(self, ctx):
        """Shuffles the current queue"""
        server = ctx.message.server
        if server.id not in self.queue:
            await self.bot.say("I have nothing in queue to shuffle.")
            return

        self._shuffle_queue(server)
        self._shuffle_temp_queue(server)

        await self.bot.say("Queues shuffled.")

    @commands.command(pass_context=True, aliases=["next"], no_pm=True)
    async def skip(self, ctx):
        """Skips a song, using the set threshold if the requester isn't
        a mod or admin. Mods, admins and bot owner are not counted in
        the vote threshold."""
        msg = ctx.message
        server = ctx.message.server
        if self.is_playing(server):
            vchan = server.me.voice_channel
            vc = self.voice_client(server)
            if msg.author.voice_channel == vchan:
                if self.can_instaskip(msg.author):
                    vc.audio_player.stop()
                    if self._get_queue_repeat(server) is False:
                        self._set_queue_nowplaying(server, None, None)
                    await self.bot.say("Skipping...")
                else:
                    if msg.author.id in self.skip_votes[server.id]:
                        self.skip_votes[server.id].remove(msg.author.id)
                        reply = "I removed your vote to skip."
                    else:
                        self.skip_votes[server.id].append(msg.author.id)
                        reply = "you voted to skip."

                    num_votes = len(self.skip_votes[server.id])
                    # Exclude bots and non-plebs
                    num_members = sum(not (m.bot or self.can_instaskip(m))
                                      for m in vchan.voice_members)
                    vote = int(100 * num_votes / num_members)
                    thresh = self.get_server_settings(server)["VOTE_THRESHOLD"]

                    if vote >= thresh:
                        vc.audio_player.stop()
                        if self._get_queue_repeat(server) is False:
                            self._set_queue_nowplaying(server, None, None)
                        self.skip_votes[server.id] = []
                        await self.bot.say("Vote threshold met. Skipping...")
                        return
                    else:
                        reply += " Votes: %d/%d" % (num_votes, num_members)
                        reply += " (%d%% out of %d%% needed)" % (vote, thresh)
                    await self.bot.reply(reply)
            else:
                await self.bot.say("You need to be in the voice channel to skip the music.")
        else:
            await self.bot.say("Can't skip if I'm not playing.")

    def can_instaskip(self, member):
        server = member.server

        if not self.get_server_settings(server)["VOTE_ENABLED"]:
            return True

        admin_role = settings.get_server_admin(server)
        mod_role = settings.get_server_mod(server)

        is_owner = member.id == settings.owner
        is_server_owner = member == server.owner
        is_admin = discord.utils.get(member.roles, name=admin_role) is not None
        is_mod = discord.utils.get(member.roles, name=mod_role) is not None

        nonbots = sum(not m.bot for m in member.voice_channel.voice_members)
        alone = nonbots <= 1

        return is_owner or is_server_owner or is_admin or is_mod or alone

    @commands.command(pass_context=True, no_pm=True)
    async def sing(self, ctx):
        """Makes Red sing one of her songs"""
        ids = ("zGTkAVsrfg8", "cGMWL8cOeAU", "vFrjMq4aL-g", "WROI5WYBU_A",
               "41tIUr_ex3g", "f9O2Rjn1azc")
        url = "https://www.youtube.com/watch?v={}".format(choice(ids))
        await ctx.invoke(self.play, url_or_search_terms=url)

    @commands.command(pass_context=True, no_pm=True)
    async def song(self, ctx):
        """Info about the current song."""
        server = ctx.message.server
        if not self.is_playing(server):
            await self.bot.say("I'm not playing on this server.")
            return

        song = self._get_queue_nowplaying(server)
        if song:
            if not hasattr(song, 'creator'):
                song.creator = None
            if not hasattr(song, 'view_count'):
                song.view_count = None
            if not hasattr(song, 'uploader'):
                song.uploader = None
            if hasattr(song, 'duration'):
                m, s = divmod(song.duration, 60)
                h, m = divmod(m, 60)
                if h:
                    dur = "{0}:{1:0>2}:{2:0>2}".format(h, m, s)
                else:
                    dur = "{0}:{1:0>2}".format(m, s)
            else:
                dur = None
            msg = ("\n**Title:** {}\n**Author:** {}\n**Uploader:** {}\n"
                   "**Views:** {}\n**Duration:** {}\n\n<{}>".format(
                       song.title, song.creator, song.uploader,
                       song.view_count, dur, song.webpage_url))
            await self.bot.say(msg.replace("**Author:** None\n", "")
                                  .replace("**Views:** None\n", "")
                                  .replace("**Uploader:** None\n", "")
                                  .replace("**Duration:** None\n", ""))
        else:
            await self.bot.say("Darude - Sandstorm.")

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops a currently playing song or playlist. CLEARS QUEUE."""
        server = ctx.message.server
        if self.is_playing(server):
            if ctx.message.author.voice_channel == server.me.voice_channel:
                if self.can_instaskip(ctx.message.author):
                    await self.bot.say('Stopping...')
                    self._stop(server)
                else:
                    await self.bot.say("You can't stop music when there are other"
                                       " people in the channel! Vote to skip"
                                       " instead.")
            else:
                await self.bot.say("You need to be in the voice channel to stop the music.")
        else:
            await self.bot.say("Can't stop if I'm not playing.")

    @commands.command(name="yt", pass_context=True, no_pm=True)
    async def yt_search(self, ctx, *, search_terms: str):
        """Searches and plays a video from YouTube"""
        await self.bot.say("Searching...")
        await ctx.invoke(self.play, url_or_search_terms=search_terms)

    def is_playing(self, server):
        if not self.voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), 'audio_player'):
            return False
        if self.voice_client(server).audio_player.is_done():
            return False
        return True

    async def cache_manager(self):
        while self == self.bot.get_cog("Audio"):
            if self._cache_too_large():
                # Our cache is too big, dumping
                log.debug("cache too large ({} > {}), dumping".format(
                    self._cache_size(), self._cache_max()))
                self._dump_cache()
            await asyncio.sleep(5)  # No need to run this every half second

    async def cache_scheduler(self):
        await asyncio.sleep(30)  # Extra careful

        self.bot.loop.create_task(self.cache_manager())

    def currently_downloading(self, server):
        if server.id in self.downloaders:
            if self.downloaders[server.id].is_alive():
                return True
        return False

    async def disconnect_timer(self):
        stop_times = {}
        while self == self.bot.get_cog('Audio'):
            for vc in self.bot.voice_clients:
                server = vc.server
                if not hasattr(vc, 'audio_player') and \
                        (server not in stop_times or
                         stop_times[server] is None):
                    log.debug("putting sid {} in stop loop, no player".format(
                        server.id))
                    stop_times[server] = int(time.time())

                if hasattr(vc, 'audio_player'):
                    if vc.audio_player.is_done():
                        if server not in stop_times or stop_times[server] is None:
                            log.debug("putting sid {} in stop loop".format(server.id))
                            stop_times[server] = int(time.time())

                    noppl_disconnect = self.get_server_settings(server)
                    noppl_disconnect = noppl_disconnect.get("NOPPL_DISCONNECT", True)
                    if noppl_disconnect and len(vc.channel.voice_members) == 1:
                        if server not in stop_times or stop_times[server] is None:
                            log.debug("putting sid {} in stop loop".format(server.id))
                            stop_times[server] = int(time.time())
                    elif not vc.audio_player.is_done():
                        stop_times[server] = None

            for server in stop_times:
                if stop_times[server] and \
                        int(time.time()) - stop_times[server] > 300:
                    # 5 min not playing to d/c
                    log.debug("dcing from sid {} after 300s".format(server.id))
                    self._clear_queue(server)
                    await self._stop_and_disconnect(server)
                    stop_times[server] = None
            await asyncio.sleep(5)

    def get_server_settings(self, server):
        try:
            sid = server.id
        except:
            sid = server

        if sid not in self.settings["SERVERS"]:
            self.settings["SERVERS"][sid] = {}
        ret = self.settings["SERVERS"][sid]

        # Not the cleanest way. Some refactoring is suggested if more settings
        # have to be added
        if "NOPPL_DISCONNECT" not in ret:
            ret["NOPPL_DISCONNECT"] = True

        for setting in self.server_specific_setting_keys:
            if setting not in ret:
                # Add the default
                ret[setting] = self.settings[setting]
                if setting.lower() == "volume" and ret[setting] <= 1:
                    ret[setting] *= 100
        # ^This will make it so that only users with an outdated config will
        # have their volume set * 100. In theory.
        self.save_settings()

        return ret

    def has_connect_perm(self, author, server):
        channel = author.voice_channel

        if channel:
            is_admin = channel.permissions_for(server.me).administrator
            if channel.user_limit == 0:
                is_full = False
            else:
                is_full = len(channel.voice_members) >= channel.user_limit

        if channel is None:
            raise AuthorNotConnected
        elif channel.permissions_for(server.me).connect is False:
            raise UnauthorizedConnect
        elif channel.permissions_for(server.me).speak is False:
            raise UnauthorizedSpeak
        elif is_full and not is_admin:
            raise ChannelUserLimit
        else:
            return True
        return False

    async def queue_manager(self, sid):
        """This function assumes that there's something in the queue for us to
            play"""
        server = self.bot.get_server(sid)
        max_length = self.settings["MAX_LENGTH"]

        # This is a reference, or should be at least
        temp_queue = self.queue[server.id][QueueKey.TEMP_QUEUE]
        queue = self.queue[server.id][QueueKey.QUEUE]
        repeat = self.queue[server.id][QueueKey.REPEAT]
        last_song = self.queue[server.id][QueueKey.NOW_PLAYING]
        last_song_channel = self.queue[server.id][QueueKey.NOW_PLAYING_CHANNEL]

        assert temp_queue is self.queue[server.id][QueueKey.TEMP_QUEUE]
        assert queue is self.queue[server.id][QueueKey.QUEUE]

        # _play handles creating the voice_client and player for us

        if not self.is_playing(server):
            log.debug("not playing anything on sid {}".format(server.id) +
                      ", attempting to start a new song.")
            self.skip_votes[server.id] = []
            # Reset skip votes for each new song
            if len(temp_queue) > 0:
                # Fake queue for irdumb's temp playlist songs
                log.debug("calling _play because temp_queue is non-empty")
                try:
                    queued_song = temp_queue.popleft()
                    url = queued_song.url
                    channel = queued_song.channel
                    song = await self._play(sid, url, channel)
                except MaximumLength:
                    return
            elif len(queue) > 0:  # We're in the normal queue
                queued_song = queue.popleft()
                url = queued_song.url
                channel = queued_song.channel
                log.debug("calling _play on the normal queue")
                try:
                    song = await self._play(sid, url, channel)
                except MaximumLength:
                    return
                if repeat and last_song:
                    queued_last_song = QueuedSong(last_song.webpage_url, last_song_channel)
                    queue.append(last_song.webpage_url)
            else:
                song = None
            self._set_queue_nowplaying(server, song, channel)
            log.debug("set now_playing for sid {}".format(server.id))
            self.bot.loop.create_task(self._update_bot_status())

        elif server.id in self.downloaders:
            # We're playing but we might be able to download a new song
            curr_dl = self.downloaders.get(server.id)
            if len(temp_queue) > 0:
                queued_next_song = temp_queue.peekleft()
                next_url = queued_next_song.url
                next_channel = queued_next_song.channel
                next_dl = Downloader(next_url, max_length)
            elif len(queue) > 0:
                queued_next_song = queue.peekleft()
                next_url = queued_next_song.url
                next_channel = queued_next_song.channel	
                next_dl = Downloader(next_url, max_length)
            else:
                next_dl = None

            if next_dl is not None:
                try:
                    # Download next song
                    next_dl.start()
                    await self._download_next(server, curr_dl, next_dl)
                except YouTubeDlError as e:
                    if len(temp_queue) > 0:
                        temp_queue.popleft()
                    elif len(queue) > 0:
                        queue.popleft()
                    clean_url = self._clean_url(next_url)
                    message = ("I'm unable to play '{}' because of an "
                              "error:\n'{}'".format(clean_url, str(e)))
                    message = escape(message, mass_mentions=True)
                    await self.bot.send_message(next_channel, message)

    async def queue_scheduler(self):
        while self == self.bot.get_cog('Audio'):
            tasks = []
            queue = copy.deepcopy(self.queue)
            for sid in queue:
                if len(queue[sid][QueueKey.QUEUE]) == 0 and \
                        len(queue[sid][QueueKey.TEMP_QUEUE]) == 0:
                    continue
                # log.debug("scheduler found a non-empty queue"
                #           " for sid: {}".format(sid))
                tasks.append(
                    self.bot.loop.create_task(self.queue_manager(sid)))
            completed = [t.done() for t in tasks]
            while not all(completed):
                completed = [t.done() for t in tasks]
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)

    async def reload_monitor(self):
        while self == self.bot.get_cog('Audio'):
            await asyncio.sleep(0.5)

        for vc in self.bot.voice_clients:
            try:
                vc.audio_player.stop()
            except:
                pass

    def save_settings(self):
        dataIO.save_json('data/audio/settings.json', self.settings)

    def set_server_setting(self, server, key, value):
        if server.id not in self.settings["SERVERS"]:
            self.settings["SERVERS"][server.id] = {}
        self.settings["SERVERS"][server.id][key] = value

    def voice_client(self, server):
        return self.bot.voice_client_in(server)

    def voice_connected(self, server):
        if self.bot.is_voice_connected(server):
            return True
        return False

    async def voice_state_update(self, before, after):
        server = after.server
        # Member objects
        if after.voice_channel != before.voice_channel:
            try:
                self.skip_votes[server.id].remove(after.id)
            except (ValueError, KeyError):
                pass
                # Either the server ID or member ID already isn't in there
        if after is None:
            return
        if server.id not in self.queue:
            return
        if after != server.me:
            return

        # Member is the bot

        if before.voice_channel != after.voice_channel:
            self._set_queue_channel(after.server, after.voice_channel)

        if before.mute != after.mute:
            vc = self.voice_client(server)
            if after.mute and vc.audio_player.is_playing():
                log.debug("Just got muted, pausing")
                vc.audio_player.pause()
            elif not after.mute and \
                    (not vc.audio_player.is_playing() and
                     not vc.audio_player.is_done()):
                log.debug("just got unmuted, resuming")
                vc.audio_player.resume()

    def __unload(self):
        for vc in self.bot.voice_clients:
            self.bot.loop.create_task(vc.disconnect())


def check_folders():
    folders = ("data/audio", "data/audio/cache", "data/audio/playlists",
               "data/audio/localtracks", "data/audio/sfx")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    default = {"VOLUME": 50, "MAX_LENGTH": 3700, "VOTE_ENABLED": True,
               "MAX_CACHE": 0, "SOUNDCLOUD_CLIENT_ID": None,
               "TITLE_STATUS": True, "AVCONV": False, "VOTE_THRESHOLD": 50,
               "SERVERS": {}}
    settings_path = "data/audio/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default audio settings.json...")
        dataIO.save_json(settings_path, default)
    else:  # consistency check
        try:
            current = dataIO.load_json(settings_path)
        except JSONDecodeError:
            # settings.json keeps getting corrupted for unknown reasons. Let's
            # try to keep it from making the cog load fail.
            dataIO.save_json(settings_path, default)
            current = dataIO.load_json(settings_path)
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print(
                        "Adding " + str(key) + " field to audio settings.json")
            dataIO.save_json(settings_path, current)


def verify_ffmpeg_avconv():
    try:
        subprocess.call(["ffmpeg", "-version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    else:
        return "ffmpeg"

    try:
        subprocess.call(["avconv", "-version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        return False
    else:
        return "avconv"


def setup(bot):
    check_folders()
    check_files()

    if youtube_dl is None:
        raise RuntimeError("You need to run `pip3 install youtube_dl`")
    if opus is False:
        raise RuntimeError(
            "Your opus library's bitness must match your python installation's"
            " bitness. They both must be either 32bit or 64bit.")
    elif opus is None:
        raise RuntimeError(
            "You need to install ffmpeg and opus. See \"https://github.com/"
            "Twentysix26/Red-DiscordBot/wiki/Requirements\"")

    player = verify_ffmpeg_avconv()

    if not player:
        if os.name == "nt":
            msg = "ffmpeg isn't installed"
        else:
            msg = "Neither ffmpeg nor avconv are installed"
        raise RuntimeError(
            "{}.\nConsult the guide for your operating system "
            "and do ALL the steps in order.\n"
            "https://twentysix26.github.io/Red-Docs/\n"
            "".format(msg))

    n = Audio(bot, player=player)  # Praise 26
    bot.add_cog(n)
    bot.add_listener(n.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(n.queue_scheduler())
    bot.loop.create_task(n.disconnect_timer())
    bot.loop.create_task(n.reload_monitor())
    bot.loop.create_task(n.cache_scheduler())
