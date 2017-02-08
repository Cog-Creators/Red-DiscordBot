import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils.chat_formatting import *
from .utils import checks
from __main__ import send_cmd_help
from collections import defaultdict
import os
import re
import aiohttp
import asyncio
import logging


class Streams:
    """Streams

    Twitch, Hitbox and Beam alerts"""

    def __init__(self, bot):
        self.bot = bot
        self.twitch_streams = dataIO.load_json("data/streams/twitch.json")
        self.hitbox_streams = dataIO.load_json("data/streams/hitbox.json")
        self.beam_streams = dataIO.load_json("data/streams/beam.json")
        settings = dataIO.load_json("data/streams/settings.json")
        self.settings = defaultdict(dict, settings)

    @commands.command()
    async def hitbox(self, stream: str):
        """Checks if hitbox stream is online"""
        stream = escape_mass_mentions(stream)
        regex = r'^(https?\:\/\/)?(www\.)?(hitbox\.tv\/)'
        stream = re.sub(regex, '', stream)
        online = await self.hitbox_online(stream)
        if isinstance(online, discord.Embed):
            await self.bot.say(embed=online)
        elif online is False:
            await self.bot.say(stream + " is offline.")
        elif online is None:
            await self.bot.say("That stream doesn't exist.")
        else:
            await self.bot.say("Error.")

    @commands.command(pass_context=True)
    async def twitch(self, ctx, stream: str):
        """Checks if twitch stream is online"""
        stream = escape_mass_mentions(stream)
        regex = r'^(https?\:\/\/)?(www\.)?(twitch\.tv\/)'
        stream = re.sub(regex, '', stream)
        online = await self.twitch_online(stream)
        if isinstance(online, discord.Embed):
            await self.bot.say(embed=online)
        elif online is False:
            await self.bot.say(stream + " is offline.")
        elif online == 404:
            await self.bot.say("That stream doesn't exist.")
        elif online == 400:
            await self.bot.say("Owner: Client-ID is invalid or not set. "
                               "See `{}streamset twitchtoken`"
                               "".format(ctx.prefix))
        else:
            await self.bot.say("Error.")

    @commands.command()
    async def beam(self, stream: str):
        """Checks if beam stream is online"""
        stream = escape_mass_mentions(stream)
        regex = r'^(https?\:\/\/)?(www\.)?(beam\.pro\/)'
        stream = re.sub(regex, '', stream)
        online = await self.beam_online(stream)
        if isinstance(online, discord.Embed):
            await self.bot.say(embed=online)
        elif online is False:
            await self.bot.say(stream + " is offline.")
        elif online is None:
            await self.bot.say("That stream doesn't exist.")
        else:
            await self.bot.say("Error.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def streamalert(self, ctx):
        """Adds/removes stream alerts from the current channel"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @streamalert.command(name="twitch", pass_context=True)
    async def twitch_alert(self, ctx, stream: str):
        """Adds/removes twitch alerts from the current channel"""
        stream = escape_mass_mentions(stream)
        regex = r'^(https?\:\/\/)?(www\.)?(twitch\.tv\/)'
        stream = re.sub(regex, '', stream)
        channel = ctx.message.channel
        check = await self.twitch_online(stream)
        if check == 404:
            await self.bot.say("That stream doesn't exist.")
            return
        elif check == 400:
            await self.bot.say("Owner: Client-ID is invalid or not set. "
                               "See `{}streamset twitchtoken`"
                               "".format(ctx.prefix))
            return
        elif check == "error":
            await self.bot.say("Couldn't contact Twitch API. Try again later.")
            return

        done = False

        for i, s in enumerate(self.twitch_streams):
            if s["NAME"] == stream:
                if channel.id in s["CHANNELS"]:
                    if len(s["CHANNELS"]) == 1:
                        self.twitch_streams.remove(s)
                        await self.bot.say("Alert has been removed "
                                           "from this channel.")
                        done = True
                    else:
                        self.twitch_streams[i]["CHANNELS"].remove(channel.id)
                        await self.bot.say("Alert has been removed "
                                           "from this channel.")
                        done = True
                else:
                    self.twitch_streams[i]["CHANNELS"].append(channel.id)
                    await self.bot.say("Alert activated. I will notify this " +
                                       "channel everytime {}".format(stream) +
                                       " is live.")
                    done = True

        if not done:
            self.twitch_streams.append(
                {"CHANNELS": [channel.id],
                 "NAME": stream, "ALREADY_ONLINE": False})
            await self.bot.say("Alert activated. I will notify this channel "
                               "everytime {} is live.".format(stream))

        dataIO.save_json("data/streams/twitch.json", self.twitch_streams)

    @streamalert.command(name="hitbox", pass_context=True)
    async def hitbox_alert(self, ctx, stream: str):
        """Adds/removes hitbox alerts from the current channel"""
        stream = escape_mass_mentions(stream)
        regex = r'^(https?\:\/\/)?(www\.)?(hitbox\.tv\/)'
        stream = re.sub(regex, '', stream)
        channel = ctx.message.channel
        check = await self.hitbox_online(stream)
        if check is None:
            await self.bot.say("That stream doesn't exist.")
            return
        elif check == "error":
            await self.bot.say("Error.")
            return

        done = False

        for i, s in enumerate(self.hitbox_streams):
            if s["NAME"] == stream:
                if channel.id in s["CHANNELS"]:
                    if len(s["CHANNELS"]) == 1:
                        self.hitbox_streams.remove(s)
                        await self.bot.say("Alert has been removed from this "
                                           "channel.")
                        done = True
                    else:
                        self.hitbox_streams[i]["CHANNELS"].remove(channel.id)
                        await self.bot.say("Alert has been removed from this "
                                           "channel.")
                        done = True
                else:
                    self.hitbox_streams[i]["CHANNELS"].append(channel.id)
                    await self.bot.say("Alert activated. I will notify this "
                                       "channel everytime "
                                       "{} is live.".format(stream))
                    done = True

        if not done:
            self.hitbox_streams.append(
                {"CHANNELS": [channel.id], "NAME": stream,
                 "ALREADY_ONLINE": False})
            await self.bot.say("Alert activated. I will notify this channel "
                               "everytime {} is live.".format(stream))

        dataIO.save_json("data/streams/hitbox.json", self.hitbox_streams)

    @streamalert.command(name="beam", pass_context=True)
    async def beam_alert(self, ctx, stream: str):
        """Adds/removes beam alerts from the current channel"""
        stream = escape_mass_mentions(stream)
        regex = r'^(https?\:\/\/)?(www\.)?(beam\.pro\/)'
        stream = re.sub(regex, '', stream)
        channel = ctx.message.channel
        check = await self.beam_online(stream)
        if check is None:
            await self.bot.say("That stream doesn't exist.")
            return
        elif check == "error":
            await self.bot.say("Error.")
            return

        done = False

        for i, s in enumerate(self.beam_streams):
            if s["NAME"] == stream:
                if channel.id in s["CHANNELS"]:
                    if len(s["CHANNELS"]) == 1:
                        self.beam_streams.remove(s)
                        await self.bot.say("Alert has been removed from this "
                                           "channel.")
                        done = True
                    else:
                        self.beam_streams[i]["CHANNELS"].remove(channel.id)
                        await self.bot.say("Alert has been removed from this "
                                           "channel.")
                        done = True
                else:
                    self.beam_streams[i]["CHANNELS"].append(channel.id)
                    await self.bot.say("Alert activated. I will notify this "
                                       "channel everytime "
                                       "{} is live.".format(stream))
                    done = True

        if not done:
            self.beam_streams.append(
                {"CHANNELS": [channel.id], "NAME": stream,
                 "ALREADY_ONLINE": False})
            await self.bot.say("Alert activated. I will notify this channel "
                               "everytime {} is live.".format(stream))

        dataIO.save_json("data/streams/beam.json", self.beam_streams)

    @streamalert.command(name="stop", pass_context=True)
    async def stop_alert(self, ctx):
        """Stops all streams alerts in the current channel"""
        channel = ctx.message.channel

        to_delete = []

        for s in self.hitbox_streams:
            if channel.id in s["CHANNELS"]:
                if len(s["CHANNELS"]) == 1:
                    to_delete.append(s)
                else:
                    s["CHANNELS"].remove(channel.id)

        for s in to_delete:
            self.hitbox_streams.remove(s)

        to_delete = []

        for s in self.twitch_streams:
            if channel.id in s["CHANNELS"]:
                if len(s["CHANNELS"]) == 1:
                    to_delete.append(s)
                else:
                    s["CHANNELS"].remove(channel.id)

        for s in to_delete:
            self.twitch_streams.remove(s)

        to_delete = []

        for s in self.beam_streams:
            if channel.id in s["CHANNELS"]:
                if len(s["CHANNELS"]) == 1:
                    to_delete.append(s)
                else:
                    s["CHANNELS"].remove(channel.id)

        for s in to_delete:
            self.beam_streams.remove(s)

        dataIO.save_json("data/streams/twitch.json", self.twitch_streams)
        dataIO.save_json("data/streams/hitbox.json", self.hitbox_streams)
        dataIO.save_json("data/streams/beam.json", self.beam_streams)

        await self.bot.say("There will be no more stream alerts in this "
                           "channel.")

    @commands.group(pass_context=True)
    async def streamset(self, ctx):
        """Stream settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @streamset.command()
    @checks.is_owner()
    async def twitchtoken(self, token : str):
        """Sets the Client-ID for Twitch

        https://blog.twitch.tv/client-id-required-for-kraken-api-calls-afbb8e95f843"""
        self.settings["TWITCH_TOKEN"] = token
        dataIO.save_json("data/streams/settings.json", self.settings)
        await self.bot.say('Twitch Client-ID set.')

    @streamset.command(pass_context=True)
    @checks.admin()
    async def mention(self, ctx, *, mention_type : str):
        """Sets mentions for stream alerts

        Types: everyone, here, none"""
        server = ctx.message.server
        mention_type = mention_type.lower()

        if mention_type in ("everyone", "here"):
            self.settings[server.id]["MENTION"] = "@" + mention_type
            await self.bot.say("When a stream is online @\u200b{} will be "
                               "mentioned.".format(mention_type))
        elif mention_type == "none":
            self.settings[server.id]["MENTION"] = ""
            await self.bot.say("Mentions disabled.")
        else:
            await self.bot.send_cmd_help(ctx)

        dataIO.save_json("data/streams/settings.json", self.settings)

    async def hitbox_online(self, stream):
        url = "https://api.hitbox.tv/media/live/" + stream
        try:
            async with aiohttp.get(url) as r:
                data = await r.json()
            if "livestream" not in data:
                return None
            if data["livestream"][0]["media_is_live"] == "0":
                return False
            elif data["livestream"][0]["media_is_live"] == "1":
                data = self.hitbox_embed(data)
                return data
            return "error"
        except:
            return "error"

    async def twitch_online(self, stream):
        session = aiohttp.ClientSession()
        url = "https://api.twitch.tv/kraken/streams/" + stream
        header = {'Client-ID': self.settings.get("TWITCH_TOKEN", "")}
        try:
            async with session.get(url, headers=header) as r:
                data = await r.json()
            await session.close()
            if r.status == 400:
                return 400
            elif r.status == 404:
                return 404
            elif data["stream"] is None:
                return False
            elif data["stream"]:
                embed = self.twitch_embed(data)
                return embed
        except:
            return "error"
        return "error"

    async def beam_online(self, stream):
        url = "https://beam.pro/api/v1/channels/" + stream
        try:
            async with aiohttp.get(url) as r:
                data = await r.json()
            if "online" in data:
                if data["online"] is True:
                    data = self.beam_embed(data)
                    return data
                else:
                    return False
            elif "error" in data:
                return None
        except:
            return "error"
        return "error"

    def twitch_embed(self, data):
        channel = data["stream"]["channel"]
        url = channel["url"]
        embed = discord.Embed(title=channel["status"], url=url)
        embed.set_author(name=channel["display_name"])
        embed.add_field(name="Followers", value=channel["followers"])
        embed.add_field(name="Total views", value=channel["views"])
        embed.set_thumbnail(url=channel["logo"])
        embed.set_image(url=data["stream"]["preview"]["medium"])
        embed.set_footer(text="Playing: " + channel["game"])
        embed.color = 0x6441A4
        return embed

    def hitbox_embed(self, data):
        base_url = "https://edge.sf.hitbox.tv"
        livestream = data["livestream"][0]
        channel = livestream["channel"]
        url = channel["channel_link"]
        embed = discord.Embed(title=livestream["media_status"], url=url)
        embed.set_author(name=livestream["media_name"])
        embed.add_field(name="Followers", value=channel["followers"])
        #embed.add_field(name="Views", value=channel["views"])
        embed.set_thumbnail(url=base_url + channel["user_logo"])
        embed.set_image(url=base_url + livestream["media_thumbnail"])
        embed.set_footer(text="Playing: " + livestream["category_name"])
        embed.color = 0x98CB00
        return embed

    def beam_embed(self, data):
        user = data["user"]
        url = "https://beam.pro/" + data["token"]
        embed = discord.Embed(title=data["name"], url=url)
        embed.set_author(name=user["username"])
        embed.add_field(name="Followers", value=data["numFollowers"])
        embed.add_field(name="Total views", value=data["viewersTotal"])
        embed.set_thumbnail(url=user["avatarUrl"])
        embed.set_image(url=data["thumbnail"]["url"])
        embed.color = 0x4C90F3
        if data["type"] is not None:
            embed.set_footer(text="Playing: " + data["type"]["name"])
        return embed

    async def stream_checker(self):
        CHECK_DELAY = 60

        while self == self.bot.get_cog("Streams"):
            save = False

            streams = ((self.twitch_streams, self.twitch_online),
                       (self.hitbox_streams, self.hitbox_online),
                       (self.beam_streams,   self.beam_online))

            for stream_type in streams:
                streams = stream_type[0]
                parser = stream_type[1]
                for stream in streams:
                    online = await parser(stream["NAME"])
                    if isinstance(online, discord.Embed) and not stream["ALREADY_ONLINE"]:
                        save = True
                        stream["ALREADY_ONLINE"] = True
                        for channel in stream["CHANNELS"]:
                            channel_obj = self.bot.get_channel(channel)
                            if channel_obj is None:
                                continue
                            mention = self.settings.get(channel_obj.server.id, {}).get("MENTION", "")
                            can_speak = channel_obj.permissions_for(channel_obj.server.me).send_messages
                            if channel_obj and can_speak:
                                await self.bot.send_message(channel_obj, mention, embed=online)
                    else:
                        if stream["ALREADY_ONLINE"] and not online:
                            save = True
                            stream["ALREADY_ONLINE"] = False
                    await asyncio.sleep(0.5)

            if save:
                dataIO.save_json("data/streams/twitch.json", self.twitch_streams)
                dataIO.save_json("data/streams/hitbox.json", self.hitbox_streams)
                dataIO.save_json("data/streams/beam.json", self.beam_streams)

            await asyncio.sleep(CHECK_DELAY)


def check_folders():
    if not os.path.exists("data/streams"):
        print("Creating data/streams folder...")
        os.makedirs("data/streams")


def check_files():
    f = "data/streams/twitch.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty twitch.json...")
        dataIO.save_json(f, [])

    f = "data/streams/hitbox.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty hitbox.json...")
        dataIO.save_json(f, [])

    f = "data/streams/beam.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty beam.json...")
        dataIO.save_json(f, [])

    f = "data/streams/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    logger = logging.getLogger('aiohttp.client')
    logger.setLevel(50)  # Stops warning spam
    check_folders()
    check_files()
    n = Streams(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.stream_checker())
    bot.add_cog(n)
