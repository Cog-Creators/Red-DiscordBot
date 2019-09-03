import json
from random import choice
from string import ascii_letters
from typing import ClassVar, Optional

import aiohttp
import discord

from redbot.core.i18n import Translator
from .errors import (
    APIError,
    InvalidTwitchCredentials,
    InvalidYoutubeCredentials,
    OfflineStream,
    StreamNotFound,
)

TWITCH_BASE_URL = "https://api.twitch.tv"
TWITCH_ID_ENDPOINT = TWITCH_BASE_URL + "/kraken/users?login="
TWITCH_STREAMS_ENDPOINT = TWITCH_BASE_URL + "/kraken/streams/"
TWITCH_COMMUNITIES_ENDPOINT = TWITCH_BASE_URL + "/kraken/communities"

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_CHANNELS_ENDPOINT = YOUTUBE_BASE_URL + "/channels"
YOUTUBE_SEARCH_ENDPOINT = YOUTUBE_BASE_URL + "/search"
YOUTUBE_VIDEOS_ENDPOINT = YOUTUBE_BASE_URL + "/videos"

_ = Translator("Streams", __file__)


def rnd(url):
    """Appends a random parameter to the url to avoid Discord's caching"""
    return url + "?rnd=" + "".join([choice(ascii_letters) for _ in range(6)])


class Stream:

    token_name: ClassVar[Optional[str]] = None

    def __init__(self, **kwargs):
        self.name = kwargs.pop("name", None)
        self.channels = kwargs.pop("channels", [])
        # self.already_online = kwargs.pop("already_online", False)
        self._messages_cache = kwargs.pop("_messages_cache", [])
        self.type = self.__class__.__name__

    async def is_online(self):
        raise NotImplementedError()

    def make_embed(self, data):
        raise NotImplementedError()

    def export(self):
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                data[k] = v
        data["messages"] = []
        for m in self._messages_cache:
            data["messages"].append({"channel": m.channel.id, "message": m.id})
        return data

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name}>".format(self)


class YoutubeStream(Stream):

    token_name = "youtube"

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", None)
        self._token = kwargs.pop("token", None)
        super().__init__(**kwargs)

    async def is_online(self):
        if not self._token:
            raise InvalidYoutubeCredentials("YouTube API key is not set.")

        if not self.id:
            self.id = await self.fetch_id()
        elif not self.name:
            self.name = await self.fetch_name()

        url = YOUTUBE_SEARCH_ENDPOINT
        params = {
            "key": self._token["api_key"],
            "part": "snippet",
            "channelId": self.id,
            "type": "video",
            "eventType": "live",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                data = await r.json()
        if "items" in data and len(data["items"]) == 0:
            raise OfflineStream()
        elif "items" in data:
            vid_id = data["items"][0]["id"]["videoId"]
            params = {"key": self._token["api_key"], "id": vid_id, "part": "snippet"}
            async with aiohttp.ClientSession() as session:
                async with session.get(YOUTUBE_VIDEOS_ENDPOINT, params=params) as r:
                    data = await r.json()
            return self.make_embed(data)

    def make_embed(self, data):
        vid_data = data["items"][0]
        video_url = "https://youtube.com/watch?v={}".format(vid_data["id"])
        title = vid_data["snippet"]["title"]
        thumbnail = vid_data["snippet"]["thumbnails"]["default"]["url"]
        channel_title = vid_data["snippet"]["channelTitle"]
        embed = discord.Embed(title=title, url=video_url)
        embed.set_author(name=channel_title)
        embed.set_image(url=rnd(thumbnail))
        embed.colour = 0x9255A5
        return embed

    async def fetch_id(self):
        return await self._fetch_channel_resource("id")

    async def fetch_name(self):
        snippet = await self._fetch_channel_resource("snippet")
        return snippet["title"]

    async def _fetch_channel_resource(self, resource: str):

        params = {"key": self._token["api_key"], "part": resource}
        if resource == "id":
            params["forUsername"] = self.name
        else:
            params["id"] = self.id

        async with aiohttp.ClientSession() as session:
            async with session.get(YOUTUBE_CHANNELS_ENDPOINT, params=params) as r:
                data = await r.json()

        if (
            "error" in data
            and data["error"]["code"] == 400
            and data["error"]["errors"][0]["reason"] == "keyInvalid"
        ):
            raise InvalidYoutubeCredentials()
        elif "items" in data and len(data["items"]) == 0:
            raise StreamNotFound()
        elif "items" in data:
            return data["items"][0][resource]
        raise APIError()

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name} (ID: {0.id})>".format(self)


class TwitchStream(Stream):

    token_name = "twitch"

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", None)
        self._token = kwargs.pop("token", None)
        super().__init__(**kwargs)

    async def is_online(self):
        if not self.id:
            self.id = await self.fetch_id()

        url = TWITCH_STREAMS_ENDPOINT + self.id
        header = {
            "Client-ID": str(self._token["client_id"]),
            "Accept": "application/vnd.twitchtv.v5+json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=header) as r:
                data = await r.json(encoding="utf-8")
        if r.status == 200:
            if data["stream"] is None:
                # self.already_online = False
                raise OfflineStream()
            # self.already_online = True
            #  In case of rename
            self.name = data["stream"]["channel"]["name"]
            is_rerun = True if data["stream"]["stream_type"] == "rerun" else False
            return self.make_embed(data), is_rerun
        elif r.status == 400:
            raise InvalidTwitchCredentials()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    async def fetch_id(self):
        header = {
            "Client-ID": str(self._token["client_id"]),
            "Accept": "application/vnd.twitchtv.v5+json",
        }
        url = TWITCH_ID_ENDPOINT + self.name

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=header) as r:
                data = await r.json()

        if r.status == 200:
            if not data["users"]:
                raise StreamNotFound()
            return data["users"][0]["_id"]
        elif r.status == 400:
            raise InvalidTwitchCredentials()
        else:
            raise APIError()

    def make_embed(self, data):
        channel = data["stream"]["channel"]
        is_rerun = data["stream"]["stream_type"] == "rerun"
        url = channel["url"]
        logo = channel["logo"]
        if logo is None:
            logo = "https://static-cdn.jtvnw.net/jtv_user_pictures/xarth/404_user_70x70.png"
        status = channel["status"]
        if not status:
            status = "Untitled broadcast"
        if is_rerun:
            status += " - Rerun"
        embed = discord.Embed(title=status, url=url, color=0x6441A4)
        embed.set_author(name=channel["display_name"])
        embed.add_field(name=_("Followers"), value=channel["followers"])
        embed.add_field(name=_("Total views"), value=channel["views"])
        embed.set_thumbnail(url=logo)
        if data["stream"]["preview"]["medium"]:
            embed.set_image(url=rnd(data["stream"]["preview"]["medium"]))
        if channel["game"]:
            embed.set_footer(text=_("Playing: ") + channel["game"])

        return embed

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name} (ID: {0.id})>".format(self)


class HitboxStream(Stream):

    token_name = None  # This streaming services don't currently require an API key

    async def is_online(self):
        url = "https://api.hitbox.tv/media/live/" + self.name

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                # data = await r.json(encoding='utf-8')
                data = await r.text()
        data = json.loads(data, strict=False)
        if "livestream" not in data:
            raise StreamNotFound()
        elif data["livestream"][0]["media_is_live"] == "0":
            # self.already_online = False
            raise OfflineStream()
        elif data["livestream"][0]["media_is_live"] == "1":
            # self.already_online = True
            return self.make_embed(data)

        raise APIError()

    def make_embed(self, data):
        base_url = "https://edge.sf.hitbox.tv"
        livestream = data["livestream"][0]
        channel = livestream["channel"]
        url = channel["channel_link"]
        embed = discord.Embed(title=livestream["media_status"], url=url, color=0x98CB00)
        embed.set_author(name=livestream["media_name"])
        embed.add_field(name=_("Followers"), value=channel["followers"])
        embed.set_thumbnail(url=base_url + channel["user_logo"])
        if livestream["media_thumbnail"]:
            embed.set_image(url=rnd(base_url + livestream["media_thumbnail"]))
        embed.set_footer(text=_("Playing: ") + livestream["category_name"])

        return embed


class MixerStream(Stream):

    token_name = None  # This streaming services don't currently require an API key

    async def is_online(self):
        url = "https://mixer.com/api/v1/channels/" + self.name

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                # data = await r.json(encoding='utf-8')
                data = await r.text(encoding="utf-8")
        if r.status == 200:
            data = json.loads(data, strict=False)
            if data["online"] is True:
                # self.already_online = True
                return self.make_embed(data)
            else:
                # self.already_online = False
                raise OfflineStream()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    def make_embed(self, data):
        default_avatar = "https://mixer.com/_latest/assets/images/main/avatars/default.jpg"
        user = data["user"]
        url = "https://mixer.com/" + data["token"]
        embed = discord.Embed(title=data["name"], url=url, colour=discord.Colour(0x4C90F3))
        embed.set_author(name=user["username"])
        embed.add_field(name=_("Followers"), value=data["numFollowers"])
        embed.add_field(name=_("Total views"), value=data["viewersTotal"])
        if user["avatarUrl"]:
            embed.set_thumbnail(url=user["avatarUrl"])
        else:
            embed.set_thumbnail(url=default_avatar)
        if data["thumbnail"]:
            embed.set_image(
                url=rnd(data["thumbnail"]["url"])
            )  # pylint: disable=assigning-non-slot
        if data["type"] is not None:
            embed.set_footer(text=_("Playing: ") + data["type"]["name"])
        return embed


class PicartoStream(Stream):

    token_name = None  # This streaming services don't currently require an API key

    async def is_online(self):
        url = "https://api.picarto.tv/v1/channel/name/" + self.name

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.text(encoding="utf-8")
        if r.status == 200:
            data = json.loads(data)
            if data["online"] is True:
                # self.already_online = True
                return self.make_embed(data)
            else:
                # self.already_online = False
                raise OfflineStream()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    def make_embed(self, data):
        avatar = rnd(
            "https://picarto.tv/user_data/usrimg/{}/dsdefault.jpg".format(data["name"].lower())
        )
        url = "https://picarto.tv/" + data["name"]
        thumbnail = data["thumbnails"]["web"]
        embed = discord.Embed(title=data["title"], url=url, color=0x4C90F3)
        embed.set_author(name=data["name"])
        embed.set_image(url=rnd(thumbnail))
        embed.add_field(name=_("Followers"), value=data["followers"])
        embed.add_field(name=_("Total views"), value=data["viewers_total"])
        embed.set_thumbnail(url=avatar)
        data["tags"] = ", ".join(data["tags"])

        if not data["tags"]:
            data["tags"] = _("None")

        if data["adult"]:
            data["adult"] = _("NSFW | ")
        else:
            data["adult"] = ""

        embed.set_footer(text=_("{adult}Category: {category} | Tags: {tags}").format(**data))
        return embed
