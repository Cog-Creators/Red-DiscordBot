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
except NameError:
    youtube_dl = False

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
        self.name = kwargs.get("name", "")
        self.duration = kwargs.get("duration", 0)

    @classmethod
    def from_ytdl(cls, **kwargs):
        raise NotImplemented

    @classmethod
    def from_file(cls, *args):
        raise NotImplemented


class Playlist:
    pass


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
    ytdl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(id)s-%(title)s.%(ext)s',
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

    def __init__(self, url):
        self._url = url

        self._thread_pool = ThreadPoolExecutor(max_workers=2)


class MusicQueue:
    def __init__(self, songs=[], temp_songs=[], start_index=0):
        self._songs = songs
        self._temp_songs = temp_songs

        self._current_index = start_index

    @property
    def current_song(self):
        try:
            return self._temp_songs[0]
        except IndexError:
            return self._songs[self._current_index]

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


class MusicPlayer(MusicPlayerCommandsMixin):
    def __init__(self, bot, voice_member):
        super().__init__()
        self.bot = bot
        self._starting_member = voice_member

        self._voice_channel = voice_member.voice_channel
        self._voice_client = None
        self._server = voice_member.server

        self._current_song_done = asyncio.Event(loop=bot.loop)

        self._queue = MusicQueue()

        self._dpy_player = None

        self._play_loop = discord.compat.create_task(self.play_loop(),
                                                     loop=bot.loop)

        self.bot.add_listener(self.on_red_audio_unload,
                              "on_red_audio_unload")

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

    async def update_stuff(self):
        self._current_song_done.clear()

    async def play_loop(self):
        while True:
            try:
                if not self.dpy_player_active or \
                        self._current_song_done.is_set():
                    await self.update_stuff()
            except Exception as e:
                log.error("Exception in audio play loop", exc_info=e)
            finally:
                await asyncio.sleep(1)


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
