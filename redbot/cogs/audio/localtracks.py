import asyncio
import os
import re
from pathlib import Path, WindowsPath, PurePath, PosixPath
from typing import List, Union
from operator import attrgetter

from redbot.core.data_manager import cog_data_path

from redbot.core.bot import Red

from redbot.core import Config
from redbot.core.i18n import Translator

_config = None
_bot = None

_ = Translator("Audio", __file__)


def _pass_config_to_localtracks(config: Config, bot: Red):
    global _config, _bot
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot


class ChdirClean(object):
    def __init__(self, directory):
        self.old_dir = os.getcwd()
        self.new_dir = directory
        self.cwd = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.chdir_out()
        return isinstance(value, OSError)

    def chdir_in(self):
        self.cwd = Path(self.new_dir)
        os.chdir(self.new_dir)

    def chdir_out(self):
        self.cwd = Path(self.old_dir)
        os.chdir(self.old_dir)


class LocalPath(ChdirClean):
    _supported_music_ext = (".mp3", ".flac", ".ogg")

    def __init__(self, path, localtrack_folder, **kwargs):
        if isinstance(path, str):
            path = path
        elif isinstance(path, LocalPath):
            path = str(path.path.absolute())
        elif isinstance(path, (Path, WindowsPath, PosixPath)):
            path = str(path.absolute())
        else:
            path = str(path)

        self.cwd = Path.cwd()
        if (os.sep + "localtracks") in localtrack_folder:
            self.localtrack_folder = Path(localtrack_folder) if localtrack_folder else self.cwd
        else:
            self.localtrack_folder = (
                Path(localtrack_folder) / "localtracks"
                if localtrack_folder
                else self.cwd / "localtracks"
            )

        try:
            _path = Path(path)
            self.localtrack_folder.relative_to(path)
            _path.relative_to(str(self.localtrack_folder.absolute()))
            self.path = _path
        except (ValueError, TypeError):
            self.path = self.localtrack_folder.joinpath(path) if path else self.localtrack_folder

        if self.path.is_file():
            parent = self.path.parent
        else:
            parent = self.path
        self.parent = parent

        super().__init__(str(self.parent.absolute()))
        self.cwd = Path.cwd()

    @property
    def name(self):
        return str(self.path.name)

    @classmethod
    def joinpath(cls, localtrack_folder, *args):
        modified = cls(None, localtrack_folder)
        modified.path = modified.path.joinpath(*args)
        return modified

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

    def __str__(self):
        return str(self.path.absolute())

    def to_string(self):
        return str(self.path.absolute())

    def to_string_hidden(self, arg: str = None):
        print("\n\n" + str(self.path.absolute()) + "\n" + str(self.localtrack_folder.absolute()))
        return str(self.path.absolute()).replace(
            str(self.localtrack_folder.absolute()) if arg is None else arg, ""
        )

    def tracks_in_tree(self):
        tracks = []
        for track in self.multirglob(*[f"*{ext}" for ext in self._supported_music_ext]):
            if track.is_file():
                tracks.append(
                    AudioTrack.spawn_track(
                        LocalPath(track, str(self.localtrack_folder.absolute())), local=True
                    )
                )
        return tracks

    def subfolders_in_tree(self):
        files = list(self.multirglob(*[f"*{ext}" for ext in self._supported_music_ext]))
        folders = []
        for f in files:
            if f.parent not in folders:
                folders.append(f.parent)
        return_folders = []
        for folder in folders:
            if folder.is_dir():
                return_folders.append(
                    LocalPath(str(folder.absolute()), str(self.localtrack_folder.absolute()))
                )
        return return_folders

    def tracks_in_folder(self):
        tracks = []
        for track in self.multiglob(*[f"*{ext}" for ext in self._supported_music_ext]):
            if track.is_file():
                tracks.append(
                    AudioTrack.spawn_track(
                        LocalPath(track, str(self.localtrack_folder.absolute())), local=True
                    )
                )
        return tracks

    def subfolders(self):
        files = list(self.multiglob(*[f"*{ext}" for ext in self._supported_music_ext]))
        folders = []
        for f in files:
            if f.parent not in folders:
                folders.append(f.parent)
        return_folders = []
        for folder in folders:
            if folder.is_dir():
                return_folders.append(
                    LocalPath(str(folder.absolute()), str(self.localtrack_folder.absolute()))
                )
        return return_folders


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
        returning = {}
        if isinstance(track, LocalPath):
            returning["local"] = True

        return returning

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
