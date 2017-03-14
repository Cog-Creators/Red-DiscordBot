import discord
from discord.ext import commands

from concurrent.futures import ThreadPoolExecutor
import os
import functools
import asyncio
import urllib
import logging

try:
    import youtube_dl

    # I'm trusting borkedit on this one
    youtube_dl.utils.bug_reports_message = lambda: ''
    ytdl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(id)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'
    }
except NameError:
    youtube_dl = False
    ytdl_opts = {}

log = logging.getLogger("red.audio")

"""
Audio Rewrite 2.0

Philosophy:
    - Split up the god class (Audio) we currently have
    - Get the vast majority of the functionality (other than actual Discord
        commands) out of the Audio class.
    - All bot events dispatched by this cog should begin with `red_audio_*`
    - Audio commands should handle their own exceptions instead of relying
        on the client `on_command_error`
    - All current audio features need to be implemented/improved.
    - Check https://github.com/Cog-Creators/Audio/projects/1 for extra/new
        features to be implemented.
    - Last of all, always remember, _fuck_ Audio.

    - All permissions checks need to be done in `Audio` class, don't be stupid
        like me and want to pass around the audio instance.
    - My queue logic is still a little weird so I'm going to attempt to make it
        easier to understand here. When a song is queued, the string or url
        that the user provides should automatically get dumped into a `Song`
        object which is THEN put into the queue. Then the downloader inside the
        queue instance goes through each object and grabs actual data from YT
        or wherever and REPLACES the song object in the queue using the new one
        it creates with the data from the website.
"""


class AudioException(Exception):
    """
    Base class for all audio errors.
    """
    pass


class NoPermissions(AudioException):
    """
    Thrown when a user lacks permissions to execute a command.
    """
    pass


class AudioSettings:
    def __init__(self, *, default_folder="data/audio",
                 default_name="settings2_0.json"):
        self._path = os.path.join(default_folder, default_name)


class Song:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.title = kwargs.get("title", "")
        self.duration = kwargs.get("duration", 0)

        self.downloaded = kwargs.get("downloaded", False)

        self.webpage_url = kwargs.get("webpage_url", "")

        self.meta_file = kwargs.get("meta_file")
        # Only the filename, needs to get joined with download_folder to create
        #   the actual accessible path

        self.local = False

        self.extra_data = kwargs

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return False

    @classmethod
    def from_ytdl(cls, **extracted_info):
        # TODO: Write metadata to file here
        meta_file = youtube_dl.compat.compat_expanduser(ytdl_opts["outtmpl"])
        meta_file += ".meta"
        return cls(meta_file=meta_file, **extracted_info)

    def to_json(self):
        return self.extra_data

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class LocalSong(Song):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.local = True


class Playlist(Song):
    def __init__(self, *, song_list=[], **kwargs):
        super().__init__(song_list=song_list, **kwargs)

        self.extractor_key = kwargs.get("extractor_key", "generic")

        self.song_list = song_list

    @staticmethod
    def repair_youtube_url(video_id):
        return "https://youtube.com/watch?v={}".format(video_id)

    @classmethod
    def from_ytdl(cls, **extracted_info):
        song_list = []
        for entry in extracted_info.get("entries", []):
            # For whatever stupid reason the urls in the youtube playlist json
            #   are just video id's, we may need to modify this for other
            #   websites as well.
            if entry.get("ie_key", "") == "Youtube":
                song_url = cls.repair_youtube_url(entry.get("url", ""))
            else:
                song_url = entry.get("url", "")
            song_list.append(song_url)

        try:
            del extracted_info["entries"]
            # I don't want this stored with the Playlist object, serves no
            #   purpose and will just take up filespace.
        except KeyError:
            pass
        return cls(song_list=song_list, **extracted_info)


class ChecksMixin:
    def __init__(self, *, play_checks=[], skip_checks=[], queue_checks=[],
                 connect_checks=[], **kwargs):
        self._checks_to_play = play_checks
        self._checks_to_skip = skip_checks
        self._checks_to_queue = queue_checks
        self._checks_to_connect = connect_checks

    def can_play(self, user):
        for f in self._checks_to_play:
            try:
                res = f(user)
            except Exception:
                log.exception("Error in play check '{}'".format(f.__name__))
            else:
                if res is False:
                    return False
        return True

    def add_play_check(self, f):
        self._checks_to_play.append(f)

    def remove_play_check(self, f):
        try:
            self._checks_to_play.remove(f)
        except ValueError:
            # Thrown when function doesn't exist in list
            pass

    def can_skip(self, user):
        for f in self._checks_to_skip:
            try:
                res = f(user)
            except Exception:
                log.exception("Error in skip check '{}'".format(f.__name__))
            else:
                if res is False:
                    return False
        return True

    def add_skip_check(self, f):
        self._checks_to_skip.append(f)

    def remove_skip_check(self, f):
        try:
            self._checks_to_skip.remove(f)
        except ValueError:
            # Thrown when function doesn't exist in list
            pass

    def can_queue(self, user):
        for f in self._checks_to_queue:
            try:
                res = f(user)
            except Exception:
                log.exception("Error in queue check '{}'".format(f.__name__))
            else:
                if res is False:
                    return False
        return True

    def add_queue_check(self, f):
        self._checks_to_queue.append(f)

    def remove_queue_check(self, f):
        try:
            self._checks_to_queue.remove(f)
        except ValueError:
            # Thrown when function doesn't exist in list
            pass

    def can_connect(self, user):
        for f in self._checks_to_connect:
            try:
                res = f(user)
            except Exception:
                log.exception("Error in connect check '{}'".format(f.__name__))
            else:
                if res is False:
                    return False
        return True

    def add_connect_check(self, f):
        self._checks_to_connect.append(f)

    def remove_connect_check(self, f):
        try:
            self._checks_to_connect.remove(f)
        except ValueError:
            # Thrown when function doesn't exist in list
            pass


class MusicPlayerCommandsMixin:
    def skip(self):
        raise NotImplementedError()

    def pause(self):
        raise NotImplementedError()

    def play(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def queue(self):
        raise NotImplementedError()


class AudioCommandErrorHandlersMixin:
    async def no_permissions(self, error, ctx):
        log.error("No permissions", exc_info=error)
        channel = ctx.message.channel
        # Say may turn out to be unreliable, do this instead
        await ctx.bot.send_message(channel,
                                   "You don't have permission to do that.")


class Downloader:
    """
    I'm gonna take a minute here and thank imayhaveborkedit for the majority of
        this downloader code. There's not a lot of good ways to do this and
        he's done a damn good job with it.

        Original code can be found here:
            https://github.com/Just-Some-Bots/MusicBot/blob/master/
            musicbot/downloader.py
    """

    def __init__(self, loop, download_folder="data/audio/cache",
                 max_workers=2):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.unsafe_ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        self.safe_ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        self.safe_ytdl.params['ignoreerrors'] = True
        self.download_folder = download_folder

        self.loop = loop

        if download_folder:
            otmpl = self.unsafe_ytdl.params['outtmpl']
            self.unsafe_ytdl.params['outtmpl'] = \
                os.path.join(download_folder, otmpl)

            otmpl = self.safe_ytdl.params['outtmpl']
            self.safe_ytdl.params['outtmpl'] =  \
                os.path.join(download_folder, otmpl)

    @property
    def ytdl(self):
        return self.safe_ytdl

    async def extract_info(self, url, on_error=None,
                           retry_on_error=False, download=False,
                           process=False, **kwargs):
        """
            Runs ytdl.extract_info within the threadpool. Returns a future
                that will fire when it's done. If `on_error` is passed and an
                exception is raised, the exception will be caught and passed to
                on_error as an argument.

            This should be called with `url` as a positional argument. Set the
                kwargs as necessary

            The kwarg `process` does a fuck ton of extra (I think unnecessary)
                url resolving so probably don't use it.

            The kwarg `download` determines if youtube_dl will download the
                video file (! or playlist !) at the provided link.

            A kwarg `extra_info` (dict) can be passed to this function and will
                be added to the returned result.
        """

        log.debug("{} {}".format(download, process))

        if callable(on_error):
            try:
                return await self.loop.run_in_executor(
                    self.thread_pool,
                    functools.partial(
                        self.unsafe_ytdl.extract_info, url,
                        download=download, process=process, **kwargs)
                )

            except Exception as e:
                # (youtube_dl.utils.ExtractorError
                # youtube_dl.utils.DownloadError)
                # I hope I don't have to deal with ContentTooShortError's
                if asyncio.iscoroutinefunction(on_error):
                    asyncio.ensure_future(on_error(e), loop=self.loop)

                elif asyncio.iscoroutine(on_error):
                    asyncio.ensure_future(on_error, loop=self.loop)

                else:
                    self.loop.call_soon_threadsafe(on_error, e)

                if retry_on_error:
                    return await self.safe_extract_info(url,
                                                        download=download,
                                                        process=process,
                                                        **kwargs)
        else:
            log.debug("running unsafe ytdl output: {}".format(
                self.unsafe_ytdl.params["outtmpl"]))
            return await self.loop.run_in_executor(
                self.thread_pool,
                functools.partial(self.unsafe_ytdl.extract_info,
                                  url, download=download,
                                  process=process, **kwargs)
            )

    async def safe_extract_info(self, url, download=False,
                                process=False, **kwargs):
        return await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.safe_ytdl.extract_info, url,
                              download=download, process=process, **kwargs)
        )


class MusicCache:
    def __init__(self, loop):
        self.downloader = Downloader(loop, max_workers=4)
        self._id_url_map = {}

    async def is_downloaded(self, obj):
        _id = obj.id
        if _id == "":
            _id = self._id_url_map.get(obj.webpage_url, None)
            if _id is None:
                obj = await self.get_info(obj.webpage_url)
                _id = obj.id if obj.id != "" else None
                self._id_url_map[obj.webpage_url] = _id
        audio_file = os.path.join(self.downloader.download_folder, _id)
        log.debug("{}".format(audio_file))
        return obj, os.path.exists(audio_file)

    async def get_raw_info(self, url, *, download=False, process=False,
                           ctx=None):
        """
        Does not create song/playlist object and does not save metadata.
        """

        is_url = urllib.parse.urlparse(url).scheme != ""
        if not is_url:
            url = "ytsearch1:{}".format(url)  # Thanks Mash

        if ctx is not None:
            extra_info = {
                "author": ctx.message.author.id,
                "channel": ctx.message.channel.id,
                "downloaded": download
            }
        else:
            extra_info = {
                "downloaded": download
            }
        if download is True:
            log.debug("Downloading url: {}".format(url))
            process = True
        return await self.downloader.extract_info(url, download=download,
                                                  process=process,
                                                  extra_info=extra_info)

    async def get_info(self, url, *, download=False, ctx=None):
        raw_info = await self.get_raw_info(url, download=download, ctx=ctx)

        if raw_info.get("_type", "video").lower() == "playlist":
            ret = Playlist.from_ytdl(**raw_info)
        else:
            ret = Song.from_ytdl(**raw_info)

        self._id_url_map[raw_info.get("webpage_url", url)] = raw_info.get(
            "id", "NOTFOUND")
        return ret

    async def get_filename(self, obj, *, ctx=None):
        if not (await self.is_downloaded(obj)):
            log.debug("Song {} not downloaded.".format(obj.webpage_url))
            obj = await self.get_info(obj.webpage_url, download=True, ctx=ctx)
        filename = os.path.join(self.downloader.download_folder,
                                obj.id)
        return filename

    async def get_meta_data(self, *, url=None, obj=None):
        if obj is not None:
            # TODO: open the file
            return os.path.join(self.downloader.download_folder, obj.meta_file)
        elif url is not None:
            return await self.get_raw_info(url)
        else:
            raise ValueError("You must provide either the object or the URL"
                             " to access metadata.")

    async def guarantee_downloaded(self, obj, *, ctx=None):
        log.debug("Attempting to guarantee downlaod for {}".format(obj.id))
        if obj.downloaded is False:
            return await self.get_info(obj.webpage_url, download=True, ctx=ctx)
        else:
            return obj


music_cache = None  # Is set in setup


class MusicQueue:
    def __init__(self, bot, player, songs=[], temp_songs=[], start_index=0):
        self.bot = bot
        self.player = player
        self._songs = songs
        self._temp_songs = temp_songs

        self._current_index = start_index

        self._downloads = {}  # Song/Playlist ID : Future

        self.current_song = None

        self.advance_downloads = 1
        self.download_loop = discord.compat.create_task(
            self.download_watcher(),
            loop=bot.loop)

        self.bot.add_listener(self.on_song_end, "on_red_audio_song_end")

        # TODO: Add functions for adding to queue

    async def on_song_end(self, last_song):
        # self.next()
        self.current_song = self.next_song
        log.debug("Some song just ended: {} now starting {}".format(
            last_song, self.current_song))
        self.bot.dispatch("red_audio_song_change", self.current_song)

    @property
    def next_song(self):
        try:
            return self._temp_songs[0]
        except IndexError:
            try:
                return self._songs[self._current_index]
            except IndexError:
                return None  # Empty queue

    @property
    def next_song_ready(self):
        """
        Used to determine if the `current_song` has been updated in queue and
            ready to be played.
        """
        return self.current_song is not None and \
            self.current_song.id in self._downloads and \
            self._downloads.get(self.current_song.id, True) is None

    def queue(self, num=1):
        """
        Does not include the current song.
        """
        songs = self._temp_songs + self._songs
        try:
            songs.remove(self.current_song)
        except ValueError:
            pass

        return songs[:num]

    @property
    def is_playing_tempsong(self):
        try:
            return self.current_song in self._temp_songs
        except IndexError:
            return False

    def check_start_song(self):
        if self.player.is_playing is False:
            log.debug("Not currently playing but something was just added to"
                      " the queue, starting play sequence.")
            self.bot.dispatch("red_audio_song_end", None)

    def add_to_queue(self, obj, position=None):
        """
        If position is `None` the song(s) will be put at the end of the queue.
        """
        if position is None:
            position = len(self._songs)

        try:
            for s in obj.song_list:
                self._songs.insert(position, s)
        except AttributeError:
            self._songs.insert(position, obj)

        self.check_start_song()

    def add_to_tempqueue(self, obj, position=None):
        """
        If position is `None` the song(s) will be put at the end of the
            temp queue.
        """
        if position is None:
            position = len(self._songs)

        try:
            for s in obj.song_list:
                self._temp_songs.insert(position, s)
        except AttributeError:
            self._temp_songs.insert(position, obj)

        self.check_start_song()

    def clear(self, songs=True, temp_songs=True):
        if songs is True:
            self._songs = []

        if temp_songs is True:
            self._temp_songs = []

    def skip(self, num=1):
        if num >= len(self._temp_songs):
            num -= len(self._temp_songs)
            self._temp_songs = []
            self._current_index = (self._current_index + num) % \
                len(self._songs)
        else:
            self._temp_songs = self._temp_songs[num:]

        self.bot.dispatch("red_audio_song_end", self.current_song)

    def next(self):
        return self.skip()

    def update_queue(self, position, new_object):
        try:
            self._temp_songs[position] = new_object
        except IndexError:
            position -= len(self._temp_songs)

        try:
            self._songs[position] = new_object
        except IndexError:
            log.warning("Tried to update a nonexistant queue position. Please"
                        " report this error!")
        else:
            log.debug("Updated position {} in queue".format(position))

        if self.current_song == new_object:
            self.current_song = new_object

    async def update_downloaders(self):
        songs = [s for s in [self.current_song, ] +
                 self.queue(self.advance_downloads) if s is not None]
        for i, s in enumerate(songs):
            if s.id not in self._downloads:
                d = self.bot.loop.create_task(
                    music_cache.guarantee_downloaded(s))
                self._downloads[s.id] = d
            elif self._downloads[s.id] is None:
                continue
            elif self._downloads[s.id].done():
                log.debug("downloader {} done".format(s.id))
                try:
                    info = self._downloads[s.id].result()
                except asyncio.CancelledError:
                    del self._downloads[s.id]
                else:
                    self.update_queue(i, info)
                    self._downloads[s.id] = None

        await asyncio.sleep(0.1)

        to_kill = []
        for id in self._downloads:
            if id not in [s.id for s in songs]:
                to_kill.append(id)

        for id in to_kill:
            try:
                self._downloads[id].cancel()
                log.debug("Cancelled downloader {}".format(id))
            except AttributeError:
                pass  # This will happen because we change it to None
            del self._downloads[id]

    async def download_watcher(self):
        while True:
            try:
                await self.update_downloaders()
            except:
                log.exception("Uncaught exception in MusicQueue"
                              " download_watcher.")
            await asyncio.sleep(0.5)


class MusicPlayer(MusicPlayerCommandsMixin):
    def __init__(self, bot, voice_member):
        super().__init__()
        self.bot = bot
        self._starting_member = voice_member

        self._voice_channel = voice_member.voice_channel
        self._voice_client = None
        self._server = voice_member.server

        self._dpy_player = None

        self._song_changer = None

        self.stream_mode = False

        self.ffmpeg_args = {}

        self.current_song = None

        self.bot.add_listener(self.on_red_audio_unload,
                              "on_red_audio_unload")

        self.bot.add_listener(self.on_song_change, "on_red_audio_song_change")

        self._queue = MusicQueue(bot, self)

    def __eq__(self, other):
        return self.server == other.server

    async def on_red_audio_unload(self):
        # self._play_loop.cancel()
        if self.is_connected:
            await self.disconnect()

    @property
    def is_connected(self):
        try:
            return self.bot.is_voice_connected(self._voice_channel.server)
        except AttributeError:
            # self._voice_channel is None
            return False

    @property
    def is_playing(self):
        return self.is_connected and self.dpy_player_active and \
            self._dpy_player.is_playing()

    @property
    def dpy_player_active(self):
        return self._dpy_player is not None

    async def connect(self):
        if not self.is_connected:
            connect_fut = self.bot.join_voice_channel(self._voice_channel)
            try:
                await asyncio.wait_for(connect_fut, 10, loop=self.bot.loop)
            except asyncio.TimeoutError as exc:
                log.error("Timed out connecting", exc_info=exc)
        self._voice_client = self.bot.voice_client_in(
            self._voice_channel.server)

    async def disconnect(self):
        await self._voice_client.disconnect()

    # MusicPlayerCommandsMixin

    def pause(self):
        try:
            self._dpy_player.pause()
        except AttributeError:
            pass  # Meaning we don't have a dpy player

    async def play(self, str_or_url, *, temp=False, clear=False):
        if clear is True:
            self._queue.clear()

        obj, _ = await music_cache.is_downloaded(Song(webpage_url=str_or_url))

        if temp is True:
            self._queue._temp_songs.append(obj)
        else:
            self._queue.add_to_queue(obj)

    # End mixin

    async def create_dpy_player(self, song):
        log.debug("Starting dpy player creation")
        try:
            if self._voice_client is None:
                await self.connect()
        except asyncio.TimeoutError:
            log.debug("Timed out, not creating dpy player.")
        except:
            log.exception("Something happened (not a timeout error)"
                          ", not creating dpy player")

        ffmpeg_args = ["-{} {}".format(k, v) for k, v in self.ffmpeg_args]
        ffmpeg_args = " ".join(ffmpeg_args)

        song_file = await music_cache.get_filename(song)

        if song.local is True:
            pass  # For now, might not need this
        else:
            self._dpy_player = self._voice_client.create_ffmpeg_player(
                song_file, options=ffmpeg_args,
                after=functools.partial(self.bot.dispatch,
                                        "red_audio_song_end"))

        self._dpy_player.start()

    async def change_song(self, song):
        if song != self._queue.current_song:
            # This should never happen
            log.warning("Requested song doesn't match the current song from"
                        " queue! Please report this error as it should never"
                        " happen.")
            self._queue.add_to_tempqueue(song, 0)
            self._queue.current_song = song

        # TODO: Kill current dpy player
        # TODO: Guarantee downloaded new current
        # TODO: Guarantee downloaded next N songs
        log.debug("Waiting on song to download.")
        while self._queue.current_song.downloaded is False:
            await asyncio.sleep(0.1)

        self.current_song = self._queue.current_song
        await self.create_dpy_player(self.current_song)

    async def on_song_change(self, song):
        try:
            self._song_changer.cancel()
        except (AttributeError, asyncio.CancelledError):
            pass
        self._song_changer = discord.compat.create_task(
            self.change_song(song), loop=self.bot.loop)
        log.debug("created song changer future")

    """
    async def play_loop(self):
        while True:
            try:
                await self.update_stuff()
            except Exception:
                log.exception("Exception in audio play loop")
            finally:
                await asyncio.sleep(1)
    """


class PlayerManager:
    def __init__(self):
        self._music_players = []

    def player(self, ctx):
        server = ctx.message.server
        if self.has_player(server):
            return discord.utils.get(self._music_players, _server=server)
        else:
            raise AudioException("No player for server {}".format(server.id))

    def has_player(self, server):
        return any(mp._server == server for mp in self._music_players)

    def is_connected(self, ctx):
        server = ctx.message.server
        return self.has_player(server) and self.player(ctx).is_connected

    async def create_player(self, ctx):
        member = ctx.message.author

        mp = MusicPlayer(ctx.bot, member)
        self._music_players.append(mp)

        await mp.connect()

    async def guarantee_connected(self, ctx):
        server = ctx.message.server
        if not self.has_player(server):
            await self.create_player(ctx)

    async def disconnect(self, ctx):
        try:
            await self.player(ctx).disconnect()
            self._music_players.remove(self.player(ctx))
        except AudioException:
            pass  # No player to remove


class Audio(ChecksMixin, AudioCommandErrorHandlersMixin):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

        self.settings = AudioSettings()

        self._mp_manager = PlayerManager()

    def __unload(self):
        # Dispatching this so everything can do it's own unload stuff,
        #   might not need it.
        self.bot.dispatch("red_audio_unload")

    def player(self, ctx):
        """
        A convenience function.
        """
        return self._mp_manager.player(ctx)

    async def guarantee_connected(self, ctx):
        if not self._mp_manager.is_connected(ctx):
            if self.can_connect(ctx.message.author):
                await self._mp_manager.guarantee_connected(ctx)
            else:
                raise NoPermissions("Not allowed to connect.")

    @commands.command(pass_context=True, hidden=True)
    async def disconnect(self, ctx):
        """
        This is a DEBUG FUNCTION.

        This means that you don't use it.
        """

        if ctx.message.author.id != "111655405708455936":
            # :P
            return

        await self._mp_manager.disconnect(ctx)

    @commands.command(pass_context=True, hidden=True)
    async def joinvoice(self, ctx):
        """
        This is a DEBUG FUNCTION.

        This means that you don't use it.
        """

        if ctx.message.author.id != "111655405708455936":
            # :P
            return

        await self._mp_manager.guarantee_connected(ctx)

    @commands.command(pass_context=True)
    async def play(self, ctx, str_or_url):
        await self.guarantee_connected(ctx)

        if self.can_play(ctx.message.author):
            await self.player(ctx).play(str_or_url, clear=True)
        else:
            return  # TODO: say something or raise something

        await ctx.bot.say("Done.")

    @play.error
    # @joinvoice.error  # I think we're allowed to stack these
    # @disconnect.error
    async def _play_error(self, error, ctx):
        if isinstance(error, NoPermissions):
            await self.no_permissions(error, ctx)


def import_checks():
    if youtube_dl is False:
        raise AudioException("You must install `youtube_dl` to use Audio.")


def setup(bot):
    try:
        import_checks()
    except AudioException:
        log.exception()
    else:
        global music_cache
        music_cache = MusicCache(bot.loop)
        bot.add_cog(Audio(bot))
