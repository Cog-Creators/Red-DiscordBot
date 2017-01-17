from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
import aiohttp
import asyncio
import os
import discord


class StreamHostCheck:
    """Mirror a Twitch user's hosted channel to Discord"""
    def __init__(self, bot):
        self.bot = bot
        self.settingsfile = "data/stream-hostcheck/settings.json"
        if dataIO.is_valid_json("data/streams/settings.json"):
            self.clientid =\
                dataIO.load_json("data/streams/settings.json")["TWITCH_TOKEN"]
        if dataIO.is_valid_json(self.settingsfile):
            self.username =\
                dataIO.load_json(self.settingsfile)["channel"]

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def channelset(self, ctx, channel: str):
        """Set the channel to be checked."""
        data = {"channel": channel}
        dataIO.save_json("data/stream-hostcheck/settings.json", data)
        self.username = channel
        await self.bot.say("Channel set!")

    async def set_stream(self):
        if self.username != "":
            async with aiohttp.get("https://api.twitch.tv/kraken/users/" +
                                   self.username + "?client_id=" +
                                   self.clientid) as user_r:
                user_json = await user_r.json()
                user_id = str(user_json["_id"])
            async with aiohttp.get(
                            "http://tmi.twitch.tv/hosts?include_logins=1&host="
                            + user_id) as host_r:
                host_json = await host_r.json()
                try:
                    target = host_json["hosts"][0]["target_login"]
                    async with aiohttp.get("https://api.twitch.tv/kraken/streams/" +
                                           target + "?client_id=" +
                                           self.clientid) as target_r:
                        target_json = await target_r.json()
                        streamer = "https://www.twitch.tv/" + target
                        title = target_json["stream"]["channel"]["status"]
                        game = discord.Game(type=1, url=streamer, name=title)
                        await self.bot.change_presence(game=game)
                except KeyError:
                    await self.bot.change_presence(game=None)
        await asyncio.sleep(600)


def check_folders():
    if not os.path.exists("data/stream-hostcheck"):
        print("Creating data/stream-hostcheck folder...")
        os.makedirs("data/stream-hostcheck")


def check_files():
    f = "data/stream-hostcheck/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty settings.json...")
        dataIO.save_json(f, {"channel": ""})


def setup(bot):
    check_folders()
    check_files()
    n = StreamHostCheck(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.set_stream())
    bot.add_cog(n)
