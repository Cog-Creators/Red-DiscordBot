import aiohttp


class AudioError(Exception):
    """Base exception for errors in the Audio cog."""


class LavalinkDownloadFailed(AudioError, RuntimeError):
    """Downloading the Lavalink jar failed.

    Attributes
    ----------
    response : aiohttp.ClientResponse
        The response from the server to the failed GET request.
    should_retry : bool
        Whether or not the Audio cog should retry downloading the jar.

    """

    def __init__(self, *args, response: aiohttp.ClientResponse, should_retry: bool = False):
        super().__init__(*args)
        self.response = response
        self.should_retry = should_retry

    def __repr__(self) -> str:
        str_args = [*map(str, self.args), self._response_repr()]
        return f"LavalinkDownloadFailed({', '.join(str_args)}"

    def __str__(self) -> str:
        return f"{super().__str__()} {self._response_repr()}"

    def _response_repr(self) -> str:
        return f"[{self.response.status} {self.response.reason}]"


class PlayListError(AudioError):
    """Base exception for errors related to playlists."""


class InvalidPlaylistScope(PlayListError):
    """Provided playlist scope is not valid."""


class MissingGuild(PlayListError):
    """Trying to access the Guild scope without a guild."""


class MissingAuthor(PlayListError):
    """Trying to access the User scope without an user id."""


class TooManyMatches(PlayListError):
    """Too many playlist match user input."""


class NotAllowed(PlayListError):
    """Too many playlist match user input."""


class ApiError(AudioError):
    """Base exception for API errors in the Audio cog."""


class SpotifyApiError(ApiError):
    """Base exception for Spotify API errors."""


class SpotifyFetchError(SpotifyApiError):
    """Fetching Spotify data failed."""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)


class YouTubeApiError(ApiError):
    """Base exception for YouTube Data API errors."""


class DatabaseError(AudioError):
    """Base exception for database errors in the Audio cog."""


class InvalidTableError(DatabaseError):
    """Provided table to query is not a valid table."""


class LocalTrackError(AudioError):
    """Base exception for local track errors."""


class InvalidLocalTrack(LocalTrackError):
    """Base exception for local track errors."""


class InvalidLocalTrackFolder(LocalTrackError):
    """Base exception for local track errors."""
