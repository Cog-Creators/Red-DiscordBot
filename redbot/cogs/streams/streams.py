from .errors import StreamNotFound, APIError, InvalidCredentials, OfflineStream, CommunityNotFound, OfflineCommunity
from random import choice
from string import ascii_letters
import discord
import aiohttp
import json

TWITCH_BASE_URL = "https://api.twitch.tv"
TWITCH_ID_ENDPOINT = TWITCH_BASE_URL + "/kraken/users?login="
TWITCH_STREAMS_ENDPOINT = TWITCH_BASE_URL + "/kraken/streams/"
TWITCH_COMMUNITIES_ENDPOINT = TWITCH_BASE_URL + "/kraken/communities"


def rnd(url):
    """Appends a random parameter to the url to avoid Discord's caching"""
    return url + "?rnd=" + "".join([choice(ascii_letters) for i in range(6)])


class TwitchCommunity:
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.id = kwargs.pop("id", None)
        self.channels = kwargs.pop("channels", [])
        self._token = kwargs.pop("token", None)
        self.type = self.__class__.__name__

    async def get_community_id(self):
        session = aiohttp.ClientSession()
        headers = {
            "Accept": "application/vnd.twitchtv.v5+json",
            "Client-ID": str(self._token)
        }
        params = {
            "name": self.name
        }
        async with session.get(TWITCH_COMMUNITIES_ENDPOINT, headers=headers, params=params) as r:
            data = await r.json()
        await session.close()
        if "status" in data and data["status"] == 404:
            raise CommunityNotFound()
        return data["_id"]

    async def get_community_streams(self):
        if not self.id:
            try:
                self.id = await self.get_community_id()
            except CommunityNotFound:
                raise
        session = aiohttp.ClientSession()
        headers = {
            "Accept": "application/vnd.twitchtv.v5+json",
            "Client-ID": str(self._token)
        }
        params = {
            "community_id": self.id
        }
        url = TWITCH_BASE_URL + "/kraken/streams"
        async with session.get(url, headers=headers, params=params) as r:
            data = await r.json()
        if data["_total"] == 0:
            raise OfflineCommunity()
        else:
            return data["streams"]

    def export(self):
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                data[k] = v
        return data

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name}>".format(self)


class Stream:
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.channels = kwargs.pop("channels", [])
        #self.already_online = kwargs.pop("already_online", False)
        self._messages_cache = []
        self.type = self.__class__.__name__

    async def is_online(self):
        raise NotImplementedError()

    def make_embed(self):
        raise NotImplementedError()

    def export(self):
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                data[k] = v
        return data

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name}>".format(self)


class TwitchStream(Stream):
    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", None)
        self._token = kwargs.pop("token", None)
        super().__init__(**kwargs)

    async def is_online(self):
        if not self.id:
            self.id = await self.fetch_id()

        session = aiohttp.ClientSession()
        url = TWITCH_STREAMS_ENDPOINT + self.id
        header = {
            'Client-ID': str(self._token),
            'Accept': 'application/vnd.twitchtv.v5+json'
        }

        async with session.get(url, headers=header) as r:
            data = await r.json(encoding='utf-8')
        await session.close()
        if r.status == 200:
            if data["stream"] is None:
                #self.already_online = False
                raise OfflineStream()
            #self.already_online = True
            #  In case of rename
            self.name = data["stream"]["channel"]["name"]
            return self.make_embed(data)
        elif r.status == 400:
            raise InvalidCredentials()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    async def fetch_id(self):
        header = {
            'Client-ID': str(self._token),
            'Accept': 'application/vnd.twitchtv.v5+json'
        }
        url = TWITCH_ID_ENDPOINT + self.name
        session = aiohttp.ClientSession()

        async with session.get(url, headers=header) as r:
            data = await r.json()
        await session.close()

        if r.status == 200:
            if not data["users"]:
                raise StreamNotFound()
            return data["users"][0]["_id"]
        elif r.status == 400:
            raise InvalidCredentials()
        else:
            raise APIError()

    def make_embed(self, data):
        channel = data["stream"]["channel"]
        url = channel["url"]
        logo = channel["logo"]
        if logo is None:
            logo = ("https://static-cdn.jtvnw.net/"
                    "jtv_user_pictures/xarth/404_user_70x70.png")
        status = channel["status"]
        if not status:
            status = "Untitled broadcast"
        embed = discord.Embed(title=status, url=url)
        embed.set_author(name=channel["display_name"])
        embed.add_field(name="Followers", value=channel["followers"])
        embed.add_field(name="Total views", value=channel["views"])
        embed.set_thumbnail(url=logo)
        if data["stream"]["preview"]["medium"]:
            embed.set_image(url=rnd(data["stream"]["preview"]["medium"]))
        if channel["game"]:
            embed.set_footer(text="Playing: " + channel["game"])
        embed.color = 0x6441A4

        return embed

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name} (ID: {0.id})>".format(self)


class HitboxStream(Stream):
    async def is_online(self):
        session = aiohttp.ClientSession()
        url = "https://api.hitbox.tv/media/live/" + self.name

        async with session.get(url) as r:
            #data = await r.json(encoding='utf-8')
            data = await r.text()
        await session.close()
        data = json.loads(data, strict=False)
        if "livestream" not in data:
            raise StreamNotFound()
        elif data["livestream"][0]["media_is_live"] == "0":
            #self.already_online = False
            raise OfflineStream()
        elif data["livestream"][0]["media_is_live"] == "1":
            #self.already_online = True
            return self.make_embed(data)

        raise APIError()

    def make_embed(self, data):
        base_url = "https://edge.sf.hitbox.tv"
        livestream = data["livestream"][0]
        channel = livestream["channel"]
        url = channel["channel_link"]
        embed = discord.Embed(title=livestream["media_status"], url=url)
        embed.set_author(name=livestream["media_name"])
        embed.add_field(name="Followers", value=channel["followers"])
        embed.set_thumbnail(url=base_url + channel["user_logo"])
        if livestream["media_thumbnail"]:
            embed.set_image(url=rnd(base_url + livestream["media_thumbnail"]))
        embed.set_footer(text="Playing: " + livestream["category_name"])
        embed.color = 0x98CB00

        return embed


class MixerStream(Stream):
    async def is_online(self):
        url = "https://mixer.com/api/v1/channels/" + self.name

        session = aiohttp.ClientSession()
        async with session.get(url) as r:
            #data = await r.json(encoding='utf-8')
            data = await r.text(encoding='utf-8')
        await session.close()
        if r.status == 200:
            data = json.loads(data, strict=False)
            if data["online"] is True:
                #self.already_online = True
                return self.make_embed(data)
            else:
                #self.already_online = False
                raise OfflineStream()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    def make_embed(self, data):
        default_avatar = ("https://mixer.com/_latest/assets/images/main/"
                          "avatars/default.jpg")
        user = data["user"]
        url = "https://mixer.com/" + data["token"]
        embed = discord.Embed(title=data["name"], url=url)
        embed.set_author(name=user["username"])
        embed.add_field(name="Followers", value=data["numFollowers"])
        embed.add_field(name="Total views", value=data["viewersTotal"])
        if user["avatarUrl"]:
            embed.set_thumbnail(url=user["avatarUrl"])
        else:
            embed.set_thumbnail(url=default_avatar)
        if data["thumbnail"]:
            embed.set_image(url=rnd(data["thumbnail"]["url"]))
        embed.color = 0x4C90F3
        if data["type"] is not None:
            embed.set_footer(text="Playing: " + data["type"]["name"])
        return embed


class PicartoStream(Stream):
    async def is_online(self):
        url = "https://api.picarto.tv/v1/channel/name/" + self.name

        session = aiohttp.ClientSession()

        async with session.get(url) as r:
            data = await r.text(encoding='utf-8')
        await session.close()
        if r.status == 200:
            data = json.loads(data)
            if data["online"] is True:
                #self.already_online = True
                return self.make_embed(data)
            else:
                #self.already_online = False
                raise OfflineStream()
        elif r.status == 404:
            raise StreamNotFound()
        else:
            raise APIError()

    def make_embed(self, data):
        avatar = rnd("https://picarto.tv/user_data/usrimg/{}/dsdefault.jpg"
                     "".format(data["name"].lower()))
        url = "https://picarto.tv/" + data["name"]
        thumbnail = ("https://thumb.picarto.tv/thumbnail/{}.jpg"
                     "".format(data["name"]))
        embed = discord.Embed(title=data["title"], url=url)
        embed.set_author(name=data["name"])
        embed.set_image(url=rnd(thumbnail))
        embed.add_field(name="Followers", value=data["followers"])
        embed.add_field(name="Total views", value=data["viewers_total"])
        embed.set_thumbnail(url=avatar)
        embed.color = 0x132332
        data["tags"] = ", ".join(data["tags"])

        if not data["tags"]:
            data["tags"] = "None"

        if data["adult"]:
            data["adult"] = "NSFW | "
        else:
            data["adult"] = ""

        embed.color = 0x4C90F3
        embed.set_footer(text="{adult}Category: {category} | Tags: {tags}"
                              "".format(**data))
        return embed
