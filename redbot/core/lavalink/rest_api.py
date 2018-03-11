from aiohttp import ClientSession

from .websocket import loop
from . import log

__all__ = ['initialize', 'get_tracks', 'search_yt', 'search_sc']

_session = None  # type: ClientSession
_uri = ''
_headers = {}

def initialize(host, port, password):
    global _session
    global _uri

    if _session is None:
        _session = ClientSession(loop=loop)
    _uri = "http://{}:{}/loadtracks?identifier=".format(host, port)
    _headers['Authorization'] = password


async def get_tracks(query):
    url = _uri + str(query)
    async with _session.get(url, headers=_headers) as resp:
        return await resp.json(content_type=None)


async def search_yt(query):
    return await get_tracks('ytsearch:{}'.format(query))


async def search_sc(query):
    return await get_tracks('scsearch:{}'.format(query))


async def close():
    global _session
    await _session.close()
    _session = None
    log.debug("Closed REST session.")
