import asyncio
import os
import re
from pathlib import Path, WindowsPath, PosixPath
from typing import List, Union
from urllib.parse import urlparse


from redbot.core.bot import Red

from redbot.core import Config
from redbot.core.i18n import Translator

_config = None
_bot = None
_localtrack_folder = None
_ = Translator("Audio", __file__)


def _pass_config_to_localtracks(config: Config, bot: Red, folder: str):
    global _config, _bot, _localtrack_folder
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot
    _localtrack_folder = folder


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

    def __init__(self, path, **kwargs):

        if isinstance(path, (Path, WindowsPath, PosixPath, LocalPath)):
            path = str(path.absolute())
        elif path is not None:
            path = str(path)

        self.cwd = Path.cwd()
        if (os.sep + "localtracks") in _localtrack_folder:
            self.localtrack_folder = Path(_localtrack_folder) if _localtrack_folder else self.cwd
        else:
            self.localtrack_folder = (
                Path(_localtrack_folder) / "localtracks"
                if _localtrack_folder
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

    def is_dir(self):
        return self.path.is_dir()

    def is_file(self):
        return self.path.is_file()

    def absolute(self):
        return self.path.absolute()

    @property
    def parent(self):
        return LocalPath(self.path.parent)

    @classmethod
    def joinpath(cls, *args):
        modified = cls(None)
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
        return str(self.absolute()).replace(
            str(self.localtrack_folder.absolute()) if arg is None else arg, ""
        )

    def tracks_in_tree(self):
        tracks = []
        for track in self.multirglob(*[f"*{ext}" for ext in self._supported_music_ext]):
            if track.is_file():
                tracks.append(Query.process_input(LocalPath(str(track.absolute()))))
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
                return_folders.append(LocalPath(str(folder.absolute())))
        return return_folders

    def tracks_in_folder(self):
        tracks = []
        for track in self.multiglob(*[f"*{ext}" for ext in self._supported_music_ext]):
            if track.is_file():
                tracks.append(Query.process_input(LocalPath(str(track.absolute()))))
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
                return_folders.append(LocalPath(str(folder.absolute())))
        return return_folders


class Query:
    def __init__(self, query: Union[LocalPath, str], **kwargs)
        self.valid : bool = query != "InvalidQueryPlaceHolderName"
        self.id: Optional[str] = kwargs.get("id", None)
        _localtrack = LocalPath(query)
        self.track: Union[LocalPath, str] = _localtrack if (_localtrack.is_file() or _localtrack.is_dir()) else query
        
        self.is_local: bool = kwargs.get("local", False)
        self.is_spotify: bool  = kwargs.get("spotify", False)
        self.is_youtube: bool  = kwargs.get("youtube", False)
        self.is_soundcloud: bool  = kwargs.get("soundcloud", False)
        self.is_bandcamp: bool  = kwargs.get("bandcamp", False)
        self.is_vimeo: bool  = kwargs.get("vimeo", False)
        self.is_mixer: bool  = kwargs.get("mixer", False)
        self.is_twitch: bool  = kwargs.get("twitch", False)
        self.is_other: bool  = kwargs.get("other", False)
        self.is_playlist: bool  = kwargs.get("playlist", False)
        self.is_album: bool  = kwargs.get("album", False)
        self.is_search: bool  = kwargs.get("search", False)
        self.is_stream: bool = kwargs.get("stream", False)

        self.single_track: bool  = kwargs.get("single", False)

        self.start_time: int = kwargs.get("start_time", 0)
        self.local_name: Optional[str] = kwargs.get("name", None)

        self.lavalink_query: str = self.get_query()

        if self.is_playlist or self.is_album:
            self.single_track = False

    def __str__(self):
        return str(self.lavalink_query)

    @classmethod
    def process_input(cls, query, **kwargs):
        if not query:
            query = "InvalidQueryPlaceHolderName"
        if isinstance(query, str):
            query = query.strip("<>")
        elif isinstance(query, Query): #TODO: Add full path
            return query
        possible_values = dict()
        possible_values.update(kwargs)
        possible_values.update(cls.calculate_logic(query))
        return cls(query, **possible_values)

    @staticmethod
    def calculate_logic(track):
        returning = {}
        if isinstance(track, LocalPath) and (
            track.is_file() or track.is_dir()
        ):
            returning["local"] = True
            if track.is_file():
                returning["single"] = True
            elif track.is_dir():
                returning["album"] = True
            returning["name"] = track.name
        else:
            track = str(track)
            _localtrack = LocalPath(track)
            if _localtrack.is_file():
                returning["local"] = True
                returning["single"] = True
                returning["name"] = _localtrack.name
                return returning
            elif _localtrack.is_dir():
                returning["album"] = True
                returning["local"] = True
                returning["name"] = _localtrack.name
                return returning
            try:
                query_url = urlparse(track)  
                if all([query_url.scheme, query_url.netloc, query_url.path]):
                    url_domain = ".".join(query_url.netloc.split(".")[-2:])
                    if not query_url.netloc:
                        url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
                    if url_domain in ["youtube.com", "youtu.be"]:
                        returning["youtube"] = True
                        if "&t=" in track:
                            match = re.search(r"&t=(\d+)s?", track)
                            if match:
                                returning["start_time"] = match.group(1)
                    elif url_domain == "spotify.com":
                        returning["spotify"] = True
                    elif url_domain == "soundcloud.com":
                        returning["soundcloud"] = True
                        if "#t=" in track:
                            match = re.search(r"#t=(\d+):(\d+)s?", track)
                            if match:
                                returning["start_time"] = (int(match.group(1)) * 60) + int(match.group(2))
                    elif url_domain == "bandcamp.com":
                        returning["bandcamp"] = True
                    elif url_domain == "vimeo.com":
                        returning["vimeo"] = True
                    elif url_domain == "mixer.com":
                        returning["mixer"] = True
                    elif url_domain == "twitch.tv":
                        returning["twitch"] = True
                        if "?t=" in track:
                            match = re.search(r"\?t=(\d+)h(\d+)m(\d+)s", track)
                            if match:
                                returning["start_time"] = (int(match.group(1)) * 60 * 60) + (int(match.group(2)) * 60) + int(match.group(3))
                   
                        if not any(x in track for x in ["/clip/", "/videos/"]):
                            returning["stream"] = True
                    else:
                        returning["other"] = True
                        returning["single"] = True
                else:
                    returning["search"] = True
                    returning["youtube"] = True
                    returning["single"] = True
            except Exception:
                returning["search"] = True
                returning["youtube"] = True
                returning["single"] = True
        return returning

    def get_query(self):
        if self.is_local:
            return self.track.to_string()
        elif self.is_spotify:
            if "/playlist/" in self.track:
                self.is_playlist = True
            elif "/album/" in self.track:
                self.is_album = True
            elif "/track/" in self.track:
                self.single_track = True
            val = re.sub(r"(http[s]?://)?(open.spotify.com)/", "", self.track).replace("/", ":")
            self.id = val.split(":", 1)[-1]
            if "#" in self.id:
                match = re.search(r"#(\d+):(\d+)", self.track)
                if match:
                    self.start_time = (int(match.group(1)) * 60) + int(match.group(2))
            return f"spotify:{val}"
        elif self.is_youtube:
            if "playlist?" in self.track:
                self.is_playlist = True
            else:
                self.single_track = True
            return f"ytsearch:{self.track}"
        elif self.is_soundcloud:
            return f"scsearch:{self.track}"
        else:
            return self.track



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
