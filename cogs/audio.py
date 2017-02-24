import discord
from discord.ext import commands

from concurrent.futures import ThreadPoolExecutor
import os
import functools
import asyncio
import urllib  # urllib.parse.urlparse(url).scheme != ""
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

        self.webpage_url = kwargs.get("webpage_url", "")

        self.meta_file = kwargs.get("meta_file")
        # Only the filename, needs to get joined with download_folder to create
        #   the actual accessible path

        self.extra_data = kwargs

    def __eq__(self, other):
        return self.id == other.id

    @classmethod
    def from_ytdl(cls, extracted_info: dict):
        # TODO: Write metadata to file here
        meta_file = youtube_dl.compat.compat_expanduser(ytdl_opts["outtmpl"])
        meta_file += ".meta"
        return cls(meta_file=meta_file, **extracted_info)

    def to_json(self):
        return self.extra_data

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class Playlist(Song):
    def __init__(self, *, song_list=[], **kwargs):
        super().__init__(song_list=song_list, **kwargs)

        self.extractor_key = kwargs.get("extractor_key", "generic")

        self.song_list = song_list

    @staticmethod
    def repair_youtube_url(video_id):
        return "https://youtube.com/watch?v={}".format(video_id)

    @classmethod
    def from_ytdl(cls, extracted_info: dict):
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

    def __init__(self, download_folder="data/audio/cache", max_workers=2):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.unsafe_ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        self.safe_ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        self.safe_ytdl.params['ignoreerrors'] = True
        self.download_folder = download_folder

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

    async def extract_info(self, loop, *args, on_error=None,
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
        if callable(on_error):
            try:
                return await loop.run_in_executor(
                    self.thread_pool,
                    functools.partial(
                        self.unsafe_ytdl.extract_info, *args,
                        download=download, process=process, **kwargs)
                )

            except Exception as e:
                # (youtube_dl.utils.ExtractorError
                # youtube_dl.utils.DownloadError)
                # I hope I don't have to deal with ContentTooShortError's
                if asyncio.iscoroutinefunction(on_error):
                    asyncio.ensure_future(on_error(e), loop=loop)

                elif asyncio.iscoroutine(on_error):
                    asyncio.ensure_future(on_error, loop=loop)

                else:
                    loop.call_soon_threadsafe(on_error, e)

                if retry_on_error:
                    return await self.safe_extract_info(loop, *args,
                                                        download=download,
                                                        process=process,
                                                        **kwargs)
        else:
            return await loop.run_in_executor(
                self.thread_pool,
                functools.partial(self.unsafe_ytdl.extract_info,
                                  *args, download=download,
                                  process=process, **kwargs)
            )

    async def safe_extract_info(self, loop, *args, download=False,
                                process=False, **kwargs):
        return await loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.safe_ytdl.extract_info, *args,
                              download=download, process=process, **kwargs)
        )


class MusicCache:
    def __init__(self):
        self.downloader = Downloader(max_workers=4)
        self._id_url_map = {}

    async def is_downloaded(self, url):
        _id = self._id_url_map.get(url, None)
        if _id is None:
            _id = await self.get_raw_info(url).get("id", "NOTFOUND")
        audio_file = os.path.join(self.downloader.download_folder, _id)
        return os.path.exists(audio_file)

    async def get_raw_info(self, url, *, download=False, ctx=None):
        """
        Does not create song/playlist object and does not save metadata.
        """
        if ctx is not None:
            extra_info = {
                "author": ctx.message.author.id,
                "channel": ctx.message.channel.id,
                "downloaded": download
            }
        else:
            extra_info = {}
        return await self.downloader.extract_info(url, download=download,
                                                  extra_info=extra_info)

    async def get_info(self, url, *, download=False, ctx=None):
        raw_info = await self.get_raw_info(url, download=download, ctx=ctx)

        if raw_info.get("_type", "video").lower() == "playlist":
            ret = Playlist.from_ytdl(**raw_info)
        else:
            ret = Song.from_ytdl(**raw_info)

        self._id_url_map[ret.get("webpage_url", url)] = raw_info.get(
            "id", "NOTFOUND")
        return ret

    async def get_filename(self, obj, *, ctx=None):
        if not (await self.is_downloaded(obj.webpage_url)):
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
        if not self.is_downloaded(obj.webpage_url):
            return await self.get_info(obj.webpage_url, download=True, ctx=ctx)
        else:
            return obj


music_cache = MusicCache()


class MusicQueue:
    def __init__(self, bot, songs=[], temp_songs=[], start_index=0):
        self.bot = bot
        self._songs = songs
        self._temp_songs = temp_songs

        self._current_index = start_index

        self._downloads = {}  # Song/Playlist ID : Future

        self.advance_downloads = 1
        self.download_loop = discord.compat.create_task(
            self.download_watcher(),
            loop=bot.loop)

    @property
    def current_song(self):
        try:
            return self._temp_songs[0]
        except IndexError:
            try:
                return self._songs[self._current_index]
            except IndexError:
                return None  # Empty queue

    def queue(self, num=1):
        """
        Does not include the current song.
        """
        songs = []
        try:
            songs = self._temp_songs[1:]
        except IndexError:
            # Means that the only song in temp songs is current song
            songs.extend(self._songs)
        else:
            try:
                songs = self._songs[1:]
            except IndexError:
                songs = []

        return songs[:num]

    @property
    def is_playing_tempsong(self):
        try:
            return self.current_song == self._temp_songs[0]
        except IndexError:
            return False

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
        return self.current_song

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

    async def update_downloaders():
        songs = [s.id for s in
                 [self.current_song, ] + self.queue(self.advance_downloads)]
        for i, s in enumerate(songs):
            if s not in self._downloads:
                d = self.bot.loop.create_task(
                    music_cache.guarantee_downloaded(s))
                self._downloads[s.id] = d
            elif self._downloads[s].done():
                try:
                    info = self._downloads[s].result()
                except CancelledError:
                    del self._downloads[s]
                else:
                    self.update_queue(i, info)

        await asyncio.sleep(0.1)

        to_kill = []
        for s in self._downloads:
            if s not in songs:
                to_kill.append(s)

        for s in to_kill:
            self._downloads[s].cancel()
            del self._downloads[s]

    async def download_watcher(self):
        while True:
            try:
                await self.update_downloaders()
            except Exception:
                log.exception("Uncaught exception in MusicQueue"
                              " download_watcher.")


class MusicPlayer(MusicPlayerCommandsMixin):
    def __init__(self, bot, voice_member):
        super().__init__()
        self.bot = bot
        self._starting_member = voice_member

        self._voice_channel = voice_member.voice_channel
        self._voice_client = None
        self._server = voice_member.server

        self._queue = MusicQueue(bot)

        self._dpy_player = None

        # self._play_loop = discord.compat.create_task(self.play_loop(),
        #                                              loop=bot.loop)

        self.current_song = None

        self.bot.add_listener(self.on_red_audio_unload,
                              "on_red_audio_unload")

        self.bot.add_listener(self.on_song_change, "on_red_audio_song_change")
        self.bot.add_listener(self.on_song_end, "on_red_audio_song_end")

    def __eq__(self, other):
        return self.server == other.server

    async def on_red_audio_unload(self):
        self._play_loop.cancel()
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

    def play(self, str_or_url, *, temp=False, clear=False):
        if clear is True:
            self._queue.clear_queue()

        if temp is True:
            self._queue._temp_songs.append(str_or_url)
        else:
            self._queue._songs.append(str_or_url)

    async def on_song_change(self, song):
        if song != self._queue.current_song:
            # This should never happen
            log.warning("Requested song doesn't match the current song from"
                        " queue! Please report this error as it should never"
                        " happen.")
            self._queue._temp_songs.insert(0, song)

        if self.current_song != self._queue.current_song:
            # TODO: Kill current dpy player
            # TODO: Guarantee downloaded new current
            # TODO: Guarantee downloaded next N songs
            self.current_song = self._queue.current_song

    async def on_song_end(self):
        song = self._queue.next()
        self.bot.dispatch("on_red_audio_song_change", song)

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
        self.bot.dispatch("on_red_audio_unload")

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
            self._mp_manager.player(ctx).play(str_or_url, clear=True)
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
        bot.add_cog(Audio(bot))
