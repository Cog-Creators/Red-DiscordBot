from discord.ext import commands

from concurrent.futures import ThreadPoolExecutor
import os
import logging

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
"""


class AudioException(Exception):
    """
    Base class for all audio errors.
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
    def __init__(self, *, play_checks=[], skip_checks=[], queue_checks=[]):
        self._checks_to_play = play_checks
        self._checks_to_skip = skip_checks
        self._checks_to_queue = queue_checks

    def can_play(self, user):
        for f in self._checks_to_play:
            try:
                res = f(user)
            except Exception:
                log.exception("Error in play check '{}'".format(f.__name__))
            else:
                return res

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
                return res

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
                return res

    def add_queue_check(self, f):
        self._checks_to_queue.append(f)

    def remove_queue_check(self, f):
        try:
            self._checks_to_queue.remove(f)
        except ValueError:
            # Thrown when function doesn't exist in list
            pass


class Downloader:
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

    def skip(self, num=1):
        if num >= len(self._temp_songs):
            num -= len(self._temp_songs)
            self._temp_songs = []
            self._songs = self._songs[num:]
        else:
            self._temp_songs = self._temp_songs[num:]

        return self.current_song


class MusicPlayer:
    def __init__(self, audio, voice_member):
        self._audio_instance = audio
        self._starting_member = voice_member

        self._voice_channel = voice_member.voice_channel

        self._thread_pool = ThreadPoolExecutor(max_workers=5)
        # Gonna use this for voice channel connections

    def __unload(self):
        raise NotImplemented

    @property
    def is_connected(self):
        try:
            return self._audio_instance.bot.is_voice_connected(
                self._voice_channel.server)
        except AttributeError:
            # self._voice_channel is None
            return False


class Audio(ChecksMixin):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

        self._music_players = []

    def __unload(self):
        # Dispatching this so everything can do it's own unload stuff,
        #   might not need it.
        self.bot.dispatch("on_red_audio_unload")
        for mp in self._music_players:
            mp.__unload()

    @commands.command(pass_context=True)
    async def play(self, ctx, str_or_url):
        raise NotImplemented


def setup(bot):
    bot.add_cog(bot)
