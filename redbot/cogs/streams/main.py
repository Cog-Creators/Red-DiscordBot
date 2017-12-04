import discord
from discord.ext import commands
from redbot.core import Config, checks, RedContext
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.bot import Red
from .streams import TwitchStream, HitboxStream, MixerStream, PicartoStream, TwitchCommunity
from .errors import OfflineStream, StreamNotFound, APIError, InvalidCredentials, CommunityNotFound, OfflineCommunity
from . import streams as StreamClasses
from collections import defaultdict
import asyncio

CHECK_DELAY = 60


class Streams:

    global_defaults = {
        "tokens": {},
        "streams": [],
        "communities": []
    }

    guild_defaults = {
        "autodelete": False,
        "mention_everyone": False,
        "mention_here": False
    }

    role_defaults = {
        "mention": False
    }

    def __init__(self, bot: Red):
        self.db = Config.get_conf(self, 26262626)

        self.db.register_global(**self.global_defaults)

        self.db.register_guild(**self.guild_defaults)

        self.db.register_role(**self.role_defaults)

        self.bot = bot

        self.bot.loop.create_task(self._initialize_lists())

    async def _initialize_lists(self):
        await self.bot.loop.create_task(self.load_streams())
        await self.bot.loop.create_task(self.load_communities())

        self.task = self.bot.loop.create_task(self._stream_alerts())

    @commands.command()
    async def twitch(self, ctx, channel_name: str):
        """Checks if a Twitch channel is streaming"""
        token = await self.db.tokens.get_attr(TwitchStream.__name__)
        stream = TwitchStream(name=channel_name,
                              token=token)
        await self.check_online(ctx, stream)

    @commands.command()
    async def hitbox(self, ctx, channel_name: str):
        """Checks if a Hitbox channel is streaming"""
        stream = HitboxStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def mixer(self, ctx, channel_name: str):
        """Checks if a Mixer channel is streaming"""
        stream = MixerStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def picarto(self, ctx, channel_name: str):
        """Checks if a Picarto channel is streaming"""
        stream = PicartoStream(name=channel_name)
        await self.check_online(ctx, stream)

    async def check_online(self, ctx, stream):
        try:
            embed = await stream.is_online()
        except OfflineStream:
            await ctx.send("The stream is offline.")
        except StreamNotFound:
            await ctx.send("The channel doesn't seem to exist.")
        except InvalidCredentials:
            await ctx.send("Invalid twitch token.")
        except APIError:
            await ctx.send("Error contacting the API.")
        else:
            await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @checks.mod()
    async def streamalert(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @streamalert.group(name="twitch")
    async def _twitch(self, ctx):
        """Twitch stream alerts"""
        if isinstance(ctx.invoked_subcommand, commands.Group):
            await ctx.send_help()

    @_twitch.command(name="channel")
    async def twitch_alert_channel(self, ctx: RedContext, channel_name: str):
        """Sets a Twitch stream alert notification in the channel"""
        await self.stream_alert(ctx, TwitchStream, channel_name)

    @_twitch.command(name="community")
    async def twitch_alert_community(self, ctx: RedContext, community: str):
        """Sets a Twitch stream alert notification in the channel
        for the specified community."""
        await self.community_alert(ctx, TwitchCommunity, community)

    @streamalert.command(name="hitbox")
    async def hitbox_alert(self, ctx, channel_name: str):
        """Sets a Hitbox stream alert notification in the channel"""
        await self.stream_alert(ctx, HitboxStream, channel_name)

    @streamalert.command(name="mixer")
    async def mixer_alert(self, ctx, channel_name: str):
        """Sets a Mixer stream alert notification in the channel"""
        await self.stream_alert(ctx, MixerStream, channel_name)

    @streamalert.command(name="picarto")
    async def picarto_alert(self, ctx, channel_name: str):
        """Sets a Picarto stream alert notification in the channel"""
        await self.stream_alert(ctx, PicartoStream, channel_name)

    @streamalert.command(name="stop")
    async def streamalert_stop(self, ctx, _all: bool=False):
        """Stops all stream notifications in the channel

        Adding 'yes' will disable all notifications in the server"""
        streams = self.streams.copy()
        local_channel_ids = [c.id for c in ctx.guild.channels]
        to_remove = []

        for stream in streams:
            for channel_id in stream.channels:
                if channel_id == ctx.channel.id:
                    stream.channels.remove(channel_id)
                elif _all and ctx.channel.id in local_channel_ids:
                    if channel_id in stream.channels:
                        stream.channels.remove(channel_id)

            if not stream.channels:
                to_remove.append(stream)

        for stream in to_remove:
            streams.remove(stream)

        self.streams = streams
        await self.save_streams()

        msg = "All {}'s stream alerts have been disabled." \
              "".format("server" if _all else "channel")

        await ctx.send(msg)

    @streamalert.command(name="list")
    async def streamalert_list(self, ctx):
        streams_list = defaultdict(list)
        guild_channels_ids = [c.id for c in ctx.guild.channels]
        msg = "Active stream alerts:\n\n"

        for stream in self.streams:
            for channel_id in stream.channels:
                if channel_id in guild_channels_ids:
                    streams_list[channel_id].append(stream.name)

        if not streams_list:
            await ctx.send("There are no active stream alerts in this server.")
            return

        for channel_id, streams in streams_list.items():
            channel = ctx.guild.get_channel(channel_id)
            msg += "** - #{}**\n{}\n".format(channel, ", ".join(streams))

        for page in pagify(msg):
            await ctx.send(page)

    async def stream_alert(self, ctx, _class, channel_name):
        stream = self.get_stream(_class, channel_name)
        if not stream:
            token = await self.db.tokens.get_attr(_class.__name__)
            stream = _class(name=channel_name,
                            token=token)
            if not await self.check_exists(stream):
                await ctx.send("That channel doesn't seem to exist.")
                return

        await self.add_or_remove(ctx, stream)

    async def community_alert(self, ctx, _class, community_name):
        community = self.get_community(_class, community_name)
        if not community:
            token = await self.db.tokens.get_attr(_class.__name__)
            community = _class(name=community_name, token=token)
            try:
                await community.get_community_streams()
            except CommunityNotFound:
                await ctx.send("That community doesn't seem to exist")
                return
        await self.add_or_remove_community(ctx, community)

    @commands.group()
    @checks.mod()
    async def streamset(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @streamset.command()
    @checks.is_owner()
    async def twitchtoken(self, ctx, token: str):
        tokens = await self.db.tokens()
        tokens["TwitchStream"] = token
        tokens["TwitchCommunity"] = token
        await self.db.tokens.set(tokens)
        await ctx.send("Twitch token set.")

    @streamset.group()
    @commands.guild_only()
    async def mention(self, ctx):
        """Sets mentions for stream alerts
        Types: everyone, here, role, none"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @mention.command()
    @commands.guild_only()
    async def all(self, ctx):
        """Toggles everyone mention"""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).mention_everyone()
        if current_setting:
            await self.db.guild(guild).mention_everyone.set(False)
            await ctx.send("@\u200beveryone will no longer be mentioned "
                           "for a stream alert.")
        else:
            await self.db.guild(guild).mention_everyone.set(True)
            await ctx.send("When a stream configured for stream alerts "
                           "comes online, @\u200beveryone will be mentioned")

    @mention.command()
    @commands.guild_only()
    async def online(self, ctx):
        """Toggles here mention"""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).mention_here()
        if current_setting:
            await self.db.guild(guild).mention_here.set(False)
            await ctx.send("@\u200bhere will no longer be mentioned "
                           "for a stream alert.")
        else:
            await self.db.guild(guild).mention_here.set(True)
            await ctx.send("When a stream configured for stream alerts "
                           "comes online, @\u200bhere will be mentioned")

    @mention.command()
    @commands.guild_only()
    async def role(self, ctx, role: discord.Role):
        """Toggles role mention"""
        current_setting = await self.db.role(role).mention()
        if not role.mentionable:
            await ctx.send("That role is not mentionable!")
            return
        if current_setting:
            await self.db.role(role).mention.set(False)
            await ctx.send("@\u200b{} will no longer be mentioned "
                           "for a stream alert".format(role.name))
        else:
            await self.db.role(role).mention.set(True)
            await ctx.send("When a stream configured for stream alerts "
                           "comes online, @\u200b{} will be mentioned"
                           "".format(role.name))

    @streamset.command()
    @commands.guild_only()
    async def autodelete(self, ctx, on_off: bool):
        """Toggles automatic deletion of notifications for streams that go offline"""
        await self.db.guild(ctx.guild).autodelete.set(on_off)
        if on_off:
            await ctx.send("The notifications will be deleted once "
                           "streams go offline.")
        else:
            await ctx.send("Notifications will never be deleted.")

    async def add_or_remove(self, ctx, stream):
        if ctx.channel.id not in stream.channels:
            stream.channels.append(ctx.channel.id)
            if stream not in self.streams:
                self.streams.append(stream)
            await ctx.send("I'll send a notification in this channel when {} "
                           "is online.".format(stream.name))
        else:
            stream.channels.remove(ctx.channel.id)
            if not stream.channels:
                self.streams.remove(stream)
            await ctx.send("I won't send notifications about {} in this "
                           "channel anymore.".format(stream.name))

        await self.save_streams()

    async def add_or_remove_community(self, ctx, community):
        if ctx.channel.id not in community.channels:
            community.channels.append(ctx.channel.id)
            if community not in self.communities:
                self.communities.append(community)
            await ctx.send("I'll send a notification in this channel when a "
                           "channel is streaming to the {} community"
                           "".format(community.name))
        else:
            community.channels.remove(ctx.channel.id)
            if not community.channels:
                self.communities.remove(community)
            await ctx.send("I won't send notifications about channels streaming "
                           "to the {} community in this channel anymore"
                           "".format(community.name))
        await self.save_communities()

    def get_stream(self, _class, name):
        for stream in self.streams:
            # if isinstance(stream, _class) and stream.name == name:
            #    return stream
            # Reloading this cog causes an issue with this check ^
            # isinstance will always return False
            # As a workaround, we'll compare the class' name instead.
            # Good enough.
            if stream.type == _class.__name__ and stream.name == name:
                return stream

    def get_community(self, _class, name):
        for community in self.communities:
            if community.type == _class.__name__ and community.name == name:
                return community

    async def check_exists(self, stream):
        try:
            await stream.is_online()
        except OfflineStream:
            pass
        except:
            return False
        return True

    async def _stream_alerts(self):
        while True:
            try:
                await self.check_streams()
            except asyncio.CancelledError:
                pass
            try:
                await self.check_communities()
            except asyncio.CancelledError:
                pass
            await asyncio.sleep(CHECK_DELAY)

    async def check_streams(self):
        for stream in self.streams:
            try:
                embed = await stream.is_online()
            except OfflineStream:
                for message in stream._messages_cache:
                    try:
                        autodelete = self.db.guild(message.guild).autodelete()
                        if autodelete:
                            await message.delete()
                    except:
                        pass
                stream._messages_cache.clear()
            except:
                pass
            else:
                if stream._messages_cache:
                    continue
                for channel_id in stream.channels:
                    channel = self.bot.get_channel(channel_id)
                    mention_everyone = await self.db.guild(channel.guild).mention_everyone()
                    mention_here = await self.db.guild(channel.guild).mention_here()
                    mention_roles = []
                    for r in channel.guild.roles:
                        to_append = {
                            "role": r,
                            "enabled": await self.db.role(r).mention()
                        }
                        mention_roles.append(to_append)
                    mention = None
                    if mention_everyone or mention_here or any(mention_roles):
                        mention = True
                    if mention:
                        mention_str = ""
                        if mention_everyone:
                            mention_str += "@everyone "
                        if mention_here:
                            mention_str += "@here "
                        if any(mention_roles):
                            mention_str += " ".join(
                                [
                                    r["role"].mention for r in mention_roles
                                    if r["role"].mentionable and r["enabled"]
                                ]
                            )
                        mention_str = mention_str.strip()
                        try:
                            m = await channel.send(
                                "{}, {} is online!".format(
                                    mention_str, stream.name
                                ), embed=embed
                            )
                            stream._messages_cache.append(m)
                        except:
                            pass
                    else:
                        try:
                            m = await channel.send("%s is online!" % stream.name,
                                                   embed=embed)
                            stream._messages_cache.append(m)
                        except:
                            pass

    async def check_communities(self):
        for community in self.communities:
            try:
                streams = community.get_community_streams()
            except CommunityNotFound:
                print("Community {} not found!".format(community.name))
                continue
            except OfflineCommunity:
                pass
            else:
                token = self.db.tokens().get(TwitchStream.__name__)
                for channel in community.channels:
                    chn = self.bot.get_channel(channel)
                    await chn.send("Online streams for {}".format(community.name))
                for stream in streams:
                    stream_obj = TwitchStream(
                        token=token, name=stream["channel"]["name"],
                        id=stream["_id"]
                    )
                    try:
                        emb = await stream_obj.is_online()
                    except:
                        pass
                    else:
                        for channel in community.channels:
                            chn = self.bot.get_channel(channel)
                            await chn.send(embed=emb)

    async def load_streams(self):
        streams = []

        for raw_stream in await self.db.streams():
            _class = getattr(StreamClasses, raw_stream["type"], None)
            if not _class:
                continue

            token = await self.db.tokens.get_attr(_class.__name__)
            streams.append(_class(token=token, **raw_stream))

        self.streams = streams

    async def load_communities(self):
        communities = []

        for raw_community in await self.db.communities():
            _class = getattr(StreamClasses, raw_community["type"], None)
            if not _class:
                continue

            token = await self.db.tokens.get_attr(_class.__name__)
            communities.append(_class(token=token, **raw_community))

        self.communities = communities

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.db.streams.set(raw_streams)

    async def save_communities(self):
        raw_communities = []
        for community in self.communities:
            raw_communities.append(community.export())

        await self.db.communities.set(raw_communities)

    def __unload(self):
        self.task.cancel()
