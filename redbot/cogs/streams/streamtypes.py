import json
from .errors import (
    StreamNotFound,
    APIError,
    OfflineStream,
    InvalidYoutubeCredentials,
    InvalidTwitchCredentials,
)
from redbot.core.i18n import Translator
from random import choice, sample
from string import ascii_letters
from typing import ClassVar, Optional
from urllib.parse import quote

import aiohttp
import discord

from .errors import (
    APIError,
    GameNotInStreamTargetGameList,
    InvalidTwitchCredentials,
    InvalidYoutubeCredentials,
    OfflineGame,
    OfflineStream,
    StreamNotFound,
)

TWITCH_BASE_URL = "https://api.twitch.tv"
TWITCH_STREAMS_ENDPOINT = TWITCH_BASE_URL + "/helix/streams"
TWITCH_USERS_ENDPOINT = TWITCH_BASE_URL + "/helix/users"
TWITCH_GAMES_ENDPOINT = TWITCH_BASE_URL + "/helix/games"

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_CHANNELS_ENDPOINT = YOUTUBE_BASE_URL + "/channels"
YOUTUBE_SEARCH_ENDPOINT = YOUTUBE_BASE_URL + "/search"
YOUTUBE_VIDEOS_ENDPOINT = YOUTUBE_BASE_URL + "/videos"

_ = Translator("Streams", __file__)


def rnd(url):
    """Appends a random parameter to the url to avoid Discord's caching"""
    return url + "?rnd=" + "".join([choice(ascii_letters) for i in range(6)])


class Game:

    token_name: ClassVar[Optional[str]] = None

    def __init__(self, **kwargs):
        self.name = kwargs.pop("name", None)
        self.id = kwargs.pop("id", None)
        self.channels = kwargs.pop("channels", [])
        self._messages_cache = kwargs.pop("_messages_cache", [])
        self.type = self.__class__.__name__
        self.bot = kwargs.pop("bot", None)
        self.sort = kwargs.pop("sort", None)
        self.count = kwargs.pop("count", None)

    async def has_online_channels(self):
        raise NotImplementedError()

    def make_embed(self):
        raise NotImplementedError()

    def export(self):
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                data[k] = v
        data["messages"] = []
        del data["bot"]
        for m in self._messages_cache:
            data["messages"].append({"channel": m.channel.id, "message": m.id})
        return data

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name}>".format(self)


class TwitchGame(Game):

    token_name = "twitch"

    def __init__(self, **kwargs):
        self._token = kwargs.pop("token", None)
        self.box_art = kwargs.pop("box_art_url", None)
        super().__init__(**kwargs)

    async def has_online_channels(self):
        if self._token["access_token"]:
            header = {"Authorization": "Bearer " + self._token["access_token"]}
        else:
            header = {"Client-ID": str(self._token["client_id"])}
        params = {"game_id": self.id, "first": 100}
        stream_list = []

        async with aiohttp.ClientSession() as session:
            async with session.get(TWITCH_STREAMS_ENDPOINT, headers=header, params=params) as r:
                data = await r.json()
        if r.status == 200:
            if not data["data"]:
                raise OfflineGame()
            stream_list.extend(data["data"])
            cursor = data["pagination"]
            while "cursor" in cursor:
                params2 = {"game_id": self.id, "first": 100, "after": cursor["cursor"]}
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        TWITCH_STREAMS_ENDPOINT, headers=header, params=params2
                    ) as r:
                        data2 = await r.json()
                        if not data2["data"]:
                            break
                        else:
                            stream_list.extend(data2["data"])
                            cursor = data2["pagination"]
            if self.sort == "random":
                if len(data["data"]) < self.count:
                    choices = data["data"]
                else:
                    choices = sample(data["data"], self.count)
            else:
                choices = sorted(data["data"], key=lambda x: x["viewer_count"], reverse=True)[
                    : self.count
                ]
            return self.make_embed(choices)

    def make_embed(self, data: list):
        embed = discord.Embed(
            title=f"Currently live channels playing {self.name}",
            url=f"https://twitch.tv/directory/game/{quote(self.name)}",
        )
        if self.box_art:
            embed.set_thumbnail(url=self.box_art.format(width=150, height=200))
        for chn in data:
            embed.add_field(
                name=chn["user_name"],
                value=f"[{chn['viewer_count']}](https://twitch.tv/{chn['user_name']}) viewers",
                inline=False,
            )
        return embed


class Stream:

    token_name: ClassVar[Optional[str]] = None

    def __init__(self, **kwargs):
        self.name = kwargs.pop("name", None)
        self.channels = kwargs.pop("channels", [])
        # self.already_online = kwargs.pop("already_online", False)
        self._messages_cache = kwargs.pop("_messages_cache", [])
        self.type = self.__class__.__name__
        self.bot = kwargs.pop("bot", None)

    async def is_online(self):
        raise NotImplementedError()

    def make_embed(self):
        raise NotImplementedError()

    def export(self):
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                data[k] = v
        data["messages"] = []
        del data["bot"]
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
        self.games = kwargs.pop("games", None)
        super().__init__(**kwargs)

    async def is_online(self):
        url = TWITCH_STREAMS_ENDPOINT
        params = []
        if self.id:
            params.append(("user_id", self.id))
        else:
            params.append(("user_login", self.name))
        if self._token["access_token"]:
            header = {"Authorization": "Bearer " + self._token["access_token"]}
        else:
            header = {"Client-ID": str(self._token["client_id"])}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=header, params=params) as r:
                data = await r.json(encoding="utf-8")
        if r.status == 200:
            if not data["data"]:
                # self.already_online = False
                raise OfflineStream()
            # self.already_online = True
            #  In case of rename
            stream = data["data"][0]
            self.name = stream["user_name"]
            d = {"stream": stream}
            if not self.id:
                self.id = stream["user_id"]
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TWITCH_USERS_ENDPOINT, headers=header, params={"id": self.id}
                ) as s:
                    data2 = await s.json(encoding="utf-8")

            if s.status == 200:
                d["user"] = data2["data"][0]
            game = None
            if self.games and stream["game_id"] not in self.games:
                raise GameNotInStreamTargetGameList()
            if int(stream["game_id"]) > 0:  # 0 is used for the game id when no game is set
                streams_cog = self.bot.get_cog("Streams")
                if streams_cog:
                    try:
                        game_list = await streams_cog.db.known_games.get_raw("twitch")
                    except KeyError:
                        game_list = []
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                TWITCH_GAMES_ENDPOINT,
                                headers=header,
                                params={"id": stream["game_id"]},
                            ) as game_data:
                                gd = await game_data.json(encoding="utf-8")
                        if game_data.status == 200:
                            game = gd["data"][0]
                            game_list.append(game)
                            await streams_cog.db.known_games.set_raw("twitch", value=game_list)
                    else:
                        for item in game_list:
                            if item["id"] == stream["game_id"]:
                                game = item
                                break
                        else:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(
                                    TWITCH_GAMES_ENDPOINT,
                                    headers=headers,
                                    params={"id": stream["game_id"]},
                                ) as game_data:
                                    gd = await game_data.json(encoding="utf-8")
                            if game_data.status == 200:
                                game = gd["data"][0]
                            game_list.append({"name": game["name"], "id": game["id"]})
                            await streams_cog.db.games.set_raw("twitch", value=game_list)
                    d["game"] = {"name": game["name"], "id": game["id"]}
            else:
                d["game"] = {"name": "an unspecified game", "id": "0"}
            return self.make_embed(d)
        elif r.status == 401:
            raise InvalidTwitchCredentials()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    def make_embed(self, data):
        channel = data["user"]
        stream = data["stream"]
        url = f"https://twitch.tv/{channel['login']}"
        logo = channel["profile_image_url"]
        if not logo:
            logo = "https://static-cdn.jtvnw.net/jtv_user_pictures/xarth/404_user_70x70.png"
        status = stream["title"]
        if not status:
            status = "Untitled broadcast"
        embed = discord.Embed(title=status, url=url)
        embed.set_author(name=channel["display_name"])
<<<<<<< HEAD
        embed.add_field(name="Current viewers", value=stream["viewer_count"])
        embed.add_field(name="Total views", value=channel["view_count"])
        embed.set_thumbnail(url=logo)
        embed.set_footer(text="Playing: " + data["game"]["name"])
        embed.color = 0x6441A4
=======
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
>>>>>>> release/V3/develop


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
        embed = discord.Embed(title=data["name"], url=url)
        embed.set_author(name=user["username"])
        embed.add_field(name=_("Followers"), value=data["numFollowers"])
        embed.add_field(name=_("Total views"), value=data["viewersTotal"])
        if user["avatarUrl"]:
            embed.set_thumbnail(url=user["avatarUrl"])
        else:
            embed.set_thumbnail(url=default_avatar)
        if data["thumbnail"]:
            embed.set_image(url=rnd(data["thumbnail"]["url"]))
        embed.color = 0x4C90F3  # pylint: disable=assigning-non-slot
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
