import asyncio
import os
import re
from pathlib import Path
from typing import Generator, List, Optional, Union

from fuzzywuzzy import process

from redbot.core import Config
from redbot.core.i18n import Translator

_config = None
_ = Translator("Audio", __file__)


def _pass_config_to_localtracks(config: Config):
    global _config
    if _config is None:
        _config = config


class ChdirClean(object):
    def __init__(self, directory):
        self.old_dir = os.getcwd()
        self.new_dir = directory

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.chdir_out()
        return isinstance(value, OSError)

    def chdir_in(self):
        os.chdir(self.new_dir)

    def chdir_out(self):
        os.chdir(self.old_dir)


class LocalPath(ChdirClean):
    _supported_music_ext = (".mp3", ".flac", ".ogg")

    def __init__(self, path, **kwargs):
        try:
            local_path = asyncio.get_event_loop().run_until_complete(_config.localpath())
        except Exception:
            local_path = None

        self.local_track_path = Path(local_path) if local_path else None
        self.path = Path(path)
        if self.path.is_file():
            parent = self.path.parent
        else:
            parent = self.path
        self.parent = parent
        super().__init__(str(self.parent))

    def multiglob(self, *patterns):
        paths = []
        for p in patterns:
            paths.extend(list(self.path.glob(p)))
        for p in self._filtered(paths):
            yield p

    def multirglob(self, *patterns):
        paths = []
        for p in patterns:
            paths.extend(list(self.path.rglob(p)))

        for p in self._filtered(paths):
            yield p

    def _filtered(self, paths: List[Path]):
        for p in paths:
            if p.suffix in self._supported_music_ext:
                yield p

    def to_string(self):
        return str(self.path.absolute())

    def to_string_hidden(self, arg: str = None):
        return str(self.path.absolute()).replace(
            str(self.local_track_path.absolute()) if arg is None else arg, ""
        )

    def tracks_in_tree(self):
        for track in self.multirglob(*[f"*{ext}" for ext in self._supported_music_ext]):
            if track.is_file():
                yield AudioTrack.spawn_track(track, local=True)

    def subfolders_in_tree(self):
        files = list(self.multirglob(*[f"*{ext}" for ext in self._supported_music_ext]))
        folders = []
        for f in files:
            if f.parent not in folders:
                folders.append(f.parent)

        for folder in folders:
            if folder.is_dir():
                yield LocalPath(folder)

    def tracks_in_folder(self):
        for track in self.multiglob(*[f"*{ext}" for ext in self._supported_music_ext]):
            if track.is_file():
                yield AudioTrack.spawn_track(track, local=True)

    def subfolders(self):
        files = list(self.multiglob(*[f"*{ext}" for ext in self._supported_music_ext]))
        folders = []
        for f in files:
            if f.parent not in folders:
                folders.append(f.parent)

        for folder in folders:
            if folder.is_dir():
                yield LocalPath(folder)


class AudioTrack:
    def __init__(self, track: Union[LocalPath, str], **kwargs):
        self.track = track
        self.is_local = kwargs.get("local", False)
        self.is_spotify = kwargs.get("spotify", False)
        self.is_youtube = kwargs.get("youtube", False)
        self.is_soundcloud = kwargs.get("soundcloud", False)
        self.single_track = kwargs.get("single", False)
        self.is_playlist = kwargs.get("playlist", False)
        self.is_album = kwargs.get("album", False)
        self.query = self.get_query()

    @classmethod
    def spawn_track(cls, track, **kwargs):
        possible_values = dict(local=False, spotify=False, youtube=False, soundcloud=False)
        possible_values.update(kwargs)
        possible_values.update(cls.calculate_logic(track))
        return cls(track, **possible_values)

    @staticmethod
    def calculate_logic(track):
        return dict()

    def get_query(self):
        if self.is_local:
            self.single_track = True
            return self.track.to_string()
        elif self.is_spotify:
            if "/playlist/" in self.track:
                self.is_playlist = True
            elif "/album/" in self.track:
                self.is_album = True
            elif "/track/" in self.track:
                self.single_track = True
            val = re.sub(r"(http[s]?://)?(open.spotify.com)/", "", self.track).replace("/", ":")
            return f"spotify:{val}"
        elif self.is_youtube:
            if "playlist?" in self.track:
                self.is_playlist = True
            else:
                self.single_track = True
            return f"ytsearch:{self.track}"


async def _localtracks_check(self, ctx):
    audio_data = LocalPath(await _config.localpath())
    if not audio_data.path.is_dir():
        if ctx.invoked_with == "start":
            return False
        else:
            await self._embed_msg(ctx, _("No localtracks folder."))
            return False
    else:
        return True


async def _localtracks_folders(self, ctx, show_all=False):
    if not await self._localtracks_check(ctx):
        return
    audio_data = LocalPath(await _config.localpath())
    return audio_data.subfolders_in_tree() if show_all else audio_data.subfolders()


async def _folder_list(self, ctx, folder, show_all=False):
    if not await self._localtracks_check(ctx):
        return
    folder = LocalPath(folder)
    if not folder.path.is_dir():
        return
    return folder.tracks_in_tree() if show_all else folder.tracks_in_folder()


async def _folder_tracks(self, ctx, player, folder, show_all=False):
    if not await self._localtracks_check(ctx):
        return
    folder = LocalPath(folder)
    audio_data = LocalPath(await _config.localpath())
    try:
        folder.path.relative_to(audio_data.to_string())
    except ValueError:
        return
    local_tracks = []
    for local_file in await self._all_folder_tracks(ctx, folder, show_all):
        trackdata = await player.load_tracks(local_file.track.to_string())
        try:
            local_tracks.append(trackdata.tracks[0])
        except IndexError:
            pass
    return local_tracks


async def _local_play_all(self, ctx, folder, show_all=False):
    if not await self._localtracks_check(ctx):
        return
    await ctx.invoke(self.search, query=("folder:" + folder), show_all=show_all)


async def _all_folder_tracks(self, ctx, folder, show_all=False) -> Optional[Generator[AudioTrack]]:
    if not await self._localtracks_check(ctx):
        return
    folder = LocalPath(folder)
    return folder.tracks_in_tree() if show_all else folder.tracks_in_folder()


async def _build_local_search_list(to_search, search_words):
    search_results = process.extract(search_words, to_search, limit=50)
    search_list = []
    for track_match, percent_match in search_results:
        if percent_match > 75:
            search_list.append(track_match)
    return search_list
