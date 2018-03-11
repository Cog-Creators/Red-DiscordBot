from aiohttp import ClientSession

from . import log

__all__ = ['initialize', 'get_tracks', 'search_yt', 'search_sc']

_session = None  # type: ClientSession
_uri = ''
_headers = {}

def initialize(loop, host, port, password):
    """
    Does initialization for the Lavalink REST client.

    Parameters
    ----------
    host : str
    port : int
    password : str
    """
    global _session
    global _uri

    if _session is None:
        _session = ClientSession(loop=loop)
    _uri = "http://{}:{}/loadtracks?identifier=".format(host, port)
    _headers['Authorization'] = password


async def get_tracks(query):
    """
    Gets tracks from lavalink.

    Parameters
    ----------
    query : str

    Returns
    -------
    list of dict
    """
    url = _uri + str(query)
    async with _session.get(url, headers=_headers) as resp:
        return await resp.json(content_type=None)


async def search_yt(query):
    """
    Gets track results from YouTube from Lavalink.

    Parameters
    ----------
    query : str

    Returns
    -------
    list of dict
    """
    return await get_tracks('ytsearch:{}'.format(query))


async def search_sc(query):
    """
    Gets track results from SoundCloud from Lavalink.

    Parameters
    ----------
    query : str

    Returns
    -------
    list of dict
    """
    return await get_tracks('scsearch:{}'.format(query))


async def close():
    global _session
    await _session.close()
    _session = None
    log.debug("Closed REST session.")
