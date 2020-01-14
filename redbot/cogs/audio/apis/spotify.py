import base64
import contextlib
import time
from typing import Optional, MutableMapping, Union, NoReturn, List, Tuple

import aiohttp

from redbot import logging

from ..audio_globals import get_bot
from ..errors import SpotifyFetchError


log = logging.getLogger("red.cogs.Audio.api.Spotify")


CATEGORY_ENDPOINT = "https://api.spotify.com/v1/browse/categories"
TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"
ALBUMS_ENDPOINT = "https://api.spotify.com/v1/albums"
TRACKS_ENDPOINT = "https://api.spotify.com/v1/tracks"
PLAYLISTS_ENDPOINT = "https://api.spotify.com/v1/playlists"


class SpotifyWrapper:
    """Wrapper for the Spotify API."""

    def __init__(self, session: aiohttp.ClientSession):
        self.bot = get_bot()
        self.session = session
        self.spotify_token: Optional[MutableMapping[str, Union[str, int]]] = None
        self.client_id = None
        self.client_secret = None

    @staticmethod
    def spotify_format_call(qtype: str, key: str) -> Tuple[str, MutableMapping]:
        params = {}
        if qtype == "album":
            query = f"{ALBUMS_ENDPOINT}/{key}/tracks"
        elif qtype == "track":
            query = f"{TRACKS_ENDPOINT}/{key}"
        else:
            query = f"{PLAYLISTS_ENDPOINT}/{key}/tracks"
        return query, params

    @staticmethod
    def get_spotify_track_info(track_data: MutableMapping) -> Tuple[str, ...]:
        artist_name = track_data["artists"][0]["name"]
        track_name = track_data["name"]
        track_info = f"{track_name} {artist_name}"
        song_url = track_data.get("external_urls", {}).get("spotify")
        uri = track_data["uri"]
        _id = track_data["id"]
        _type = track_data["type"]

        return song_url, track_info, uri, artist_name, track_name, _id, _type

    @staticmethod
    async def _check_token(token: MutableMapping):
        return (token["expires_at"] - int(time.time())) < 60

    @staticmethod
    def _make_token_auth(
        client_id: Optional[str], client_secret: Optional[str]
    ) -> MutableMapping[str, Union[str, int]]:
        if client_id is None:
            client_id = ""
        if client_secret is None:
            client_secret = ""
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode("ascii"))
        return {"Authorization": f"Basic {auth_header.decode('ascii')}"}

    async def _make_get(
        self, url: str, headers: MutableMapping = None, params: MutableMapping = None
    ) -> MutableMapping[str, str]:
        if params is None:
            params = {}
        async with self.session.request("GET", url, params=params, headers=headers) as r:
            data = await r.json()
            if r.status != 200:
                log.debug(f"Issue making GET request to {url}: [{r.status}] {data}")
            return data

    async def _get_auth(self) -> NoReturn:
        tokens = await self.bot.get_shared_api_tokens("spotify")
        self.client_id = tokens.get("client_id", "")
        self.client_secret = tokens.get("client_secret", "")

    async def _request_token(self) -> MutableMapping[str, Union[str, int]]:
        await self._get_auth()
        payload = {"grant_type": "client_credentials"}
        headers = self._make_token_auth(self.client_id, self.client_secret)
        r = await self.post_call(TOKEN_ENDPOINT, payload=payload, headers=headers)
        return r

    async def _get_spotify_token(self) -> Optional[str]:
        if self.spotify_token and not await self._check_token(self.spotify_token):
            return self.spotify_token["access_token"]
        token = await self._request_token()
        if token is None:
            log.debug("Requested a token from Spotify, did not end up getting one.")
        try:
            token["expires_at"] = int(time.time()) + token["expires_in"]
        except KeyError:
            return
        self.spotify_token = token
        log.debug(f"Created a new access token for Spotify: {token}")
        return self.spotify_token["access_token"]

    async def post_call(
        self, url: str, payload: MutableMapping, headers: MutableMapping = None
    ) -> MutableMapping[str, Union[str, int]]:
        async with self.session.post(url, data=payload, headers=headers) as r:
            data = await r.json()
            if r.status != 200:
                log.debug(f"Issue making POST request to {url}: [{r.status}] {data}")
            return data

    async def get_call(
        self, url: str, params: MutableMapping
    ) -> MutableMapping[str, Union[str, int]]:
        token = await self._get_spotify_token()
        return await self._make_get(
            url, params=params, headers={"Authorization": f"Bearer {token}"}
        )

    async def get_categories(self) -> List[MutableMapping]:
        params = {}
        result = await self.get_call(CATEGORY_ENDPOINT, params=params)
        with contextlib.suppress(KeyError):
            if result["error"]["status"] == 401:
                raise SpotifyFetchError(
                    message=(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    )
                )
        categories = result.get("categories", {}).get("items", [])
        return [{c["name"]: c["id"]} for c in categories]

    async def get_playlist_from_category(self, category: str):
        url = f"{CATEGORY_ENDPOINT}/{category}/playlists"
        params = {}
        result = await self.get_call(url, params=params)
        playlists = result.get("playlists", {}).get("items", [])
        return [
            {
                "name": c["name"],
                "uri": c["uri"],
                "url": c.get("external_urls", {}).get("spotify"),
                "tracks": c.get("tracks", {}).get("total", "Unknown"),
            }
            for c in playlists
        ]
