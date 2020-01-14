import datetime
import json
from dataclasses import dataclass, field
from typing import Optional, MutableMapping, List


@dataclass
class YouTubeCacheFetchResult:
    query: Optional[str]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)


@dataclass
class SpotifyCacheFetchResult:
    query: Optional[str]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)


@dataclass
class LavalinkCacheFetchResult:
    query: Optional[MutableMapping]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)

        if isinstance(self.query, str):
            self.query = json.loads(self.query)


@dataclass
class PlaylistFetchResult:
    playlist_id: int
    playlist_name: str
    scope_id: int
    author_id: int
    playlist_url: Optional[str] = None
    tracks: List[MutableMapping] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)
