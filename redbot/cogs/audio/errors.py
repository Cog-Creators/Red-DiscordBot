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



class ApiError(AudioError):
    """"""

class SpotifyApiError(ApiError):
    """"""

class SpotifyFetchError(SpotifyApiError):
    """"""
    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)

class YouTubeApiError(ApiError):
    """"""


