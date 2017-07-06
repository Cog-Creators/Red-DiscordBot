from discord.ext import commands
from core.config import Config
from core.utils.chat_formatting import pagify
from core import checks
from core.bot import Red
from .streams import TwitchStream, HitboxStream, MixerStream, PicartoStream, TwitchCommunity
from .errors import OfflineStream, StreamNotFound, APIError, InvalidCredentials, CommunityNotFound, OfflineCommunity
from . import streams as StreamClasses
from collections import defaultdict
import asyncio

CHECK_DELAY = 60


class Streams:
    def __init__(self, bot: Red):
        self.db = Config.get_conf(self, 26262626, force_registration=True)

        self.db.register_global(
            tokens={},
            streams=[],
            communities=[]
        )

        self.db.register_guild(
            autodelete=False,
            mention=""
        )

        self.streams = self.load_streams()
        self.communities = self.load_communities()
        self.task = bot.loop.create_task(self._stream_alerts())
        self.bot = bot

    @commands.command()
    async def twitch(self, ctx, channel_name: str):
        """Checks if a Twitch channel is streaming"""
        token = self.db.tokens().get(TwitchStream.__name__)
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
            await ctx.bot.send_cmd_help(ctx)

    @streamalert.group(name="twitch")
    async def twitch(self, ctx):
        """Twitch stream alerts"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @twitch.command(name="channel")
    async def twitch_alert_channel(self, ctx: commands.Context, channel_name: str):
        """Sets a Twitch stream alert notification in the channel"""
        await self.stream_alert(ctx, TwitchStream, channel_name)

    @twitch.command(name="community")
    async def twitch_alert_community(self, ctx: commands.Context, community: str):
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
            token = self.db.tokens().get(_class.__name__)
            stream = _class(name=channel_name,
                            token=token)
            if not await self.check_exists(stream):
                await ctx.send("That channel doesn't seem to exist.")
                return

        await self.add_or_remove(ctx, stream)

    async def community_alert(self, ctx, _class, community_name):
        community = self.get_community(_class, community_name)
        if not community:
            token = self.db.tokens().get(_class.__name__)
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
            await ctx.bot.send_cmd_help(ctx)

    @streamset.command()
    @checks.is_owner()
    async def twitchtoken(self, ctx, token: str):
        tokens = self.db.tokens()
        tokens["TwitchStream"] = token
        tokens["TwitchCommunity"] = token
        await self.db.set("tokens", tokens)
        await ctx.send("Twitch token set.")

    @streamset.command()
    @commands.guild_only()
    async def mention(self, ctx, mention_type: str):
        ...

    @streamset.command()
    @commands.guild_only()
    async def autodelete(self, ctx, on_off: bool):
        """Toggles automatic deletion of notifications for streams that go offline"""
        await self.db.guild(ctx.guild).set("autodelete", on_off)
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

    def load_streams(self):
        streams = []

        for raw_stream in self.db.streams():
            _class = getattr(StreamClasses, raw_stream["type"], None)
            if not _class:
                continue

            token = self.db.tokens().get(_class.__name__)
            streams.append(_class(token=token, **raw_stream))

        return streams

    def load_communities(self):
        communities = []

        for raw_community in self.db.communities():
            _class = getattr(StreamClasses, raw_community["type"], None)
            if not _class:
                continue

            token = self.db.tokens().get(_class.__name__)
            communities.append(_class(token=token, **raw_community))

        return communities

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.db.set("streams", raw_streams)

    async def save_communities(self):
        raw_communities = []
        for community in self.communities:
            raw_communities.append(community.export())

        await self.db.set("communities", raw_communities)

    def __unload(self):
        self.task.cancel()
