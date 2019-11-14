import os
import re
from pathlib import Path, PosixPath, WindowsPath
from typing import List, Optional, Union
from urllib.parse import urlparse

import lavalink

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.i18n import Translator

_config: Optional[Config] = None
_bot: Optional[Red] = None
_localtrack_folder: Optional[str] = None
_ = Translator("Audio", __file__)

_RE_REMOVE_START = re.compile(r"^(sc|list) ")
_RE_YOUTUBE_TIMESTAMP = re.compile(r"&t=(\d+)s?")
_RE_YOUTUBE_INDEX = re.compile(r"&index=(\d+)")
_RE_SPOTIFY_URL = re.compile(r"(http[s]?://)?(open.spotify.com)/")
_RE_SPOTIFY_TIMESTAMP = re.compile(r"#(\d+):(\d+)")
_RE_SOUNDCLOUD_TIMESTAMP = re.compile(r"#t=(\d+):(\d+)s?")
_RE_TWITCH_TIMESTAMP = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")

_fully_supported_music_ext = (".mp3", ".flac", ".ogg")
_partially_supported_music_ext = (
    ".m3u",
    ".m4a",
    ".aac",
    ".ra",
    ".wav",
    ".opus",
    ".wma",
    ".ts",
    ".au",
    # These do not work
    # ".mid",
    # ".mka",
    # ".amr",
    # ".aiff",
    # ".ac3",
    # ".voc",
    # ".dsf",
)
_partially_supported_video_ext = (
    ".mp4",
    ".mov",
    ".flv",
    ".webm",
    ".mkv",
    ".wmv",
    ".3gp",
    ".m4v",
    ".mk3d",  # https://github.com/Devoxin/lavaplayer
    ".mka",  # https://github.com/Devoxin/lavaplayer
    ".mks",  # https://github.com/Devoxin/lavaplayer
    # These do not work
    # ".vob",
    # ".mts",
    # ".avi",
    # ".mpg",
    # ".mpeg",
    # ".swf",
)
_partially_supported_music_ext += _partially_supported_video_ext


def _pass_config_to_dataclasses(config: Config, bot: Red, folder: str):
    global _config, _bot, _localtrack_folder
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot
    _localtrack_folder = folder


class LocalPath:
    """Local tracks class.

    Used to handle system dir trees in a cross system manner. The only use of this class is for
    `localtracks`.
    """

    _all_music_ext = _fully_supported_music_ext + _partially_supported_music_ext

    def __init__(self, path, **kwargs):
        self._path = path
        if isinstance(path, (Path, WindowsPath, PosixPath, LocalPath)):
            path = str(path.absolute())
        elif path is not None:
            path = str(path)

        self.cwd = Path.cwd()
        _lt_folder = Path(_localtrack_folder) if _localtrack_folder else self.cwd
        _path = Path(path) if path else self.cwd

        if _lt_folder.parts[-1].lower() == "localtracks" and not kwargs.get("forced"):
            self.localtrack_folder = _lt_folder
        elif kwargs.get("forced"):
            if _path.parts[-1].lower() == "localtracks":
                self.localtrack_folder = _path
            else:
                self.localtrack_folder = _path / "localtracks"
        else:
            self.localtrack_folder = _lt_folder / "localtracks"

        try:
            _path = Path(path)
            _path.relative_to(self.localtrack_folder)
            self.path = _path
        except (ValueError, TypeError):
            if path and path.startswith("localtracks//"):
                path = path.replace("localtracks//", "", 1)
            elif path and path.startswith("localtracks/"):
                path = path.replace("localtracks/", "", 1)
            self.path = self.localtrack_folder.joinpath(path) if path else self.localtrack_folder

        try:
            if self.path.is_file():
                parent = self.path.parent
            else:
                parent = self.path
            self.parent = Path(parent)
        except OSError:
            self.parent = None

    @property
    def name(self):
        return str(self.path.name)

    @property
    def suffix(self):
        return str(self.path.suffix)

    def is_dir(self):
        try:
            return self.path.is_dir()
        except OSError:
            return False

    def exists(self):
        try:
            return self.path.exists()
        except OSError:
            return False

    def is_file(self):
        try:
            return self.path.is_file()
        except OSError:
            return False

    def absolute(self):
        try:
            return self.path.absolute()
        except OSError:
            return self._path

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
            if p.suffix in self._all_music_ext:
                yield p

    def __str__(self):
        return self.to_string()

    def to_string(self):
        try:
            return str(self.path.absolute())
        except OSError:
            return str(self._path)

    def to_string_user(self, arg: str = None):
        string = str(self.absolute()).replace(
            (str(self.localtrack_folder.absolute()) + os.sep) if arg is None else arg, ""
        )
        chunked = False
        while len(string) > 145 and os.sep in string:
            string = string.split(os.sep, 1)[-1]
            chunked = True

        if chunked:
            string = f"...{os.sep}{string}"
        return string

    def tracks_in_tree(self):
        tracks = []
        for track in self.multirglob(*[f"*{ext}" for ext in self._all_music_ext]):
            if track.exists() and track.is_file() and track.parent != self.localtrack_folder:
                tracks.append(Query.process_input(LocalPath(str(track.absolute()))))
        return sorted(tracks, key=lambda x: x.to_string_user().lower())

    def subfolders_in_tree(self):
        files = list(self.multirglob(*[f"*{ext}" for ext in self._all_music_ext]))
        folders = []
        for f in files:
            if f.exists() and f.parent not in folders and f.parent != self.localtrack_folder:
                folders.append(f.parent)
        return_folders = []
        for folder in folders:
            if folder.exists() and folder.is_dir():
                return_folders.append(LocalPath(str(folder.absolute())))
        return sorted(return_folders, key=lambda x: x.to_string_user().lower())

    def tracks_in_folder(self):
        tracks = []
        for track in self.multiglob(*[f"*{ext}" for ext in self._all_music_ext]):
            if track.exists() and track.is_file() and track.parent != self.localtrack_folder:
                tracks.append(Query.process_input(LocalPath(str(track.absolute()))))
        return sorted(tracks, key=lambda x: x.to_string_user().lower())

    def subfolders(self):
        files = list(self.multiglob(*[f"*{ext}" for ext in self._all_music_ext]))
        folders = []
        for f in files:
            if f.exists() and f.parent not in folders and f.parent != self.localtrack_folder:
                folders.append(f.parent)
        return_folders = []
        for folder in folders:
            if folder.exists() and folder.is_dir():
                return_folders.append(LocalPath(str(folder.absolute())))
        return sorted(return_folders, key=lambda x: x.to_string_user().lower())

    def __eq__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return self.path._cparts == other.path._cparts

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(tuple(self.path._cparts))
            return self._hash

    def __lt__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return self.path._cparts < other.path._cparts

    def __le__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return self.path._cparts <= other.path._cparts

    def __gt__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return self.path._cparts > other.path._cparts

    def __ge__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return self.path._cparts >= other.path._cparts


class Query:
    """Query data class.

    Use: Query.process_input(query) to generate the Query object.
    """

    def __init__(self, query: Union[LocalPath, str], **kwargs):
        query = kwargs.get("queryforced", query)
        self._raw: Union[LocalPath, str] = query

        _localtrack: LocalPath = LocalPath(query)

        self.track: Union[LocalPath, str] = _localtrack if (
            (_localtrack.is_file() or _localtrack.is_dir()) and _localtrack.exists()
        ) else query

        self.valid: bool = query != "InvalidQueryPlaceHolderName"
        self.is_local: bool = kwargs.get("local", False)
        self.is_spotify: bool = kwargs.get("spotify", False)
        self.is_youtube: bool = kwargs.get("youtube", False)
        self.is_soundcloud: bool = kwargs.get("soundcloud", False)
        self.is_bandcamp: bool = kwargs.get("bandcamp", False)
        self.is_vimeo: bool = kwargs.get("vimeo", False)
        self.is_mixer: bool = kwargs.get("mixer", False)
        self.is_twitch: bool = kwargs.get("twitch", False)
        self.is_other: bool = kwargs.get("other", False)
        self.is_playlist: bool = kwargs.get("playlist", False)
        self.is_album: bool = kwargs.get("album", False)
        self.is_search: bool = kwargs.get("search", False)
        self.is_stream: bool = kwargs.get("stream", False)
        self.single_track: bool = kwargs.get("single", False)
        self.id: Optional[str] = kwargs.get("id", None)
        self.invoked_from: Optional[str] = kwargs.get("invoked_from", None)
        self.local_name: Optional[str] = kwargs.get("name", None)
        self.search_subfolders: bool = kwargs.get("search_subfolders", False)
        self.spotify_uri: Optional[str] = kwargs.get("uri", None)
        self.uri: Optional[str] = kwargs.get("url", None)

        self.start_time: int = kwargs.get("start_time", 0)
        self.track_index: Optional[int] = kwargs.get("track_index", None)

        if self.invoked_from == "sc search":
            self.is_youtube = False
            self.is_soundcloud = True

        self.lavalink_query: str = self._get_query()

        if self.is_playlist or self.is_album:
            self.single_track = False
        self._hash = hash(
            (
                self.valid,
                self.is_local,
                self.is_spotify,
                self.is_youtube,
                self.is_soundcloud,
                self.is_bandcamp,
                self.is_vimeo,
                self.is_mixer,
                self.is_twitch,
                self.is_other,
                self.is_playlist,
                self.is_album,
                self.is_search,
                self.is_stream,
                self.single_track,
                self.id,
                self.spotify_uri,
                self.start_time,
                self.track_index,
                self.uri,
            )
        )

    def __str__(self):
        return str(self.lavalink_query)

    @classmethod
    def process_input(cls, query: Union[LocalPath, lavalink.Track, "Query", str], **kwargs):
        """A replacement for :code:`lavalink.Player.load_tracks`. This will try to get a valid
        cached entry first if not found or if in valid it will then call the lavalink API.

        Parameters
        ----------
        query : Union[Query, LocalPath, lavalink.Track, str]
            The query string or LocalPath object.
        Returns
        -------
        Query
            Returns a parsed Query object.
        """
        if not query:
            query = "InvalidQueryPlaceHolderName"
        possible_values = {}

        if isinstance(query, str):
            query = query.strip("<>")

        elif isinstance(query, Query):
            for key, val in kwargs.items():
                setattr(query, key, val)
            return query
        elif isinstance(query, lavalink.Track):
            possible_values["stream"] = query.is_stream
            query = query.uri

        possible_values.update(dict(**kwargs))
        possible_values.update(cls._parse(query, **kwargs))
        return cls(query, **possible_values)

    @staticmethod
    def _parse(track, **kwargs):
        returning = {}
        if (
            type(track) == type(LocalPath)
            and (track.is_file() or track.is_dir())
            and track.exists()
        ):
            returning["local"] = True
            returning["name"] = track.name
            if track.is_file():
                returning["single"] = True
            elif track.is_dir():
                returning["album"] = True
        else:
            track = str(track)
            if track.startswith("spotify:"):
                returning["spotify"] = True
                if ":playlist:" in track:
                    returning["playlist"] = True
                elif ":album:" in track:
                    returning["album"] = True
                elif ":track:" in track:
                    returning["single"] = True
                _id = track.split(":", 2)[-1]
                _id = _id.split("?")[0]
                returning["id"] = _id
                if "#" in _id:
                    match = re.search(_RE_SPOTIFY_TIMESTAMP, track)
                    if match:
                        returning["start_time"] = (int(match.group(1)) * 60) + int(match.group(2))
                returning["uri"] = track
                return returning
            if track.startswith("sc ") or track.startswith("list "):
                if track.startswith("sc "):
                    returning["invoked_from"] = "sc search"
                    returning["soundcloud"] = True
                elif track.startswith("list "):
                    returning["invoked_from"] = "search list"
                track = _RE_REMOVE_START.sub("", track, 1)
                returning["queryforced"] = track

            _localtrack = LocalPath(track)
            if _localtrack.exists():
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
                    returning["url"] = track
                    url_domain = ".".join(query_url.netloc.split(".")[-2:])
                    if not query_url.netloc:
                        url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
                    if url_domain in ["youtube.com", "youtu.be"]:
                        returning["youtube"] = True
                        _has_index = "&index=" in track
                        if "&t=" in track:
                            match = re.search(_RE_YOUTUBE_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = int(match.group(1))
                        if _has_index:
                            match = re.search(_RE_YOUTUBE_INDEX, track)
                            if match:
                                returning["track_index"] = int(match.group(1)) - 1
                        if all(k in track for k in ["&list=", "watch?"]):
                            returning["track_index"] = 0
                            returning["playlist"] = True
                            returning["single"] = False
                        elif all(x in track for x in ["playlist?"]):
                            returning["playlist"] = not _has_index
                            returning["single"] = _has_index
                        elif any(k in track for k in ["list="]):
                            returning["track_index"] = 0
                            returning["playlist"] = True
                            returning["single"] = False
                        else:
                            returning["single"] = True
                    elif url_domain == "spotify.com":
                        returning["spotify"] = True
                        if "/playlist/" in track:
                            returning["playlist"] = True
                        elif "/album/" in track:
                            returning["album"] = True
                        elif "/track/" in track:
                            returning["single"] = True
                        val = re.sub(_RE_SPOTIFY_URL, "", track).replace("/", ":")
                        if "user:" in val:
                            val = val.split(":", 2)[-1]
                        _id = val.split(":", 1)[-1]
                        _id = _id.split("?")[0]

                        if "#" in _id:
                            _id = _id.split("#")[0]
                            match = re.search(_RE_SPOTIFY_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = (int(match.group(1)) * 60) + int(
                                    match.group(2)
                                )

                        returning["id"] = _id
                        returning["uri"] = f"spotify:{val}"
                    elif url_domain == "soundcloud.com":
                        returning["soundcloud"] = True
                        if "#t=" in track:
                            match = re.search(_RE_SOUNDCLOUD_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = (int(match.group(1)) * 60) + int(
                                    match.group(2)
                                )
                        if "/sets/" in track:
                            if "?in=" in track:
                                returning["single"] = True
                            else:
                                returning["playlist"] = True
                        else:
                            returning["single"] = True
                    elif url_domain == "bandcamp.com":
                        returning["bandcamp"] = True
                        if "/album/" in track:
                            returning["album"] = True
                        else:
                            returning["single"] = True
                    elif url_domain == "vimeo.com":
                        returning["vimeo"] = True
                    elif url_domain in ["mixer.com", "beam.pro"]:
                        returning["mixer"] = True
                    elif url_domain == "twitch.tv":
                        returning["twitch"] = True
                        if "?t=" in track:
                            match = re.search(_RE_TWITCH_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = (
                                    (int(match.group(1)) * 60 * 60)
                                    + (int(match.group(2)) * 60)
                                    + int(match.group(3))
                                )

                        if not any(x in track for x in ["/clip/", "/videos/"]):
                            returning["stream"] = True
                    else:
                        returning["other"] = True
                        returning["single"] = True
                else:
                    if kwargs.get("soundcloud", False):
                        returning["soundcloud"] = True
                    else:
                        returning["youtube"] = True
                    returning["search"] = True
                    returning["single"] = True
            except Exception:
                returning["search"] = True
                returning["youtube"] = True
                returning["single"] = True
        return returning

    def _get_query(self):
        if self.is_local:
            return self.track.to_string()
        elif self.is_spotify:
            return self.spotify_uri
        elif self.is_search and self.is_youtube:
            return f"ytsearch:{self.track}"
        elif self.is_search and self.is_soundcloud:
            return f"scsearch:{self.track}"
        return self.track

    def to_string_user(self):
        if self.is_local:
            return str(self.track.to_string_user())
        return str(self._raw)

    @property
    def suffix(self):
        if self.is_local:
            return self.track.suffix
        return None

    def __eq__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() == other.to_string_user()

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(
                (
                    self.valid,
                    self.is_local,
                    self.is_spotify,
                    self.is_youtube,
                    self.is_soundcloud,
                    self.is_bandcamp,
                    self.is_vimeo,
                    self.is_mixer,
                    self.is_twitch,
                    self.is_other,
                    self.is_playlist,
                    self.is_album,
                    self.is_search,
                    self.is_stream,
                    self.single_track,
                    self.id,
                    self.spotify_uri,
                    self.start_time,
                    self.track_index,
                    self.uri,
                )
            )
            return self._hash

    def __lt__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() < other.to_string_user()

    def __le__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() <= other.to_string_user()

    def __gt__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() > other.to_string_user()

    def __ge__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() >= other.to_string_user()
